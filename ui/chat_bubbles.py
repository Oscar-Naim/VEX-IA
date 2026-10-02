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

        # Texto del mensaje
        self.lbl_text = ctk.CTkLabel(
            self,
            text=text,
            font=get_font_body(),
            text_color=TEXT_PRIMARY,
            justify="left",
            anchor="w"
        )
        self.lbl_text.pack(fill="x", padx=14, pady=(0, 12))

    def update_wraplength(self, wrap_width: int):
        """Actualiza el ancho de envoltura del texto responsivamente."""
        try:
            self.lbl_text.configure(wraplength=max(260, wrap_width))
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
        self.content_frame.pack(fill="x", padx=14, pady=(2, 6))

        self.text_labels: List[ctk.CTkLabel] = []
        self._parse_and_render_content(raw_text)

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
                anchor="w"
            )
            lbl.pack(fill="x", pady=2)
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
                    anchor="w"
                )
                lbl.pack(fill="x", pady=2)
                self.text_labels.append(lbl)

            if i + 2 < len(parts):
                lang = parts[i + 1].strip() or "code"
                code_body = parts[i + 2]
                code_frame = CodeBlockFrame(self.content_frame, code_text=code_body, language=lang)
                code_frame.pack(fill="x", pady=6)
                i += 3
            else:
                break

    def update_wraplength(self, wrap_width: int):
        """Ajusta el ancho de envoltura de los textos dentro de la burbuja."""
        for lbl in self.text_labels:
            try:
                lbl.configure(wraplength=max(260, wrap_width))
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
            text=f"✔ {action_title}:",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#10b981"
        )
        lbl_title.pack(side="left")

        lbl_detail = ctk.CTkLabel(
            inner,
            text=f"'{detail}'" if detail else "",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#a7f3d0"
        )
        lbl_detail.pack(side="left", padx=(4, 0))

        lbl_time = ctk.CTkLabel(
            inner,
            text=time_str,
            font=ctk.CTkFont(family="Consolas", size=9),
            text_color=TEXT_MUTED
        )
        lbl_time.pack(side="right")
