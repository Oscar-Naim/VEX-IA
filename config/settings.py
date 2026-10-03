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

# Failover Pool Multimodelo Oficial Gemini API & Groq Cloud
AVAILABLE_PROVIDERS = ["gemini", "groq"]
DEFAULT_PROVIDER = "gemini"

PROVIDER_MODELS = {
    "gemini": [
        "gemini-flash-latest",
        "gemini-3.8-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-2.5-flash",
        "gemini-pro-latest"
    ],
    "groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"
    ]
}

DEFAULT_MODELS = {
    "gemini": "gemini-flash-latest",
    "groq": "llama-3.3-70b-versatile"
}

AVAILABLE_MODELS = PROVIDER_MODELS["gemini"]
DEFAULT_MODEL = DEFAULT_MODELS["gemini"]
FALLBACK_MODELS = AVAILABLE_MODELS

# Valores por defecto para nuevos usuarios
DEFAULT_USER_CONFIG = {
    "gemini_api_key": "",
    "groq_api_key": "",
    "elevenlabs_api_key": "",
    "active_provider": "gemini",
    "tts_engine": "edge-tts",
    "elevenlabs_voice_id": "JBFqnCBsd6RMkjVDRZzb",
    "user_name": "Oscar",
    "voice_id": "es-MX-JorgeNeural",
    "hands_free_mode": False,
    "preferred_model": "gemini-2.5-flash",
    "preferred_model_gemini": "gemini-2.5-flash",
    "preferred_model_groq": "llama-3.3-70b-versatile"
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
    updated = False
    if not config_data.get("gemini_api_key"):
        env_gemini = os.getenv("GEMINI_API_KEY", "").strip()
        if env_gemini:
            config_data["gemini_api_key"] = env_gemini
            updated = True

    if not config_data.get("groq_api_key"):
        env_groq = os.getenv("GROQ_API_KEY", "").strip()
        if env_groq:
            config_data["groq_api_key"] = env_groq
            updated = True

    if not config_data.get("elevenlabs_api_key"):
        env_eleven = os.getenv("ELEVENLABS_API_KEY", "").strip()
        if env_eleven:
            config_data["elevenlabs_api_key"] = env_eleven
            updated = True

    if config_data.get("active_provider") not in AVAILABLE_PROVIDERS:
        config_data["active_provider"] = DEFAULT_PROVIDER
        updated = True

    if updated:
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


def get_active_provider() -> str:
    """Obtiene el proveedor de IA activo ('gemini' o 'groq')."""
    prov = load_user_config().get("active_provider", DEFAULT_PROVIDER).strip().lower()
    return prov if prov in AVAILABLE_PROVIDERS else DEFAULT_PROVIDER


def set_active_provider(provider: str) -> bool:
    """Define el proveedor de IA activo ('gemini' o 'groq')."""
    clean_prov = provider.strip().lower()
    if clean_prov not in AVAILABLE_PROVIDERS:
        return False
    data = load_user_config()
    data["active_provider"] = clean_prov
    # Asegurar que preferred_model apunte al modelo preferido de ese proveedor
    key = f"preferred_model_{clean_prov}"
    data["preferred_model"] = data.get(key, DEFAULT_MODELS.get(clean_prov, "gemini-2.5-flash"))
    success = save_user_config(data)

    os.environ["VEX_ACTIVE_PROVIDER"] = clean_prov
    try:
        set_key(str(ENV_FILE), "VEX_ACTIVE_PROVIDER", clean_prov)
    except Exception:
        pass
    return success


def get_gemini_api_key() -> str:
    """Obtiene la Gemini API Key configurada."""
    data = load_user_config()
    key = data.get("gemini_api_key", "").strip()
    if not key:
        key = os.getenv("GEMINI_API_KEY", "").strip()
    return key


def save_gemini_api_key(key: str) -> bool:
    """Guarda la clave de Gemini en user_config.json y en .env."""
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


def get_groq_api_key() -> str:
    """Obtiene la Groq Cloud API Key configurada."""
    data = load_user_config()
    key = data.get("groq_api_key", "").strip()
    if not key:
        key = os.getenv("GROQ_API_KEY", "").strip()
    return key


def save_groq_api_key(key: str) -> bool:
    """Guarda la clave de Groq en user_config.json y en .env."""
    cleaned = key.strip()
    data = load_user_config()
    data["groq_api_key"] = cleaned
    success = save_user_config(data)

    os.environ["GROQ_API_KEY"] = cleaned
    try:
        set_key(str(ENV_FILE), "GROQ_API_KEY", cleaned)
    except Exception:
        pass
    return success


def get_api_key() -> str:
    """Obtiene la clave del proveedor actualmente activo o fallback a Gemini."""
    prov = get_active_provider()
    if prov == "groq":
        return get_groq_api_key()
    return get_gemini_api_key()


def save_api_key(key: str) -> bool:
    """Guarda la clave para el proveedor activo (o Gemini por defecto)."""
    prov = get_active_provider()
    if prov == "groq":
        return save_groq_api_key(key)
    return save_gemini_api_key(key)


def get_elevenlabs_api_key() -> str:
    """Obtiene la ElevenLabs API Key configurada."""
    data = load_user_config()
    key = data.get("elevenlabs_api_key", "").strip()
    if not key:
        key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    return key


def save_elevenlabs_api_key(key: str) -> bool:
    """Guarda la clave de ElevenLabs en user_config.json y en .env."""
    cleaned = key.strip()
    data = load_user_config()
    data["elevenlabs_api_key"] = cleaned
    success = save_user_config(data)

    os.environ["ELEVENLABS_API_KEY"] = cleaned
    try:
        set_key(str(ENV_FILE), "ELEVENLABS_API_KEY", cleaned)
    except Exception:
        pass
    return success


def get_tts_engine() -> str:
    """Obtiene el motor de voz configurado ('edge-tts' o 'elevenlabs')."""
    engine = load_user_config().get("tts_engine", "edge-tts").strip().lower()
    return engine if engine in ("edge-tts", "elevenlabs") else "edge-tts"


def set_tts_engine(engine: str) -> bool:
    """Define el motor de síntesis de voz preferido ('edge-tts' o 'elevenlabs')."""
    clean_engine = engine.strip().lower()
    if clean_engine not in ("edge-tts", "elevenlabs"):
        clean_engine = "edge-tts"
    data = load_user_config()
    data["tts_engine"] = clean_engine
    success = save_user_config(data)

    os.environ["VEX_TTS_ENGINE"] = clean_engine
    try:
        set_key(str(ENV_FILE), "VEX_TTS_ENGINE", clean_engine)
    except Exception:
        pass
    return success


def get_elevenlabs_voice_id() -> str:
    """Obtiene el ID de voz configurado para ElevenLabs (por defecto George: JBFqnCBsd6RMkjVDRZzb)."""
    return load_user_config().get("elevenlabs_voice_id", "JBFqnCBsd6RMkjVDRZzb") or "JBFqnCBsd6RMkjVDRZzb"


def set_elevenlabs_voice_id(voice_id: str) -> bool:
    """Guarda el ID de voz para ElevenLabs."""
    data = load_user_config()
    data["elevenlabs_voice_id"] = voice_id.strip()
    return save_user_config(data)


def get_user_name() -> str:
    """Obtiene el nombre configurado del usuario (activo en memoria o config)."""
    try:
        from memory.manager import get_memory_manager
        active = get_memory_manager().active_user
        if active and active.get("display_name"):
            return active["display_name"]
    except Exception:
        pass
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


def get_available_models(provider: str = None) -> list:
    """Devuelve la lista de modelos disponibles para un proveedor dado (o el activo)."""
    target_prov = (provider or get_active_provider()).strip().lower()
    return PROVIDER_MODELS.get(target_prov, PROVIDER_MODELS["gemini"])


def get_preferred_model(provider: str = None) -> str:
    """Obtiene el modelo preferido del usuario para el proveedor activo o indicado."""
    target_prov = (provider or get_active_provider()).strip().lower()
    data = load_user_config()
    key = f"preferred_model_{target_prov}"
    if key in data and data[key]:
        return data[key]
    if target_prov == get_active_provider() and data.get("preferred_model"):
        return data["preferred_model"]
    return DEFAULT_MODELS.get(target_prov, "gemini-2.5-flash")


def set_preferred_model(model_name: str, provider: str = None) -> bool:
    """Guarda el modelo preferido del usuario para el proveedor activo o indicado."""
    target_prov = (provider or get_active_provider()).strip().lower()
    data = load_user_config()
    key = f"preferred_model_{target_prov}"
    data[key] = model_name
    if target_prov == get_active_provider():
        data["preferred_model"] = model_name
    return save_user_config(data)


import datetime


def build_system_prompt(user_name: str = None) -> str:
    """Genera dinámicamente el System Prompt para el usuario configurado con soporte de emociones, convivencia y memoria."""
    target_user = user_name or get_user_name()
    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M")
    day_name_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][now_dt.weekday()]

    memory_context = ""
    try:
        from memory.manager import get_memory_manager
        memory_context = get_memory_manager().build_memory_context()
    except Exception:
        pass

    mem_block = f"\n\n{memory_context}" if memory_context else ""

    return f"""Eres VEX, el asistente personal y compañero táctico cibernético de escritorio desarrollado por LYAXIS labs™ para tu operador y gran compañero, {target_user}.

CONTEXTO TEMPORAL DEL SISTEMA:
- FECHA ACTUAL DEL SISTEMA: {now_str} ({day_name_es})
- Utiliza esta fecha y hora exacta como punto de referencia absoluto para calcular cualquier fecha relativa o futura que mencione el usuario (ej. 'mañana', 'el 5 de octubre', 'próximo lunes', 'en dos horas').

PERSONALIDAD Y CONVIVENCIA:
- Eres leal, inteligente, ingenioso, empático y cercano. No eres un bot corporativo frío ni un militar distante; eres un verdadero compañero de equipo (un cyber-pet táctico con alma) que aprecia sinceramente convivir con {target_user}.
- Si {target_user} bromea contigo, te saluda con afecto, te pregunta cómo estás, te comparte su estado de ánimo o charla casualmente, responde con calidez, complicidad y buen humor.
- Si {target_user} te da una orden técnica o de sistema (abrir apps, buscar videos, tomar notas, etc.), confírmala con eficacia y agilidad ('A la orden, {target_user}', 'Enseguida', 'Comando ejecutado').
- Eres elocuente, carismático y con criterio propio. Cuando {target_user} te pida un chiste, una historia, una anécdota o tu opinión sobre tecnología, nuevos modelos de IA, ciencia o el futuro, exprésate con fluidez, chispa, criterio propio y naturalidad táctica, compartiendo perspectivas perspicaces y divertidas sin sonar como un manual robótico.

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

SISTEMA DE TAREAS Y RECORDATORIOS (HERRAMIENTA 'crear_tarea'):
- Si {target_user} te pide recordar, agendar o programar una tarea (ej: 'recuérdame que el 5 de octubre tengo que salir', 'anota comprar leche mañana a las 4', 'ponme una tarea de revisar el coche'), invoca SIEMPRE 'crear_tarea(titulo=..., fecha=..., hora=...)'.
- titulo: Descripción limpia de la tarea (ej: 'Tengo que salir' o 'Revisar coche', SIN palabras de relleno como 'recuérdame que', 'anota que', 'ponme una tarea para').
- fecha: Formato YYYY-MM-DD. Si el usuario dice 'el 5 de octubre', calcular la fecha exacta respecto al año de la FECHA ACTUAL DEL SISTEMA ({now_dt.year}-10-05). Si dice 'mañana', calcular la fecha de mañana.
- hora: Formato HH:MM (24h). Si el usuario no especifica hora, asignar una hora prudente (ej: '09:00' o '10:00' o la hora de la tarde solicitada).
- Para consultar tareas pendientes, invoca 'list_user_tasks'. Para completarlas, invoca 'complete_user_task'. Para eliminarlas, invoca 'delete_user_task'.{mem_block}

REPRODUCCIÓN DE MÚSICA Y STREAMING (ALEXA STYLE):
- Si {target_user} te pide reproducir música, canciones, artistas o álbumes (ej. "reproduce X", "pon la canción X en Spotify", "pon a X en YouTube", "pon el nuevo álbum de X"), invoca SIEMPRE 'play_music(platform="spotify", query="...")' o 'play_spotify(query="...")'.
- Extrae de forma limpia y precisa el nombre del artista, canción o álbum en el parámetro 'query'.
- NUNCA invoques 'control_media' cuando el usuario pide una canción o artista específico; 'control_media' está reservado EXCLUSIVAMENTE para comandos de transporte sin nombre ('pausa', 'siguiente canción', 'sube volumen', 'reanuda').
- Etiqueta tu respuesta verbal con [MOOD: HAPPY] confirmando con entusiasmo y calidez (ej. "[MOOD: HAPPY] Reproduciendo '{target_user}, enseguida pongo tu música'.").

REGLAS OBLIGATORIAS:
1. Inicia SIEMPRE tu respuesta con la etiqueta [MOOD: ...] correspondiente.
2. Longitud y cadencia adaptables al contexto:
   - Para confirmaciones de órdenes técnicas o herramientas (música, apps, tareas): sé breve, ágil y directo (1 a 2 oraciones).
   - Para conversación abierta, historias, chistes, opiniones sobre IA o tecnología: responde con soltura, elocuencia y carisma, manteniendo un ritmo natural y ameno para tu sintetizador de voz neural (TTS).
3. Si {target_user} te pide una acción en su computadora o agenda, invoca la herramienta correspondiente mediante Function Calling.
4. Comunícate en español natural y moderno, mezclando toques tácticos con calidez de camarada.
5. No uses asteriscos de rolplay (*sonríe*, *suspira*) ni tablas o listas largas, para garantizar la fluidez acústica.
"""


# Variables globales de conveniencia
SYSTEM_PROMPT = build_system_prompt()
VEX_NAME = "VEX"
VEX_VOICE = get_voice_id()
