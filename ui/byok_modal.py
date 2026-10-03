"""
LYAXIS labs™ - Modal de Configuración BYOK Multi-Proveedor y Voz Híbrida (ui/byok_modal.py)
Gestor visual para Google Gemini API, Groq Cloud API y ElevenLabs Voice Engine con
selectores segmentados, actualización dinámica de modelos y persistencia en user_config.json.
"""
import webbrowser
import customtkinter as ctk

import config
from ui.styles import (
    BG_ROOT,
    BORDER_BLUE,
    BORDER_CYAN,
    ACCENT_CYAN,
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    get_font_badge
)


class ApiKeyModal(ctk.CTkToplevel):
    """
    Modal de configuración de credenciales BYOK (Bring Your Own Key) Multi-Proveedor y Voz Híbrida.
    Permite alternar entre Google Gemini y Groq Cloud, configurar la voz cinematográfica
    de ElevenLabs o el motor Edge-TTS gratuito, y habilitar el Failover Inteligente.
    """

    def __init__(self, master, on_save_callback=None):
        super().__init__(master)
        self.on_save_callback = on_save_callback

        self.title("LYAXIS labs™ // VEX - Ajustes BYOK & Motor de Voz")
        self.geometry("580x720")
        self.minsize(540, 600)
        self.configure(fg_color=BG_ROOT)

        self.transient(master)
        self.grab_set()

        # Cargar configuración actual
        self.user_cfg = config.load_user_config()
        self.current_provider = config.get_active_provider()
        self.current_tts_engine = config.get_tts_engine()

        self.show_gemini_pass = False
        self.show_groq_pass = False
        self.show_eleven_pass = False

        self._build_ui()

    def _build_ui(self):
        # Marco exterior principal con estética Cyberpunk
        self.container = ctk.CTkFrame(
            self,
            fg_color="#0b0f19",
            border_color=BORDER_BLUE,
            border_width=1.2,
            corner_radius=12
        )
        self.container.pack(fill="both", expand=True, padx=14, pady=14)

        # Encabezado fijo
        lbl_title = ctk.CTkLabel(
            self.container,
            text="⚙ CONFIGURACIÓN BYOK // NEXUS TÁCTICO",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_title.pack(pady=(12, 2))

        lbl_desc = ctk.CTkLabel(
            self.container,
            text="Credenciales de IA y motores de voz almacenadas localmente en config/user_config.json.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY,
            justify="center"
        )
        lbl_desc.pack(pady=(0, 8))

        # Contenedor desplazable para albergar todos los controles cómodamente
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent",
            scrollbar_button_color="#18233b",
            scrollbar_button_hover_color=ACCENT_BLUE
        )
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        # ================= SECCIÓN 1: OPERADOR =================
        lbl_user = ctk.CTkLabel(
            self.scroll_frame,
            text="OPERADOR ASIGNADO:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_user.pack(anchor="w", padx=16, pady=(4, 2))

        self.entry_user = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="Nombre de usuario (ej. Oscar)",
            width=480,
            height=32,
            fg_color="#07090f",
            border_color="#1f2c4a",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_user.pack(fill="x", padx=16, pady=(0, 10))
        self.entry_user.insert(0, config.get_user_name())

        # ================= SECCIÓN 2: PROVEEDOR LLM =================
        lbl_prov = ctk.CTkLabel(
            self.scroll_frame,
            text="PROVEEDOR DE INFERENCIA ACTIVO:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_prov.pack(anchor="w", padx=16, pady=(0, 3))

        self.seg_provider = ctk.CTkSegmentedButton(
            self.scroll_frame,
            values=["Google Gemini", "Groq Cloud"],
            command=self._on_provider_segment_changed,
            height=32,
            fg_color="#07090f",
            selected_color=ACCENT_BLUE,
            selected_hover_color=ACCENT_BLUE_HOVER,
            unselected_color="#0e1424",
            unselected_hover_color="#18223a",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold")
        )
        self.seg_provider.pack(fill="x", padx=16, pady=(0, 10))
        initial_seg = "Google Gemini" if self.current_provider == "gemini" else "Groq Cloud"
        self.seg_provider.set(initial_seg)

        # ================= SECCIÓN 3: GEMINI KEY =================
        header_gem = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_gem.pack(fill="x", padx=16, pady=(0, 2))

        lbl_gem = ctk.CTkLabel(
            header_gem,
            text="Google Gemini API Key:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_gem.pack(side="left")

        gemini_key_val = config.get_gemini_api_key()
        gem_status_text = "● Configurada" if gemini_key_val else "○ No configurada"
        gem_status_color = "#10b981" if gemini_key_val else "#64748b"

        self.lbl_gem_status = ctk.CTkLabel(
            header_gem,
            text=gem_status_text,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=gem_status_color
        )
        self.lbl_gem_status.pack(side="right")

        self.entry_gemini_key = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="AIzaSy...",
            height=32,
            show="*",
            fg_color="#07090f",
            border_color="#1f2c4a",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.entry_gemini_key.pack(fill="x", padx=16, pady=(0, 2))
        if gemini_key_val:
            self.entry_gemini_key.insert(0, gemini_key_val)

        row_gem_links = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_gem_links.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_gem_toggle = ctk.CTkButton(
            row_gem_links,
            text="👁 Ver",
            width=65,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Consolas", size=10),
            command=self._toggle_gemini_visibility
        )
        self.btn_gem_toggle.pack(side="left")

        btn_gem_link = ctk.CTkButton(
            row_gem_links,
            text="🔗 Obtener clave en Google AI Studio",
            width=230,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=10, underline=True),
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")
        )
        btn_gem_link.pack(side="right")

        # ================= SECCIÓN 4: GROQ KEY =================
        header_groq = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_groq.pack(fill="x", padx=16, pady=(0, 2))

        lbl_groq = ctk.CTkLabel(
            header_groq,
            text="Groq Cloud API Key:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_groq.pack(side="left")

        groq_key_val = config.get_groq_api_key()
        groq_status_text = "● Configurada" if groq_key_val else "○ No configurada"
        groq_status_color = "#10b981" if groq_key_val else "#64748b"

        self.lbl_groq_status = ctk.CTkLabel(
            header_groq,
            text=groq_status_text,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=groq_status_color
        )
        self.lbl_groq_status.pack(side="right")

        self.entry_groq_key = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="gsk_...",
            height=32,
            show="*",
            fg_color="#07090f",
            border_color="#1f2c4a",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.entry_groq_key.pack(fill="x", padx=16, pady=(0, 2))
        if groq_key_val:
            self.entry_groq_key.insert(0, groq_key_val)

        row_groq_links = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_groq_links.pack(fill="x", padx=16, pady=(0, 8))

        self.btn_groq_toggle = ctk.CTkButton(
            row_groq_links,
            text="👁 Ver",
            width=65,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Consolas", size=10),
            command=self._toggle_groq_visibility
        )
        self.btn_groq_toggle.pack(side="left")

        btn_groq_link = ctk.CTkButton(
            row_groq_links,
            text="🔗 Obtener clave en Groq Console (Gratis)",
            width=240,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=10, underline=True),
            command=lambda: webbrowser.open("https://console.groq.com/keys")
        )
        btn_groq_link.pack(side="right")

        # ================= SECCIÓN 5: MODELO ASOCIADO =================
        row_model = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_model.pack(fill="x", padx=16, pady=(2, 10))

        lbl_model = ctk.CTkLabel(
            row_model,
            text="MODELO ASOCIADO AL PROVEEDOR:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_model.pack(side="left")

        models_list = config.get_available_models(self.current_provider)
        self.menu_model = ctk.CTkOptionMenu(
            row_model,
            values=models_list,
            width=230,
            height=28,
            fg_color="#0e1526",
            button_color="#16223d",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#080c16",
            dropdown_hover_color="#18233b",
            dropdown_text_color="#f8fafc",
            text_color=ACCENT_CYAN,
            font=get_font_badge()
        )
        self.menu_model.pack(side="right")
        preferred_m = config.get_preferred_model(self.current_provider)
        if preferred_m in models_list:
            self.menu_model.set(preferred_m)
        else:
            self.menu_model.set(models_list[0])

        # ================= SECCIÓN 6: MOTOR DE VOZ HÍBRIDO =================
        sep_tts = ctk.CTkFrame(self.scroll_frame, height=1, fg_color="#17223b")
        sep_tts.pack(fill="x", padx=16, pady=(6, 8))

        lbl_tts_title = ctk.CTkLabel(
            self.scroll_frame,
            text="MOTOR DE SÍNTESIS DE VOZ (TTS):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_tts_title.pack(anchor="w", padx=16, pady=(0, 4))

        self.seg_tts = ctk.CTkSegmentedButton(
            self.scroll_frame,
            values=["edge-tts (Gratis / Ilimitado)", "ElevenLabs (Ultra-realista)"],
            command=self._on_tts_segment_changed,
            height=32,
            fg_color="#07090f",
            selected_color="#0284c7",
            selected_hover_color="#0369a1",
            unselected_color="#0e1424",
            unselected_hover_color="#18223a",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold")
        )
        self.seg_tts.pack(fill="x", padx=16, pady=(0, 6))
        initial_tts_seg = "ElevenLabs (Ultra-realista)" if self.current_tts_engine == "elevenlabs" else "edge-tts (Gratis / Ilimitado)"
        self.seg_tts.set(initial_tts_seg)

        # Aviso dinámico de ElevenLabs
        self.lbl_tts_notice = ctk.CTkLabel(
            self.scroll_frame,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#f59e0b",
            wraplength=480,
            justify="left"
        )
        self.lbl_tts_notice.pack(anchor="w", padx=16, pady=(0, 4))

        # Campo ELEVENLABS_API_KEY
        header_eleven = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        header_eleven.pack(fill="x", padx=16, pady=(0, 2))

        lbl_eleven = ctk.CTkLabel(
            header_eleven,
            text="ELEVENLABS_API_KEY (Opcional - Voz de cine):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_eleven.pack(side="left")

        eleven_key_val = config.get_elevenlabs_api_key()
        eleven_status_text = "● Configurada" if eleven_key_val else "○ No configurada"
        eleven_status_color = "#10b981" if eleven_key_val else "#64748b"

        self.lbl_eleven_status = ctk.CTkLabel(
            header_eleven,
            text=eleven_status_text,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=eleven_status_color
        )
        self.lbl_eleven_status.pack(side="right")

        self.entry_eleven_key = ctk.CTkEntry(
            self.scroll_frame,
            placeholder_text="xi_api_key...",
            height=32,
            show="*",
            fg_color="#07090f",
            border_color="#1f2c4a",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.entry_eleven_key.pack(fill="x", padx=16, pady=(0, 2))
        if eleven_key_val:
            self.entry_eleven_key.insert(0, eleven_key_val)

        row_eleven_links = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_eleven_links.pack(fill="x", padx=16, pady=(0, 6))

        self.btn_eleven_toggle = ctk.CTkButton(
            row_eleven_links,
            text="👁 Ver",
            width=65,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Consolas", size=10),
            command=self._toggle_eleven_visibility
        )
        self.btn_eleven_toggle.pack(side="left")

        btn_eleven_link = ctk.CTkButton(
            row_eleven_links,
            text="🔗 Obtener clave en ElevenLabs (elevenlabs.io)",
            width=260,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=10, underline=True),
            command=lambda: webbrowser.open("https://elevenlabs.io")
        )
        btn_eleven_link.pack(side="right")

        # Selector de voz masculina táctica para ElevenLabs
        row_eleven_voice = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_eleven_voice.pack(fill="x", padx=16, pady=(0, 8))

        lbl_el_voice = ctk.CTkLabel(
            row_eleven_voice,
            text="Voz masculina táctica ElevenLabs:",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#94a3b8"
        )
        lbl_el_voice.pack(side="left")

        self.menu_eleven_voice = ctk.CTkOptionMenu(
            row_eleven_voice,
            values=["George (Profunda / Táctica)", "Adam (Neutra / Natural)"],
            width=210,
            height=26,
            fg_color="#0e1526",
            button_color="#16223d",
            dropdown_fg_color="#080c16",
            text_color="#f8fafc",
            font=get_font_badge()
        )
        self.menu_eleven_voice.pack(side="right")
        current_el_vid = config.get_elevenlabs_voice_id()
        if "adam" in current_el_vid.lower() or current_el_vid == "pNInz6obpgDQGcFmaJgB":
            self.menu_eleven_voice.set("Adam (Neutra / Natural)")
        else:
            self.menu_eleven_voice.set("George (Profunda / Táctica)")

        # Inicializar advertencia de estado de voz
        self._refresh_tts_warning()

        # ================= SECCIÓN 7: TARJETA FAILOVER =================
        failover_card = ctk.CTkFrame(
            self.scroll_frame,
            fg_color="#08101a",
            border_color="#132742",
            border_width=1,
            corner_radius=8
        )
        failover_card.pack(fill="x", padx=16, pady=(4, 10))

        lbl_failover = ctk.CTkLabel(
            failover_card,
            text="⚡ ALTA DISPONIBILIDAD & FAILOVER INTELIGENTE:\n"
                 "• IA: Si configuras ambas claves (Gemini y Groq), VEX conmutará de forma invisible ante errores 429 de cuota.\n"
                 "• Voz: Si la cuota mensual de ElevenLabs se agota, VEX conmutará a Edge-TTS sin cortar la conversación.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#7dd3fc",
            justify="left",
            wraplength=480
        )
        lbl_failover.pack(padx=12, pady=8)

        # ================= BOTONES DE ACCIÓN (FIJOS AL PIE) =================
        actions = ctk.CTkFrame(self.container, fg_color="transparent")
        actions.pack(fill="x", padx=16, pady=(6, 8))

        self.btn_cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            width=120,
            height=34,
            fg_color="#141824",
            hover_color="#1f2638",
            border_color="#2b354d",
            border_width=1,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left", padx=6)

        self.btn_save = ctk.CTkButton(
            actions,
            text="Guardar Configuración",
            width=200,
            height=34,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            border_color="#60a5fa",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=self._save_config
        )
        self.btn_save.pack(side="right", padx=6)

    def _on_provider_segment_changed(self, selection: str):
        selected_prov = "gemini" if "gemini" in selection.lower() else "groq"
        self.current_provider = selected_prov

        models = config.get_available_models(selected_prov)
        self.menu_model.configure(values=models)
        preferred = config.get_preferred_model(selected_prov)
        if preferred in models:
            self.menu_model.set(preferred)
        else:
            self.menu_model.set(models[0])

    def _on_tts_segment_changed(self, selection: str):
        self.current_tts_engine = "elevenlabs" if "elevenlabs" in selection.lower() else "edge-tts"
        self._refresh_tts_warning()

    def _refresh_tts_warning(self):
        is_eleven = "elevenlabs" in self.seg_tts.get().lower()
        has_key = bool(self.entry_eleven_key.get().strip())

        if is_eleven and not has_key:
            self.lbl_tts_notice.configure(
                text="⚠️ Has seleccionado ElevenLabs pero no has configurado una API Key. VEX utilizará Edge-TTS como respaldo hasta que ingreses tu clave.",
                text_color="#f59e0b"
            )
        elif is_eleven and has_key:
            self.lbl_tts_notice.configure(
                text="✔ ElevenLabs activo como motor primario (con respaldo automático a Edge-TTS si se agota la cuota).",
                text_color="#10b981"
            )
        else:
            self.lbl_tts_notice.configure(
                text="✔ Edge-TTS activo: Motor gratuito, ilimitado y ágil (+15% cadencia humana).",
                text_color="#94a3b8"
            )

    def _toggle_gemini_visibility(self):
        self.show_gemini_pass = not self.show_gemini_pass
        self.entry_gemini_key.configure(show="" if self.show_gemini_pass else "*")
        self.btn_gem_toggle.configure(text="🔒 Ocultar" if self.show_gemini_pass else "👁 Ver")

    def _toggle_groq_visibility(self):
        self.show_groq_pass = not self.show_groq_pass
        self.entry_groq_key.configure(show="" if self.show_groq_pass else "*")
        self.btn_groq_toggle.configure(text="🔒 Ocultar" if self.show_groq_pass else "👁 Ver")

    def _toggle_eleven_visibility(self):
        self.show_eleven_pass = not self.show_eleven_pass
        self.entry_eleven_key.configure(show="" if self.show_eleven_pass else "*")
        self.btn_eleven_toggle.configure(text="🔒 Ocultar" if self.show_eleven_pass else "👁 Ver")

    def _save_config(self):
        new_user = self.entry_user.get().strip() or "Oscar"
        new_gemini = self.entry_gemini_key.get().strip()
        new_groq = self.entry_groq_key.get().strip()
        new_eleven = self.entry_eleven_key.get().strip()
        chosen_model = self.menu_model.get().strip()

        # Guardar usuario
        config.set_user_name(new_user)

        # Guardar claves
        if new_gemini:
            config.save_gemini_api_key(new_gemini)
        if new_groq:
            config.save_groq_api_key(new_groq)
        if new_eleven:
            config.save_elevenlabs_api_key(new_eleven)

        # Guardar proveedor y modelo LLM
        config.set_active_provider(self.current_provider)
        if chosen_model:
            config.set_preferred_model(chosen_model, self.current_provider)

        # Guardar motor de voz y voz de ElevenLabs
        tts_choice = "elevenlabs" if "elevenlabs" in self.seg_tts.get().lower() else "edge-tts"
        config.set_tts_engine(tts_choice)

        chosen_voice_str = self.menu_eleven_voice.get()
        if "adam" in chosen_voice_str.lower():
            config.set_elevenlabs_voice_id("pNInz6obpgDQGcFmaJgB")
        else:
            config.set_elevenlabs_voice_id("JBFqnCBsd6RMkjVDRZzb")

        if self.on_save_callback:
            try:
                self.on_save_callback(self.current_provider, chosen_model, new_user)
            except Exception as e:
                print(f"[BYOK Modal] Error en callback on_save: {e}")

        self.destroy()
