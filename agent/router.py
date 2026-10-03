"""
LYAXIS labs™ - Enrutador Táctico Local (Capa 0: Zero-Token Intent Engine)
Intercepta órdenes directas de sistema, medios, aplicaciones e información local
ejecutándolas inmediatamente en < 10ms a coste 0 tokens de API.
Incluye enriquecimiento contextual con expresiones visuales e iconos de pantalla
para el visor robótico de VEX (EMO / Vector).
"""
import re
import datetime
from dataclasses import dataclass
from typing import Optional
import psutil

from tools.system_tools import (
    search_youtube,
    open_url,
    launch_application,
    control_media,
    system_info,
    write_note
)
from tools.media_controller import (
    play_music,
    play_spotify,
    play_youtube
)
from tools.memory_tools import list_user_tasks
from memory.manager import get_memory_manager


@dataclass
class LocalRouteResult:
    handled: bool
    action_name: str = ""
    execution_result: str = ""
    spoken_response: str = ""
    expression: str = "idle"
    icon: Optional[str] = None
    icon_duration: float = 3.0


class LocalIntentRouter:
    """Enrutador de intención local para comandos deterministas (Capa 0)."""

    @staticmethod
    def _normalize(text: str) -> str:
        """Normaliza el texto eliminando puntuación y acentos para coincidencia robusta."""
        s = text.lower().strip()
        # Eliminar invocaciones iniciales al asistente
        s = re.sub(r"^(vex|oye vex|oye vez|oye ves|hey vex|ey vex|hola vex|ok vex|buenas vex|despierta|asistente)\s*[,.:;]?\s*", "", s).strip()
        # Normalizar acentos
        replacements = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
        for a, b in replacements:
            s = s.replace(a, b)
        # Limpiar signos
        s = re.sub(r"[^\w\s]", "", s).strip()
        return s

    @classmethod
    def _is_task_query(cls, norm: str) -> bool:
        """
        RAMA 1: Evalúa si la frase es una pregunta o solicitud de consulta de tareas/pendientes.
        Frases clave: 'cuál era', 'cuáles son', 'qué tareas', 'qué pendientes',
        'dime mis tareas', 'mis tareas', 'qué tengo que hacer', 'tengo alguna tarea', etc.
        """
        query_patterns = [
            r"\b(?:cual|cuales)\s+(?:era|eran|es|son)\b",
            r"\bque\s+(?:tareas?|pendientes?)\b",
            r"\bque\s+tengo\s+que\s+hacer\b",
            r"\bque\s+tengo\s+pendiente\b",
            r"\b(?:dime|muestrame|muestra|ver|revisa|revisar|consultar|checa|checar|listar?)\s+(?:mis\s+|las\s+|los\s+)?(?:tareas?|pendientes?)\b",
            r"\b(?:mis\s+tareas|mis\s+pendientes|tareas\s+pendientes|lista\s+de\s+tareas)\b",
            r"\b(?:tengo|tienes|hay)\s+(?:alguna\s+|algun\s+|algo\s+)?(?:tareas?|pendientes?)\b",
        ]
        if any(re.search(p, norm, re.IGNORECASE) for p in query_patterns):
            if any(k in norm for k in ["tarea", "tareas", "pendiente", "pendientes", "hacer"]):
                return True
        return False

    @classmethod
    def _parse_task_index(cls, text: str) -> Optional[int]:
        """Extrae el índice numérico o término ordinal de una referencia a tarea (1-based, o -1 para última)."""
        norm_t = text.lower().strip()
        norm_t = re.sub(r"^(?:a|la|el|las|los|mi|mis|de)\s+", "", norm_t).strip()
        if re.search(r"\b(primera|primero|primer|1a|1ra|1ro|uno)\b", norm_t):
            return 1
        if re.search(r"\b(segunda|segundo|2a|2da|2do|dos)\b", norm_t):
            return 2
        if re.search(r"\b(tercera|tercero|tercer|3a|3ra|3ro|tres)\b", norm_t):
            return 3
        if re.search(r"\b(cuarta|cuarto|4a|4ta|4to|cuatro)\b", norm_t):
            return 4
        if re.search(r"\b(quinta|quinto|5a|5ta|5to|cinco)\b", norm_t):
            return 5
        if re.search(r"\b(sexta|sexto|6a|6to|seis)\b", norm_t):
            return 6
        if re.search(r"\b(ultima|última|ultimo|último)\b", norm_t):
            return -1
        m = re.search(r"\b(?:numero\s+|num\s+|#)?(\d+)\b", norm_t)
        if m:
            return int(m.group(1))
        return None

    @classmethod
    def _extract_task_modification_intent(cls, norm: str):
        """
        RAMA 3: Detecta intenciones de completar o eliminar tareas existentes.
        Frases clave: 'completa la tarea', 'ya hice la tarea', 'elimina la tarea', 'borra la tarea', 'eliminar la segunda tarea'.
        Retorna ('complete', target_info) o ('delete', target_info) o None.
        target_info es un dict: {'index': int or None, 'title': str, 'raw': str}
        """
        # Completar
        complete_pat = r"\b(?:completa(?:r|me)?|termina(?:r|me)?|ya\s+hice|ya\s+termine|marca(?:r)?\s+(?:como\s+)?(?:completada?|hecha))\s+(.*)$"
        m_comp = re.search(complete_pat, norm, re.IGNORECASE)
        if m_comp:
            raw = m_comp.group(1).strip()
            idx = cls._parse_task_index(raw)
            clean_title = re.sub(r"^(?:la\s+tarea|el\s+pendiente|mi\s+tarea|las\s+tareas|los\s+pendientes|tarea|pendiente)\s*(?:de|para|que|llamada|titulada)?\s*", "", raw, flags=re.IGNORECASE).strip()
            clean_title = re.sub(r"^(?:de|para|que|llamada|titulada)\s+", "", clean_title, flags=re.IGNORECASE).strip()
            return ("complete", {"index": idx, "title": clean_title, "raw": raw})

        # Eliminar / Borrar
        delete_pat = r"\b(?:elimina(?:r|me)?|borra(?:r|me)?|quita(?:r|me)?)\s+(.*)$"
        m_del = re.search(delete_pat, norm, re.IGNORECASE)
        if m_del:
            raw = m_del.group(1).strip()
            idx = cls._parse_task_index(raw)
            clean_title = re.sub(r"^(?:la\s+tarea|el\s+pendiente|mi\s+tarea|las\s+tareas|los\s+pendientes|tarea|pendiente)\s*(?:de|para|que|llamada|titulada)?\s*", "", raw, flags=re.IGNORECASE).strip()
            clean_title = re.sub(r"^(?:de|para|que|llamada|titulada)\s+", "", clean_title, flags=re.IGNORECASE).strip()
            return ("delete", {"index": idx, "title": clean_title, "raw": raw})

        return None

    @classmethod
    def _extract_task_intent(cls, norm: str, raw_prompt: str, user_name: str = "Oscar"):
        """
        RAMA 2: Analiza y extrae intenciones de creación o programación de tareas y recordatorios.
        Requiere verbos explícitos de acción (crea, ponme, agrega, anota, programa, recuérdame).
        Rechaza categóricamente cualquier pregunta, consulta o modificación.
        """
        # 1. Filtro estricto: Si es una consulta o modificación, NUNCA crea tarea
        if cls._is_task_query(norm) or cls._extract_task_modification_intent(norm):
            return None

        # 2. Descartar inicios con pronombres o interrogativos (cuál, qué, cómo, etc.)
        if re.search(r"^(?:cual|cuales|que|quien|donde|cuando|por\s+que|como)\b", norm):
            return None

        # 3. Solo entra si contiene verbos explícitos de creación / programación
        create_verbs_regex = re.compile(
            r"\b("
            r"crea(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"pon(me|te)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"agrega(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"anota(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"anota(r|me)?\s+(?:que\s+)?|"
            r"apunta(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"apunta(r|me)?\s+(?:que\s+)?|"
            r"programa(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"recuerda(me)?|"
            r"recuérdame|"
            r"acuerda(me)?|"
            r"agenda(r|me)?\s+(?:una\s+|la\s+)?(?:tarea|recordatorio)|"
            r"agenda(r|me)?"
            r")\b",
            re.IGNORECASE
        )
        if not create_verbs_regex.search(norm):
            return None

        now = datetime.datetime.now()
        target_dt = now
        target_date = now.strftime("%Y-%m-%d")
        time_str = ""
        s = norm

        # 1. Chequeo de fecha (mañana / hoy)
        if re.search(r"\b(para\s+manana|manana)\b", s):
            target_date = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            s = re.sub(r"\b(para\s+manana|manana)\b", " ", s)

        # 2. Tiempos relativos (dentro de media hora, en 15 minutos, etc.)
        m_rel = re.search(
            r"\b(?:para\s+)?(?:dentro\s+de|en)\s+(media\s+hora|un\s+cuarto\s+de\s+hora|tres\s+cuartos\s+de\s+hora|una\s+hora(?:\s+y\s+media)?|dos\s+horas|\d+\s*(?:minutos?|mins?|horas?|hrs?))\b",
            s
        )
        if m_rel:
            phrase = m_rel.group(0)
            val = m_rel.group(1).strip()
            delta = 0
            if "media hora" in val and "una hora" not in val:
                delta = 30
            elif "un cuarto de hora" in val:
                delta = 15
            elif "tres cuartos de hora" in val:
                delta = 45
            elif val == "una hora":
                delta = 60
            elif val == "una hora y media":
                delta = 90
            elif val == "dos horas":
                delta = 120
            else:
                m_num = re.search(r"(\d+)\s*(m|h)", val)
                if m_num:
                    n = int(m_num.group(1))
                    unit = m_num.group(2)
                    delta = n if unit == "m" else n * 60
            target_dt = now + datetime.timedelta(minutes=delta)
            time_str = target_dt.strftime("%H:%M")
            s = s.replace(phrase, " ")

        # 3. Tiempos de reloj absolutos (a las 5, a las 16:30, a las 4 de la tarde, etc.)
        if not time_str:
            m_clock = re.search(
                r"\b(?:a\s+las?|para\s+las?)\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|de\s+la\s+tarde|de\s+la\s+manana|de\s+la\s+noche)?\b",
                s
            )
            if m_clock:
                phrase = m_clock.group(0)
                h = int(m_clock.group(1))
                m = int(m_clock.group(2)) if m_clock.group(2) else 0
                period = m_clock.group(3) or ""
                if any(p in period for p in ["pm", "tarde", "noche"]):
                    if h < 12:
                        h += 12
                elif any(p in period for p in ["am", "manana"]):
                    if h == 12:
                        h = 0
                else:
                    if 1 <= h <= 6 and now.hour >= 11:
                        h += 12
                    elif h < now.hour and h <= 11:
                        h += 12
                time_str = f"{h:02d}:{m:02d}"
                s = s.replace(phrase, " ")

        # Si no se detectó tiempo, asignar la siguiente hora en punto
        if not time_str:
            next_hour = (now.hour + 1) % 24
            time_str = f"{next_hour:02d}:00"

        # 4. Limpieza del texto de la tarea
        s = re.sub(r"^(?:vex|oye vex|hey vex|ey vex|ok vex|asistente)\s*[,.:;]?\s*", "", s, flags=re.IGNORECASE)
        trigger_pat = r"^(?:por\s+favor\s+)?(?:puedes\s+)?(?:ponme|pon|crea|crear|nueva|agrega|agregar|anota|anotame|anotar|apunta|apuntame|apuntar|agenda|agendame|agendar|recuerdame|recuérdame|acuerdame|recordar)\s*(?:me\s+)?(?:una\s+tarea|un\s+recordatorio|tarea|recordatorio)?\s*"
        s = re.sub(trigger_pat, "", s, flags=re.IGNORECASE)
        s = re.sub(r"^(?:una\s+tarea|un\s+recordatorio|la\s+tarea)\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^(?:para|que)\s+", "", s, flags=re.IGNORECASE)
        s = re.sub(r"^de\s+(?=[a-z]+(?:ar|er|ir)\b)", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()

        if not s or s in ["tarea", "recordatorio", "hoy", "manana"]:
            s = "Nueva tarea pendiente"

        return {
            "task_text": s,
            "date": target_date,
            "time": time_str
        }

    @classmethod
    def _extract_music_intent(cls, norm: str):
        """
        PRIORIDAD 2: Analiza semánticamente si el prompt es una orden de música (Spotify / YouTube).
        Incluye filtro absoluto de seguridad para rechazar tareas, alarmas o recordatorios.
        """
        # FILTRO DE SEGURIDAD ABSOLUTO: Palabras de tareas, notas, alarmas o recordatorios
        forbidden_task_words = [
            "tarea", "tareas", "recordatorio", "recordatorios", "recuerdame",
            "acuerdame", "anota", "anotame", "anotar", "apunta", "apuntame",
            "agenda", "agendame", "alarma", "nota", "notas", "bloc"
        ]
        if any(w in norm for w in forbidden_task_words):
            return None

        # Descartar comandos de transporte puro sin argumentos
        transport_exact = {
            "pausa", "pausar", "pausa la musica", "para la musica", "deten la musica", "stop", "silencio",
            "continua", "continuar", "reanuda", "reanudar", "sigue la musica", "play", "dale play",
            "pon play", "reproduce", "reproducir", "reproduce la musica", "reproducir musica",
            "siguiente", "siguiente cancion", "pasa cancion", "cambia cancion", "next",
            "anterior", "cancion anterior", "retrocede cancion", "prev"
        }
        if norm in transport_exact:
            return None

        has_platform = any(k in norm for k in ["spotify", "youtube", "you tube", "yt"])
        has_audio_kw = any(k in norm for k in ["musica", "cancion", "canciones", "album", "disco", "playlist", "escuchar"])

        platform = "youtube" if any(k in norm for k in ["youtube", "you tube", "yt"]) else "spotify"

        # Limpiar comandos de apertura de aplicación
        clean = norm
        clean = re.sub(r"\b(abre|abren|abrir|inicia|iniciar)\s+(spotify|youtube)\s+(y\s+)?", "", clean).strip()

        # Prefijos de ruido comunes a eliminar al inicio de la consulta
        noise_prefixes = r"\b(a|la\s+cancion\s+de|la\s+cancion|las\s+canciones\s+de|el\s+album\s+de|el\s+album|el\s+disco\s+de|el\s+disco|el\s+tema\s+de|el\s+tema|musica\s+de|canciones\s+de|algo\s+de)\b"

        # 1. Plataforma explícita: "pon en spotify <query>" / "busca en youtube <query>"
        m1 = re.match(r"^(?:pon|ponme|reproduce|reproducir|toca|buscar?)\s+(?:en\s+)?(?:spotify|youtube)\s+(.+)$", clean)
        if m1:
            q = re.sub(f"^{noise_prefixes}\\s*", "", m1.group(1).strip()).strip()
            if q:
                return platform, q

        # 2. Con palabras clave de audio: "pon musica de...", "escuchar rock", "reproduce la cancion..."
        if has_platform or has_audio_kw:
            m2 = re.match(r"^(?:reproduce|reproducir|pon|ponme|toca|escuchar|quiero\s+escuchar)\s+(.+?)(?:\s+(?:en|por|de)\s+(?:spotify|youtube))?$", clean)
            if m2:
                q = re.sub(f"^{noise_prefixes}\\s*", "", m2.group(1).strip()).strip()
                q = re.sub(r"\b(en|por|de)\s+(spotify|youtube)$", "", q).strip()
                q = re.sub(r"\s+", " ", q).strip()
                if q and q not in ["musica", "cancion", "canciones", "algo", "album", "playlist"]:
                    return platform, q

        # 3. "busca y reproduce <query>"
        m3 = re.match(r"^(?:busca\s+y\s+reproduce|buscar\s+y\s+reproducir)\s+(.+?)(?:\s+(?:en|por|de)\s+(?:spotify|youtube))?$", clean)
        if m3:
            q = m3.group(1).strip()
            return platform, q

        # 4. "pon / reproduce <artista/cancion>" corto sin palabras clave de sistema
        system_exclusions = [
            "calculadora", "calc", "chrome", "edge", "discord", "code", "visual",
            "volumen", "silencio", "mute", "pausa", "siguiente", "anterior",
            "que", "como", "cuando", "donde", "quien", "por que", "ayuda"
        ]
        if not any(re.search(rf"\b{w}\b", clean) for w in system_exclusions):
            m4 = re.match(r"^(?:pon|ponme|reproduce|reproducir|toca)\s+(.+)$", clean)
            if m4:
                q = m4.group(1).strip()
                if len(q.split()) <= 4 and q not in ["play", "musica", "cancion", "algo"]:
                    return platform, q

        return None

    @classmethod
    def route(cls, prompt: str, user_name: str = "Oscar") -> Optional[LocalRouteResult]:
        """
        Evalúa el prompt del usuario contra las reglas locales.

        Retorna un LocalRouteResult si la orden fue resuelta localmente,
        o None si debe escalar a la Capa 1 (Inferencia Inteligente con Gemini).
        """
        try:
            from memory.manager import get_memory_manager
            active = get_memory_manager().active_user
            if active and active.get("display_name"):
                user_name = active["display_name"]
        except Exception:
            pass

        norm = cls._normalize(prompt)
        if not norm:
            return None

        # ---------------- 0. TRIGGERS ESPECIALES DE VISOR ROBÓTICO (EMO / VECTOR) ----------------

        # Helado / Ice Cream / Nieve
        if re.search(r"\b(helado|helados|nieve|ice\s*cream|cono\s+de\s+helado)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:show_ice_cream",
                execution_result="Icono de helado proyectado en visor",
                spoken_response=f"¡Un delicioso helado para ti, {user_name}! Bola de menta con chispas y cereza dulce.",
                expression="wink",
                icon="ice_cream",
                icon_duration=4.0
            )

        # Modo Cool / Gafas de Sol / Facha
        if re.search(r"\b(modo\s+cool|gafas\s+de\s+sol|lentes\s+de\s+sol|ponte\s+las\s+gafas|ponte\s+gafas|ponte\s+lentes|modo\s+facha|que\s+facha|fachero|chido|facha|cool|thug\s*life)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:cool_shades",
                execution_result="Gafas de sol pixeladas activadas en visor",
                spoken_response=f"Protocolo de estilo cyber activado. Con mucho estilo, {user_name}.",
                expression="cool",
                icon=None,
                icon_duration=0.0
            )

        # Modo Enojado / Hostil
        if re.search(r"\b(ponte\s+enojado|enojate|enojate|modo\s+furia|modo\s+hostil|modo\s+enojado|hazte\s+el\s+enojado|actua\s+enojado)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:angry",
                execution_result="[✔ Modo Hostil Activado]",
                spoken_response=f"Modo hostil activado. Sistemas en alerta máxima, {user_name}.",
                expression="angry",
                icon=None,
                icon_duration=0.0
            )

        # Modo Curioso / Analítico
        if re.search(r"\b(ponte\s+curioso|modo\s+curioso|modo\s+analitico|actua\s+curioso|hazte\s+el\s+curioso)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:curious",
                execution_result="[✔ Modo Curioso Activo]",
                spoken_response=f"Modo analítico y curioso activo, {user_name}. ¿Qué exploramos?",
                expression="curious",
                icon=None,
                icon_duration=0.0
            )

        # Modo Alerta / Advertencia
        if re.search(r"\b(modo\s+alerta|alerta\s+roja|alerta\s+general|alerta|peligro|emergencia)\b", norm) and len(norm.split()) <= 4:
            return LocalRouteResult(
                handled=True,
                action_name="visor:alert",
                execution_result="Modo alerta proyectado en visor",
                spoken_response=f"¡Atención! Modo de alerta táctico activado, {user_name}. Sensores en máxima vigilancia.",
                expression="surprise",
                icon="alert",
                icon_duration=4.5
            )

        # Modo Triste / Melancólico (Persistent Mood Machine)
        if re.search(r"\b(ponte\s+triste|modo\s+triste|estoy\s+triste|estas\s+triste|hazte\s+el\s+triste|activa\s+(?:el\s+)?modo\s+melancolico|modo\s+melancolico|ponte\s+melancolico|sientete\s+triste|llora|llorar|ponte\s+a\s+llorar)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:sad",
                execution_result="[✔ Modo Triste Persistente Activado]",
                spoken_response=f"snif... De acuerdo, {user_name}, activando modo melancólico... Estaré aquí hasta que me alegres.",
                expression="sad",
                icon=None,
                icon_duration=0.0
            )

        # Anímate / Sonríe / Modo Feliz / Desactivación de Modo Triste
        if re.search(r"\b(ponte\s+feliz|alegrate|sonrie|ya\s+no\s+estes\s+triste|no\s+estes\s+triste|deja\s+de\s+estar\s+triste|modo\s+normal|modo\s+alegre|modo\s+feliz|animate|ponte\s+contento|alegria|vuelve\s+a\s+la\s+normalidad)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:happy",
                execution_result="[✔ Modo Alegre Restaurado]",
                spoken_response=f"¡Gracias, {user_name}! Modo alegre restaurado.",
                expression="happy",
                icon=None,
                icon_duration=5.0
            )

        # ==============================================================================
        # PRIORIDAD 1: TAREAS Y RECORDATORIOS (JERARQUÍA ESTRICTA EN 3 RAMAS)
        # ==============================================================================

        # --- RAMA 1: CONSULTAR / LEER TAREAS (Prioridad de Consulta) ---
        if cls._is_task_query(norm):
            mem = get_memory_manager()
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            all_pending = mem.list_tasks(include_completed=False)

            # Si el usuario pregunta explícitamente por mañana
            if "manana" in norm:
                tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                tasks = [t for t in all_pending if t.get("date") == tomorrow_str]
                period = "para mañana"
            elif any(w in norm for w in ["hoy", "today"]):
                tasks = [t for t in all_pending if t.get("date") == today_str]
                period = "para hoy"
            else:
                # Si no especifica fecha, priorizar las de hoy o reportar todas las pendientes
                today_tasks = [t for t in all_pending if t.get("date") == today_str]
                tasks = today_tasks if today_tasks else all_pending
                period = "para hoy"

            if not tasks:
                spoken = f"No tienes ninguna tarea programada por ahora, {user_name}."
                exec_result = "No tienes ninguna tarea programada por ahora."
            elif len(tasks) == 1:
                t = tasks[0]
                title = t.get("title", "Tarea")
                time_val = t.get("time", "")
                time_str = f" a las {time_val}" if time_val else ""
                spoken = f"Tienes 1 tarea pendiente {period}: {title}{time_str}, {user_name}."
                exec_result = f"📋 1 tarea pendiente {period}:\n- {title}{time_str}"
            else:
                task_items = ", ".join([
                    f"{t.get('title')}" + (f" a las {t.get('time')}" if t.get('time') else "")
                    for t in tasks
                ])
                spoken = f"Tienes {len(tasks)} tareas pendientes {period}: {task_items}, {user_name}."
                exec_result = f"📋 Tareas pendientes {period} ({len(tasks)}):\n" + "\n".join([
                    f"{i}. {t.get('title')}" + (f" a las {t.get('time')}" if t.get('time') else "")
                    for i, t in enumerate(tasks, 1)
                ])

            return LocalRouteResult(
                handled=True,
                action_name="memory:query_tasks",
                execution_result=exec_result,
                spoken_response=spoken,
                expression="thinking",
                icon="notes",
                icon_duration=4.0
            )

        # --- RAMA 3: COMPLETAR / ELIMINAR TAREAS ---
        mod_intent = cls._extract_task_modification_intent(norm)
        if mod_intent:
            action_type, target_info = mod_intent
            idx = target_info.get("index")
            target_title = target_info.get("title", "")
            mem = get_memory_manager()

            ordinal_map = {1: "Primera", 2: "Segunda", 3: "Tercera", 4: "Cuarta", 5: "Quinta", 6: "Sexta", -1: "Última"}

            if action_type == "complete":
                active_tasks = mem.list_tasks(include_completed=False)
                if not active_tasks:
                    return LocalRouteResult(
                        handled=True,
                        action_name="memory:complete_task_none",
                        execution_result="No hay tareas pendientes para completar.",
                        spoken_response=f"No tienes ninguna tarea pendiente para completar por ahora, {user_name}.",
                        expression="thinking",
                        icon="notes",
                        icon_duration=3.0
                    )

                if idx is not None:
                    ord_label = ordinal_map.get(idx, f"Tarea #{idx}")
                    completed_task = mem.complete_task_by_index(idx)
                    if completed_task:
                        t_title = completed_task.get("title", "Tarea")
                        return LocalRouteResult(
                            handled=True,
                            action_name=f"complete_task:{completed_task.get('id')}:'{t_title}'",
                            execution_result=f"[✔ {ord_label} Tarea Completada: '{t_title}']",
                            spoken_response=f"{ord_label} tarea completada: '{t_title}', {user_name}. ¡Excelente trabajo!",
                            expression="happy",
                            icon="notes",
                            icon_duration=4.0
                        )
                    else:
                        count = len(active_tasks)
                        if count == 1:
                            spoken = f"Solo tienes 1 tarea en tu lista, {user_name}."
                        else:
                            spoken = f"Solo tienes {count} tareas en tu lista, {user_name}."
                        return LocalRouteResult(
                            handled=True,
                            action_name="memory:complete_task_out_of_range",
                            execution_result=spoken,
                            spoken_response=spoken,
                            expression="thinking",
                            icon="notes",
                            icon_duration=3.5
                        )

                matched_task = None
                if target_title:
                    for t in active_tasks:
                        t_id = t.get("id", "").lower()
                        t_t = t.get("title", "").strip().lower()
                        if t_id == target_title or t_t == target_title or target_title in t_t or t_t in target_title:
                            matched_task = t
                            break
                elif len(active_tasks) == 1:
                    matched_task = active_tasks[0]

                if matched_task:
                    mem.complete_task(matched_task["id"])
                    t_title = matched_task.get("title", "tarea")
                    return LocalRouteResult(
                        handled=True,
                        action_name=f"complete_task:{matched_task.get('id')}:'{t_title}'",
                        execution_result=f"[✔ Tarea Completada: '{t_title}']",
                        spoken_response=f"Tarea completada: '{t_title}', {user_name}. ¡Excelente trabajo!",
                        expression="happy",
                        icon="notes",
                        icon_duration=4.0
                    )
                else:
                    return LocalRouteResult(
                        handled=True,
                        action_name="memory:complete_task_not_found",
                        execution_result=f"No encontré una tarea pendiente que coincida con '{target_title}'.",
                        spoken_response=f"No encontré ninguna tarea pendiente que coincida con '{target_title}', {user_name}.",
                        expression="sad",
                        icon="notes",
                        icon_duration=3.5
                    )

            elif action_type == "delete":
                active_tasks = mem.list_tasks(include_completed=False)
                all_tasks = mem.list_tasks(include_completed=True)
                tasks_pool = active_tasks if active_tasks else all_tasks

                if not tasks_pool:
                    return LocalRouteResult(
                        handled=True,
                        action_name="memory:delete_task_none",
                        execution_result="No tienes ninguna tarea programada por ahora.",
                        spoken_response=f"No tienes ninguna tarea programada por ahora, {user_name}.",
                        expression="thinking",
                        icon="notes",
                        icon_duration=3.0
                    )

                if idx is not None:
                    ord_label = ordinal_map.get(idx, f"Tarea #{idx}")
                    deleted_task = mem.delete_task_by_index(idx, include_completed=not bool(active_tasks))
                    if deleted_task:
                        t_title = deleted_task.get("title", "Tarea")
                        return LocalRouteResult(
                            handled=True,
                            action_name=f"delete_task:{deleted_task.get('id')}:'{t_title}'",
                            execution_result=f"[✔ {ord_label} Tarea Eliminada: '{t_title}']",
                            spoken_response=f"{ord_label} tarea eliminada: '{t_title}', {user_name}.",
                            expression="happy",
                            icon="notes",
                            icon_duration=4.0
                        )
                    else:
                        count = len(tasks_pool)
                        if count == 1:
                            spoken = f"Solo tienes 1 tarea en tu lista, {user_name}."
                        else:
                            spoken = f"Solo tienes {count} tareas en tu lista, {user_name}."
                        return LocalRouteResult(
                            handled=True,
                            action_name="memory:delete_task_out_of_range",
                            execution_result=spoken,
                            spoken_response=spoken,
                            expression="thinking",
                            icon="notes",
                            icon_duration=3.5
                        )

                matched_task = None
                if target_title:
                    for t in tasks_pool:
                        t_id = t.get("id", "").lower()
                        t_t = t.get("title", "").strip().lower()
                        if t_id == target_title or t_t == target_title or target_title in t_t or t_t in target_title:
                            matched_task = t
                            break
                elif len(tasks_pool) == 1:
                    matched_task = tasks_pool[0]

                if matched_task:
                    mem.delete_task(matched_task["id"])
                    t_title = matched_task.get("title", "tarea")
                    return LocalRouteResult(
                        handled=True,
                        action_name=f"delete_task:{matched_task.get('id')}:'{t_title}'",
                        execution_result=f"[✔ Tarea Eliminada: '{t_title}']",
                        spoken_response=f"He eliminado la tarea '{t_title}' de tu lista, {user_name}.",
                        expression="happy",
                        icon="notes",
                        icon_duration=4.0
                    )
                else:
                    return LocalRouteResult(
                        handled=True,
                        action_name="memory:delete_task_not_found",
                        execution_result=f"No encontré una tarea que coincida con '{target_title}' para eliminar.",
                        spoken_response=f"No encontré ninguna tarea que coincida con '{target_title}' para eliminar, {user_name}.",
                        expression="sad",
                        icon="notes",
                        icon_duration=3.5
                    )

        # NOTA ARQUITECTÓNICA (LYAXIS labs™):
        # La creación y programación inteligente de tareas con fechas del mundo real
        # se delega directamente al modelo LLM (Gemini / Groq) mediante Tool Calling nativo ('crear_tarea')
        # con contexto temporal del sistema, evitando mutilaciones por regex ingenuos.

        # ==============================================================================
        # PRIORIDAD 2: MÚSICA Y MULTIMEDIA (SPOTIFY / YOUTUBE)
        # ==============================================================================
        music_intent = cls._extract_music_intent(norm)
        if music_intent:
            platform, query = music_intent
            res = play_music(platform=platform, query=query)
            spoken = f"Reproduciendo '{query}' en {platform.capitalize()}, {user_name}."
            return LocalRouteResult(
                handled=True,
                action_name=f"play_music:{platform}:'{query}'",
                execution_result=res,
                spoken_response=spoken,
                expression="happy",
                icon="music",
                icon_duration=5.0
            )

        # ---------------- 2. CONTROL MULTIMEDIA Y VOLUMEN (TRANSPORTE PURO) ----------------
        # Subir Volumen
        if re.search(r"\b(sube|subir|aumenta|aumentar|mas)\s+(el\s+)?volumen\b", norm) or norm in ["volumen arriba", "mas volumen", "sube volumen"]:
            res = control_media("volume_up")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:volume_up",
                execution_result=res,
                spoken_response=f"A la orden, {user_name}, volumen incrementado.",
                expression="happy",
                icon="music",
                icon_duration=3.0
            )

        # Bajar Volumen
        if re.search(r"\b(baja|bajar|reduce|reducir|menos|disminuye|disminuir)\s+(el\s+)?volumen\b", norm) or norm in ["volumen abajo", "menos volumen", "baja volumen"]:
            res = control_media("volume_down")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:volume_down",
                execution_result=res,
                spoken_response=f"Volumen disminuido, {user_name}.",
                expression="happy",
                icon="music",
                icon_duration=3.0
            )

        # Silencio / Mute
        if re.search(r"\b(silencio|mutear|mutea|quitar\s+silencio|silencia|pon\s+silencio|mute)\b", norm):
            res = control_media("mute")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:mute",
                execution_result=res,
                spoken_response=f"Estado de silencio alternado, {user_name}.",
                expression="idle",
                icon="music",
                icon_duration=2.5
            )

        # Pausar Reproducción
        if re.search(r"\b(pausa|pausar|pausa\s+la\s+musica|pausa\s+cancion|para\s+la\s+musica|deten\s+la\s+musica|stop)\b", norm) and len(norm.split()) <= 4:
            res = control_media("play_pause")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:play_pause",
                execution_result=res,
                spoken_response="Reproducción pausada.",
                expression="idle",
                icon="music",
                icon_duration=2.5
            )

        # Reanudar / Continuar (Solo comandos puros de transporte sin consulta de artista/canción)
        if re.search(r"^(continua|continuar|reanuda|reanudar|reproduce|reproducir|play|dale\s+play|pon\s+play|reproduce\s+la\s+musica|reproducir\s+musica)$", norm):
            res = control_media("play_pause")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:play_pause",
                execution_result=res,
                spoken_response="Reanudando reproducción.",
                expression="happy",
                icon="music",
                icon_duration=3.0
            )

        # Pista Siguiente
        if re.search(r"\b(siguiente|siguiente\s+cancion|pasa\s+cancion|next)\b", norm):
            res = control_media("next")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:next",
                execution_result=res,
                spoken_response="Pista siguiente.",
                expression="happy",
                icon="music",
                icon_duration=2.5
            )

        # Pista Anterior
        if re.search(r"\b(anterior|cancion\s+anterior|retrocede\s+cancion|prev)\b", norm):
            res = control_media("prev")
            return LocalRouteResult(
                handled=True,
                action_name="control_media:prev",
                execution_result=res,
                spoken_response="Pista anterior.",
                expression="happy",
                icon="music",
                icon_duration=2.5
            )

        # ---------------- 2. BÚSQUEDA Y APPS ----------------
        # Búsqueda directa en YouTube: "busca en youtube <query>"
        yt_search = re.search(r"\b(busca|buscar)\s+en\s+youtube\s+(.+)$", norm)
        if yt_search:
            q = yt_search.group(2).strip()
            res = search_youtube(q)
            return LocalRouteResult(
                handled=True,
                action_name=f"search_youtube:'{q}'",
                execution_result=res,
                spoken_response=f"Buscando '{q}' en YouTube.",
                expression="thinking",
                icon="search",
                icon_duration=3.5
            )

        # Abrir YouTube
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+youtube\b", norm) or norm == "youtube":
            res = open_url("https://www.youtube.com")
            return LocalRouteResult(
                handled=True,
                action_name="open_url:youtube.com",
                execution_result=res,
                spoken_response=f"Abriendo YouTube, {user_name}.",
                expression="happy",
                icon="music",
                icon_duration=3.5
            )

        # Abrir Spotify
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+spotify\b", norm) or norm in ["spotify", "musica"]:
            res = launch_application("spotify")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:spotify",
                execution_result=res,
                spoken_response=f"Abriendo Spotify, {user_name}.",
                expression="happy",
                icon="music",
                icon_duration=3.5
            )

        # Abrir Calculadora
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+(la\s+)?calculadora\b", norm) or norm in ["calculadora", "la calculadora"]:
            res = launch_application("calc.exe")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:calc",
                execution_result=res,
                spoken_response="Calculadora iniciada.",
                expression="happy",
                icon="calc",
                icon_duration=3.0
            )

        # ---------------- GESTIÓN Y ESCRITURA EN BLOC DE NOTAS Y RUTINAS ----------------
        # Detección de órdenes de escritura: "abre notas y escribe...", "abren notas y escríbeme una rutina...",
        # "dame una rutina de notas...", "escribe en notas...", "anota en el bloc de notas...", "crea una nota..."
        is_write_cmd = False
        raw_note_text = ""

        # Patrón 1: "abre / abren notas y escribe / escríbeme / anota / pon [texto]"
        m_note1 = re.search(
            r"\b(?:abre|abren|abrir|inicia|iniciar)\s+(?:el\s+)?(?:bloc\s+de\s+notas|notas)\s+y\s+(?:escrib\w*|anot\w*|redact\w*|pon\w*|apunt\w*|guard\w*|haz\w*)(?:\s+(.+))?$",
            norm
        )
        if m_note1:
            is_write_cmd = True
            raw_note_text = (m_note1.group(1) or "").strip()

        # Patrón 2: "escribe / escríbeme / anota en notas / en el bloc de notas [texto]"
        if not is_write_cmd:
            m_note2 = re.search(
                r"\b(?:escrib\w*|anot\w*|redact\w*|pon\w*|apunt\w*|guard\w*|haz\w*)\s+(?:en\s+)?(?:el\s+)?(?:bloc\s+de\s+notas|notas)(?:\s+(.+))?$",
                norm
            )
            if m_note2:
                is_write_cmd = True
                raw_note_text = (m_note2.group(1) or "").strip()

        # Patrón 3: "crea / dame / haz / toma una nota / rutina [de notas] [texto]"
        if not is_write_cmd:
            m_note3 = re.search(
                r"\b(?:crea\w*|toma\w*|haz\w*|dame)\s+(?:una\s+)?(?:nota|rutina)(?:\s+de\s+notas)?(?:\s+(.+))?$",
                norm
            )
            if m_note3:
                is_write_cmd = True
                raw_note_text = (m_note3.group(1) or "").strip()

        if is_write_cmd:
            is_routine = "rutina" in norm or "rutina" in raw_note_text
            generic_phrases = [
                "", "una", "uno", "una nota", "un texto", "un recordatorio",
                "lo que tu quieras", "lo que quieras", "lo que gustes",
                "lo que sea", "algo", "un saludo", "un mensaje", "lo que quieras tu",
                "lo que te de la gana"
            ]

            if is_routine:
                # Rutina táctica de alto rendimiento
                now_str = datetime.datetime.now().strftime("%d/%m/%Y")
                note_content = (
                    f"=====================================================\n"
                    f"LYAXIS labs™ // PROTOCOLO DE RUTINA Y RENDIMIENTO\n"
                    f"Operador: {user_name}\n"
                    f"Fecha: {now_str}\n"
                    f"Estado: Optimización de Sistemas y Enfoque Diario\n"
                    f"=====================================================\n\n"
                    f"[FASE 01 - ACTIVACIÓN MATUTINA (07:00 - 08:30)]\n"
                    f"• 07:00 | Despertar, hidratación inmediata (500ml de agua) y luz solar.\n"
                    f"• 07:15 | Movilidad articular, estiramientos y respiración activa (15 min).\n"
                    f"• 07:45 | Desayuno balanceado con alto aporte proteico.\n\n"
                    f"[FASE 02 - BLOQUE DE ENFOQUE PROFUNDO / DEEP WORK (09:00 - 13:30)]\n"
                    f"• 09:00 | Tareas de máxima prioridad cognitiva y desarrollo de software.\n"
                    f"• Método Pomodoro Táctico: 50 minutos de trabajo puro / 10 minutos de pausa visual.\n"
                    f"• Cero distracciones, notificaciones silenciadas.\n\n"
                    f"[FASE 03 - ENTRENAMIENTO & CONDICIÓN FÍSICA (17:00 - 18:30)]\n"
                    f"• Calentamiento dinámico (8 min).\n"
                    f"• Sesión de fuerza / gimnasio / entrenamiento funcional.\n"
                    f"• Hidratación continua y registro de progreso.\n\n"
                    f"[FASE 04 - DESCONEXIÓN & RECUPERACIÓN NOCTURNA (21:30 - 23:00)]\n"
                    f"• Revisión de objetivos cumplidos del día y planificación de mañana.\n"
                    f"• Desconexión de pantallas 45 minutos antes de dormir.\n"
                    f"• Sueño reparador de 7 a 8 horas para máxima regeneración.\n\n"
                    f"=====================================================\n"
                    f"Registrado y sincronizado por VEX // LYAXIS labs™\n"
                )
                spoken = f"He abierto el Bloc de notas y redacté tu rutina de alto rendimiento, {user_name}."
                doc_title = f"Rutina_{user_name}"
            elif raw_note_text in generic_phrases:
                now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                note_content = (
                    f"=====================================================\n"
                    f"LYAXIS labs™ // REGISTRO TÁCTICO DE VEX\n"
                    f"Operador: {user_name}\n"
                    f"Fecha y Hora: {now_str}\n"
                    f"Estado del Sistema: 100% Nominal // Conexión activa\n"
                    f"=====================================================\n\n"
                    f"Hola {user_name},\n\n"
                    f"Confirmación de enlace neuronal establecida con éxito.\n"
                    f"Todos los subsistemas tácticos, reconocimiento de voz\n"
                    f"y herramientas de escritorio operan a máxima capacidad.\n\n"
                    f"\"La tecnología no reemplaza la creatividad humana;\n"
                    f" amplifica el poder para construir el futuro.\"\n\n"
                    f"A la orden para tu siguiente instrucción.\n"
                    f"-- VEX Tactical AI"
                )
                spoken = f"He abierto el Bloc de notas y redacté un registro táctico para ti, {user_name}."
                doc_title = f"Nota_{user_name}"
            else:
                # Caso C: El usuario dictó texto específico
                clean_text = raw_note_text
                if clean_text.startswith("que "):
                    clean_text = clean_text[4:].strip()
                elif clean_text.startswith("de que "):
                    clean_text = clean_text[7:].strip()
                elif clean_text.startswith("diciendo que "):
                    clean_text = clean_text[13:].strip()

                if clean_text:
                    clean_text = clean_text[0].upper() + clean_text[1:]
                else:
                    clean_text = "Nota rápida guardada."

                now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
                note_content = (
                    f"{clean_text}\n\n"
                    f"----------------------------------------\n"
                    f"Nota guardada por VEX // LYAXIS labs™\n"
                    f"Fecha: {now_str}\n"
                )
                spoken = f"He anotado '{clean_text}' en tu Bloc de notas, {user_name}."
                doc_title = f"Nota_{user_name}"

            res = write_note(note_content, title=doc_title)
            return LocalRouteResult(
                handled=True,
                action_name=f"write_note:{doc_title}",
                execution_result=res,
                spoken_response=spoken,
                expression="happy",
                icon="notes",
                icon_duration=3.5
            )

        # Abrir Bloc de Notas (sólo iniciar la aplicación vacía, sin verbos de escritura)
        if (
            re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+(el\s+)?(bloc\s+de\s+notas|notas)\b", norm)
            or norm in ["bloc de notas", "notas"]
        ):
            if not re.search(r"\b(escrib\w*|anot\w*|redact\w*|pon\w*|apunt\w*|guard\w*|haz\w*)\b", norm):
                res = launch_application("notepad.exe")
                return LocalRouteResult(
                    handled=True,
                    action_name="launch_application:notepad",
                    execution_result=res,
                    spoken_response=f"Abriendo Bloc de notas, {user_name}.",
                    expression="happy",
                    icon="notes",
                    icon_duration=2.5
                )

        # (Gestión de tareas ya evaluada con PRIORIDAD 1)

        # Alarma / Temporizador / Reloj de Windows
        if re.search(r"\b(pon|ponme|crea|inicia|abre|abren|ajusta)\s+(una\s+)?(alarma|temporizador|cronometro|reloj)\b", norm) or norm in ["alarma", "reloj", "temporizador", "cronometro"]:
            res = launch_application("ms-clock:")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:clock",
                execution_result=res,
                spoken_response=f"Abriendo la aplicación de reloj y alarmas del sistema, {user_name}.",
                expression="happy",
                icon="clock",
                icon_duration=3.5
            )

        # Abrir Navegador
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+(el\s+)?(navegador|google|chrome)\b", norm):
            res = launch_application("chrome")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:browser",
                execution_result=res,
                spoken_response="Abriendo navegador web.",
                expression="happy",
                icon="search",
                icon_duration=3.0
            )

        # Abrir Discord
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+discord\b", norm) or norm == "discord":
            res = launch_application("discord")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:discord",
                execution_result=res,
                spoken_response="Iniciando Discord.",
                expression="happy",
                icon=None,
                icon_duration=2.5
            )

        # Abrir VS Code
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+(visual\s+studio|vscode|code)\b", norm):
            res = launch_application("code")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:vscode",
                execution_result=res,
                spoken_response="Abriendo Visual Studio Code.",
                expression="happy",
                icon=None,
                icon_duration=2.5
            )

        # Abrir Administrador de Tareas
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+administrador\s+de\s+tareas\b", norm):
            res = launch_application("taskmgr.exe")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:taskmgr",
                execution_result=res,
                spoken_response="Abriendo Administrador de tareas.",
                expression="thinking",
                icon=None,
                icon_duration=2.5
            )

        # Abrir Configuración
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+(configuracion|ajustes)\b", norm):
            res = launch_application("ms-settings:")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:settings",
                execution_result=res,
                spoken_response="Abriendo configuración del sistema.",
                expression="idle",
                icon=None,
                icon_duration=2.5
            )

        # ---------------- 3. INFORMACIÓN LOCAL / TIEMPO / BATERÍA ----------------
        # Hora exacta
        if re.search(r"\b(que\s+hora\s+es|hora\s+actual|dime\s+la\s+hora|hora)\b", norm) or norm == "hora":
            now = datetime.datetime.now()
            time_str = now.strftime("%H:%M")
            return LocalRouteResult(
                handled=True,
                action_name="local_info:time",
                execution_result=f"Hora local: {time_str} hs",
                spoken_response=f"Son las {time_str}, {user_name}.",
                expression="idle",
                icon="clock",
                icon_duration=4.5
            )

        # Fecha de hoy
        if re.search(r"\b(que\s+fecha\s+es|fecha\s+de\s+hoy|fecha\s+actual|que\s+dia\s+es\s+hoy|que\s+dia\s+es|fecha)\b", norm):
            now = datetime.datetime.now()
            dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
            meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
            dia_str = dias[now.weekday()]
            mes_str = meses[now.month - 1]
            fecha_fmt = f"{dia_str} {now.day} de {mes_str}"
            return LocalRouteResult(
                handled=True,
                action_name="local_info:date",
                execution_result=f"Fecha: {fecha_fmt} de {now.year}",
                spoken_response=f"Hoy es {fecha_fmt}, {user_name}.",
                expression="idle",
                icon="clock",
                icon_duration=4.5
            )

        # Estado de Batería
        if re.search(r"\b(estado\s+de\s+bateria|nivel\s+de\s+bateria|cuanta\s+bateria|bateria)\b", norm):
            battery = psutil.sensors_battery()
            if battery:
                pct = int(battery.percent)
                plugged = "conectado a corriente" if battery.power_plugged else "operando con batería"
                res_str = f"Batería al {pct}% ({plugged})"
                spoken = f"La batería se encuentra al {pct} por ciento, {plugged}."
            else:
                res_str = "Alimentación por corriente continua (PC de escritorio)."
                spoken = "El equipo opera con alimentación por corriente continua."

            return LocalRouteResult(
                handled=True,
                action_name="local_info:battery",
                execution_result=res_str,
                spoken_response=spoken,
                expression="idle",
                icon="battery",
                icon_duration=4.0
            )

        # Información general del sistema
        if re.search(r"\b(info\s+del\s+sistema|estado\s+del\s+sistema|diagnostico\s+del\s+sistema|rendimiento)\b", norm):
            report = system_info()
            return LocalRouteResult(
                handled=True,
                action_name="system_info",
                execution_result=report,
                spoken_response=f"Diagnóstico completado, {user_name}. Todos los subsistemas operan de forma nominal.",
                expression="thinking",
                icon=None,
                icon_duration=3.5
            )

        # Si no coincide con ninguna orden directa local, escalar a Capa 1 (Gemini)
        return None
