"""
LYAXIS labs™ - Componentes Visuales de Burbujas de Chat y Tarjetas Tácticas (VEX HUD)
Implementa:
- Burbujas de usuario (alineadas a la derecha, padding amplio, badge de operador).
- Respuestas de VEX (alineadas a la izquierda, glassmorphic, bloques de código estilizados con botón de copia, acciones de re-escucha y copia de texto).
- Tarjetas compactas de eventos y herramientas del sistema (YouTube, Spotify, etc.).
"""
import re
import datetime
import tkinter as tk
from typing import Callable, Optional, List
import customtkinter as ctk

from ui.styles import (
    BG_USER_CARD, BG_VEX_CARD, BG_TOOL_CARD, BG_CODE_BLOCK,
    BORDER_CARD, BORDER_BLUE, BORDER_CYAN, BORDER_GREEN, BORDER_SUBTLE,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED, TEXT_CYAN, TEXT_WHITE,
    ACCENT_BLUE, ACCENT_CYAN, ACCENT_GREEN,
    get_font_body, get_font_code, get_font_badge
)


class CodeBlockFrame(ctk.CTkFrame):
    """Bloque de código estilizado con cabecera de lenguaje y botón de copia rápida."""
    def __init__(self, master, code_text: str, language: str = "code", **kwargs):
        super().__init__(
            master,
            fg_color=BG_CODE_BLOCK,
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=8,
            **kwargs
        )
        self.code_text = code_text.strip()
        self.language = language or "code"

        # Cabecera del bloque de código
        header = ctk.CTkFrame(self, fg_color="#080c16", height=28, corner_radius=0)
        header.pack(fill="x", side="top", padx=0, pady=0)

        lbl_lang = ctk.CTkLabel(
            header,
            text=f"  {self.language.upper()}",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color="#64748b"
        )
        lbl_lang.pack(side="left", padx=8, pady=4)

        # Botón de copiar código
        self.btn_copy = ctk.CTkButton(
            header,
            text="<> Copiar",
            width=68,
            height=20,
            fg_color="transparent",
            hover_color="#141c2e",
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            command=self._copy_code
        )
        self.btn_copy.pack(side="right", padx=8, pady=4)

        # Contenido de código con Text box monoespaciado
        lines = self.code_text.split("\n")
        height_lines = min(max(len(lines), 2), 16)

        self.txt_code = ctk.CTkTextbox(
            self,
            fg_color="transparent",
            text_color="#e2e8f0",
            font=get_font_code(),
            height=height_lines * 19,
            activate_scrollbars=True if len(lines) > 16 else False
        )
        self.txt_code.pack(fill="both", expand=True, padx=8, pady=6)
        self.txt_code.insert("0.0", self.code_text)
        self.txt_code.configure(state="disabled")

    def _copy_code(self):
        """Copia el código al portapapeles y ofrece retroalimentación visual."""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.code_text)
            self.btn_copy.configure(text="✔ Copiado!", text_color="#10b981")
            self.after(2000, lambda: self.btn_copy.configure(text="<> Copiar", text_color=ACCENT_CYAN))
        except Exception:
            pass


