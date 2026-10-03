"""
LYAXIS labs™ - Robot Visor Digital Expresivo e Inteligente (VEX Cyber-Pet HUD)
Rig de Ojos Robóticos Expresivos Procedurales (inspirado en Cozmo, Vector y LOOI).

Características del Sistema:
1. Geometría Orgánica: Superelipses (Squircles n=3.6) con deformación morfológica (Shape Morphing)
   continua y fluida de vértices (Happy, Curious, Cool Shades, Drowsy, Surprise, Love, Wink, Idle, etc.).
2. Físicas de Animación: Rebote elástico (Squash & Stretch) con oscilador armónico amortiguado
   (compresión a 0.05 y estiramiento en X al 112%, con overshoot de apertura a 1.08x).
3. Micro-movimientos Biológicos: Micro-sacádicos involuntarios (2 a 4px cada 3-5s),
   respiración digital senoidal (ciclo de 3s a ±2%) y seguimiento suave de mirada (Look at Mouse).
4. Acabado Visual OLED: Pantalla negro absoluto (#000000), halo difuminado multicapa de retroiluminación,
   cuerpo cian neón de alta luminosidad (#00d9ff), núcleo blanco cian (#bbf2ff) y reflejo de cristal.
5. API Limpia y Completa: set_emotion(), blink(), look_at(), start_speaking_bounce(), stop_speaking_bounce()
   con compatibilidad total con llamadas heredadas (RobotVisorCanvas, set_expression, set_state, etc.).
"""

import math
import random
import time
import datetime
import tkinter as tk
from typing import Optional, List, Tuple, Dict


class VisorState:
    """Máquina de estados de presencia y ciclo de vida de VEX."""
    AWAKE = "awake"                 # 0 - 60s: 100% despierto, atento, mirando ratón, micro-gestos
    PLAYFUL_IDLE = "playful_idle"   # 1 - 3 min: aburrido / juguetón, caras cómicas, tarareo
    DROWSY = "drowsy"               # 3 - 5 min: somnoliento, pestañeo pesado, bostezo, cabeceo
    SLEEPING = "sleeping"           # 5+ min: reposo profundo con Z z z flotantes
    ANIMATING_ACTION = "action"     # Secuencia narrativa activa (helado, sobresalto, etc.)


