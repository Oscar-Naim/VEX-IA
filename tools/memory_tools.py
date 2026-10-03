"""
LYAXIS labs™ - Herramientas de Memoria Persistente para el Agente (tools/memory_tools.py)
Expuestas a Google Gemini y Groq Cloud mediante Tool Calling / Function Calling nativo.
Permite a VEX registrar tareas con fechas y horas reales, rutinas y aprender hechos sobre la marcha.
"""
import re
import datetime
from typing import Optional, List, Dict
from memory.manager import get_memory_manager


def clean_task_title(title: str) -> str:
    """Elimina palabras de relleno ('recuérdame que', 'anota que', 'ponme una tarea para') y limpia el título."""
    s = (title or "").strip()
    fillers = [
        r"^(?:por\s+favor\s+)?(?:puedes\s+)?(?:recuerdame\s+que|recuérdame\s+que|recuerda\s+que|recuérdame|recuerdame|acuerdame\s+que|acuérdame\s+que)\s*",
        r"^(?:por\s+favor\s+)?(?:puedes\s+)?(?:anota\s+que|anota|anotame\s+que|anótame\s+que|apunta\s+que|apunta|apuntame\s+que|apúntame\s+que)\s*",
        r"^(?:por\s+favor\s+)?(?:puedes\s+)?(?:ponme\s+una\s+tarea\s+(?:para|de|que)?|pon\s+una\s+tarea\s+(?:para|de|que)?|crea\s+una\s+tarea\s+(?:para|de|que)?|agrega\s+una\s+tarea\s+(?:para|de|que)?|agenda\s+(?:una\s+tarea\s+)?(?:para|de|que)?)\s*",
        r"^(?:tengo\s+que\s+acordarme\s+de|no\s+olvidar\s+que|no\s+olvides\s+que|recordar\s+que)\s*",
        r"^(?:el\s+\d{1,2}\s+de\s+[a-záéíóú]+(?:\s+de\s+\d{4})?\s+)?(?:para\s+el\s+\d{1,2}\s+de\s+[a-záéíóú]+(?:\s+de\s+\d{4})?\s+)?",
        r"^(?:para\s+mañana|para\s+manana|mañana|manana|para\s+hoy|hoy)\s*",
        r"^(?:que\s+|de\s+)",
    ]
    for pat in fillers:
        s = re.sub(pat, "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"^(?:que\s+|de\s+)", "", s, flags=re.IGNORECASE).strip()
    if s:
        s = s[0].upper() + s[1:]
    return s or "Nueva tarea"


def normalize_task_date(date_str: str) -> str:
    """Normaliza cualquier expresión de fecha a formato estricto YYYY-MM-DD."""
    today = datetime.date.today()
    if not date_str:
        return today.strftime("%Y-%m-%d")

    s = str(date_str).lower().strip()
    if s in ["hoy", "today"]:
        return today.strftime("%Y-%m-%d")
    if s in ["mañana", "manana", "tomorrow"]:
        return (today + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if s in ["pasado mañana", "pasado manana"]:
        return (today + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    # Formato ISO ya existente YYYY-MM-DD
    m_iso = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", s)
    if m_iso:
        y, m, d = int(m_iso.group(1)), int(m_iso.group(2)), int(m_iso.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    # Formato DD/MM/YYYY o DD-MM-YYYY
    m_slash = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", s)
    if m_slash:
        d, m, y = int(m_slash.group(1)), int(m_slash.group(2)), int(m_slash.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    # Texto en español: 'el 5 de octubre', '5 de octubre', '5 de octubre de 2026'
    months = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
        "noviembre": 11, "diciembre": 12
    }
    m_text = re.search(r"(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de\s+(\d{4}))?", s)
    if m_text:
        day = int(m_text.group(1))
        month_name = m_text.group(2).lower()
        year = int(m_text.group(3)) if m_text.group(3) else today.year
        if month_name in months:
            month_num = months[month_name]
            try:
                dt = datetime.date(year, month_num, day)
                if not m_text.group(3) and dt < today:
                    dt = datetime.date(year + 1, month_num, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return today.strftime("%Y-%m-%d")


def normalize_task_time(time_str: str) -> str:
    """Normaliza la hora a formato militar HH:MM (24h). Por defecto 10:00."""
    if not time_str:
        return "10:00"

    s = str(time_str).lower().strip()
    m_clock = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|de\s+la\s+tarde|de\s+la\s+manana|de\s+la\s+noche)?", s)
    if m_clock:
        h = int(m_clock.group(1))
        m = int(m_clock.group(2)) if m_clock.group(2) else 0
        period = m_clock.group(3) or ""
        if any(p in period for p in ["pm", "tarde", "noche"]):
            if h < 12:
                h += 12
        elif any(p in period for p in ["am", "manana"]):
            if h == 12:
                h = 0
        elif 1 <= h <= 6 and datetime.datetime.now().hour >= 11:
            h += 12
        return f"{h:02d}:{m:02d}"

    return "10:00"


def format_friendly_date(date_str: str) -> str:
    """Convierte YYYY-MM-DD en texto amigable en español para la confirmación de voz de VEX."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.date.today()
        if dt == today:
            return "hoy"
        if dt == today + datetime.timedelta(days=1):
            return "mañana"
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        return f"el {dt.day} de {months[dt.month - 1]}"
    except Exception:
        return f"el {date_str}"


def format_badge_date(date_str: str) -> str:
    """Genera el texto de badge visual para la interfaz: '📅 05 Oct 2026'."""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        months_short = [
            "Ene", "Feb", "Mar", "Abr", "May", "Jun",
            "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
        ]
        return f"📅 {dt.day:02d} {months_short[dt.month - 1]} {dt.year}"
    except Exception:
        return f"📅 {date_str}"


def crear_tarea(titulo: str, fecha: str = "", hora: str = "") -> str:
    """
    titulo: Descripción limpia de la tarea (ej: 'Tengo que salir' o 'Revisar coche', SIN palabras de relleno como 'recuérdame que').
    fecha: Formato YYYY-MM-DD. Si el usuario dice 'el 5 de octubre', calcular la fecha exacta respecto al año actual. Si dice 'mañana', calcular fecha de mañana.
    hora: Formato HH:MM (24h). Si el usuario no especifica hora, asignar una hora prudente (ej: '09:00' o la hora de la tarde solicitada).
    """
    clean_title = clean_task_title(titulo)
    target_date = normalize_task_date(fecha)
    target_time = normalize_task_time(hora)

    mem = get_memory_manager()
    user_name = mem.get_active_user_name()
    new_task = mem.add_task(title=clean_title, date=target_date, time=target_time)

    friendly_date = format_friendly_date(target_date)
    time_spoken = f" a las {target_time}" if target_time else ""

    # Registro en el sistema y confirmación por voz
    # Formato de fecha para el registro visual: DD/MM/YYYY
    try:
        date_obj = datetime.datetime.strptime(target_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d/%m/%Y")
    except Exception:
        date_display = target_date

    print(f"[VEX Memory] ✔ Tarea Guardada: '{clean_title}' para el {date_display} a las {target_time}")

    return f"Anotado, {user_name}: tienes programado '{clean_title}' para {friendly_date}{time_spoken}."


def add_user_task(title: str = "", date: str = "", time: str = "", titulo: str = "", fecha: str = "", hora: str = "") -> str:
    """Alias compatible con add_user_task que redirige a crear_tarea."""
    t = titulo or title
    d = fecha or date
    h = hora or time
    return crear_tarea(titulo=t, fecha=d, hora=h)


def set_user_routine(name: str, description: str, time: str = "08:00") -> str:
    """
    Registra o actualiza una rutina habitual del usuario (ej. rutina matutina, rutina de estudio).
    Usa esta herramienta cuando el usuario explique lo que suele o quiere hacer como hábito diario.

    Args:
        name: Nombre identificador de la rutina (ej. 'Rutina matutina', 'Rutina de ejercicio').
        description: Acciones o detalles que componen la rutina.
        time: Hora aproximada de la rutina (ej. '08:00', '18:00').
    """
    clean_name = (name or "").strip()
    clean_desc = (description or "").strip()
    if not clean_name:
        return "Error: Debes proporcionar un nombre para la rutina."

    mem = get_memory_manager()
    routine = mem.set_routine(clean_name, clean_desc, time=time)
    r_time = routine.get("time", "08:00")
    return f"[✔ RUTINA GUARDADA] Rutina '{clean_name}' registrada a las {r_time}: {clean_desc}."


def remember_fact(key: str, value: str) -> str:
    """
    Memoriza de forma permanente un dato, preferencia o hecho relevante sobre el usuario.
    Usa esta función cuando el usuario diga 'recuerda que mi comida favorita es...',
    'anota que uso Google Chrome', 'mi canción preferida es...', etc.

    Args:
        key: Concepto, categoría o etiqueta del dato (ej. 'preferencia_musica', 'lenguaje_favorito', 'color_favorito').
        value: La preferencia, dato o valor que debe recordarse.
    """
    clean_key = (key or "").strip()
    clean_val = (value or "").strip()
    if not clean_key or not clean_val:
        return "Error: Se requiere una clave y un valor para memorizar el dato."

    mem = get_memory_manager()
    mem.remember_fact(clean_key, clean_val)
    readable = clean_key.replace("_", " ").capitalize()
    return f"[✔ MEMORIA ACTUALIZADA] He memorizado que tu {readable} es '{clean_val}'."


def list_user_tasks(date: str = "", date_filter: str = "") -> str:
    """
    Consulta y reporta las tareas pendientes del usuario activo.
    Usa esta función cuando el usuario pregunte '¿qué pendientes tengo hoy?', 'mis tareas',
    '¿qué tengo que hacer?', '¿tengo tareas pendientes?'.

    Args:
        date: Filtro de fecha ('hoy', 'today', 'all', o formato 'YYYY-MM-DD').
        date_filter: Alias opcional para el filtro de fecha.
    """
    filter_val = date or date_filter or ""
    mem = get_memory_manager()
    tasks = mem.list_tasks(include_completed=False, for_date=filter_val or None)

    if not tasks:
        filtro_str = f" para {filter_val}" if filter_val and filter_val not in ("all", "todas") else ""
        return f"No tienes tareas pendientes registradas{filtro_str} en tu perfil de VEX."

    lines = [f"📋 Tareas pendientes encontradas ({len(tasks)}):"]
    for i, t in enumerate(tasks, 1):
        t_time = f" a las {t.get('time')}" if t.get("time") else ""
        badge_d = format_badge_date(t.get("date", ""))
        lines.append(f"{i}. [{badge_d}{t_time}] {t.get('title')}")

    return "\n".join(lines)


def complete_user_task(title_or_id: str = "", task_id_or_title: str = "") -> str:
    """
    Marca una tarea pendiente como completada.
    Usa esta función cuando el usuario indique 'ya terminé la tarea...', 'marca como completada la tarea de...', 'completa la segunda tarea'.

    Args:
        title_or_id: Título, posición ordinal (ej. 'primera', 'segunda', '2') o identificador de la tarea concluida.
        task_id_or_title: Alias para el título o ID de la tarea.
    """
    clean = (title_or_id or task_id_or_title or "").strip()
    mem = get_memory_manager()
    user_name = mem.get_active_user_name()
    pending = mem.list_tasks(include_completed=False)

    if not pending:
        return f"No tienes ninguna tarea pendiente por ahora, {user_name}."

    idx = mem.parse_task_index(clean)
    if idx is not None:
        ordinal_map = {1: "Primera", 2: "Segunda", 3: "Tercera", 4: "Cuarta", 5: "Quinta", -1: "Última"}
        ord_label = ordinal_map.get(idx, f"Tarea #{idx}")
        completed_task = mem.complete_task_by_index(idx)
        if completed_task:
            t_title = completed_task.get("title", "Tarea")
            return f"[✔ TAREA CONCLUIDA] {ord_label} tarea completada: '{t_title}', {user_name}. ¡Excelente trabajo!"
        else:
            return f"Solo tienes {len(pending)} tarea{'s' if len(pending) != 1 else ''} en tu lista, {user_name}."

    if not clean:
        if len(pending) == 1:
            t = pending[0]
            mem.complete_task(t["id"])
            return f"[✔ TAREA CONCLUIDA] Tarea completada: '{t.get('title')}', {user_name}. ¡Excelente trabajo!"
        return f"Tienes {len(pending)} tareas pendientes. ¿Cuál de ellas deseas completar, {user_name}?"

    success = mem.complete_task(clean)
    if success:
        return f"[✔ TAREA CONCLUIDA] Tarea completada: '{clean}', {user_name}. ¡Excelente trabajo!"
    else:
        return f"No encontré ninguna tarea pendiente que coincida con '{clean}', {user_name}."


# Alias de retrocompatibilidad
marcar_tarea_completada = complete_user_task
completar_tarea = complete_user_task


def delete_user_task(title_or_id: str = "", task_id_or_title: str = "") -> str:
    """
    Elimina una tarea de la lista del usuario activo.
    Usa esta función cuando el usuario indique 'elimina la tarea...', 'borra el pendiente de...', 'eliminar la segunda tarea'.

    Args:
        title_or_id: Título, posición ordinal (ej. 'primera', 'segunda', '2') o identificador de la tarea a eliminar.
        task_id_or_title: Alias para el título o ID de la tarea.
    """
    clean = (title_or_id or task_id_or_title or "").strip()
    mem = get_memory_manager()
    user_name = mem.get_active_user_name()
    pending = mem.list_tasks(include_completed=False)
    all_tasks = mem.list_tasks(include_completed=True)
    tasks_pool = pending if pending else all_tasks

    if not tasks_pool:
        return f"No tienes ninguna tarea programada por ahora, {user_name}."

    idx = mem.parse_task_index(clean)
    if idx is not None:
        ordinal_map = {1: "Primera", 2: "Segunda", 3: "Tercera", 4: "Cuarta", 5: "Quinta", -1: "Última"}
        ord_label = ordinal_map.get(idx, f"Tarea #{idx}")
        deleted_task = mem.delete_task_by_index(idx, include_completed=not bool(pending))
        if deleted_task:
            t_title = deleted_task.get("title", "Tarea")
            return f"[✔ TAREA ELIMINADA] {ord_label} tarea eliminada: '{t_title}', {user_name}."
        else:
            return f"Solo tienes {len(tasks_pool)} tarea{'s' if len(tasks_pool) != 1 else ''} en tu lista, {user_name}."

    if not clean:
        if len(tasks_pool) == 1:
            t = tasks_pool[0]
            mem.delete_task(t["id"])
            return f"[✔ TAREA ELIMINADA] He eliminado la tarea '{t.get('title')}' de tu lista, {user_name}."
        return f"Tienes {len(tasks_pool)} tareas en tu lista. ¿Cuál de ellas deseas eliminar, {user_name}?"

    target_id = None
    target_title = clean
    for t in tasks_pool:
        if t.get("id") == clean or clean.lower() in t.get("title", "").lower() or t.get("title", "").lower() in clean.lower():
            target_id = t.get("id")
            target_title = t.get("title", clean)
            break

    if target_id and mem.delete_task(target_id):
        return f"[✔ TAREA ELIMINADA] He eliminado la tarea '{target_title}' de tu lista, {user_name}."
    return f"No encontré ninguna tarea que coincida con '{clean}' para eliminar, {user_name}."


MEMORY_TOOLS = {
    "crear_tarea": crear_tarea,
    "add_user_task": add_user_task,
    "set_user_routine": set_user_routine,
    "remember_fact": remember_fact,
    "list_user_tasks": list_user_tasks,
    "complete_user_task": complete_user_task,
    "delete_user_task": delete_user_task,
}

__all__ = [
    "clean_task_title",
    "normalize_task_date",
    "normalize_task_time",
    "format_friendly_date",
    "format_badge_date",
    "crear_tarea",
    "add_user_task",
    "set_user_routine",
    "remember_fact",
    "list_user_tasks",
    "complete_user_task",
    "delete_user_task",
    "MEMORY_TOOLS",
]
