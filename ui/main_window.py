"""
LYAXIS labs™ - Ventana Principal de VEX HUD (ui/main_window.py)
Interfaz gráfica táctica profesional Cyber-Premium para VEX inspirada en JARVIS y Cozmo:
- Zona A: Riel lateral minimalista (62px fija) con accesos directos, atajos y rueda de ajustes (⚙).
- Zona B: Barra lateral de conversaciones 'Mis Chats' (240px colapsable con búsqueda y gestión).
- Zona C: Área central de conversación:
  * Cabecera Hero con el Gran Visor Panorámico de VEX (380x160px) centrado sobre fondo OLED.
  * Flujo de chat con scroll suave acelerado, tarjetas reactivas y retícula cibernética.
  * Cápsula flotante inferior de entrada por voz y teclado siempre disponible.
- Comportamiento de Spotify y herramientas: La ventana principal NUNCA se oculta automáticamente.
"""
import os
import sys
import time
import datetime
import threading
import webbrowser
from typing import Optional, List, Dict, Any
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

import config
from ui.styles import (
    BG_ROOT, BG_RAIL, BG_CHATS_PANEL, BG_HEADER, BG_CHAT_AREA, BG_INPUT_CAPSULE,
    BORDER_SUBTLE, BORDER_CARD, BORDER_BLUE, BORDER_CYAN, BORDER_GREEN,
    ACCENT_CYAN, ACCENT_CYAN_GLOW, ACCENT_BLUE, ACCENT_BLUE_HOVER, ACCENT_GREEN,
    ACCENT_RED, ACCENT_AMBER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_CYAN, TEXT_WHITE,
    get_font_title, get_font_subtitle, get_font_badge, get_font_body, get_font_code,
    get_font_header_title, get_font_header_sub
)
from ui.chat_bubbles import (
    UserMessageCard,
    VexResponseCard,
    ToolActionCard,
    MediaPlayerCard,
    TaskInteractiveCard
)
from ui.robot_visor import RobotVisorCanvas
from ui.floating_widget import FloatingWidget
from ui.settings_modal import SettingsModal
from ui.byok_modal import ApiKeyModal
from ui.profile_modal import UserProfileModal
from ui.tasks_panel import TasksPanelModal
from voice.tts import TextToSpeechEngine
from voice.stt import SpeechToTextListener
from voice.manager import VoiceAssistantManager, AssistantState
from agent.factory import create_agent
from agent.router import LocalIntentRouter
from tools.system_tools import open_url, launch_application, control_media
from memory.manager import get_memory_manager
from memory.briefing import play_proactive_briefing


def safe_print(msg: str):
    try:
        print(msg)
    except Exception:
        pass


class _DummyControl:
    """Control señuelo para garantizar 100% retrocompatibilidad con scripts que accedan a widgets antiguos."""
    def __init__(self, default: str = ""):
        self._val = default

    def configure(self, *args, **kwargs):
        pass

    def set(self, val: str):
        self._val = str(val)

    def get(self) -> str:
        return self._val


