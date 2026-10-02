"""
LYAXIS labs™ - Robot Visor Wrapper y Retrocompatibilidad (VEX Avatar)
Re-exporta RobotVisorCanvas como CyberAvatarCanvas para compatibilidad total
con módulos y scripts existentes.
"""
from ui.robot_visor import RobotVisorCanvas

class CyberAvatarCanvas(RobotVisorCanvas):
    """
    Subclase retrocompatible que vincula el nuevo Visor de Robot Digital
    estilo EMO / Vector con cualquier referencia histórica a CyberAvatarCanvas.
    """
    pass

__all__ = ["CyberAvatarCanvas", "RobotVisorCanvas"]
