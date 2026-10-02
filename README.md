# LYAXIS labs™ // VEX HUD - 3-Zone Cyber Desktop Assistant

![LYAXIS Core](https://img.shields.io/badge/LYAXIS%20labs™-VEX%20v4.5-00d9ff?style=for-the-badge)
![Layout](https://img.shields.io/badge/Layout-3--Panel%20JARVIS%20Console-2563ff?style=for-the-badge)
![Robot Visor](https://img.shields.io/badge/UI-EMO%20%2F%20Vector%20Visor-000000?style=for-the-badge)
![Edge-TTS](https://img.shields.io/badge/Voice-Edge--TTS%20Neural-10b981?style=for-the-badge)

Asistente de escritorio táctico e interactivo **VEX** (Visual & Execution Nexus) desarrollado por **LYAXIS labs™** para Oscar. Incorpora una arquitectura visual completa de **3 Zonas (Layout tipo ChatGPT / JARVIS)** con diseño Cyber-Premium OLED:

---

## 🌟 Estructura y Maquetación de la Ventana (Layout de 3 Zonas)

### Zona A: Riel de Iconos Lateral Izquierdo (Icon Rail - 60px)
- Columna vertical fija con accesos rápidos minimalistas con iconos vectoriales:
  - 💬 **Chat principal**: Vista activa de conversación.
  - ▶ **YouTube**: Búsqueda o apertura de YouTube.
  - 🎧 **Spotify**: Lanzador rápido del reproductor de música.
  - 📝 **Bloc de notas**: Apertura instantánea de notas del sistema.
  - 🔊 **Volumen**: Control táctico de audio.
  - 🍦 **Helado**: Proyección temática en el visor robótico.
  - ⚙ **Ajustes BYOK**: Modal para clave de API y operador.
  - `●` **Indicador ONLINE**: Pulsación verde esmeralda inferior.

### Zona B: Barra Lateral Desplegable ("Mis Chats" - 240px)
- **Botón píldora neón**: `+ Nueva conversación`.
- **Buscador interactivo**: `🔍 Buscar en chats...` con filtrado en tiempo real.
- **Lista scrolleable de sesiones**: Agrupadas con fechas, títulos auto-generados y botón de papelera `🗑` para eliminar sesiones.

### Zona C: Área Central de Conversación (Chat Canvas)
- **Header Superior Táctico**:
  - Lado izquierdo: **Visor de Robot Digital Expresivo (EMO / Vector)** integrado (ojos en cian neón que pestañean, sonríen, articulan boca al hablar y despliegan gafas de sol o iconos contextuales), título `VEX // TACTICAL ASSISTANT` y subtítulo `LYAXIS labs™`.
  - Lado derecho: Selector desplegable de modelo (Failover Pool), badge `VEX v3.0`, switch `⚡ CHARLA CONTINUA [ON/OFF]` y botón `⚙ BYOK`.
- **Flujo de Mensajes**:
  - **Mensajes de Usuario**: Tarjetas alineadas a la derecha con badge `● [OPERADOR // OSCAR]`, padding amplio y bordes azules.
  - **Respuestas de VEX**: Tarjetas glassmorphic oscuras (`#0d111a`), avatar de IA con aro cian, bloques de código estilizados con botón `<> Copiar` y botones de acción `🔊 Escuchar de nuevo` y `📋 Copiar texto`.
  - **Acciones y Herramientas**: Tarjetas compactas de eventos (`✔ YouTube ejecutado: '...'`) con acento verde esmeralda.
- **Cápsula Flotante Inferior**:
  - Botón de adjuntar archivos `📎`.
  - Campo de entrada de texto auto-expandible con placeholder *"Escribe o habla con VEX..."*.
  - Botón de micrófono `🎙 VOZ` con animación de respiración pulsante en cian neón.
  - Botón de envío con flecha azul eléctrica `➤`.

---

## 📁 Estructura del Proyecto

```plaintext
aistente lyaxis/
├── main.py                     # Punto de arranque principal
├── config/
│   ├── settings.py             # Configuración centralizada y gestión BYOK
│   └── user_config.json        # Almacenamiento local desacoplado
├── agent/
│   ├── router.py               # Capa 0: Enrutador rápido Zero-Token con emociones
│   └── gemini_agent.py         # Capa 1: Cliente Gemini con Failover Pool y detector de emociones
├── ui/
│   ├── styles.py               # Tokens visuales, paleta OLED, fuentes y bordes
│   ├── chat_bubbles.py         # Tarjetas de mensajes de usuario, respuestas VEX y herramientas
│   ├── layout.py               # Arquitectura principal de 3 zonas y canvas de chat
│   ├── main_window.py          # Re-exportador de MainWindow
│   ├── window.py               # Re-exportador retrocompatible de MainWindow
│   ├── robot_visor.py          # Pantalla Visor de Robot Digital (EMO / Vector)
│   └── avatar.py               # Wrapper retrocompatible
├── voice/
│   ├── wakeword.py             # Motor 100% Offline de Palabra de Activación (Vosk + Energy Gate)
│   ├── manager.py              # Orquestador del ciclo de vida inteligente (Standby -> Wake -> Follow-up)
│   ├── stt.py                  # Reconocimiento de órdenes vocalizadas
│   └── tts.py                  # Síntesis Edge-TTS (JorgeNeural) con articulación de boca
└── tools/
    └── system_tools.py         # Herramientas del sistema operativo
```

---

## ⚡ Activación por Voz Manos Libres (Wake Word Zero-Cloud)

VEX incluye detección de palabra clave local e instantánea (estilo Alexa / Google Home):
- **100% Offline (<1.5% CPU)**: Monitoreo acústico continuo con umbral RMS y modelo Vosk ligero en segundo plano. Sin llamadas a Gemini ni consumo de datos en espera.
- **Palabras Clave Reconocidas**: *"VEX"*, *"Oye VEX"*, *"Hey VEX"*, *"Bex"*.
- **Ciclo de Vida Inteligente**:
  1. **Standby**: Visor con ojos entrecerrados y respiración tenue.
  2. **Wake**: Destello en cian neón (`#00d9ff`), chime cibernético ascendente (880Hz $\rightarrow$ 1320Hz) y ojos abiertos de inmediato.
  3. **Listening**: Captura de orden durante 5-6 segundos.
  4. **Speaking**: Respuesta táctica vocalizada con modulación de boca en el visor.
  5. **Follow-up (4s)**: Ventana de 4 segundos para preguntas consecutivas sin repetir *"VEX"*. Si no hay más consultas, emite un tono suave de descanso y vuelve a Standby.

---

## 🚀 Guía de Ejecución

1. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Iniciar la aplicación:
   ```bash
   python main.py
   ```
3. Interactuar libremente:
   - Di en voz alta en tu habitación: *"**VEX**"* u *"**Oye VEX**"*.
   - Dicta cualquier orden: *"Abre YouTube"*, *"Sube el volumen"*, *"Pon música en Spotify"*, o haz preguntas complejas a Gemini.
   - O usa el panel visual táctico y el chat integrado.