class MainWindow(ctk.CTk):
    """
    Ventana principal del HUD Táctico de VEX (LYAXIS labs™).
    Arquitectura limpia con el Visor de Robot como Hero principal centrado en la cabecera
    y controles de configuración desacoplados en el modal de ajustes (⚙).
    """

    def __init__(self):
        super().__init__()

        # Apariencia y configuración de ventana principal
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("LYAXIS labs™ // VEX HUD - Tactical AI Desktop")
        self.geometry("1100x840")
        self.minsize(880, 700)
        self.configure(fg_color=BG_ROOT)

        # Control de concurrencia y prevención de bloqueos
        self.is_processing = False

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
        self._attached_image_path: Optional[str] = None

        # Instancia activa del modal de ajustes (singleton)
        self._settings_modal_instance: Optional[SettingsModal] = None

        # Controles retrocompatibles para scripts y plugins
        self.menu_user = _DummyControl("👤 Operador")
        self.btn_provider = _DummyControl("✦ GEMINI")
        self.menu_model = _DummyControl("gemini-2.5-flash")
        self.btn_hands_free = _DummyControl("⚡ CHARLA: OFF")
        self.btn_byok = _DummyControl("⚙ BYOK")

        # Inicialización del orquestador de voz con Wake Word Detection
        self.voice_mgr = VoiceAssistantManager(
            on_state_change=self._on_assistant_state_change,
            on_user_command=self._on_user_voice_command,
            on_wake_flash=self._on_wake_flash_triggered
        )
        self.tts = self.voice_mgr.tts
        self.stt = self.voice_mgr.stt

        self.agent = create_agent(
            on_tool_call=self._on_tool_executed,
            on_model_change=self._on_agent_model_change,
            on_emotion=self._on_agent_emotion,
            on_failover=self._on_agent_failover
        )

        # Construcción visual de las 3 zonas del layout
        self._build_layout()

        # Inicialización del Mini-VEX Companion (Widget flotante Always-on-Top - 100% opcional)
        self.floating_widget = FloatingWidget(
            master=self,
            on_restore=self.restore_from_floating_widget,
            on_toggle_hands_free=self._toggle_hands_free,
            on_quit=self.on_closing
        )
        self.floating_widget.withdraw()

        # Atajos de teclado
        self.bind("<Escape>", lambda event: self._on_escape_pressed())
        self.bind_all("<Control-space>", lambda event: self.bring_to_front_and_focus())

        # Atajo global de sistema Windows (Ctrl + Espacio) en hilo desacoplado
        self._hotkey_thread_running = False
        self._init_global_hotkey()

        # Iniciar ciclo de animación de respiración del micrófono
        self._update_mic_breathing()

        # Saludo táctico inicial y briefing proactivo
        self.after(400, self._initial_greeting)

    # ================= CONSTRUCCIÓN DEL LAYOUT DE 3 ZONAS =================

    def _build_layout(self):
        """Maqueta las 3 zonas: Zona A (Riel 62px), Zona B (Mis Chats 240px), Zona C (Canvas de Chat y Visor Hero)."""

        # ---------------- ZONA A: RIEL DE ICONOS LATERAL (62px) ----------------
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

        # Icono 4: Tareas y Recordatorios (Agenda Táctica)
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
            command=self._open_tasks_panel
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

        # Icono 6: Helado (Fun feature de visor animado)
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

        # Icono 7: Modo Widget Flotante (Mini-VEX) - Activación 100% deliberada y manual
        self.btn_rail_widget = ctk.CTkButton(
            self.frame_rail,
            text="⧉",
            width=44,
            height=44,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color=ACCENT_CYAN,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=16),
            command=self.show_floating_widget
        )
        self.btn_rail_widget.pack(side="top", pady=4)

        # Riel inferior: Ajustes del Sistema (⚙) vinculados al moderno SettingsModal
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
            command=self._open_settings_modal
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

        # Cabecera de la barra de chats
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

        # 1. HEADER SUPERIOR HERO - EL GRAN VISOR PANORÁMICO DE VEX
        # Espacio superior exclusivo para el rostro de VEX: limpio, flotando sobre fondo negro OLED
        self.frame_header = ctk.CTkFrame(
            self.frame_main_area,
            height=224,
            fg_color=BG_HEADER,
            corner_radius=0,
            border_width=1,
            border_color=BORDER_SUBTLE
        )
        self.frame_header.pack(side="top", fill="x", padx=0, pady=0)
        self.frame_header.pack_propagate(False)

        # Visor panorámico centrado flotando sobre fondo negro OLED con bisel de cristal
        # Escala Hero: 520px de ancho x 200px de alto
        self.visor_card = ctk.CTkFrame(
            self.frame_header,
            width=520,
            height=200,
            fg_color="#000000",
            corner_radius=24,
            border_width=2.0,
            border_color="#1d4ed8"
        )
        self.visor_card.place(relx=0.5, rely=0.5, anchor="center")
        self.visor_card.pack_propagate(False)

        # Visor Robótico animado de matriz neón de alta fidelidad (516x196)
        self.visor_canvas = RobotVisorCanvas(self.visor_card, width=516, height=196)
        self.visor_canvas.pack(fill="both", expand=True, padx=2, pady=2)
        self.avatar_canvas = self.visor_canvas  # Alias para compatibilidad

        # 2. ÁREA DE CHAT (CANVAS SCROLLEABLE CON RETÍCULA CIBERNÉTICA)
        # El contenedor de conversación se desplaza cómodamente hacia abajo
        self._chat_bg_frame = ctk.CTkFrame(
            self.frame_main_area,
            fg_color=BG_CHAT_AREA,
            corner_radius=0
        )
        self._chat_bg_frame.pack(fill="both", expand=True, padx=0, pady=(4, 0))

        # Canvas de retícula OLED (cyber grid de puntos y líneas sutiles)
        self._grid_canvas = tk.Canvas(
            self._chat_bg_frame,
            bg=BG_CHAT_AREA,
            highlightthickness=0,
            bd=0
        )
        self._grid_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._grid_canvas.bind("<Configure>", self._redraw_cyber_grid)

        self.chat_container = ctk.CTkScrollableFrame(
            self._chat_bg_frame,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#1e293b",
            scrollbar_button_hover_color=ACCENT_CYAN,
            scrollbar_fg_color="#070a12"
        )
        self.chat_container.pack(fill="both", expand=True, padx=24, pady=(6, 82))
        self.chat_container.bind("<Configure>", self._on_chat_resize)
        self.chat_container.bind("<MouseWheel>", self._on_chat_mouse_wheel, add=True)
        self.chat_container._parent_canvas.bind("<MouseWheel>", self._on_chat_mouse_wheel, add=True)

        # Espaciador inferior dinámico para evitar que la cápsula flotante tape los últimos mensajes
        self._chat_bottom_spacer = ctk.CTkFrame(self.chat_container, height=85, fg_color="transparent")
        self._chat_bottom_spacer.pack(fill="x", pady=0)

        # 3. CÁPSULA FLOTANTE INFERIOR DE ENTRADA
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
        self.entry_prompt.bind("<FocusIn>", lambda e: self.frame_floating_input.configure(border_color=BORDER_CYAN))
        self.entry_prompt.bind("<FocusOut>", lambda e: self.frame_floating_input.configure(border_color=BORDER_CARD))

        # Alias estandarizados para thread-safety y retrocompatibilidad total
        self.input_entry = self.entry_prompt

        # Botón de micrófono (+ VOZ)
        self.btn_mic = ctk.CTkButton(
            self.frame_floating_input,
            text="+ VOZ",
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
        self.btn_voice = self.btn_mic

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
            command=self.send_message
        )
        self.btn_send.pack(side="right", padx=(4, 10), pady=8)

        # Vinculación permanente y segura de la tecla Enter
        self.input_entry.bind("<Return>", self.send_message)

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
                    hover_color="#3b1116",
                    text_color="#64748b",
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    corner_radius=4,
                    command=lambda sid=s_id: self._delete_chat_session(sid)
                )
                btn_del.pack(side="right", padx=4)

    def _create_new_chat(self):
        """Crea y activa una nueva conversación limpia."""
        new_id = f"session_{int(time.time())}"
        new_session = {
            "id": new_id,
            "title": f"Conversación {len(self.chat_sessions) + 1}",
            "date": "Hoy",
            "messages": []
        }
        self.chat_sessions.insert(0, new_session)
        self.active_session_id = new_id

        # Limpiar mensajes visuales actuales
        self._message_cards.clear()
        for child in self.chat_container.winfo_children():
            if child != self._chat_bottom_spacer:
                child.destroy()

        self._render_chats_list()
        self._add_message_card("system", "Nueva sesión táctica iniciada. VEX en espera de órdenes.")
        self.entry_prompt.focus()

    def _switch_chat_session(self, session_id: str):
        """Cambia entre conversaciones guardadas."""
        if session_id == self.active_session_id:
            return
        self.active_session_id = session_id
        self._render_chats_list()

        # Re-renderizar mensajes de la sesión
        self._message_cards.clear()
        for child in self.chat_container.winfo_children():
            if child != self._chat_bottom_spacer:
                child.destroy()

        sess = next((s for s in self.chat_sessions if s["id"] == session_id), None)
        if sess:
            for msg in sess.get("messages", []):
                self._render_card_only(msg.get("role", "system"), msg.get("text", ""), msg.get("timestamp", ""))

        self._scroll_chat_to_bottom()

    def _delete_chat_session(self, session_id: str):
        """Elimina una conversación."""
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
        search = self.entry_search_chats.get()
        self._render_chats_list(filter_text=search)

    def _toggle_chats_sidebar(self):
        """Muestra u oculta la barra lateral 'Mis Chats'."""
        if self.chats_sidebar_visible:
            self.frame_chats.pack_forget()
            self.chats_sidebar_visible = False
        else:
            self.frame_chats.pack(side="left", fill="y", padx=0, pady=0, after=self.frame_rail)
            self.chats_sidebar_visible = True

    # ================= RENDERIZADO DE MENSAJES Y SCROLLING =================

    def _add_message_card(self, role: str, text: str, user_name: str = "Operador"):
        """Agrega una tarjeta de mensaje y la registra en la sesión activa."""
        now_str = datetime.datetime.now().strftime("%H:%M")
        curr_sess = next((s for s in self.chat_sessions if s["id"] == self.active_session_id), None)
        if curr_sess:
            curr_sess["messages"].append({"role": role, "text": text, "timestamp": now_str})
            if len(curr_sess["messages"]) == 2 and role == "user":
                clean_title = text.strip()[:24]
                curr_sess["title"] = clean_title
                self._render_chats_list()

        self._render_card_only(role, text, now_str, user_name)
        self._scroll_chat_to_bottom()

    def _render_card_only(self, role: str, text: str, timestamp: str, user_name: str = "Operador"):
        """Dibuja una tarjeta en el contenedor de chat."""
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
            lower_text = text.lower()
            if "spotify" in lower_text or "youtube" in lower_text or "reproduciendo" in lower_text:
                plat = "Spotify" if "spotify" in lower_text else "YouTube"
                card = MediaPlayerCard(
                    self.chat_container,
                    title=text,
                    platform=plat,
                    timestamp=timestamp
                )
                card.pack(fill="x", padx=16, pady=6)
            elif "tarea guardada" in lower_text or "[✔ tarea" in lower_text:
                card = TaskInteractiveCard(
                    self.chat_container,
                    title=text,
                    timestamp=timestamp
                )
                card.pack(fill="x", padx=16, pady=6)
            else:
                card = ToolActionCard(
                    self.chat_container,
                    action_title="EVENTO DE SISTEMA",
                    detail=text,
                    timestamp=timestamp
                )
                card.pack(fill="x", padx=20, pady=4)

        if card:
            if hasattr(self, "_chat_bottom_spacer"):
                try:
                    self._chat_bottom_spacer.pack_forget()
                    self._chat_bottom_spacer.pack(fill="x", pady=0)
                except Exception:
                    pass

            if hasattr(card, "update_wraplength"):
                self._message_cards.append(card)
                curr_width = self.chat_container.winfo_width()
                wrap = max(320, curr_width - 80) if curr_width > 100 else 650
                card.update_wraplength(wrap)

            self._bind_mousewheel_recursive(card)

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

    def _on_chat_mouse_wheel(self, event):
        """Desplazamiento ágil, veloz y fluido del lienzo de chat."""
        try:
            if sys.platform.startswith("win"):
                delta = -int(event.delta / 2)
                self.chat_container._parent_canvas.yview_scroll(delta, "units")
            elif sys.platform == "darwin":
                self.chat_container._parent_canvas.yview_scroll(-int(event.delta * 4), "units")
            else:
                self.chat_container._parent_canvas.yview_scroll(-4 if event.num == 4 else 4, "units")
            return "break"
        except Exception:
            pass

    def _bind_mousewheel_recursive(self, widget):
        """Propaga el evento de la rueda del ratón hacia el canvas de chat."""
        try:
            widget.bind("<MouseWheel>", self._on_chat_mouse_wheel, add=True)
            widget.bind("<Button-4>", self._on_chat_mouse_wheel, add=True)
            widget.bind("<Button-5>", self._on_chat_mouse_wheel, add=True)
        except Exception:
            pass

        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _redraw_cyber_grid(self, event=None):
        """Dibuja la retícula cibernética sutil (cyber grid) como textura de fondo OLED."""
        try:
            canvas = self._grid_canvas
            canvas.delete("grid")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 10 or h < 10:
                return
            step = 36
            for x in range(0, w, step):
                for y in range(0, h, step):
                    canvas.create_oval(
                        x - 1, y - 1, x + 1, y + 1,
                        fill="#0d1829", outline="",
                        tags="grid"
                    )
            for y in range(0, h, 72):
                canvas.create_line(
                    0, y, w, y,
                    fill="#0a1220", width=1,
                    tags="grid"
                )
        except Exception:
            pass

    def _on_chat_resize(self, event):
        """Ajusta dinámicamente el ancho de envoltura al redimensionar la ventana."""
        new_width = event.width
        if new_width > 100:
            wrap = max(320, new_width - 80)
            for card in self._message_cards:
                try:
                    card.update_wraplength(wrap)
                except Exception:
                    pass

    def _on_re_speak(self, text_to_speak: str):
        """Vocaliza de nuevo un mensaje al pulsar 'Escuchar de nuevo'."""
        self.voice_mgr.speak(text_to_speak, from_voice=False)

    # ================= SINCRONIZACIÓN Y ESTADOS DEL VISOR ROBÓTICO =================

    def _set_hud_state(self, state_name: str):
        """Actualiza el estado del visor robótico en el HUD y en el widget flotante."""
        self.visor_canvas.set_state(state_name)
        if hasattr(self, "floating_widget") and self.floating_widget:
            self.floating_widget.set_state(state_name)

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
        self.btn_hands_free.set("⚡ CHARLA: ON")
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
        self.btn_hands_free.set("⚡ CHARLA: OFF")
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
        self.visor_canvas.set_expression("sleeping", duration=3.0, force=True)

    # ================= CONTROL DE WIDGET FLOTANTE (100% MANUAL Y OPCIONAL) =================

    def show_floating_widget(self):
        """
        Minimiza la ventana principal del HUD y activa el Mini-VEX Companion flotante.
        ESTA ACCIÓN SOLO SE EJECUTA SI EL USUARIO PULSA DELIBERADAMENTE EL BOTÓN O ATAJO.
        """
        if hasattr(self, "floating_widget") and self.floating_widget:
            self.floating_widget.set_state(self.visor_canvas.state)
            self.floating_widget.set_speaking(self.visor_canvas.is_speaking)
            self.floating_widget.set_expression(self.visor_canvas.expression)
            if hasattr(self.visor_canvas, "persistent_mood"):
                self.floating_widget.set_persistent_mood(self.visor_canvas.persistent_mood)
            if self.visor_canvas.active_icon:
                self.floating_widget.show_icon(self.visor_canvas.active_icon)

            self.floating_widget.deiconify()
            self.floating_widget.lift()
            self.withdraw()

    def restore_from_floating_widget(self):
        """
        Restaura instantáneamente la ventana principal completa de VEX y oculta el widget flotante.
        Mantiene el hilo de conversación y enfoca inmediatamente el campo de entrada.
        """
        if hasattr(self, "floating_widget") and self.floating_widget:
            if hasattr(self.floating_widget, "visor") and hasattr(self.floating_widget.visor, "persistent_mood"):
                self.visor_canvas.set_persistent_mood(self.floating_widget.visor.persistent_mood)
            self.floating_widget.withdraw()

        self.deiconify()
        self.lift()
        self.focus_force()

        # Asegurar foco inmediato en el campo de texto para que el usuario pueda escribir
        try:
            self._set_input_enabled(True)
            self.entry_prompt.focus()
        except Exception:
            pass

    # ================= MODAL DE AJUSTES (⚙) Y CONFIGURACIÓN =================

    def _open_settings_modal(self):
        """Abre el panel moderno de configuración centralizada de VEX (SettingsModal)."""
        if self._settings_modal_instance and self._settings_modal_instance.winfo_exists():
            self._settings_modal_instance.lift()
            self._settings_modal_instance.focus_force()
            return
        self._settings_modal_instance = SettingsModal(self)

    def _open_byok_modal(self):
        """Abre directamente el modal de configuración de claves BYOK."""
        def on_saved(provider, model, user_name):
            self.agent.reload_api_key()
            self.agent.set_provider(provider)
            if model:
                self.agent.set_model(model)
            self._update_header_provider_and_models()
            self._refresh_user_profiles_menu()
            self._add_message_card("system", f"Perfil actualizado para {user_name}. Motor activo: {provider.upper()} ({model}).")
        ApiKeyModal(self, on_save_callback=on_saved)

    def _open_tasks_panel(self):
        """Abre el panel visual de Tareas y Recordatorios."""
        TasksPanelModal(self)

    def _toggle_active_provider(self):
        """Alterna el proveedor activo entre Google Gemini y Groq Cloud."""
        curr = self.agent.get_active_provider()
        target = "groq" if curr == "gemini" else "gemini"
        self.agent.set_provider(target)
        self._update_header_provider_and_models()
        self._add_message_card("system", f"Motor cambiado a {target.upper()} ({self.agent.active_model}).")

    def _update_header_provider_and_models(self):
        """Sincroniza el estado del proveedor con el modal de ajustes si está activo."""
        prov = self.agent.get_active_provider()
        self.btn_provider.set("⚡ GROQ" if prov == "groq" else "✦ GEMINI")
        self.menu_model.set(self.agent.active_model)
        if self._settings_modal_instance and self._settings_modal_instance.winfo_exists():
            try:
                self._settings_modal_instance.active_provider = prov
                self._settings_modal_instance._update_provider_buttons()
                self._settings_modal_instance._refresh_model_options()
            except Exception:
                pass

    def _on_model_selected(self, model_choice: str):
        success = self.agent.set_model(model_choice)
        if success:
            config.set_preferred_model(model_choice, self.agent.get_active_provider())
            self._add_message_card("system", f"Modelo vinculado: '{model_choice}' ({self.agent.get_active_provider().upper()})")

    def _on_agent_model_change(self, new_model: str):
        safe_print(f"[VEX UI] Selector de modelo actualizado a: '{new_model}'")
        self.menu_model.set(new_model)
        if self._settings_modal_instance and self._settings_modal_instance.winfo_exists():
            try:
                self._settings_modal_instance.menu_model.set(new_model)
            except Exception:
                pass

    def _on_agent_failover(self, old_prov: str, new_prov: str, reason: str):
        """Notificación ante Failover Inteligente entre proveedores."""
        safe_print(f"[VEX UI] Conmutación transparente de proveedor: {old_prov.upper()} -> {new_prov.upper()} ({reason})")
        self.after(0, self._update_header_provider_and_models)

    def _on_agent_emotion(self, expr_name: str, icon_name: Optional[str], duration: float):
        """Callback thread-safe para reflejar expresiones e iconos en el visor principal y widget flotante."""
        def apply():
            if expr_name:
                dur_arg = duration if duration > 0 else None
                self.visor_canvas.set_expression(expr_name, dur_arg)
                if hasattr(self, "floating_widget") and self.floating_widget:
                    self.floating_widget.set_expression(expr_name, dur_arg)
            if icon_name:
                self.visor_canvas.show_icon(icon_name, duration)
                if hasattr(self, "floating_widget") and self.floating_widget:
                    self.floating_widget.show_icon(icon_name, duration)
        self.after(0, apply)

    def _refresh_user_profiles_menu(self):
        """Actualiza los perfiles si el modal de ajustes está abierto."""
        if self._settings_modal_instance and self._settings_modal_instance.winfo_exists():
            try:
                self._settings_modal_instance.refresh_profiles_list()
            except Exception:
                pass

    def _on_user_profile_selected(self, choice: str):
        """Maneja el cambio de perfil de operador."""
        if choice in ("➕ Nuevo perfil...", "+ Nuevo perfil..."):
            self._open_new_user_modal()
            return

        display_name = choice.replace("👤", "").strip()
        manager = get_memory_manager()
        profiles = manager.list_profiles()
        matched = next((p for p in profiles if p["display_name"].lower() == display_name.lower()), None)
        if matched:
            user_id = matched["user_id"]
            if manager.active_user_id != user_id:
                manager.switch_user(user_id)
                config.set_user_name(matched["display_name"])
                self._add_message_card(
                    "system",
                    f"👤 Perfil activo cambiado a: {matched['display_name']} ({matched.get('voice_speed', '+15%')}). Tareas y rutinas vinculadas."
                )
                self.visor_canvas.set_expression("happy", duration=3.0)

    def _open_new_user_modal(self):
        """Abre el diálogo modal de registro de nuevo operador."""
        def on_created(profile):
            self._refresh_user_profiles_menu()
            name = profile.get("display_name", "Operador")
            self._add_message_card("system", f"✅ Nuevo perfil registrado y activado: {name}.")
            play_proactive_briefing(self, speak_audio=True)

        UserProfileModal(self, on_save_callback=on_created)

    def _initial_greeting(self, speak_audio: bool = True):
        try:
            self.voice_mgr.start()
        except Exception as e:
            print(f"[UI] No se pudo inicializar reconocimiento de voz: {e}")

        # Saludo proactivo multi-usuario y reporte matutino
        try:
            play_proactive_briefing(self, speak_audio=speak_audio)
        except Exception as e:
            print(f"[UI] Error al ejecutar briefing inicial: {e}")

        self.visor_canvas.set_expression("happy", duration=3.0)

    def _focus_chat(self):
        """Enfoca la entrada de texto."""
        self.entry_prompt.focus()

    def bring_to_front_and_focus(self):
        """
        Restaura, enfoca y trae al frente absoluto la ventana principal de VEX
        desde cualquier aplicación o juego mediante Ctrl + Espacio.
        Garantiza que la ventana principal NUNCA se oculte ni se pierda.
        """
        try:
            # Si el floating widget está activo, ocultarlo para mostrar ventana completa
            if hasattr(self, "floating_widget") and self.floating_widget and self.floating_widget.winfo_exists():
                try:
                    self.floating_widget.withdraw()
                except Exception:
                    pass

            self.deiconify()
            self.lift()
            self.attributes("-topmost", True)
            self.after(60, lambda: self.attributes("-topmost", False))
            self.focus_force()

            try:
                import ctypes
                hwnd = self.winfo_id()
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            except Exception:
                pass

            if hasattr(self, "entry_prompt"):
                self.entry_prompt.focus_set()
                self.entry_prompt.focus()

            if hasattr(self, "visor_canvas") and self.visor_canvas:
                self.visor_canvas.trigger_wake_flash(0.4)
                self.visor_canvas.set_ambient_state("listening", duration=4.0)
        except Exception as e:
            print(f"[UI] Error al traer VEX al frente: {e}")

    def _init_global_hotkey(self):
        """Registra el atajo global de sistema 'Ctrl + Espacio' en Windows en un hilo demonio desacoplado."""
        import sys
        if sys.platform != "win32":
            return

        import ctypes
        from ctypes import wintypes
        import time

        MOD_CONTROL = 0x0002
        MOD_NOREPEAT = 0x4000
        VK_SPACE = 0x20
        HOTKEY_ID = 9911

        self._hotkey_thread_running = True

        def hotkey_loop():
            user32 = ctypes.windll.user32
            registered = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL | MOD_NOREPEAT, VK_SPACE)
            if not registered:
                registered = user32.RegisterHotKey(None, HOTKEY_ID, MOD_CONTROL, VK_SPACE)

            if registered:
                print("[Hotkey] ✔ Atajo global 'Ctrl + Espacio' registrado con éxito en Windows.")
            else:
                print("[Hotkey] ⚠ No se pudo registrar el atajo global 'Ctrl + Espacio' (puede estar en uso por otra app).")
                return

            try:
                msg = wintypes.MSG()
                PM_REMOVE = 0x0001
                WM_HOTKEY = 0x0312
                while self._hotkey_thread_running:
                    if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                        if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                            self.after(0, self.bring_to_front_and_focus)
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                    time.sleep(0.04)
            finally:
                try:
                    user32.UnregisterHotKey(None, HOTKEY_ID)
                except Exception:
                    pass

        threading.Thread(target=hotkey_loop, daemon=True, name="VEX-GlobalHotkey").start()

    def apply_theme(self, theme_id: str):
        """Aplica la paleta de colores del tema seleccionado al visor y elementos de UI."""
        from ui.styles import set_active_theme
        theme = set_active_theme(theme_id)
        if hasattr(self, "visor_canvas") and self.visor_canvas:
            self.visor_canvas.c_cyan_bright = theme["ACCENT_CYAN"]
            self.visor_canvas.c_cyan_glow = theme["ACCENT_CYAN_GLOW"]
            self.visor_canvas.c_cyan_dim = theme["ACCENT_CYAN_DIM"]
            self.visor_canvas.c_cyan_core = theme["ACCENT_CYAN"]
            self.visor_canvas.set_ambient_state("idle")
        print(f"[Theme] ✔ Aplicado tema en caliente: {theme['name']}")

    def _on_attach_file(self):
        """Abre diálogo para adjuntar archivos o imágenes."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo para VEX",
            filetypes=[
                ("Todos los archivos", "*.*"),
                ("Imágenes", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"),
                ("Documentos", "*.txt;*.py;*.pdf;*.docx")
            ]
        )
        if file_path:
            filename = os.path.basename(file_path)
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
                self._attached_image_path = file_path
                try:
                    self.btn_attach.configure(text_color=ACCENT_CYAN)
                except Exception:
                    pass
            self._add_message_card("system", f"Archivo adjuntado para análisis: {filename}")
            self.entry_prompt.insert("insert", f"[Adjunto: {filename}] ")
            self.entry_prompt.focus()

    # ================= MENSAJERÍA, CONCURRENCIA Y THREAD-SAFETY =================

    def _unlock_input(self):
        """Liberación garantizada e inmediata del input en el hilo principal sin esperar al audio."""
        self.is_processing = False
        try:
            self.input_entry.configure(state="normal")
            self.btn_send.configure(state="normal")
            if hasattr(self, 'btn_voice'):
                self.btn_voice.configure(state="normal")
            if hasattr(self, 'btn_mic'):
                self.btn_mic.configure(state="normal")
            self.input_entry.focus()

            # Restaurar estado del visor/HUD si estaba pensando
            self._set_hud_state("idle")
            if hasattr(self, "voice_mgr") and self.voice_mgr.state == AssistantState.THINKING:
                self.voice_mgr.set_state(AssistantState.STANDBY)
            if hasattr(self, "visor_canvas") and self.visor_canvas:
                if not getattr(self.visor_canvas, "persistent_mood", None):
                    self.visor_canvas.set_expression("idle")
                self.visor_canvas.set_ambient_state("idle")
            if hasattr(self, "floating_widget") and self.floating_widget:
                if not getattr(getattr(self.floating_widget, "visor", None), "persistent_mood", None):
                    self.floating_widget.set_expression("idle")
        except Exception as e:
            safe_print(f"[UI] Error en _unlock_input: {e}")

    def reset_input_state(self):
        """Garantiza la reactivación del campo de texto en el hilo principal."""
        self._unlock_input()

    def add_user_message(self, text: str):
        """Añade tarjeta de mensaje del usuario al chat."""
        active_u = get_memory_manager().active_user
        user_name = active_u.get("display_name", "Operador") if active_u else "Operador"
        self._add_message_card("user", text, user_name=user_name)

    def add_assistant_message(self, text: str):
        """Añade tarjeta de respuesta de VEX al chat."""
        self._add_message_card("agent", text)

    def add_system_message(self, text: str):
        """Añade tarjeta de aviso táctico del sistema al chat."""
        self._add_message_card("system", text)

    def send_message(self, event=None):
        """Flujo de envío desacoplado y blindado contra congelamiento."""
        texto = self.input_entry.get().strip()
        if not texto:
            return "break"

        # Si por algún motivo quedó en True de una petición anterior, forzar reseteo si no hay hilo activo
        self.is_processing = False

        img_path = self._attached_image_path
        self._attached_image_path = None
        if hasattr(self, "btn_attach"):
            try:
                self.btn_attach.configure(text_color="#94a3b8")
            except Exception:
                pass

        # Limpiar caja de texto inmediatamente para dar feedback al usuario
        self.input_entry.delete(0, "end")
        self.add_user_message(texto)

        # Ejecutar procesamiento en segundo plano
        threading.Thread(target=self._async_dispatch, args=(texto, img_path), daemon=True).start()
        return "break"

    def _async_dispatch(self, texto: str, image_path: Optional[str] = None):
        """Worker desacoplado para inferencia y enrutamiento con garantía de reactivación."""
        try:
            # 1. Comprobar si es un comando determinista de hardware local (Capa 0) si no hay imagen
            local_result = None
            if not image_path:
                try:
                    local_result = LocalIntentRouter.route(texto)
                except Exception as route_err:
                    safe_print(f"[UI Router] Error en evaluación local: {route_err}")

            if local_result and local_result.handled:
                # Despachar cambios visuales y tarjetas en hilo principal
                self.after(0, lambda: self._apply_local_intent_ui(local_result, texto))
                # Reproducir voz en segundo plano SIN bloquear la interfaz
                if local_result.spoken_response:
                    self.tts.speak_async(local_result.spoken_response)
                return

            # 2. Todo lo demás (chistes, historias, 'hola', charlas, preguntas) pasa directamente a la IA
            self.after(0, self._set_hud_thinking)
            respuesta = self.agent.process(texto, image_path=image_path)
            self.after(0, self.add_assistant_message, respuesta)
            # Reproducir voz en segundo plano SIN bloquear la interfaz
            self.tts.speak_async(respuesta)
        except Exception as e:
            self.after(0, self.add_assistant_message, f"Error: {e}")
        finally:
            # Liberación garantizada siempre en el hilo principal
            self.after(0, self._unlock_input)

    def _worker_process_message(self, texto: str, from_voice: bool = False, image_path: Optional[str] = None):
        """Alias para compatibilidad con llamadas existentes."""
        self._async_dispatch(texto, image_path=image_path)

    def _on_send_text(self, event=None):
        """Alias para retrocompatibilidad total con invocadores de _on_send_text."""
        return self.send_message(event)

    def _toggle_voice_input(self):
        """Alterna la escucha manual del micrófono."""
        if self.voice_mgr.state == AssistantState.LISTENING:
            self.voice_mgr.emergency_stop()
            self._mic_breathing = False
            self.btn_mic.configure(fg_color="#0e1b2e", border_color=BORDER_CYAN, text="+ VOZ")
        else:
            self._mic_breathing = True
            self.voice_mgr.trigger_manual_listen()

    def _set_hud_thinking(self):
        """Activa el estado 'pensando' en la interfaz de forma segura en el hilo principal."""
        try:
            self.voice_mgr.set_state(AssistantState.THINKING)
            self._set_hud_state("thinking")
            if hasattr(self, "visor_canvas") and self.visor_canvas:
                self.visor_canvas.set_ambient_state("thinking")
                self.visor_canvas.set_expression("thinking")
            if hasattr(self, "floating_widget") and self.floating_widget:
                self.floating_widget.set_expression("thinking")
        except Exception:
            pass

    def _apply_local_intent_ui(self, local_result, prompt: str):
        """Aplica la UI del router determinista de forma segura en el hilo principal."""
        try:
            act = getattr(local_result, "action_name", "")
            low_p = prompt.lower()
            if act in ["spotify", "youtube", "music"] or "spotify" in low_p or "youtube" in low_p or "reproduce" in low_p:
                self.visor_canvas.set_ambient_state("music", duration=25.0)
            elif "task" in act or "tarea" in act or act in ["add_task", "create_task", "write_note"]:
                self.visor_canvas.set_ambient_state("success", duration=6.0)
            else:
                self.visor_canvas.set_ambient_state("success", duration=4.0)

            # Despacho universal de expresiones y accesorios (Persistent Mood Machine)
            _act = local_result.action_name
            _expr = local_result.expression or ""

            _persistent_moods = {
                "visor:sad": "sad",
                "visor:angry": "angry",
                "visor:curious": "curious",
                "visor:cool_shades": "cool",
            }

            if _act in _persistent_moods:
                mood_arg = _persistent_moods[_act]
                self.visor_canvas.set_persistent_mood(mood_arg)
                if hasattr(self, "floating_widget") and self.floating_widget:
                    try:
                        self.floating_widget.set_persistent_mood(mood_arg)
                    except Exception:
                        pass
            elif _act in ("clear_persistent_mood", "visor:happy") or _expr == "happy":
                self.visor_canvas.set_persistent_mood(None)
                self.visor_canvas.set_expression("happy", duration=6.0, force=True)
                if hasattr(self, "floating_widget") and self.floating_widget:
                    try:
                        self.floating_widget.set_persistent_mood(None)
                        self.floating_widget.set_expression("happy", duration=6.0, force=True)
                    except Exception:
                        pass
            elif local_result.icon == "ice_cream" or _act == "visor:show_ice_cream":
                self.visor_canvas.play_temporary_emote("ice_cream")
                if hasattr(self, "floating_widget") and self.floating_widget:
                    try:
                        self.floating_widget.show_icon("ice_cream", duration=7.0)
                    except Exception:
                        pass
            else:
                if local_result.icon:
                    self.visor_canvas.show_icon(local_result.icon, duration=local_result.icon_duration)
                    if hasattr(self, "floating_widget") and self.floating_widget:
                        try:
                            self.floating_widget.show_icon(local_result.icon, duration=local_result.icon_duration)
                        except Exception:
                            pass
                if _expr and _expr != "idle":
                    self.visor_canvas.set_expression(_expr, duration=local_result.icon_duration)
                    if hasattr(self, "floating_widget") and self.floating_widget:
                        try:
                            self.floating_widget.set_expression(_expr, duration=local_result.icon_duration)
                        except Exception:
                            pass

            if local_result.execution_result:
                self.add_system_message(local_result.execution_result)
            if local_result.spoken_response:
                self.add_assistant_message(local_result.spoken_response)
        except Exception as e:
            safe_print(f"[UI] Error al aplicar UI local: {e}")

    def _handle_user_prompt(self, prompt: str, from_voice: bool = False, image_path: Optional[str] = None):
        """Procesa una orden proveniente de voz o botones de acceso rápido de forma thread-safe."""
        texto = prompt.strip()
        if not texto:
            return

        self.is_processing = False
        self.add_user_message(texto)
        try:
            self.input_entry.delete(0, "end")
        except Exception:
            pass

        threading.Thread(
            target=self._async_dispatch,
            args=(texto, image_path),
            daemon=True
        ).start()

    def _set_input_enabled(self, enabled: bool):
        """Compatibilidad: habilita o deshabilita la entrada del usuario de forma segura."""
        if enabled:
            self.reset_input_state()
        else:
            try:
                self.is_processing = True
                self.btn_send.configure(state="disabled")
            except Exception:
                pass

    def _ensure_input_unlocked(self):
        """Watchdog que garantiza que la barra inferior nunca se quede congelada en 'Procesando...'."""
        self.reset_input_state()

    def _on_agent_response(self, response_text: str, from_voice: bool = False):
        """Compatibilidad con callbacks legados del agente."""
        try:
            self.add_assistant_message(response_text)
        except Exception as e:
            print(f"[UI] Error al agregar tarjeta de agente: {e}")
        finally:
            self.reset_input_state()
        try:
            self.tts.speak_async(response_text)
        except Exception as e:
            print(f"[UI] Error al reproducir voz: {e}")

    def _on_tool_executed(self, tool_name: str, args: dict, result: str):
        """Registra la ejecución de herramientas deterministas en el chat sin minimizar la ventana."""

        # Herramienta especial: cambiar_expresion -> actualiza el visor directamente
        if tool_name == "cambiar_expresion":
            emocion = args.get("emocion", "idle").lower().strip()
            persistente = bool(args.get("persistente", False))
            def _apply_expr():
                try:
                    if persistente:
                        self.visor_canvas.set_persistent_mood(emocion)
                    else:
                        self.visor_canvas.set_expression(emocion, duration=4.0)
                except Exception:
                    pass
            self.after(0, _apply_expr)
            return

        low_t = tool_name.lower()
        low_r = str(result).lower()
        if "spotify" in low_t or "youtube" in low_t or "media" in low_t or "spotify" in low_r or "youtube" in low_r:
            self.visor_canvas.set_ambient_state("music", duration=25.0)
        elif "tarea" in low_t or "task" in low_t or "note" in low_t or "tarea guardada" in low_r:
            self.visor_canvas.set_ambient_state("success", duration=6.0)
        else:
            self.visor_canvas.set_ambient_state("success", duration=4.0)

        if str(result).startswith("[✔"):
            msg = str(result)
        else:
            args_str = ", ".join(f"{k}='{v}'" for k, v in args.items())
            msg = f"Herramienta ejecutada: {tool_name}({args_str}) -> {result}"
        self.after(0, lambda: self._add_message_card("system", msg))
        # EL WIDGET NUNCA SE ACTIVA AUTOMÁTICAMENTE: LA VENTANA PRINCIPAL QUEDA ABIERTA

    # ================= ORQUESTACIÓN DEL ASISTENTE Y WAKE WORD =================

    def _on_user_voice_command(self, recognized_text: str):
        """Recepción thread-safe de comandos de voz hacia la interfaz gráfica."""
        print(f"[UI] [VOZ] Procesando orden de voz en hilo principal: '{recognized_text}'")
        self.after(0, lambda: self._handle_user_prompt(recognized_text, from_voice=True))

    def _on_wake_flash_triggered(self):
        """Dispara el destello y halo cian neón en el visor al detectar la palabra clave 'VEX'."""
        self.after(0, lambda: self.visor_canvas.trigger_wake_flash(duration=0.65))
        if hasattr(self, "floating_widget") and self.floating_widget:
            self.after(0, lambda: self.floating_widget.trigger_wake_flash(duration=0.65))

    def _on_assistant_state_change(self, new_state: AssistantState):
        """Actualiza estados de la interfaz en respuesta a cambios de estado del motor de voz."""
        def apply():
            if new_state == AssistantState.STANDBY:
                self._mic_breathing = False
                self.btn_mic.configure(fg_color="#0e1b2e", border_color=BORDER_CYAN, text="+ VOZ")
                self._set_hud_state("idle")
                self.visor_canvas.set_ambient_state("idle")
            elif new_state in (AssistantState.LISTENING, AssistantState.FOLLOW_UP):
                self._mic_breathing = True
                self._set_hud_state("listening")
                self.visor_canvas.set_ambient_state("listening")
                self.visor_canvas.set_expression("listening")
                if hasattr(self, "floating_widget") and self.floating_widget:
                    self.floating_widget.set_expression("listening")
            elif new_state == AssistantState.THINKING:
                self._mic_breathing = False
                self.btn_mic.configure(fg_color="#1e1808", border_color="#f59e0b", text="🟡 PENSANDO")
                self._set_hud_state("thinking")
                self.visor_canvas.set_ambient_state("thinking")
                self.visor_canvas.set_expression("thinking")
                if hasattr(self, "floating_widget") and self.floating_widget:
                    self.floating_widget.set_expression("thinking")
            elif new_state == AssistantState.SPEAKING:
                self._mic_breathing = False
                self.btn_mic.configure(fg_color="#064e3b", border_color=ACCENT_GREEN, text="🟢 HABLANDO")
                self._set_hud_state("speaking")
                self.visor_canvas.set_speaking(True)
                if hasattr(self, "floating_widget") and self.floating_widget:
                    self.floating_widget.set_speaking(True)
        self.after(0, apply)

    def on_closing(self):
        """Cierre ordenado y seguro de hilos, procesos y sockets."""
        self._hotkey_thread_running = False
        try:
            self.voice_mgr.stop()
        except Exception:
            pass
        try:
            if hasattr(self, "floating_widget") and self.floating_widget:
                self.floating_widget.destroy()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)


# Exportaciones públicas del módulo
__all__ = [
    "MainWindow",
    "SettingsModal",
    "ApiKeyModal",
    "UserProfileModal",
    "TasksPanelModal",
    "RobotVisorCanvas",
    "FloatingWidget",
    "UserMessageCard",
    "VexResponseCard",
    "ToolActionCard",
    "MediaPlayerCard",
    "TaskInteractiveCard"
]
