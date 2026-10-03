"""LYAXIS labs™ System & Memory Tools Package"""
from tools.system_tools import (
    play_music,
    play_spotify,
    play_youtube,
    search_youtube,
    open_url,
    launch_application,
    control_media,
    system_info,
    write_note,
    AVAILABLE_TOOLS as SYSTEM_TOOLS
)
from tools.memory_tools import (
    add_user_task,
    set_user_routine,
    remember_fact,
    list_user_tasks,
    complete_user_task,
    delete_user_task,
    MEMORY_TOOLS
)

ALL_TOOLS = {**SYSTEM_TOOLS, **MEMORY_TOOLS}

__all__ = [
    "play_music", "play_spotify", "play_youtube", "search_youtube",
    "open_url", "launch_application", "control_media", "system_info",
    "write_note", "add_user_task", "set_user_routine", "remember_fact",
    "list_user_tasks", "complete_user_task", "delete_user_task", "ALL_TOOLS"
]

