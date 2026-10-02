"""
LYAXIS labs™ - Herramientas Nativas de Control de Sistema
Implementación de acciones ejecutadas por Function Calling de Gemini.
"""
import os
import sys
import re
import shutil
import ctypes
import datetime
import urllib.parse
import webbrowser
import subprocess
import psutil


# Virtual Key Codes para control multimedia nativo en Windows
VK_VOLUME_MUTE = 0xAD        # 173
VK_VOLUME_DOWN = 0xAE        # 174
VK_VOLUME_UP = 0xAF          # 175
VK_MEDIA_NEXT_TRACK = 0xB0   # 176
VK_MEDIA_PREV_TRACK = 0xB1   # 177
VK_MEDIA_PLAY_PAUSE = 0xB3   # 179
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_key_event(vk_code: int):
    """Envía un evento de tecla hacia el sistema operativo."""
    if sys.platform == "win32":
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def search_youtube(query: str) -> str:
    """
    Abre el navegador web y busca directamente un video, canción o contenido en YouTube.

    Args:
        query: Término de búsqueda, artista o título del video.
    """
    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    webbrowser.open(url)
    return f"Búsqueda en YouTube ejecutada para: '{clean_query}'"


def open_url(url: str) -> str:
    """
    Abre cualquier dirección web o página de Internet solicitada en el navegador predeterminado.

    Args:
        url: Dirección web o dominio (ej. 'google.com', 'https://github.com').
    """
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url
    webbrowser.open(clean_url)
    return f"Navegador abierto en la URL: {clean_url}"


def launch_application(app_name: str) -> str:
    """
    Abre una aplicación instalada en la computadora (Spotify, Discord, Calculadora, Navegador, etc.).
    IMPORTANTE: Si el usuario te pide abrir el Bloc de Notas y escribir, anotar o redactar texto,
    NO uses esta función; usa la herramienta especializada 'write_note'.

    Args:
        app_name: Nombre de la aplicación a ejecutar.
    """
    raw_name = (app_name or "").strip()
    # Sanitización estricta: Rechazar inyección de comandos en shell
    if any(ch in raw_name for ch in ["&", "|", ";", ">", "<", "`", "$", "\n", "\r"]):
        return f"Error de seguridad: Nombre de aplicación contiene caracteres inválidos: '{raw_name}'"

    name_lower = raw_name.lower().strip()

    # Mapeo seguro de aplicaciones comunes en Windows
    app_mapping = {
        "spotify": "spotify:",
        "discord": "discord:",
        "bloc de notas": "notepad.exe",
        "notepad": "notepad.exe",
        "calculadora": "calc.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "navegador": "https://www.google.com",
        "browser": "https://www.google.com",
        "chrome": "chrome.exe",
        "edge": "msedge.exe",
        "explorador": "explorer.exe",
        "archivos": "explorer.exe",
        "terminal": "powershell.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "vscode": "code",
        "visual studio code": "code",
        "administrador de tareas": "taskmgr.exe",
        "task manager": "taskmgr.exe",
        "configuracion": "ms-settings:",
        "ajustes": "ms-settings:",
        "settings": "ms-settings:",
        "alarma": "ms-clock:",
        "alarmas": "ms-clock:",
        "reloj": "ms-clock:",
        "temporizador": "ms-clock:",
        "cronometro": "ms-clock:"
    }

    target = app_mapping.get(name_lower, name_lower)

    try:
        if sys.platform == "win32":
            # Protocolos o URLs de Windows se abren de forma nativa y segura con os.startfile
            if target.startswith(("http://", "https://")) or target.endswith(":"):
                os.startfile(target)
                return f"Aplicación o protocolo '{app_name}' iniciado correctamente."

            # Ejecutar binario sin shell=True
            executable = shutil.which(target) or target
            subprocess.Popen([executable], shell=False)
        else:
            executable = shutil.which(target) or target
            subprocess.Popen([executable], shell=False)
        return f"Aplicación '{app_name}' iniciada correctamente."
    except Exception as e:
        return f"No se pudo iniciar la aplicación '{app_name}'. Detalle: {e}"


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
        # Subir 5 pasos (10%)
        for _ in range(5):
            _send_key_event(VK_VOLUME_UP)
        return "Volumen incrementado."
    elif "down" in act or "bajar" in act:
        # Bajar 5 pasos (10%)
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
        return "Pista siguiente reproducida."
    elif "prev" in act or "anterior" in act:
        _send_key_event(VK_MEDIA_PREV_TRACK)
        return "Pista anterior reproducida."
    else:
        return f"Acción de control multimedia '{action}' no reconocida. Opciones: volume_up, volume_down, mute, play_pause, next, prev."


