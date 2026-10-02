"""
LYAXIS labs™ - Motor de Voz Neural VEX con Edge-TTS y Pygame
Generación de voz masculina ultra-realista (es-MX-JorgeNeural) en segundo plano
con sincronización milimétrica para el visor digital del robot (Robot Visor).
"""
import os
import sys
import time
import queue
import threading
import asyncio
import re

# Suprimir mensaje de bienvenida de pygame en consola
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import edge_tts

import config


class TextToSpeechEngine:
    def __init__(self, on_start=None, on_end=None, on_speaking_state=None):
        """
        Inicializa el motor de voz neural para VEX.

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
        self.temp_file = getattr(config, "TEMP_AUDIO_FILE", "temp_vex_voice.mp3")

        # Inicializar el mezclador de audio de pygame
        self._init_mixer()

        # Iniciar hilo en segundo plano para procesar la cola de voz sin trabar la UI
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
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

    async def _generate_audio_file(self, text: str, output_path: str):
        """Genera el archivo MP3 mediante edge-tts de forma asíncrona."""
        voice = getattr(config, "get_voice_id", lambda: self.voice)()
        communicate = edge_tts.Communicate(text, voice=voice, rate="+0%", pitch="+0Hz")
        await communicate.save(output_path)

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
        """Bucle consumidor que corre en hilo secundario."""
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

            try:
                # 1. Generar audio con Edge-TTS
                asyncio.run(self._generate_audio_file(text, self.temp_file))

                if not os.path.exists(self.temp_file):
                    self.queue.task_done()
                    continue

                # 2. Notificar inicio de habla (activa boca y animación en el visor)
                self._notify_speaking(True)

                # 3. Reproducir audio con pygame.mixer
                self._init_mixer()
                pygame.mixer.music.load(self.temp_file)
                pygame.mixer.music.play()

                # Esperar a que termine la reproducción o se ordene detener
                while pygame.mixer.music.get_busy() and self.is_running and self.is_speaking:
                    time.sleep(0.025)

            except Exception as e:
                print(f"[VEX TTS] Error en síntesis o reproducción: {e}")

            finally:
                # 4. Detener, liberar el archivo en Windows y notificar fin
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.music.unload()
                except Exception:
                    pass

                # Intentar limpiar archivo temporal
                try:
                    if os.path.exists(self.temp_file):
                        os.remove(self.temp_file)
                except Exception:
                    # En Windows se sobrescribirá en la siguiente orden
                    pass

                self._notify_speaking(False)
                self.queue.task_done()

    def speak(self, text: str):
        """Encola un texto para ser vocalizado por la voz masculina de VEX."""
        if text and text.strip():
            self.queue.put(text.strip())

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
