"""
LYAXIS labs™ - Motor de Reconocimiento de Voz (STT) para VEX
Captura adaptativa de audio con SpeechRecognition, ajuste automático al ruido ambiental,
y soporte para comandos breves y conversación natural.
"""
import time
import threading
import speech_recognition as sr


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
        self.recognizer.energy_threshold = 250  # Umbral inicial sensible

        # Detección de fin de habla por silencio natural
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.4

        self._is_listening = False
        self._current_thread = None
        self._stop_requested = False

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def start_listening_async(self):
        """Inicia la captura de audio en un hilo independiente."""
        if self._is_listening:
            return

        self._stop_requested = False
        self._is_listening = True
        self._current_thread = threading.Thread(target=self._capture_audio, daemon=True, name="VEX-STT-Worker")
        self._current_thread.start()

    def stop_listening(self):
        """Solicita la detención inmediata de la escucha activa."""
        self._stop_requested = True
        self._is_listening = False

    def _capture_audio(self):
        """Captura audio del micrófono y realiza el reconocimiento."""
        if self.on_listening_start and not self._stop_requested:
            try:
                self.on_listening_start()
            except Exception as e:
                print(f"[VEX STT] Error en callback on_listening_start: {e}")

        try:
            with sr.Microphone() as source:
                if self._stop_requested:
                    return

                # Calibración rápida de ruido de fondo (0.3s)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                print(f"[VEX STT] [MIC] Microfono activo (umbral de energia: {self.recognizer.energy_threshold:.1f}). Esperando orden...")

                if self._stop_requested:
                    return

                if self.on_speech_detected:
                    try:
                        self.on_speech_detected()
                    except Exception:
                        pass

                # Captura la frase del usuario
                audio = self.recognizer.listen(source, timeout=6.0, phrase_time_limit=10.0)

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

            text = raw_text.strip()
            if self._stop_requested:
                return

            if not text:
                print("[VEX STT] No se detecto ninguna palabra clara.")
                if self.on_timeout and not self._stop_requested:
                    self.on_timeout()
                return

            print(f"[VEX STT] [OK] Orden vocalizada reconocida: '{text}'")

            # Entregar resultado al orquestador
            if self.on_result and not self._stop_requested:
                self.on_result(text)

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
            self._is_listening = False