def system_info() -> str:
    """
    Reporta el estado actual del sistema: fecha, hora exacta, nivel de batería, uso de CPU y memoria RAM.
    """
    now = datetime.datetime.now()
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

    dia_semana = dias[now.weekday()]
    mes_nombre = meses[now.month - 1]
    hora_str = now.strftime("%H:%M")
    fecha_str = f"{dia_semana}, {now.day} de {mes_nombre} de {now.year}"

    # Estado de la Batería
    battery = psutil.sensors_battery()
    if battery:
        porcentaje_bat = f"{int(battery.percent)}%"
        estado_carga = "conectado y cargando" if battery.power_plugged else "operando con batería"
        bat_info = f"Batería al {porcentaje_bat} ({estado_carga})"
    else:
        bat_info = "Alimentación por corriente alterna (PC de escritorio)"

    # Rendimiento
    cpu_usage = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory()
    ram_usage = ram.percent

    reporte = (
        f"Diagnóstico de Sistema LYAXIS labs™:\n"
        f"• Tiempo: {hora_str} ({fecha_str})\n"
        f"• Energía: {bat_info}\n"
        f"• Rendimiento: CPU al {cpu_usage:.0f}%, RAM al {ram_usage:.0f}% en uso."
    )
    return reporte


def write_note(content: str, title: str = "Nota_VEX") -> str:
    """
    Crea, redacta y abre una nota de texto en el Bloc de Notas (Notepad) de Windows con el contenido especificado.
    Úsala SIEMPRE que el usuario te pida escribir, anotar, apuntar, redactar o guardar algo en el bloc de notas,
    o cuando pida crear una nota rápida.

    Args:
        content: El texto o mensaje completo que debe redactarse y quedar escrito dentro de la nota.
        title: Título o nombre temático del archivo de nota (opcional, ej. 'Nota_Oscar', 'Lista_Compras').
    """
    clean_content = (content or "").strip()
    if not clean_content:
        clean_content = "Nota creada por el asistente táctico VEX // LYAXIS labs™"

    try:
        user_profile = os.environ.get("USERPROFILE", "")
        onedrive_desktop = os.path.join(user_profile, "OneDrive", "Desktop")
        std_desktop = os.path.join(os.path.expanduser("~"), "Desktop")

        if os.path.isdir(onedrive_desktop):
            desktop_path = onedrive_desktop
        elif os.path.isdir(std_desktop):
            desktop_path = std_desktop
        else:
            desktop_path = os.getcwd()

        clean_title = re.sub(r'[\\/*?:"<>|]', "", title or "Nota_VEX").strip().replace(" ", "_")
        if not clean_title:
            clean_title = "Nota_VEX"

        file_path = os.path.join(desktop_path, f"{clean_title}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(clean_content + "\n")

        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])

        return f"Nota '{clean_title}.txt' redactada con éxito y abierta en el Bloc de notas."
    except Exception as e:
        return f"Error al redactar y abrir la nota: {e}"


# Diccionario con el catálogo de herramientas mapeadas para Gemini
AVAILABLE_TOOLS = {
    "search_youtube": search_youtube,
    "open_url": open_url,
    "launch_application": launch_application,
    "control_media": control_media,
    "system_info": system_info,
    "write_note": write_note,
}

