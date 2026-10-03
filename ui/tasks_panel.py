"""
LYAXIS labs™ - Panel Visual de Tareas y Recordatorios (ui/tasks_panel.py)
Panel interactivo con diseño Cyberpunk sincronizado en tiempo real con la memoria
persistente multi-usuario (memory/profiles/<usuario>.json).
Soporta badges de fecha de calendario real (📅 DD Mes YYYY), hora (⏰ HH:MM) y títulos limpios.
"""
import datetime
import tkinter as tk
import customtkinter as ctk
from typing import Optional, Callable

from memory.manager import get_memory_manager
from tools.memory_tools import (
    format_badge_date,
    normalize_task_date,
    normalize_task_time,
    clean_task_title
)
from ui.styles import (
    BG_ROOT,
    BORDER_BLUE,
    BORDER_CYAN,
    BORDER_SUBTLE,
    ACCENT_CYAN,
    ACCENT_BLUE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED
)


class TasksPanelModal(ctk.CTkToplevel):
    """
    Panel modal moderno para gestionar la lista de tareas y recordatorios del operador.
    Sincronizado bidireccionalmente con la memoria local y accesible tanto por interfaz
    como por órdenes de voz del asistente VEX.
    """

    def __init__(self, master=None):
        super().__init__(master)

        self.title("LYAXIS labs™ // VEX - Tareas y Recordatorios")
        self.geometry("560x680")
        self.minsize(500, 580)
        self.configure(fg_color=BG_ROOT)

        # Configuración modal flotante centrada
        if master:
            self.transient(master)
        self.after(100, self.lift)

        self.mem = get_memory_manager()

        self._build_ui()
        self._center_window(master)

        # Suscripción a eventos de cambio en la memoria para sincronización en vivo
        self.mem.subscribe_changes(self._on_memory_changed_threadsafe)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_window(self, master):
        """Centra la ventana respecto a la ventana principal."""
        try:
            self.update_idletasks()
            if master:
                master_x = master.winfo_x()
                master_y = master.winfo_y()
                master_w = master.winfo_width()
                master_h = master.winfo_height()
                w = 560
                h = 680
                x = max(50, master_x + (master_w - w) // 2)
                y = max(50, master_y + (master_h - h) // 2)
                self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def _on_close(self):
        """Desuscribe escuchas y destruye la ventana ordenadamente."""
        try:
            self.mem.unsubscribe_changes(self._on_memory_changed_threadsafe)
        except Exception:
            pass
        self.destroy()

    def _on_memory_changed_threadsafe(self):
        """Re-renderiza la lista de tareas de forma thread-safe cuando la voz modifica la memoria."""
        try:
            self.after(0, self._render_tasks)
        except Exception:
            pass

    def _build_ui(self):
        # Marco exterior con estética cibernética
        self.container = ctk.CTkFrame(
            self,
            fg_color="#0b0f19",
            border_color=BORDER_BLUE,
            border_width=1.2,
            corner_radius=14
        )
        self.container.pack(fill="both", expand=True, padx=16, pady=16)

        # 1. ENCABEZADO
        header_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(16, 10))

        lbl_badge = ctk.CTkLabel(
            header_frame,
            text="📝 AGENDA TÁCTICA // MEMORIA PERSISTENTE",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_badge.pack(anchor="w")

        lbl_title = ctk.CTkLabel(
            header_frame,
            text="TAREAS Y RECORDATORIOS",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=ACCENT_CYAN
        )
        lbl_title.pack(anchor="w", pady=(2, 2))

        user_name = self.mem.get_active_user_name()
        self.lbl_subtitle = ctk.CTkLabel(
            header_frame,
            text=f"Operador activo: {user_name} • Sincronizado en tiempo real",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=TEXT_SECONDARY
        )
        self.lbl_subtitle.pack(anchor="w")

        # 2. FORMULARIO SUPERIOR (AGREGAR NUEVA TAREA CON FECHA Y HORA)
        form_card = ctk.CTkFrame(
            self.container,
            fg_color="#101827",
            border_color=BORDER_SUBTLE,
            border_width=1,
            corner_radius=10
        )
        form_card.pack(fill="x", padx=20, pady=(0, 14))

        lbl_form = ctk.CTkLabel(
            form_card,
            text="NUEVA TAREA O RECORDATORIO",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_MUTED
        )
        lbl_form.pack(anchor="w", padx=14, pady=(10, 6))

        # Fila 1: Título de la tarea
        self.entry_task = ctk.CTkEntry(
            form_card,
            placeholder_text="Descripción limpia (ej. Tengo que salir, Revisar el coche...)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0b1120",
            border_color=BORDER_SUBTLE,
            text_color=TEXT_PRIMARY,
            height=36
        )
        self.entry_task.pack(fill="x", padx=14, pady=(0, 8))
        self.entry_task.bind("<Return>", lambda e: self._on_add_task())

        # Fila 2: Selector de Fecha, Hora y Botón Agregar
        row2 = ctk.CTkFrame(form_card, fg_color="transparent")
        row2.pack(fill="x", padx=14, pady=(0, 12))

        # Campo de fecha
        today_iso = datetime.date.today().strftime("%Y-%m-%d")
        self.entry_date = ctk.CTkEntry(
            row2,
            placeholder_text=f"Fecha (ej. {today_iso}, 5 de oct, mañana)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0b1120",
            border_color=BORDER_SUBTLE,
            text_color=TEXT_PRIMARY,
            width=210,
            height=34
        )
        self.entry_date.insert(0, today_iso)
        self.entry_date.pack(side="left", padx=(0, 8))
        self.entry_date.bind("<Return>", lambda e: self._on_add_task())

        # Selector de hora militar (HH:MM)
        time_options = [
            "08:00", "09:00", "10:00", "11:00", "12:00",
            "13:00", "14:00", "15:00", "16:00", "17:00",
            "18:00", "19:00", "20:00", "21:00", "22:00"
        ]
        now_hour = (datetime.datetime.now().hour + 1) % 24
        default_time = f"{now_hour:02d}:00"
        if default_time not in time_options:
            time_options.append(default_time)
            time_options.sort()

        self.opt_time = ctk.CTkOptionMenu(
            row2,
            values=time_options,
            width=85,
            height=34,
            fg_color="#1e293b",
            button_color="#2563ff",
            button_hover_color="#1d4ed8",
            dropdown_fg_color="#0f172a",
            dropdown_text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        self.opt_time.set(default_time)
        self.opt_time.pack(side="left", padx=(0, 8))

        # Botón Agregar Tarea
        btn_add = ctk.CTkButton(
            row2,
            text="+ Agregar",
            width=100,
            height=34,
            fg_color="#2563ff",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=8,
            command=self._on_add_task
        )
        btn_add.pack(side="left", fill="x", expand=True)

        # 3. LISTA DE TAREAS SCROLLEABLE
        list_header = ctk.CTkFrame(self.container, fg_color="transparent")
        list_header.pack(fill="x", padx=20, pady=(4, 6))

        self.lbl_list_count = ctk.CTkLabel(
            list_header,
            text="TAREAS PROGRAMADAS (0)",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color=TEXT_MUTED
        )
        self.lbl_list_count.pack(side="left")

        self.scroll_tasks = ctk.CTkScrollableFrame(
            self.container,
            fg_color="transparent",
            corner_radius=8
        )
        self.scroll_tasks.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # Render inicial de tareas
        self._render_tasks()

    def _on_add_task(self):
        """Registra la tarea ingresada en el perfil activo con fecha y hora normalizadas."""
        text = self.entry_task.get().strip()
        if not text:
            return

        date_val = self.entry_date.get().strip() or datetime.date.today().strftime("%Y-%m-%d")
        time_val = self.opt_time.get().strip() or "10:00"

        title_clean = clean_task_title(text)
        date_norm = normalize_task_date(date_val)
        time_norm = normalize_task_time(time_val)

        self.mem.add_task(title=title_clean, date=date_norm, time=time_norm)
        self.entry_task.delete(0, "end")
        self._render_tasks()

    def _render_tasks(self):
        """Limpia y reconstruye las tarjetas de tareas en el contenedor scrolleable."""
        for widget in self.scroll_tasks.winfo_children():
            widget.destroy()

        tasks = self.mem.list_tasks(include_completed=True, for_date=None)
        # Ordenar tareas por fecha y hora
        tasks_sorted = sorted(tasks, key=lambda x: (x.get("completed", False), x.get("date", "9999-99-99"), x.get("time", "99:99")))
        self.lbl_list_count.configure(text=f"TAREAS PROGRAMADAS ({len(tasks)})")

        if not tasks_sorted:
            empty_frame = ctk.CTkFrame(self.scroll_tasks, fg_color="#0f172a", corner_radius=10)
            empty_frame.pack(fill="both", expand=True, padx=10, pady=30)

            lbl_icon = ctk.CTkLabel(
                empty_frame,
                text="✨",
                font=ctk.CTkFont(size=32)
            )
            lbl_icon.pack(pady=(24, 6))

            lbl_empty_title = ctk.CTkLabel(
                empty_frame,
                text="No hay tareas programadas",
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                text_color=TEXT_PRIMARY
            )
            lbl_empty_title.pack(pady=(0, 4))

            lbl_empty_hint = ctk.CTkLabel(
                empty_frame,
                text="Agrega una con el formulario superior o pídeselo a VEX por voz:\n\"VEX, recuérdame que el 5 de octubre tengo que salir\"",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_SECONDARY,
                justify="center"
            )
            lbl_empty_hint.pack(pady=(0, 24))
            return

        # Renderizar cada tarjeta de tarea
        for task in tasks_sorted:
            task_id = task.get("id", "")
            title = task.get("title", "")
            date_str = task.get("date", "")
            time_str = task.get("time", "10:00")
            is_completed = task.get("completed", False)

            self._create_task_card(task_id, title, date_str, time_str, is_completed)

    def _create_task_card(self, task_id: str, title: str, date_str: str, time_str: str, is_completed: bool):
        """
        Crea una tarjeta individual para la tarea con checkbox, badge de fecha real [📅 05 Oct 2026],
        badge de hora [⏰ 10:00] y botón eliminar.
        """
        card = ctk.CTkFrame(
            self.scroll_tasks,
            fg_color="#0d1526" if not is_completed else "#0a0e17",
            border_color="#1e293b" if not is_completed else "#162032",
            border_width=1,
            corner_radius=8
        )
        card.pack(fill="x", padx=4, pady=4)

        # Checkbox interactivo
        cb_var = tk.BooleanVar(value=is_completed)

        def on_toggle():
            new_val = cb_var.get()
            self.mem.set_task_completed(task_id, new_val)
            self._render_tasks()

        display_text = f"~ {title} ~" if is_completed else title
        cb = ctk.CTkCheckBox(
            card,
            text=display_text,
            variable=cb_var,
            command=on_toggle,
            fg_color="#2563ff",
            hover_color="#1d4ed8",
            checkmark_color="#ffffff",
            text_color=TEXT_MUTED if is_completed else TEXT_PRIMARY,
            font=ctk.CTkFont(
                family="Segoe UI",
                size=12,
                slant="italic" if is_completed else "roman"
            )
        )
        cb.pack(side="left", padx=(12, 8), pady=10, fill="x", expand=True)

        # 1. Badge de Fecha (📅 DD Mes YYYY - Neón Cyan)
        date_badge_text = format_badge_date(date_str)
        badge_date_frame = ctk.CTkFrame(
            card,
            fg_color="#061c2d" if not is_completed else "#0a131c",
            border_color="#0284c7" if not is_completed else "#1e293b",
            border_width=1,
            corner_radius=6
        )
        badge_date_frame.pack(side="left", padx=(0, 6), pady=8)

        lbl_badge_date = ctk.CTkLabel(
            badge_date_frame,
            text=date_badge_text,
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#38bdf8" if not is_completed else "#475569"
        )
        lbl_badge_date.pack(padx=7, pady=3)

        # 2. Badge de Hora (⏰ HH:MM - Neón Azul)
        badge_time_frame = ctk.CTkFrame(
            card,
            fg_color="#172554" if not is_completed else "#0e1726",
            border_color="#2563ff" if not is_completed else "#1e293b",
            border_width=1,
            corner_radius=6
        )
        badge_time_frame.pack(side="left", padx=(0, 6), pady=8)

        lbl_badge_time = ctk.CTkLabel(
            badge_time_frame,
            text=f"⏰ {time_str}",
            font=ctk.CTkFont(family="Consolas", size=10, weight="bold"),
            text_color="#60a5fa" if not is_completed else "#475569"
        )
        lbl_badge_time.pack(padx=7, pady=3)

        # 3. Botón Eliminar Tarea
        def on_delete():
            self.mem.delete_task(task_id)
            self._render_tasks()

        btn_del = ctk.CTkButton(
            card,
            text="✕",
            width=28,
            height=28,
            fg_color="transparent",
            hover_color="#ef444433",
            text_color="#ef4444",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            corner_radius=6,
            command=on_delete
        )
        btn_del.pack(side="right", padx=(4, 8), pady=8)


__all__ = ["TasksPanelModal"]
