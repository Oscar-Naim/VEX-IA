"""
LYAXIS labs™ - Controlador Inteligente Multimedia y Streaming (Spotify & YouTube)
Búsqueda y reproducción automática de música con deep linking nativo y fallback web.
Garantiza que la ventana principal de VEX permanezca siempre abierta y activa,
sin forzar jamás la minimización ni la transición al modo widget.
"""
import os
import sys
import time
import re
import urllib.parse
import webbrowser
import threading
import subprocess
import requests

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    HAVE_PYAUTOGUI = True
except ImportError:
    HAVE_PYAUTOGUI = False

try:
    import win32gui
    import win32con
    HAVE_WIN32 = True
except ImportError:
    HAVE_WIN32 = False

import ctypes

# Teclas virtuales para control multimedia nativo en Windows
VK_VOLUME_MUTE = 0xAD        # 173
VK_VOLUME_DOWN = 0xAE        # 174
VK_VOLUME_UP = 0xAF          # 175
VK_MEDIA_NEXT_TRACK = 0xB0   # 176
VK_MEDIA_PREV_TRACK = 0xB1   # 177
VK_MEDIA_PLAY_PAUSE = 0xB3   # 179
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_key_event(vk_code: int):
    """Envía un evento de tecla nativo hacia el sistema operativo."""
    if sys.platform == "win32":
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def is_spotify_installed() -> bool:
    """Verifica si el cliente de escritorio oficial de Spotify está instalado en Windows."""
    if sys.platform != "win32":
        return False
    possible_paths = [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\Spotify\Spotify.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Spotify\Spotify.exe"),
    ]
    return any(os.path.exists(p) for p in possible_paths)


def _press_enter_key():
    """Simula pulsación de tecla Enter a nivel de sistema operativo y pyautogui."""
    VK_RETURN = 0x0D
    if sys.platform == "win32":
        try:
            ctypes.windll.user32.keybd_event(VK_RETURN, 0, 0, 0)
            time.sleep(0.05)
            ctypes.windll.user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass
    if HAVE_PYAUTOGUI:
        try:
            pyautogui.press("enter")
        except Exception:
            pass


def _auto_play_spotify(query: str):
    """
    Automatización táctica de Spotify:
    1. Espera 1.2 segundos a que cargue la ventana de Spotify.
    2. Simula la pulsación de la tecla Enter para reproducir de inmediato el primer resultado.
    Nota: La ventana de VEX permanece intacta en segundo plano o lista para recibir comandos.
    """
    time.sleep(1.2)
    _press_enter_key()
    time.sleep(0.35)
    _press_enter_key()


DETACHED_PROCESS = 0x00000008  # Desacopla el subproceso de Windows
CREATE_NEW_PROCESS_GROUP = 0x00000200


def launch_application_safely(command_or_path: str) -> bool:
    """Lanza cualquier comando o URL sin bloquear ni arriesgar el proceso de VEX."""
    try:
        if sys.platform == "win32":
            subprocess.Popen(
                command_or_path,
                shell=True,
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                close_fds=True
            )
        else:
            subprocess.Popen(
                command_or_path,
                shell=True,
                close_fds=True
            )
        return True
    except Exception as e:
        print(f"[VEX Media] Error seguro al lanzar '{command_or_path}': {e}")
        return False


def play_spotify(query: str) -> str:
    """
    Busca y reproduce un artista, canción o álbum en Spotify activando auto-play.
    La ventana principal de VEX PERMANECE ABIERTA y con el campo de texto disponible.
    NUNCA fuerza el modo widget ni minimiza la ventana del asistente.

    Args:
        query: Nombre de la canción, artista o álbum deseado.
    """
    clean_query = query.strip().strip('"\'')
    if not clean_query:
        return control_media("play_pause")

    try:
        if sys.platform == "win32":
            # Ejecutar con lanzador desacoplado no bloqueante
            launched = launch_application_safely(f'start "" "spotify:search:{clean_query}"')
            if not launched:
                encoded = urllib.parse.quote(clean_query)
                launch_application_safely(f'start "" "https://open.spotify.com/search/{encoded}"')
        else:
            webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(clean_query)}")
    except Exception:
        webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(clean_query)}")

    threading.Thread(target=_auto_play_spotify, args=(clean_query,), daemon=True).start()
    return f"[✔ Spotify: Reproduciendo '{clean_query}']"


def play_youtube(query: str) -> str:
    """
    Busca y reproduce contenido en YouTube o YouTube Music.
    Intenta resolver el enlace directo del primer video para reproducción inmediata;
    si no es posible, abre la búsqueda con los resultados.
    La ventana principal de VEX PERMANECE ABIERTA y con el campo de texto disponible.

    Args:
        query: Término de búsqueda, artista o título del video.
    """
    clean_query = query.strip().strip('"\'')
    if not clean_query:
        return "Consulta vacía para YouTube."

    encoded = urllib.parse.quote_plus(clean_query)
    search_url = f"https://www.youtube.com/results?search_query={encoded}"

    # Intentar resolver el ID del primer video para reproducir de forma inmediata
    direct_played = False
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(search_url, headers=headers, timeout=3.0)
        if resp.status_code == 200:
            video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', resp.text)
            if video_ids:
                first_id = video_ids[0]
                watch_url = f"https://www.youtube.com/watch?v={first_id}"
                if sys.platform == "win32":
                    launch_application_safely(f'start "" "{watch_url}"')
                else:
                    webbrowser.open(watch_url)
                direct_played = True
    except Exception:
        direct_played = False

    if not direct_played:
        if sys.platform == "win32":
            launch_application_safely(f'start "" "{search_url}"')
        else:
            webbrowser.open(search_url)

    return f"[✔ YouTube: Buscando y reproduciendo '{clean_query}']"


def play_music(platform: str = "spotify", query: str = "") -> str:
    """
    Punto de entrada universal estilo Alexa para reproducir música en la plataforma elegida.

    Args:
        platform: Plataforma deseada ('spotify', 'youtube', 'yt').
        query: Nombre de la canción, artista o álbum.
    """
    plat = (platform or "spotify").lower().strip()
    if not query:
        return control_media("play_pause")

    if any(k in plat for k in ["youtube", "yt"]):
        return play_youtube(query)
    else:
        return play_spotify(query)


def control_media(action: str) -> str:
    """
    Controla el sistema multimedia y volumen del equipo.

    Args:
        action: Acción deseada ('volume_up', 'volume_down', 'mute', 'play_pause', 'next', 'prev').
    """
    act = action.lower().strip()

    if sys.platform != "win32":
        return f"Control de medios no soportado en plataforma {sys.platform}."

    if "up" in act or "subir" in act:
        for _ in range(5):
            _send_key_event(VK_VOLUME_UP)
        return "Volumen incrementado."
    elif "down" in act or "bajar" in act:
        for _ in range(5):
            _send_key_event(VK_VOLUME_DOWN)
        return "Volumen disminuido."
    elif "mute" in act or "silenciar" in act or "mutear" in act:
        _send_key_event(VK_VOLUME_MUTE)
        return "Estado de silencio alternado."
    elif "play" in act or "pause" in act or "pausar" in act or "reproducir" in act:
        _send_key_event(VK_MEDIA_PLAY_PAUSE)
        return "Reproducción pausada o reanudada."
    elif "next" in act or "siguiente" in act:
        _send_key_event(VK_MEDIA_NEXT_TRACK)
        return "Pista siguiente."
    elif "prev" in act or "anterior" in act:
        _send_key_event(VK_MEDIA_PREV_TRACK)
        return "Pista anterior."
    else:
        return f"Acción de control multimedia desconocida: '{action}'."
