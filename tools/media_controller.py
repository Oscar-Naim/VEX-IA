"""
LYAXIS labs™ - Controlador Inteligente Multimedia y Streaming (Spotify & YouTube)
Búsqueda y reproducción automática de música con deep linking nativo y fallback web.
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


def _auto_play_spotify(query: str):
    """
    Automatización en segundo plano:
    Espera a que el cliente de Spotify cargue la consulta mediante el protocolo URI
    y envía la pulsación para iniciar de inmediato la reproducción del primer resultado.
    """
    time.sleep(1.8)
    if not (HAVE_PYAUTOGUI or HAVE_WIN32):
        return

    try:
        # 1. Localizar y enfocar la ventana de Spotify
        target_hwnd = None
        if HAVE_WIN32:
            def enum_handler(hwnd, _):
                nonlocal target_hwnd
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    cls = win32gui.GetClassName(hwnd)
                    if "spotify" in title or "spotify" in cls.lower():
                        target_hwnd = hwnd

            win32gui.EnumWindows(enum_handler, None)
            if target_hwnd:
                try:
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(target_hwnd)
                except Exception:
                    pass

        time.sleep(0.4)
        if HAVE_PYAUTOGUI:
            # En la vista de búsqueda abierta por URI, presionar Enter selecciona y reproduce el Top Result
            pyautogui.press("enter")
            time.sleep(0.3)
            pyautogui.press("enter")
    except Exception as e:
        print(f"[MediaController] Advertencia en auto-reproducción de Spotify: {e}")


def play_spotify(query: str) -> str:
    """
    Busca y reproduce un artista, canción o álbum en Spotify.

    1. Utiliza el protocolo URI nativo de Windows: spotify:search:"{encoded_query}"
    2. Si Spotify está instalado, abre la app y activa la reproducción del primer resultado.
    3. Si no está instalado, abre automáticamente la versión web en open.spotify.com.

    Args:
        query: Nombre de la canción, artista o álbum deseado.
    """
    clean_query = query.strip().strip('"\'')
    if not clean_query:
        return control_media("play_pause")

    encoded = urllib.parse.quote(clean_query)
    opened_desktop = False

    if sys.platform == "win32":
        try:
            # Deep linking nativo por protocolo URI
            uri = f"spotify:search:{encoded}"
            os.startfile(uri)
            opened_desktop = True
        except Exception:
            # Respaldo con comando start si el protocolo no responde directamente
            try:
                subprocess.Popen(f'start spotify:search:"{encoded}"', shell=True)
                opened_desktop = True
            except Exception:
                opened_desktop = False

    if opened_desktop:
        # Lanzar automatización de reproducción inmediata en hilo independiente
        threading.Thread(target=_auto_play_spotify, args=(clean_query,), daemon=True).start()
        return f"[✔ Spotify: Buscando y reproduciendo '{clean_query}']"
    else:
        # Fallback automático a Spotify Web en el navegador
        web_url = f"https://open.spotify.com/search/{encoded}"
        webbrowser.open(web_url)
        return f"[✔ Spotify Web: Abriendo búsqueda para '{clean_query}']"


def play_youtube(query: str) -> str:
    """
    Busca y reproduce contenido en YouTube o YouTube Music.
    Intenta resolver el enlace directo del primer video para reproducción inmediata;
    si no es posible, abre la búsqueda con los resultados.

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
        resp = requests.get(search_url, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            video_ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', resp.text)
            if video_ids:
                first_id = video_ids[0]
                watch_url = f"https://www.youtube.com/watch?v={first_id}"
                webbrowser.open(watch_url)
                direct_played = True
    except Exception:
        direct_played = False

    if not direct_played:
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