class RobotVisor(tk.Canvas):
    """
    Componente Canvas de alta fidelidad para el visor robótico de VEX.
    Renderiza ojos procedurales basados en superelipses (squircles) con deformación morfológica,
    físicas elásticas de squash & stretch, micro-movimientos sacádicos y brillo OLED.
    """

    NUM_POINTS = 32  # Resolución paramétrica por ojo para curvas orgánicas suaves

    def __init__(self, master, width: int = 520, height: int = 200, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            bg="#000000",
            highlightthickness=0,
            bd=0,
            **kwargs
        )
        self.width = width
        self.height = height

        # ---------------- 1. PALETA DE COLOR OLED NEÓN ----------------
        self.c_oled_black = "#000000"
        self.c_helmet_shell = "#050811"
        self.c_helmet_bevel = "#1d4ed8"
        self.c_glow_outer = "#022a3d"       # Halo difuminado de retroiluminación
        self.c_glow_mid = "#0090be"         # Bloom intermedio
        self.c_cyan_bright = "#00d9ff"     # Cian neón de alta luminosidad
        self.c_cyan_core = "#bbf2ff"       # Centro claro blanco cian
        self.c_cyan_dim = "#024a6b"
        self.c_white = "#ffffff"
        self.c_amber = "#f59e0b"
        self.c_amber_glow = "#fbbf24"
        self.c_pink_blush = "#f43f5e"
        self.c_pink_tongue = "#fb7185"
        self.c_green = "#10b981"
        self.c_green_glow = "#34d399"

        # ---------------- 2. ESTADOS OPERATIVOS Y EMOCIONALES ----------------
        self.state = "idle"         # "idle", "listening", "thinking", "speaking"
        self.is_speaking = False
        self._speaking_bounce = False
        self.visor_state = VisorState.AWAKE

        self.emotion = "idle"
        self._target_emotion = "idle"
        self._emotion_until: float = 0.0

        # Estado de ánimo persistente (Persistent Mood Machine)
        self.persistent_mood: Optional[str] = None
        self._curr_mouth_curvature: float = 0.2     # Curvatura spline continua [-1.0: triste, 0.2: reposo, 1.0: feliz]
        self._target_mouth_curvature: float = 0.2

        # Temporizador de inactividad progresiva
        self._last_activity_time: float = time.time()
        self._deep_sleep_forced: bool = False

        # ---------------- HALO DE LUZ AMBIENTAL REACTIVO (AMBIENT GLOW) ----------------
        self.ambient_glow_state: str = "idle"  # "idle", "listening", "music", "success", "task", "thinking"
        self.ambient_glow_until: float = 0.0
        self._curr_glow_rgb: List[float] = [0.0, 217.0, 255.0]  # RGB dinámico (Cian Neón inicial)

        # ---------------- 3. GEOMETRÍA ORGÁNICA Y SHAPE MORPHING ----------------
        # Vértices paramétricos normalizados [-1.0, 1.0] para cada ojo
        self._base_vertices = self._build_base_squircle_points(n=3.6, count=self.NUM_POINTS)
        self._curr_vertices_left = [list(pt) for pt in self._base_vertices]
        self._curr_vertices_right = [list(pt) for pt in self._base_vertices]

        # ---------------- 4. FÍSICAS DE RESORTE (SQUASH & STRETCH) ----------------
        self._is_blinking: bool = False
        self._blink_start_time: float = 0.0
        self._blink_duration: float = 0.15      # 120ms - 160ms en total
        self._blink_scale_x: float = 1.0
        self._blink_scale_y: float = 1.0
        self._next_blink_time: float = time.time() + random.uniform(3.0, 5.0)

        # ---------------- 5. MICRO-MOVIMIENTOS BIOLÓGICOS ----------------
        # Mirada suave interpolada (Look at Mouse / Target Gaze)
        self._gaze_x: float = 0.0
        self._gaze_y: float = 0.0
        self._target_gaze_x: float = 0.0
        self._target_gaze_y: float = 0.0
        self._mouse_nearby: bool = False

        # Sacadas involuntarias (micro-saltos de 2 a 4px)
        self._saccade_x: float = 0.0
        self._saccade_y: float = 0.0
        self._saccade_target_x: float = 0.0
        self._saccade_target_y: float = 0.0
        self._saccade_start_time: float = 0.0
        self._saccade_duration: float = 0.28
        self._next_saccade_time: float = time.time() + random.uniform(3.0, 5.0)

        # Micro-comportamientos ociosos (Quirks)
        self._current_quirk: Optional[str] = None
        self._quirk_start_time: float = 0.0
        self._quirk_duration: float = 0.0
        self._next_quirk_time: float = time.time() + random.uniform(4.5, 8.0)

        # ---------------- 6. ACCIONES NARRATIVAS E ICONOS ----------------
        self.active_action: Optional[str] = None
        self._action_start_time: float = 0.0
        self._action_duration: float = 0.0

        self.active_icon: Optional[str] = None
        self._icon_until: float = 0.0
        self._wake_flash_until: float = 0.0

        # Partículas tenues de polvo OLED para sensación de profundidad
        self.particles = []
        for _ in range(14):
            self.particles.append([
                random.uniform(10, max(20, width - 10)),
                random.uniform(10, max(20, height - 10)),
                random.uniform(0.15, 0.45),
                random.uniform(0.8, 1.5),
                random.choice(["#072033", "#042c44", "#0a1e30"])
            ])

        self._start_time = time.time()

        # ---------------- 7. EVENTOS DE ENTRADA Y SEGUIMIENTO ----------------
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self._on_canvas_mouse_move)
        self.bind("<Enter>", self._on_canvas_mouse_enter)
        self.bind("<Leave>", self._on_canvas_mouse_leave)
        self.bind("<Button-1>", self._on_canvas_click)

        # Conexión suave con la ventana superior para seguimiento global del ratón
        self.after(250, self._bind_window_mouse)

        # Bucle de animación procedural (~35 FPS)
        self._animate()

    # ================= MÉTODOS DE LA API PRINCIPAL =================

    def set_ambient_state(self, state_name: str, duration: Optional[float] = None):
        """
        Modifica dinámicamente el Halo de Luz Ambiental Reactivo (Ambient Glow):
        - 'idle' / 'listening': 🔵 Cian Neón (#00d9ff)
        - 'music': 🟣 Morado Cósmico (#a855f7)
        - 'success' / 'task': 🟢 Verde Esmeralda (#10b981)
        - 'thinking': 🟡 Ámbar / Naranja (#f59e0b)
        """
        cleaned = (state_name or "idle").lower().strip()
        self.ambient_glow_state = cleaned
        if duration and duration > 0:
            self.ambient_glow_until = time.time() + duration
        else:
            self.ambient_glow_until = 0.0

    @property
    def mood(self) -> str:
        """Devuelve el estado de ánimo persistente activo o la emoción actual."""
        if self.persistent_mood:
            return self.persistent_mood
        return self.emotion

    @mood.setter
    def mood(self, val: Optional[str]):
        """Define el estado de ánimo persistente o lo restablece si es None/idle/happy."""
        if not val or val.lower().strip() in ["idle", "none", "clear", "normal", "default"]:
            self.set_persistent_mood(None)
        elif val.lower().strip() in ["sad", "melancholy"]:
            self.set_persistent_mood("sad")
        elif val.lower().strip() in ["happy", "content", "alegre"]:
            self.set_persistent_mood("happy")
        else:
            self.persistent_mood = val.lower().strip()
            self.set_emotion(val)

    def set_persistent_mood(self, mood: Optional[str]):
        """
        Establece o limpia un estado de ánimo permanente e indefinido (Persistent Mood Machine).
        - 'sad': El visor permanece triste indefinidamente con ojos caídos y boca en ⁀.
        - 'angry': Ojos en diagonal agresiva, color rojo neón (#ff3366), boca tensa.
        - 'curious': Ojo izquierdo achinado/ceja alzada, ojo derecho dilatado.
        - 'cool'/'sunglasses': Gafas de sol cyberpunk sobre ojos con sonrisa ladeada.
        - 'happy' / None / 'idle': Limpia el modo y restaura la alegría.
        """
        if not mood or mood.lower().strip() in ["idle", "none", "clear", "normal", "default", "happy"]:
            self.persistent_mood = None
            if mood and mood.lower().strip() == "happy":
                self.set_emotion("happy", duration=6.0, force=True)
            else:
                self.set_emotion("idle", force=True)
            self._blink_duration = 0.15
            self._target_mouth_curvature = 0.22
            return

        cleaned = mood.lower().strip()
        # Aliases
        if cleaned in ["sunglasses", "cool_shades", "cool_sunglasses"]:
            cleaned = "cool"
        elif cleaned == "enojado":
            cleaned = "angry"
        elif cleaned == "curioso":
            cleaned = "curious"
        elif cleaned == "triste":
            cleaned = "sad"
        elif cleaned == "feliz":
            cleaned = "happy"

        self.persistent_mood = cleaned
        self._target_emotion = cleaned
        self.emotion = cleaned
        self._emotion_until = 0.0  # Sin temporizador: permanente hasta orden explícita

        if cleaned in ["sad", "melancholy"]:
            self._blink_duration = 0.28
            self._target_mouth_curvature = -1.0
        elif cleaned in ["happy", "love", "heart"]:
            self._blink_duration = 0.15
            self._target_mouth_curvature = 1.0
            self.register_user_activity()
        elif cleaned == "angry":
            self._blink_duration = 0.12
            self._target_mouth_curvature = -0.5
            self.register_user_activity()
        elif cleaned in ["cool", "curious"]:
            self._blink_duration = 0.15
            self._target_mouth_curvature = 0.1
            self.register_user_activity()
        else:
            self._blink_duration = 0.15

    def set_emotion(self, emotion_name: str, duration: Optional[float] = None, force: bool = False):
        """
        Cambia la emoción del visor con transición continua mediante Shape Morphing.
        Soporta: 'idle', 'happy', 'sad', 'curious', 'cool'/'cool_shades', 'drowsy',
                 'surprise', 'love', 'wink', 'thinking', 'sleeping'.
        """
        cleaned = emotion_name.lower().strip()
        if cleaned in ["cool_shades", "cool_sunglasses", "glasses"]:
            cleaned = "cool"

        # Si está en modo triste persistente, mantenerse en triste hasta que se ordene ser feliz
        if self.persistent_mood == "sad" and not force:
            if cleaned in ["happy", "alegre"]:
                self.persistent_mood = None
            else:
                return

        self._target_emotion = cleaned
        self.emotion = cleaned

        # Ajuste de curvatura objetivo de la boca según emoción
        if cleaned in ["happy", "love", "heart"]:
            self._target_mouth_curvature = 1.0
        elif cleaned in ["sad", "melancholy"]:
            self._target_mouth_curvature = -1.0
        elif cleaned in ["surprise", "shock", "alert"]:
            self._target_mouth_curvature = 0.0
        elif cleaned == "curious":
            self._target_mouth_curvature = 0.1
        else:
            self._target_mouth_curvature = 0.22

        if duration and duration > 0:
            self._emotion_until = time.time() + duration
        else:
            self._emotion_until = 0.0

        if cleaned in ["happy", "curious", "cool", "surprise", "love", "wink"]:
            self.register_user_activity()

    def blink(self):
        """Dispara un parpadeo reactivo con física elástica de resorte (Squash & Stretch)."""
        now = time.time()
        self._is_blinking = True
        self._blink_start_time = now
        self._blink_duration = 0.15

    def look_at(self, x: float, y: float):
        """
        Orienta suavemente la mirada hacia las coordenadas objetivo.
        Acepta coordenadas relativas a la ventana o normalizadas (-1.0 a 1.0).
        """
        w = float(self.width)
        h = float(self.height)
        # Si las coordenadas están en rango normalizado [-1, 1]
        if -1.5 <= x <= 1.5 and -1.5 <= y <= 1.5:
            self._target_gaze_x = max(-9.0, min(9.0, x * 9.0))
            self._target_gaze_y = max(-5.5, min(5.5, y * 5.5))
        else:
            # Coordenadas en píxeles de pantalla/ventana
            cx = w / 2.0
            cy = h / 2.0
            dx = x - cx
            dy = y - cy
            self._target_gaze_x = max(-9.0, min(9.0, dx / 24.0))
            self._target_gaze_y = max(-5.5, min(5.5, dy / 18.0))

    def start_speaking_bounce(self):
        """Inicia la modulación orgánica de habla (rebote rítmico fonético en ojos y boca)."""
        self._speaking_bounce = True
        self.is_speaking = True
        self.state = "speaking"
        self.register_user_activity()

    def stop_speaking_bounce(self):
        """Detiene la modulación de habla y regresa al reposo vivo."""
        self._speaking_bounce = False
        self.is_speaking = False
        if self.state == "speaking":
            self.state = "idle"

    # ================= MÉTODOS HEREDADOS (BACKWARD COMPATIBILITY) =================

    @property
    def expression(self) -> str:
        """Alias de compatibilidad con código que consulta visor.expression."""
        return self.emotion

    @expression.setter
    def expression(self, val: str):
        self.set_emotion(val)

    def set_expression(self, expr_name: str, duration: Optional[float] = None, force: bool = False):
        """Compatibilidad total con la firma anterior de set_expression."""
        cleaned = expr_name.lower().strip()
        if self.persistent_mood == "sad" and not force:
            if cleaned in ["happy", "alegre"]:
                self.persistent_mood = None
            else:
                return

        if cleaned == "sleeping":
            if force:
                self._deep_sleep_forced = True
                self.visor_state = VisorState.SLEEPING
                self.set_emotion("sleeping", force=True)
                return
            else:
                self.register_user_activity()
                self.set_emotion("idle", force=True)
                return
        self.set_emotion(cleaned, duration=duration, force=force)

    def set_state(self, new_state: str):
        """Actualiza el estado operativo (idle, listening, thinking, speaking)."""
        valid_states = ["idle", "listening", "thinking", "speaking"]
        cleaned = new_state.lower().strip()
        if cleaned in valid_states:
            self.state = cleaned
            if cleaned == "speaking":
                self.start_speaking_bounce()
            elif cleaned in ["listening", "thinking"]:
                self.stop_speaking_bounce()
                self.register_user_activity()
                if cleaned == "thinking":
                    self.set_emotion("thinking")
                elif cleaned == "listening":
                    self.set_emotion("idle")
            elif cleaned == "idle":
                self.stop_speaking_bounce()

    def set_speaking(self, speaking: bool):
        """Activa o desactiva la articulación fonética y el rebote al hablar."""
        if speaking:
            self.start_speaking_bounce()
        else:
            self.stop_speaking_bounce()

    def show_icon(self, icon_name: str, duration: float = 3.0):
        """Proyecta un icono contextual en pantalla (música, búsqueda, reloj, etc.)."""
        self.register_user_activity()
        if icon_name == "ice_cream":
            self.show_eating_icecream(duration=max(6.5, duration))
            return
        self.active_icon = icon_name
        self._icon_until = time.time() + duration

    def show_eating_icecream(self, duration: float = 7.0):
        """Secuencia narrativa del helado con 4 fases (aparición, mordiscos, satisfacción, guiño)."""
        self.register_user_activity()
        self.active_action = "eating_icecream"
        self._action_start_time = time.time()
        self._action_duration = duration
        self.visor_state = VisorState.ANIMATING_ACTION
        self.active_icon = None

    def play_temporary_emote(self, emote_name: str):
        """
        Ejecuta un emote temporal de corta duración y luego regresa al estado de ánimo
        activo (persistent_mood) sin dormirse.
        - 'ice_cream': Secuencia de ~7s con cono, 3 mordiscos y guiño final.
        - 'surprised': Ojos redondos dilatados y boca abierta (4 segundos).
        """
        self.register_user_activity()
        name = emote_name.lower().strip()
        if name == "ice_cream":
            self.show_eating_icecream(duration=7.0)
        elif name in ["surprised", "surprise"]:
            self.set_emotion("surprise", duration=4.0, force=True)
        else:
            self.set_emotion(name, duration=3.5, force=True)

    def reset_to_normal(self):
        """Limpia cualquier mood persistente y restaura el estado alegre normal."""
        self.set_persistent_mood(None)
        self.set_emotion("happy", duration=5.0, force=True)

    def trigger_wake_flash(self, duration: float = 0.65):
        """Efecto luminoso reactivo de onda expansiva al escuchar 'VEX'."""
        self.register_user_activity()
        self._wake_flash_until = time.time() + duration
        self.blink()
        self.set_emotion("idle", duration=duration + 0.5)

    def register_user_activity(self):
        """Registra actividad del usuario para reiniciar el temporizador de sueño."""
        now = time.time()
        if self.visor_state in [VisorState.DROWSY, VisorState.SLEEPING] or self._deep_sleep_forced:
            self.wake_up()
        else:
            self._last_activity_time = now
            self._deep_sleep_forced = False

    def wake_up(self):
        """Despierta a VEX con sobresalto cómico, apertura elástica y sonrisa alegre."""
        self._last_activity_time = time.time()
        self._deep_sleep_forced = False
        self.visor_state = VisorState.ANIMATING_ACTION
        self.active_action = "startle_wake"
        self._action_start_time = time.time()
        self._action_duration = 1.3
        self._current_quirk = None
        self.blink()

    # ================= EVENTOS Y ENLACES DE RATÓN =================

    def _bind_window_mouse(self):
        """Asocia la escucha de movimiento a la ventana superior de forma segura."""
        try:
            top = self.winfo_toplevel()
            if top:
                top.bind("<Motion>", self._on_window_mouse_move, add=True)
                top.bind("<Key>", lambda e: self.register_user_activity(), add=True)
        except Exception:
            pass

    def _on_resize(self, event):
        """Ajusta las dimensiones del visor responsivamente."""
        if event.width > 50 and event.height > 30:
            self.width = event.width
            self.height = event.height

    def _on_canvas_mouse_move(self, event):
        self.register_user_activity()
        self._mouse_nearby = True
        self.look_at(event.x, event.y)

    def _on_canvas_mouse_enter(self, event):
        self.register_user_activity()
        self._mouse_nearby = True

    def _on_canvas_mouse_leave(self, event):
        self._mouse_nearby = False

    def _on_canvas_click(self, event):
        self.register_user_activity()
        if self.visor_state in [VisorState.DROWSY, VisorState.SLEEPING]:
            self.wake_up()
        else:
            self.set_emotion("happy", duration=1.8)
            self.blink()

    def _on_window_mouse_move(self, event):
        """Detecta la posición del ratón en la ventana para seguimiento suave."""
        try:
            ptr_x = event.x_root
            ptr_y = event.y_root
            root_x = self.winfo_rootx()
            root_y = self.winfo_rooty()

            w = float(self.width)
            h = float(self.height)
            cx = root_x + w / 2.0
            cy = root_y + h / 2.0

            dx = ptr_x - cx
            dy = ptr_y - cy
            dist = math.hypot(dx, dy)

            if dist < 850.0:
                self._mouse_nearby = True
                self._target_gaze_x = max(-9.0, min(9.0, dx / 24.0))
                self._target_gaze_y = max(-5.5, min(5.5, dy / 18.0))
            else:
                self._mouse_nearby = False
                self._target_gaze_x = 0.0
                self._target_gaze_y = 0.0

            if dist < 450.0:
                self.register_user_activity()
        except Exception:
            pass

    # ================= 1. MATEMÁTICA DE SQUIRCLES Y MORFOLOGÍA =================

    @staticmethod
    def _build_base_squircle_points(n: float = 3.6, count: int = 32) -> List[Tuple[float, float]]:
        """
        Genera vértices base normalizados en [-1.0, 1.0] para una superelipse (Squircle).
        La fórmula paramétrica |x/a|^n + |y/b|^n = 1 con n=3.6 produce curvas G2 continuas y orgánicas.
        """
        pts = []
        for i in range(count):
            theta = 2.0 * math.pi * i / count
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            x = math.copysign(abs(cos_t) ** (2.0 / n), cos_t)
            y = math.copysign(abs(sin_t) ** (2.0 / n), sin_t)
            pts.append((x, y))
        return pts

    def _get_target_morph_vertices(self, emotion: str, is_left: bool = True) -> List[Tuple[float, float]]:
        """
        Aplica deformación procedural continua a los puntos del ojo según la emoción solicitada.
        Diseñado para mantener una superelipse orgánica (Squircle) sin dobleces ni auto-intersecciones.
        El ojo derecho se calcula como un espejo matemático exacto del izquierdo.
        """
        morphed = []
        for x, y in self._base_vertices:
            mx, my = x, y

            # 1. EMOCIÓN: FELIZ (Happy - ^  ^)
            # Base curvada hacia arriba en forma de media luna suave y sonriente
            if emotion in ["happy", "love", "heart", "affection"]:
                if y > -0.15:
                    my = y - 0.75 * (1.0 - min(1.0, x * x)) * max(0.1, y + 0.35)
                else:
                    my = y - 0.20 * (1.0 - min(1.0, x * x))
                my = (my * 0.82) + 0.10

            # 2. EMOCIÓN: TRISTE / MELANCÓLICO (Sad - caída suave del párpado superior)
            elif emotion in ["sad", "melancholy"]:
                if y < 0.15:
                    my = y + 0.42 * (1.0 - 0.28 * x * x)
                my = (my * 0.86) + 0.14

            # 3. EMOCIÓN: CURIOSO / ATENTO (Curious)
            elif emotion == "curious":
                if y < -0.15:
                    my = max(y, -0.45)
                mx *= 1.05
                my *= 1.05

            # 4. EMOCIÓN: COOL (Gafas de sol cyberpunk / angular shades)
            elif emotion in ["cool", "cool_shades"]:
                if y < -0.20:
                    my = -0.38
                if y > 0.0:
                    my = y - 0.42 * max(0.0, -x)

            # 4b. EMOCIÓN: ENOJADO (Angry - cejas en diagonal agresiva hacia adentro)
            elif emotion == "angry":
                # Parte superior del ojo: inclinación interna pronunciada (\  /)
                if y < 0.0:
                    # La mitad interior (x positivo para ojo izquierdo) baja agresivamente
                    tilt = 0.55 * x if is_left else -0.55 * x
                    my = y - max(0.0, tilt) * 0.9
                # Aplanar parte inferior para aspecto amenazante
                if y > 0.25:
                    my = 0.25 + (y - 0.25) * 0.4
                mx *= 0.95
                my *= 0.90

            # 5. EMOCIÓN: SOMNOLIENTO (Drowsy)
            elif emotion == "drowsy":
                if y < 0.05:
                    my = y + 0.60 * (1.0 - 0.25 * x * x)
                mx *= 1.08
                my = (my * 0.55) + 0.20

            # 6. EMOCIÓN: ASOMBRO / ALERTA (Surprise)
            elif emotion in ["surprise", "shock", "alert"]:
                mx *= 1.15
                my *= 1.15

            # 7. EMOCIÓN: PENSATIVO (Thinking)
            elif emotion == "thinking":
                if y < -0.15:
                    my = max(y, -0.40)
                mx *= 0.95
                my *= 0.95

            # 8. EMOCIÓN: REPOSO PROFUNDO (Sleeping)
            elif emotion == "sleeping":
                my *= 0.05

            morphed.append((mx, my))
        return morphed

    def _update_shape_morphing(self, dt: float):
        """
        Interpola gradualmente cada vértice hacia la emoción objetivo.
        Garantiza que el ojo derecho se renderice como un ESPEJO MATEMÁTICO EXACTO del ojo izquierdo:
        mismas curvas Bézier / Squircle, invirtiendo la coordenada horizontal X y preservando el orden
        de winding antihorario (CCW) de Tkinter para evitar deformaciones en forma de campana rota.
        """
        active_emo = self.emotion
        if self.visor_state == VisorState.SLEEPING:
            active_emo = "sleeping"
        elif self.state == "thinking" and self.emotion == "idle":
            active_emo = "thinking"

        target_l = self._get_target_morph_vertices(active_emo, is_left=True)

        # Factor de lerp suave y continuo
        lerp_speed = min(1.0, dt * 14.0)

        for i in range(self.NUM_POINTS):
            cl = self._curr_vertices_left[i]
            tl = target_l[i]
            cl[0] += (tl[0] - cl[0]) * lerp_speed
            cl[1] += (tl[1] - cl[1]) * lerp_speed

        if active_emo == "wink":
            # Guiño asimétrico: el ojo derecho se convierte en arco feliz cerrado
            target_r = []
            for x, y in self._base_vertices:
                if y > -0.1:
                    wy = y - 0.90 * (1.0 - min(1.0, x * x)) * max(0.1, y + 0.35)
                else:
                    wy = y - 0.25 * (1.0 - min(1.0, x * x))
                target_r.append((x, (wy * 0.3) + 0.15))
            for i in range(self.NUM_POINTS):
                cr = self._curr_vertices_right[i]
                tr = target_r[i]
                cr[0] += (tr[0] - cr[0]) * lerp_speed
                cr[1] += (tr[1] - cr[1]) * lerp_speed
        else:
            # Espejo matemático exacto del ojo izquierdo:
            # Invierte X (x -> -x) y recorre en orden inverso para mantener orientación CCW en Tkinter
            self._curr_vertices_right = [[-cl[0], cl[1]] for cl in reversed(self._curr_vertices_left)]

    # ================= 2. FÍSICAS DE RESORTE (SQUASH & STRETCH) =================

    def _update_blink_spring_physics(self, now: float):
        """
        Calcula las escalas Sx y Sy con física elástica de resorte y rebote (Overshoot):
        - Compresión en Y: 1.0 -> 0.05
        - Estiramiento en X: 1.0 -> 1.12 (+12% Squash)
        - Apertura: Damped oscillator con rebote por encima de 1.0 (1.08x Overshoot)
        - Modo Triste: Parpadeo lento y pesado (0.28s), sin rebote feliz y párpados caídos.
        """
        if self.visor_state == VisorState.SLEEPING:
            self._blink_scale_x = 1.0
            self._blink_scale_y = 0.05
            return

        is_sad = (self.emotion in ["sad", "melancholy"] or self.persistent_mood == "sad")

        # Pestañeo involuntario periódico si no está activo
        if not self._is_blinking and now >= self._next_blink_time:
            if not self.active_action and self.emotion != "sleeping":
                self.blink()

        if self._is_blinking:
            elapsed = now - self._blink_start_time
            dur = 0.28 if is_sad else self._blink_duration
            close_dur = dur * 0.40  # Bajada más pausada y pesada en tristeza

            if elapsed < close_dur:
                p = elapsed / close_dur
                # Compresión vertical
                self._blink_scale_y = 1.0 - 0.95 * math.sin(p * math.pi * 0.5)
                self._blink_scale_x = 1.0 + 0.12 * math.sin(p * math.pi * 0.5)
            else:
                topen = elapsed - close_dur
                # Oscilador armónico amortiguado (más lento y sin sobrepaso si está triste)
                zeta = 0.95 if is_sad else 0.88
                omega = 22.0 if is_sad else 34.0
                env = math.exp(-zeta * omega * topen)
                self._blink_scale_y = 1.0 - 0.95 * env * math.cos(omega * topen)
                self._blink_scale_x = 1.0 - 0.12 * (self._blink_scale_y - 1.0)

            if elapsed >= dur + 0.08:
                self._is_blinking = False
                self._blink_scale_x = 1.0
                self._blink_scale_y = 1.0
                if is_sad:
                    interval = random.uniform(4.5, 7.5)
                elif self.visor_state == VisorState.DROWSY:
                    interval = random.uniform(1.8, 3.2)
                else:
                    interval = random.uniform(3.5, 6.0)
                self._next_blink_time = now + interval
        else:
            self._blink_scale_x = 1.0
            self._blink_scale_y = 1.0

        # Somnoliento o triste: párpados naturalmente más pesados
        if self.visor_state == VisorState.DROWSY and not self._is_blinking:
            self._blink_scale_y = min(self._blink_scale_y, 0.65)
        elif is_sad and not self._is_blinking:
            self._blink_scale_y = min(self._blink_scale_y, 0.78)

    # ================= 3. MICRO-MOVIMIENTOS BIOLÓGICOS =================

    def _update_biological_saccades(self, now: float, scale: float):
        """
        Micro-movimientos sacádicos involuntarios:
        - Modo Normal: Cada 3 a 5 segundos de inactividad, micro-salto rápido y orgánico de 2 a 4px (0.28s).
        - Modo Triste: Movimientos más lentos (0.50s), sutiles (1 a 2px) y con ojos caídos.
        """
        if self.visor_state == VisorState.SLEEPING or self.active_action:
            self._saccade_x = 0.0
            self._saccade_y = 0.0
            return

        is_sad = (self.emotion in ["sad", "melancholy"] or self.persistent_mood == "sad")

        if now >= self._next_saccade_time:
            ang = random.uniform(0.0, 2.0 * math.pi)
            if is_sad:
                dist = random.uniform(1.0, 2.0) * scale  # Menor amplitud (1-2px)
                self._saccade_target_x = math.cos(ang) * dist
                self._saccade_target_y = abs(math.sin(ang)) * dist + (1.5 * scale)  # Sesgo hacia abajo
                self._saccade_start_time = now
                self._saccade_duration = random.uniform(0.45, 0.60)  # Más lenta (~0.5s)
                self._next_saccade_time = now + random.uniform(5.0, 8.0)
            else:
                dist = random.uniform(2.0, 4.0) * scale
                self._saccade_target_x = math.cos(ang) * dist
                self._saccade_target_y = math.sin(ang) * dist
                self._saccade_start_time = now
                self._saccade_duration = random.uniform(0.24, 0.32)
                self._next_saccade_time = now + random.uniform(3.0, 5.0)

        # Animar la sacada actual si está activa
        if self._saccade_start_time > 0:
            elapsed = now - self._saccade_start_time
            if elapsed < self._saccade_duration:
                p = elapsed / self._saccade_duration
                if p < 0.25:
                    sub_p = p / 0.25
                    self._saccade_x = self._saccade_target_x * sub_p
                    self._saccade_y = self._saccade_target_y * sub_p
                else:
                    sub_p = (p - 0.25) / 0.75
                    ease = 1.0 - sub_p
                    self._saccade_x = self._saccade_target_x * ease
                    self._saccade_y = self._saccade_target_y * ease
            else:
                self._saccade_x = 0.0
                self._saccade_y = 0.0
                self._saccade_start_time = 0.0

    def _update_gaze_tracking(self, scale: float):
        """Interpola suavemente la mirada hacia el objetivo o ratón."""
        if self.visor_state == VisorState.SLEEPING or self.active_action:
            self._gaze_x += (0.0 - self._gaze_x) * 0.12
            self._gaze_y += (0.0 - self._gaze_y) * 0.12
            return

        tx = self._target_gaze_x * scale
        ty = self._target_gaze_y * scale

        # En modo triste, la mirada cae ligeramente hacia abajo si no está siguiendo el ratón
        is_sad = (self.emotion in ["sad", "melancholy"] or self.persistent_mood == "sad")
        if is_sad and not self._mouse_nearby:
            ty += 3.2 * scale

        self._gaze_x += (tx - self._gaze_x) * 0.16
        self._gaze_y += (ty - self._gaze_y) * 0.16

    # ================= MÁQUINA DE INACTIVIDAD Y COMPORTAMIENTOS =================

    def _update_inactivity_timeline(self, now: float):
        """Actualiza la línea de tiempo de inactividad progresiva."""
        if self.persistent_mood:
            self.visor_state = VisorState.AWAKE
            return
        if self.active_action:
            self.visor_state = VisorState.ANIMATING_ACTION
            return
        if self._deep_sleep_forced:
            self.visor_state = VisorState.SLEEPING
            return
        if self.is_speaking or self.state in ["listening", "thinking"]:
            self.visor_state = VisorState.AWAKE
            self._last_activity_time = now
            return

        idle_seconds = now - self._last_activity_time
        if idle_seconds < 60.0:
            self.visor_state = VisorState.AWAKE
        elif idle_seconds < 180.0:
            self.visor_state = VisorState.PLAYFUL_IDLE
        elif idle_seconds < 300.0:
            self.visor_state = VisorState.DROWSY
        else:
            self.visor_state = VisorState.SLEEPING

    def _update_idle_quirks(self, now: float):
        """Micro-gestos espontáneos durante la inactividad para que se sienta vivo."""
        if self.persistent_mood or self.active_action or self._emotion_until > now:
            return

        if self._current_quirk:
            if now >= self._quirk_start_time + self._quirk_duration:
                self._current_quirk = None
                self._next_quirk_time = now + random.uniform(4.5, 7.5)
            return

        if now >= self._next_quirk_time:
            if self.visor_state == VisorState.AWAKE:
                pool = [("curious", 2.2), ("wink", 1.8), ("idle", 2.0)]
            elif self.visor_state == VisorState.PLAYFUL_IDLE:
                pool = [("curious", 2.4), ("cool", 2.5), ("wink", 2.0), ("happy", 2.2)]
            elif self.visor_state == VisorState.DROWSY:
                pool = [("drowsy", 3.0)]
            else:
                pool = []

            if pool:
                chosen, dur = random.choice(pool)
                self._current_quirk = chosen
                self._quirk_start_time = now
                self._quirk_duration = dur
                self.set_emotion(chosen, duration=dur)

    # ================= BUCLE PRINCIPAL DE DIBUJO =================

    def _animate(self):
        """Bucle continuo de renderizado procedural a ~35 FPS."""
        try:
            if not self.winfo_exists():
                return
            if self.winfo_ismapped():
                self._draw_frame()
                delay = 28  # ~35 FPS
            else:
                delay = 180
        except Exception:
            delay = 100

        try:
            if self.winfo_exists():
                self.after(delay, self._animate)
        except Exception:
            pass

    def _draw_frame(self):
        """Renderiza un fotograma completo en el lienzo adaptando la escala dinámicamente."""
        self.delete("all")
        now = time.time()
        dt = max(0.01, min(0.05, now - getattr(self, "_last_frame_time", now - 0.028)))
        self._last_frame_time = now
        t = now - self._start_time

        # 1. Actualizar máquinas de estado y cronómetros
        self._update_inactivity_timeline(now)
        self._update_idle_quirks(now)

        if self.active_icon and now >= self._icon_until:
            self.active_icon = None

        if self._emotion_until > 0 and now >= self._emotion_until:
            if self.persistent_mood:
                self.emotion = self.persistent_mood
                self._target_emotion = self.persistent_mood
            else:
                self.emotion = "idle"
                self._target_emotion = "idle"
            self._emotion_until = 0.0

        # Curvatura objetivo de la boca según la emoción activa
        _active_emo = self.persistent_mood or self.emotion
        if _active_emo in ["happy", "love", "heart"]:
            self._target_mouth_curvature = 1.0
        elif _active_emo in ["sad", "melancholy"]:
            self._target_mouth_curvature = -1.0
        elif _active_emo == "angry":
            self._target_mouth_curvature = -0.5
        elif _active_emo in ["surprise", "shock", "alert"]:
            self._target_mouth_curvature = 0.0
        elif _active_emo in ["curious", "cool", "cool_shades"]:
            self._target_mouth_curvature = 0.1
        else:
            self._target_mouth_curvature = 0.22

        # Transición continua y orgánica de la boca (Lerp)
        dt_lerp = min(1.0, dt * 10.0)
        self._curr_mouth_curvature += (self._target_mouth_curvature - self._curr_mouth_curvature) * dt_lerp

        if self.active_action:
            if now - self._action_start_time >= self._action_duration:
                self.active_action = None
                self.visor_state = VisorState.AWAKE
                self._last_activity_time = now
                # Retornar al mood persistente en lugar de dormirse
                if self.persistent_mood:
                    self.emotion = self.persistent_mood
                    self._target_emotion = self.persistent_mood
                else:
                    self.emotion = "idle"
                    self._target_emotion = "idle"

        # 2. Dimensiones y escala adaptativa
        w, h = float(self.width), float(self.height)
        cx, cy = w / 2.0, h / 2.0

        # Escala armónica adaptativa calibrada para visor Hero de 520x200
        scale = min(w / 516.0, h / 196.0)
        scale = max(0.42, min(scale, 1.40))

        visor_w = max(w - 6.0, 80.0)
        visor_h = max(h - 6.0, 44.0)
        r_outer = min(30.0 * scale, visor_h / 2.0)
        r_inner = max(8.0, r_outer - 4.0)
        compact = (w < 260)

        # 3. Respiración digital: ciclo senoidal de 3.0s a ±2%
        breath_cycle = math.sin((2.0 * math.pi * t) / 3.0)
        breath_scale = 1.0 + 0.02 * breath_cycle
        breath_bob_y = breath_cycle * (1.8 * scale)

        # 4. Modulación de habla (Speaking bounce)
        speech_scale_x = 1.0
        speech_scale_y = 1.0
        speech_bob_y = 0.0
        if self._speaking_bounce or self.is_speaking:
            speech_scale_y = 1.0 + 0.06 * math.sin(t * 14.0) + 0.04 * math.cos(t * 9.5)
            speech_scale_x = 1.0 - 0.03 * math.sin(t * 14.0)
            speech_bob_y = -3.0 * abs(math.sin(t * 11.0)) * scale

        # 5. Físicas elásticas y micro-movimientos
        self._update_shape_morphing(dt)
        self._update_blink_spring_physics(now)
        self._update_biological_saccades(now, scale)
        self._update_gaze_tracking(scale)

        # ---------------- HALO DE LUZ AMBIENTAL REACTIVO (LERP COLOR) ----------------
        if self.ambient_glow_until > 0 and now >= self.ambient_glow_until:
            self.ambient_glow_state = "idle"
            self.ambient_glow_until = 0.0

        target_state = self.ambient_glow_state
        if self.state == "thinking" or self.emotion == "thinking":
            target_state = "thinking"
        elif target_state == "idle" and (self.state == "listening" or self.emotion == "listening"):
            target_state = "listening"

        palette_map = {
            "idle": [0.0, 217.0, 255.0],      # Cian Neón (#00d9ff)
            "listening": [0.0, 217.0, 255.0], # Cian Neón
            "music": [168.0, 85.0, 247.0],    # Morado Cósmico (#a855f7)
            "success": [16.0, 185.0, 129.0],  # Verde Esmeralda (#10b981)
            "task": [16.0, 185.0, 129.0],     # Verde Esmeralda
            "thinking": [245.0, 158.0, 11.0]  # Ámbar / Naranja (#f59e0b)
        }
        target_rgb = palette_map.get(target_state, [0.0, 217.0, 255.0])

        glow_lerp = min(1.0, dt * 7.5)
        for c in range(3):
            self._curr_glow_rgb[c] += (target_rgb[c] - self._curr_glow_rgb[c]) * glow_lerp

        gr, gg, gb = self._curr_glow_rgb
        glow_bright = f"#{int(gr):02x}{int(gg):02x}{int(gb):02x}"
        glow_mid = f"#{int(gr * 0.65):02x}{int(gg * 0.65):02x}{int(gb * 0.65):02x}"
        glow_outer = f"#{int(gr * 0.22):02x}{int(gg * 0.22):02x}{int(gb * 0.22):02x}"

        # ---------------- PARALLAX DINÁMICO 2.5D (PROFUNDIDAD 3D) ----------------
        bg_px = -self._gaze_x * 0.40 * scale
        bg_py = -self._gaze_y * 0.40 * scale
        face_px = self._gaze_x * 0.70 * scale
        face_py = self._gaze_y * 0.70 * scale
        glass_px = -self._gaze_x * 1.15 * scale
        glass_py = -self._gaze_y * 1.15 * scale

        # 6. Renderizar Casco, Bisel, Pantalla OLED y Halo Ambiental Reactivo
        self._draw_helmet_and_screen(
            cx, cy, visor_w, visor_h, r_outer, r_inner, t, compact,
            glow_bright, glow_mid, glow_outer, bg_px, bg_py, scale
        )

        # Resplandor de activación instantánea al despertar
        if now < self._wake_flash_until:
            rem = self._wake_flash_until - now
            flash_intensity = min(1.0, rem / 0.65)
            pulse_pad = (1.0 - flash_intensity) * 12.0 * scale
            self._draw_rounded_capsule(
                cx - (visor_w / 2.0) - 3.0 - pulse_pad,
                cy - (visor_h / 2.0) - 3.0 - pulse_pad,
                cx + (visor_w / 2.0) + 3.0 + pulse_pad,
                cy + (visor_h / 2.0) + 3.0 + pulse_pad,
                r_outer + 3.0,
                fill="", outline=glow_bright,
                width=max(2.0, 3.5 * flash_intensity)
            )

        # 7. Renderizado de Contenido Facial / Icono / Acción Narrativa con Parallax
        total_bob_y = breath_bob_y + speech_bob_y + face_py
        total_cx = cx + face_px

        if self.active_action == "eating_icecream":
            self._draw_eating_icecream_action(total_cx, cy + total_bob_y, visor_w, visor_h, scale, now)
        elif self.active_action == "startle_wake":
            self._draw_startle_wake_action(total_cx, cy + total_bob_y, scale, now)
        elif self.active_icon:
            self._draw_contextual_icon(total_cx, cy + total_bob_y, visor_w, visor_h, scale, t, self.active_icon)
        else:
            self._draw_procedural_face(
                total_cx, cy + total_bob_y, scale, t,
                breath_scale, speech_scale_x, speech_scale_y
            )

        # Reflejo de cristal pulido sobre la pantalla OLED con Parallax Inverso
        self._draw_glass_reflection(cx, cy, visor_w, visor_h, scale, glass_px, glass_py)

    # ================= 4. RENDERIZADO DEL CASCO Y PANTALLA OLED =================

    def _draw_rounded_capsule(self, x1, y1, x2, y2, r, **kwargs):
        """Dibuja un rectángulo con esquinas redondeadas suaves."""
        r = max(2.0, min(r, (x2 - x1) / 2.0, (y2 - y1) / 2.0))
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2 - r,
            x2, y2,
            x2 - r, y2,
            x1 + r, y2,
            x1, y2,
            x1, y2 - r,
            x1, y1 + r,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw_helmet_and_screen(
        self, cx: float, cy: float, vw: float, vh: float, r_outer: float, r_inner: float,
        t: float, compact: bool, glow_bright: str, glow_mid: str, glow_outer: str,
        bg_px: float, bg_py: float, scale: float
    ):
        """Renderiza la carcasa exterior, la pantalla negra pura OLED y el Halo Ambiental Reactivo."""
        vx1 = cx - vw / 2.0
        vy1 = cy - vh / 2.0
        vx2 = cx + vw / 2.0
        vy2 = cy + vh / 2.0

        # Halo Ambiental Reactivo Multicapa (Ambient Glow)
        self._draw_rounded_capsule(
            vx1 - 6 * scale, vy1 - 6 * scale, vx2 + 6 * scale, vy2 + 6 * scale,
            r_outer + 6 * scale, fill="", outline=glow_outer, width=max(2.5, 4.5 * scale)
        )
        self._draw_rounded_capsule(
            vx1 - 3 * scale, vy1 - 3 * scale, vx2 + 3 * scale, vy2 + 3 * scale,
            r_outer + 3 * scale, fill="", outline=glow_mid, width=max(1.8, 2.5 * scale)
        )

        # Capa 0: Carcasa exterior metálica oscura con bisel
        self._draw_rounded_capsule(
            vx1 - 2, vy1 - 2, vx2 + 2, vy2 + 2,
            r_outer, fill=self.c_helmet_shell, outline=self.c_helmet_bevel, width=1.5
        )

        # Capa 1: Pantalla OLED Negro Puro (#000000)
        self._draw_rounded_capsule(
            vx1, vy1, vx2, vy2,
            r_inner, fill=self.c_oled_black, outline=""
        )

        # Borde interior activo con color del Halo Ambiental
        self._draw_rounded_capsule(
            vx1 + 1, vy1 + 1, vx2 - 1, vy2 - 1,
            r_inner - 1, fill="", outline=glow_bright, width=1.3
        )

        # Partículas tenues de polvo digital con Parallax Dinámico 2.5D
        if not compact and self.visor_state != VisorState.SLEEPING:
            for p in self.particles:
                p[1] -= p[2]
                if p[1] < vy1 + 6:
                    p[1] = vy2 - 6
                    p[0] = random.uniform(vx1 + 10, vx2 - 10)
                px = p[0] + bg_px
                py = p[1] + bg_py
                if vx1 + 8 < px < vx2 - 8 and vy1 + 8 < py < vy2 - 8:
                    self.create_oval(
                        px - p[3], py - p[3],
                        px + p[3], py + p[3],
                        fill=p[4], outline=""
                    )

    def _draw_audio_waveform(self, *args, **kwargs):
        """Eliminado: La boca se dibuja como un arco vectorial limpio sin ondas ni barras."""
        pass

    def _draw_glass_reflection(self, cx: float, cy: float, vw: float, vh: float, scale: float, glass_px: float = 0.0, glass_py: float = 0.0):
        """Reflejo diagonal curvo de cristal pulido para acabado de pantalla táctica con Parallax."""
        vx1 = cx - vw / 2.0 + glass_px
        vy1 = cy - vh / 2.0 + glass_py

        ref_x1 = vx1 + 12.0 * scale
        ref_y1 = vy1 + 6.0 * scale
        ref_x2 = vx1 + vw * 0.42
        ref_y2 = vy1 + 22.0 * scale

        points = [
            ref_x1 + 16 * scale, ref_y1,
            ref_x2, ref_y1,
            ref_x2 - 18 * scale, ref_y2,
            ref_x1, ref_y2
        ]
        self.create_polygon(points, fill="#0a1826", outline="", smooth=True)

    # ================= 5. RENDERIZADO PROCEDURAL DE LA CARA Y OJOS OLED =================

    def _draw_procedural_face(
        self, cx: float, cy: float, scale: float, t: float,
        breath_scale: float, speech_scale_x: float, speech_scale_y: float
    ):
        """
        Renderiza la pareja de ojos robóticos expresivos y la boca reactiva.
        Dimensiones Hero: ~85px ancho x 90px alto cada ojo, separados por 50px (135px entre centros).
        """
        # Dimensiones de Ojos Escala Hero: 85px ancho x 90px alto, separados por 50px
        base_eye_w = 85.0 * scale
        base_eye_h = 90.0 * scale
        eye_spacing = 67.5 * scale      # Centro a cx ± 67.5px (distancia entre centros = 135px, gap = 50px)
        base_eye_y = cy - 8.0 * scale
        mouth_y = cy + 46.0 * scale

        # Posiciones centrales de cada ojo con mirada y sacadas
        total_offset_x = self._gaze_x + self._saccade_x
        total_offset_y = self._gaze_y + self._saccade_y

        lx = cx - eye_spacing + total_offset_x
        rx = cx + eye_spacing + total_offset_x
        ey = base_eye_y + total_offset_y

        # Factores de escala combinados (Física de Resorte + Respiración + Habla)
        sx = self._blink_scale_x * breath_scale * speech_scale_x
        sy = self._blink_scale_y * breath_scale * speech_scale_y

        final_w = base_eye_w * sx
        final_h = base_eye_h * sy

        # Si está durmiendo, mostrar ojos cerrados con Zs flotantes
        if self.visor_state == VisorState.SLEEPING:
            self._draw_sleeping_slit(lx, ey, base_eye_w, scale)
            self._draw_sleeping_slit(rx, ey, base_eye_w, scale)
            self._draw_floating_zs(rx + 24 * scale, base_eye_y - 10 * scale, scale, t)
            self._draw_straight_mouth(cx, mouth_y, scale)
            return

        # Paleta de color según estado o emoción
        eye_body_color = self.c_cyan_bright
        eye_core_color = self.c_cyan_core
        eye_glow_color = self.c_glow_outer
        eye_bloom_color = self.c_glow_mid

        active_emo = self.persistent_mood or self.emotion

        if self.state == "thinking" or active_emo == "thinking":
            eye_body_color = self.c_amber
            eye_core_color = "#fffbeb"
            eye_glow_color = "#451a03"
            eye_bloom_color = self.c_amber_glow
        elif active_emo in ["love", "heart"]:
            eye_body_color = "#f43f5e"
            eye_core_color = "#ffe4e6"
            eye_glow_color = "#4c0519"
            eye_bloom_color = "#fb7185"
        elif active_emo == "angry":
            # Rojo neón agresivo (#ff3366)
            eye_body_color = "#ff3366"
            eye_core_color = "#ffccd5"
            eye_glow_color = "#3d0010"
            eye_bloom_color = "#cc0033"

        # Renderizar Ojo Izquierdo y Ojo Derecho con multicapa OLED
        self._render_single_eye_oled(
            lx, ey, final_w, final_h, self._curr_vertices_left, scale,
            eye_body_color, eye_core_color, eye_glow_color, eye_bloom_color, is_left=True
        )
        self._render_single_eye_oled(
            rx, ey, final_w, final_h, self._curr_vertices_right, scale,
            eye_body_color, eye_core_color, eye_glow_color, eye_bloom_color, is_left=False
        )

        # Accesorios faciales
        if active_emo in ["cool", "cool_shades"]:
            self._draw_cool_sunglasses_glint(lx, rx, ey, final_w, final_h, scale, t)
        elif active_emo in ["happy", "love", "heart", "wink"]:
            self._draw_cheeks(lx, rx, ey + 22.0 * scale, scale, t)

        # Boca con arco vectorial limpio y minimalista (‿ o ⁀)
        self._draw_clean_arc_mouth(cx, mouth_y, scale, t)

    def _render_single_eye_oled(
        self, ex: float, ey: float, ew: float, eh: float,
        vertices: List[List[float]], scale: float,
        body_col: str, core_col: str, glow_col: str, bloom_col: str, is_left: bool
    ):
        """
        Dibuja un ojo squircle procedural con sombreado multicapa OLED:
        1. Capa 0: Halo difuminado exterior (Ambient Backlight Glow a 1.10x)
        2. Capa 1: Bloom intermedio (1.04x)
        3. Capa 2: Masa del ojo cian neón de alta luminosidad (1.00x)
        4. Capa 3: Núcleo blanco cian volumétrico (0.62x)
        5. Capa 4: Pupila brillante / destello especular de cristal
        """
        hw = ew / 2.0
        hh = eh / 2.0

        if hh < 1.0 or hw < 1.0:
            return

        # ---------------- 1. HALO DIFUMINADO EXTERIOR (BACKLIGHT GLOW) ----------------
        glow_pts = []
        glow_scale = 1.10
        for vx, vy in vertices:
            gx = ex + vx * hw * glow_scale
            gy = ey + vy * hh * glow_scale
            glow_pts.extend([gx, gy])

        if len(glow_pts) >= 6:
            self.create_polygon(glow_pts, smooth=True, fill=glow_col, outline="")

        # ---------------- 2. BLOOM INTERMEDIO ----------------
        bloom_pts = []
        bloom_scale = 1.04
        for vx, vy in vertices:
            bx = ex + vx * hw * bloom_scale
            by = ey + vy * hh * bloom_scale
            bloom_pts.extend([bx, by])

        if len(bloom_pts) >= 6:
            self.create_polygon(bloom_pts, smooth=True, fill=bloom_col, outline="")

        # ---------------- 3. CUERPO CIAN NEÓN PRINCIPAL (#00d9ff) ----------------
        main_pts = []
        for vx, vy in vertices:
            mx = ex + vx * hw
            my = ey + vy * hh
            main_pts.extend([mx, my])

        if len(main_pts) >= 6:
            self.create_polygon(main_pts, smooth=True, fill=body_col, outline="#e0f7ff", width=max(1.0, 1.2 * scale))

        # ---------------- 4. NÚCLEO INTERIOR BLANCO CIAN (#bbf2ff) ----------------
        # Se dibuja si el ojo está abierto con altura suficiente (> 12px)
        if hh > 8.0 * scale:
            core_pts = []
            core_scale = 0.60
            # Desplazamiento sutil hacia la mirada para volumen tridimensional
            gaze_shift_x = (self._gaze_x / 14.0) * hw * 0.12
            gaze_shift_y = (self._gaze_y / 10.0) * hh * 0.12
            core_cx = ex + gaze_shift_x
            core_cy = ey + gaze_shift_y

            for vx, vy in vertices:
                cx_pt = core_cx + vx * hw * core_scale
                cy_pt = core_cy + vy * hh * core_scale
                core_pts.extend([cx_pt, cy_pt])

            if len(core_pts) >= 6:
                self.create_polygon(core_pts, smooth=True, fill=core_col, outline="")

            # ---------------- 5. REFLEJO ESPECULAR DE CRISTAL (GLINT) ----------------
            # Destello circular vivo en esquina superior para ojos orgánicos OLED
            if self.emotion not in ["cool", "cool_shades", "sleeping"]:
                glint_r = 5.5 * scale
                glint_x = ex - hw * 0.33 if is_left else ex + hw * 0.33
                glint_y = ey - hh * 0.38
                # Halo exterior del reflejo
                self.create_oval(
                    glint_x - glint_r * 1.6, glint_y - glint_r * 1.6,
                    glint_x + glint_r * 1.6, glint_y + glint_r * 1.6,
                    fill="#c8f0ff", outline=""
                )
                # Núcleo blanco brillante
                self.create_oval(
                    glint_x - glint_r, glint_y - glint_r,
                    glint_x + glint_r, glint_y + glint_r,
                    fill=self.c_white, outline=""
                )
                # Segundo destello pequeño (reflejo secundario de pantalla)
                glint2_x = glint_x + glint_r * 1.4
                glint2_y = glint_y + glint_r * 1.2
                glint2_r = glint_r * 0.45
                self.create_oval(
                    glint2_x - glint2_r, glint2_y - glint2_r,
                    glint2_x + glint2_r, glint2_y + glint2_r,
                    fill="#e8f8ff", outline=""
                )

    def _draw_cool_sunglasses_glint(
        self, lx: float, rx: float, ey: float, ew: float, eh: float, scale: float, t: float
    ):
        """Dibuja el destello diagonal reflectante que recorre las gafas cyberpunk."""
        glint_phase = (t * 2.2) % 2.5
        if glint_phase < 0.65:
            p = glint_phase / 0.65
            # Línea de destello que cruza ambos ojos
            span = (rx - lx) + ew * 1.4
            bar_x = (lx - ew * 0.7) + p * span
            self.create_line(
                bar_x - 12 * scale, ey - eh * 0.3,
                bar_x + 12 * scale, ey + eh * 0.3,
                fill=self.c_white, width=max(2.0, 3.0 * scale)
            )

    def _draw_sleeping_slit(self, ex: float, ey: float, ew: float, scale: float):
        """Ojo cerrado pacífico en reposo profundo con brillo neón."""
        hw = ew * 0.45
        self.create_line(
            ex - hw, ey, ex + hw, ey,
            fill=self.c_glow_outer, width=max(5.0, 8.0 * scale), capstyle="round"
        )
        self.create_line(
            ex - hw, ey, ex + hw, ey,
            fill=self.c_cyan_bright, width=max(2.5, 4.0 * scale), capstyle="round"
        )

    def _draw_floating_zs(self, start_x: float, start_y: float, scale: float, t: float):
        """Letras Z z z flotantes nítidas de reposo."""
        zs = ["z", "Z", "z"]
        for i, ch in enumerate(zs):
            phase = (t * 0.80 + i * 0.60) % 2.0
            fy = start_y - (phase * 22.0 * scale)
            fx = start_x + math.sin(phase * 3.0) * 7.0 * scale
            col = self.c_cyan_bright if phase < 1.3 else self.c_cyan_dim
            sz = int(max(10, (11 + i * 4) * scale))
            self.create_text(fx, fy, text=ch, font=("Consolas", sz, "bold"), fill=col)

    def _draw_cheeks(self, lx: float, rx: float, cy: float, scale: float, t: float):
        """Mejillas sonrosadas animadas."""
        r = 7.5 * scale
        for cx in [lx - 8 * scale, rx + 8 * scale]:
            self.create_oval(cx - r, cy - r / 2, cx + r, cy + r / 2, fill=self.c_pink_blush, outline="")

    # ================= 6. RENDERIZADO DE LA BOCA REACTIVA (CURVAS ORGÁNICAS) =================

    def _draw_clean_arc_mouth(self, cx: float, cy: float, scale: float, t: float):
        """
        Dibuja la boca de VEX con un arco vectorial limpio y minimalista:
        - Boca Normal / Sonrisa: Arco simple y limpio curvado hacia arriba (‿) con grosor de 4px en cian neón (#00d9ff).
        - Boca en Modo Triste: Si self.mood == 'sad', el arco se curva hacia abajo (⁀) y se mantiene así hasta 'ponte feliz'.
        - Al Hablar: Modulación suave y orgánica de apertura vertical, sin deformaciones ni marcas laterales.
        """
        w = 26.0 * scale
        d = 7.0 * scale
        stroke_w = 4.0
        cyan = self.c_cyan_bright  # #00d9ff
        glow = self.c_glow_outer

        is_sad = (self.mood == "sad" or self.persistent_mood == "sad" or self.emotion in ["sad", "melancholy"])
        is_speaking = (self.is_speaking or self._speaking_bounce)

        open_h = 0.0
        if is_speaking:
            open_h = (2.0 + 5.0 * abs(math.sin(t * 12.0))) * scale

        if is_sad:
            # MODO TRISTE (⁀): Arco limpio curvado hacia abajo (centro arriba, extremos abajo)
            if is_speaking and open_h > 1.2 * scale:
                top_y = cy - d - open_h * 0.45
                bot_y = cy - d + open_h * 0.45
                pts_top = [
                    cx - w, cy + d * 0.35,
                    cx - w * 0.5, top_y + d * 0.2,
                    cx, top_y,
                    cx + w * 0.5, top_y + d * 0.2,
                    cx + w, cy + d * 0.35
                ]
                pts_bot = [
                    cx - w, cy + d * 0.35,
                    cx - w * 0.5, bot_y + d * 0.2,
                    cx, bot_y,
                    cx + w * 0.5, bot_y + d * 0.2,
                    cx + w, cy + d * 0.35
                ]
                self.create_line(pts_top, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts_bot, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts_top, smooth=True, fill=cyan, width=stroke_w, capstyle="round")
                self.create_line(pts_bot, smooth=True, fill=cyan, width=stroke_w, capstyle="round")
            else:
                pts = [
                    cx - w, cy + d * 0.35,
                    cx - w * 0.5, cy - d * 0.7,
                    cx, cy - d,
                    cx + w * 0.5, cy - d * 0.7,
                    cx + w, cy + d * 0.35
                ]
                self.create_line(pts, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts, smooth=True, fill=cyan, width=stroke_w, capstyle="round")
        else:
            # MODO NORMAL / SONRISA (‿): Arco limpio curvado hacia arriba (centro abajo, extremos arriba)
            if is_speaking and open_h > 1.2 * scale:
                top_y = cy + d - open_h * 0.45
                bot_y = cy + d + open_h * 0.45
                pts_top = [
                    cx - w, cy - d * 0.35,
                    cx - w * 0.5, top_y - d * 0.2,
                    cx, top_y,
                    cx + w * 0.5, top_y - d * 0.2,
                    cx + w, cy - d * 0.35
                ]
                pts_bot = [
                    cx - w, cy - d * 0.35,
                    cx - w * 0.5, bot_y - d * 0.2,
                    cx, bot_y,
                    cx + w * 0.5, bot_y - d * 0.2,
                    cx + w, cy - d * 0.35
                ]
                self.create_line(pts_top, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts_bot, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts_top, smooth=True, fill=cyan, width=stroke_w, capstyle="round")
                self.create_line(pts_bot, smooth=True, fill=cyan, width=stroke_w, capstyle="round")
            else:
                pts = [
                    cx - w, cy - d * 0.35,
                    cx - w * 0.5, cy + d * 0.7,
                    cx, cy + d,
                    cx + w * 0.5, cy + d * 0.7,
                    cx + w, cy - d * 0.35
                ]
                self.create_line(pts, smooth=True, fill=glow, width=stroke_w + 3.0, capstyle="round")
                self.create_line(pts, smooth=True, fill=cyan, width=stroke_w, capstyle="round")

    def _draw_curved_mouth(self, cx: float, cy: float, scale: float, t: float, curv: float = 0.2):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_speaking_mouth(self, cx: float, cy: float, scale: float, t: float, curv: float = 0.2):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_surprise_mouth(self, cx: float, cy: float, scale: float, t: float):
        if self.mood == "sad" or self.persistent_mood == "sad":
            self._draw_clean_arc_mouth(cx, cy, scale, t)
            return
        rx = 7.0 * scale
        ry = 9.0 * scale
        self.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill=self.c_oled_black, outline=self.c_cyan_bright, width=4.0)

    def _draw_speaking_or_idle_mouth(self, cx: float, cy: float, scale: float, t: float):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_happy_mouth(self, cx: float, cy: float, scale: float, t: float):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_sad_mouth(self, cx: float, cy: float, scale: float, t: float):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_smug_mouth(self, cx: float, cy: float, scale: float, t: float):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_curious_mouth(self, cx: float, cy: float, scale: float, t: float):
        self._draw_clean_arc_mouth(cx, cy, scale, t)

    def _draw_straight_mouth(self, cx: float, cy: float, scale: float):
        self._draw_clean_arc_mouth(cx, cy, scale, 0.0)

    # ================= 7. ACCIONES NARRATIVAS (SOBRESALTO Y HELADO) =================

    def _draw_startle_wake_action(self, cx: float, cy: float, scale: float, now: float):
        """Sobresalto cómico al despertarse: sacudida rápida y sonrisa alegre."""
        elapsed = now - self._action_start_time
        prog = min(1.0, elapsed / max(0.1, self._action_duration))

        shake_x = 0.0
        if prog < 0.45:
            shake_amp = (1.0 - (prog / 0.45)) * 10.0 * scale
            shake_x = math.sin(elapsed * 32.0) * shake_amp

        eye_spacing = 55.0 * scale
        lx = cx - eye_spacing + shake_x
        rx = cx + eye_spacing + shake_x
        ey = cy - 8.0 * scale
        mouth_y = cy + 32.0 * scale

        if prog < 0.55:
            for ex in [lx, rx]:
                r = 26.0 * scale
                self.create_oval(ex - r, ey - r, ex + r, ey + r, fill="#022a3d", outline=self.c_cyan_bright, width=2.5)
                self.create_line(ex, ey - 14 * scale, ex, ey + 4 * scale, fill=self.c_white, width=max(2.5, 4.0 * scale), capstyle="round")
                self.create_oval(ex - 2.5 * scale, ey + 9 * scale, ex + 2.5 * scale, ey + 14 * scale, fill=self.c_white, outline="")
            self.create_oval(cx - 8 * scale + shake_x, mouth_y - 8 * scale, cx + 8 * scale + shake_x, mouth_y + 8 * scale, fill="#000000", outline=self.c_cyan_bright, width=2)
        else:
            self.set_emotion("happy")
            self._draw_procedural_face(cx + shake_x, cy, scale, elapsed, 1.0, 1.0, 1.0)

    def _draw_eating_icecream_action(self, cx: float, cy: float, vw: float, vh: float, scale: float, now: float):
        """Secuencia animada del helado con narrativa completa de 4 fases (7s)."""
        elapsed = now - self._action_start_time
        eye_spacing = 55.0 * scale
        lx = cx - eye_spacing
        rx = cx + eye_spacing
        ey = cy - 10.0 * scale
        mouth_y = cy + 30.0 * scale

        bob = math.sin(elapsed * 6.0) * (2.5 * scale)
        ice_x = cx
        ice_y = cy + 8.0 * scale + bob

        # FASE 1: Ilusión y aparición del helado
        if elapsed < 1.8:
            self.set_emotion("happy")
            self._draw_procedural_face(cx, cy, scale, elapsed, 1.0, 1.0, 1.0)
            self._render_icecream_prop(ice_x, ice_y, scale, bite_stage=0, elapsed=elapsed)
        # FASE 2: Los tres mordiscos y masticación
        elif elapsed < 4.8:
            eat_t = elapsed - 1.8
            if eat_t < 1.0:
                bite_stage = 1
                is_chomping = (eat_t < 0.35)
            elif eat_t < 2.0:
                bite_stage = 2
                is_chomping = (eat_t - 1.0 < 0.35)
            else:
                bite_stage = 3
                is_chomping = (eat_t - 2.0 < 0.35)

            if is_chomping:
                self.set_emotion("drowsy")
                self._draw_procedural_face(cx, cy, scale, elapsed, 1.0, 1.0, 1.0)
                self.create_oval(
                    cx - 14 * scale, mouth_y - 10 * scale,
                    cx + 14 * scale, mouth_y + 10 * scale,
                    fill="#000000", outline=self.c_cyan_bright, width=2.5
                )
            else:
                self.set_emotion("happy")
                self._draw_procedural_face(cx, cy, scale, elapsed, 1.0, 1.0, 1.0)
                chew_h = abs(math.sin(elapsed * 16.0)) * 5.0 * scale
                self.create_oval(
                    cx - 12 * scale, mouth_y - chew_h,
                    cx + 12 * scale, mouth_y + chew_h,
                    fill="#041a29", outline=self.c_cyan_bright, width=2.0
                )
            self._render_icecream_prop(ice_x, ice_y, scale, bite_stage=bite_stage, elapsed=elapsed)
        # FASE 3: Satisfacción y lamido
        elif elapsed < 6.2:
            self.set_emotion("happy")
            self._draw_procedural_face(cx, cy, scale, elapsed, 1.0, 1.0, 1.0)
            heart_p = (elapsed - 4.8) / 1.4
            hx = cx + 32.0 * scale + math.sin(heart_p * 6.0) * 6.0 * scale
            hy = cy - (heart_p * 26.0 * scale)
            self.create_text(hx, hy, text="♥", font=("Consolas", int(max(12, 16 * scale)), "bold"), fill=self.c_pink_blush)
        # FASE 4: Guiño final y retorno despierto
        else:
            self.set_emotion("wink")
            self._draw_procedural_face(cx, cy, scale, elapsed, 1.0, 1.0, 1.0)

    def _render_icecream_prop(self, base_x: float, base_y: float, scale: float, bite_stage: int, elapsed: float):
        """Renderiza el cono de barquillo y la bola de helado con migajas animadas."""
        if bite_stage > 0:
            crumb_seed = bite_stage * 19
            for i in range(5):
                angle = (i * 0.9) + crumb_seed
                dist = (8.0 + (elapsed * 25.0) % 20.0) * scale
                cx = base_x + math.cos(angle) * dist
                cy = base_y - 10 * scale + math.sin(angle) * dist
                col = random.choice([self.c_cyan_bright, "#fde047", "#f43f5e", "#d97706"])
                self.create_rectangle(cx - 1.5 * scale, cy - 1.5 * scale, cx + 1.5 * scale, cy + 1.5 * scale, fill=col, outline="")

        if bite_stage == 0:
            self.create_oval(base_x - 5 * scale, base_y - 32 * scale, base_x + 5 * scale, base_y - 22 * scale, fill="#ef4444", outline="#b91c1c")
            r_scoop = 16.0 * scale
            self.create_oval(base_x - r_scoop, base_y - 24 * scale, base_x + r_scoop, base_y + 4 * scale, fill=self.c_cyan_bright, outline=self.c_white, width=1.5)
            cone_pts = [base_x - 13 * scale, base_y + 2 * scale, base_x + 13 * scale, base_y + 2 * scale, base_x, base_y + 34 * scale]
            self.create_polygon(cone_pts, fill="#d97706", outline="#b45309", width=1.5)
        elif bite_stage == 1:
            r_scoop = 14.0 * scale
            self.create_oval(base_x - r_scoop, base_y - 18 * scale, base_x + r_scoop - 4 * scale, base_y + 4 * scale, fill=self.c_cyan_bright, outline=self.c_white, width=1.5)
            self.create_oval(base_x + 2 * scale, base_y - 22 * scale, base_x + 16 * scale, base_y - 8 * scale, fill=self.c_oled_black, outline="")
            cone_pts = [base_x - 13 * scale, base_y + 2 * scale, base_x + 13 * scale, base_y + 2 * scale, base_x, base_y + 34 * scale]
            self.create_polygon(cone_pts, fill="#d97706", outline="#b45309", width=1.5)
        elif bite_stage == 2:
            self.create_oval(base_x - 10 * scale, base_y - 8 * scale, base_x + 10 * scale, base_y + 6 * scale, fill=self.c_cyan_bright, outline=self.c_white, width=1.5)
            cone_pts = [base_x - 13 * scale, base_y + 2 * scale, base_x + 13 * scale, base_y + 2 * scale, base_x, base_y + 34 * scale]
            self.create_polygon(cone_pts, fill="#d97706", outline="#b45309", width=1.5)
        elif bite_stage == 3:
            cone_pts = [base_x - 7 * scale, base_y + 12 * scale, base_x + 7 * scale, base_y + 12 * scale, base_x, base_y + 32 * scale]
            self.create_polygon(cone_pts, fill="#d97706", outline="#b45309", width=1.5)

    # ================= 8. ICONOS CONTEXTUALES =================

    def _draw_contextual_icon(self, cx: float, cy: float, vw: float, vh: float, scale: float, t: float, icon_name: str):
        """Proyecta un icono temático en el centro de la pantalla."""
        if icon_name == "music":
            self._draw_pixel_music(cx, cy, scale, t)
        elif icon_name == "search":
            self._draw_pixel_search(cx, cy, scale, t)
        elif icon_name == "clock":
            self._draw_tactical_clock(cx, cy, scale, t)
        elif icon_name == "battery":
            self._draw_pixel_battery(cx, cy, scale, t)
        elif icon_name == "calc":
            self._draw_pixel_calc(cx, cy, scale, t)
        elif icon_name in ["notes", "notepad", "edit"]:
            self._draw_pixel_notes(cx, cy, scale, t)
        else:
            self._draw_pixel_music(cx, cy, scale, t)

    def _draw_pixel_music(self, cx: float, cy: float, scale: float, t: float):
        """Notas musicales flotantes con ecualizador animado."""
        for dx, base_dy, phase, phase_offset in [(-22.0, 0.0, t * 1.1, 0.0), (3.0, -8.0, t * 1.45, 1.8), (24.0, 4.0, t * 0.85, 3.5)]:
            float_y = math.sin(phase + phase_offset) * 7.0 * scale
            nx = cx + dx * scale
            ny = cy + base_dy * scale + float_y - 8.0 * scale
            hrx, hry = 6.0 * scale, 4.5 * scale
            self.create_oval(nx - hrx, ny + 10 * scale, nx + hrx, ny + 10 * scale + hry * 2, fill=self.c_cyan_bright, outline="")
            self.create_line(nx + hrx - 1, ny + 12 * scale, nx + hrx - 1, ny - 4 * scale, fill=self.c_cyan_bright, width=max(1.5, 2.0 * scale))
            self.create_line(nx + hrx - 1, ny - 4 * scale, nx + hrx + 6 * scale, ny + 2 * scale, fill=self.c_cyan_bright, width=max(1.5, 2.0 * scale))

        eq_y = cy + 28.0 * scale
        bar_w = 5.5 * scale
        bar_gap = 4.5 * scale
        total_w = 5 * (bar_w + bar_gap) - bar_gap
        start_x = cx - total_w / 2.0
        for i in range(5):
            bx = start_x + i * (bar_w + bar_gap)
            val = math.sin(t * (8.0 + i * 2.5) + i * 1.2) * 0.5 + 0.5
            bh = (3.0 + val * 13.0) * scale
            self.create_rectangle(bx, eq_y - bh, bx + bar_w, eq_y, fill=self.c_cyan_bright, outline="")

    def _draw_pixel_search(self, cx: float, cy: float, scale: float, t: float):
        r = 18.0 * scale
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#041b2a", outline=self.c_cyan_bright, width=max(2.0, 2.5 * scale))
        self.create_line(cx + r * 0.7, cy + r * 0.7, cx + r + 12 * scale, cy + r + 12 * scale, fill=self.c_cyan_bright, width=max(3.0, 4.0 * scale), capstyle="round")

    def _draw_tactical_clock(self, cx: float, cy: float, scale: float, t: float):
        time_str = datetime.datetime.now().strftime("%H:%M")
        box_w = 110.0 * scale
        box_h = 42.0 * scale
        self._draw_rounded_capsule(cx - box_w / 2.0, cy - box_h / 2.0, cx + box_w / 2.0, cy + box_h / 2.0, 8 * scale, fill="#041220", outline=self.c_cyan_bright, width=1.5)
        self.create_text(cx, cy, text=time_str, font=("Consolas", int(max(10, 14 * scale)), "bold"), fill=self.c_cyan_core)

    def _draw_pixel_battery(self, cx: float, cy: float, scale: float, t: float):
        bw = 58.0 * scale
        bh = 26.0 * scale
        bx1, by1 = cx - bw / 2.0, cy - bh / 2.0
        bx2, by2 = cx + bw / 2.0, cy + bh / 2.0
        self._draw_rounded_capsule(bx1, by1, bx2, by2, 6 * scale, fill="#05101a", outline=self.c_cyan_bright, width=1.5)
        self.create_rectangle(bx2, cy - 5 * scale, bx2 + 4 * scale, cy + 5 * scale, fill=self.c_cyan_bright, outline="")
        for i in range(3):
            bar_x = bx1 + (6 + i * 16) * scale
            self.create_rectangle(bar_x, by1 + 4 * scale, bar_x + 12 * scale, by2 - 4 * scale, fill=self.c_green_glow, outline="")

    def _draw_pixel_calc(self, cx: float, cy: float, scale: float, t: float):
        bw = 50.0 * scale
        bh = 42.0 * scale
        self._draw_rounded_capsule(cx - bw / 2.0, cy - bh / 2.0, cx + bw / 2.0, cy + bh / 2.0, 6 * scale, fill="#081829", outline=self.c_cyan_bright, width=1.5)
        self.create_rectangle(cx - 20 * scale, cy - 14 * scale, cx + 20 * scale, cy - 4 * scale, fill="#042033", outline=self.c_cyan_glow)
        self.create_text(cx, cy + 8 * scale, text="+ - =", font=("Consolas", int(max(7, 9 * scale)), "bold"), fill=self.c_cyan_core)

    def _draw_pixel_notes(self, cx: float, cy: float, scale: float, t: float):
        bob = math.sin(t * 4.0) * (2.0 * scale)
        base_y = cy + bob - 2.0 * scale
        bw = 42.0 * scale
        bh = 50.0 * scale
        bx1, by1 = cx - bw / 2.0, base_y - bh / 2.0
        bx2, by2 = cx + bw / 2.0, base_y + bh / 2.0
        self._draw_rounded_capsule(bx1, by1, bx2, by2, 5 * scale, fill="#071526", outline=self.c_cyan_bright, width=1.5)
        self.create_rectangle(bx1 + 2, by1 + 2, bx2 - 2, by1 + 8 * scale, fill=self.c_cyan_glow, outline="")
        for i in range(3):
            ly = by1 + (16 + i * 8) * scale
            lw = (28 - i * 4) * scale
            self.create_line(bx1 + 7 * scale, ly, bx1 + 7 * scale + lw, ly, fill=self.c_cyan_core, width=max(1.5, 2.0 * scale), capstyle="round")


# Alias de compatibilidad total para código existente
RobotVisorCanvas = RobotVisor
