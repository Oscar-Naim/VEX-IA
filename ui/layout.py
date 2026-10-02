"""
LYAXIS labs™ - Layout Principal de 3 Zonas (Icon Rail, Mis Chats y Chat Canvas)
Interfaz gráfica profesional Cyber-Premium para VEX inspirada en ChatGPT/JARVIS:
- Zona A: Riel lateral de iconos minimalistas (60px fija).
- Zona B: Barra lateral de conversaciones 'Mis Chats' (240px colapsable con búsqueda y gestión).
- Zona C: Área central con Header táctico, Visor Robótico animado, flujo de chat y cápsula flotante.
"""
import os
import sys
import time
import datetime
import threading
import webbrowser
from typing import Optional, List, Dict
import customtkinter as ctk
from tkinter import filedialog

import config
from ui.styles import (
    BG_ROOT, BG_RAIL, BG_CHATS_PANEL, BG_HEADER, BG_CHAT_AREA, BG_INPUT_CAPSULE,
    BORDER_SUBTLE, BORDER_CARD, BORDER_BLUE, BORDER_CYAN, BORDER_GREEN,
    ACCENT_CYAN, ACCENT_CYAN_GLOW, ACCENT_BLUE, ACCENT_BLUE_HOVER, ACCENT_GREEN,
    ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_CYAN, TEXT_WHITE,
    get_font_title, get_font_subtitle, get_font_badge, get_font_body, get_font_code
)
from ui.chat_bubbles import UserMessageCard, VexResponseCard, ToolActionCard
from ui.robot_visor import RobotVisorCanvas
from voice.tts import TextToSpeechEngine
from voice.stt import SpeechToTextListener
from voice.manager import VoiceAssistantManager, AssistantState
from agent.gemini_agent import GeminiAgent
from agent.router import LocalIntentRouter
from tools.system_tools import open_url, launch_application, control_media


