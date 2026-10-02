"""
LYAXIS labs™ - Agente Táctico Gemini (VEX Core - Capa 1)
Inferencia inteligente ultra-optimizada con:
- Recorte dinámico de contexto (Sliding Window de 3 intercambios / 6 mensajes).
- Límite estricto de tokens de salida (max_output_tokens=150).
- Limitador de tasa del cliente (Cooldown de 2.0s).
- Cascada de modelos y reintento automático con Backoff de 5s ante 429.
- Detección inteligente de emociones y proyecciones contextuales para el Visor Robótico.
"""
import functools
import re
import time
import threading
from typing import Callable, Optional, List, Set, Tuple
from google import genai
from google.genai import types

import config
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


def safe_print(msg: str):
    """Imprime mensajes de forma segura en consolas con codificación restringida."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def detect_emotion_and_icon(
    prompt: str,
    response: str,
    explicit_mood: Optional[str] = None
) -> Tuple[str, Optional[str], float]:
    """
    Analiza la etiqueta explícita de ánimo [MOOD: ...], el prompt del usuario y la respuesta de Gemini
    para determinar la expresión visual y los iconos contextuales a proyectar en el visor EMO / Vector.

    Retorna: (expression_name, icon_name, icon_duration)
    """
    # 0. Mapeo prioritario si el modelo devolvió una etiqueta estructurada [MOOD: ...]
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
            # Verificar si además se menciona algún icono contextual (música, búsqueda, etc.)
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


class GeminiAgent:
    AVAILABLE_MODELS: List[str] = getattr(config, "AVAILABLE_MODELS", [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
    ])

    def __init__(
        self,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None
    ):
        """
        Inicializa el agente de VEX con control estricto de cuota y tolerancia a fallos.
        """
        self.on_tool_call = on_tool_call
        self.on_model_change = on_model_change
        self.on_emotion = on_emotion
        self.client: Optional[genai.Client] = None
        self.chat = None
        self.active_model: str = getattr(config, "DEFAULT_MODEL", self.AVAILABLE_MODELS[0])
        self.known_unavailable: Set[str] = set()
        self._send_lock = threading.Lock()

        # Control de tasa local (Cooldown de 2.0 segundos entre llamadas)
        self.last_api_call_time: float = 0.0
        self.min_request_interval: float = 2.0

        # Historial deslizante estricto: Podar a un máximo de 4 mensajes del chat
        self.max_history_messages: int = 4

        self.raw_tools = [
            play_music,
            play_spotify,
            search_youtube,
            open_url,
            launch_application,
            control_media,
            system_info,
            write_note
        ]
        self._initialize_client()

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
                    safe_print(f"[VEX Core] Error en callback de herramienta: {ex}")
            return result
        return wrapper

    def _build_chat_config(self) -> types.GenerateContentConfig:
        """
        Construye la configuración del chat con instrucciones tácticas y
        límite estricto de tokens de salida (150 tokens) para ahorro extremo.
        """
        wrapped_tools = [self._wrap_tool(fn) for fn in self.raw_tools]
        prompt = config.build_system_prompt()
        return types.GenerateContentConfig(
            system_instruction=prompt,
            tools=wrapped_tools,
            temperature=0.7,
            max_output_tokens=150,  # Límite táctico de salida concisa
        )

    @staticmethod
    def _is_fn_call(item) -> bool:
        """Determina si un mensaje contiene una llamada a función (model -> tool)."""
        parts = getattr(item, "parts", []) or []
        return any(getattr(p, "function_call", None) is not None for p in parts)

    @staticmethod
    def _is_fn_resp(item) -> bool:
        """Determina si un mensaje contiene una respuesta de función (tool -> model)."""
        parts = getattr(item, "parts", []) or []
        return any(getattr(p, "function_response", None) is not None for p in parts)

    def _sanitize_history(self, history: list) -> list:
        """
        Filtra y sanea el historial asegurando:
        1. Que comience con un turno legítimo de 'user' (que no sea un function_response huérfano).
        2. Que ningún function_call quede desprovisto de su function_response correspondiente.
        """
        clean = []
        for item in history:
            try:
                role = getattr(item, "role", None)
                parts = getattr(item, "parts", None)
                if role in ("user", "model") and parts:
                    clean.append(item)
            except Exception:
                pass

        # Exigencia estricta de Gemini API: el historial DEBE iniciar con un turno de 'user' normal
        while clean:
            first_role = getattr(clean[0], "role", None)
            if first_role == "user" and not self._is_fn_resp(clean[0]):
                break
            clean.pop(0)

        # Si el último mensaje es un function_call que nunca recibió function_response, descartarlo
        while clean and self._is_fn_call(clean[-1]):
            clean.pop(-1)

        if len(clean) < 2:
            return []

        return clean

    def _create_chat_session(self, model_name: str, history: Optional[list] = None):
        """Crea una sesión de chat con el modelo especificado y recorte de historial."""
        if not self.client:
            return None
        chat_config = self._build_chat_config()
        clean_hist = self._sanitize_history(history or [])
        try:
            return self.client.chats.create(
                model=model_name,
                config=chat_config,
                history=clean_hist
            )
        except Exception as e:
            # Si el historial causa conflicto en el cambio de modelo, iniciar sesión limpia
            try:
                return self.client.chats.create(
                    model=model_name,
                    config=chat_config,
                    history=[]
                )
            except Exception as ex:
                safe_print(f"[VEX Core] Error creando chat con {model_name}: {self._sanitize_error(str(ex))}")
                return None

    def _initialize_client(self):
        """Inicializa el cliente de Gemini y la sesión de chat inicial."""
        api_key = config.get_api_key()
        if not api_key:
            self.client = None
            self.chat = None
            return

        try:
            self.client = genai.Client(api_key=api_key)
            self.chat = self._create_chat_session(self.active_model)
        except Exception as e:
            safe_print(f"[VEX Core] Inicialización de cliente en espera: {self._sanitize_error(str(e))}")
            self.client = None
            self.chat = None

    def _trim_chat_history(self):
        """
        Recorte dinámico de contexto (Sliding Window):
        Mantiene en memoria los últimos intercambios asegurando que ningún function_call
        quede huérfano de su function_response correspondiente.
        """
        if self.chat is None:
            return

        try:
            full_history = self.chat.get_history()
            if len(full_history) > self.max_history_messages:
                # Buscar un punto de corte seguro donde comience un turno de usuario genuino
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
            safe_print(f"[VEX Core] Advertencia en recorte de historial: {self._sanitize_error(str(e))}")

    def _enforce_rate_limit(self):
        """
        Controlador de tasa local del cliente:
        Garantiza que no se dispare más de 1 petición cada 2.0 segundos.
        """
        now = time.time()
        elapsed = now - self.last_api_call_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            time.sleep(wait_time)
        self.last_api_call_time = time.time()

    def reload_api_key(self):
        """Recarga la clave de API desde la configuración y reinicia el cliente."""
        self.known_unavailable.clear()
        self._initialize_client()

    def is_configured(self) -> bool:
        """Verifica si existe una API Key válida configurada."""
        return self.client is not None and bool(config.get_api_key())

    def set_model(self, model_name: str) -> bool:
        """Cambia el modelo activo si es soportado."""
        if model_name in self.AVAILABLE_MODELS:
            self.active_model = model_name
            if self.client:
                try:
                    self.chat = self._create_chat_session(model_name)
                    safe_print(f"[VEX Core] Canal neuronal vinculado a: {model_name}")
                    return True
                except Exception as e:
                    safe_print(f"[VEX Core] Error al vincular modelo {model_name}: {self._sanitize_error(str(e))}")
            return True
        return False

    def reset_chat(self):
        """Reinicia la conversación actual de VEX."""
        if self.client:
            self.chat = self._create_chat_session(self.active_model)

    def _sanitize_error(self, raw_err: str) -> str:
        """Limpia cadenas crudas de error JSON para proteger la consola."""
        cleaned = re.sub(r"\{.*?\}", "", raw_err, flags=re.DOTALL)
        cleaned = re.sub(r"\[.*?\]", "", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"[\n\r\t]+", " ", cleaned)
        cleaned = cleaned.replace("ClientError", "").replace("ServerError", "").replace("APIError", "")
        cleaned = cleaned.strip(" :.-")
        if not cleaned:
            cleaned = "Error de comunicación con el servicio de IA"
        return cleaned

    def send_message(self, message: str) -> str:
        """
        Envía un mensaje al modelo (Capa 1: Inferencia Inteligente) con:
        - Bloqueo thread-safe contra peticiones concurrentes simultáneas.
        - Freno de tasa (2s).
        - Recorte dinámico de historial (últimos 3 intercambios).
        - Backoff automático de 5s ante código 429.
        - Failover Pool multimodelo.
        - Detección de emociones e iconos contextuales.
        """
        with self._send_lock:
            return self._send_message_locked(message)

    def _send_message_locked(self, message: str) -> str:
        if not self.is_configured():
            return (
                "⚠️ Clave de API no configurada. Por favor abre el panel '⚙ BYOK CONFIG' "
                "e ingresa tu Gemini API Key de Google AI Studio para activar los sistemas."
            )

        if self.chat is None:
            try:
                self.chat = self._create_chat_session(self.active_model)
            except Exception as e:
                safe_print(f"[VEX Core] Error al crear sesión inicial con {self.active_model}: {self._sanitize_error(str(e))}")

        # Ordenar modelos priorizando los que no han arrojado 404
        available_candidates = [m for m in self.AVAILABLE_MODELS if m not in self.known_unavailable and m != self.active_model]
        models_to_try = [self.active_model] + available_candidates + [m for m in self.AVAILABLE_MODELS if m in self.known_unavailable and m != self.active_model]

        last_error = None
        rate_limit_occurred = False

        for idx, model_name in enumerate(models_to_try):
            try:
                # 1. Aplicar limitador de tasa del cliente (2 segundos entre llamadas)
                self._enforce_rate_limit()

                # 2. Recortar historial a los últimos 3 intercambios
                self._trim_chat_history()

                # 3. Conmutar sesión si el modelo cambió
                if self.active_model != model_name or self.chat is None:
                    safe_print(f"[VEX Core] Conmutando canal neuronal al modelo '{model_name}'...")
                    hist = []
                    if self.chat:
                        try:
                            hist = self.chat.get_history()[-self.max_history_messages:]
                        except Exception:
                            pass
                    self.chat = self._create_chat_session(model_name, history=hist)

                # 4. Enviar mensaje
                response = self.chat.send_message(message)
                reply = ""
                if response:
                    try:
                        reply = (response.text or "").strip()
                    except Exception:
                        pass

                if not reply:
                    reply = "Orden táctica ejecutada con éxito."

                # Extraer etiqueta de ánimo si está presente (ej. [MOOD: HAPPY] o [MOOD: SAD])
                explicit_mood = None
                mood_match = re.search(r"\[MOOD:\s*([A-Za-z_-]+)\]", reply, flags=re.IGNORECASE)
                if mood_match:
                    explicit_mood = mood_match.group(1).upper()
                # Limpiar TODOS los tags entre corchetes para evitar truncado en la UI
                reply = re.sub(r"\[[A-Z_:][^\]\[]*\]", "", reply, flags=re.IGNORECASE).strip()
                reply = re.sub(r"\s{2,}", " ", reply).strip()
                if not reply:
                    reply = "Orden táctica ejecutada con éxito."

                prev_model = self.active_model
                self.active_model = model_name
                # Post-recorte de historial tras respuesta
                self._trim_chat_history()

                if prev_model != model_name and self.on_model_change:
                    try:
                        self.on_model_change(model_name)
                    except Exception:
                        pass

                # 5. Detección de emoción / icono contextual
                expr, icon, dur = detect_emotion_and_icon(message, reply, explicit_mood=explicit_mood)
                if self.on_emotion:
                    try:
                        self.on_emotion(expr, icon, dur)
                    except Exception as ex:
                        safe_print(f"[VEX Core] Error en callback de emoción: {ex}")

                return reply

            except Exception as e:
                err_str = str(e)
                last_error = e

                # Si es un error de clave de API inválida, detener failover
                if "API_KEY_INVALID" in err_str or "API key not valid" in err_str:
                    safe_print("[VEX Core] Alerta: Clave API de Gemini rechazada por el servidor.")
                    return "❌ La API Key proporcionada no es válida. Por favor verifica tus credenciales en '⚙ BYOK CONFIG'."

                # 1. Recuperación automática ante error de historial (400, InvalidArgument, roles desalineados)
                if any(k in err_str.lower() for k in ["400", "history", "please ensure", "invalid argument", "role"]):
                    safe_print(f"[VEX Core] Conflicto de historial con '{model_name}'. Reintentando con sesión limpia...")
                    try:
                        self.chat = self._create_chat_session(model_name, history=[])
                        self._enforce_rate_limit()
                        retry_resp = self.chat.send_message(message)
                        retry_text = ""
                        if retry_resp:
                            try:
                                retry_text = (retry_resp.text or "").strip()
                            except Exception:
                                pass
                        if not retry_text:
                            retry_text = "Orden procesada con éxito."

                        explicit_mood = None
                        mood_match = re.search(r"\[MOOD:\s*([A-Za-z_-]+)\]", retry_text, flags=re.IGNORECASE)
                        if mood_match:
                            explicit_mood = mood_match.group(1).upper()
                        retry_text = re.sub(r"\[[A-Z_:][^\]\[]*\]", "", retry_text, flags=re.IGNORECASE).strip()
                        retry_text = re.sub(r"\s{2,}", " ", retry_text).strip()
                        if not retry_text:
                            retry_text = "Orden procesada con éxito."

                        expr, icon, dur = detect_emotion_and_icon(message, retry_text, explicit_mood=explicit_mood)
                        if self.on_emotion:
                            try:
                                self.on_emotion(expr, icon, dur)
                            except Exception:
                                pass
                        return retry_text
                    except Exception as clean_err:
                        err_str = str(clean_err)
                        last_error = clean_err

                # 2. Manejo de error 429 (Resource Exhausted) con backoff de 4 segundos
                if "ResourceExhausted" in err_str or "429" in err_str:
                    rate_limit_occurred = True
                    safe_print(f"[VEX Core] Límite de cuota en '{model_name}'. Aplicando backoff táctico de 4 segundos...")
                    time.sleep(4.0)
                    try:
                        self._enforce_rate_limit()
                        retry_resp = self.chat.send_message(message)
                        retry_text = ""
                        if retry_resp:
                            try:
                                retry_text = (retry_resp.text or "").strip()
                            except Exception:
                                pass
                        if not retry_text:
                            retry_text = "Orden procesada con éxito."

                        explicit_mood = None
                        mood_match = re.search(r"\[MOOD:\s*([A-Za-z_-]+)\]", retry_text, flags=re.IGNORECASE)
                        if mood_match:
                            explicit_mood = mood_match.group(1).upper()
                        retry_text = re.sub(r"\[[A-Z_:][^\]\[]*\]", "", retry_text, flags=re.IGNORECASE).strip()
                        retry_text = re.sub(r"\s{2,}", " ", retry_text).strip()
                        if not retry_text:
                            retry_text = "Orden procesada con éxito."

                        expr, icon, dur = detect_emotion_and_icon(message, retry_text, explicit_mood=explicit_mood)
                        if self.on_emotion:
                            try:
                                self.on_emotion(expr, icon, dur)
                            except Exception:
                                pass
                        return retry_text
                    except Exception as retry_err:
                        err_str = str(retry_err)
                        last_error = retry_err

                # 3. Detección de modelo deprecado o 404
                if any(k in err_str for k in ["404", "NOT_FOUND", "not found"]):
                    self.known_unavailable.add(model_name)

                # 4. FAILOVER INCONDICIONAL: Pasar al siguiente modelo del pool
                if idx < len(models_to_try) - 1:
                    next_model = models_to_try[idx + 1]
                    safe_print(f"[VEX Core] Fallo en '{model_name}'. Conmutando Failover Pool a '{next_model}'...")
                    self.chat = self._create_chat_session(next_model, history=[])
                    continue
                else:
                    safe_print(f"[VEX Core] Agotados todos los modelos del Failover Pool.")
                    break

        # Si agotamos el pool o persiste 429 tras backoff
        err_msg = str(last_error) if last_error else "Error desconocido"
        safe_print(f"[VEX Core] Error en transmisión: {self._sanitize_error(err_msg)}")

        if self.on_emotion:
            try:
                self.on_emotion("surprise", "alert", 3.5)
            except Exception:
                pass

        if rate_limit_occurred or "ResourceExhausted" in err_msg or "429" in err_msg:
            return "Canal de inferencia temporalmente ocupado, dame unos segundos."
        elif "503" in err_msg or "UNAVAILABLE" in err_msg:
            return "Los servidores de Gemini presentan alta demanda. Reintentando enlace en unos instantes."
        elif "Failed to connect" in err_msg or "getaddrinfo" in err_msg:
            return "Error de enlace de red. No se pudo conectar con el satélite de IA. Revisa tu internet."
        else:
            return "VEX: No se pudo establecer conexión táctica con el modelo de IA. Sistemas en espera."
