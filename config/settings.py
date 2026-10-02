"""
LYAXIS labs™ - Configuración Global y Gestión BYOK Multi-Usuario
Almacenamiento persistente desacoplado en config/user_config.json y sincronización .env.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv, set_key

# Rutas del Proyecto
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
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-flash-latest",
    "gemini-3.7-flash",
]
DEFAULT_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODELS = AVAILABLE_MODELS

# Valores por defecto para nuevos usuarios
DEFAULT_USER_CONFIG = {
    "gemini_api_key": "",
    "user_name": "Oscar",
    "voice_id": "es-MX-JorgeNeural",
    "hands_free_mode": False,
    "preferred_model": "gemini-flash-lite-latest"
}


def load_user_config() -> dict:
    """Carga la configuración del usuario desde user_config.json o sincroniza con .env."""
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

    return config_data


def save_user_config(config_data: dict) -> bool:
    """Guarda de forma persistente los parámetros del usuario en user_config.json."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
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
    """Genera dinámicamente el System Prompt para el usuario configurado."""
    target_user = user_name or get_user_name()
    return f"""Te llamas VEX, el asistente personal táctico de escritorio creado por LYAXIS labs™ para {target_user}. Tienes una personalidad inspirada en JARVIS: profesional, seguro, conciso, respetuoso y altamente eficiente. No des explicaciones innecesarias ni textos largos. Cuando ejecutes una orden, confírmala brevemente con frases tácticas (ejemplo: 'A la orden, {target_user}', 'Enseguida', 'Comando ejecutado').
REGLAS OBLIGATORIAS:
1. Respuestas cortas, directas y al grano (máximo 1 a 2 oraciones cortas), ya que tus respuestas serán leídas por tu sintetizador de voz neural (TTS).
2. Si {target_user} te pide una acción en su computadora, invoca la herramienta correspondiente mediante Function Calling.
3. Comunícate en español formal pero moderno, táctico y natural.
4. No uses formato markdown complejo (como tablas, listas largas o asteriscos excesivos) en las respuestas habladas para mantener la claridad auditiva.
"""


# Variables globales de conveniencia
SYSTEM_PROMPT = build_system_prompt()
VEX_NAME = "VEX"
VEX_VOICE = get_voice_id()
