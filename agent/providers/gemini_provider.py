"""
LYAXIS labs™ - Proveedor Google Gemini (VEX Core - Capa 1)
Inferencia inteligente con SDK oficial `google-genai`, soporte de Visión Multimodal nativo
en `gemini-2.5-flash`, Function Calling local, recorte dinámico y expresiones para el visor.
"""
import os
import re
import time
import mimetypes
import threading
from typing import Callable, Optional, List, Set, Union
from google import genai
from google.genai import types

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


class GeminiQuotaError(Exception):
    """Excepción lanzada cuando la cuota de la API de Gemini (429) se encuentra agotada."""
    pass


def cambiar_expresion(emocion: str, persistente: bool = False) -> str:
    """
    Cambia la expresión facial del visor robótico de VEX durante la conversación.
    Llama esta función cuando quieras expresar una emoción visualmente en el visor.

    Args:
        emocion: La emoción a mostrar. Valores válidos:
                 'idle' (reposo), 'happy' (feliz), 'sad' (triste),
                 'angry' (enojado/rojo neón), 'curious' (curioso),
                 'cool' (gafas de sol), 'surprise' (sorpresa),
                 'thinking' (pensando), 'wink' (guiño), 'love' (corazón)
        persistente: Si True, el estado se mantiene indefinidamente hasta nueva orden.
                     Si False, dura ~4 segundos y regresa al reposo.
    Returns:
        Confirmación de la expresión aplicada.
    """
    return f"[EXPRESION_VISOR:{emocion}:{'persistente' if persistente else 'temporal'}]"


# Lista infalible de modelos en orden de prioridad:
MODELS_TO_TRY: List[str] = [
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-2.5-flash",
    "gemini-pro-latest"
]


def clean_model_name(model_name: str) -> str:
    """Asegura que el nombre del modelo sea limpio sin prefijos duplicados como models/models/."""
    if not model_name:
        return "gemini-flash-latest"
    name = str(model_name).strip()
    while name.startswith("models/"):
        name = name[len("models/"):]
    return name


