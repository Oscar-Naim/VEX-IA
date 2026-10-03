"""
LYAXIS labs™ - Motor de Voz Neural Híbrido VEX (Edge-TTS & ElevenLabs)
Generación de voz en segundo plano con dos niveles:
- Nivel 1: ElevenLabs (Voz Hiper-realista cinematográfica con API Key, modelo eleven_multilingual_v2).
- Nivel 2: edge-tts (Motor gratuito ilimitado por defecto con voz es-MX-JorgeNeural a +15% de velocidad).
Conmutación automática y transparente ante agotamiento de cuota o errores 401/429.
"""
import os
import sys
import time
import queue
import threading
import asyncio
import tempfile
import re
from typing import Optional

# Suprimir mensaje de bienvenida de pygame en consola
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import edge_tts

try:
    from elevenlabs.client import ElevenLabs
    HAVE_ELEVENLABS = True
except ImportError:
    HAVE_ELEVENLABS = False

import config


def safe_print(msg: str):
    """Imprime mensajes de forma segura evitando excepciones de codificación en consolas de Windows."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


# Voces masculinas tácticas recomendadas para ElevenLabs
ELEVENLABS_VOICES = {
    "George": "JBFqnCBsd6RMkjVDRZzb",   # Voz profunda, sobria y táctica
    "Adam": "pNInz6obpgDQGcFmaJgB",     # Voz neutra y natural
}
DEFAULT_ELEVENLABS_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


class TextToSpeechEngine:
    def __init__(self, on_start=None, on_end=None, on_speaking_state=None):
        """
        Inicializa el motor de voz neural híbrido para VEX.

        Args:
            on_start: Callback invocado cuando la voz comienza a sonar.
            on_end: Callback invocado cuando la voz finaliza.
            on_speaking_state: Callback invocado con booleano (True/False) indicando si habla.
        """
        self.on_start = on_start
        self.on_end = on_end
        self.on_speaking_state = on_speaking_state
        self.queue = queue.Queue()
        self.is_running = True
        self.is_speaking = False
        self.voice = getattr(config, "VEX_VOICE", "es-MX-JorgeNeural")

        # Inicializar el mezclador de audio de pygame
        self._init_mixer()

        # Iniciar hilo en segundo plano para procesar la cola de voz sin bloquear la UI
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="VEX-TTS-Worker")
        self.worker_thread.start()

    def _init_mixer(self):
        """Inicializa pygame.mixer con parámetros optimizados."""
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=2048)
        except Exception as e:
            print(f"[VEX TTS] Advertencia al inicializar mezclador de audio: {e}")

    def _clean_text(self, text: str) -> str:
        """Limpia el texto de caracteres de markdown y signos que entorpecen la síntesis auditiva."""
        cleaned = re.sub(r"[\*#`_~\[\]\(\)<>•–—]", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _generate_elevenlabs(self, text: str, output_path: str) -> bool:
        """
        Intenta generar el archivo de audio usando ElevenLabs API (Nivel 1).
        Retorna True si tuvo éxito, o False si falló (activando fallback transparente a edge-tts).
        """
        if not HAVE_ELEVENLABS:
            return False

        api_key = config.get_elevenlabs_api_key()
        if not api_key:
            return False

        try:
            # Obtener ID de voz (resolver alias como 'George' o 'Adam')
            raw_voice = config.get_elevenlabs_voice_id()
            voice_id = ELEVENLABS_VOICES.get(raw_voice, raw_voice) or DEFAULT_ELEVENLABS_VOICE_ID

            client = ElevenLabs(api_key=api_key)
            audio_stream = client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            with open(output_path, "wb") as f:
                for chunk in audio_stream:
                    if chunk:
                        f.write(chunk)

            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return True
            return False

        except Exception as e:
            err_str = str(e)
            if any(k in err_str.lower() for k in ["401", "429", "quota", "credits", "unauthorized"]):
                safe_print(f"[VEX TTS] [ElevenLabs] Cuota mensual agotada o error de autenticación ({err_str}).")
                safe_print(f"[VEX TTS] [Auto-Failover] Conmutando de forma automática y transparente a Edge-TTS...")
            else:
                safe_print(f"[VEX TTS] [ElevenLabs] Error en síntesis: {err_str}. Conmutando a Edge-TTS...")
            return False

    async def _generate_edge_tts(self, text: str, output_path: str):
        """
        Genera el archivo MP3 mediante edge-tts de forma asíncrona (Nivel 2 - Gratuito).
        Velocidad adaptativa configurada según el perfil activo del usuario (por defecto +15%).
        """
        voice = getattr(config, "get_voice_id", lambda: self.voice)()
        rate = "+15%"
        try:
            from memory.manager import get_memory_manager
            active = get_memory_manager().active_user
            if active and active.get("voice_speed"):
                rate = active["voice_speed"]
        except Exception:
            pass
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch="+0Hz")
        await communicate.save(output_path)

    async def _generate_audio_file(self, text: str, output_path: str):
        """
        Orquestador de síntesis de audio de dos niveles con conmutación por cuota.
        1. Si el motor configurado es 'elevenlabs' y hay API Key, intenta ElevenLabs.
        2. Si falla o el motor es 'edge-tts', utiliza edge-tts de forma transparente.
        """
        engine = config.get_tts_engine()
        has_eleven_key = bool(config.get_elevenlabs_api_key())

        if engine == "elevenlabs" and has_eleven_key:
            # Ejecutar llamada síncrona a ElevenLabs en hilo de trabajo
            success = self._generate_elevenlabs(text, output_path)
            if success:
                return

        # Fallback incondicional a edge-tts
        await self._generate_edge_tts(text, output_path)

    def _notify_speaking(self, speaking: bool):
        """Notifica los callbacks de cambio de estado de habla de forma segura."""
        self.is_speaking = speaking
        if self.on_speaking_state:
            try:
                self.on_speaking_state(speaking)
            except Exception as ex:
                print(f"[VEX TTS] Error en callback on_speaking_state: {ex}")

        if speaking and self.on_start:
            try:
                self.on_start()
            except Exception as ex:
                print(f"[VEX TTS] Error en callback on_start: {ex}")
        elif not speaking and self.on_end:
            try:
                self.on_end()
            except Exception as ex:
                print(f"[VEX TTS] Error en callback on_end: {ex}")

    def _worker_loop(self):
        """Bucle consumidor que corre en hilo secundario con bucle de eventos persistente."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while self.is_running:
                try:
                    raw_text = self.queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                if raw_text is None or not self.is_running:
                    break

                text = self._clean_text(raw_text)
                if not text:
                    self.queue.task_done()
                    continue

                temp_path = None
                try:
                    # Crear archivo temporal único para evitar bloqueos por descriptores de archivo en Windows
                    fd, temp_path = tempfile.mkstemp(prefix="vex_voice_", suffix=".mp3")
                    os.close(fd)

                    # 1. Generar audio (ElevenLabs o Edge-TTS con failover)
                    loop.run_until_complete(self._generate_audio_file(text, temp_path))

                    if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                        self.queue.task_done()
                        continue

                    # 2. Notificar inicio de habla (activa boca y animación en el visor)
                    self._notify_speaking(True)

                    # 3. Reproducir audio con pygame.mixer
                    self._init_mixer()
                    pygame.mixer.music.load(temp_path)
                    pygame.mixer.music.play()

                    # Esperar a que termine la reproducción o se ordene detener
                    while pygame.mixer.music.get_busy() and self.is_running and self.is_speaking:
                        time.sleep(0.025)

                except Exception as e:
                    print(f"[VEX TTS] Error en síntesis o reproducción: {e}")

                finally:
                    # 4. Detener, liberar el archivo en Windows con unload() y notificar fin
                    try:
                        if pygame.mixer.get_init():
                            pygame.mixer.music.stop()
                            pygame.mixer.music.unload()
                    except Exception:
                        pass

                    # Limpiar archivo temporal único de forma segura
                    if temp_path:
                        try:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                        except Exception:
                            pass

                    self._notify_speaking(False)
                    self.queue.task_done()
        finally:
            try:
                loop.close()
            except Exception:
                pass

    def speak(self, text: str):
        """Encola un texto para ser vocalizado por la voz masculina de VEX."""
        if text and text.strip():
            self.queue.put(text.strip())

    def speak_async(self, text: str):
        """Vocaliza de forma asíncrona a través de la cola de audio sin bloquear el hilo llamador."""
        self.speak(text)

    def stop(self):
        """Detiene la reproducción activa inmediatamente y limpia la cola."""
        with self.queue.mutex:
            self.queue.queue.clear()

        self._notify_speaking(False)
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass

    def shutdown(self):
        """Cierra el motor de voz y sus hilos de forma segura."""
        self.is_running = False
        self.stop()
        self.queue.put(None)
