"""
LYAXIS labs™ - Orquestador del Asistente de Voz VEX (Voice Manager)
Gestiona la máquina de estados completa del ciclo de vida inteligente:
STANDBY -> WAKE -> LISTENING -> THINKING -> SPEAKING -> FOLLOW_UP -> STANDBY
Incluye síntesis de tonos cibernéticos (chimes de activación y descanso),
ventana de seguimiento de 4 segundos y control del micrófono sin colisiones.
"""
import re
import math
import struct
import time
import threading
from typing import Callable, Optional, List, Tuple
from enum import Enum
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from voice.wakeword import WakeWordDetector
from voice.stt import SpeechToTextListener
from voice.tts import TextToSpeechEngine


class AssistantState(str, Enum):
    STANDBY = "standby"         # Reposo monitoreando wake word
    WAKE = "wake"               # Activación instantánea (chime y ojos abiertos)
    LISTENING = "listening"     # Escuchando orden activa (ventana de 5-6s)
    THINKING = "thinking"       # Procesando enrutador o Gemini
    SPEAKING = "speaking"       # Transmitiendo respuesta por voz y boca animada
    FOLLOW_UP = "follow_up"     # Ventana de 4s para repreguntas sin decir 'VEX'


class CyberChimes:
    """Generador en memoria de tonos cibernéticos para activación y descanso."""
    _wake_sound: Optional[pygame.mixer.Sound] = None
    _sleep_sound: Optional[pygame.mixer.Sound] = None

    @classmethod
    def _generate_pcm_tone(cls, f1: float, f2: float, duration_ms: int = 180, sample_rate: int = 24000) -> bytes:
        """Sintetiza una ráfaga tonal exponencial suave de frecuencia f1 a f2."""
        n_samples = int(sample_rate * (duration_ms / 1000.0))
        buf = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            progress = i / n_samples
            freq = f1 + (f2 - f1) * progress
            decay = math.exp(-3.5 * progress)
            val = int(decay * 16000 * math.sin(2 * math.pi * freq * t))
            buf.extend(struct.pack("<h", max(-32767, min(32767, val))))
        return bytes(buf)

    @classmethod
    def get_wake_sound(cls) -> Optional[pygame.mixer.Sound]:
        """Tono ascendente de activación (880Hz -> 1320Hz, limpio y futurista)."""
        if cls._wake_sound is None:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=1024)
                pcm = cls._generate_pcm_tone(880, 1320, 180)
                cls._wake_sound = pygame.mixer.Sound(buffer=pcm)
                cls._wake_sound.set_volume(0.65)
            except Exception:
                return None
        return cls._wake_sound

    @classmethod
    def get_sleep_sound(cls) -> Optional[pygame.mixer.Sound]:
        """Tono descendente suave de reposo (660Hz -> 440Hz, sutil)."""
        if cls._sleep_sound is None:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=1024)
                pcm = cls._generate_pcm_tone(660, 440, 220)
                cls._sleep_sound = pygame.mixer.Sound(buffer=pcm)
                cls._sleep_sound.set_volume(0.50)
            except Exception:
                return None
        return cls._sleep_sound

    @classmethod
    def play_wake(cls):
        snd = cls.get_wake_sound()
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    @classmethod
    def play_sleep(cls):
        snd = cls.get_sleep_sound()
        if snd:
            try:
                snd.play()
            except Exception:
                pass


