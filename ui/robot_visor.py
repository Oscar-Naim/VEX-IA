"""
LYAXIS labs™ - Robot Visor Digital Expresivo (VEX Cyber-Pet HUD)
Pantalla visor de robot digital estilo EMO / Vector / Cyber-Pet.
Casco con acabado pulido, pantalla OLED (#000000) con reflejo de cristal,
ojos y boca de matriz de neón azul cian (#00d9ff), expresiones dinámicas
y proyecciones contextuales de iconos pixelados en pantalla.
Soporta renderizado escalable adaptativo para header táctico o pantalla completa.
"""
import math
import random
import time
import datetime
import tkinter as tk
from typing import Optional, List, Tuple, Dict


class RobotVisorCanvas(tk.Canvas):
    def __init__(self, master, width: int = 740, height: int = 240, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            bg="#07070a",
            highlightthickness=0,
            bd=0,
            **kwargs
        )
        self.width = width
        self.height = height

        # Estado del sistema: "idle", "listening", "thinking", "speaking"
        self.state = "idle"
        self.is_speaking = False

        # Expresión visual actual:
        # "idle", "cool_shades", "happy", "thinking", "surprise", "listening", "wink", "sleeping"
        self.expression = "idle"
        self._expression_until: float = 0.0

        # Proyección de iconos en pantalla:
        # None, "ice_cream", "music", "search", "clock", "battery", "calc"
        self.active_icon: Optional[str] = None
        self._icon_until: float = 0.0
        self._wake_flash_until: float = 0.0

        # Tiempos de animación
        self._start_time = time.time()
        self._blink_start_time = 0.0
        self._is_blinking = False
        self._next_blink_time = time.time() + 3.8

        # Sacadas y mirada (micro-movimientos)
        self._gaze_x = 0.0
        self._gaze_y = 0.0
        self._next_gaze_time = time.time() + 2.0

        # Paleta Cyber-Neón EMO / Vector
        self.c_bg_canvas = "#07070a"
        self.c_oled_black = "#000000"

        # Carcasa y marco del casco
        self.c_bezel_outer = "#1a2130"
        self.c_bezel_mid = "#0f1523"
        self.c_bezel_rim = "#253450"
        self.c_glass_sheen = "#ffffff"

        # Neón Matrix
        self.c_cyan_bright = "#00d9ff"
        self.c_cyan_glow = "#38bdf8"
        self.c_cyan_dim = "#034b6e"
        self.c_cyan_core = "#e0f7ff"
        self.c_white = "#ffffff"
        self.c_amber = "#f59e0b"
        self.c_amber_glow = "#fbbf24"
        self.c_pink_blush = "#f43f5e"
        self.c_green = "#10b981"
        self.c_green_glow = "#34d399"

        # Partículas de polvo de cristal
        self.particles = []
        for _ in range(16):
            self.particles.append([
                random.uniform(10, max(20, width - 10)),
                random.uniform(10, max(20, height - 10)),
                random.uniform(0.2, 0.6),
                random.uniform(0.8, 1.8),
                random.choice(["#0e2a42", "#073b54", "#122036"])
            ])

        # Adaptación responsiva al cambiar tamaño de ventana
        self.bind("<Configure>", self._on_resize)

        # Bucle de animación continuo (~33 FPS)
        self._animate()

    def _on_resize(self, event):
        """Ajusta las dimensiones del visor responsivamente."""
        if event.width > 60 and event.height > 40:
            self.width = event.width
            self.height = event.height

    # ================= MÉTODOS DE CONTROL DE ESTADO Y EXPRESIONES =================

    def set_state(self, new_state: str):
        """Actualiza el estado operativo (idle, listening, thinking, speaking)."""
        valid_states = ["idle", "listening", "thinking", "speaking"]
        cleaned = new_state.lower().strip()
        if cleaned in valid_states:
            self.state = cleaned
            if cleaned == "speaking":
                self.is_speaking = True
            elif cleaned in ["idle", "listening", "thinking"]:
                self.is_speaking = False

    def set_speaking(self, speaking: bool):
        """Activa o desactiva la articulación de la boca."""
        self.is_speaking = speaking
        if speaking:
            self.state = "speaking"
        elif self.state == "speaking":
            self.state = "idle"

    def set_expression(self, expr_name: str, duration: Optional[float] = None):
        """
        Cambia temporal o permanentemente la expresión del visor.
        Expresiones: "idle", "cool_shades", "happy", "thinking", "surprise", "listening", "wink", "sleeping"
        """
        self.expression = expr_name
        if duration:
            self._expression_until = time.time() + duration
        else:
            self._expression_until = 0.0

    def show_icon(self, icon_name: str, duration: float = 3.0):
        """
        Proyecta un icono contextual en la pantalla durante 'duration' segundos.
        Iconos disponibles: "ice_cream", "music", "search", "clock", "battery", "calc"
        """
        self.active_icon = icon_name
        self._icon_until = time.time() + duration

    def trigger_wake_flash(self, duration: float = 0.65):
        """Activa un resplandor luminoso cian expansivo al detectar la palabra de activación."""
        self._wake_flash_until = time.time() + duration
        self.expression = "listening"

    # ================= BUCLE PRINCIPAL DE DIBUJO =================

    def _animate(self):
        """Bucle continuo de renderizado a ~33 FPS."""
        try:
            self._draw_frame()
        except Exception:
            pass
        self.after(30, self._animate)

    def _draw_frame(self):
        """Renderiza un fotograma completo en el lienzo adaptando la escala dinámicamente."""
        self.delete("all")
        now = time.time()
        t = now - self._start_time

        # Revisar expiración de iconos temporales
        if self.active_icon and now >= self._icon_until:
            self.active_icon = None

        # Revisar expiración de expresiones temporales
        if self._expression_until > 0 and now >= self._expression_until:
            self.expression = "idle"
            self._expression_until = 0.0

        w, h = float(self.width), float(self.height)
        cx, cy = w / 2.0, h / 2.0

        # Factor de escala adaptativo según si es visor de cabecera (< 320px) o pantalla completa
        if w < 320:
            visor_w = max(w - 6.0, 90.0)
            visor_h = max(h - 6.0, 50.0)
            scale = max(0.55, min(visor_w / 440.0, visor_h / 190.0) * 1.85)
            r_outer = min(24.0, visor_h / 2.0)
            r_inner = max(10.0, r_outer - 4.0)
            compact = True
        else:
            visor_w = min(w - 36.0, 560.0)
            visor_w = max(visor_w, 280.0)
            visor_h = min(h - 24.0, 220.0)
            visor_h = max(visor_h, 150.0)
            scale = 1.0
            r_outer = 44.0
            r_inner = 36.0
            compact = False

        # Flotación orgánica sutil de respiración
        bob_y = math.sin(t * 1.8) * (2.2 * scale)

        # Micro-sacadas de mirada cada 2.5 - 4.5 segundos
        if now >= self._next_gaze_time:
            self._next_gaze_time = now + random.uniform(2.5, 4.5)
            if self.expression not in ["cool_shades", "sleeping"]:
                self._gaze_x = random.choice([-4.0, -2.0, 0.0, 0.0, 2.0, 4.0])
                self._gaze_y = random.choice([-2.0, 0.0, 0.0, 2.0])

        # Control de parpadeo suave cada 3.5 - 4.8 segundos
        if not self._is_blinking and now >= self._next_blink_time:
            if self.expression not in ["cool_shades", "sleeping", "wink"]:
                self._is_blinking = True
                self._blink_start_time = now

        blink_ratio = 0.0
        if self._is_blinking:
            dt = now - self._blink_start_time
            dur = 0.18
            if dt < dur:
                blink_ratio = math.sin((dt / dur) * math.pi)
            else:
                self._is_blinking = False
                self._next_blink_time = now + random.uniform(3.5, 5.0)

        # 1. Dibujar el Casco, Bisel y Pantalla de Cristal OLED
        self._draw_helmet_and_screen(cx, cy, visor_w, visor_h, r_outer, r_inner, t, compact)

        # Efecto de halo y resplandor neón de activación instantánea al escuchar "VEX"
        if now < self._wake_flash_until:
            rem = self._wake_flash_until - now
            flash_intensity = min(1.0, rem / 0.65)
            pulse_pad = (1.0 - flash_intensity) * 10.0 * scale
            self._draw_rounded_capsule(
                cx - (visor_w / 2.0) - 3.0 - pulse_pad,
                cy - (visor_h / 2.0) - 3.0 - pulse_pad,
                cx + (visor_w / 2.0) + 3.0 + pulse_pad,
                cy + (visor_h / 2.0) + 3.0 + pulse_pad,
                r_outer + 3.0,
                fill="",
                outline=self.c_cyan_bright,
                width=max(2.0, 3.5 * flash_intensity)
            )

        # 2. Dibujar Proyección de Icono Contextual O Expresión Facial
        if self.active_icon:
            self._draw_contextual_icon(cx, cy + bob_y, visor_w, visor_h, scale, t, self.active_icon)
        else:
            self._draw_face_matrix(cx, cy + bob_y, visor_w, visor_h, scale, t, blink_ratio)

        # 3. Reflejo de Cristal Tenue sobre la Pantalla (Glossy Curve)
        self._draw_glass_reflection(cx, cy, visor_w, visor_h, scale)

        # 4. Indicadores Tácticos de la Pantalla (LEDs superiores)
        if not compact:
            self._draw_visor_telemetry(cx, cy, visor_w, visor_h, t)

    # ================= 1. CASCO Y PANTALLA VISOR =================

    def _draw_rounded_capsule(self, x1, y1, x2, y2, r, **kwargs):
        """Dibuja un rectángulo con esquinas redondeadas suaves (cápsula)."""
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

    def _draw_helmet_and_screen(self, cx: float, cy: float, vw: float, vh: float, r_outer: float, r_inner: float, t: float, compact: bool):
        """Renderiza la carcasa exterior del casco y la pantalla negra pura OLED."""
        vx1 = cx - vw / 2.0
        vy1 = cy - vh / 2.0
        vx2 = cx + vw / 2.0
        vy2 = cy + vh / 2.0

        # Capa 0: Sombra exterior
        self._draw_rounded_capsule(
            vx1 - 3, vy1 - 1,
            vx2 + 3, vy2 + 3,
            r_outer + 2,
            fill="#030408", outline=""
        )

        # Capa 1: Carcasa exterior pulida metálica
        self._draw_rounded_capsule(
            vx1 - 2, vy1 - 2,
            vx2 + 2, vy2 + 2,
            r_outer,
            fill=self.c_bezel_outer, outline="#2b384e", width=1.0
        )

        # Capa 2: Pantalla OLED Negro Puro (#000000)
        self._draw_rounded_capsule(
            vx1, vy1, vx2, vy2,
            r_inner,
            fill=self.c_oled_black, outline=""
        )

        # Borde sutil delimitador
        neon_border_color = self.c_cyan_dim if self.state != "thinking" else "#451a03"
        self._draw_rounded_capsule(
            vx1 + 1, vy1 + 1, vx2 - 1, vy2 - 1,
            r_inner - 1,
            fill="", outline=neon_border_color, width=1.0
        )

        # Partículas de polvo si hay espacio
        if not compact:
            for p in self.particles:
                p[1] -= p[2]
                if p[1] < vy1 + 6:
                    p[1] = vy2 - 6
                    p[0] = random.uniform(vx1 + 12, vx2 - 12)
                if vx1 + 10 < p[0] < vx2 - 10 and vy1 + 10 < p[1] < vy2 - 10:
                    self.create_oval(
                        p[0] - p[3], p[1] - p[3],
                        p[0] + p[3], p[1] + p[3],
                        fill=p[4], outline=""
                    )

    def _draw_glass_reflection(self, cx: float, cy: float, vw: float, vh: float, scale: float):
        """Dibuja un reflejo tenue diagonal de cristal curvado (glossy screen)."""
        vx1 = cx - vw / 2.0
        vy1 = cy - vh / 2.0

        ref_x1 = vx1 + 12.0 * scale
        ref_y1 = vy1 + 6.0 * scale
        ref_x2 = vx1 + vw * 0.44
        ref_y2 = vy1 + 22.0 * scale

        points = [
            ref_x1 + 16 * scale, ref_y1,
            ref_x2, ref_y1,
            ref_x2 - 20 * scale, ref_y2,
            ref_x1, ref_y2
        ]
        self.create_polygon(points, fill="#0d1b2a", outline="", smooth=True)

        self.create_line(
            vx1 + 18 * scale, vy1 + 10 * scale,
            vx1 + 60 * scale, vy1 + 10 * scale,
            fill="#1e3a5f", width=max(1.0, 1.5 * scale)
        )

    def _draw_visor_telemetry(self, cx: float, cy: float, vw: float, vh: float, t: float):
        """Muestra mini-indicadores de hardware en la parte superior del visor."""
        vx1 = cx - vw / 2.0
        vy1 = cy - vh / 2.0

        # LED de estado superior central
        led_color = self.c_cyan_bright
        if self.state == "thinking":
            led_color = self.c_amber
        elif self.state == "speaking":
            led_pulse = 0.5 + 0.5 * math.sin(t * 12.0)
            led_color = self.c_cyan_glow if led_pulse > 0.5 else self.c_cyan_bright
        elif self.state == "listening":
            led_color = "#38bdf8"

        self.create_oval(
            cx - 3, vy1 + 6,
            cx + 3, vy1 + 12,
            fill=led_color, outline="#072238"
        )

    # ================= 2. MATRIZ DE EXPRESIONES FACIALES =================

    def _draw_face_matrix(self, cx: float, cy: float, vw: float, vh: float, scale: float, t: float, blink: float):
        """
        Dibuja los ojos expresivos de neón y la boca articulada según la emoción activa:
        "idle", "cool_shades", "happy", "thinking", "surprise", "listening", "wink", "sleeping"
        """
        expr = self.expression

        if self.state == "thinking" and expr == "idle":
            expr = "thinking"
        elif self.state == "listening" and expr == "idle":
            expr = "listening"

        eye_y = cy - 10.0 * scale + (self._gaze_y * scale)
        mouth_y = cy + 28.0 * scale

        eye_spacing = 64.0 * scale
        left_eye_x = cx - eye_spacing + (self._gaze_x * scale)
        right_eye_x = cx + eye_spacing + (self._gaze_x * scale)

        # ---------------- CASO 1: MODO COOL (GAFAS DE SOL) ----------------
        if expr == "cool_shades":
            self._draw_cool_shades(cx, eye_y, scale, t)
            self._draw_smug_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 2: FELIZ / CONTENTO (^  ^) ----------------
        if expr == "happy":
            self._draw_happy_eye(left_eye_x, eye_y, scale, t)
            self._draw_happy_eye(right_eye_x, eye_y, scale, t)
            self._draw_cheeks(left_eye_x, right_eye_x, eye_y + 18.0 * scale, scale, t)
            self._draw_happy_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 3: GUIÑO (WINK) ----------------
        if expr == "wink":
            self._draw_blocky_eye(left_eye_x, eye_y, scale, t, blink=0.0)
            self._draw_happy_eye(right_eye_x, eye_y, scale, t)
            self._draw_cheeks(left_eye_x, right_eye_x, eye_y + 18.0 * scale, scale, t)
            self._draw_smug_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 4: PENSANDO / ESCANEANDO ----------------
        if expr == "thinking":
            self._draw_thinking_eyes(left_eye_x, right_eye_x, eye_y, scale, t)
            self._draw_scanner_beam(cx, cy, vw, vh, scale, t)
            self._draw_wavy_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 5: SORPRESA / ALERTA (O  O) ----------------
        if expr == "surprise":
            self._draw_surprise_eye(left_eye_x, eye_y, scale, t)
            self._draw_surprise_eye(right_eye_x, eye_y, scale, t)
            self._draw_surprise_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 6: ESCUCHANDO (ATENTO) ----------------
        if expr == "listening":
            self._draw_listening_eyes(left_eye_x, right_eye_x, eye_y, scale, t)
            self._draw_listening_soundwaves(cx, cy, vw, scale, t)
            self._draw_speaking_or_idle_mouth(cx, mouth_y, scale, t)
            return

        # ---------------- CASO 7: DURMIENDO / REPOSO (-  -) ----------------
        if expr == "sleeping":
            self._draw_sleeping_eyes(left_eye_x, right_eye_x, eye_y, scale, t)
            self._draw_floating_zs(right_eye_x + 22 * scale, eye_y - 8 * scale, scale, t)
            self._draw_straight_mouth(cx, mouth_y, scale)
            return

        # ---------------- CASO 8: NORMAL / IDLE (OJOS GRANDES AMIGABLES) ----------------
        self._draw_blocky_eye(left_eye_x, eye_y, scale, t, blink)
        self._draw_blocky_eye(right_eye_x, eye_y, scale, t, blink)
        self._draw_speaking_or_idle_mouth(cx, mouth_y, scale, t)

    # ================= DIBUJO DE OJOS =================

    def _draw_blocky_eye(self, ex: float, ey: float, scale: float, t: float, blink: float):
        """Ojo digital grande y expresivo estilo EMO/Vector con brillo difuminado."""
        ew = 48.0 * scale
        eh = 58.0 * scale

        scale_y = max(0.08, 1.0 - (blink * 0.92))
        curr_h = eh * scale_y

        x1 = ex - ew / 2.0
        y1 = ey - curr_h / 2.0
        x2 = ex + ew / 2.0
        y2 = ey + curr_h / 2.0

        corner_r = min(16.0 * scale, curr_h / 2.0)

        # 1. Glow exterior
        glow_pad = 3.0 * scale
        self._draw_rounded_capsule(
            x1 - glow_pad, y1 - glow_pad,
            x2 + glow_pad, y2 + glow_pad,
            corner_r + 2,
            fill=self.c_cyan_dim, outline=""
        )

        # 2. Neón principal
        self._draw_rounded_capsule(
            x1, y1, x2, y2,
            corner_r,
            fill=self.c_cyan_bright, outline=self.c_cyan_glow, width=max(1.0, 1.5 * scale)
        )

        # 3. Pupila blanca de destello
        if scale_y > 0.4:
            spark_sz = 8.0 * scale
            sp_x = ex + ew * 0.12
            sp_y = ey - curr_h * 0.22
            self.create_rectangle(
                sp_x - spark_sz / 2.0, sp_y - spark_sz / 2.0,
                sp_x + spark_sz / 2.0, sp_y + spark_sz / 2.0,
                fill=self.c_white, outline=""
            )

    def _draw_happy_eye(self, ex: float, ey: float, scale: float, t: float):
        """Ojo curvado hacia arriba en forma de arco (^)."""
        ew = 44.0 * scale
        eh = 28.0 * scale

        points = [
            ex - ew / 2.0, ey + eh / 2.0,
            ex - ew * 0.25, ey - eh / 2.0,
            ex + ew * 0.25, ey - eh / 2.0,
            ex + ew / 2.0, ey + eh / 2.0
        ]
        self.create_line(points, fill=self.c_cyan_dim, width=max(4.0, 8.0 * scale), smooth=True, capstyle="round")
        self.create_line(points, fill=self.c_cyan_bright, width=max(2.5, 5.0 * scale), smooth=True, capstyle="round")
        self.create_line(points, fill=self.c_white, width=max(1.0, 2.0 * scale), smooth=True, capstyle="round")

    def _draw_thinking_eyes(self, lx: float, rx: float, ey: float, scale: float, t: float):
        """Ojos mirando de lado en actitud reflexiva."""
        offset_x = 8.0 * scale
        offset_y = -4.0 * scale

        for ex in [lx + offset_x, rx + offset_x]:
            ew, eh = 40.0 * scale, 48.0 * scale
            x1, y1 = ex - ew / 2.0, ey + offset_y - eh / 2.0
            x2, y2 = ex + ew / 2.0, ey + offset_y + eh / 2.0
            self._draw_rounded_capsule(x1, y1, x2, y2, 12 * scale, fill=self.c_amber, outline=self.c_amber_glow, width=1.5)
            self.create_rectangle(ex + 2, ey + offset_y - 6 * scale, ex + 10 * scale, ey + offset_y + 2, fill="#ffffff", outline="")

    def _draw_surprise_eye(self, ex: float, ey: float, scale: float, t: float):
        """Ojos redondos de alerta/asombro."""
        r = (26.0 + math.sin(t * 8.0) * 1.5) * scale
        self.create_oval(ex - r - 3, ey - r - 3, ex + r + 3, ey + r + 3, fill=self.c_cyan_dim, outline="")
        self.create_oval(ex - r, ey - r, ex + r, ey + r, fill=self.c_cyan_bright, outline=self.c_white, width=1.5)
        pr = 11.0 * scale
        self.create_oval(ex - pr, ey - pr, ex + pr, ey + pr, fill="#000000", outline="")

    def _draw_listening_eyes(self, lx: float, rx: float, ey: float, scale: float, t: float):
        """Ojos atentos al escuchar."""
        pulse = math.sin(t * 6.0) * (2.0 * scale)
        for ex in [lx, rx]:
            ew = 48.0 * scale + pulse
            eh = 58.0 * scale + pulse
            x1, y1 = ex - ew / 2.0, ey - eh / 2.0
            x2, y2 = ex + ew / 2.0, ey + eh / 2.0
            self._draw_rounded_capsule(x1, y1, x2, y2, 14 * scale, fill="#00d9ff", outline="#38bdf8", width=1.5)
            self.create_rectangle(ex - 4 * scale, ey - 4 * scale, ex + 4 * scale, ey + 4 * scale, fill="#ffffff", outline="")

    def _draw_sleeping_eyes(self, lx: float, rx: float, ey: float, scale: float, t: float):
        """Ojos cerrados pacíficamente (-  -)."""
        w = 38.0 * scale
        for ex in [lx, rx]:
            self.create_line(ex - w / 2.0, ey, ex + w / 2.0, ey, fill=self.c_cyan_bright, width=max(2.5, 4.0 * scale), capstyle="round")

    def _draw_floating_zs(self, start_x: float, start_y: float, scale: float, t: float):
        """Letras Z flotantes."""
        zs = ["z", "Z"]
        for i, ch in enumerate(zs):
            phase = (t * 0.8 + i * 0.6) % 2.0
            fade_y = start_y - (phase * 22.0 * scale)
            fade_x = start_x + math.sin(phase * 3.0) * 6.0
            col = "#38bdf8" if phase < 1.4 else "#074a6b"
            sz = int(max(7, (8 + i * 3) * scale))
            self.create_text(fade_x, fade_y, text=ch, font=("Consolas", sz, "bold"), fill=col)

    def _draw_cheeks(self, lx: float, rx: float, cy: float, scale: float, t: float):
        """Mejillas sonrosadas."""
        r = 7.0 * scale
        for cx in [lx - 6 * scale, rx + 6 * scale]:
            self.create_oval(cx - r, cy - r / 2, cx + r, cy + r / 2, fill="#f43f5e", outline="")

    def _draw_scanner_beam(self, cx: float, cy: float, vw: float, vh: float, scale: float, t: float):
        """Haz de escaneo láser."""
        sweep_w = vw * 0.65
        beam_x = cx - sweep_w / 2.0 + ((math.sin(t * 3.5) + 1.0) / 2.0) * sweep_w
        self.create_line(beam_x, cy - 26 * scale, beam_x, cy + 26 * scale, fill="#f59e0b", width=2)

    def _draw_listening_soundwaves(self, cx: float, cy: float, vw: float, scale: float, t: float):
        """Ondas sonoras laterales."""
        vx1 = cx - vw / 2.0
        vx2 = cx + vw / 2.0
        for i in range(2):
            wave_h = (10 + i * 8 + math.sin(t * 10.0 + i) * 4) * scale
            self.create_line(vx1 + (12 + i * 6) * scale, cy - wave_h, vx1 + (12 + i * 6) * scale, cy + wave_h, fill="#00d9ff", width=1.5)
            self.create_line(vx2 - (12 + i * 6) * scale, cy - wave_h, vx2 - (12 + i * 6) * scale, cy + wave_h, fill="#00d9ff", width=1.5)

    # ================= MODO COOL: GAFAS DE SOL =================

    def _draw_cool_shades(self, cx: float, cy: float, scale: float, t: float):
        """Gafas de sol pixeladas 8-bit estilo cyber con destello."""
        px_sz = 4.2 * scale
        base_x = cx
        base_y = cy - 4.0 * scale

        lens_cols = 10
        lens_rows = 6
        gap = 12.0 * scale

        left_x = base_x - (lens_cols * px_sz) - (gap / 2.0)
        right_x = base_x + (gap / 2.0)

        self._draw_pixel_lens(left_x, base_y, lens_cols, lens_rows, px_sz, is_left=True)
        self._draw_pixel_lens(right_x, base_y, lens_cols, lens_rows, px_sz, is_left=False)

        bridge_y = base_y + 3.0 * scale
        self.create_rectangle(
            left_x + (lens_cols * px_sz), bridge_y,
            right_x, bridge_y + px_sz * 1.5,
            fill="#000000", outline=self.c_cyan_bright, width=1.5
        )

        # Destello sparkle
        sparkle_phase = (t * 2.5) % 3.0
        if sparkle_phase < 0.6:
            sp_cx = right_x + (lens_cols * px_sz) - 2
            sp_cy = base_y
            arm = 5.0 * scale
            self.create_line(sp_cx - arm, sp_cy, sp_cx + arm, sp_cy, fill="#ffffff", width=1.5)
            self.create_line(sp_cx, sp_cy - arm, sp_cx, sp_cy + arm, fill="#ffffff", width=1.5)

    def _draw_pixel_lens(self, ox: float, oy: float, cols: int, rows: int, sz: float, is_left: bool):
        """Lente pixelada de gafas de sol."""
        for r in range(rows):
            col_start = 0
            col_end = cols
            if r == rows - 2:
                col_start = 1
                col_end = cols - 1
            elif r == rows - 1:
                col_start = 2
                col_end = cols - 2

            for c in range(col_start, col_end):
                x1 = ox + c * sz
                y1 = oy + r * sz
                x2 = x1 + sz
                y2 = y1 + sz

                fill_col = "#06121e"
                outline_col = "#000000"

                if is_left and (c - r == 2 or c - r == 3) and r < rows - 1:
                    fill_col = "#ffffff"
                    outline_col = "#ffffff"
                elif not is_left and (c - r == 1 or c - r == 2) and r < rows - 1:
                    fill_col = "#38bdf8"
                    outline_col = "#38bdf8"

                self.create_rectangle(x1, y1, x2, y2, fill=fill_col, outline=outline_col)

        total_w = cols * sz
        total_h = rows * sz
        self.create_rectangle(
            ox - 1, oy - 1, ox + total_w + 1, oy + total_h - sz + 1,
            fill="", outline=self.c_cyan_bright, width=max(1.0, 1.8 * (sz / 4.2))
        )

    # ================= DIBUJO DE LA BOCA =================

    def _draw_speaking_or_idle_mouth(self, cx: float, cy: float, scale: float, t: float):
        """Boca que articula fonemas al hablar o sonríe en reposo."""
        if self.is_speaking or self.state == "speaking":
            phase = int((t * 14.0) % 5)
            w = 16.0 * scale
            if phase == 0:
                self.create_rectangle(cx - w, cy - 2, cx + w, cy + 2, fill=self.c_cyan_bright, outline=self.c_white)
            elif phase == 1:
                r = 8.0 * scale
                self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=self.c_cyan_bright, outline=self.c_white, width=1.5)
            elif phase == 2:
                self._draw_rounded_capsule(cx - w * 1.2, cy - 6 * scale, cx + w * 1.2, cy + 6 * scale, 6 * scale, fill=self.c_cyan_bright, outline=self.c_white)
            elif phase == 3:
                self.create_rectangle(cx - w * 1.4, cy - 2, cx + w * 1.4, cy + 2, fill=self.c_cyan_glow, outline="")
            else:
                self.create_line(cx - w, cy - 2, cx, cy + 3 * scale, cx + w, cy - 2, fill=self.c_cyan_bright, width=max(2.0, 3.5 * scale), smooth=True)
        else:
            w = 12.0 * scale
            self.create_line(
                cx - w, cy - 2,
                cx - w * 0.4, cy + 2 * scale,
                cx + w * 0.4, cy + 2 * scale,
                cx + w, cy - 2,
                fill=self.c_cyan_bright, width=max(2.0, 3.0 * scale), smooth=True, capstyle="round"
            )

    def _draw_smug_mouth(self, cx: float, cy: float, scale: float, t: float):
        """Sonrisa cómplice (smirk) para modo Cool."""
        w = 14.0 * scale
        self.create_line(
            cx - w, cy + 3 * scale,
            cx, cy + 3 * scale,
            cx + w * 1.2, cy - 5 * scale,
            fill=self.c_cyan_bright, width=max(2.0, 3.5 * scale), smooth=True, capstyle="round"
        )

    def _draw_happy_mouth(self, cx: float, cy: float, scale: float, t: float):
        """Boca amplia y feliz."""
        w = 20.0 * scale
        h = 12.0 * scale
        self.create_arc(
            cx - w, cy - h,
            cx + w, cy + h,
            start=180, extent=180,
            fill=self.c_cyan_bright, outline=self.c_white, width=1.5
        )

    def _draw_wavy_mouth(self, cx: float, cy: float, scale: float, t: float):
        """Boca ondulada de pensamiento."""
        points = [
            cx - 14 * scale, cy,
            cx - 7 * scale, cy - 3 * scale,
            cx, cy + 2 * scale,
            cx + 7 * scale, cy - 2 * scale,
            cx + 14 * scale, cy + 1
        ]
        self.create_line(points, fill=self.c_amber, width=max(2.0, 3.0 * scale), smooth=True, capstyle="round")

    def _draw_surprise_mouth(self, cx: float, cy: float, scale: float, t: float):
        """Boca redonda en 'O'."""
        r = 8.0 * scale
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#000000", outline=self.c_cyan_bright, width=2)

    def _draw_straight_mouth(self, cx: float, cy: float, scale: float):
        """Boca neutral cerrada."""
        w = 10.0 * scale
        self.create_line(cx - w, cy, cx + w, cy, fill=self.c_cyan_bright, width=max(2.0, 2.5 * scale), capstyle="round")

    # ================= 3. PROYECCIONES CONTEXTUALES DE ICONOS EN PANTALLA =================

    def _draw_contextual_icon(self, cx: float, cy: float, vw: float, vh: float, scale: float, t: float, icon_name: str):
        """Dibuja un icono temático en el centro de la pantalla."""
        mini_eye_y = cy - 14.0 * scale
        self._draw_happy_eye(cx - vw * 0.32, mini_eye_y, scale * 0.85, t)
        self._draw_happy_eye(cx + vw * 0.32, mini_eye_y, scale * 0.85, t)

        if icon_name == "ice_cream":
            self._draw_pixel_ice_cream(cx, cy, scale, t)
        elif icon_name == "music":
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

    def _draw_pixel_ice_cream(self, cx: float, cy: float, scale: float, t: float):
        """Icono pixelado de cono de helado."""
        bob = math.sin(t * 4.0) * (2.0 * scale)
        base_x = cx
        base_y = cy + bob

        # Cereza
        self.create_oval(base_x - 5 * scale, base_y - 32 * scale, base_x + 5 * scale, base_y - 22 * scale, fill="#ef4444", outline="#b91c1c")
        # Bola
        r_scoop = 16.0 * scale
        self.create_oval(
            base_x - r_scoop, base_y - 24 * scale,
            base_x + r_scoop, base_y + 4 * scale,
            fill=self.c_cyan_bright, outline=self.c_white, width=1.5
        )
        # Chispas
        self.create_rectangle(base_x - 6 * scale, base_y - 14 * scale, base_x - 2 * scale, base_y - 11 * scale, fill="#f43f5e", outline="")
        self.create_rectangle(base_x + 4 * scale, base_y - 12 * scale, base_x + 8 * scale, base_y - 9 * scale, fill="#fde047", outline="")

        # Cono
        cone_pts = [
            base_x - 13 * scale, base_y + 2 * scale,
            base_x + 13 * scale, base_y + 2 * scale,
            base_x, base_y + 34 * scale
        ]
        self.create_polygon(cone_pts, fill="#d97706", outline="#b45309", width=1.5)

    def _draw_pixel_music(self, cx: float, cy: float, scale: float, t: float):
        """Notas musicales flotantes 🎵."""
        bob = math.sin(t * 5.0) * (2.5 * scale)
        base_x = cx
        base_y = cy + bob - 6 * scale

        # Nota izquierda
        self.create_oval(base_x - 18 * scale, base_y + 4 * scale, base_x - 8 * scale, base_y + 12 * scale, fill=self.c_cyan_bright, outline="")
        self.create_line(base_x - 9 * scale, base_y + 6 * scale, base_x - 9 * scale, base_y - 14 * scale, fill=self.c_cyan_bright, width=max(2.0, 2.5 * scale))

        # Nota derecha
        self.create_oval(base_x + 6 * scale, base_y, base_x + 16 * scale, base_y + 8 * scale, fill=self.c_cyan_bright, outline="")
        self.create_line(base_x + 15 * scale, base_y + 2 * scale, base_x + 15 * scale, base_y - 18 * scale, fill=self.c_cyan_bright, width=max(2.0, 2.5 * scale))

        # Barra
        self.create_polygon([
            base_x - 9 * scale, base_y - 14 * scale,
            base_x + 15 * scale, base_y - 18 * scale,
            base_x + 15 * scale, base_y - 14 * scale,
            base_x - 9 * scale, base_y - 10 * scale
        ], fill=self.c_cyan_bright)

        # Mini ecualizador 3 barras
        eq_y = cy + 22.0 * scale
        for i in range(3):
            bx = base_x - 10 * scale + i * 9 * scale
            val = math.sin(t * 12.0 + i * 2.0) * 0.5 + 0.5
            bh = (4 + val * 12) * scale
            self.create_rectangle(bx, eq_y - bh, bx + 5 * scale, eq_y, fill=self.c_cyan_glow, outline="")

    def _draw_pixel_search(self, cx: float, cy: float, scale: float, t: float):
        """Lupa pixelada 🔍."""
        base_x = cx
        base_y = cy - 4.0 * scale
        r = 18.0 * scale

        self.create_oval(base_x - r, base_y - r, base_x + r, base_y + r, fill="#051929", outline=self.c_cyan_bright, width=max(2.0, 2.5 * scale))
        self.create_line(base_x + r * 0.7, base_y + r * 0.7, base_x + r + 12 * scale, base_y + r + 12 * scale, fill=self.c_cyan_bright, width=max(3.0, 4.0 * scale), capstyle="round")

        ang = t * 6.0
        lx2 = base_x + math.cos(ang) * (r - 3)
        ly2 = base_y + math.sin(ang) * (r - 3)
        self.create_line(base_x, base_y, lx2, ly2, fill="#38bdf8", width=1.5)

    def _draw_tactical_clock(self, cx: float, cy: float, scale: float, t: float):
        """Reloj digital táctico."""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")

        box_w = 110.0 * scale
        box_h = 42.0 * scale

        self._draw_rounded_capsule(
            cx - box_w / 2.0, cy - box_h / 2.0,
            cx + box_w / 2.0, cy + box_h / 2.0,
            8 * scale,
            fill="#061220", outline=self.c_cyan_bright, width=1.5
        )

        font_sz = int(max(10, 14 * scale))
        self.create_text(cx, cy, text=time_str, font=("Consolas", font_sz, "bold"), fill=self.c_cyan_core)

    def _draw_pixel_battery(self, cx: float, cy: float, scale: float, t: float):
        """Icono de batería."""
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
        """Mini calculadora digital."""
        bw = 50.0 * scale
        bh = 42.0 * scale
        self._draw_rounded_capsule(cx - bw / 2.0, cy - bh / 2.0, cx + bw / 2.0, cy + bh / 2.0, 6 * scale, fill="#081829", outline=self.c_cyan_bright, width=1.5)
        self.create_rectangle(cx - 20 * scale, cy - 14 * scale, cx + 20 * scale, cy - 4 * scale, fill="#042033", outline=self.c_cyan_glow)
        font_sz = int(max(7, 9 * scale))
        self.create_text(cx, cy + 8 * scale, text="+ - =", font=("Consolas", font_sz, "bold"), fill=self.c_cyan_core)

    def _draw_pixel_notes(self, cx: float, cy: float, scale: float, t: float):
        """Icono animado de libreta / bloc de notas digital 📝."""
        bob = math.sin(t * 4.0) * (2.0 * scale)
        base_x = cx
        base_y = cy + bob - 2.0 * scale

        bw = 42.0 * scale
        bh = 50.0 * scale
        bx1 = base_x - bw / 2.0
        by1 = base_y - bh / 2.0
        bx2 = base_x + bw / 2.0
        by2 = base_y + bh / 2.0

        # Fondo del bloc de notas
        self._draw_rounded_capsule(bx1, by1, bx2, by2, 5 * scale, fill="#071526", outline=self.c_cyan_bright, width=1.5)

        # Barra superior de la nota
        self.create_rectangle(bx1 + 2, by1 + 2, bx2 - 2, by1 + 8 * scale, fill=self.c_cyan_glow, outline="")

        # Líneas de texto holográficas
        line_colors = [self.c_white, self.c_cyan_core, self.c_cyan_core]
        for i in range(3):
            ly = by1 + (16 + i * 8) * scale
            lw = (28 - i * 4) * scale
            self.create_line(bx1 + 7 * scale, ly, bx1 + 7 * scale + lw, ly, fill=line_colors[i], width=max(1.5, 2.0 * scale), capstyle="round")

        # Lápiz / cursor táctico brillante en la esquina
        px = bx2 - 3 * scale
        py = by2 - 4 * scale
        self.create_line(px - 10 * scale, py - 10 * scale, px, py, fill="#fde047", width=max(2.0, 3.0 * scale), capstyle="round")
        self.create_oval(px - 2 * scale, py - 2 * scale, px + 2 * scale, py + 2 * scale, fill="#ffffff", outline="")

