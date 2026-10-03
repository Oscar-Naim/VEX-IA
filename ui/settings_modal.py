"""
LYAXIS labs™ - Modal de Configuración y Ajustes de IA (ui/settings_modal.py)
Panel de control centralizado y moderno para VEX HUD:
- Selector de Perfil de Operador Multi-Usuario (Oscar, crear nuevo, memoria persistente).
- Selector de Proveedor de IA (Google Gemini ✦ / Groq Cloud ⚡).
- Selector dinámico de Modelo de Lenguaje según el proveedor activo.
- Gestión de Credenciales y Claves API (BYOK - Bring Your Own Key).
- Interruptor de Modo Charla Continua Manos Libres (Continuous Listening).
"""
import os
import sys
import customtkinter as ctk
import tkinter as tk
from typing import Optional, Callable, Dict, Any, List

import config
from memory.manager import get_memory_manager
from ui.byok_modal import ApiKeyModal
from ui.profile_modal import UserProfileModal
from ui.styles import (
    BG_ROOT,
    BORDER_SUBTLE,
    BORDER_CARD,
    BORDER_BLUE,
    BORDER_CYAN,
    BORDER_GREEN,
    ACCENT_CYAN,
    ACCENT_CYAN_GLOW,
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_GREEN,
    ACCENT_AMBER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    TEXT_CYAN,
    TEXT_WHITE,
    get_font_badge
)


