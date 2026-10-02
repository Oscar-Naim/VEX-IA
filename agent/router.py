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
        s = re.sub(r"^(vex|oye vex|hey vex|ey vex|hola vex|ok vex|buenas vex|asistente)\s*[,.:;]?\s*", "", s).strip()
        # Normalizar acentos
        replacements = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")]
        for a, b in replacements:
            s = s.replace(a, b)
        # Limpiar signos
        s = re.sub(r"[^\w\s]", "", s).strip()
        return s

    @classmethod
    def route(cls, prompt: str, user_name: str = "Oscar") -> Optional[LocalRouteResult]:
        """
        Evalúa el prompt del usuario contra las reglas locales.

        Retorna un LocalRouteResult si la orden fue resuelta localmente,
        o None si debe escalar a la Capa 1 (Inferencia Inteligente con Gemini).
        """
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
        if re.search(r"\b(modo\s+cool|gafas\s+de\s+sol|lentes\s+de\s+sol|ponte\s+las\s+gafas|modo\s+facha|que\s+facha|fachero|chido|facha|cool|thug\s*life)\b", norm):
            return LocalRouteResult(
                handled=True,
                action_name="visor:cool_shades",
                execution_result="Gafas de sol pixeladas activadas en visor",
                spoken_response=f"Protocolo de estilo cyber activado. Nivel de facha al cien por ciento, {user_name}.",
                expression="cool_shades",
                icon=None,
                icon_duration=7.0
            )

        # Saludo amistoso directo
        if re.search(r"^(hola|buenos\s+dias|buenas\s+tardes|buenas\s+noches|que\s+tal|saludos)\b", norm) and len(norm.split()) <= 4:
            return LocalRouteResult(
                handled=True,
                action_name="local:greeting",
                execution_result="Saludo local",
                spoken_response=f"¡Hola, {user_name}! Todos los subsistemas de VEX operan de forma nominal. ¿Qué orden ejecutamos?",
                expression="happy",
                icon=None,
                icon_duration=3.5
            )

        # Cumplido o agradecimiento directo
        if re.search(r"\b(gracias|muchas\s+gracias|buen\s+trabajo|excelente|eres\s+el\s+mejor|crack|genial)\b", norm) and len(norm.split()) <= 4:
            return LocalRouteResult(
                handled=True,
                action_name="local:compliment",
                execution_result="Agradecimiento local",
                spoken_response=f"Siempre a tu servicio, {user_name}. Es un auténtico placer coordinar contigo.",
                expression="happy",
                icon=None,
                icon_duration=4.0
            )

        # ---------------- 1. CONTROL MULTIMEDIA Y VOLUMEN ----------------
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
        if re.search(r"\b(pausa|pausar|pausa\s+la\s+musica|pausa\s+cancion|para\s+la\s+musica)\b", norm):
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

        # Reanudar / Continuar
        if re.search(r"\b(continua|continuar|reanuda|reanudar|reproduce|reproducir|play|dale\s+play)\b", norm):
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
        if re.search(r"\b(abre|abren|abrir|inicia|iniciar)\s+calculadora\b", norm) or norm == "calculadora":
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

        # ---------------- GESTIÓN Y ESCRITURA EN BLOC DE NOTAS ----------------
        # Detección de órdenes de escritura: "abre notas y escribe...", "abren notas y escribe...",
        # "escribe en notas...", "anota en el bloc de notas...", "crea una nota...", "toma nota de..."
        is_write_cmd = False
        raw_note_text = ""

        # Patrón 1: "abre / abren notas y escribe / anota / pon [texto]"
        m_note1 = re.search(
            r"\b(?:abre|abren|abrir|inicia|iniciar)\s+(?:el\s+)?(?:bloc\s+de\s+notas|notas)\s+y\s+(?:escribe|escribir|anota|anotar|redacta|redactar|pon|poner|apunta|apuntar|guarda|guardar)(?:\s+(.+))?$",
            norm
        )
        if m_note1:
            is_write_cmd = True
            raw_note_text = (m_note1.group(1) or "").strip()

        # Patrón 2: "escribe / anota / pon en notas / en el bloc de notas [texto]"
        if not is_write_cmd:
            m_note2 = re.search(
                r"\b(?:escribe|escribir|anota|anotar|redacta|redactar|pon|poner|apunta|apuntar|guarda|guardar)\s+(?:en\s+)?(?:el\s+)?(?:bloc\s+de\s+notas|notas)(?:\s+(.+))?$",
                norm
            )
            if m_note2:
                is_write_cmd = True
                raw_note_text = (m_note2.group(1) or "").strip()

        # Patrón 3: "crea una nota / toma nota / haz una nota [que diga / con / de] [texto]"
        if not is_write_cmd:
            m_note3 = re.search(
                r"\b(?:crea\s+una\s+nota|toma\s+nota|haz\s+una\s+nota|hazme\s+una\s+nota|nueva\s+nota)\s*(?:que\s+diga\s+|de\s+|con\s+|que\s+)?(.+)?$",
                norm
            )
            if m_note3:
                is_write_cmd = True
                raw_note_text = (m_note3.group(1) or "").strip()

        if is_write_cmd:
            # Caso A: El usuario pide escribir "lo que tú quieras", "lo que sea", etc. o no dio texto
            generic_phrases = [
                "", "lo que tu quieras", "lo que quieras", "lo que gustes",
                "lo que sea", "algo", "un saludo", "un mensaje", "lo que quieras tu",
                "lo que te de la gana"
            ]
            if raw_note_text in generic_phrases:
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
            else:
                # Caso B: El usuario dictó texto específico
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

            res = write_note(note_content, title=f"Nota_{user_name}")
            return LocalRouteResult(
                handled=True,
                action_name="write_note:notepad",
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
            if not re.search(r"\b(escribe|escribir|anota|anotar|redacta|redactar|pon|poner|apunta|apuntar)\b", norm):
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