class VoiceAssistantManager:
    """
    Orquestador principal del ciclo de vida inteligente de VEX.
    Coordina la transición fluida entre Standby, Wake Word, Escucha,
    Inferencia, Respuesta y Ventana de Seguimiento (Follow-up).
    """

    def __init__(
        self,
        on_state_change: Callable[[AssistantState], None],
        on_user_command: Callable[[str], None],
        on_wake_flash: Optional[Callable[[], None]] = None
    ):
        """
        Inicializa el orquestador de voz de VEX.

        Args:
            on_state_change: Notifica cambios de estado a la interfaz (Standby, Listening, etc.).
            on_user_command: Callback cuando el usuario termina de hablar y se procesa el texto.
            on_wake_flash: Notifica el efecto de brillo neón instantáneo en el visor.
        """
        self.on_state_change = on_state_change
        self.on_user_command = on_user_command
        self.on_wake_flash = on_wake_flash

        self.current_state = AssistantState.STANDBY
        self.hands_free_mode = False
        self.is_voice_session = False
        self._recent_spoken_texts: List[Tuple[str, float]] = []
        self._follow_up_timer: Optional[threading.Timer] = None

        # 1. Motor de Palabra de Activación (100% Offline)
        self.wake_detector = WakeWordDetector(
            on_wake=self._handle_wake_word_detected
        )

        # 2. Motor de Reconocimiento de Órdenes (STT)
        self.stt = SpeechToTextListener(
            on_listening_start=self._on_stt_listening_start,
            on_speech_detected=self._on_stt_speech_detected,
            on_result=self._on_stt_result,
            on_error=self._on_stt_error,
            on_timeout=self._on_stt_timeout
        )

        # 3. Motor de Síntesis Vocal (Edge-TTS)
        self.tts = TextToSpeechEngine(
            on_start=self._on_tts_start,
            on_end=self._on_tts_end
        )

    @property
    def state(self) -> AssistantState:
        return self.current_state

    def set_hands_free_mode(self, enabled: bool):
        """Habilita o deshabilita el bucle de charla continua permanente."""
        self.hands_free_mode = enabled

    def start(self):
        """Inicia el sistema situando a VEX en modo Standby a la espera de su nombre."""
        self._cancel_follow_up_timer()
        self.is_voice_session = False
        self.set_state(AssistantState.STANDBY)
        self.wake_detector.start()

    def set_state(self, new_state: AssistantState):
        """Actualiza el estado interno y notifica a la interfaz gráfica."""
        self.current_state = new_state
        try:
            self.on_state_change(new_state)
        except Exception as e:
            print(f"[VEX Manager] Error en callback de estado: {e}")

    @staticmethod
    def _clean_normalize(text: str) -> str:
        """Normaliza texto eliminando acentos y signos para comparaciones acústicas."""
        s = text.lower().strip()
        replacements = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
        for a, b in replacements:
            s = s.replace(a, b)
        return re.sub(r"[^\w\s]", "", s).strip()

    def _is_echo_of_speech(self, norm_rec: str, norm_spoken: str) -> bool:
        """Detecta si lo reconocido por el micrófono es el eco de los altavoces de VEX."""
        if not norm_rec or not norm_spoken:
            return False
        # Coincidencia directa de subcadena (ej. "darme una orden" dentro de "...para darme una orden")
        if norm_rec in norm_spoken:
            return True
        # Coincidencia si la mayoría de las palabras reconocidas estaban en lo hablado por VEX
        rec_words = [w for w in norm_rec.split() if len(w) > 2]
        spoken_words = set(norm_spoken.split())
        if rec_words and len(rec_words) <= 6:
            matches = sum(1 for w in rec_words if w in spoken_words)
            if matches / len(rec_words) >= 0.65:
                return True
        return False

    def register_spoken_text(self, text: str, from_voice: bool = False):
        """Registra el texto vocalizado por VEX para evitar eco acústico y definir el modo de sesión."""
        if text and text.strip():
            self._recent_spoken_texts.append((text.strip(), time.time()))
        self.is_voice_session = from_voice

    def speak(self, text: str, from_voice: bool = False):
        """Vocaliza una respuesta asegurando el registro anti-eco y el origen de la orden."""
        self.register_spoken_text(text, from_voice=from_voice)
        self.tts.speak(text)

    # ================= 1. EVENTO WAKE WORD (¡VEX!) =================

    def _handle_wake_word_detected(self, keyword_heard: str):
        """Invocado en cuanto el detector offline escucha 'VEX' en la habitación."""
        self._cancel_follow_up_timer()
        self.is_voice_session = True

        # 1. Notificar efecto de luz y sonido cibernético
        if self.on_wake_flash:
            try:
                self.on_wake_flash()
            except Exception:
                pass

        # 2. Reproducir chime de activación
        CyberChimes.play_wake()

        # 3. Transicionar a estado WAKE y de inmediato a LISTENING
        self.set_state(AssistantState.WAKE)

        # Pausa breve de 250ms para que termine el chime antes de abrir el micrófono
        def start_listening():
            time.sleep(0.22)
            self.set_state(AssistantState.LISTENING)
            self.stt.start_listening_async()

        threading.Thread(target=start_listening, daemon=True).start()

    # ================= 2. EVENTOS DE CAPTURA DE ORDEN (STT) =================

    def _on_stt_listening_start(self):
        """El micrófono está grabando la orden del usuario."""
        if self.current_state != AssistantState.LISTENING:
            self.set_state(AssistantState.LISTENING)

    def _on_stt_speech_detected(self):
        """Se detectó la primera modulación de voz en la ventana de escucha."""
        pass

    def _on_stt_result(self, recognized_text: str):
        """Texto reconocido exitosamente tras superar los filtros acústicos."""
        self._cancel_follow_up_timer()

        # Limpiar texto de invocaciones residuales al inicio
        clean = recognized_text.strip()
        norm_rec = self._clean_normalize(clean)

        # 1. Filtro Anti-Eco: Verificar si el micrófono captó los propios altavoces de VEX
        now = time.time()
        self._recent_spoken_texts = [(t, ts) for (t, ts) in self._recent_spoken_texts if now - ts < 15.0]

        for (spoken_text, _) in self._recent_spoken_texts:
            norm_spoken = self._clean_normalize(spoken_text)
            if self._is_echo_of_speech(norm_rec, norm_spoken):
                print(f"[VEX Manager] 🔇 Eco acústico descartado (VEX escuchó sus propios altavoces: '{clean}')")
                self.is_voice_session = False
                self._go_to_sleep()
                return

        # 2. Transicionar a THINKING
        self.set_state(AssistantState.THINKING)

        # 3. Notificar orden al manejador principal
        try:
            self.on_user_command(clean)
        except Exception as e:
            print(f"[VEX Manager] Error al procesar comando: {e}")

    def _on_stt_timeout(self):
        """El usuario no habló dentro de la ventana de escucha de 5-6 segundos."""
        if self.hands_free_mode:
            # En modo charla continua forzado, reintentar escucha
            self.set_state(AssistantState.LISTENING)
            self.stt.start_listening_async()
            return

        self.is_voice_session = False
        self._go_to_sleep()

    def _on_stt_error(self, err_message: str):
        """Ocurrió un error en el reconocimiento de voz."""
        self.is_voice_session = False
        if self.current_state in [AssistantState.LISTENING, AssistantState.FOLLOW_UP]:
            self._go_to_sleep()

    # ================= 3. EVENTOS DE HABLA (TTS) =================

    def _on_tts_start(self):
        """VEX comienza a vocalizar la respuesta."""
        self._cancel_follow_up_timer()
        self.set_state(AssistantState.SPEAKING)

    def _on_tts_end(self):
        """VEX terminó de vocalizar la respuesta."""
        # Solo abrir ventana de seguimiento si la sesión provino de voz o estamos en modo manos libres
        if (self.is_voice_session or self.hands_free_mode) and self.current_state == AssistantState.SPEAKING:
            self._enter_follow_up_window()
        else:
            self.is_voice_session = False
            self._go_to_sleep()

    # ================= 4. VENTANA DE SEGUIMIENTO (FOLLOW-UP) Y REPOSO =================

    def _enter_follow_up_window(self):
        """Mantiene el micrófono abierto 4 segundos para conversación fluida sin repetir 'VEX'."""
        self.set_state(AssistantState.FOLLOW_UP)

        def follow_up_task():
            # Pausa de transición acústica para que la reverberación de los altavoces cese por completo
            time.sleep(1.2)
            if self.current_state == AssistantState.FOLLOW_UP and not self.tts.is_speaking:
                self.stt.start_listening_async()

        threading.Thread(target=follow_up_task, daemon=True).start()

    def _go_to_sleep(self):
        """Regresa ordenadamente al modo Standby emitiendo el tono de descanso."""
        self._cancel_follow_up_timer()
        self.is_voice_session = False
        self.stt.stop_listening()

        # Reproducir sonido suave de descanso
        CyberChimes.play_sleep()

        self.set_state(AssistantState.STANDBY)

        # Reanudar detector de palabra clave tras liberar micrófono
        def resume_wake():
            time.sleep(0.4)
            if self.current_state == AssistantState.STANDBY:
                self.wake_detector.resume()

        threading.Thread(target=resume_wake, daemon=True).start()

    def _cancel_follow_up_timer(self):
        """Cancela temporizadores activos de seguimiento."""
        if self._follow_up_timer:
            try:
                self._follow_up_timer.cancel()
            except Exception:
                pass
            self._follow_up_timer = None

    def trigger_manual_listen(self):
        """Activa manualmente el micrófono al hacer clic en el botón '+ VOZ'."""
        self._cancel_follow_up_timer()
        self.is_voice_session = True
        self.wake_detector.pause()
        self.tts.stop()

        if self.current_state == AssistantState.LISTENING:
            self._go_to_sleep()
        else:
            CyberChimes.play_wake()
            self.set_state(AssistantState.LISTENING)
            self.stt.start_listening_async()

    def emergency_stop(self):
        """Detiene toda actividad vocal, interrumpe el habla y duerme al asistente (Esc)."""
        self._cancel_follow_up_timer()
        self.tts.stop()
        self.stt.stop_listening()
        self._go_to_sleep()

    def shutdown(self):
        """Cierre completo y limpio de todos los hilos y mezcladores de audio."""
        self._cancel_follow_up_timer()
        self.wake_detector.stop()
        self.stt.stop_listening()
        self.tts.shutdown()
