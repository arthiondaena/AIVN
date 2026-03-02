from pathlib import Path
from typing import Dict, Any, Tuple
import os

class SettingsKeeper:
    """
    Manages game configuration and settings.
    Based on Source_code/Application/Assets/Scripts/Core/Settings_Keeper.py
    """
    def __init__(self):
        self._game_settings: Dict[str, Any] = {
            "screen_size": (1280, 720),
            "screen_type": "windowed",
            "general_volume": 100,
            "music_volume": 100,
            "sound_volume": 100,
            "text_language": "eng",
            "voice_acting_language": "eng",
            "frames_per_second": 60,
            "window_title": "AI Visual Novel Engine"
        }
        # In a real app, load from file here

    def get_window_size(self) -> Tuple[int, int]:
        return self._game_settings["screen_size"]

    def get_frames_per_second(self) -> int:
        return self._game_settings["frames_per_second"]
        
    def get_window_title(self) -> str:
        return self._game_settings["window_title"]
        
    def get_text_language(self) -> str:
        return self._game_settings["text_language"]

# Singleton instance
settings = SettingsKeeper()
