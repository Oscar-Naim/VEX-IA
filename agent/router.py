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
    system_info
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+spotify\b", norm) or norm in ["spotify", "musica"]:
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+calculadora\b", norm) or norm == "calculadora":
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

        # Abrir Bloc de Notas
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+(el\s+)?(bloc\s+de\s+notas|notas)\b", norm) or norm in ["bloc de notas", "notas"]:
            res = launch_application("notepad.exe")
            return LocalRouteResult(
                handled=True,
                action_name="launch_application:notepad",
                execution_result=res,
                spoken_response="Abriendo Bloc de notas.",
                expression="happy",
                icon=None,
                icon_duration=2.5
            )

        # Abrir Navegador
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+(el\s+)?(navegador|google|chrome)\b", norm):
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+discord\b", norm) or norm == "discord":
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+(visual\s+studio|vscode|code)\b", norm):
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+administrador\s+de\s+tareas\b", norm):
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
        if re.search(r"\b(abre|abrir|inicia|iniciar)\s+(configuracion|ajustes)\b", norm):
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
