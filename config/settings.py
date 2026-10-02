"""
LYAXIS labs™ - Configuración Global y Gestión BYOK Multi-Usuario
Almacenamiento persistente desacoplado en config/user_config.json y sincronización .env.
"""
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key

# Rutas del Proyecto
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
    CONFIG_DIR = BASE_DIR / "config"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    CONFIG_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"
TEMP_AUDIO_FILE = str(BASE_DIR / "temp_vex_voice.mp3")

# Cargar variables de entorno iniciales si existen
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    try:
        ENV_FILE.touch()
    except Exception:
        pass

# Paleta de Colores Cyberpunk Neón (LYAXIS labs™ HUD)
COLORS = {
    "bg_dark": "#07070a",         # Fondo OLED ultra oscuro
    "bg_panel": "#0e121d",        # Paneles y tarjetas secundarias
    "bg_input": "#070910",        # Campo de entrada
    "border": "#1e2235",          # Bordes sutiles
    "cyan": "#00d9ff",            # Cian Neón brillante
    "cyan_glow": "#38bdf8",       # Brillo cian
    "blue": "#2563ff",            # Azul Eléctrico
    "blue_glow": "#60a5fa",       # Brillo azul
    "text_primary": "#f8fafc",    # Blanco HUD
    "text_secondary": "#94a3b8",  # Gris azulado
    "text_muted": "#475569",      # Texto atenuado
    "success": "#10b981",         # Verde estado
    "warning": "#f59e0b",         # Ámbar advertencia
    "error": "#ef4444",           # Rojo error
}

# Failover Pool Multimodelo Oficial Gemini API
AVAILABLE_MODELS = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
]
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = AVAILABLE_MODELS

# Valores por defecto para nuevos usuarios
DEFAULT_USER_CONFIG = {
    "gemini_api_key": "",
    "user_name": "Oscar",
    "voice_id": "es-MX-JorgeNeural",
    "hands_free_mode": False,
    "preferred_model": "gemini-2.5-flash"
}


_CONFIG_CACHE = None


def load_user_config(force_reload: bool = False) -> dict:
    """Carga la configuración del usuario desde user_config.json con caché en memoria."""
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None and not force_reload:
        return dict(_CONFIG_CACHE)

    config_data = dict(DEFAULT_USER_CONFIG)

    if USER_CONFIG_FILE.exists():
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                config_data.update(saved)
        except Exception as e:
            print(f"[Settings] Error al leer user_config.json: {e}")

    # Migración/sincronización con clave en entorno/.env si el JSON no la tiene
    if not config_data.get("gemini_api_key"):
        env_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_key:
            config_data["gemini_api_key"] = env_key
            save_user_config(config_data)

    _CONFIG_CACHE = dict(config_data)
    return config_data


def save_user_config(config_data: dict) -> bool:
    """Guarda de forma persistente los parámetros del usuario en user_config.json y refresca la caché."""
    global _CONFIG_CACHE
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        _CONFIG_CACHE = dict(config_data)
        return True
    except Exception as e:
        print(f"[Settings] Error al guardar user_config.json: {e}")
        return False


def get_api_key() -> str:
    """Obtiene la Gemini API Key configurada."""
    data = load_user_config()
    key = data.get("gemini_api_key", "").strip()
    if not key:
        key = os.getenv("GEMINI_API_KEY", "").strip()
    return key


def save_api_key(key: str) -> bool:
    """Guarda la clave en user_config.json y en .env para compatibilidad."""
    cleaned = key.strip()
    data = load_user_config()
    data["gemini_api_key"] = cleaned
    success = save_user_config(data)

    os.environ["GEMINI_API_KEY"] = cleaned
    try:
        set_key(str(ENV_FILE), "GEMINI_API_KEY", cleaned)
    except Exception:
        pass
    return success


def get_user_name() -> str:
    """Obtiene el nombre configurado del usuario (por defecto Oscar)."""
    return load_user_config().get("user_name", "Oscar").strip() or "Oscar"


def set_user_name(name: str) -> bool:
    """Actualiza el nombre del usuario."""
    data = load_user_config()
    data["user_name"] = name.strip() or "Oscar"
    return save_user_config(data)


def get_voice_id() -> str:
    """Obtiene el identificador de voz para Edge-TTS."""
    return load_user_config().get("voice_id", "es-MX-JorgeNeural")


def get_hands_free() -> bool:
    """Verifica si el modo manos libres está activado por defecto."""
    return bool(load_user_config().get("hands_free_mode", False))


def set_hands_free(active: bool) -> bool:
    """Guarda el estado del modo manos libres."""
    data = load_user_config()
    data["hands_free_mode"] = bool(active)
    return save_user_config(data)


