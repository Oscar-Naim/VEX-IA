"""
LYAXIS labs™ - Control Acústico de Audio Ducking para VEX
Atenúa automáticamente el volumen maestro de Windows (25%) durante la captura
vocal para garantizar que la música o sonidos de la PC no contaminen el micrófono.
"""
import ctypes
import threading
import time
from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities
    HAVE_PYCAW = True
except Exception:
    HAVE_PYCAW = False


class AudioDucker:
    """
    Controlador de Audio Ducking para el sistema operativo Windows.
    Permite atenuar temporalmente el volumen de altavoces mientras VEX escucha
    al usuario o procesa una orden vocal, evitando interferencias de Spotify/reproducción.
    """
    _lock = threading.Lock()
    _original_volume: Optional[float] = None
    _restore_timer: Optional[threading.Timer] = None
    _is_ducked: bool = False

    @classmethod
    def _get_endpoint_volume(cls):
        """Obtiene el objeto de volumen de altavoces de Windows."""
        if not HAVE_PYCAW:
            return None
        try:
            speakers = AudioUtilities.GetSpeakers()
            return speakers.EndpointVolume
        except Exception:
            return None

    @classmethod
    def duck(cls, target_scalar: float = 0.25, duration: float = 4.0):
        """
        Atenúa el volumen del sistema al porcentaje especificado (ej. 0.25 = 25%)
        durante el tiempo indicado en segundos. Si ya está atenuado, refresca el temporizador.
        """
        if not HAVE_PYCAW:
            return

        def _do_duck():
            with cls._lock:
                # Cancelar temporizador previo de restauración si existe
                if cls._restore_timer:
                    try:
                        cls._restore_timer.cancel()
                    except Exception:
                        pass
                    cls._restore_timer = None

                ctypes.windll.ole32.CoInitialize(None)
                try:
                    vol = cls._get_endpoint_volume()
                    if not vol:
                        return

                    current = vol.GetMasterVolumeLevelScalar()

                    # Guardar volumen original solo la primera vez que se atenúa
                    if not cls._is_ducked or cls._original_volume is None:
                        cls._original_volume = current

                    # Solo reducir si el volumen actual es mayor que el objetivo
                    if current > target_scalar:
                        vol.SetMasterVolumeLevelScalar(target_scalar, None)
                        print(f"[VEX Ducking] [VOL] Volumen atenuado al {int(target_scalar * 100)}% (era {int(current * 100)}%)")

                    cls._is_ducked = True

                    # Programar restauración automática tras `duration` segundos
                    cls._restore_timer = threading.Timer(duration, cls.restore)
                    cls._restore_timer.daemon = True
                    cls._restore_timer.start()

                except Exception as e:
                    print(f"[VEX Ducking] Error al atenuar volumen: {e}")
                finally:
                    ctypes.windll.ole32.CoUninitialize()

        threading.Thread(target=_do_duck, daemon=True).start()

    @classmethod
    def restore(cls):
        """
        Restaura de inmediato el volumen original previo al ducking.
        """
        if not HAVE_PYCAW:
            return

        def _do_restore():
            with cls._lock:
                if cls._restore_timer:
                    try:
                        cls._restore_timer.cancel()
                    except Exception:
                        pass
                    cls._restore_timer = None

                if not cls._is_ducked or cls._original_volume is None:
                    cls._is_ducked = False
                    return

                ctypes.windll.ole32.CoInitialize(None)
                try:
                    vol = cls._get_endpoint_volume()
                    if vol and cls._original_volume is not None:
                        vol.SetMasterVolumeLevelScalar(cls._original_volume, None)
                        print(f"[VEX Ducking] [VOL] Volumen restaurado al {int(cls._original_volume * 100)}%")
                except Exception as e:
                    print(f"[VEX Ducking] Error al restaurar volumen: {e}")
                finally:
                    cls._original_volume = None
                    cls._is_ducked = False
                    ctypes.windll.ole32.CoUninitialize()

        threading.Thread(target=_do_restore, daemon=True).start()
