"""
LYAXIS labs™ - Proveedor Groq Cloud (VEX Core - Capa 1)
Inferencia ultra-rápida (Llama 3.3 70B & Llama 3.1 8B Instant) mediante la librería oficial `groq`.
Soporte de Visión Multimodal con `llama-3.2-11b-vision-preview` y Auto-Vision Dispatcher
con fallback transparente hacia Google Gemini Flash ante 404 o indisponibilidad.
"""
import os
import re
import json
import time
import base64
import mimetypes
import threading
from typing import Callable, Optional, List, Dict, Any

from groq import (
    Groq,
    RateLimitError,
    AuthenticationError,
    APIConnectionError,
    APIStatusError,
    NotFoundError
)

import config
from agent.providers.base_provider import (
    BaseProvider,
    safe_print,
    detect_emotion_and_icon,
    extract_mood_and_clean_text
)
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
from tools.memory_tools import (
    crear_tarea,
    add_user_task,
    set_user_routine,
    remember_fact,
    list_user_tasks,
    complete_user_task,
    delete_user_task
)


class GroqQuotaError(Exception):
    """Excepción lanzada cuando la cuota de la API de Groq (429) se encuentra agotada."""
    pass


# Mapeo oficial de herramientas locales de VEX al esquema estándar de Groq / OpenAI
GROQ_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Reproduce música, canciones o artistas en Spotify o YouTube (estilo Alexa).",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["spotify", "youtube"],
                        "description": "Plataforma seleccionada (por defecto 'spotify')."
                    },
                    "query": {
                        "type": "string",
                        "description": "Nombre del artista, canción o álbum a reproducir."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_spotify",
            "description": "Busca y reproduce un artista, canción o álbum directamente en la aplicación Spotify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nombre de la canción, artista o álbum."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": "Busca y reproduce directamente un video musical o canción en YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Nombre de la canción o video a reproducir."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_youtube",
            "description": "Abre el navegador web y busca directamente un video o contenido en YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Término de búsqueda, artista o tema del video."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Abre cualquier dirección web o página de Internet en el navegador predeterminado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Dirección web o dominio (ej. 'google.com', 'https://github.com')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "launch_application",
            "description": "Abre una aplicación instalada en la computadora (Spotify, Discord, Calculadora, Navegador, etc.). IMPORTANTE: Para redactar notas usa 'write_note'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Nombre de la aplicación a ejecutar en la computadora."
                    }
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "control_media",
            "description": "Controla el sistema multimedia y volumen del equipo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["volume_up", "volume_down", "mute", "play_pause", "next", "prev"],
                        "description": "Acción multimedia solicitada."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_info",
            "description": "Reporta el estado actual del sistema: fecha, hora exacta, nivel de batería, uso de CPU y memoria RAM.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "Crea, redacta y abre una nota de texto en el Bloc de Notas (Notepad) con el contenido indicado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "El texto o mensaje completo que debe redactarse y guardarse en la nota."
                    },
                    "title": {
                        "type": "string",
                        "description": "Título o nombre del archivo de nota (ej. 'Nota_Oscar', 'Tareas')."
                    }
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "crear_tarea",
            "description": "Programa y registra una tarea o recordatorio en la agenda del usuario con fecha y hora específicas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo": {
                        "type": "string",
                        "description": "Descripción limpia de la tarea (ej: 'Tengo que salir' o 'Revisar coche', SIN palabras de relleno como 'recuérdame que')."
                    },
                    "fecha": {
                        "type": "string",
                        "description": "Formato YYYY-MM-DD. Si el usuario dice 'el 5 de octubre', calcular la fecha exacta respecto al año actual. Si dice 'mañana', calcular fecha de mañana."
                    },
                    "hora": {
                        "type": "string",
                        "description": "Formato HH:MM (24h). Si el usuario no especifica hora, asignar una hora prudente (ej: '09:00' o '10:00' o la hora de la tarde solicitada)."
                    }
                },
                "required": ["titulo", "fecha"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_user_task",
            "description": "Programa y registra una tarea o pendiente en la memoria del usuario actual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Título o descripción de la tarea a realizar."
                    },
                    "date": {
                        "type": "string",
                        "description": "Fecha en formato 'YYYY-MM-DD' o 'hoy' / 'mañana'. Opcional."
                    },
                    "time": {
                        "type": "string",
                        "description": "Hora de la tarea (ej. '15:00', '16:30'). Opcional."
                    }
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_user_routine",
            "description": "Registra o actualiza una rutina diaria o hábito para el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nombre de la rutina (ej. 'Rutina matutina', 'Entrenamiento')."
                    },
                    "description": {
                        "type": "string",
                        "description": "Detalle de los pasos o acciones de la rutina."
                    },
                    "time": {
                        "type": "string",
                        "description": "Hora programada para la rutina (ej. '08:00'). Opcional."
                    }
                },
                "required": ["name", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Memoriza y guarda una preferencia o dato relevante del usuario para personalizar respuestas futuras.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string",
                        "description": "Concepto o clave a recordar (ej. 'preferencia_musica', 'lenguaje_favorito', 'ciudad')."
                    },
                    "value": {
                        "type": "string",
                        "description": "Detalle o valor a recordar."
                    }
                },
                "required": ["key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_user_tasks",
            "description": "Consulta y lista las tareas y pendientes del usuario actual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Filtro de fecha: 'today'/'hoy' para hoy, 'all'/'todas' para todas las tareas, o 'YYYY-MM-DD'."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "complete_user_task",
            "description": "Marca una tarea como completada en la memoria del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id_or_title": {
                        "type": "string",
                        "description": "ID o fragmento del título de la tarea a marcar como completada."
                    }
                },
                "required": ["task_id_or_title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_user_task",
            "description": "Elimina permanentemente una tarea o pendiente de la lista del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id_or_title": {
                        "type": "string",
                        "description": "ID o fragmento del título de la tarea a eliminar."
                    }
                },
                "required": ["task_id_or_title"]
            }
        }
    }
]


