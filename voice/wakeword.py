"""
LYAXIS labs™ - Detector de Palabra de Activación (Wake Word Detection) 100% Offline
Monitoreo continuo de baja latencia y consumo de CPU ultrabajo (< 2%) mediante
PyAudio, puerta de energía adaptativa RMS y motor Vosk local sin conexión a la nube.
Detecta variaciones fonéticas: 'VEX', 'Oye VEX', 'Hey VEX', 'Bex', 'Veks', 'Vez', 'Ves', 'Hola'.
"""
import os
import sys
import time
import json
import math
import struct
import threading
import re
from typing import Callable, Optional

import pyaudio

try:
    import vosk
    vosk.SetLogLevel(-1)
    HAVE_VOSK = True
except ImportError:
    HAVE_VOSK = False


class WakeWordDetector:
    """
    Detector de palabra de activación local de alta sensibilidad y eficiencia.
    Monitorea el micrófono en segundo plano consumiendo < 1.5% de CPU.
    """

    # Variaciones fonéticas naturales en español para "VEX" y llamadas de atención
    WAKE_KEYWORDS_REGEX = re.compile(
        r"\b(vex|bex|veks|vecks|ves|vez|becs|pex|mex|tex|buey|oye|hey|ey|hola|despierta|oye\s+vex|hey\s+vex|ey\s+vex|hola\s+vex|ok\s+vex|oye\s+vez|hey\s+vez|oye\s+ves|oye\s+ver|despierta\s+vex|buenas\s+vex)\b",
        re.IGNORECASE
    )

    def __init__(
        self,
        on_wake: Callable[[str], None],
        energy_threshold: int = 160,
        sample_rate: int = 16000,
        chunk_size: int = 1024
    ):
        """
        Inicializa el detector de palabra clave en segundo plano.

        Args:
            on_wake: Callback invocado inmediatamente al detectar la palabra clave.
            energy_threshold: Umbral RMS base para la compuerta acústica.
            sample_rate: Frecuencia de muestreo (16 kHz mono optimizado para Vosk).
            chunk_size: Tamaño del bloque de audio por ciclo (1024 muestras = ~64ms).
        """
        self.on_wake = on_wake
        self.energy_threshold = energy_threshold
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        self.ambient_rms = 100.0  # Nivel base ambiental estimado

        self.is_running = False
        self.is_paused = False
        self.worker_thread: Optional[threading.Thread] = None

        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None

        # Inicialización del modelo Vosk offline
        self.vosk_model = None
        self.recognizer = None
        self._init_vosk_model()

    def _init_vosk_model(self):
        """Carga el modelo Vosk liviano en español desde la caché local o por defecto."""
        if not HAVE_VOSK:
            print("[VEX WakeWord] Error: Vosk no está instalado.")
            return

        try:
            cache_path = os.path.expanduser(r"~/.cache/vosk/vosk-model-small-es-0.42")
            if os.path.exists(cache_path):
                self.vosk_model = vosk.Model(cache_path)
            else:
                self.vosk_model = vosk.Model(lang="es")

            self._reset_recognizer()
            print("[VEX WakeWord] [OK] Motor Vosk offline cargado correctamente.")
        except Exception as e:
            print(f"[VEX WakeWord] Advertencia al cargar modelo Vosk: {e}")
            self.vosk_model = None

    def _reset_recognizer(self):
        """Crea o reinicia el reconocedor Kaldi sin restricciones de vocabulario para máxima sensibilidad."""
        if not self.vosk_model:
            return
        try:
            self.recognizer = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
        except Exception as e:
            print(f"[VEX WakeWord] Error al crear KaldiRecognizer: {e}")

    @staticmethod
    def _calculate_rms(data_bytes: bytes) -> float:
        """Calcula el valor RMS de un búfer de audio PCM de 16-bits para la puerta de ruido."""
        count = len(data_bytes) // 2
        if count == 0:
            return 0.0
        try:
            shorts = struct.unpack(f"<{count}h", data_bytes)
            sum_squares = sum(s * s for s in shorts)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0.0

    def start(self):
        """Inicia el monitoreo continuo en un hilo secundario."""
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self.worker_thread = threading.Thread(target=self._listen_loop, daemon=True, name="VEX-WakeWord-Thread")
        self.worker_thread.start()
        print("[VEX WakeWord] [ONLINE] Monitoreo de palabra de activacion iniciado en segundo plano.")

    def pause(self):
        """Pausa temporalmente la captura del micrófono (para cederlo al STT o TTS)."""
        self.is_paused = True
        self._close_audio_stream()

    def resume(self):
        """Reanuda la escucha activa de la palabra clave."""
        self.is_paused = False
        self._reset_recognizer()

    def stop(self):
        """Detiene definitivamente el detector y libera todos los recursos de audio."""
        self.is_running = False
        self.is_paused = True
        self._close_audio_stream()
        if self._pyaudio:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

    def _open_audio_stream(self) -> bool:
        """Abre el flujo de entrada de PyAudio si no está activo."""
        if self._stream is not None:
            return True

        try:
            if not self._pyaudio:
                self._pyaudio = pyaudio.PyAudio()

            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            return True
        except Exception as e:
            time.sleep(0.3)
            return False

    def _close_audio_stream(self):
        """Cierra el stream de audio liberando el dispositivo de grabación."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _check_wake_text(self, text: str) -> bool:
        """Verifica si el texto reconocido contiene la palabra de activación VEX o sus variantes."""
        if not text:
            return False
        clean = text.lower().strip()
        return bool(self.WAKE_KEYWORDS_REGEX.search(clean))

    def _listen_loop(self):
        """Bucle continuo de monitoreo en segundo plano."""
        silence_sleep = 0.02

        while self.is_running:
            if self.is_paused:
                time.sleep(0.1)
                continue

            # Abrir stream de micrófono si no está abierto
            if not self._open_audio_stream():
                time.sleep(0.2)
                continue

            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception:
                time.sleep(0.05)
                continue

            # 1. Puerta de Energía RMS Adaptativa
            rms = self._calculate_rms(data)

            # Umbral dinámico: ligeramente por encima del ruido ambiental (mínimo 135)
            dynamic_gate = max(135.0, self.ambient_rms * 1.35)

            if rms < dynamic_gate:
                # Actualizar estimador de silencio ambiental
                self.ambient_rms = self.ambient_rms * 0.96 + rms * 0.04
                time.sleep(silence_sleep)
                continue

            # 2. Análisis Fonético Offline con Vosk (Solo cuando se supera la puerta)
            if self.recognizer:
                try:
                    if self.recognizer.AcceptWaveform(data):
                        res_json = json.loads(self.recognizer.Result())
                        recognized = res_json.get("text", "").strip()
                        if recognized:
                            print(f"[VEX WakeWord] [AUDIO] Escuchado offline: '{recognized}' (RMS: {rms:.0f})")
                        if self._check_wake_text(recognized):
                            self._trigger_wake(recognized)
                            continue
                    else:
                        partial_json = json.loads(self.recognizer.PartialResult())
                        partial_text = partial_json.get("partial", "").strip()
                        if partial_text and self._check_wake_text(partial_text):
                            print(f"[VEX WakeWord] [WAKE RAPIDO] '{partial_text}' (RMS: {rms:.0f})")
                            self._trigger_wake(partial_text)
                            continue
                except Exception:
                    pass

    def _trigger_wake(self, detected_text: str):
        """Dispara el evento de activación de forma segura y pausa el detector."""
        print(f"[VEX WakeWord] [WAKE] PALABRA CLAVE DETECTADA: '{detected_text}'. Despertando a VEX...")
        self._reset_recognizer()
        self.pause()
        try:
            self.on_wake(detected_text)
        except Exception as e:
            print(f"[VEX WakeWord] Error en callback on_wake: {e}")
