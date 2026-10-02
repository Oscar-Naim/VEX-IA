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


# ==================== HELPERS DE TIPOGRAFÍA JERARQUIZADA ====================

def get_font_title():
    """Fuente de branding y cabeceras tácticas."""
    return ctk.CTkFont(family="Consolas", size=13, weight="bold")

def get_font_subtitle():
    """Fuente de subtítulo de identidad y rol."""
    return ctk.CTkFont(family="Consolas", size=10, weight="normal")

def get_font_body():
    """Fuente legible de lectura en burbujas de mensaje (13-14px)."""
    return ctk.CTkFont(family="Segoe UI", size=13, weight="normal")

def get_font_code():
    """Fuente monoespaciada para bloques de código y telemetría."""
    return ctk.CTkFont(family="Consolas", size=12, weight="normal")

def get_font_badge():
    """Fuente de badges luminosos y botones compactos."""
    return ctk.CTkFont(family="Consolas", size=10, weight="bold")

def get_font_icon():
    """Fuente para iconos vectoriales/emojis del riel."""
    return ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
