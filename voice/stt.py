"""
LYAXIS labs™ - Motor de Reconocimiento de Voz (STT) para VEX
Filtro estricto de ruido ambiental (umbral 3000), descarte de monosílabos/ruido (< 2 palabras),
y soporte para modo conversación continua manos libres.
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

        # UMBRAL FIJO DE ENERGÍA (2800 - 3200) para filtrar ventiladores y tecleo
        self.recognizer.energy_threshold = 3000
        self.recognizer.dynamic_energy_threshold = False

        # Detección de fin de habla por silencio
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.5

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
        self._current_thread = threading.Thread(target=self._capture_audio, daemon=True)
        self._current_thread.start()

    def stop_listening(self):
        """Solicita la detención inmediata de la escucha activa."""
        self._stop_requested = True
        self._is_listening = False

    def _capture_audio(self):
        """Captura audio con filtro estricto de duración y palabras mínimas."""
        if self.on_listening_start and not self._stop_requested:
            try:
                self.on_listening_start()
            except Exception as e:
                print(f"[VEX STT] Error en callback on_listening_start: {e}")

        try:
            with sr.Microphone() as source:
                if self._stop_requested:
                    return

                # Calibración rápida inicial
                self.recognizer.adjust_for_ambient_noise(source, duration=0.25)
                # Asegurar que el umbral no caiga por debajo de 2800 tras ajuste
                if self.recognizer.energy_threshold < 2800:
                    self.recognizer.energy_threshold = 3000

                if self._stop_requested:
                    return

                if self.on_speech_detected:
                    try:
                        self.on_speech_detected()
                    except Exception:
                        pass

                start_capture_time = time.time()
                audio = self.recognizer.listen(source, timeout=6.0, phrase_time_limit=12.0)
                capture_duration = time.time() - start_capture_time

            if self._stop_requested:
                return

            # FILTRO 1: Descartar sonidos ultracortos (< 0.8 segundos) como carraspeos o clics
            if capture_duration < 0.8:
                if self.on_timeout and not self._stop_requested:
                    self.on_timeout()
                return

            # Transcripción a texto usando Google Speech Recognition en español
            raw_text = self.recognizer.recognize_google(audio, language="es-ES")
            text = raw_text.strip()

            if self._stop_requested or not text:
                return

            # FILTRO 2: Descartar capturas con menos de 2 palabras ("eh", "um", ruidos aislados)
            words = text.split()
            if len(words) < 2:
                # Descarte silencioso sin escalar a Gemini ni mostrar error
                if self.on_timeout and not self._stop_requested:
                    self.on_timeout()
                return

            # Si pasa los filtros, entregar resultado
            if self.on_result and not self._stop_requested:
                self.on_result(text)

        except sr.WaitTimeoutError:
            if not self._stop_requested:
                if self.on_timeout:
                    self.on_timeout()
                elif self.on_error:
                    self.on_error("Tiempo de espera agotado. No se detectó audio.")
        except sr.UnknownValueError:
            if not self._stop_requested:
                if self.on_timeout:
                    self.on_timeout()
                elif self.on_error:
                    self.on_error("No se pudo interpretar el audio.")
        except sr.RequestError as e:
            if not self._stop_requested and self.on_error:
                self.on_error(f"Error de conexión con el servicio de voz: {e}")
        except Exception as e:
            if not self._stop_requested and self.on_error:
                self.on_error(f"Error en micrófono: {e}")
        finally:
            self._is_listening = False