class ApiKeyModal(ctk.CTkToplevel):
    """Modal de configuración de credenciales BYOK (Bring Your Own Key) y nombre de usuario."""
    def __init__(self, master, on_save_callback=None):
        super().__init__(master)
        self.on_save_callback = on_save_callback

        self.title("LYAXIS labs™ // VEX - Configuración BYOK")
        self.geometry("520x430")
        self.resizable(False, False)
        self.configure(fg_color=BG_ROOT)

        self.transient(master)
        self.grab_set()

        self.container = ctk.CTkFrame(
            self,
            fg_color="#0b0f19",
            border_color=BORDER_BLUE,
            border_width=1,
            corner_radius=12
        )
        self.container.pack(fill="both", expand=True, padx=16, pady=16)

        self.lbl_title = ctk.CTkLabel(
            self.container,
            text="⚙ CONFIGURACIÓN BYOK // VEX NEXUS",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=ACCENT_CYAN
        )
        self.lbl_title.pack(pady=(16, 4))

        self.lbl_desc = ctk.CTkLabel(
            self.container,
            text="Credenciales personales almacenadas de forma local y segura en config/user_config.json.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY,
            justify="center"
        )
        self.lbl_desc.pack(pady=(0, 14))

        # Nombre de Operador
        self.lbl_user = ctk.CTkLabel(
            self.container,
            text="Nombre de Operador:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_user.pack(anchor="w", padx=36, pady=(0, 2))

        self.entry_user = ctk.CTkEntry(
            self.container,
            placeholder_text="Ej. Oscar",
            width=430,
            height=34,
            fg_color="#07090f",
            border_color="#1f2c4a",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_user.pack(pady=(0, 8))
        self.entry_user.insert(0, config.get_user_name())

        # Gemini API Key
        self.lbl_key = ctk.CTkLabel(
            self.container,
            text="Google Gemini API Key (BYOK):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        self.lbl_key.pack(anchor="w", padx=36, pady=(0, 2))

        self.entry_key = ctk.CTkEntry(
            self.container,
            placeholder_text="AIzaSy...",
            width=430,
            height=34,
            show="*",
            fg_color="#07090f",
            border_color=BORDER_BLUE,
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self.entry_key.pack(pady=(0, 2))

        curr_key = config.get_api_key()
        if curr_key:
            self.entry_key.insert(0, curr_key)

        self.show_pass = False
        self.btn_toggle = ctk.CTkButton(
            self.container,
            text="👁 Mostrar clave",
            width=110,
            height=20,
            fg_color="transparent",
            hover_color="#141a29",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Consolas", size=10),
            command=self._toggle_visibility
        )
        self.btn_toggle.pack(pady=(2, 6))

        self.btn_link = ctk.CTkButton(
            self.container,
            text="🔗 Obtener clave gratuita en Google AI Studio",
            width=320,
            height=24,
            fg_color="#101827",
            hover_color="#1e293b",
            border_color="#1e293b",
            border_width=1,
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=11, underline=True),
            command=lambda: webbrowser.open("https://aistudio.google.com/app/apikey")
        )
        self.btn_link.pack(pady=4)

        # Botones de Acción
        actions = ctk.CTkFrame(self.container, fg_color="transparent")
        actions.pack(pady=(14, 8))

        self.btn_cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            width=110,
            height=32,
            fg_color="#141824",
            hover_color="#1f2638",
            border_color="#2b354d",
            border_width=1,
            text_color=TEXT_SECONDARY,
            font=ctk.CTkFont(family="Consolas", size=11),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left", padx=8)

        self.btn_save = ctk.CTkButton(
            actions,
            text="Guardar Configuración",
            width=170,
            height=32,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            border_color="#60a5fa",
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=self._save_config
        )
        self.btn_save.pack(side="left", padx=8)

    def _toggle_visibility(self):
        self.show_pass = not self.show_pass
        self.entry_key.configure(show="" if self.show_pass else "*")
        self.btn_toggle.configure(text="🔒 Ocultar clave" if self.show_pass else "👁 Mostrar clave")

    def _save_config(self):
        new_key = self.entry_key.get().strip()
        new_user = self.entry_user.get().strip() or "Oscar"

        config.set_user_name(new_user)
        if new_key:
            config.save_api_key(new_key)

        if self.on_save_callback:
            self.on_save_callback(new_key, new_user)
        self.destroy()


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Apariencia y configuración de ventana principal
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("LYAXIS labs™ // VEX HUD - Tactical AI Desktop")
        self.geometry("1100x820")
        self.minsize(860, 680)
        self.configure(fg_color=BG_ROOT)

        # Estado del botón de micrófono y pulso
        self._mic_breathing = False
        self._mic_pulse_state = 0

        # Estado de Modo Charla Continua Manos Libres
        self.hands_free_mode = config.get_hands_free()

        # Gestión de chats y sesiones
        self.chats_sidebar_visible = True
        self.chat_sessions: List[Dict] = [
            {
                "id": "session_default",
                "title": "Conversación activa",
                "date": "Hoy",
                "messages": []
            }
        ]
        self.active_session_id = "session_default"
        self._message_cards = []

        # Inicialización del orquestador de voz con Wake Word Detection
        self.voice_mgr = VoiceAssistantManager(
            on_state_change=self._on_assistant_state_change,
            on_user_command=self._on_user_voice_command,
            on_wake_flash=self._on_wake_flash_triggered
        )
        self.tts = self.voice_mgr.tts
        self.stt = self.voice_mgr.stt

        self.agent = GeminiAgent(
            on_tool_call=self._on_tool_executed,
            on_model_change=self._on_agent_model_change,
            on_emotion=self._on_agent_emotion
        )

        # Construcción visual de las 3 zonas del layout
        self._build_layout()

        # Atajos de teclado
        self.bind("<Escape>", lambda event: self._on_escape_pressed())

        # Iniciar ciclo de animación de respiración del micrófono
        self._update_mic_breathing()

        # Saludo táctico inicial
        self.after(400, self._initial_greeting)

    # ================= CONSTRUCCIÓN DEL LAYOUT DE 3 ZONAS =================

    def _build_layout(self):
        """Maqueta las 3 zonas: Zona A (Riel 60px), Zona B (Mis Chats 240px), Zona C (Canvas de Chat)."""

        # ---------------- ZONA A: RIEL DE ICONOS LATERAL (60px) ----------------
        self.frame_rail = ctk.CTkFrame(
            self,
            width=62,
            fg_color=BG_RAIL,
            corner_radius=0,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.frame_rail.pack(side="left", fill="y", padx=0, pady=0)
        self.frame_rail.pack_propagate(False)

        # Logo superior insignia VEX
        self.lbl_rail_logo = ctk.CTkLabel(
            self.frame_rail,
            text="⚡",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=ACCENT_CYAN
        )
        self.lbl_rail_logo.pack(side="top", pady=(16, 12))

        # Icono 1: Chat Activo (Destacado)
        self.btn_rail_chat = ctk.CTkButton(
            self.frame_rail,
            text="💬",
            width=44,
            height=44,
            fg_color="#0f2238",
            hover_color="#183659",
            border_color=BORDER_CYAN,
            border_width=1,
            corner_radius=10,
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=16),
            command=self._focus_chat
        )
        self.btn_rail_chat.pack(side="top", pady=6)

        # Separador tenue
        sep1 = ctk.CTkFrame(self.frame_rail, height=1, fg_color=BORDER_SUBTLE)
        sep1.pack(fill="x", padx=12, pady=8)

        # Icono 2: YouTube
        btn_yt = ctk.CTkButton(
            self.frame_rail,
            text="▶",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=lambda: self._handle_user_prompt("Abre YouTube")
        )
        btn_yt.pack(side="top", pady=4)

        # Icono 3: Spotify
        btn_sp = ctk.CTkButton(
            self.frame_rail,
            text="🎧",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            command=lambda: self._handle_user_prompt("Abre Spotify")
        )
        btn_sp.pack(side="top", pady=4)

        # Icono 4: Bloc de notas
        btn_notes = ctk.CTkButton(
            self.frame_rail,
            text="📝",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            command=lambda: self._handle_user_prompt("Abre el bloc de notas")
        )
        btn_notes.pack(side="top", pady=4)

        # Icono 5: Volumen (Subir / Bajar / Silencio)
        btn_vol = ctk.CTkButton(
            self.frame_rail,
            text="🔊",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            command=lambda: self._handle_user_prompt("Sube el volumen")
        )
        btn_vol.pack(side="top", pady=4)

        # Icono 6: Helado (Fun feature de visor)
        btn_ice = ctk.CTkButton(
            self.frame_rail,
            text="🍦",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=15),
            command=lambda: self._handle_user_prompt("Quiero un helado")
        )
        btn_ice.pack(side="top", pady=4)

        # Riel inferior: Ajustes BYOK e indicador ONLINE
        self.btn_rail_settings = ctk.CTkButton(
            self.frame_rail,
            text="⚙",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color="#94a3b8",
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=17),
            command=self._open_byok_modal
        )
        self.btn_rail_settings.pack(side="bottom", pady=12)

        # Indicador de estado ONLINE inferior
        self.lbl_rail_status = ctk.CTkLabel(
            self.frame_rail,
            text="●",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=ACCENT_GREEN
        )
        self.lbl_rail_status.pack(side="bottom", pady=(0, 2))

        # ---------------- ZONA B: BARRA LATERAL ("MIS CHATS" - 240px) ----------------
        self.frame_chats = ctk.CTkFrame(
            self,
            width=240,
            fg_color=BG_CHATS_PANEL,
            corner_radius=0,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.frame_chats.pack(side="left", fill="y", padx=0, pady=0)
        self.frame_chats.pack_propagate(False)

        # Cabecera de la barra de chats (Título + botón colapsar)
        frame_chats_header = ctk.CTkFrame(self.frame_chats, fg_color="transparent", height=46)
        frame_chats_header.pack(fill="x", padx=12, pady=(14, 8))

        lbl_chats_title = ctk.CTkLabel(
            frame_chats_header,
            text="MIS CHATS",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=TEXT_SECONDARY
        )
        lbl_chats_title.pack(side="left")

        btn_collapse = ctk.CTkButton(
            frame_chats_header,
            text="◀",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color="#161f30",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            command=self._toggle_chats_sidebar
        )
        btn_collapse.pack(side="right")

        # Botón estilo píldora neón: + Nueva conversación
        self.btn_new_chat = ctk.CTkButton(
            self.frame_chats,
            text="+ Nueva conversación",
            height=36,
            fg_color="#0e2238",
            hover_color="#163454",
            border_color=BORDER_CYAN,
            border_width=1.2,
            corner_radius=18,
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=self._create_new_chat
        )
        self.btn_new_chat.pack(fill="x", padx=12, pady=(0, 10))

        # Campo de búsqueda rápida con icono de lupa
        self.entry_search_chats = ctk.CTkEntry(
            self.frame_chats,
            placeholder_text="🔍 Buscar en chats...",
            height=32,
            fg_color="#060910",
            border_color="#182236",
            border_width=1,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.entry_search_chats.pack(fill="x", padx=12, pady=(0, 10))
        self.entry_search_chats.bind("<KeyRelease>", lambda e: self._filter_chat_list())

        # Lista scrolleable de chats guardados
        self.scroll_chats = ctk.CTkScrollableFrame(
            self.frame_chats,
            fg_color="transparent",
            corner_radius=0
        )
        self.scroll_chats.pack(fill="both", expand=True, padx=4, pady=(0, 8))

        # ---------------- ZONA C: ÁREA CENTRAL DE CONVERSACIÓN (CHAT CANVAS) ----------------
        self.frame_main_area = ctk.CTkFrame(
            self,
            fg_color=BG_ROOT,
            corner_radius=0
        )
        self.frame_main_area.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # 1. HEADER SUPERIOR TÁCTICO
        self.frame_header = ctk.CTkFrame(
            self.frame_main_area,
            height=92,
            fg_color=BG_HEADER,
            corner_radius=0,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.frame_header.pack(side="top", fill="x", padx=0, pady=0)
        self.frame_header.pack_propagate(False)

        # Lado izquierdo del header: Visor Robótico animado y títulos
        header_left = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        header_left.pack(side="left", fill="y", padx=12, pady=6)

        # Visor de Robot Expresivo compacto integrado en el header
        self.visor_canvas = RobotVisorCanvas(header_left, width=220, height=80)
        self.visor_canvas.pack(side="left", padx=(0, 10), pady=0)
        self.avatar_canvas = self.visor_canvas  # Alias para compatibilidad

        # Bloque de título y rol
        title_box = ctk.CTkFrame(header_left, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=14)

        self.lbl_app_title = ctk.CTkLabel(
            title_box,
            text="VEX // TACTICAL ASSISTANT",
            font=get_font_title(),
            text_color=ACCENT_CYAN
        )
        self.lbl_app_title.pack(anchor="w")

        self.lbl_app_sub = ctk.CTkLabel(
            title_box,
            text="LYAXIS labs™ // NEURAL DESKTOP CORE",
            font=get_font_subtitle(),
            text_color=TEXT_MUTED
        )
        self.lbl_app_sub.pack(anchor="w")

        # Lado derecho del header: Controles tácticos
        header_right = ctk.CTkFrame(self.frame_header, fg_color="transparent")
        header_right.pack(side="right", fill="y", padx=14, pady=18)

        # Botón BYOK
        self.btn_byok = ctk.CTkButton(
            header_right,
            text="⚙ BYOK",
            width=76,
            height=28,
            fg_color="#0e1626",
            hover_color="#18233b",
            border_color=BORDER_CYAN,
            border_width=1,
            text_color=ACCENT_CYAN,
            font=get_font_badge(),
            command=self._open_byok_modal
        )
        self.btn_byok.pack(side="right", padx=(6, 0))

        # Selector de modelo Gemini (Failover Pool)
        preferred_m = config.get_preferred_model()
        if preferred_m in self.agent.AVAILABLE_MODELS:
            self.agent.active_model = preferred_m

        self.menu_model = ctk.CTkOptionMenu(
            header_right,
            values=self.agent.AVAILABLE_MODELS,
            command=self._on_model_selected,
            width=150,
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
        self.menu_model.set(self.agent.active_model)
        self.menu_model.pack(side="right", padx=6)

        # Badge de versión VEX v3.0
        self.badge_version = ctk.CTkLabel(
            header_right,
            text="VEX v3.0",
            font=get_font_badge(),
            text_color="#64748b",
            fg_color="#0b101c",
            corner_radius=6,
            padx=8,
            pady=4
        )
        self.badge_version.pack(side="right", padx=6)

        # Switch / Botón de Modo Charla Continua
        hf_text = "⚡ CHARLA: ON" if self.hands_free_mode else "⚡ CHARLA: OFF"
        hf_bg = "#083344" if self.hands_free_mode else "#0e1526"
        hf_border = ACCENT_CYAN if self.hands_free_mode else BORDER_BLUE
        hf_fg = ACCENT_CYAN if self.hands_free_mode else TEXT_MUTED

        self.btn_hands_free = ctk.CTkButton(
            header_right,
            text=hf_text,
            width=120,
            height=28,
            fg_color=hf_bg,
            hover_color="#162b3d",
            border_color=hf_border,
            border_width=1.2,
            corner_radius=8,
            text_color=hf_fg,
            font=get_font_badge(),
            command=self._toggle_hands_free
        )
        self.btn_hands_free.pack(side="right", padx=6)

        # 2. ÁREA DE CHAT (CANVAS SCROLLEABLE CON RETÍCULA CIBERNÉTICA)
        self.chat_container = ctk.CTkScrollableFrame(
            self.frame_main_area,
            fg_color=BG_CHAT_AREA,
            corner_radius=0,
            scrollbar_button_color="#1e293b",
            scrollbar_button_hover_color=ACCENT_CYAN,
            scrollbar_fg_color="#070a12"
        )
        self.chat_container.pack(fill="both", expand=True, padx=20, pady=(10, 85))
        self.chat_container.bind("<Configure>", self._on_chat_resize)

        # Espaciador inferior dinámico para evitar que la cápsula flotante tape los últimos mensajes
        self._chat_bottom_spacer = ctk.CTkFrame(self.chat_container, height=85, fg_color="transparent")
        self._chat_bottom_spacer.pack(fill="x", pady=0)

        # 3. CÁPSULA FLOTANTE INFERIOR
        self.frame_floating_input = ctk.CTkFrame(
            self.frame_main_area,
            height=58,
            fg_color=BG_INPUT_CAPSULE,
            corner_radius=22,
            border_width=1.5,
            border_color=BORDER_CARD
        )
        # Posicionamiento flotante al pie
        self.frame_floating_input.place(relx=0.5, rely=0.94, anchor="center", relwidth=0.88)

        # Botón de adjuntar archivo o imagen (📎)
        self.btn_attach = ctk.CTkButton(
            self.frame_floating_input,
            text="📎",
            width=36,
            height=38,
            fg_color="transparent",
            hover_color="#18233b",
            text_color="#94a3b8",
            font=ctk.CTkFont(family="Segoe UI", size=15),
            command=self._on_attach_file
        )
        self.btn_attach.pack(side="left", padx=(10, 4), pady=8)

        # Campo de entrada de texto
        self.entry_prompt = ctk.CTkEntry(
            self.frame_floating_input,
            placeholder_text="Escribe o habla con VEX...",
            height=40,
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.entry_prompt.pack(side="left", fill="x", expand=True, padx=4, pady=8)
        self.entry_prompt.bind("<Return>", lambda event: self._on_send_text())
        self.entry_prompt.bind("<FocusIn>", lambda e: self.frame_floating_input.configure(border_color=BORDER_CYAN))
        self.entry_prompt.bind("<FocusOut>", lambda e: self.frame_floating_input.configure(border_color=BORDER_CARD))

        # Botón de micrófono (+ VOZ)
        self.btn_mic = ctk.CTkButton(
            self.frame_floating_input,
            text="🎙 VOZ",
            width=76,
            height=38,
            fg_color="#0e1b2e",
            hover_color="#192b45",
            border_color=BORDER_CYAN,
            border_width=1.2,
            corner_radius=16,
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            command=self._toggle_voice_input
        )
        self.btn_mic.pack(side="left", padx=4, pady=8)

        # Botón de envío con flecha azul eléctrica
        self.btn_send = ctk.CTkButton(
            self.frame_floating_input,
            text="➤",
            width=46,
            height=38,
            fg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            border_color="#60a5fa",
            border_width=1,
            corner_radius=16,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self._on_send_text
        )
        self.btn_send.pack(side="right", padx=(4, 10), pady=8)

        # Renderizar la lista de chats inicial
        self._render_chats_list()

    # ================= GESTIÓN DE CHATS LATERALES ("MIS CHATS") =================

    def _render_chats_list(self, filter_text: str = ""):
        """Renderiza los botones de sesión de chat en el panel lateral."""
        for child in self.scroll_chats.winfo_children():
            child.destroy()

        filt = filter_text.lower().strip()
        matched_sessions = [
            s for s in self.chat_sessions
            if not filt or filt in s["title"].lower()
        ]

        # Agrupar por sección
        lbl_today = ctk.CTkLabel(
            self.scroll_chats,
            text="Hoy",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_MUTED
        )
        lbl_today.pack(anchor="w", padx=8, pady=(4, 4))

        for session in matched_sessions:
            s_id = session["id"]
            is_active = (s_id == self.active_session_id)

            item_frame = ctk.CTkFrame(
                self.scroll_chats,
                fg_color="#0f192b" if is_active else "transparent",
                border_color=BORDER_CYAN if is_active else "#101624",
                border_width=1 if is_active else 0,
                corner_radius=8,
                height=36
            )
            item_frame.pack(fill="x", padx=4, pady=2)
            item_frame.pack_propagate(False)

            # Botón de selección de chat
            title_text = session["title"]
            if len(title_text) > 20:
                title_text = title_text[:18] + "..."

            btn_chat = ctk.CTkButton(
                item_frame,
                text=f"💬 {title_text}",
                fg_color="transparent",
                hover_color="#16233b",
                text_color=TEXT_PRIMARY if is_active else TEXT_SECONDARY,
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                command=lambda sid=s_id: self._switch_chat_session(sid)
            )
            btn_chat.pack(side="left", fill="both", expand=True, padx=(4, 0))

            # Botón de eliminar chat
            if len(self.chat_sessions) > 1:
                btn_del = ctk.CTkButton(
                    item_frame,
                    text="🗑",
                    width=22,
                    height=22,
                    fg_color="transparent",
                    hover_color="#2b141d",
                    text_color="#64748b",
                    font=ctk.CTkFont(family="Segoe UI", size=9),
                    command=lambda sid=s_id: self._delete_chat_session(sid)
                )
                btn_del.pack(side="right", padx=4)

    def _create_new_chat(self):
        """Crea una nueva conversación limpia y la establece como activa."""
        new_id = f"session_{int(time.time())}"
        new_session = {
            "id": new_id,
            "title": f"Chat {len(self.chat_sessions) + 1}",
            "date": "Hoy",
            "messages": []
        }
        self.chat_sessions.insert(0, new_session)
        self.active_session_id = new_id

        # Limpiar el contenedor de chat
        for child in self.chat_container.winfo_children():
            child.destroy()
        self._message_cards.clear()
        self._chat_bottom_spacer = ctk.CTkFrame(self.chat_container, height=85, fg_color="transparent")
        self._chat_bottom_spacer.pack(fill="x", pady=0)

        self._render_chats_list()
        self._initial_greeting()

    def _switch_chat_session(self, session_id: str):
        """Cambia a la sesión de chat seleccionada y reconstruye sus mensajes."""
        if self.active_session_id == session_id:
            return

        self.active_session_id = session_id
        self._render_chats_list()

        # Limpiar contenedor y recargar mensajes de la sesión
        for child in self.chat_container.winfo_children():
            child.destroy()
        self._message_cards.clear()
        self._chat_bottom_spacer = ctk.CTkFrame(self.chat_container, height=85, fg_color="transparent")
        self._chat_bottom_spacer.pack(fill="x", pady=0)

        curr_sess = next((s for s in self.chat_sessions if s["id"] == session_id), None)
        if curr_sess:
            for role, text, ts in curr_sess["messages"]:
                self._render_message_ui(role, text, timestamp=ts, persist=False)

    def _delete_chat_session(self, session_id: str):
        """Elimina una sesión de chat."""
        if len(self.chat_sessions) <= 1:
            return
        self.chat_sessions = [s for s in self.chat_sessions if s["id"] != session_id]
        if self.active_session_id == session_id:
            self.active_session_id = self.chat_sessions[0]["id"]
            self._switch_chat_session(self.active_session_id)
        else:
            self._render_chats_list()

    def _filter_chat_list(self):
        """Filtra la lista de chats en base al texto del buscador."""
        query = self.entry_search_chats.get()
        self._render_chats_list(filter_text=query)

    def _toggle_chats_sidebar(self):
        """Colapsa o expande la barra lateral de chats."""
        if self.chats_sidebar_visible:
            self.frame_chats.pack_forget()
            self.chats_sidebar_visible = False
        else:
            self.frame_chats.pack(side="left", fill="y", after=self.frame_rail)
            self.chats_sidebar_visible = True

    def _focus_chat(self):
        """Asegura que el panel de chat esté visible y enfoca la entrada."""
        if not self.chats_sidebar_visible:
            self._toggle_chats_sidebar()
        self.entry_prompt.focus()

    def _on_attach_file(self):
        """Abre un diálogo para seleccionar archivos o imágenes."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo para VEX",
            filetypes=[("Todos los archivos", "*.*"), ("Imágenes", "*.png;*.jpg;*.jpeg")]
        )
        if file_path:
            fname = os.path.basename(file_path)
            self._add_message_card("system", f"📎 Archivo adjuntado: '{fname}'")
            self.entry_prompt.insert("end", f" [Archivo: {fname}] ")

    # ================= RENDERIZADO DE MENSAJES Y CHAT FLOW =================

    def _add_message_card(self, role: str, text: str):
        """Añade un mensaje a la sesión activa y lo renderiza en pantalla."""
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self._render_message_ui(role, text, timestamp=ts, persist=True)

    def _render_message_ui(self, role: str, text: str, timestamp: str, persist: bool = True):
        """Construye el widget de burbuja correspondiente según el rol."""
        user_name = config.get_user_name()

        # Guardar en memoria de la sesión
        if persist:
            curr_sess = next((s for s in self.chat_sessions if s["id"] == self.active_session_id), None)
            if curr_sess:
                curr_sess["messages"].append((role, text, timestamp))
                # Renombrar chat según el primer comando del usuario
                if role == "user" and curr_sess["title"].startswith("Chat"):
                    clean_title = text.strip()[:24]
                    curr_sess["title"] = clean_title
                    self._render_chats_list()

        card = None
        if role == "user":
            card = UserMessageCard(self.chat_container, text=text, user_name=user_name, timestamp=timestamp)
            card.pack(fill="x", padx=(60, 8), pady=6, anchor="e")
        elif role == "agent":
            card = VexResponseCard(
                self.chat_container,
                raw_text=text,
                on_speak_again=self._on_re_speak,
                timestamp=timestamp
            )
            card.pack(fill="x", padx=(8, 60), pady=6, anchor="w")
        else:  # system / tool
            card = ToolActionCard(
                self.chat_container,
                action_title="EVENTO DE SISTEMA",
                detail=text,
                timestamp=timestamp
            )
            card.pack(fill="x", padx=20, pady=4)

        if card:
            # Mantener espaciador al final para que la cápsula flotante nunca tape el último mensaje
            if hasattr(self, "_chat_bottom_spacer"):
                try:
                    self._chat_bottom_spacer.pack_forget()
                    self._chat_bottom_spacer.pack(fill="x", pady=0)
                except Exception:
                    pass

            if hasattr(card, "update_wraplength"):
                self._message_cards.append(card)
                curr_width = self.chat_container.winfo_width()
                wrap = max(280, curr_width - 120) if curr_width > 100 else 480
                card.update_wraplength(wrap)

            # Habilitar desplazamiento de ratón en toda el área de la tarjeta
            self._bind_mousewheel_recursive(card)

        # Desplazamiento automático fluido y garantizado hacia el fondo
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        """Desplaza la vista al fondo de manera confiable en múltiples ciclos de cálculo de Tkinter."""
        def _do_scroll():
            try:
                self.chat_container.update_idletasks()
                self.chat_container._parent_canvas.yview_moveto(1.0)
            except Exception:
                pass

        _do_scroll()
        self.after(30, _do_scroll)
        self.after(120, _do_scroll)
        self.after(260, _do_scroll)

    def _bind_mousewheel_recursive(self, widget):
        """Propaga el evento de la rueda del ratón hacia el canvas de chat para desplazamiento sin interrupciones."""
        def _on_wheel(event):
            try:
                if sys.platform.startswith("win"):
                    delta = -int(event.delta / 40)
                    self.chat_container._parent_canvas.yview_scroll(delta, "units")
                else:
                    self.chat_container._parent_canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
            except Exception:
                pass

        try:
            widget.bind("<MouseWheel>", _on_wheel, add=True)
            widget.bind("<Button-4>", _on_wheel, add=True)
            widget.bind("<Button-5>", _on_wheel, add=True)
        except Exception:
            pass

        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _on_chat_resize(self, event):
        """Ajusta dinámicamente el ancho de envoltura al redimensionar la ventana."""
        new_width = event.width
        if new_width > 100:
            wrap = max(280, new_width - 120)
            for card in self._message_cards:
                try:
                    card.update_wraplength(wrap)
                except Exception:
                    pass

    def _on_re_speak(self, text_to_speak: str):
        """Vocaliza de nuevo un mensaje al pulsar 'Escuchar de nuevo'."""
        self.tts.speak(text_to_speak)

    # ================= SINCRONIZACIÓN Y ESTADOS DEL VISOR ROBÓTICO =================

    def _set_hud_state(self, state_name: str):
        """Actualiza el estado del visor robótico."""
        self.visor_canvas.set_state(state_name)

    def _on_agent_emotion(self, expression: str, icon: Optional[str], duration: float):
        """Callback invocado al detectarse una emoción en la respuesta del agente."""
        self.after(0, lambda: self._apply_visor_emotion(expression, icon, duration))

    def _apply_visor_emotion(self, expression: str, icon: Optional[str], duration: float):
        if icon:
            self.visor_canvas.show_icon(icon, duration=duration)
        if expression and expression != "idle":
            self.visor_canvas.set_expression(expression, duration=duration)

    def _update_mic_breathing(self):
        """Animación de respiración pulsante del botón de micrófono."""
        if self._mic_breathing:
            self._mic_pulse_state = (self._mic_pulse_state + 1) % 6
            pulse_colors = [
                ("#083344", "#00d9ff"),
                ("#0c4a6e", "#38bdf8"),
                ("#075985", "#7dd3fc"),
                ("#0c4a6e", "#38bdf8"),
                ("#083344", "#00d9ff"),
                ("#042f2e", "#00d9ff"),
            ]
            bg_col, border_col = pulse_colors[self._mic_pulse_state]
            try:
                self.btn_mic.configure(
                    fg_color=bg_col,
                    border_color=border_col,
                    text="🔴 ESCUCHA"
                )
            except Exception:
                pass
        self.after(200, self._update_mic_breathing)

    # ================= MODO CHARLA CONTINUA MANOS LIBRES =================

    def _toggle_hands_free(self):
        """Alterna el modo de conversación continua."""
        if self.hands_free_mode:
            self._disable_hands_free(user_message=True)
        else:
            self._enable_hands_free()

    def _enable_hands_free(self):
        self.hands_free_mode = True
        config.set_hands_free(True)
        self.voice_mgr.set_hands_free_mode(True)
        self.btn_hands_free.configure(
            text="⚡ CHARLA: ON",
            fg_color="#083344",
            border_color=ACCENT_CYAN,
            text_color=ACCENT_CYAN
        )
        self._add_message_card(
            "system",
            "⚡ Modo Charla Continua Activado. Di 'descansa' o presiona Esc para pausar."
        )
        if self.voice_mgr.state == AssistantState.STANDBY:
            self.voice_mgr.trigger_manual_listen()

    def _disable_hands_free(self, user_message: bool = True):
        self.hands_free_mode = False
        config.set_hands_free(False)
        self.voice_mgr.set_hands_free_mode(False)
        self.btn_hands_free.configure(
            text="⚡ CHARLA: OFF",
            fg_color="#0e1526",
            border_color=BORDER_BLUE,
            text_color=TEXT_MUTED
        )
        if user_message:
            self._add_message_card("system", "Modo Charla Continua Desactivado (Ciclo Wake Word VEX activo).")
        if self.voice_mgr.state in (AssistantState.LISTENING, AssistantState.FOLLOW_UP):
            self.voice_mgr.emergency_stop()

    def _on_escape_pressed(self):
        """Detiene síntesis, cancela escucha activa y duerme a VEX (Esc)."""
        if self.hands_free_mode:
            self._disable_hands_free(user_message=False)
        self.voice_mgr.emergency_stop()
        self._set_hud_state("idle")
        self.visor_canvas.set_expression("sleeping", duration=3.0)

    # ================= SELECTOR DE MODELO Y BYOK =================

    def _on_model_selected(self, model_choice: str):
        success = self.agent.set_model(model_choice)
        if success:
            config.set_preferred_model(model_choice)
            self._add_message_card("system", f"Modelo vinculado: '{model_choice}'")

    def _on_agent_model_change(self, new_model: str):
        self.after(0, lambda: self.menu_model.set(new_model))
        self.after(0, lambda: self._add_message_card("system", f"⚡ Failover: Conmutado a '{new_model}'."))

    def _open_byok_modal(self):
        def on_saved(key, user_name):
            self.agent.reload_api_key()
            self._add_message_card("system", f"Perfil actualizado para {user_name}. Núcleo sincronizado.")
        ApiKeyModal(self, on_save_callback=on_saved)

    def _initial_greeting(self):
        user_name = config.get_user_name()
        try:
            self.voice_mgr.start()
        except Exception as e:
            print(f"[UI] Error iniciando VoiceAssistantManager: {e}")

        if not self.agent.is_configured():
            self._add_message_card(
                "system",
                "⚠️ Núcleo de VEX en espera. Por favor ingresa tu Gemini API Key en '⚙ BYOK' para activar los sistemas."
            )
            self._set_hud_state("idle")
            self.after(300, self._open_byok_modal)
        else:
            greeting = f"VEX en línea. Sistemas tácticos activos y a tu orden, {user_name}. Di 'VEX' u 'Oye VEX' para darme una orden."
            self._add_message_card("agent", greeting)
            self._set_hud_state("idle")
            self.visor_canvas.set_expression("happy", duration=3.5)
            self.tts.speak(greeting)

    # ================= ENTRADA DE COMANDOS Y 2 CAPAS =================

    def _on_send_text(self):
        query = self.entry_prompt.get().strip()
        if not query:
            return
        self.entry_prompt.delete(0, "end")
        self._handle_user_prompt(query)

    def _handle_user_prompt(self, prompt: str):
        """Enrutamiento de 2 Capas: Capa 0 Local Zero-Token y Capa 1 Gemini."""
        user_name = config.get_user_name()

        # Comprobar si el usuario pide a VEX volver a reposo
        lower_prompt = prompt.lower().strip()
        sleep_phrases = [
            "descansa", "ve a dormir", "duérmete", "duermete",
            "modo reposo", "apágate", "apagate", "silencio",
            "adiós vex", "adios vex", "para la charla", "detén la charla"
        ]
        if any(sp in lower_prompt for sp in sleep_phrases):
            self._add_message_card("user", prompt)
            farewell = f"Entendido, {user_name}. VEX entrando en modo reposo. Quedo atento a tu llamado."
            self._add_message_card("agent", farewell)
            self.voice_mgr.emergency_stop()
            self.tts.speak(farewell)
            self.visor_canvas.set_expression("sleeping", duration=4.0)
            return

        # CAPA 0: ENRUTAMIENTO DETERMINISTA LOCAL
        local_result = LocalIntentRouter.route(prompt, user_name=user_name)
        if local_result and local_result.handled:
            self._add_message_card("user", prompt)
            self._add_message_card(
                "system",
                f"Acción ejecutada: {local_result.action_name} -> {local_result.execution_result}"
            )
            self._add_message_card("agent", local_result.spoken_response)

            if local_result.icon:
                self.visor_canvas.show_icon(local_result.icon, duration=local_result.icon_duration)
            if local_result.expression and local_result.expression != "idle":
                self.visor_canvas.set_expression(local_result.expression, duration=local_result.icon_duration)

            self.tts.speak(local_result.spoken_response)
            return

        # CAPA 1: INFERENCIA INTELIGENTE GEMINI
        self._add_message_card("user", prompt)
        self.voice_mgr.set_state(AssistantState.THINKING)
        self._set_hud_state("thinking")
        self.visor_canvas.set_expression("thinking")

        def task():
            response = self.agent.send_message(prompt)
            self.after(0, lambda: self._on_agent_response(response))

        threading.Thread(target=task, daemon=True).start()

    def _on_agent_response(self, response_text: str):
        self._add_message_card("agent", response_text)
        self.tts.speak(response_text)

    def _on_tool_executed(self, tool_name: str, args: dict, result: str):
        args_str = ", ".join(f"{k}='{v}'" for k, v in args.items())
        msg = f"Herramienta ejecutada: {tool_name}({args_str}) -> {result}"
        self.after(0, lambda: self._add_message_card("system", msg))

    # ================= ORQUESTACIÓN DEL ASISTENTE Y WAKE WORD =================

    def _on_user_voice_command(self, recognized_text: str):
        """Recepción thread-safe de comandos de voz hacia la interfaz gráfica."""
        print(f"[UI] [VOZ] Procesando orden de voz en hilo principal: '{recognized_text}'")
        self.after(0, lambda: self._handle_user_prompt(recognized_text))

    def _on_wake_flash_triggered(self):
        """Dispara el destello y halo cian neón en el visor al detectar la palabra clave 'VEX'."""
        self.after(0, lambda: self.visor_canvas.trigger_wake_flash(duration=0.65))

    def _on_assistant_state_change(self, new_state: AssistantState):
        """Callback thread-safe para reflejar el estado del asistente en la interfaz."""
        self.after(0, lambda: self._apply_assistant_state(new_state))

    def _apply_assistant_state(self, state: AssistantState):
        """Actualiza el visor, botones e indicadores de estado según el ciclo de vida de VEX."""
        if state == AssistantState.STANDBY:
            self._set_hud_state("idle")
            self.visor_canvas.set_expression("sleeping")
            self._mic_breathing = False
            self.btn_mic.configure(
                text="🎙 REPOSO",
                fg_color="#0e1b2e",
                border_color=BORDER_SUBTLE
            )
            self.lbl_app_sub.configure(
                text="MODO REPOSO // ESCUCHANDO: 'VEX'",
                text_color=TEXT_MUTED
            )

        elif state == AssistantState.WAKE:
            self._set_hud_state("idle")
            self.visor_canvas.set_expression("happy", duration=1.2)
            self.btn_mic.configure(
                text="⚡ ¡DESPIERTO!",
                fg_color="#083344",
                border_color=ACCENT_CYAN
            )
            self.lbl_app_sub.configure(
                text="¡VEX ACTIVADO! // PREPARANDO ESCUCHA",
                text_color=ACCENT_CYAN
            )

        elif state == AssistantState.LISTENING:
            self._set_hud_state("listening")
            self.visor_canvas.set_expression("listening")
            self._mic_breathing = True
            self.btn_mic.configure(
                text="🔴 ESCUCHANDO",
                fg_color="#2b1122",
                border_color=ACCENT_RED
            )
            self.lbl_app_sub.configure(
                text="CAPTANDO TU VOZ // HABLA AHORA...",
                text_color=ACCENT_RED
            )

        elif state == AssistantState.THINKING:
            self._set_hud_state("thinking")
            self.visor_canvas.set_expression("thinking")
            self._mic_breathing = False
            self.btn_mic.configure(
                text="⚙ PROCESANDO",
                fg_color="#1e182e",
                border_color="#a855f7"
            )
            self.lbl_app_sub.configure(
                text="PROCESANDO INTENCIÓN // CERO-TOKENS O GEMINI",
                text_color="#c084fc"
            )

        elif state == AssistantState.SPEAKING:
            self._set_hud_state("speaking")
            self.visor_canvas.set_speaking(True)
            self._mic_breathing = False
            self.btn_mic.configure(
                text="🔊 HABLANDO",
                fg_color="#083344",
                border_color=ACCENT_CYAN
            )
            self.lbl_app_sub.configure(
                text="VOCALIZANDO RESPUESTA TÁCTICA",
                text_color=ACCENT_CYAN
            )

        elif state == AssistantState.FOLLOW_UP:
            self._set_hud_state("listening")
            self.visor_canvas.set_expression("listening")
            self.visor_canvas.set_speaking(False)
            self._mic_breathing = True
            self.btn_mic.configure(
                text="👂 SEGUIMIENTO",
                fg_color="#083344",
                border_color=ACCENT_CYAN
            )
            self.lbl_app_sub.configure(
                text="VENTANA DE SEGUIMIENTO (4s) // CHARLA FLUIDA",
                text_color=ACCENT_CYAN
            )

    # ================= CONTROL DE VOZ =================

    def _toggle_voice_input(self):
        """Activa manualmente la escucha o interrumpe la sesión."""
        if self.voice_mgr.state in (AssistantState.LISTENING, AssistantState.FOLLOW_UP):
            self.voice_mgr.emergency_stop()
        else:
            self.voice_mgr.trigger_manual_listen()

    def on_closing(self):
        self.hands_free_mode = False
        try:
            self.voice_mgr.shutdown()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)
