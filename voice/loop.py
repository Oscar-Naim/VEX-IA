"""
LYAXIS labs™ - Bucle Principal de Escucha y Orquestación Vocal para VEX
Proporciona la interfaz del ciclo acústico con soporte para blindaje de micrófono,
palabra de activación y atenuación de audio (Audio Ducking).
"""
from voice.manager import VoiceAssistantManager, AssistantState
from voice.ducking import AudioDucker
from voice.stt import SpeechToTextListener
from voice.wakeword import WakeWordDetector

__all__ = [
    "VoiceAssistantManager",
    "AssistantState",
    "AudioDucker",
    "SpeechToTextListener",
    "WakeWordDetector",
]