class UserMessageCard(ctk.CTkFrame):
    """Burbuja de mensaje del usuario moderna, con esquinas redondeadas y badge de operador."""
    def __init__(self, master, text: str, user_name: str = "Oscar", timestamp: Optional[str] = None, **kwargs):
        super().__init__(
            master,
            fg_color=BG_USER_CARD,
            border_color=BORDER_BLUE,
            border_width=1,
            corner_radius=12,
            **kwargs
        )
        time_str = timestamp or datetime.datetime.now().strftime("%H:%M:%S")

        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))

        lbl_badge = ctk.CTkLabel(
            hdr,
            text=f"● [OPERADOR // {user_name.upper()}]",
            font=get_font_badge(),
            text_color="#38bdf8"
        )
        lbl_badge.pack(side="left")

        lbl_time = ctk.CTkLabel(
            hdr,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")

        # Texto del mensaje con salto de línea automático y margen
        self.lbl_text = ctk.CTkLabel(
            self,
            text=text,
            font=get_font_body(),
            text_color=TEXT_PRIMARY,
            justify="left",
            anchor="w",
            wraplength=650
        )
        self.lbl_text.pack(fill="x", padx=16, pady=(6, 10))

        self._last_width = None
        self.bind("<Configure>", self._on_card_resize)

    def _on_card_resize(self, event):
        """Ajuste dinámico al redimensionar la tarjeta del mensaje."""
        if event.widget != self:
            return
        if event.width <= 100:
            return
        if getattr(self, "_last_width", None) == event.width:
            return
        self._last_width = event.width
        ancho_ajustado = max(320, event.width - 50)
        try:
            self.lbl_text.configure(wraplength=ancho_ajustado)
        except Exception:
            pass

    def update_wraplength(self, wrap_width: int):
        """Actualiza el ancho de envoltura del texto responsivamente."""
        try:
            ancho_ajustado = max(320, wrap_width - 50)
            self.lbl_text.configure(wraplength=ancho_ajustado)
        except Exception:
            pass


class VexResponseCard(ctk.CTkFrame):
    """
    Burbuja de respuesta de VEX con superficie glassmorphic,
    avatar con aro cian, parser de bloques de código y botones de acción.
    """
    def __init__(
        self,
        master,
        raw_text: str,
        on_speak_again: Optional[Callable[[str], None]] = None,
        timestamp: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=BG_VEX_CARD,
            border_color=BORDER_CARD,
            border_width=1,
            corner_radius=12,
            **kwargs
        )
        self.raw_text = raw_text
        self.on_speak_again = on_speak_again
        time_str = timestamp or datetime.datetime.now().strftime("%H:%M:%S")

        # Cabecera con avatar y distintivo de IA
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))

        lbl_avatar = ctk.CTkLabel(
            hdr,
            text="● [VEX // TACTICAL IA]",
            font=get_font_badge(),
            text_color=ACCENT_CYAN
        )
        lbl_avatar.pack(side="left")

        lbl_time = ctk.CTkLabel(
            hdr,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")

        # Contenedor dinámico de texto y código
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="x", padx=0, pady=(2, 6))

        self.text_labels: List[ctk.CTkLabel] = []
        self._last_width = None
        self._parse_and_render_content(raw_text)

        # Vincular evento <Configure> para auto-wrap dinámico y responsivo
        self.bind("<Configure>", self._on_card_resize)

        # Barra de acciones al pie de la burbuja (Re-escuchar, Copiar)
        actions_bar = ctk.CTkFrame(self, fg_color="transparent", height=24)
        actions_bar.pack(fill="x", padx=14, pady=(4, 10))

        # Botón Escuchar de nuevo
        if self.on_speak_again:
            self.btn_speak = ctk.CTkButton(
                actions_bar,
                text="🔊 Escuchar de nuevo",
                width=110,
                height=22,
                fg_color="#0f1624",
                hover_color="#18233b",
                border_color=BORDER_SUBTLE,
                border_width=1,
                text_color="#94a3b8",
                font=ctk.CTkFont(family="Consolas", size=9),
                command=lambda: self.on_speak_again(self.raw_text)
            )
            self.btn_speak.pack(side="left", padx=(0, 6))

        # Botón Copiar texto
        self.btn_copy_all = ctk.CTkButton(
            actions_bar,
            text="📋 Copiar texto",
            width=90,
            height=22,
            fg_color="#0f1624",
            hover_color="#18233b",
            border_color=BORDER_SUBTLE,
            border_width=1,
            text_color="#94a3b8",
            font=ctk.CTkFont(family="Consolas", size=9),
            command=self._copy_full_text
        )
        self.btn_copy_all.pack(side="left")

    def _copy_full_text(self):
        """Copia la respuesta de texto completa al portapapeles."""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.raw_text)
            self.btn_copy_all.configure(text="✔ Copiado!", text_color="#10b981")
            self.after(2000, lambda: self.btn_copy_all.configure(text="📋 Copiar texto", text_color="#94a3b8"))
        except Exception:
            pass

    def _parse_and_render_content(self, text: str):
        """Parsea bloques de código entre ``` y texto estándar intercalado."""
        parts = re.split(r"```([a-zA-Z0-9_\-\+]*)\n(.*?)```", text, flags=re.DOTALL)

        if len(parts) == 1:
            # Texto plano sin código
            lbl = ctk.CTkLabel(
                self.content_frame,
                text=text.strip(),
                font=get_font_body(),
                text_color=TEXT_PRIMARY,
                justify="left",
                anchor="w",
                wraplength=650
            )
            lbl.pack(fill="x", padx=16, pady=(6, 10))
            self.text_labels.append(lbl)
            return

        i = 0
        while i < len(parts):
            chunk = parts[i].strip()
            if chunk:
                # Texto estándar
                lbl = ctk.CTkLabel(
                    self.content_frame,
                    text=chunk,
                    font=get_font_body(),
                    text_color=TEXT_PRIMARY,
                    justify="left",
                    anchor="w",
                    wraplength=650
                )
                lbl.pack(fill="x", padx=16, pady=(6, 10))
                self.text_labels.append(lbl)

            if i + 2 < len(parts):
                lang = parts[i + 1].strip() or "code"
                code_body = parts[i + 2]
                code_frame = CodeBlockFrame(self.content_frame, code_text=code_body, language=lang)
                code_frame.pack(fill="x", padx=14, pady=6)
                i += 3
            else:
                break

    def _on_card_resize(self, event):
        """Ajuste dinámico al redimensionar la tarjeta del mensaje."""
        if event.widget != self:
            return
        if event.width <= 100:
            return
        if getattr(self, "_last_width", None) == event.width:
            return
        self._last_width = event.width
        # Mantener un margen interior de 50px para padding
        ancho_ajustado = max(320, event.width - 50)
        for lbl in self.text_labels:
            try:
                lbl.configure(wraplength=ancho_ajustado)
            except Exception:
                pass

    def update_wraplength(self, wrap_width: int):
        """Ajusta el ancho de envoltura de los textos dentro de la burbuja."""
        ancho_ajustado = max(320, wrap_width - 50)
        for lbl in self.text_labels:
            try:
                lbl.configure(wraplength=ancho_ajustado)
            except Exception:
                pass


