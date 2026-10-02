"""
LYAXIS labs™ - Mini-VEX Floating Companion Widget
Widget flotante holográfico ultra-compacto 'Always-on-Top' con Visor Robótico animado,
soporte Drag & Drop fluido, opacidad inteligente, menú contextual táctico y conmutación
automática con la ventana principal del HUD.
"""
import tkinter as tk
from typing import Optional, Callable
import customtkinter as ctk

from ui.robot_visor import RobotVisorCanvas
from ui.styles import ACCENT_CYAN, ACCENT_BLUE, BORDER_BLUE, BG_ROOT


class FloatingWidget(ctk.CTkToplevel):
    """
    Mini-VEX Companion:
    Ventana flotante sin bordes, fija siempre al frente (Always-on-Top),
    con visor robótico reactivo para acompañar al usuario sin tapar su pantalla.
    """

    WIDGET_WIDTH = 210
    WIDGET_HEIGHT = 120

    def __init__(
        self,
        master,
        on_restore: Optional[Callable[[], None]] = None,
        on_toggle_hands_free: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None
    ):
        super().__init__(master)

        self.on_restore_callback = on_restore
        self.on_toggle_hf_callback = on_toggle_hands_free
        self.on_quit_callback = on_quit

        # Configuración de ventana sin marco y siempre arriba
        self.overrideredirect(True)
        self.wm_attributes("-topmost", True)
        self.configure(fg_color="#000000")

        # Opacidad inicial
        self._default_alpha = 0.93
        self._hover_alpha = 1.0
        try:
            self.wm_attributes("-alpha", self._default_alpha)
        except Exception:
            pass

        # Posicionamiento inicial: esquina inferior derecha sobre la barra de tareas
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(20, screen_w - self.WIDGET_WIDTH - 30)
        pos_y = max(20, screen_h - self.WIDGET_HEIGHT - 75)
        self.geometry(f"{self.WIDGET_WIDTH}x{self.WIDGET_HEIGHT}+{pos_x}+{pos_y}")

        # Contenedor estilizado tipo cápsula cibernética
        self.container = ctk.CTkFrame(
            self,
            width=self.WIDGET_WIDTH,
            height=self.WIDGET_HEIGHT,
            fg_color="#04060a",
            border_color=BORDER_BLUE,
            border_width=1.5,
            corner_radius=14
        )
        self.container.pack(fill="both", expand=True)

        # Barra decorativa superior de arrastre (pill indicator)
        self.drag_indicator = ctk.CTkFrame(
            self.container,
            height=3,
            width=38,
            fg_color="#1e293b",
            corner_radius=2
        )
        self.drag_indicator.pack(side="top", pady=(4, 1))

        # Visor Robótico animado compacto
        self.visor = RobotVisorCanvas(
            self.container,
            width=self.WIDGET_WIDTH - 12,
            height=self.WIDGET_HEIGHT - 16
        )
        self.visor.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Menú contextual rápido con clic derecho
        self._create_context_menu()

        # Registro de eventos de arrastre, doble clic, clic derecho y hover
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._bind_events_recursive(self)

    # ================= EVENTOS Y ARRASTRE (DRAG & DROP) =================

    def _bind_events_recursive(self, widget):
        """Asocia recursivamente los controladores de arrastre y control a cada sub-elemento."""
        try:
            widget.bind("<ButtonPress-1>", self._on_drag_start, add=True)
            widget.bind("<B1-Motion>", self._on_drag_motion, add=True)
            widget.bind("<Double-Button-1>", self._on_double_click, add=True)
            widget.bind("<Button-3>", self._show_context_menu, add=True)
            widget.bind("<Enter>", lambda e: self._on_hover(True), add=True)
            widget.bind("<Leave>", lambda e: self._on_hover(False), add=True)
        except Exception:
            pass

        for child in widget.winfo_children():
            self._bind_events_recursive(child)

    def _on_drag_start(self, event):
        """Registra el punto inicial del arrastre en coordenadas de pantalla."""
        self._drag_start_x = event.x_root - self.winfo_x()
        self._drag_start_y = event.y_root - self.winfo_y()

    def _on_drag_motion(self, event):
        """Mueve la ventana suavemente siguiendo el cursor del ratón."""
        x = event.x_root - self._drag_start_x
        y = event.y_root - self._drag_start_y
        self.geometry(f"+{x}+{y}")

    def _on_hover(self, hovering: bool):
        """Ajusta opacidad y resplandor del borde al pasar el ratón."""
        try:
            if hovering:
                self.wm_attributes("-alpha", self._hover_alpha)
                self.container.configure(border_color=ACCENT_CYAN)
                self.drag_indicator.configure(fg_color="#38bdf8")
            else:
                self.wm_attributes("-alpha", self._default_alpha)
                self.container.configure(border_color=BORDER_BLUE)
                self.drag_indicator.configure(fg_color="#1e293b")
        except Exception:
            pass

    def _on_double_click(self, event):
        """Doble clic para restaurar la ventana completa de VEX."""
        self.restore_main_window()

    # ================= MENÚ CONTEXTUAL =================

    def _create_context_menu(self):
        """Crea el menú minimalista emergente con clic derecho."""
        self.context_menu = tk.Menu(
            self,
            tearoff=0,
            bg="#060913",
            fg="#94a3b8",
            activebackground="#2563ff",
            activeforeground="#ffffff",
            activeborderwidth=0,
            relief="flat",
            bd=1,
            font=("Segoe UI", 9)
        )
        self.context_menu.add_command(
            label="  ⧉  Expandir a ventana completa",
            command=self.restore_main_window
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="  ⚡  Alternar Modo Manos Libres",
            command=self._on_toggle_hands_free
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="  ✕  Cerrar asistente VEX",
            command=self._on_quit
        )

    def _show_context_menu(self, event):
        """Muestra el menú emergente bajo el cursor."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # ================= ACCIONES DE CONTROL =================

    def restore_main_window(self):
        """Notifica para ocultar este widget y restaurar la ventana principal."""
        if self.on_restore_callback:
            self.on_restore_callback()

    def _on_toggle_hands_free(self):
        """Alterna el modo manos libres."""
        if self.on_toggle_hf_callback:
            self.on_toggle_hf_callback()

    def _on_quit(self):
        """Cierra la aplicación por completo."""
        if self.on_quit_callback:
            self.on_quit_callback()

    # ================= MÉTODOS DE SINCRONIZACIÓN DEL VISOR =================

    def set_state(self, new_state: str):
        """Sincroniza el estado operativo (idle, listening, thinking, speaking)."""
        self.visor.set_state(new_state)

    def set_speaking(self, speaking: bool):
        """Activa o desactiva la articulación fonética de la boca."""
        self.visor.set_speaking(speaking)

    def set_expression(self, expr_name: str, duration: Optional[float] = None):
        """Proyecta una expresión facial en el visor del widget."""
        self.visor.set_expression(expr_name, duration)

    def show_icon(self, icon_name: str, duration: float = 3.0):
        """Proyecta un icono contextual (música, notas, reloj, etc.) en el visor."""
        self.visor.show_icon(icon_name, duration)

    def trigger_wake_flash(self, duration: float = 0.65):
        """Dispara el destello cian reactivo al escuchar la palabra clave 'VEX'."""
        self.visor.trigger_wake_flash(duration)