class SettingsModal(ctk.CTkToplevel):
    """
    Diálogo modal de Ajustes del Sistema para VEX HUD.
    Agrupa todos los controles técnicos liberando la cabecera principal:
    - Gestión de Operador / Perfiles
    - Selección de Motor IA (Gemini / Groq)
    - Selector dinámico de modelo
    - Claves BYOK
    - Switch de Charla Continua
    """

    def __init__(self, master, on_close_callback: Optional[Callable[[], None]] = None):
        super().__init__(master)
        self.master = master
        self.on_close_callback = on_close_callback

        self.title("LYAXIS labs™ // VEX - Panel de Control & Ajustes")
        self.geometry("560x700")
        self.minsize(500, 620)
        self.configure(fg_color="#070a12")

        # Configuración modal flotante
        self.transient(master)
        self.grab_set()

        # Cache de estado
        self.active_provider = getattr(self.master.agent, "get_active_provider", lambda: config.get_active_provider())()
        self.active_model = getattr(self.master.agent, "active_model", config.get_preferred_model(self.active_provider))
        self.hands_free_active = getattr(self.master, "hands_free_mode", config.get_hands_free())

        self._build_ui()
        self._center_window(master)

    def _center_window(self, master):
        """Centra la ventana modal sobre la ventana principal del HUD."""
        try:
            self.update_idletasks()
            mx = master.winfo_x()
            my = master.winfo_y()
            mw = master.winfo_width()
            mh = master.winfo_height()

            w = 560
            h = 700
            x = max(40, mx + (mw - w) // 2)
            y = max(40, my + (mh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # Contenedor exterior con borde neón cian/azul cibernético
        self.main_frame = ctk.CTkFrame(
            self,
            fg_color="#070a12",
            border_color="#1d4ed8",
            border_width=1.5,
            corner_radius=16
        )
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # ---------------- CABECERA DEL MODAL ----------------
        header_bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_bar.pack(fill="x", padx=18, pady=(16, 10))

        title_left = ctk.CTkFrame(header_bar, fg_color="transparent")
        title_left.pack(side="left", fill="y")

        lbl_badge = ctk.CTkLabel(
            title_left,
            text="⚡ LYAXIS labs™ // SISTEMA OPERATIVO TÁCTICO",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_badge.pack(anchor="w")

        lbl_title = ctk.CTkLabel(
            title_left,
            text="⚙ AJUSTES DEL SISTEMA // VEX CORE",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_title.pack(anchor="w", pady=(1, 0))

        btn_close_top = ctk.CTkButton(
            header_bar,
            text="✕",
            width=28,
            height=28,
            fg_color="#0e1726",
            hover_color="#ef4444",
            text_color="#94a3b8",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6,
            command=self._on_close
        )
        btn_close_top.pack(side="right", anchor="ne")

        # Separador tenue
        sep = ctk.CTkFrame(self.main_frame, height=1, fg_color="#131c2e")
        sep.pack(fill="x", padx=18, pady=(0, 10))

        # Contenedor scrolleable para todas las secciones de ajustes
        scroll_content = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#1e293b",
            scrollbar_button_hover_color=ACCENT_CYAN
        )
        scroll_content.pack(fill="both", expand=True, padx=8, pady=(0, 10))

        # ================= 1. PERFIL DE OPERADOR & MEMORIA =================
        self._build_profile_section(scroll_content)

        # ================= 2. MOTOR DE IA (GEMINI / GROQ) =================
        self._build_provider_section(scroll_content)

        # ================= 3. SELECTOR DE MODELO =================
        self._build_model_section(scroll_content)

        # ================= 4. GESTIÓN DE CLAVES API (BYOK) =================
        self._build_byok_section(scroll_content)

        # ================= 5. MODO CHARLA CONTINUA =================
        self._build_hands_free_section(scroll_content)

        # ================= 6. TEMA VISUAL CYBER-PREMIUM =================
        self._build_theme_section(scroll_content)

        # ---------------- PIE CON BOTONES DE ACCIÓN ----------------
        footer_bar = ctk.CTkFrame(self.main_frame, fg_color="#050811", height=54, corner_radius=10)
        footer_bar.pack(fill="x", padx=14, pady=(0, 12))

        btn_apply = ctk.CTkButton(
            footer_bar,
            text="Guardar y Aplicar Cambios",
            height=36,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=8,
            command=self._on_close
        )
        btn_apply.pack(side="right", padx=12, pady=9)

        lbl_footer_status = ctk.CTkLabel(
            footer_bar,
            text="● Configuración local persistida en tiempo real",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#34d399"
        )
        lbl_footer_status.pack(side="left", padx=14, pady=9)

    # ================= CONSTRUCTORES DE SECCIONES =================

    def _build_profile_section(self, parent):
        """Sección 1: Selector y gestión de perfiles de memoria multi-usuario."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(12, 4))

        lbl_sec = ctk.CTkLabel(
            header_row,
            text="👤 PERFIL DE OPERADOR & MEMORIA PERSISTENTE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_sec.pack(side="left")

        lbl_desc = ctk.CTkLabel(
            card,
            text="VEX asocia tus tareas, recordatorios, rutinas matutinas y estilo de conversación a tu perfil individual.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=14, pady=(0, 8))

        controls_row = ctk.CTkFrame(card, fg_color="transparent")
        controls_row.pack(fill="x", padx=14, pady=(0, 14))

        # Menú desplegable de perfiles registrados
        self.menu_profiles = ctk.CTkOptionMenu(
            controls_row,
            values=["Cargando..."],
            command=self._on_profile_selected,
            height=32,
            fg_color="#0e172a",
            button_color="#1e293b",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#070a12",
            dropdown_hover_color="#1e293b",
            dropdown_text_color="#f8fafc",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.menu_profiles.pack(side="left", fill="x", expand=True, padx=(0, 8))

        # Botón para crear nuevo perfil
        btn_new_profile = ctk.CTkButton(
            controls_row,
            text="➕ Nuevo Perfil",
            width=120,
            height=32,
            fg_color="#082f49",
            hover_color="#0c4a6e",
            border_color="#0284c7",
            border_width=1,
            corner_radius=8,
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._open_new_profile_modal
        )
        btn_new_profile.pack(side="right")

        self.refresh_profiles_list()

    def _build_provider_section(self, parent):
        """Sección 2: Selector del motor de IA principal (Google Gemini vs Groq Cloud)."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(12, 4))

        lbl_sec = ctk.CTkLabel(
            header_row,
            text="🧠 MOTOR DE INTELIGENCIA ARTIFICIAL",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_sec.pack(side="left")

        lbl_desc = ctk.CTkLabel(
            card,
            text="Conmuta en caliente el proveedor cognitivo. Failover inteligente conmutará automáticamente si uno falla.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=14, pady=(0, 10))

        prov_row = ctk.CTkFrame(card, fg_color="transparent")
        prov_row.pack(fill="x", padx=14, pady=(0, 14))

        # Botón Gemini
        self.btn_prov_gemini = ctk.CTkButton(
            prov_row,
            text="✦ GOOGLE GEMINI",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=lambda: self._set_provider("gemini")
        )
        self.btn_prov_gemini.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Botón Groq
        self.btn_prov_groq = ctk.CTkButton(
            prov_row,
            text="⚡ GROQ CLOUD LPU",
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=lambda: self._set_provider("groq")
        )
        self.btn_prov_groq.pack(side="right", fill="x", expand=True, padx=(6, 0))

        self._update_provider_buttons()

    def _build_model_section(self, parent):
        """Sección 3: Selector dinámico de modelo según el proveedor activo."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(12, 4))

        lbl_sec = ctk.CTkLabel(
            header_row,
            text="🤖 SELECTOR DE MODELO DE LENGUAJE",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_sec.pack(side="left")

        lbl_desc = ctk.CTkLabel(
            card,
            text="Variantes optimizadas para baja latencia (Flash/Instant) o máxima precisión analítica (Versatile/Pro).",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=14, pady=(0, 10))

        model_row = ctk.CTkFrame(card, fg_color="transparent")
        model_row.pack(fill="x", padx=14, pady=(0, 14))

        self.menu_model = ctk.CTkOptionMenu(
            model_row,
            values=["Cargando..."],
            command=self._on_model_selected,
            height=34,
            fg_color="#0e172a",
            button_color="#1e293b",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#070a12",
            dropdown_hover_color="#1e293b",
            dropdown_text_color="#f8fafc",
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold")
        )
        self.menu_model.pack(fill="x", expand=True)

        self._refresh_model_options()

    def _build_byok_section(self, parent):
        """Sección 4: Estado de claves de API (BYOK) y acceso al gestor de credenciales."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        header_row = ctk.CTkFrame(card, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(12, 4))

        lbl_sec = ctk.CTkLabel(
            header_row,
            text="🔑 CLAVES API & MOTORES DE VOZ (BYOK)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#fbbf24"
        )
        lbl_sec.pack(side="left")

        # Fila de estados de credenciales
        status_row = ctk.CTkFrame(card, fg_color="transparent")
        status_row.pack(fill="x", padx=14, pady=(2, 8))

        has_gemini = bool(config.get_gemini_api_key())
        has_groq = bool(config.get_groq_api_key())

        lbl_st_gemini = ctk.CTkLabel(
            status_row,
            text=f"✦ Gemini: {'✔ Vinculada' if has_gemini else '⚠️ Sin clave'}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#34d399" if has_gemini else "#f59e0b"
        )
        lbl_st_gemini.pack(side="left", padx=(0, 14))

        lbl_st_groq = ctk.CTkLabel(
            status_row,
            text=f"⚡ Groq: {'✔ Vinculada' if has_groq else '⚠️ Sin clave'}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#34d399" if has_groq else "#f59e0b"
        )
        lbl_st_groq.pack(side="left")

        btn_manage_keys = ctk.CTkButton(
            card,
            text="⚙ Gestionar Claves API (BYOK) & Voces ElevenLabs",
            height=34,
            fg_color="#1e1808",
            hover_color="#29200b",
            border_color="#f59e0b",
            border_width=1.2,
            corner_radius=8,
            text_color="#fbbf24",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._open_byok_modal
        )
        btn_manage_keys.pack(fill="x", padx=14, pady=(0, 14))

    def _build_hands_free_section(self, parent):
        """Sección 5: Interruptor del Modo Charla Continua (Hands-Free)."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        info_box = ctk.CTkFrame(row, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True)

        lbl_sec = ctk.CTkLabel(
            info_box,
            text="⚡ MODO CHARLA CONTINUA (MANOS LIBRES)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_sec.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            info_box,
            text="VEX reabre la escucha automáticamente tras responder para conversar sin pulsar el botón.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
            wraplength=340,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        self.switch_hands_free = ctk.CTkSwitch(
            row,
            text="ACTIVO" if self.hands_free_active else "INACTIVO",
            command=self._on_hands_free_toggled,
            onvalue=True,
            offvalue=False,
            progress_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=ACCENT_CYAN if self.hands_free_active else TEXT_MUTED
        )
        if self.hands_free_active:
            self.switch_hands_free.select()
        else:
            self.switch_hands_free.deselect()
        self.switch_hands_free.pack(side="right", padx=(8, 0))

    def _build_theme_section(self, parent):
        """Sección 6: Selector de Temas Visuales Cyber-Premium."""
        card = ctk.CTkFrame(parent, fg_color="#0b101c", border_color="#18233b", border_width=1, corner_radius=12)
        card.pack(fill="x", padx=8, pady=6)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=12)

        info_box = ctk.CTkFrame(row, fg_color="transparent")
        info_box.pack(side="left", fill="both", expand=True)

        lbl_sec = ctk.CTkLabel(
            info_box,
            text="🎨 TEMA VISUAL CYBER-PREMIUM",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_sec.pack(anchor="w")

        lbl_desc = ctk.CTkLabel(
            info_box,
            text="Personaliza la paleta estética del visor y los acentos luminosos de VEX.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=TEXT_MUTED,
            wraplength=300,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        theme_options = [
            "✦ Electric Cyan (LYAXIS)",
            "🟣 Cyber Synth (Morado)",
            "🟢 Matrix Green"
        ]

        from ui.styles import get_current_theme
        curr_theme = get_current_theme()
        curr_name = curr_theme.get("name", "Electric Cyan (LYAXIS)")
        if "Synth" in curr_name:
            default_choice = "🟣 Cyber Synth (Morado)"
        elif "Matrix" in curr_name:
            default_choice = "🟢 Matrix Green"
        else:
            default_choice = "✦ Electric Cyan (LYAXIS)"

        self.menu_theme = ctk.CTkOptionMenu(
            row,
            values=theme_options,
            command=self._on_theme_selected,
            width=185,
            height=30,
            fg_color="#0f172a",
            button_color="#1e293b",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#070a12",
            dropdown_hover_color="#1e293b",
            dropdown_text_color="#f8fafc",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        self.menu_theme.set(default_choice)
        self.menu_theme.pack(side="right", padx=(8, 0))

    def _on_theme_selected(self, choice: str):
        """Aplica el tema seleccionado en caliente en la UI de VEX."""
        theme_map = {
            "✦ Electric Cyan (LYAXIS)": "electric_cyan",
            "🟣 Cyber Synth (Morado)": "cyber_synth",
            "🟢 Matrix Green": "matrix_green"
        }
        theme_id = theme_map.get(choice, "electric_cyan")
        from ui.styles import set_active_theme
        theme = set_active_theme(theme_id)

        # Actualizar la ventana principal
        if hasattr(self.master, "apply_theme"):
            self.master.apply_theme(theme_id)
        elif hasattr(self.master, "visor_canvas"):
            self.master.visor_canvas.c_cyan_bright = theme["ACCENT_CYAN"]
            self.master.visor_canvas.c_cyan_glow = theme["ACCENT_CYAN_GLOW"]
            self.master.visor_canvas.c_cyan_core = theme["ACCENT_CYAN"]
            self.master.visor_canvas.set_ambient_state("idle")

    # ================= MÉTODOS DE CONTROL Y EVENTOS =================

    def refresh_profiles_list(self):
        """Carga y actualiza los perfiles disponibles en el selector."""
        try:
            manager = get_memory_manager()
            profiles = manager.list_profiles()
            vals = [f"👤 {p['display_name']}" for p in profiles]
            if not vals:
                vals = ["👤 Oscar (Default)"]
            self.menu_profiles.configure(values=vals)

            if manager.active_user:
                self.menu_profiles.set(f"👤 {manager.active_user.get('display_name', 'Operador')}")
            elif profiles:
                self.menu_profiles.set(f"👤 {profiles[0]['display_name']}")
            else:
                self.menu_profiles.set(vals[0])
        except Exception as e:
            print(f"[SettingsModal] Error al listar perfiles: {e}")

    def _on_profile_selected(self, choice: str):
        """Conmuta el perfil activo en el gestor de memoria persistente."""
        display_name = choice.replace("👤", "").strip()
        manager = get_memory_manager()
        profiles = manager.list_profiles()
        matched = next((p for p in profiles if p["display_name"].lower() == display_name.lower()), None)
        if matched:
            user_id = matched["user_id"]
            if manager.active_user_id != user_id:
                manager.switch_user(user_id)
                config.set_user_name(matched["display_name"])
                if hasattr(self.master, "_add_message_card"):
                    self.master._add_message_card(
                        "system",
                        f"👤 Perfil activo cambiado a: {matched['display_name']} ({matched.get('voice_speed', '+15%')}). Tareas y rutinas sincronizadas."
                    )
                if hasattr(self.master, "visor_canvas"):
                    self.master.visor_canvas.set_expression("happy", duration=3.0)

    def _open_new_profile_modal(self):
        """Abre el diálogo modal de registro de nuevo operador."""
        def on_created(profile):
            self.refresh_profiles_list()
            name = profile.get("display_name", "Operador")
            if hasattr(self.master, "_add_message_card"):
                self.master._add_message_card("system", f"✅ Nuevo perfil registrado y activado: {name}.")

        UserProfileModal(self, on_save_callback=on_created)

    def _set_provider(self, prov_name: str):
        """Cambia el proveedor activo y actualiza los modelos."""
        self.active_provider = prov_name
        if hasattr(self.master, "agent"):
            self.master.agent.set_provider(prov_name)
        config.set_active_provider(prov_name)

        self._update_provider_buttons()
        self._refresh_model_options()

        if hasattr(self.master, "_add_message_card"):
            active_m = getattr(self.master.agent, "active_model", "")
            self.master._add_message_card(
                "system",
                f"Motor de IA cambiado a {prov_name.upper()} ({active_m})."
            )

    def _update_provider_buttons(self):
        """Actualiza el estilo visual de los botones de Gemini y Groq."""
        if self.active_provider == "gemini":
            self.btn_prov_gemini.configure(
                fg_color="#0e2238",
                border_color=BORDER_CYAN,
                border_width=1.5,
                text_color=ACCENT_CYAN
            )
            self.btn_prov_groq.configure(
                fg_color="#0e1526",
                border_color="#18233b",
                border_width=1,
                text_color=TEXT_MUTED
            )
        else:
            self.btn_prov_gemini.configure(
                fg_color="#0e1526",
                border_color="#18233b",
                border_width=1,
                text_color=TEXT_MUTED
            )
            self.btn_prov_groq.configure(
                fg_color="#1e1808",
                border_color="#f59e0b",
                border_width=1.5,
                text_color="#fbbf24"
            )

    def _refresh_model_options(self):
        """Actualiza la lista de modelos según el proveedor activo."""
        try:
            if hasattr(self.master, "agent") and hasattr(self.master.agent, "AVAILABLE_MODELS"):
                models = self.master.agent.AVAILABLE_MODELS
                current_model = self.master.agent.active_model
            else:
                if self.active_provider == "groq":
                    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
                else:
                    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
                current_model = models[0]

            self.menu_model.configure(values=models)
            if current_model in models:
                self.menu_model.set(current_model)
            elif models:
                self.menu_model.set(models[0])
        except Exception as e:
            print(f"[SettingsModal] Error al refrescar modelos: {e}")

    def _on_model_selected(self, model_choice: str):
        """Maneja la selección de modelo de lenguaje."""
        if hasattr(self.master, "agent"):
            success = self.master.agent.set_model(model_choice)
            if success:
                config.set_preferred_model(model_choice, self.active_provider)
                if hasattr(self.master, "_add_message_card"):
                    self.master._add_message_card(
                        "system",
                        f"Modelo vinculado: '{model_choice}' ({self.active_provider.upper()})"
                    )

    def _open_byok_modal(self):
        """Abre el gestor completo de claves BYOK."""
        def on_saved(provider, model, user_name):
            if hasattr(self.master, "agent"):
                self.master.agent.reload_api_key()
                self.master.agent.set_provider(provider)
                if model:
                    self.master.agent.set_model(model)
            self.active_provider = provider
            self._update_provider_buttons()
            self._refresh_model_options()
            self.refresh_profiles_list()

        ApiKeyModal(self.master, on_save_callback=on_saved)

    def _on_hands_free_toggled(self):
        """Alterna el modo charla continua manos libres en la ventana principal."""
        val = self.switch_hands_free.get()
        self.hands_free_active = val
        self.switch_hands_free.configure(
            text="ACTIVO" if val else "INACTIVO",
            text_color=ACCENT_CYAN if val else TEXT_MUTED
        )
        if val:
            if hasattr(self.master, "_enable_hands_free"):
                self.master._enable_hands_free()
        else:
            if hasattr(self.master, "_disable_hands_free"):
                self.master._disable_hands_free(user_message=True)

    def _on_close(self):
        """Cierra el diálogo modal y devuelve el foco al chat."""
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        if self.on_close_callback:
            self.on_close_callback()
        try:
            if hasattr(self.master, "entry_prompt"):
                self.master.entry_prompt.focus()
        except Exception:
            pass
