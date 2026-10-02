"""
LYAXIS labs™ - VEX C.O.R.E. (Personal AI Desktop Assistant)
Punto de arranque de la aplicación con arquitectura de 3 paneles (ChatGPT/JARVIS style),
visor de robot expresivo EMO/Vector, enrutador Zero-Token y motor Edge-TTS.
"""
import sys

# Asegurar codificación UTF-8 en consola de Windows para evitar errores cp1252
if sys.platform.startswith("win"):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from ui.layout import MainWindow


def main():
    try:
        app = MainWindow()
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
