"""
LYAXIS labs™ - Despachador y Orquestador Multi-Proveedor (agent/factory.py)
Instancia y gestiona los clientes de inferencia según el proveedor activo ('gemini' o 'groq')
con tolerancia a fallos y Failover Inteligente automático ante errores 429 (Cuota excedida).
"""
import threading
from typing import Callable, Optional, List, Dict

import config
from agent.providers.base_provider import BaseProvider, safe_print
from agent.providers.gemini_provider import GeminiProvider, GeminiQuotaError
from agent.providers.groq_provider import GroqProvider, GroqQuotaError


class AgentOrchestrator:
    """
    Orquestador unificado de inferencia multi-proveedor para VEX.
    Ofrece compatibilidad total de interfaz con la UI y conmuta transparentemente
    entre Gemini y Groq en tiempo real o ante agotamiento de cuota.
    """

    def __init__(
        self,
        on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None,
        on_failover: Optional[Callable[[str, str, str], None]] = None,
    ):
        self.on_tool_call = on_tool_call
        self.on_model_change = on_model_change
        self.on_emotion = on_emotion
        self.on_failover = on_failover

        self._lock = threading.Lock()

        # Instanciar proveedores
        self.providers: Dict[str, BaseProvider] = {
            "gemini": GeminiProvider(
                on_tool_call=self.on_tool_call,
                on_model_change=self._handle_provider_model_change,
                on_emotion=self.on_emotion
            ),
            "groq": GroqProvider(
                on_tool_call=self.on_tool_call,
                on_model_change=self._handle_provider_model_change,
                on_emotion=self.on_emotion
            )
        }

        self.active_provider_name: str = config.get_active_provider()
        self._sync_active_provider()

    def _sync_active_provider(self):
        """Asegura que el proveedor activo esté sincronizado con la configuración."""
        prov = config.get_active_provider()
        if prov in self.providers:
            self.active_provider_name = prov

    def _handle_provider_model_change(self, new_model: str):
        """Notifica a la UI si el proveedor activo cambió de modelo internamente."""
        if self.on_model_change:
            try:
                self.on_model_change(new_model)
            except Exception as e:
                safe_print(f"[Orchestrator] Error en callback de cambio de modelo: {e}")

    @property
    def current_provider(self) -> BaseProvider:
        self._sync_active_provider()
        return self.providers.get(self.active_provider_name, self.providers["gemini"])

    @property
    def AVAILABLE_MODELS(self) -> List[str]:
        return self.current_provider.AVAILABLE_MODELS

    @property
    def active_model(self) -> str:
        return self.current_provider.active_model

    @active_model.setter
    def active_model(self, model_name: str):
        self.current_provider.active_model = model_name

    def set_provider(self, provider_name: str) -> bool:
        """Cambia el proveedor activo ('gemini' o 'groq') y actualiza la configuración."""
        clean_name = provider_name.strip().lower()
        if clean_name not in self.providers:
            return False

        with self._lock:
            self.active_provider_name = clean_name
            config.set_active_provider(clean_name)
            safe_print(f"[Orchestrator] Proveedor activo conmutado a: {clean_name.upper()}")

            # Notificar a la UI el modelo preferido del nuevo proveedor
            if self.on_model_change:
                try:
                    self.on_model_change(self.current_provider.active_model)
                except Exception:
                    pass

        return True

    def get_active_provider(self) -> str:
        return self.active_provider_name

    def set_model(self, model_name: str) -> bool:
        """Asigna el modelo deseado al proveedor actualmente activo."""
        success = self.current_provider.set_model(model_name)
        if success:
            config.set_preferred_model(model_name, self.active_provider_name)
        return success

    def reload_api_key(self):
        """Recarga credenciales en ambos proveedores y auto-ajusta el proveedor si es necesario."""
        with self._lock:
            self.providers["gemini"].reload_api_key()
            self.providers["groq"].reload_api_key()
            self._sync_active_provider()

    def is_configured(self) -> bool:
        """Verifica si el proveedor activo o al menos uno de los proveedores está listo."""
        if self.current_provider.is_configured():
            return True

        # Si el proveedor activo no tiene clave pero el alternativo sí, verificar
        alt_name = "groq" if self.active_provider_name == "gemini" else "gemini"
        if self.providers[alt_name].is_configured():
            # Conmutar automáticamente al que sí está configurado
            self.set_provider(alt_name)
            return True

        return False

    def reset_chat(self):
        """Reinicia la conversación en todos los proveedores."""
        for p in self.providers.values():
            p.reset_chat()

    def process(self, message: str, image_path: Optional[str] = None) -> str:
        """Alias para procesar mensajes con el orquestador multi-proveedor."""
        return self.send_message(message, image_path=image_path)

    def send_message(self, message: str, image_path: Optional[str] = None) -> str:
        """
        Envía un mensaje al proveedor activo con Failover Inteligente automático y soporte de Visión.
        Si Groq devuelve error 404, cuota excedida (429) o fallas de inferencia, conmuta silenciosa
        e inmediatamente hacia Google Gemini para que VEX responda sin interrumpir la conversación.
        """
        primary_name = self.active_provider_name
        primary_provider = self.current_provider

        # Si el primario no está configurado pero el alternativo sí, cambiar
        alt_name = "gemini" if primary_name == "groq" else "groq"
        if not primary_provider.is_configured() and self.providers[alt_name].is_configured():
            safe_print(f"[Orchestrator] '{primary_name}' sin clave. Conmutando automáticamente a '{alt_name}'...")
            self.set_provider(alt_name)
            primary_name = alt_name
            primary_provider = self.current_provider

        try:
            resp = primary_provider.send_message(message, image_path=image_path)
            
            # Detección de respuestas con error neuronal, 404, límites o fallas no recuperables
            resp_lower = resp.lower()
            is_error_resp = (
                "error neuronal" in resp_lower
                or "404" in resp
                or "not_found" in resp_lower
                or "notfound" in resp_lower
                or "solicitud neuronal" in resp_lower
                or resp.startswith(f"vex ({primary_name}): no se pudo")
                or resp.startswith(f"vex ({primary_name}): error")
                or "límite de cuota" in resp_lower
                or "429" in resp
            )

            if is_error_resp:
                fallback_name = "gemini" if primary_name == "groq" else "groq"
                fallback_provider = self.providers[fallback_name]
                if fallback_provider.is_configured():
                    safe_print(f"[Orchestrator] ⚡ CONMUTACIÓN SILENCIOSA: Canal {primary_name.upper()} devolvió error ({resp.strip()}). Failover inmediato a {fallback_name.upper()}...")
                    self.set_provider(fallback_name)
                    if self.on_failover:
                        try:
                            self.on_failover(primary_name, fallback_name, "conmutación silenciosa por error 404 o indisponibilidad")
                        except Exception:
                            pass
                    return fallback_provider.send_message(message, image_path=image_path)
            return resp

        except (GeminiQuotaError, GroqQuotaError) as quota_err:
            safe_print(f"[Orchestrator] Cuota agotada en {primary_name.upper()}: {quota_err}")
            fallback_name = "gemini" if primary_name == "groq" else "groq"
            fallback_provider = self.providers[fallback_name]

            if fallback_provider.is_configured():
                safe_print(f"[Orchestrator] ⚡ CONMUTACIÓN SILENCIOSA: Conmutando a {fallback_name.upper()} por cuota...")
                self.set_provider(fallback_name)
                if self.on_failover:
                    try:
                        self.on_failover(primary_name, fallback_name, "límite de cuota")
                    except Exception as ex:
                        safe_print(f"[Orchestrator] Error en callback de failover: {ex}")

                try:
                    return fallback_provider.send_message(message, image_path=image_path)
                except Exception as fallback_err:
                    safe_print(f"[Orchestrator] Error en proveedor secundario {fallback_name.upper()}: {fallback_err}")
                    return (
                        f"⚠️ Límite de cuota alcanzado en {primary_name.title()} y error en "
                        f"proveedor de respaldo {fallback_name.title()}: {fallback_err}"
                    )
            else:
                return (
                    f"⚠️ Se ha alcanzado el límite de cuota en {primary_name.title()}. "
                    f"Puedes ingresar tu clave de {fallback_name.title()} en '⚙ BYOK' "
                    f"para habilitar conmutación automática de alta disponibilidad."
                )

        except Exception as e:
            safe_print(f"[Orchestrator] Excepción en canal {primary_name.upper()}: {e}. Activando failover silencioso a Gemini...")
            fallback_name = "gemini" if primary_name == "groq" else "groq"
            fallback_provider = self.providers[fallback_name]
            if fallback_provider.is_configured():
                self.set_provider(fallback_name)
                if self.on_failover:
                    try:
                        self.on_failover(primary_name, fallback_name, "recuperación automática ante excepción")
                    except Exception:
                        pass
                try:
                    return fallback_provider.send_message(message, image_path=image_path)
                except Exception as fb_err:
                    safe_print(f"[Orchestrator] Error en proveedor de respaldo {fallback_name.upper()}: {fb_err}")
                    return f"VEX ({fallback_name.title()}): Error en conmutación ({fb_err})."
            return f"VEX ({primary_name.title()}): Error al procesar orden ({e})."


def create_agent(
    on_tool_call: Optional[Callable[[str, dict, str], None]] = None,
    on_model_change: Optional[Callable[[str], None]] = None,
    on_emotion: Optional[Callable[[str, Optional[str], float], None]] = None,
    on_failover: Optional[Callable[[str, str, str], None]] = None
) -> AgentOrchestrator:
    """Función de fábrica para instanciar el orquestador multi-proveedor de VEX."""
    return AgentOrchestrator(
        on_tool_call=on_tool_call,
        on_model_change=on_model_change,
        on_emotion=on_emotion,
        on_failover=on_failover
    )
