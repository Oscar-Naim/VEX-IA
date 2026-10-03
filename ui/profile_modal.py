"""
LYAXIS labs™ - Modal de Gestión y Creación de Perfiles de Operador (ui/profile_modal.py)
Permite registrar nuevos usuarios con memoria persistente, velocidad de voz personalizada
y preferencias iniciales con estética Cyberpunk integrada al HUD de VEX.
"""
import re
import customtkinter as ctk
from typing import Optional, Callable, Dict, Any

import config
from memory.manager import get_memory_manager
from ui.styles import (
    BG_ROOT,
    BORDER_BLUE,
    BORDER_CYAN,
    ACCENT_CYAN,
    ACCENT_BLUE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    get_font_badge
)


class UserProfileModal(ctk.CTkToplevel):
    """
    Diálogo modal para registrar un nuevo operador con perfil de memoria persistente en VEX.
    """

    def __init__(self, master, on_save_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        super().__init__(master)
        self.on_save_callback = on_save_callback

        self.title("LYAXIS labs™ // VEX - Registro de Operador")
        self.geometry("520x620")
        self.minsize(480, 560)
        self.configure(fg_color=BG_ROOT)

        self.transient(master)
        self.grab_set()

        self._build_ui()
        self._center_window(master)

    def _center_window(self, master):
        """Centra la ventana modal sobre la ventana principal."""
        try:
            self.update_idletasks()
            master_x = master.winfo_x()
            master_y = master.winfo_y()
            master_w = master.winfo_width()
            master_h = master.winfo_height()

            w = 520
            h = 620
            x = max(50, master_x + (master_w - w) // 2)
            y = max(50, master_y + (master_h - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        # Marco contenedor exterior Cyberpunk
        self.container = ctk.CTkFrame(
            self,
            fg_color="#0b0f19",
            border_color=BORDER_BLUE,
            border_width=1.2,
            corner_radius=14
        )
        self.container.pack(fill="both", expand=True, padx=16, pady=16)

        # Encabezado
        lbl_badge = ctk.CTkLabel(
            self.container,
            text="👤 PERFIL DE MEMORIA PERSISTENTE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_badge.pack(pady=(16, 2))

        lbl_title = ctk.CTkLabel(
            self.container,
            text="REGISTRO DE NUEVO OPERADOR",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_title.pack(pady=(0, 4))

        lbl_desc = ctk.CTkLabel(
            self.container,
            text="Configura tu identidad. VEX recordará tus rutinas, tareas y preferencias de forma individual.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY,
            wraplength=440,
            justify="center"
        )
        lbl_desc.pack(pady=(0, 14))

        # Contenedor scrolleable
        scroll = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent",
            scrollbar_button_color="#18233b",
            scrollbar_button_hover_color=ACCENT_BLUE
        )
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        # 1. Nombre visible (Display Name)
        lbl_name = ctk.CTkLabel(
            scroll,
            text="NOMBRE DEL OPERADOR (DISPLAY NAME):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_name.pack(anchor="w", padx=10, pady=(6, 2))

        self.entry_name = ctk.CTkEntry(
            scroll,
            placeholder_text="ej. Alexis, Valeria, Comandante...",
            height=36,
            fg_color="#060910",
            border_color="#1e293b",
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.entry_name.pack(fill="x", padx=10, pady=(0, 10))
        self.entry_name.bind("<KeyRelease>", self._on_name_change)

        # 2. Identificador de archivo (user_id slug)
        lbl_id = ctk.CTkLabel(
            scroll,
            text="IDENTIFICADOR ÚNICO (SLUG DE ARCHIVO JSON):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_id.pack(anchor="w", padx=10, pady=(4, 2))

        self.entry_id = ctk.CTkEntry(
            scroll,
            placeholder_text="ej. alexis",
            height=34,
            fg_color="#060910",
            border_color="#1e293b",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.entry_id.pack(fill="x", padx=10, pady=(0, 10))

        # 3. Velocidad de Voz (Voice Speed)
        lbl_speed = ctk.CTkLabel(
            scroll,
            text="CADENCIA / VELOCIDAD DE VOZ NEURAL:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_speed.pack(anchor="w", padx=10, pady=(4, 2))

        self.speed_options = [
            "+15% (Recomendado - Táctica y Ágil)",
            "+0% (Estándar Neutra)",
            "+10% (Fluida Rápida)",
            "+25% (Ultra Dinámica)",
            "-10% (Pausada y Calma)"
        ]
        self.menu_speed = ctk.CTkOptionMenu(
            scroll,
            values=self.speed_options,
            height=34,
            fg_color="#0e1526",
            button_color="#16223d",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#080c16",
            dropdown_hover_color="#18233b",
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.menu_speed.set(self.speed_options[0])
        self.menu_speed.pack(fill="x", padx=10, pady=(0, 12))

        # 4. Preferencia Musical Inicial
        lbl_music = ctk.CTkLabel(
            scroll,
            text="PREFERENCIA MUSICAL INICIAL (HECHO A RECORDAR):",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_music.pack(anchor="w", padx=10, pady=(4, 2))

        self.entry_music = ctk.CTkEntry(
            scroll,
            placeholder_text="ej. Rock y Hip Hop, Synthwave, Lo-Fi...",
            height=34,
            fg_color="#060910",
            border_color="#1e293b",
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.entry_music.pack(fill="x", padx=10, pady=(0, 10))

        # 5. Navegador Preferido
        lbl_browser = ctk.CTkLabel(
            scroll,
            text="NAVEGADOR PRINCIPAL DEL OPERADOR:",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_browser.pack(anchor="w", padx=10, pady=(4, 2))

        self.browser_options = ["Google Chrome", "Microsoft Edge", "Brave", "Mozilla Firefox"]
        self.menu_browser = ctk.CTkOptionMenu(
            scroll,
            values=self.browser_options,
            height=34,
            fg_color="#0e1526",
            button_color="#16223d",
            button_hover_color=ACCENT_BLUE,
            dropdown_fg_color="#080c16",
            dropdown_hover_color="#18233b",
            text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.menu_browser.set("Google Chrome")
        self.menu_browser.pack(fill="x", padx=10, pady=(0, 10))

        # Mensaje de error/estado
        self.lbl_status = ctk.CTkLabel(
            self.container,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#f87171"
        )
        self.lbl_status.pack(pady=(2, 6))

        # Botones de Acción
        frame_actions = ctk.CTkFrame(self.container, fg_color="transparent")
        frame_actions.pack(fill="x", padx=12, pady=(0, 12))

        self.btn_cancel = ctk.CTkButton(
            frame_actions,
            text="CANCELAR",
            width=110,
            height=36,
            fg_color="#161f30",
            hover_color="#222f46",
            text_color=TEXT_MUTED,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=self.destroy
        )
        self.btn_cancel.pack(side="left", padx=(0, 8))

        self.btn_save = ctk.CTkButton(
            frame_actions,
            text="⚡ CREAR Y ACTIVAR PERFIL",
            height=36,
            fg_color="#0e2238",
            hover_color="#163454",
            border_color=BORDER_CYAN,
            border_width=1.2,
            text_color=ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            command=self._on_save
        )
        self.btn_save.pack(side="left", fill="x", expand=True)

        # Foco inicial
        self.after(100, lambda: self.entry_name.focus_set())

    def _on_name_change(self, event=None):
        """Auto-genera el identificador slug cuando el usuario escribe su nombre si el ID no fue modificado manualmente."""
        name = self.entry_name.get().strip()
        slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
        slug = re.sub(r"[-\s]+", "_", slug)
        self.entry_id.delete(0, "end")
        self.entry_id.insert(0, slug)

    def _on_save(self):
        """Valida y guarda el nuevo perfil de usuario en el gestor de memoria."""
        name = self.entry_name.get().strip()
        user_id = self.entry_id.get().strip().lower()

        if not name:
            self.lbl_status.configure(text="⚠️ Ingresa un nombre para el operador.")
            self.entry_name.focus_set()
            return

        if not user_id:
            user_id = re.sub(r"[^\w\s-]", "", name).strip().lower()
            user_id = re.sub(r"[-\s]+", "_", user_id) or "operador"

        # Extraer velocidad de voz limpia (+15%, +0%, etc.)
        speed_raw = self.menu_speed.get()
        speed_match = re.search(r"([+-]\d+%)", speed_raw)
        voice_speed = speed_match.group(1) if speed_match else "+15%"

        # Hechos iniciales
        initial_facts = {}
        music_pref = self.entry_music.get().strip()
        if music_pref:
            initial_facts["preferencia_musica"] = music_pref

        browser_pref = self.menu_browser.get().strip()
        if browser_pref:
            initial_facts["navegador"] = browser_pref

        try:
            manager = get_memory_manager()
            profile = manager.create_profile(
                user_id=user_id,
                display_name=name,
                voice_speed=voice_speed,
                initial_facts=initial_facts
            )

            # Activar inmediatamente
            manager.switch_user(user_id)
            config.set_user_name(name)

            if self.on_save_callback:
                try:
                    self.on_save_callback(profile)
                except Exception as ex:
                    print(f"[UserProfileModal] Error en on_save_callback: {ex}")

            self.destroy()

        except Exception as e:
            self.lbl_status.configure(text=f"❌ Error al crear perfil: {e}")