class ToolActionCard(ctk.CTkFrame):
    """Tarjeta compacta de evento de herramienta ejecutada (YouTube, Spotify, Volumen, etc.)."""
    def __init__(self, master, action_title: str, detail: str, timestamp: Optional[str] = None, **kwargs):
        super().__init__(
            master,
            fg_color=BG_TOOL_CARD,
            border_color=BORDER_GREEN,
            border_width=1,
            corner_radius=10,
            **kwargs
        )
        time_str = timestamp or datetime.datetime.now().strftime("%H:%M:%S")

        # Parseo inteligente de formato [✔ Plataforma: Detalle]
        display_title = action_title
        display_detail = detail.strip() if detail else ""
        if display_detail.startswith("[✔") and "]" in display_detail:
            inner_content = display_detail.strip("[]").replace("✔", "").strip()
            if ":" in inner_content:
                parts = inner_content.split(":", 1)
                display_title = parts[0].strip()
                display_detail = parts[1].strip()
            else:
                display_title = "SISTEMA"
                display_detail = inner_content

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        lbl_icon = ctk.CTkLabel(
            inner,
            text="⚡",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#10b981"
        )
        lbl_icon.pack(side="left", padx=(0, 6))

        lbl_title = ctk.CTkLabel(
            inner,
            text=f"✔ {display_title}:",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#10b981"
        )
        lbl_title.pack(side="left")

        self.lbl_detail = ctk.CTkLabel(
            inner,
            text=f"{display_detail}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#a7f3d0",
            justify="left",
            anchor="w",
            wraplength=600
        )
        self.lbl_detail.pack(side="left", fill="x", expand=True, padx=(4, 8))

        lbl_time = ctk.CTkLabel(
            inner,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")

        self._last_width = None
        self.bind("<Configure>", self._on_card_resize)

    def _on_card_resize(self, event):
        """Ajuste dinámico al redimensionar la tarjeta de herramienta."""
        if event.widget != self:
            return
        if event.width <= 100:
            return
        if getattr(self, "_last_width", None) == event.width:
            return
        self._last_width = event.width
        ancho_ajustado = max(240, event.width - 120)
        try:
            self.lbl_detail.configure(wraplength=ancho_ajustado)
        except Exception:
            pass

    def update_wraplength(self, wrap_width: int):
        """Actualiza el ancho de envoltura del detalle responsivamente."""
        try:
            ancho_ajustado = max(240, wrap_width - 120)
            self.lbl_detail.configure(wraplength=ancho_ajustado)
        except Exception:
            pass


class MediaPlayerCard(ctk.CTkFrame):
    """
    Tarjeta de Reproductor Multimedia estilo Glassmorphism táctico.
    Generada al reproducir música (Spotify, YouTube, pistas locales).
    Incluye:
    - Plataforma (Spotify / YouTube / Audio) con badge luminoso
    - Título o consulta de la canción
    - Controles táctiles inmediatos:
        [⏮ Anterior]  [⏯ Play / Pausa]  [⏭ Siguiente]  [🔊 +Vol]
    - Retroalimentación visual interactiva en tiempo real.
    """
    def __init__(
        self,
        master,
        title: str,
        platform: str = "SPOTIFY",
        timestamp: Optional[str] = None,
        on_control: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        is_spotify = "SPOTIFY" in platform.upper()
        accent_col = "#10b981" if is_spotify else "#a855f7"
        super().__init__(
            master,
            fg_color="#0a101f",
            border_color=accent_col,
            border_width=1,
            corner_radius=12,
            **kwargs
        )
        self.title_text = title.strip()
        self.platform = platform.upper().strip()
        self.on_control = on_control
        self.accent_col = accent_col
        time_str = timestamp or datetime.datetime.now().strftime("%H:%M:%S")

        # Parsear si el texto vino en formato [✔ Spotify: Reproduciendo 'cancion']
        self._parse_composite_title()

        # Cabecera con Badge de Plataforma y Reloj
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))

        badge_text = "● [SPOTIFY // MEDIA]" if is_spotify else f"● [{self.platform} // MEDIA]"

        lbl_badge = ctk.CTkLabel(
            hdr,
            text=badge_text,
            font=get_font_badge(),
            text_color=self.accent_col
        )
        lbl_badge.pack(side="left")

        lbl_time = ctk.CTkLabel(
            hdr,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")

        # Contenido: Icono de nota + Título de la pista
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(4, 8))

        lbl_music_icon = ctk.CTkLabel(
            body,
            text="🎵",
            font=ctk.CTkFont(family="Segoe UI", size=20),
            text_color=self.accent_col
        )
        lbl_music_icon.pack(side="left", padx=(0, 10))

        info_box = ctk.CTkFrame(body, fg_color="transparent")
        info_box.pack(side="left", fill="x", expand=True)

        self.lbl_title = ctk.CTkLabel(
            info_box,
            text=self.title_text,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=480
        )
        self.lbl_title.pack(fill="x")

        self.lbl_status = ctk.CTkLabel(
            info_box,
            text="En reproducción • Controles táctiles activos",
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        self.lbl_status.pack(fill="x", pady=(2, 0))

        # Fila de Controles Táctiles [⏮ Anterior] [⏯ Play/Pausa] [⏭ Siguiente] [🔊 +Vol]
        ctrl_frame = ctk.CTkFrame(self, fg_color="#060c18", corner_radius=8, height=36)
        ctrl_frame.pack(fill="x", padx=14, pady=(2, 10))

        btn_prev = ctk.CTkButton(
            ctrl_frame,
            text="⏮ Anterior",
            width=78,
            height=26,
            fg_color="#0e1726",
            hover_color="#1e293b",
            border_color="#334155",
            border_width=1,
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            command=lambda: self._trigger_action("previous")
        )
        btn_prev.pack(side="left", padx=(8, 4), pady=5)

        btn_play = ctk.CTkButton(
            ctrl_frame,
            text="⏯ Play / Pausa",
            width=100,
            height=26,
            fg_color="#064e3b" if is_spotify else "#3b0764",
            hover_color="#047857" if is_spotify else "#581c87",
            border_color=self.accent_col,
            border_width=1,
            text_color="#ffffff",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            command=lambda: self._trigger_action("play_pause")
        )
        btn_play.pack(side="left", padx=4, pady=5)

        btn_next = ctk.CTkButton(
            ctrl_frame,
            text="⏭ Siguiente",
            width=78,
            height=26,
            fg_color="#0e1726",
            hover_color="#1e293b",
            border_color="#334155",
            border_width=1,
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            command=lambda: self._trigger_action("next")
        )
        btn_next.pack(side="left", padx=(4, 8), pady=5)

        btn_vol = ctk.CTkButton(
            ctrl_frame,
            text="🔊 +Vol",
            width=60,
            height=26,
            fg_color="#0e1726",
            hover_color="#1e293b",
            border_color="#334155",
            border_width=1,
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            command=lambda: self._trigger_action("volume_up")
        )
        btn_vol.pack(side="right", padx=(4, 8), pady=5)

        self._last_width = None
        self.bind("<Configure>", self._on_card_resize)

    def _on_card_resize(self, event):
        """Ajuste dinámico al redimensionar la tarjeta multimedia."""
        if event.widget != self:
            return
        if event.width <= 100:
            return
        if getattr(self, "_last_width", None) == event.width:
            return
        self._last_width = event.width
        ancho_ajustado = max(240, event.width - 100)
        try:
            self.lbl_title.configure(wraplength=ancho_ajustado)
        except Exception:
            pass

    def _parse_composite_title(self):
        raw = self.title_text
        if raw.startswith("[✔") and "]" in raw:
            inner = raw.strip("[]").replace("✔", "").strip()
            if ":" in inner:
                parts = inner.split(":", 1)
                self.platform = parts[0].strip().upper()
                self.title_text = parts[1].strip()
            else:
                self.title_text = inner
        if self.title_text.lower().startswith("reproduciendo"):
            self.title_text = self.title_text[len("reproduciendo"):].strip(" '\"")

    def _trigger_action(self, action: str):
        """Ejecuta el comando multimedia sin bloquear y actualiza la etiqueta de feedback."""
        try:
            if self.on_control:
                self.on_control(action)
            else:
                from tools.media_controller import control_media
                control_media(action)

            action_labels = {
                "previous": "Pista anterior",
                "play_pause": "Play / Pausa alternado",
                "next": "Pista siguiente",
                "volume_up": "Volumen incrementado"
            }
            lbl_txt = action_labels.get(action, action)
            self.lbl_status.configure(text=f"⚡ {lbl_txt}", text_color="#38bdf8")
            self.after(2200, lambda: self.lbl_status.configure(
                text="En reproducción • Controles táctiles activos",
                text_color=TEXT_MUTED
            ))
        except Exception as e:
            self.lbl_status.configure(text=f"⚠ Error: {e}", text_color="#f87171")

    def update_wraplength(self, wrap_width: int):
        try:
            self.lbl_title.configure(wraplength=max(240, wrap_width - 100))
        except Exception:
            pass


class TaskInteractiveCard(ctk.CTkFrame):
    """
    Tarjeta interactiva de tareas estilo Cyber-Glassmorphic:
    - Badge de fecha real: [📅 05 Oct 2026]
    - Badge de hora: [⏰ 15:00]
    - Título claro de la tarea
    - Checkbox interactivo: al marcarlo, tacha inmediatamente el título en tiempo real
      y actualiza el estado en la base de datos de memoria persistente de VEX.
    """
    def __init__(
        self,
        master,
        title: str,
        date_str: str = "",
        time_str: str = "",
        task_id: Optional[str] = None,
        is_completed: bool = False,
        on_toggle: Optional[Callable[[bool], None]] = None,
        timestamp: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color="#0b1324" if not is_completed else "#080c14",
            border_color="#0284c7" if not is_completed else "#1e293b",
            border_width=1,
            corner_radius=12,
            **kwargs
        )
        self.original_title = title.strip()
        self.task_id = task_id
        self.date_str = date_str.strip()
        self.time_str = time_str.strip() or "15:00"
        self.is_completed = is_completed
        self.on_toggle = on_toggle
        time_rec = timestamp or datetime.datetime.now().strftime("%H:%M:%S")

        # Parsear si el título vino en formato compuesto tipo [✔ Tarea Guardada: '...' para el ... a las ...]
        self._parse_composite_text_if_needed()

        # Cabecera
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(10, 4))

        lbl_badge = ctk.CTkLabel(
            hdr,
            text="⚡ [RECORDATORIO TÁCTICO // VEX AGENDA]",
            font=get_font_badge(),
            text_color="#38bdf8" if not self.is_completed else "#64748b"
        )
        lbl_badge.pack(side="left")

        lbl_time = ctk.CTkLabel(
            hdr,
            text=time_rec,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")

        # Fila del Checkbox + Título
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x", padx=14, pady=(4, 6))

        self.cb_var = tk.BooleanVar(value=self.is_completed)
        self.cb = ctk.CTkCheckBox(
            body,
            text=f"~ {self.original_title} ~" if self.is_completed else self.original_title,
            variable=self.cb_var,
            command=self._on_check_toggle,
            fg_color="#10b981",
            hover_color="#059669",
            checkmark_color="#ffffff",
            text_color=TEXT_MUTED if self.is_completed else TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                weight="bold" if not self.is_completed else "normal",
                slant="italic" if self.is_completed else "roman"
            )
        )
        self.cb.pack(side="left", fill="x", expand=True)

        # Fila de Badges: Fecha, Hora y Estado
        badges_row = ctk.CTkFrame(self, fg_color="transparent")
        badges_row.pack(fill="x", padx=14, pady=(2, 10))

        # Badge Fecha
        date_display = self._format_date_badge(self.date_str)
        self.frame_date = ctk.CTkFrame(
            badges_row,
            fg_color="#061c2d" if not self.is_completed else "#0d1520",
            border_color="#0284c7" if not self.is_completed else "#1e293b",
            border_width=1,
            corner_radius=6
        )
        self.frame_date.pack(side="left", padx=(0, 6))

        self.lbl_date = ctk.CTkLabel(
            self.frame_date,
            text=f"📅 {date_display}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8" if not self.is_completed else "#64748b"
        )
        self.lbl_date.pack(padx=8, pady=3)

        # Badge Hora
        self.frame_time = ctk.CTkFrame(
            badges_row,
            fg_color="#172554" if not self.is_completed else "#0e1726",
            border_color="#2563ff" if not self.is_completed else "#1e293b",
            border_width=1,
            corner_radius=6
        )
        self.frame_time.pack(side="left", padx=(0, 6))

        self.lbl_time_badge = ctk.CTkLabel(
            self.frame_time,
            text=f"⏰ {self.time_str}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#60a5fa" if not self.is_completed else "#64748b"
        )
        self.lbl_time_badge.pack(padx=8, pady=3)

        # Badge Estado
        self.lbl_status = ctk.CTkLabel(
            badges_row,
            text="[COMPLETADA]" if self.is_completed else "[PENDIENTE]",
            font=ctk.CTkFont(family="Consolas", size=9, weight="bold"),
            text_color="#10b981" if self.is_completed else "#f59e0b"
        )
        self.lbl_status.pack(side="left", padx=(4, 0))

        self._last_width = None
        self.bind("<Configure>", self._on_card_resize)

    def _parse_composite_text_if_needed(self):
        """Extrae título, fecha y hora si la tarjeta fue invocada con el texto directo de resultado."""
        raw = self.original_title
        if "Tarea Guardada:" in raw or "[✔ Tarea" in raw:
            m_title = re.search(r"['\"](.*?)['\"]", raw)
            if m_title:
                self.original_title = m_title.group(1).strip()

            m_date = re.search(r"para\s+(?:el\s+)?(\d{1,2}\s+[a-zA-Z]{3,10}(?:\s+\d{4})?|\d{4}-\d{2}-\d{2}|hoy|mañana)", raw, re.IGNORECASE)
            if m_date and not self.date_str:
                self.date_str = m_date.group(1).strip()

            m_time = re.search(r"(?:a\s+las\s+|a\s+la\s+)(\d{1,2}:\d{2})", raw, re.IGNORECASE)
            if m_time and (not self.time_str or self.time_str == "15:00"):
                self.time_str = m_time.group(1).strip()

    def _format_date_badge(self, date_val: str) -> str:
        """Formatea la fecha de manera elegante."""
        if not date_val:
            return datetime.datetime.now().strftime("%d %b %Y")
        try:
            from tools.memory_tools import format_badge_date
            res = format_badge_date(date_val)
            return res.replace("📅", "").strip()
        except Exception:
            return date_val

    def _on_check_toggle(self):
        """Maneja el marcado / desmarcado interactivo."""
        new_completed = self.cb_var.get()
        self.is_completed = new_completed

        if new_completed:
            self.cb.configure(
                text=f"~ {self.original_title} ~",
                text_color=TEXT_MUTED,
                font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic")
            )
            self.configure(fg_color="#080c14", border_color="#1e293b")
            self.lbl_status.configure(text="[COMPLETADA]", text_color="#10b981")
        else:
            self.cb.configure(
                text=self.original_title,
                text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            )
            self.configure(fg_color="#0b1324", border_color="#0284c7")
            self.lbl_status.configure(text="[PENDIENTE]", text_color="#f59e0b")

        try:
            if self.on_toggle:
                self.on_toggle(new_completed)
            elif self.task_id:
                from memory.manager import get_memory_manager
                get_memory_manager().set_task_completed(self.task_id, new_completed)
            else:
                from tools.memory_tools import complete_user_task
                if new_completed:
                    complete_user_task(title_or_id=self.original_title)
        except Exception as e:
            print(f"[TaskCard] Nota: No se pudo sincronizar estado de tarea: {e}")

    def _on_card_resize(self, event):
        """Ajuste dinámico al redimensionar la tarjeta de tarea."""
        if event.widget != self:
            return
        if event.width <= 100:
            return
        if getattr(self, "_last_width", None) == event.width:
            return
        self._last_width = event.width
        ancho_ajustado = max(240, event.width - 80)
        try:
            self.cb.configure(wraplength=ancho_ajustado)
        except Exception:
            pass

    def update_wraplength(self, wrap_width: int):
        try:
            ancho_ajustado = max(240, wrap_width - 80)
            self.cb.configure(wraplength=ancho_ajustado)
        except Exception:
            pass


__all__ = [
    "CodeBlockFrame",
    "UserMessageCard",
    "VexResponseCard",
    "ToolActionCard",
    "MediaPlayerCard",
    "TaskInteractiveCard"
]
