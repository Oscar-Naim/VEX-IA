"""
LYAXIS labs™ - Gestor de Memoria Persistente Multi-Usuario para VEX
Almacenamiento desacoplado en archivos JSON locales en memory/profiles/<user_id>.json.
Gestiona perfiles de usuario, tareas programadas, rutinas diarias y hechos aprendidos (learned facts).
"""
import os
import sys
import json
import re
import uuid
import datetime
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

import config


class MemoryManager:
    """
    Gestor central de memoria persistente multi-usuario de VEX.
    Permite a cada usuario tener su propio historial de tareas, rutinas y hechos aprendidos.
    """

    def __init__(self, profiles_dir: Optional[Path] = None):
        if profiles_dir:
            self.profiles_dir = Path(profiles_dir)
        elif getattr(sys, "frozen", False):
            self.profiles_dir = Path(sys.executable).resolve().parent / "memory" / "profiles"
        else:
            self.profiles_dir = Path(__file__).resolve().parent / "profiles"

        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self.active_user_id: Optional[str] = None
        self.active_profile: Dict[str, Any] = {}
        self._change_listeners: List[Any] = []

        # Cargar o inicializar perfil activo
        self._initialize_active_profile()

    def subscribe_changes(self, callback: Any):
        """Registra un observador que se ejecuta cuando cambian tareas o perfil."""
        if callback not in self._change_listeners:
            self._change_listeners.append(callback)

    def unsubscribe_changes(self, callback: Any):
        """Desregistra un observador."""
        if callback in self._change_listeners:
            self._change_listeners.remove(callback)

    def notify_changes(self):
        """Notifica a todos los escuchas que los datos del perfil han cambiado."""
        for cb in list(self._change_listeners):
            try:
                cb()
            except Exception as e:
                print(f"[MemoryManager] Error en callback de cambios: {e}")

    @property
    def active_user(self) -> Dict[str, Any]:
        """Alias para acceder al diccionario del perfil activo."""
        return self.active_profile

    @staticmethod
    def _slugify(name: str) -> str:
        """Convierte un nombre legible en un ID de archivo seguro (ej. 'Alexis Naim' -> 'alexis_naim')."""
        s = name.strip().lower()
        replacements = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]
        for a, b in replacements:
            s = s.replace(a, b)
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s-]+", "_", s).strip("_")
        return s or "usuario"

    def _get_profile_path(self, user_id: str) -> Path:
        """Devuelve la ruta absoluta al archivo JSON de un perfil."""
        return self.profiles_dir / f"{user_id}.json"

    def _initialize_active_profile(self):
        """Descubre perfiles existentes o prepara el perfil inicial por defecto."""
        profiles = self.list_profiles()
        current_cfg_name = config.get_user_name()
        current_slug = self._slugify(current_cfg_name)

        if current_slug and self._get_profile_path(current_slug).exists():
            self.load_profile(current_slug)
        elif profiles:
            # Cargar el primer perfil disponible
            self.load_profile(profiles[0]["user_id"])
        else:
            # Si no existe ningún perfil, crear el inicial basado en config
            self.create_profile(display_name=current_cfg_name or "Oscar")

    # ================= GESTIÓN DE PERFILES =================

    def list_profiles(self) -> List[Dict[str, str]]:
        """Lista todos los perfiles de usuario registrados en memory/profiles/."""
        results = []
        with self._lock:
            for p in self.profiles_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        results.append({
                            "user_id": data.get("user_id", p.stem),
                            "display_name": data.get("display_name", p.stem.title()),
                            "created_at": data.get("created_at", "")
                        })
                except Exception:
                    pass
        return sorted(results, key=lambda x: x["display_name"].lower())

    def create_profile(
        self,
        display_name: str,
        user_id: Optional[str] = None,
        voice_speed: str = "+15%",
        routines: Optional[List[Dict]] = None,
        tasks: Optional[List[Dict]] = None,
        learned_facts: Optional[Dict[str, str]] = None,
        initial_facts: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Crea un nuevo perfil de usuario con estructura estándar y lo establece como activo."""
        clean_name = display_name.strip() or "Operador"
        if not user_id:
            user_id = self._slugify(clean_name)
        else:
            user_id = self._slugify(user_id)

        # Evitar sobreescritura accidental si ya existe otro con el mismo id base
        profile_path = self._get_profile_path(user_id)
        if profile_path.exists() and not self.active_profile:
            return self.load_profile(user_id)

        today_str = datetime.date.today().strftime("%Y-%m-%d")

        default_routines = routines if routines is not None else []
        default_tasks = tasks if tasks is not None else []

        facts_source = learned_facts or initial_facts or {
            "preferencia_musica": "Rock y Hip Hop",
            "navegador": "Google Chrome",
            "asistente": "VEX Tactical AI"
        }
        default_facts = dict(facts_source)

        profile_data = {
            "user_id": user_id,
            "display_name": clean_name,
            "voice_speed": voice_speed,
            "created_at": today_str,
            "routines": default_routines,
            "tasks": default_tasks,
            "learned_facts": default_facts
        }

        with self._lock:
            try:
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[MemoryManager] Error al guardar perfil '{user_id}': {e}")

            self.active_user_id = user_id
            self.active_profile = profile_data

        # Sincronizar nombre global con config
        config.set_user_name(clean_name)
        return profile_data

    def load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Carga un perfil existente en memoria y lo establece como activo."""
        profile_path = self._get_profile_path(user_id)
        if not profile_path.exists():
            return None

        with self._lock:
            try:
                with open(profile_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.active_user_id = user_id
                self.active_profile = data
                disp_name = data.get("display_name", user_id.title())
                config.set_user_name(disp_name)
                self.notify_changes()
                return data
            except Exception as e:
                print(f"[MemoryManager] Error al cargar perfil '{user_id}': {e}")
                return None

    def switch_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Cambia el usuario activo cargando su perfil persistente."""
        return self.load_profile(user_id)

    def save_active_profile(self) -> bool:
        """Persiste los cambios del perfil activo en su archivo JSON."""
        if not self.active_user_id or not self.active_profile:
            return False

        profile_path = self._get_profile_path(self.active_user_id)
        with self._lock:
            try:
                with open(profile_path, "w", encoding="utf-8") as f:
                    json.dump(self.active_profile, f, indent=2, ensure_ascii=False)
                return True
            except Exception as e:
                print(f"[MemoryManager] Error al persistir perfil activo: {e}")
                return False

    def get_active_profile(self) -> Dict[str, Any]:
        """Obtiene una copia segura del perfil activo."""
        return dict(self.active_profile)

    def get_active_user_name(self) -> str:
        """Obtiene el nombre en pantalla del usuario activo."""
        return self.active_profile.get("display_name", config.get_user_name())

    # ================= GESTIÓN DE TAREAS =================

    def add_task(self, title: str, date: str = "", time: str = "") -> Dict[str, Any]:
        """
        Registra una nueva tarea en el perfil activo.
        Normaliza siempre la fecha a formato estricto YYYY-MM-DD y la hora a HH:MM (24h).
        """
        clean_title = title.strip()
        try:
            from tools.memory_tools import normalize_task_date, normalize_task_time, clean_task_title
            clean_title = clean_task_title(title)
            target_date = normalize_task_date(date)
            clean_time = normalize_task_time(time)
        except Exception:
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            clean_date = date.strip().lower()
            if not clean_date or clean_date in ["hoy", "today"]:
                target_date = today_str
            elif clean_date in ["mañana", "tomorrow"]:
                target_date = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                target_date = date.strip() or today_str
            clean_time = time.strip() or "10:00"

        task_id = f"task_{uuid.uuid4().hex[:6]}"
        new_task = {
            "id": task_id,
            "title": clean_title,
            "date": target_date,
            "time": clean_time,
            "completed": False
        }

        tasks = self.active_profile.setdefault("tasks", [])
        tasks.append(new_task)
        self.save_active_profile()
        self.notify_changes()
        return new_task

    def list_tasks(self, include_completed: bool = False, for_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Devuelve las tareas del usuario activo con filtros opcionales."""
        tasks = self.active_profile.get("tasks", [])
        filtered = []
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        for t in tasks:
            if not include_completed and t.get("completed", False):
                continue
            if for_date:
                t_date = t.get("date", "")
                if for_date in ["hoy", "today"] and t_date != today_str:
                    continue
                elif for_date not in ["hoy", "today"] and t_date != for_date:
                    continue
            filtered.append(t)
        return filtered

    @staticmethod
    def parse_task_index(text: str) -> Optional[int]:
        """Extrae el índice numérico o término ordinal de una referencia a tarea (1-based, o -1 para última)."""
        norm_t = text.lower().strip()
        norm_t = re.sub(r"^(?:a|la|el|las|los|mi|mis|de)\s+", "", norm_t).strip()
        if re.search(r"\b(primera|primero|primer|1a|1ra|1ro|uno)\b", norm_t):
            return 1
        if re.search(r"\b(segunda|segundo|2a|2da|2do|dos)\b", norm_t):
            return 2
        if re.search(r"\b(tercera|tercero|tercer|3a|3ra|3ro|tres)\b", norm_t):
            return 3
        if re.search(r"\b(cuarta|cuarto|4a|4ta|4to|cuatro)\b", norm_t):
            return 4
        if re.search(r"\b(quinta|quinto|5a|5ta|5to|cinco)\b", norm_t):
            return 5
        if re.search(r"\b(sexta|sexto|6a|6to|seis)\b", norm_t):
            return 6
        if re.search(r"\b(ultima|última|ultimo|último)\b", norm_t):
            return -1
        m = re.search(r"\b(?:numero\s+|num\s+|#)?(\d+)\b", norm_t)
        if m:
            return int(m.group(1))
        return None

    def delete_task_by_index(self, index: int, include_completed: bool = False) -> Optional[Dict[str, Any]]:
        """
        Elimina una tarea por su posición en la lista (1-based, o -1 para la última).
        Devuelve el diccionario de la tarea eliminada, o None si el índice no existe.
        """
        tasks = self.list_tasks(include_completed=include_completed)
        if not tasks:
            return None
        idx = len(tasks) - 1 if index == -1 else index - 1
        if 0 <= idx < len(tasks):
            target_task = tasks[idx]
            target_id = target_task.get("id")
            if target_id:
                # Eliminación directa sin recursión por índice
                initial_len = len(self.active_profile.get("tasks", []))
                self.active_profile["tasks"] = [
                    t for t in self.active_profile.get("tasks", []) if t.get("id") != target_id
                ]
                if len(self.active_profile["tasks"]) < initial_len:
                    self.save_active_profile()
                    self.notify_changes()
                    return target_task
        return None

    def complete_task_by_index(self, index: int) -> Optional[Dict[str, Any]]:
        """
        Marca una tarea como completada por su posición en la lista de pendientes (1-based, o -1 para la última).
        Devuelve el diccionario de la tarea completada, o None si el índice no existe.
        """
        tasks = self.list_tasks(include_completed=False)
        if not tasks:
            return None
        idx = len(tasks) - 1 if index == -1 else index - 1
        if 0 <= idx < len(tasks):
            target_task = tasks[idx]
            target_id = target_task.get("id")
            for t in self.active_profile.get("tasks", []):
                if t.get("id") == target_id:
                    t["completed"] = True
                    self.save_active_profile()
                    self.notify_changes()
                    return target_task
        return None

    def complete_task(self, identifier: str) -> bool:
        """Marca una tarea como completada por ID, título o posición ordinal/numérica."""
        target = identifier.strip().lower()
        if not target:
            return False

        parsed_idx = self.parse_task_index(target)
        if parsed_idx is not None and not any(t.get("id") == target for t in self.active_profile.get("tasks", [])):
            return self.complete_task_by_index(parsed_idx) is not None

        tasks = self.active_profile.get("tasks", [])
        found = False

        for t in tasks:
            t_id = t.get("id", "").lower()
            t_title = t.get("title", "").strip().lower()
            if t_id == target or t_title == target:
                t["completed"] = True
                found = True
                break
            if len(target) >= 3 and (target in t_title or t_title in target):
                t["completed"] = True
                found = True
                break

        if found:
            self.save_active_profile()
            self.notify_changes()
        return found

    def set_task_completed(self, task_id: str, completed: bool = True) -> bool:
        """Establece explícitamente el estado completado de una tarea por su ID."""
        target = task_id.strip()
        tasks = self.active_profile.get("tasks", [])
        found = False

        for t in tasks:
            if t.get("id") == target:
                t["completed"] = bool(completed)
                found = True
                break

        if found:
            self.save_active_profile()
            self.notify_changes()
        return found

    def delete_task(self, identifier: str) -> bool:
        """Elimina una tarea por su ID, coincidencia en el título o posición ordinal/numérica."""
        target = identifier.strip().lower()
        if not target:
            return False

        parsed_idx = self.parse_task_index(target)
        if parsed_idx is not None and not any(t.get("id") == target for t in self.active_profile.get("tasks", [])):
            return self.delete_task_by_index(parsed_idx) is not None

        tasks = self.active_profile.get("tasks", [])
        initial_len = len(tasks)

        def _matches(t):
            t_id = t.get("id", "").lower()
            t_title = t.get("title", "").strip().lower()
            if t_id == target or t_title == target:
                return True
            if len(target) >= 3 and (target in t_title or t_title in target):
                return True
            return False

        self.active_profile["tasks"] = [
            t for t in tasks if not _matches(t)
        ]
        if len(self.active_profile["tasks"]) < initial_len:
            self.save_active_profile()
            self.notify_changes()
            return True
        return False

    # ================= GESTIÓN DE RUTINAS =================

    def set_routine(self, name: str, description: str, time: str = "08:00") -> Dict[str, Any]:
        """Añade o actualiza una rutina en el perfil activo."""
        routines = self.active_profile.setdefault("routines", [])
        clean_name = name.strip()
        slug_id = self._slugify(clean_name)

        # Buscar si ya existe para actualizar
        for r in routines:
            if r.get("id") == slug_id or r.get("name", "").lower() == clean_name.lower():
                r["name"] = clean_name
                r["description"] = description.strip()
                if time:
                    r["time"] = time.strip()
                self.save_active_profile()
                return r

        new_routine = {
            "id": slug_id,
            "name": clean_name,
            "time": time.strip() or "08:00",
            "description": description.strip()
        }
        routines.append(new_routine)
        self.save_active_profile()
        return new_routine

    def list_routines(self) -> List[Dict[str, Any]]:
        """Devuelve las rutinas configuradas en el perfil activo."""
        return self.active_profile.get("routines", [])

    # ================= HECHOS APRENDIDOS (LEARNED FACTS) =================

    def remember_fact(self, key: str, value: str) -> bool:
        """Almacena un hecho, preferencia o dato clave sobre el usuario."""
        clean_key = self._slugify(key)
        clean_val = value.strip()
        facts = self.active_profile.setdefault("learned_facts", {})
        facts[clean_key] = clean_val
        return self.save_active_profile()

    def get_facts(self) -> Dict[str, str]:
        """Devuelve el diccionario de hechos aprendidos."""
        return dict(self.active_profile.get("learned_facts", {}))

    def forget_fact(self, key: str) -> bool:
        """Elimina un hecho aprendido."""
        clean_key = self._slugify(key)
        facts = self.active_profile.get("learned_facts", {})
        if clean_key in facts:
            del facts[clean_key]
            return self.save_active_profile()
        return False

    # ================= CONTEXTO PARA PROMPT DE IA =================

    def build_memory_context(self) -> str:
        """
        Genera un bloque de texto contextual para inyectar en el System Prompt de Gemini o Groq.
        Permite a la IA saber exactamente qué tareas, rutinas y preferencias tiene el usuario.
        """
        user_name = self.get_active_user_name()
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        lines = [f"PERFIL Y MEMORIA DEL USUARIO ACTUAL ({user_name}):"]

        # Tareas pendientes
        pending_today = self.list_tasks(include_completed=False, for_date="hoy")
        if pending_today:
            lines.append("TAREAS PENDIENTES PARA HOY:")
            for t in pending_today:
                lines.append(f"- [{t.get('time', 'Sin hora')}] {t.get('title')}")
        else:
            lines.append("TAREAS PENDIENTES PARA HOY: Ninguna tarea pendiente para hoy.")

        # Rutinas
        routines = self.list_routines()
        if routines:
            lines.append("RUTINAS HABITUALES:")
            for r in routines:
                lines.append(f"- {r.get('name')} ({r.get('time')}): {r.get('description')}")

        # Hechos aprendidos
        facts = self.get_facts()
        if facts:
            lines.append("PREFERENCIAS Y HECHOS RECORDADOS:")
            for k, v in facts.items():
                readable_k = k.replace("_", " ").capitalize()
                lines.append(f"- {readable_k}: {v}")

        return "\n".join(lines)


# Instancia única singleton para todo el proceso
_GLOBAL_MEMORY_MANAGER: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Obtiene la instancia global compartida de MemoryManager."""
    global _GLOBAL_MEMORY_MANAGER
    if _GLOBAL_MEMORY_MANAGER is None:
        _GLOBAL_MEMORY_MANAGER = MemoryManager()
    return _GLOBAL_MEMORY_MANAGER
