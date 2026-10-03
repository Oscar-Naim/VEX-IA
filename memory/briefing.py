"""
LYAXIS labs™ - Generador de Briefing Táctico Proactivo de Bienvenida (memory/briefing.py)
Determina el saludo según la hora (buenos días / tardes / noches), consulta las tareas
pendientes del día y rutinas activas, y vocaliza un informe conciso al iniciar VEX.
"""
import datetime
from typing import Optional, Callable

from memory.manager import get_memory_manager


def get_time_greeting() -> str:
    """Devuelve el saludo correspondiente al tramo horario del día."""
    current_hour = datetime.datetime.now().hour
    if 5 <= current_hour < 12:
        return "Buenos días"
    elif 12 <= current_hour < 19:
        return "Buenas tardes"
    else:
        return "Buenas noches"


def _format_time_12h(time_str: str) -> str:
    """Formatea '16:00' o '16:30' a formato audible amigable '4:00 PM'."""
    clean = time_str.strip()
    try:
        parts = clean.split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{m:02d} {ampm}" if m > 0 else f"{h12} {ampm}"
    except Exception:
        return clean


def generate_briefing_text(user_name: Optional[str] = None) -> str:
    """
    Construye el texto del briefing proactivo en estilo copiloto táctico de VEX.
    Ejemplo:
    'Buenos días, Alexis. Sistemas en línea. Recuerdo que tienes 1 tarea pendiente para hoy:
    Entregar avance de software a las 4:00 PM. Tu rutina matutina está lista. ¿Qué orden ejecutamos?'
    """
    mem = get_memory_manager()
    name = user_name or mem.get_active_user_name() or "Operador"
    greeting = get_time_greeting()

    # Consultar tareas pendientes para hoy
    pending_tasks = mem.list_tasks(include_completed=False, for_date="hoy")
    task_count = len(pending_tasks)

    # Consultar rutinas activas
    routines = mem.list_routines()
    routine_mention = ""
    if routines:
        first_routine = routines[0]
        routine_name = first_routine.get("name", "rutina")
        routine_mention = f"Tu {routine_name.lower()} está lista. "

    if task_count == 1:
        task = pending_tasks[0]
        title = task.get("title", "Tarea programada")
        raw_time = task.get("time", "")
        time_part = f" a las {_format_time_12h(raw_time)}" if raw_time else ""
        return (
            f"{greeting}, {name}. Sistemas en línea. "
            f"Recuerdo que tienes 1 tarea pendiente para hoy: {title}{time_part}. "
            f"{routine_mention}¿Qué orden ejecutamos?"
        )
    elif task_count > 1:
        first_task = pending_tasks[0]
        title = first_task.get("title", "")
        raw_time = first_task.get("time", "")
        time_part = f" a las {_format_time_12h(raw_time)}" if raw_time else ""
        return (
            f"{greeting}, {name}. Sistemas tácticos en línea. "
            f"Tienes {task_count} tareas pendientes para hoy, la primera es: {title}{time_part}. "
            f"{routine_mention}¿Qué orden ejecutamos?"
        )
    else:
        return (
            f"{greeting}, {name}. Sistemas en línea. "
            f"No tienes tareas pendientes para hoy. ¿En qué te colaboro?"
        )



def play_proactive_briefing(main_window, speak_audio: bool = True):
    """
    Dispara la presentación visual y vocalización del briefing proactivo en la ventana principal.
    - Publica la tarjeta del briefing en el chat.
    - Pone al visor en expresión alegre (happy).
    - Vocaliza la bienvenida con edge-tts y sincroniza la boca en tiempo real.
    """
    briefing = generate_briefing_text()

    try:
        # Publicar tarjeta en el feed de chat
        main_window._add_message_card("agent", briefing)
        main_window._set_hud_state("idle")

        # Expresión facial alegre de bienvenida
        if hasattr(main_window, "visor_canvas") and main_window.visor_canvas:
            main_window.visor_canvas.set_expression("happy", duration=4.5)

        # Sincronización con mini-widget flotante si existe
        if hasattr(main_window, "floating_widget") and main_window.floating_widget:
            main_window.floating_widget.set_expression("happy", duration=4.5)

        # Vocalización en modo anuncio (from_voice=False para no abrir el micrófono accidentalmente)
        if speak_audio and hasattr(main_window, "voice_mgr") and main_window.voice_mgr:
            main_window.voice_mgr.speak(briefing, from_voice=False)
        elif hasattr(main_window, "voice_mgr") and main_window.voice_mgr:
            main_window.voice_mgr.register_spoken_text(briefing, from_voice=False)

    except Exception as e:
        print(f"[Briefing] Error al reproducir briefing proactivo: {e}")
