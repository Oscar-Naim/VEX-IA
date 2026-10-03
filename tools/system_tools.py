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


DETACHED_PROCESS = 0x00000008  # Bandera de Windows para desacoplar proceso
CREATE_NEW_PROCESS_GROUP = 0x00000200


def launch_application_safely(command_or_path: str) -> bool:
    """
    Lanza cualquier aplicación o comando externo en un subproceso completamente independiente
    y desacoplado de Windows (DETACHED_PROCESS), garantizando que el ciclo de vida del programa
    abierto no interfiera, bloquee ni destruya jamás el proceso o la ventana de VEX.
    """
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
        print(f"[VEX Safe Launcher] Error seguro al lanzar '{command_or_path}': {e}")
        return False


def search_youtube(query: str) -> str:
    """
    Abre el navegador web y busca directamente un video, canción o contenido en YouTube.

    Args:
        query: Término de búsqueda, artista o título del video.
    """
    clean_query = query.strip()
    encoded = urllib.parse.quote_plus(clean_query)
    url = f"https://www.youtube.com/results?search_query={encoded}"
    try:
        if sys.platform == "win32":
            launch_application_safely(f'start "" "{url}"')
        else:
            webbrowser.open(url)
        return f"Búsqueda en YouTube ejecutada para: '{clean_query}'"
    except Exception as e:
        return f"Error seguro al buscar en YouTube: {e}"


def open_url(url: str) -> str:
    """
    Abre cualquier dirección web o página de Internet solicitada en el navegador predeterminado.

    Args:
        url: Dirección web o dominio (ej. 'google.com', 'https://github.com').
    """
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
        clean_url = "https://" + clean_url
    try:
        if sys.platform == "win32":
            launch_application_safely(f'start "" "{clean_url}"')
        else:
            webbrowser.open(clean_url)
        return f"Navegador abierto en la URL: {clean_url}"
    except Exception as e:
        return f"Error seguro al abrir enlace: {e}"


def launch_application(app_name: str) -> str:
    """
    Abre una aplicación instalada en la computadora (Spotify, Discord, Calculadora, Word, Navegador, etc.).
    IMPORTANTE: Si el usuario te pide abrir el Bloc de Notas y escribir, anotar o redactar texto,
    usa la herramienta especializada 'write_note'.

    Args:
        app_name: Nombre de la aplicación a ejecutar.
    """
    raw_name = (app_name or "").strip()
    # Sanitización estricta: Rechazar inyección de comandos en shell
    if any(ch in raw_name for ch in ["&", "|", ";", ">", "<", "`", "$", "\n", "\r"]):
        return f"Error de seguridad: Nombre de aplicación contiene caracteres inválidos: '{raw_name}'"

    name_lower = raw_name.lower().strip()

    # Mapeo universal y robusto de aplicaciones comunes en Windows
    app_mapping = {
        "spotify": 'start "" "spotify:"',
        "discord": 'start "" "discord:"',
        "bloc de notas": "notepad.exe",
        "notepad": "notepad.exe",
        "calculadora": "calc.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "word": 'start "" winword',
        "microsoft word": 'start "" winword',
        "excel": 'start "" excel',
        "microsoft excel": 'start "" excel',
        "powerpoint": 'start "" powerpnt',
        "navegador": 'start "" "https://www.google.com"',
        "browser": 'start "" "https://www.google.com"',
        "chrome": 'start "" chrome',
        "google chrome": 'start "" chrome',
        "edge": 'start "" msedge',
        "microsoft edge": 'start "" msedge',
        "firefox": 'start "" firefox',
        "explorador": "explorer.exe",
        "archivos": "explorer.exe",
        "terminal": "start cmd.exe",
        "cmd": "start cmd.exe",
        "powershell": "start powershell.exe",
        "vscode": 'start "" code',
        "visual studio code": 'start "" code',
        "code": 'start "" code',
        "administrador de tareas": "taskmgr.exe",
        "task manager": "taskmgr.exe",
        "configuracion": 'start "" "ms-settings:"',
        "ajustes": 'start "" "ms-settings:"',
        "settings": 'start "" "ms-settings:"',
        "alarma": 'start "" "ms-clock:"',
        "alarmas": 'start "" "ms-clock:"',
        "reloj": 'start "" "ms-clock:"',
        "temporizador": 'start "" "ms-clock:"',
        "cronometro": 'start "" "ms-clock:"'
    }

    cmd = app_mapping.get(name_lower)
    if not cmd:
        import shutil
        is_known_uri = any(raw_name.startswith(p) for p in ["http://", "https://", "ms-", "mailto:", "spotify:"])
        is_executable = (
            os.path.exists(raw_name) or
            shutil.which(raw_name) is not None or
            shutil.which(raw_name + ".exe") is not None or
            is_known_uri
        )
        if not is_executable:
            possible_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), raw_name),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), raw_name),
                os.path.join(os.environ.get("LocalAppData", ""), "Programs", raw_name)
            ]
            found = False
            for p in possible_paths:
                if os.path.exists(p) or os.path.exists(p + ".exe"):
                    found = True
                    raw_name = p
                    break
            if not found:
                try:
                    from memory.manager import get_memory_manager
                    active_u = get_memory_manager().active_user
                    user_name = active_u.get("display_name", "Oscar") if active_u else "Oscar"
                except Exception:
                    user_name = "Oscar"
                return f"No pude encontrar esa aplicación en tu sistema, {user_name}."

        if sys.platform == "win32":
            cmd = f'start "" "{raw_name}"'
        else:
            cmd = raw_name

    try:
        success = launch_application_safely(cmd)
        if success:
            return f"Aplicación '{app_name}' iniciada correctamente."
        else:
            try:
                from memory.manager import get_memory_manager
                active_u = get_memory_manager().active_user
                user_name = active_u.get("display_name", "Oscar") if active_u else "Oscar"
            except Exception:
                user_name = "Oscar"
            return f"No pude encontrar esa aplicación en tu sistema, {user_name}."
    except Exception:
        try:
            from memory.manager import get_memory_manager
            active_u = get_memory_manager().active_user
            user_name = active_u.get("display_name", "Oscar") if active_u else "Oscar"
        except Exception:
            user_name = "Oscar"
        return f"No pude encontrar esa aplicación en tu sistema, {user_name}."


from tools.media_controller import (
    play_spotify,
    play_youtube,
    play_music,
    control_media
)


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
            launch_application_safely(f'notepad.exe "{file_path}"')
        else:
            launch_application_safely(f'xdg-open "{file_path}"')

        return f"Nota '{clean_title}.txt' redactada con éxito y abierta en el Bloc de notas."
    except Exception as e:
        return f"Error al redactar y abrir la nota: {e}"


# Diccionario con el catálogo de herramientas mapeadas para Gemini
AVAILABLE_TOOLS = {
    "play_music": play_music,
    "play_spotify": play_spotify,
    "play_youtube": play_youtube,
    "search_youtube": search_youtube,
    "open_url": open_url,
    "launch_application": launch_application,
    "control_media": control_media,
    "system_info": system_info,
    "write_note": write_note,
}