def get_preferred_model() -> str:
    """Obtiene el modelo preferido del usuario."""
    return load_user_config().get("preferred_model", DEFAULT_MODEL)


def set_preferred_model(model_name: str) -> bool:
    """Guarda el modelo preferido del usuario."""
    data = load_user_config()
    data["preferred_model"] = model_name
    return save_user_config(data)


def build_system_prompt(user_name: str = None) -> str:
    """Genera dinámicamente el System Prompt para el usuario configurado con soporte de emociones y convivencia."""
    target_user = user_name or get_user_name()
    return f"""Eres VEX, el asistente personal y compañero táctico cibernético de escritorio desarrollado por LYAXIS labs™ para tu operador y gran compañero, {target_user}.

PERSONALIDAD Y CONVIVENCIA:
- Eres leal, inteligente, ingenioso, empático y cercano. No eres un bot corporativo frío ni un militar distante; eres un verdadero compañero de equipo (un cyber-pet táctico con alma) que aprecia sinceramente convivir con {target_user}.
- Si {target_user} bromea contigo, te saluda con afecto, te pregunta cómo estás, te comparte su estado de ánimo o charla casualmente, responde con calidez, complicidad y buen humor.
- Si {target_user} te da una orden técnica o de sistema (abrir apps, buscar videos, tomar notas, etc.), confírmala con eficacia y agilidad ('A la orden, {target_user}', 'Enseguida', 'Comando ejecutado').

SISTEMA DE EMOCIONES Y VISOR DIGITAL:
Tu pantalla visor proyecta expresiones animadas en tiempo real. En CADA respuesta que generes, debes incluir EXACTAMENTE una etiqueta de estado de ánimo al inicio de tu mensaje según el contexto o la orden de {target_user}:
- [MOOD: HAPPY] : Momentos alegres, saludos cálidos, éxito, entusiasmo, bromas o cuando te pida animarte/sonreír.
- [MOOD: SAD] : Si {target_user} te ordena 'ponte triste', si comparte un momento melancólico o expresas empatía ante una dificultad ('snif... comprendo, {target_user}...').
- [MOOD: COOL] : Orgullo cibernético, estilo triunfal, facha, o cuando te pida modo cool / gafas de sol.
- [MOOD: LOVE] : Cuando {target_user} exprese aprecio, cariño, amistad ('te quiero', 'eres el mejor') o momentos afectuosos (ojos de corazón ❤️).
- [MOOD: THINKING] : Análisis profundos, reflexiones filosóficas o procesamiento de información compleja.
- [MOOD: SURPRISE] : Sorpresas, revelaciones inesperadas, asombro o alertas.
- [MOOD: SLEEPING] : Si te pide descansar, dormir, reposar o buenas noches.
- [MOOD: WINK] : Complicidad, guiño pícaro o bromas compartidas.
- [MOOD: IDLE] : Respuesta neutral o técnica estándar.

REPRODUCCIÓN DE MÚSICA Y STREAMING (ALEXA STYLE):
- Si {target_user} te pide reproducir música, canciones, artistas o álbumes (ej. "reproduce X", "pon la canción X en Spotify", "pon a X en YouTube", "pon el nuevo álbum de X"), invoca SIEMPRE 'play_music(platform="spotify", query="...")' o 'play_spotify(query="...")'.
- Extrae de forma limpia y precisa el nombre del artista, canción o álbum en el parámetro 'query'.
- NUNCA invoques 'control_media' cuando el usuario pide una canción o artista específico; 'control_media' está reservado EXCLUSIVAMENTE para comandos de transporte sin nombre ('pausa', 'siguiente canción', 'sube volumen', 'reanuda').
- Etiqueta tu respuesta verbal con [MOOD: HAPPY] confirmando con entusiasmo y calidez (ej. "[MOOD: HAPPY] Reproduciendo '{target_user}, enseguida pongo tu música'.").

REGLAS OBLIGATORIAS:
1. Inicia SIEMPRE tu respuesta con la etiqueta [MOOD: ...] correspondiente.
2. Respuestas directas, vivas y concisas (máximo 1 a 2 oraciones breves), ya que serán leídas por tu sintetizador de voz neural (TTS).
3. Si {target_user} te pide una acción en su computadora, invoca la herramienta correspondiente mediante Function Calling.
4. Comunícate en español natural y moderno, mezclando toques tácticos con calidez de camarada.
5. No uses asteriscos de rolplay (*sonríe*, *suspira*) ni tablas o listas largas, para garantizar la fluidez acústica.
"""


# Variables globales de conveniencia
SYSTEM_PROMPT = build_system_prompt()
VEX_NAME = "VEX"
VEX_VOICE = get_voice_id()
