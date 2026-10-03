"""
LYAXIS labs™ - Tokens Visuales y Estilos Cyber-Premium (VEX UI)
Paleta de colores de alta fidelidad OLED, tipografía jerarquizada y estilos
glassmorphism para la arquitectura de 3 paneles de VEX.
"""
import customtkinter as ctk

# ==================== PALETA DE COLOR OLED & CYBER-PREMIUM ====================
# Fondos estructurales
BG_ROOT = "#050608"             # Negro puro OLED / Grafito ultra-oscuro
BG_RAIL = "#07080d"             # Riel de iconos lateral (60px)
BG_CHATS_PANEL = "#090c13"      # Panel lateral de conversaciones (240px)
BG_HEADER = "#070a12"           # Encabezado táctico superior
BG_CHAT_AREA = "#050609"        # Lienzo principal de chat
BG_INPUT_CAPSULE = "#0b0f19"    # Cápsula de entrada flotante

# Tarjetas y burbujas
BG_USER_CARD = "#121828"        # Mensajes de usuario
BG_VEX_CARD = "#0d111a"         # Respuestas de VEX
BG_TOOL_CARD = "#071318"        # Notificaciones de herramientas / sistema
BG_CODE_BLOCK = "#04070e"       # Bloques de código
BG_HOVER_ITEM = "#141b2b"       # Elementos en lista al pasar el cursor

# Bordes y divisores
BORDER_SUBTLE = "#151c2e"       # Borde base translúcido
BORDER_CARD = "#1b253d"         # Borde de burbujas
BORDER_CYAN = "#00d9ff"         # Acento neón cian
BORDER_BLUE = "#2563ff"         # Acento azul eléctrico
BORDER_AMBER = "#f59e0b"        # Acento advertencia / proceso
BORDER_GREEN = "#10b981"        # Acento online / completado

# Acentos luminosos LYAXIS labs™
ACCENT_CYAN = "#00d9ff"
ACCENT_CYAN_GLOW = "#38bdf8"
ACCENT_CYAN_DIM = "#063c54"
ACCENT_BLUE = "#2563ff"
ACCENT_BLUE_HOVER = "#1d4ed8"
ACCENT_GREEN = "#10b981"
ACCENT_GREEN_GLOW = "#34d399"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#ef4444"

# Tipografía y textos
TEXT_PRIMARY = "#f8fafc"        # Texto de lectura principal
TEXT_SECONDARY = "#94a3b8"      # Subtítulos y descripciones
TEXT_MUTED = "#475569"          # Marcas de tiempo y leyendas
TEXT_CYAN = "#00d9ff"           # Acentos clave de marca
TEXT_GREEN = "#10b981"
TEXT_AMBER = "#fbbf24"
TEXT_WHITE = "#ffffff"

# ==================== SISTEMA DE TEMAS CYBER-PREMIUM ====================
THEMES = {
    "electric_cyan": {
        "id": "electric_cyan",
        "name": "✦ Electric Cyan (LYAXIS)",
        "accent": "#00d9ff",
        "accent_glow": "#38bdf8",
        "accent_dim": "#0369a1",
        "accent_secondary": "#2563ff",
        "bg_header": "#070a12",
        "glow_rgb": [0.0, 217.0, 255.0],
        "ACCENT_CYAN": "#00d9ff",
        "ACCENT_CYAN_GLOW": "#38bdf8",
        "ACCENT_CYAN_DIM": "#0369a1"
    },
    "cyber_synth": {
        "id": "cyber_synth",
        "name": "🟣 Cyber Synth",
        "accent": "#a855f7",
        "accent_glow": "#ec4899",
        "accent_dim": "#7e22ce",
        "accent_secondary": "#c084fc",
        "bg_header": "#0d071a",
        "glow_rgb": [168.0, 85.0, 247.0],
        "ACCENT_CYAN": "#a855f7",
        "ACCENT_CYAN_GLOW": "#ec4899",
        "ACCENT_CYAN_DIM": "#7e22ce"
    },
    "matrix_green": {
        "id": "matrix_green",
        "name": "🟢 Matrix Green",
        "accent": "#10b981",
        "accent_glow": "#34d399",
        "accent_dim": "#047857",
        "accent_secondary": "#059669",
        "bg_header": "#05130a",
        "glow_rgb": [16.0, 185.0, 129.0],
        "ACCENT_CYAN": "#10b981",
        "ACCENT_CYAN_GLOW": "#34d399",
        "ACCENT_CYAN_DIM": "#047857"
    }
}

CURRENT_THEME = "electric_cyan"

def get_current_theme():
    return THEMES.get(CURRENT_THEME, THEMES["electric_cyan"])

def set_active_theme(theme_id: str):
    global CURRENT_THEME, ACCENT_CYAN, ACCENT_CYAN_GLOW, BORDER_CYAN
    if theme_id in THEMES:
        CURRENT_THEME = theme_id
        t = THEMES[theme_id]
        ACCENT_CYAN = t["accent"]
        ACCENT_CYAN_GLOW = t["accent_glow"]
        BORDER_CYAN = t["accent"]
        return t
    return THEMES["electric_cyan"]


# ==================== HELPERS DE TIPOGRAFÍA JERARQUIZADA ====================

def get_font_title():
    """Fuente de branding y cabeceras tácticas — 14px bold legible."""
    return ctk.CTkFont(family="Consolas", size=14, weight="bold")

def get_font_subtitle():
    """Fuente de subtítulo de identidad y rol — 11px."""
    return ctk.CTkFont(family="Consolas", size=11, weight="normal")

def get_font_body():
    """Fuente legible de lectura en burbujas de mensaje — 14px cómodo."""
    return ctk.CTkFont(family="Segoe UI", size=14, weight="normal")

def get_font_code():
    """Fuente monoespaciada para bloques de código y telemetría — 12px."""
    return ctk.CTkFont(family="Consolas", size=12, weight="normal")

def get_font_badge():
    """Fuente de badges luminosos y botones compactos — 11px bold."""
    return ctk.CTkFont(family="Consolas", size=11, weight="bold")

def get_font_icon():
    """Fuente para iconos vectoriales/emojis del riel."""
    return ctk.CTkFont(family="Segoe UI", size=16, weight="bold")

def get_font_header_title():
    """Fuente grande para el nombre del asistente en el header — 16px bold."""
    return ctk.CTkFont(family="Consolas", size=16, weight="bold")

def get_font_header_sub():
    """Fuente pequeña para subtítulo del header — 10px."""
    return ctk.CTkFont(family="Consolas", size=10, weight="normal")
