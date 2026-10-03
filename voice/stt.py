"""
LYAXIS labs™ - Motor de Reconocimiento de Voz (STT) para VEX
Captura adaptativa de audio con SpeechRecognition, ajuste automático al ruido ambiental,
prevención de ejecuciones concurrentes con threading.Lock, reseteo estricto de buffers
y filtro anti-duplicación para erradicar repeticiones de frases.
"""
import time
import threading
import speech_recognition as sr
from voice.ducking import AudioDucker


class SpeechToTextListener:
    def __init__(
        self,
        on_listening_start=None,
        on_speech_detected=None,
        on_result=None,
        on_error=None,
        on_timeout=None
    ):
        self.on_listening_start = on_listening_start
        self.on_speech_detected = on_speech_detected
        self.on_result = on_result
        self.on_error = on_error
        self.on_timeout = on_timeout

        self.recognizer = sr.Recognizer()

        # Ajuste dinámico de energía adaptado al entorno del usuario
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.energy_threshold = 100  # Umbral inicial sensible y balanceado

        # Calibración anti-cortes: pausas naturales de respiración o reflexión sin cortar a media frase
        self.recognizer.pause_threshold = 1.8         # Esperar 1.8 segundos de silencio real antes de cerrar la frase
        self.recognizer.non_speaking_duration = 0.8  # Margen de silencio
        self.recognizer.phrase_time_limit = 20       # Permitir frases de hasta 20 segundos de duración

        # Candado y flags para garantizar exclusión mutua estricta
        self._lock = threading.Lock()
        self._is_listening = False
        self._current_thread = None
        self._stop_requested = False

        # Filtro de deduplicación de buffer
        self._last_delivered_text = ""
        self._last_delivered_time = 0.0

    @property
    def is_listening(self) -> bool:
        with self._lock:
            return self._is_listening

    def start_listening_async(self):
        """Inicia la captura de audio en un hilo independiente garantizando exclusión mutua."""
        with self._lock:
            if self._is_listening:
                print("[VEX STT] Escucha ya en progreso. Rechazando hilo concurrente.")
                return

            self._stop_requested = False
            self._is_listening = True
            self._current_thread = threading.Thread(
                target=self._capture_audio,
                daemon=True,
                name="VEX-STT-Worker"
            )
            self._current_thread.start()

    def stop_listening(self):
        """Solicita la detención inmediata de la escucha activa."""
        with self._lock:
            self._stop_requested = True
            self._is_listening = False

    def _capture_audio(self):
        """Captura audio del micrófono y realiza el reconocimiento con reseteo de buffer."""
        if self.on_listening_start and not self._stop_requested:
            try:
                self.on_listening_start()
            except Exception as e:
                print(f"[VEX STT] Error en callback on_listening_start: {e}")

        transcript = ""
        try:
            with sr.Microphone() as source:
                if self._stop_requested:
                    return

                # Calibración de ruido de fondo adaptativo
                self.recognizer.adjust_for_ambient_noise(source, duration=0.20)
                self.recognizer.energy_threshold = max(70.0, min(self.recognizer.energy_threshold, 350.0))
                self.recognizer.pause_threshold = 1.8
                self.recognizer.non_speaking_duration = 0.8
                print(f"[VEX STT] [MIC] Micrófono activo (umbral: {self.recognizer.energy_threshold:.1f}, pausa: 1.8s). Esperando orden...")

                if self._stop_requested:
                    return

                if self.on_speech_detected:
                    try:
                        self.on_speech_detected()
                    except Exception:
                        pass

                # Captura la frase del usuario
                audio = self.recognizer.listen(source, timeout=8.0, phrase_time_limit=20.0)

            if self._stop_requested:
                return

            print("[VEX STT] [AUDIO] Capturado. Transcribiendo...")

            # Transcripción a texto usando Google Speech Recognition
            raw_text = ""
            try:
                raw_text = self.recognizer.recognize_google(audio, language="es-MX")
            except sr.UnknownValueError:
                try:
                    raw_text = self.recognizer.recognize_google(audio, language="es-ES")
                except Exception:
                    raw_text = ""

            transcript = raw_text.strip()
            if self._stop_requested:
                transcript = ""
                return

            if not transcript:
                print("[VEX STT] No se detectó ninguna palabra clara.")
                if self.on_timeout and not self._stop_requested:
                    self.on_timeout()
                return

            # Filtro anti-duplicación temporal: ignora si es idéntica en menos de 2.0s
            now = time.time()
            if transcript == self._last_delivered_text and (now - self._last_delivered_time) < 2.0:
                print(f"[VEX STT] Filtro activo: descartando frase duplicada en < 2.0s: '{transcript}'")
                transcript = ""
                return

            self._last_delivered_text = transcript
            self._last_delivered_time = now

            print(f"[VEX STT] [OK] Orden vocalizada reconocida: '{transcript}'")

            # Entregar resultado al orquestador y vaciar inmediatamente variable de buffer
            delivered_text = transcript
            transcript = ""

            if self.on_result and not self._stop_requested:
                self.on_result(delivered_text)

        except sr.WaitTimeoutError:
            print("[VEX STT] Tiempo de espera agotado (silencio en la habitación).")
            if not self._stop_requested:
                if self.on_timeout:
                    self.on_timeout()
                elif self.on_error:
                    self.on_error("Tiempo de espera agotado.")
        except sr.UnknownValueError:
            print("[VEX STT] No se pudo interpretar el audio.")
            if not self._stop_requested:
                if self.on_timeout:
                    self.on_timeout()
                elif self.on_error:
                    self.on_error("No se pudo interpretar el audio.")
        except sr.RequestError as e:
            print(f"[VEX STT] Error de conexión: {e}")
            if not self._stop_requested and self.on_error:
                self.on_error(f"Error de conexión con el servicio de voz: {e}")
        except Exception as e:
            print(f"[VEX STT] Error en micrófono: {e}")
            if not self._stop_requested and self.on_error:
                self.on_error(f"Error en micrófono: {e}")
        finally:
            transcript = ""
            AudioDucker.restore()
            with self._lock:
                self._is_listening = False
