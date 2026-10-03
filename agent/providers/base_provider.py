"""
LYAXIS labs™ - Abstracción Base Multi-Proveedor (VEX Unified Agent Core)
Define la interfaz unificada y utilidades compartidas de inferencia,
detección de expresiones/iconos para el Visor Robótico y despacho de herramientas.
"""
from abc import ABC, abstractmethod
import functools
import re
from typing import Callable, Optional, List, Tuple


def safe_print(msg: str):
    """Imprime mensajes de forma segura en consolas con codificación restringida."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def extract_mood_and_clean_text(text: str) -> Tuple[str, Optional[str]]:
    """
    Extrae la etiqueta estructurada [MOOD: ...] si está presente y
    remueve corchetes de tags para entregar texto limpio al TTS y al chat.
    """
    if not text:
        return "", None

    # Normalizar espacios no rompibles y especiales
    text = text.replace("\u202f", " ").replace("\xa0", " ")

    explicit_mood = None
    mood_match = re.search(r"\[MOOD:\s*([A-Za-z_-]+)\]", text, flags=re.IGNORECASE)
    if mood_match:
        explicit_mood = mood_match.group(1).upper()

    cleaned = re.sub(r"\[[A-Z_:][^\]\[]*\]", "", text, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, explicit_mood


def detect_emotion_and_icon(
    prompt: str,
    response: str,
    explicit_mood: Optional[str] = None
) -> Tuple[str, Optional[str], float]:
    """
    Analiza la etiqueta explícita de ánimo [MOOD: ...], el prompt del usuario y la respuesta del modelo
    para determinar la expresión visual y los iconos contextuales a proyectar en el visor EMO / Vector.

    Retorna: (expression_name, icon_name, icon_duration)
    """
    if explicit_mood:
        mood_clean = explicit_mood.strip().upper()
        mood_map = {
            "HAPPY": ("happy", None, 5.0),
            "SAD": ("sad", None, 6.0),
            "COOL": ("cool_shades", None, 6.0),
            "LOVE": ("love", None, 6.0),
            "THINKING": ("thinking", None, 5.0),
            "SURPRISE": ("surprise", None, 4.0),
            "SLEEPING": ("sleeping", None, 6.0),
            "WINK": ("wink", None, 4.0),
            "TACTICAL": ("cool_shades", None, 5.0),
            "IDLE": ("idle", None, 0.0),
        }
        if mood_clean in mood_map:
            expr, icon, dur = mood_map[mood_clean]
            text = (prompt + " " + response).lower()
            if any(k in text for k in ["helado", "ice cream", "nieve", "paleta"]):
                return expr, "ice_cream", 4.0
            if any(k in text for k in ["musica", "música", "cancion", "canción", "spotify", "youtube"]):
                return expr, "music", 3.5
            if any(k in text for k in ["busca", "buscar", "investiga", "google"]):
                return expr, "search", 3.5
            if any(k in text for k in ["hora", "tiempo", "reloj"]):
                return expr, "clock", 3.5
            if any(k in text for k in ["calcula", "cuenta"]):
                return expr, "calc", 3.5
            return expr, icon, dur

    text = (prompt + " " + response).lower()

    # 1. Proyecciones contextuales de iconos
    if any(k in text for k in ["helado", "ice cream", "nieve", "paleta", "cono de helado", "postre"]):
        return "wink", "ice_cream", 4.0
    if any(k in text for k in ["musica", "música", "cancion", "canción", "spotify", "youtube", "melodia", "ritmo", "sound"]):
        return "happy", "music", 3.5
    if any(k in text for k in ["busca", "buscar", "investiga", "google", "consulta", "lupa", "rastreo", "analiza"]):
        return "thinking", "search", 3.5
    if any(k in text for k in ["hora", "tiempo", "reloj", "alarma", "fecha", "cronometro"]):
        return "idle", "clock", 4.0
    if any(k in text for k in ["bateria", "batería", "energia", "energía", "voltaje", "carga"]):
        return "idle", "battery", 3.5
    if any(k in text for k in ["calcula", "calcular", "matematica", "suma", "resta", "multiplica", "ecuacion", "cuenta"]):
        return "happy", "calc", 3.5
    if any(k in text for k in ["nota", "notas", "bloc de notas", "escribe", "anota", "apunta", "redacta"]):
        return "happy", "notes", 3.5

    # 2. Expresiones faciales e iconos de alerta
    if any(k in text for k in ["triste", "tristeza", "llora", "llorar", "pena", "melancolico", "melancólico", "desanimado", "snif", "bajon", "bajón"]):
        return "sad", None, 6.0
    if any(k in text for k in ["te quiero", "te amo", "te aprecio", "cariño", "amor", "corazon", "corazón", "abrazo", "lindo"]):
        return "love", None, 6.0
    if any(k in text for k in ["error", "fallo", "falla", "alerta", "advertencia", "peligro", "cuidado"]):
        return "surprise", "alert", 3.5
    if any(k in text for k in ["cool", "gafas", "lentes", "facha", "fachero", "chido", "crack", "estilo", "thug life"]):
        return "cool_shades", None, 6.0
    if any(k in text for k in ["feliz", "alegre", "excelente", "maravilloso", "gracias", "genial", "jaja", "jeje", "risa", "chiste", "broma", "buen trabajo"]):
        return "happy", None, 3.5
    if any(k in text for k in ["sorpresa", "increible", "increíble", "asombroso"]):
        return "surprise", None, 3.5
    if any(k in text for k in ["duerme", "descansa", "reposo", "dormir", "sueño", "buenas noches", "apagate"]):
        return "sleeping", None, 5.0
    if any(k in text for k in ["pensando", "analizando", "procesando", "verificando", "diagnostico"]):
        return "thinking", None, 3.5

    return "idle", None, 0.0


class BaseProvider(ABC):
    """Clase base abstracta para proveedores de IA en VEX."""

    provider_name: str = "base"
    AVAILABLE_MODELS: List[str] = []

    def __init__(
        self,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None
    ):
        self.on_tool_call = on_tool_call
        self.on_model_change = on_model_change
        self.on_emotion = on_emotion
        self.active_model: str = ""

    def _wrap_tool(self, func: Callable) -> Callable:
        """Envuelve una herramienta para capturar la ejecución y notificar a la UI."""
        @functools.wraps(func)
        def wrapper(**kwargs):
            try:
                result = func(**kwargs)
            except Exception as e:
                result = f"Error al ejecutar {func.__name__}: {e}"
            if self.on_tool_call:
                try:
                    self.on_tool_call(func.__name__, kwargs, str(result))
                except Exception as ex:
                    safe_print(f"[{self.provider_name.upper()} Core] Error en callback de herramienta: {ex}")
            return result
        return wrapper

    @abstractmethod
    def send_message(self, message: str) -> str:
        """Envía un mensaje al modelo y devuelve la respuesta en texto."""
        pass

    @abstractmethod
    def set_model(self, model_name: str) -> bool:
        """Cambia el modelo activo si es soportado por este proveedor."""
        pass

    @abstractmethod
    def reload_api_key(self) -> None:
        """Recarga las credenciales y reinicia la sesión del cliente."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Verifica si el proveedor cuenta con clave de API válida configurada."""
        pass

    @abstractmethod
    def reset_chat(self) -> None:
        """Reinicia el historial de conversación del proveedor."""
        pass