class GroqProvider(BaseProvider):
    provider_name: str = "groq"
    AVAILABLE_MODELS: List[str] = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b"
    ]

    def __init__(
        self,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None
    ):
        super().__init__(on_tool_call, on_model_change, on_emotion)
        self.api_key: str = config.get_groq_api_key()
        self.client: Optional[Groq] = None
        self.active_model: str = "llama-3.3-70b-versatile"
        self.model: str = self.active_model

        self._send_lock = threading.Lock()
        self.last_api_call_time: float = 0.0
        self.min_request_interval: float = 1.0  # Groq es ultra veloz
        self.max_history_turns: int = 4         # Últimos 4 intercambios (8 mensajes)
        self.history: List[Dict[str, Any]] = []

        # Registro de funciones locales ejecutables
        self.local_functions: Dict[str, Callable] = {
            "play_music": self._wrap_tool(play_music),
            "play_spotify": self._wrap_tool(play_spotify),
            "play_youtube": self._wrap_tool(play_youtube),
            "search_youtube": self._wrap_tool(search_youtube),
            "open_url": self._wrap_tool(open_url),
            "launch_application": self._wrap_tool(launch_application),
            "control_media": self._wrap_tool(control_media),
            "system_info": self._wrap_tool(system_info),
            "write_note": self._wrap_tool(write_note),
            "crear_tarea": self._wrap_tool(crear_tarea),
            "add_user_task": self._wrap_tool(add_user_task),
            "complete_user_task": self._wrap_tool(complete_user_task),
            "delete_user_task": self._wrap_tool(delete_user_task),
            "set_user_routine": self._wrap_tool(set_user_routine),
            "remember_fact": self._wrap_tool(remember_fact),
            "list_user_tasks": self._wrap_tool(list_user_tasks),
        }

        self.init_groq()

    def init_groq(self):
        """Inicializa el cliente oficial de Groq de forma limpia sin duplicar rutas."""
        self.api_key = config.get_groq_api_key()
        if not self.api_key or self.api_key.strip() == "":
            self.client = None
            return

        try:
            # Cliente oficial Groq: el SDK ya utiliza https://api.groq.com/openai/v1 por defecto
            self.client = Groq(api_key=self.api_key)
            self.active_model = "llama-3.3-70b-versatile"
            self.model = self.active_model
            config.set_preferred_model(self.active_model, "groq")
            safe_print(f"[Groq Core] Cliente oficial Groq inicializado con modelo: {self.active_model}")
        except Exception as e:
            safe_print(f"[Groq Core] Inicialización de cliente en espera: {e}")
            self.client = None

    def _initialize_client(self):
        self.init_groq()

    def reload_api_key(self):
        self.init_groq()

    def is_configured(self) -> bool:
        return self.client is not None and bool(config.get_groq_api_key())

    def set_model(self, model_name: str) -> bool:
        if model_name in self.AVAILABLE_MODELS:
            self.active_model = model_name
            config.set_preferred_model(model_name, "groq")
            safe_print(f"[Groq Core] Canal neuronal vinculado a: {model_name}")
            return True
        return False

    def reset_chat(self):
        self.history = []

    def _enforce_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_api_call_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_api_call_time = time.time()

    def _sanitize_groq_history(self) -> List[Dict[str, Any]]:
        system_msg = {
            "role": "system",
            "content": config.build_system_prompt()
        }
        dialog = [m for m in self.history if m.get("role") in ("user", "assistant", "tool")]
        max_msgs = self.max_history_turns * 2
        if len(dialog) > max_msgs:
            cut_idx = len(dialog) - max_msgs
            while cut_idx < len(dialog):
                if dialog[cut_idx].get("role") == "user":
                    break
                cut_idx += 1
            dialog = dialog[cut_idx:]

        return [system_msg] + dialog

    def send_vision_message(self, message: str, image_path: str) -> str:
        """
        Enrutamiento Inteligente de Visión (Auto-Vision Dispatcher):
        1. Intenta procesar con el modelo de visión de Groq: `llama-3.2-11b-vision-preview`.
        2. Si Groq da error 404, modelo no disponible o cuota, conmuta automáticamente
           a Google Gemini Flash (`gemini-2.5-flash`) para análisis transparente.
        """
        if not os.path.exists(image_path):
            return f"⚠️ No se encontró la imagen en la ruta especificada: {image_path}"

        clean_text = re.sub(r"\[(Imagen|Adjunto|Archivo):.*?\]", "", message).strip()
        if not clean_text:
            clean_text = "¿Qué ves en esta imagen? Describe detalladamente su contenido con el estilo táctico de VEX."

        # Intento 1: Groq Vision (llama-3.2-11b-vision-preview)
        if self.is_configured():
            try:
                mime_type, _ = mimetypes.guess_type(image_path)
                if not mime_type or not mime_type.startswith("image/"):
                    mime_type = "image/png"

                with open(image_path, "rb") as f:
                    b64_image = base64.b64encode(f.read()).decode("utf-8")

                data_url = f"data:{mime_type};base64,{b64_image}"
                safe_print(f"[Groq Vision] 👁 Analizando imagen con llama-3.2-11b-vision-preview...")

                self._enforce_rate_limit()
                # En modelos de visión de Groq NO se pasan herramientas (tools) para evitar error 400/404
                completion = self.client.chat.completions.create(
                    model="llama-3.2-11b-vision-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": config.build_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": clean_text},
                                {"type": "image_url", "image_url": {"url": data_url}}
                            ]
                        }
                    ],
                    temperature=0.3,
                    max_tokens=300
                )
                raw_reply = completion.choices[0].message.content or ""
                reply, explicit_mood = extract_mood_and_clean_text(raw_reply)
                if reply:
                    expr, icon, dur = detect_emotion_and_icon(clean_text, reply, explicit_mood=explicit_mood or "CURIOUS")
                    if self.on_emotion:
                        try:
                            self.on_emotion(expr, icon or "search", dur)
                        except Exception:
                            pass
                    return reply
            except Exception as groq_err:
                safe_print(f"[Groq Vision] Error en llama-3.2-11b-vision-preview ({groq_err}). Activando failover transparente a Gemini...")

        # Intento 2: Fallback transparente hacia Gemini Flash Multimodal
        gemini_key = config.get_gemini_api_key()
        if gemini_key:
            try:
                from agent.providers.gemini_provider import GeminiProvider
                gemini_prov = GeminiProvider(on_emotion=self.on_emotion)
                safe_print(f"[Auto-Vision Dispatcher] ✦ Despachando imagen a Gemini Flash...")
                return gemini_prov.send_vision_message(message, image_path)
            except Exception as gem_err:
                safe_print(f"[Auto-Vision Dispatcher] Error en fallback de Gemini: {gem_err}")

        return "VEX: No se pudo completar el análisis visual. Por favor verifica que tu API Key de Gemini o Groq tenga acceso a modelos de visión."

    def send_message(self, message: str, image_path: Optional[str] = None) -> str:
        with self._send_lock:
            return self._send_message_locked(message, image_path=image_path)

    def _send_message_locked(self, message: str, image_path: Optional[str] = None) -> str:
        # Detectar si hay imagen adjunta (parámetro o tag [Imagen: /path])
        detected_img = image_path
        if not detected_img:
            m = re.search(r"\[(?:Imagen|Adjunto):\s*([^\]]+)\]", message)
            if m:
                candidate = m.group(1).strip()
                if os.path.exists(candidate) and any(candidate.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
                    detected_img = candidate

        if detected_img:
            return self.send_vision_message(message, detected_img)

        if not self.is_configured():
            return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

        self._enforce_rate_limit()

        # Añadir mensaje del usuario al historial
        self.history.append({"role": "user", "content": message})
        messages = self._sanitize_groq_history()

        # Modelo inicial preferido
        if not self.active_model or self.active_model not in self.AVAILABLE_MODELS:
            self.active_model = "llama-3.3-70b-versatile"

        max_retries = len(self.AVAILABLE_MODELS) - 1
        retries = 0
        tried_models = [self.active_model]
        final_reply = ""
        explicit_mood = None

        while True:
            try:
                chat_completion = self.client.chat.completions.create(
                    model=self.active_model,
                    messages=messages,
                    tools=GROQ_TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=200,
                    frequency_penalty=0.5,
                )
            except AuthenticationError as e:
                safe_print(f"[Groq Core] Clave API rechazada por Groq Cloud: {e}")
                return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."
            except APIConnectionError as e:
                safe_print(f"[Groq Core] Error de conexión de red con Groq Cloud: {e}")
                return "Error de enlace con los satélites de Groq Cloud. Revisa tu conexión a internet."
            except Exception as e:
                is_quota = isinstance(e, RateLimitError)
                status = getattr(e, "status_code", 404 if isinstance(e, NotFoundError) else None)
                if status == 429:
                    is_quota = True

                err_str = str(e).lower()
                is_recoverable = (
                    is_quota
                    or status in (404, 500, 502, 503, 504)
                    or any(k in err_str for k in ["rate limit", "quota", "timeout", "timed out", "model not found", "does not exist", "404", "overloaded", "capacity"])
                )

                # Cascada resiliente de modelos oficiales de Groq
                if is_recoverable and retries < max_retries:
                    candidates = [m for m in self.AVAILABLE_MODELS if m not in tried_models]
                    if candidates:
                        retries += 1
                        old_model = self.active_model
                        new_model = candidates[0]
                        self.active_model = new_model
                        self.model = new_model
                        tried_models.append(new_model)
                        config.set_preferred_model(new_model, "groq")
                        safe_print(f"[Groq Core] ⚡ Conmutación resiliente: '{old_model}' -> '{new_model}' (intento {retries}/{max_retries}).")
                        if self.on_model_change:
                            try:
                                self.on_model_change(new_model)
                            except Exception:
                                pass
                        time.sleep(0.2)
                        continue

                # Si fallan todos los modelos o la API key es inválida
                safe_print(f"[Groq Core] Fallo o modelos agotados en Groq ({self.active_model}): {e}")
                if is_quota:
                    raise GroqQuotaError(f"Groq API 429 Cuota Excedida tras failover: {e}")
                return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

            choice = chat_completion.choices[0]
            response_msg = choice.message

            if response_msg.tool_calls:
                user_name = config.get_user_name()
                confirmations = []

                for tc in response_msg.tool_calls:
                    fn_name = tc.function.name
                    raw_args = tc.function.arguments or "{}"
                    try:
                        parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        parsed_args = {}

                    tool_fn = self.local_functions.get(fn_name)
                    if tool_fn:
                        try:
                            tool_result = str(tool_fn(**parsed_args))
                        except Exception as ex:
                            tool_result = f"Error al ejecutar {fn_name}: {ex}"
                    else:
                        tool_result = f"Herramienta '{fn_name}' no disponible."

                    if self.on_tool_call:
                        try:
                            self.on_tool_call(fn_name, parsed_args, tool_result)
                        except Exception:
                            pass

                    if fn_name == "control_media":
                        act = parsed_args.get("action", "").lower()
                        if "play" in act or "pause" in act:
                            confirmations.append(f"A la orden, {user_name}, reproducción pausada o reanudada.")
                        elif "up" in act:
                            confirmations.append(f"Volumen aumentado, {user_name}.")
                        elif "down" in act:
                            confirmations.append(f"Volumen reducido, {user_name}.")
                        elif "mute" in act:
                            confirmations.append(f"Audio silenciado, {user_name}.")
                        elif "next" in act:
                            confirmations.append(f"Pista siguiente, {user_name}.")
                        elif "prev" in act:
                            confirmations.append(f"Pista anterior, {user_name}.")
                        else:
                            confirmations.append(f"Control multimedia aplicado, {user_name}.")
                    elif fn_name == "play_spotify":
                        q = parsed_args.get("query", "")
                        confirmations.append(f"A la orden, {user_name}, reproduciendo '{q}' en Spotify.")
                    elif fn_name in ("play_youtube", "search_youtube"):
                        q = parsed_args.get("query", "")
                        confirmations.append(f"Buscando y reproduciendo '{q}' en YouTube, {user_name}.")
                    elif fn_name == "play_music":
                        q = parsed_args.get("query", "")
                        confirmations.append(f"Reproduciendo '{q}', {user_name}.")
                    elif fn_name == "launch_application":
                        app = parsed_args.get("app_name", "la aplicación")
                        confirmations.append(f"Iniciando {app}, {user_name}.")
                    elif fn_name == "open_url":
                        u = parsed_args.get("url", "")
                        confirmations.append(f"Abriendo {u} en el navegador, {user_name}.")
                    elif fn_name == "write_note":
                        confirmations.append(f"Nota redactada y guardada en el Bloc de notas, {user_name}.")
                    elif fn_name in ("crear_tarea", "add_user_task"):
                        clean_res = re.sub(r"\[[✔\w\s:]+\]", "", tool_result).strip()
                        confirmations.append(clean_res or f"Anotado, {user_name}: tarea registrada en tus pendientes.")
                    elif fn_name == "complete_user_task":
                        clean_res = re.sub(r"\[[✔\w\s:]+\]", "", tool_result).strip()
                        confirmations.append(clean_res or f"Tarea marcada como completada en tu perfil, {user_name}.")
                    elif fn_name == "delete_user_task":
                        clean_res = re.sub(r"\[[✔\w\s:]+\]", "", tool_result).strip()
                        confirmations.append(clean_res or f"Tarea eliminada de tus pendientes, {user_name}.")
                    elif fn_name == "set_user_routine":
                        r_name = parsed_args.get("name", "la rutina")
                        confirmations.append(f"Rutina '{r_name}' guardada en tu perfil, {user_name}.")
                    elif fn_name == "remember_fact":
                        confirmations.append(f"He memorizado esa preferencia en tu perfil, {user_name}.")
                    elif fn_name in ("list_user_tasks", "system_info"):
                        confirmations.append(tool_result)
                    else:
                        clean_res = re.sub(r"\[[✔\w\s:]+\]", "", tool_result).strip()
                        confirmations.append(clean_res or f"A la orden, {user_name}, orden ejecutada.")

                final_reply = " ".join(confirmations)
                explicit_mood = "HAPPY"
                break

            raw_text = response_msg.content or ""
            final_reply, explicit_mood = extract_mood_and_clean_text(raw_text)
            break

        if not final_reply:
            final_reply = raw_text.strip() if 'raw_text' in locals() and raw_text else "A la orden, Oscar. Sistemas listos y en línea."

        self.history.append({"role": "assistant", "content": final_reply})
        self.history = self.history[-self.max_history_turns * 2:]

        expr, icon, dur = detect_emotion_and_icon(message, final_reply, explicit_mood=explicit_mood)
        if self.on_emotion:
            try:
                self.on_emotion(expr, icon, dur)
            except Exception as ex:
                safe_print(f"[Groq Core] Error en callback de emoción: {ex}")

        return final_reply