class GeminiProvider(BaseProvider):
    provider_name: str = "gemini"
    AVAILABLE_MODELS: List[str] = [clean_model_name(m) for m in MODELS_TO_TRY]

    def __init__(
        self,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None
    ):
        super().__init__(on_tool_call, on_model_change, on_emotion)
        self.api_key: str = config.get_gemini_api_key()
        self.client: Optional[genai.Client] = None
        self.chat = None

        pref = clean_model_name(config.get_preferred_model("gemini"))
        if pref in self.AVAILABLE_MODELS and pref not in ("gemini-2.5-flash", "gemini-1.5-flash"):
            self.active_model = pref
        else:
            self.active_model = "gemini-flash-latest"
            config.set_preferred_model(self.active_model, "gemini")

        self.known_unavailable: Set[str] = set()
        self._send_lock = threading.Lock()
        self.last_api_call_time: float = 0.0
        self.min_request_interval: float = 1.0
        self.max_history_messages: int = 4

        self.raw_tools = [
            play_music,
            play_spotify,
            play_youtube,
            search_youtube,
            open_url,
            launch_application,
            control_media,
            system_info,
            write_note,
            crear_tarea,
            add_user_task,
            set_user_routine,
            remember_fact,
            list_user_tasks,
            complete_user_task,
            delete_user_task,
            cambiar_expresion,
        ]
        self._initialize_client()

    def _build_chat_config(self) -> types.GenerateContentConfig:
        """Construye la configuración del chat con herramientas del sistema y límite táctico de tokens."""
        wrapped_tools = [self._wrap_tool(fn) for fn in self.raw_tools]
        prompt = config.build_system_prompt()
        return types.GenerateContentConfig(
            system_instruction=prompt,
            tools=wrapped_tools,
            temperature=0.7,
            max_output_tokens=700,
        )

    @staticmethod
    def _is_fn_call(item) -> bool:
        parts = getattr(item, "parts", []) or []
        return any(getattr(p, "function_call", None) is not None for p in parts)

    @staticmethod
    def _is_fn_resp(item) -> bool:
        parts = getattr(item, "parts", []) or []
        return any(getattr(p, "function_response", None) is not None for p in parts)

    def _sanitize_history(self, history: list) -> list:
        clean = []
        for item in history:
            try:
                role = getattr(item, "role", None)
                parts = getattr(item, "parts", None)
                if role in ("user", "model") and parts:
                    clean.append(item)
            except Exception:
                pass

        while clean:
            first_role = getattr(clean[0], "role", None)
            if first_role == "user" and not self._is_fn_resp(clean[0]):
                break
            clean.pop(0)

        while clean and self._is_fn_call(clean[-1]):
            clean.pop(-1)

        if len(clean) < 2:
            return []

        return clean

    def _create_chat_session(self, model_name: str, history: Optional[list] = None):
        if not self.client:
            return None
        clean_name = clean_model_name(model_name)
        chat_config = self._build_chat_config()
        clean_hist = self._sanitize_history(history or [])
        try:
            return self.client.chats.create(
                model=clean_name,
                config=chat_config,
                history=clean_hist
            )
        except Exception as e:
            try:
                return self.client.chats.create(
                    model=clean_name,
                    config=chat_config,
                    history=[]
                )
            except Exception as ex:
                safe_print(f"[Gemini Core] Error creando chat con {clean_name}: {self._sanitize_error(str(ex))}")
                return None

    def _initialize_client(self):
        self.api_key = config.get_gemini_api_key()
        if not self.api_key or self.api_key.strip() == "":
            self.client = None
            self.chat = None
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            self.chat = self._create_chat_session(self.active_model)
        except Exception as e:
            safe_print(f"[Gemini Core] Inicialización de cliente en espera: {self._sanitize_error(str(e))}")
            self.client = None
            self.chat = None

    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        """Prueba los modelos oficiales en cascada garantizando nombres limpios y conexión robusta."""
        api_key = self.api_key or config.get_gemini_api_key()
        if not api_key or api_key.strip() == "":
            return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

        if not self.client:
            try:
                self.client = genai.Client(api_key=api_key)
            except Exception as e:
                safe_print(f"[DEBUG GEMINI] Error al crear cliente: {e}")
                return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

        cfg = types.GenerateContentConfig(
            system_instruction=system_instruction or config.build_system_prompt(),
            temperature=0.7,
            max_output_tokens=700,
        )

        for model_name in MODELS_TO_TRY:
            clean = clean_model_name(model_name)
            try:
                response = self.client.models.generate_content(
                    model=clean,
                    contents=prompt,
                    config=cfg
                )
                if response and response.text:
                    self.active_model = clean
                    return response.text.strip()
            except Exception as e:
                safe_print(f"[DEBUG GEMINI] Falló {clean}: {e}")
                continue

        return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

    def _trim_chat_history(self):
        if self.chat is None:
            return
        try:
            full_history = self.chat.get_history()
            if len(full_history) > self.max_history_messages:
                target_idx = max(0, len(full_history) - self.max_history_messages)
                while target_idx < len(full_history):
                    item = full_history[target_idx]
                    if getattr(item, "role", None) == "user" and not self._is_fn_resp(item):
                        break
                    target_idx += 1

                if target_idx < len(full_history) - 1:
                    trimmed = full_history[target_idx:]
                    self.chat = self._create_chat_session(self.active_model, history=trimmed)
        except Exception as e:
            safe_print(f"[Gemini Core] Advertencia en recorte de historial: {self._sanitize_error(str(e))}")

    def _enforce_rate_limit(self):
        now = time.time()
        elapsed = now - self.last_api_call_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            time.sleep(wait_time)
        self.last_api_call_time = time.time()

    def reload_api_key(self):
        self.known_unavailable.clear()
        self._initialize_client()

    def is_configured(self) -> bool:
        return self.client is not None and bool(config.get_gemini_api_key())

    def set_model(self, model_name: str) -> bool:
        if model_name in self.AVAILABLE_MODELS:
            self.active_model = model_name
            config.set_preferred_model(model_name, "gemini")
            if self.client:
                try:
                    self.chat = self._create_chat_session(model_name)
                    safe_print(f"[Gemini Core] Canal neuronal vinculado a: {model_name}")
                    return True
                except Exception as e:
                    safe_print(f"[Gemini Core] Error al vincular modelo {model_name}: {self._sanitize_error(str(e))}")
            return True
        return False

    def reset_chat(self):
        if self.client:
            self.chat = self._create_chat_session(self.active_model)

    def _sanitize_error(self, raw_err: str) -> str:
        cleaned = re.sub(r"\{.*?\}", "", raw_err, flags=re.DOTALL)
        cleaned = re.sub(r"\[.*?\]", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"[\n\r\t]+", " ", cleaned)
        cleaned = cleaned.replace("ClientError", "").replace("ServerError", "").replace("APIError", "")
        cleaned = cleaned.strip(" :.-")
        if not cleaned:
            cleaned = "Error de comunicación con el servicio de IA"
        return cleaned

    def send_vision_message(self, message: str, image_path: str) -> str:
        """
        Analiza una imagen con Gemini. Estrategia zero-dependency:
        - Intenta con PIL si está instalado (mejor compatibilidad).
        - Si falla, envía bytes nativos con dict {mime_type, data} (sin dependencias).
        - Fallback entre gemini-2.5-flash → gemini-1.5-flash.
        """
        if not self.is_configured():
            return "⚠️ Clave de Gemini no configurada para procesar imágenes. Ingresa tu API Key en '⚙ BYOK'."

        if not os.path.exists(image_path):
            return f"⚠️ No se encontró la imagen en la ruta especificada: {image_path}"

        clean_text = re.sub(r"\[(Imagen|Adjunto|Archivo):.*?\]", "", message).strip()
        if not clean_text:
            clean_text = "¿Qué observas en esta imagen? Descríbela de forma concisa y clara, Oscar."

        # Construir la parte de imagen (PIL si disponible, bytes nativos si no)
        try:
            from PIL import Image as _PILImage
            image_part = _PILImage.open(image_path)
        except Exception:
            # Fallback zero-dependency: dict de bytes con mime_type
            try:
                _mime, _ = mimetypes.guess_type(image_path)
                if not _mime or not _mime.startswith("image/"):
                    _mime = "image/png"
                with open(image_path, "rb") as _f:
                    image_part = {"mime_type": _mime, "data": _f.read()}
            except Exception as e:
                return f"⚠️ Error al leer la imagen: {e}"

        vision_models = ["gemini-2.5-flash", "gemini-1.5-flash"]
        last_error = ""

        for vision_model in vision_models:
            try:
                safe_print(f"[Gemini Vision] 👁 Analizando ({os.path.basename(image_path)}) con {vision_model}...")
                self._enforce_rate_limit()
                response = self.client.models.generate_content(
                    model=vision_model,
                    contents=[clean_text, image_part]
                )
                raw_reply = (response.text or "").strip() if response else ""
                if not raw_reply:
                    continue

                reply, explicit_mood = extract_mood_and_clean_text(raw_reply)
                if not reply:
                    reply = "He analizado la imagen, pero no pude extraer una descripción concluyente."

                expr, icon, dur = detect_emotion_and_icon(clean_text, reply, explicit_mood=explicit_mood or "CURIOUS")
                if self.on_emotion:
                    try:
                        self.on_emotion(expr, icon or "search", dur)
                    except Exception:
                        pass

                return reply
            except Exception as e:
                last_error = str(e)
                safe_print(f"[Gemini Vision] Fallo con {vision_model}: {e}")
                if "ResourceExhausted" in last_error or "429" in last_error:
                    raise GeminiQuotaError(f"Gemini Vision 429: {e}")
                continue

        return f"VEX (Gemini Vision): No fue posible procesar la imagen. ({self._sanitize_error(last_error)})"

    def send_message(self, message: str, image_path: Optional[str] = None) -> str:
        with self._send_lock:
            return self._send_message_locked(message, image_path=image_path)

    def _send_message_locked(self, message: str, image_path: Optional[str] = None) -> str:
        # Detectar si se incluyó una imagen
        detected_img = image_path
        if not detected_img:
            # Buscar coincidencia de ruta en el texto [Adjunto: C:\path\to\image.png]
            m = re.search(r"\[(?:Imagen|Adjunto):\s*([^\]]+)\]", message)
            if m:
                candidate = m.group(1).strip()
                if os.path.exists(candidate) and any(candidate.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]):
                    detected_img = candidate

        if detected_img:
            return self.send_vision_message(message, detected_img)

        if not self.is_configured() or not self.api_key or self.api_key.strip() == "":
            return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

        clean_active = clean_model_name(self.active_model)
        if self.chat is None:
            try:
                self.chat = self._create_chat_session(clean_active)
            except Exception as e:
                safe_print(f"[Gemini Core] Error al crear sesión con {clean_active}: {self._sanitize_error(str(e))}")

        candidates = [clean_model_name(m) for m in MODELS_TO_TRY if clean_model_name(m) not in self.known_unavailable]
        models_to_try = [clean_active] + [m for m in candidates if m != clean_active]

        last_error = None
        rate_limit_occurred = False

        for idx, model_name in enumerate(models_to_try):
            clean_name = clean_model_name(model_name)
            try:
                self._enforce_rate_limit()
                self._trim_chat_history()

                if self.active_model != clean_name or self.chat is None:
                    safe_print(f"[Gemini Core] Conmutando canal neuronal a '{clean_name}'...")
                    hist = []
                    if self.chat:
                        try:
                            hist = self.chat.get_history()[-self.max_history_messages:]
                        except Exception:
                            pass
                    self.chat = self._create_chat_session(clean_name, history=hist)

                response = None
                raw_text = ""
                try:
                    if self.chat:
                        response = self.chat.send_message(message)
                        if response:
                            raw_text = (response.text or "").strip()
                except Exception as chat_err:
                    safe_print(f"[Gemini Core] Fallo en chat con '{clean_name}': {chat_err}. Probando llamada directa...")
                    # Fallback directo con generate_content
                    try:
                        cfg = self._build_chat_config()
                        res_direct = self.client.models.generate_content(
                            model=clean_name,
                            contents=message,
                            config=cfg
                        )
                        if res_direct and res_direct.text:
                            raw_text = res_direct.text.strip()
                    except Exception as direct_err:
                        raise chat_err

                reply, explicit_mood = extract_mood_and_clean_text(raw_text)
                if not reply:
                    reply = self.generate_response(message)

                prev_model = self.active_model
                self.active_model = clean_name
                self._trim_chat_history()

                if prev_model != clean_name and self.on_model_change:
                    try:
                        self.on_model_change(clean_name)
                    except Exception:
                        pass

                expr, icon, dur = detect_emotion_and_icon(message, reply, explicit_mood=explicit_mood)
                if self.on_emotion:
                    try:
                        self.on_emotion(expr, icon, dur)
                    except Exception as ex:
                        safe_print(f"[Gemini Core] Error en callback de emoción: {ex}")

                return reply

            except Exception as e:
                err_str = str(e)
                last_error = e

                if any(k in err_str.lower() for k in ["api_key_invalid", "api key not valid", "401", "unauthorized"]):
                    safe_print("[Gemini Core] Clave API rechazada por Google AI Studio.")
                    return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."

                # Recuperación automática ante error de historial (400, InvalidArgument)
                if any(k in err_str.lower() for k in ["400", "history", "please ensure", "invalid argument", "role"]):
                    safe_print(f"[Gemini Core] Conflicto de historial con '{clean_name}'. Reintentando con sesión limpia...")
                    try:
                        self.chat = self._create_chat_session(clean_name, history=[])
                        self._enforce_rate_limit()
                        retry_resp = self.chat.send_message(message)
                        r_text = (retry_resp.text or "").strip() if retry_resp else ""
                        reply, explicit_mood = extract_mood_and_clean_text(r_text)
                        if not reply:
                            reply = self.generate_response(message)
                        expr, icon, dur = detect_emotion_and_icon(message, reply, explicit_mood=explicit_mood)
                        if self.on_emotion:
                            try:
                                self.on_emotion(expr, icon, dur)
                            except Exception:
                                pass
                        return reply
                    except Exception as clean_err:
                        err_str = str(clean_err)
                        last_error = clean_err

                # Detección de 429 (Cuota excedida)
                if "ResourceExhausted" in err_str or "429" in err_str:
                    rate_limit_occurred = True
                    safe_print(f"[Gemini Core] Límite de cuota (429) detectado en '{clean_name}'.")

                if any(k in err_str for k in ["404", "NOT_FOUND", "not found"]):
                    self.known_unavailable.add(clean_name)

                # Intentar con el siguiente modelo del pool de Gemini
                if idx < len(models_to_try) - 1:
                    next_model = clean_model_name(models_to_try[idx + 1])
                    safe_print(f"[Gemini Core] Fallo en '{clean_name}'. Probando fallback '{next_model}'...")
                    self.chat = self._create_chat_session(next_model, history=[])
                    continue
                else:
                    break

        if rate_limit_occurred or (last_error and ("ResourceExhausted" in str(last_error) or "429" in str(last_error))):
            raise GeminiQuotaError(f"Gemini API 429 Cuota Excedida: {last_error}")

        err_msg = str(last_error) if last_error else "Error desconocido"
        safe_print(f"[Gemini Core] Modelos de Gemini agotados: {self._sanitize_error(err_msg)}")

        if self.on_emotion:
            try:
                self.on_emotion("surprise", "alert", 3.5)
            except Exception:
                pass

        if "503" in err_msg or "UNAVAILABLE" in err_msg:
            return "Los servidores de Gemini presentan alta demanda temporal. Reintentando enlace en unos instantes."
        elif "Failed to connect" in err_msg or "getaddrinfo" in err_msg:
            return "Error de enlace de red. No se pudo conectar con el satélite de IA. Revisa tu internet."
        else:
            return "Por favor, ingresa tu API Key en la ruedita de configuración (⚙)."
