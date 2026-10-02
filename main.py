"""
LYAXIS labs™ - VEX C.O.R.E. (Personal AI Desktop Assistant)
Punto de arranque de la aplicación con arquitectura de 3 paneles (ChatGPT/JARVIS style),
visor de robot expresivo EMO/Vector, enrutador Zero-Token y motor Edge-TTS.
"""
import sys
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
