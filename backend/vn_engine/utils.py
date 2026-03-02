import pygame
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os

class AssetLoader:
    """
    Responsible for loading assets (images, sounds, fonts, json).
    Based on Source_code/Application/Assets/Scripts/Universal_computing/Assets_load.py
    """
    def __init__(self, base_path: str = "backend/services/output"):
        self.base_path = Path(base_path)
        self._font_cache: Dict[str, pygame.font.Font] = {}
        self._image_cache: Dict[str, pygame.Surface] = {}
        
    def set_base_path(self, path: str):
        self.base_path = Path(path)

    def load_json(self, relative_path: str) -> Dict[str, Any]:
        full_path = self.base_path / relative_path
        if not full_path.exists():
            print(f"Warning: JSON file not found: {full_path}")
            return {}
            
        with open(full_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_image(self, relative_path: str, convert_alpha: bool = True) -> Optional[pygame.Surface]:
        if relative_path in self._image_cache:
            return self._image_cache[relative_path]
            
        full_path = self.base_path / relative_path
        if not full_path.exists():
            # Try finding it relative to project root if not in output dir
            # Or just warn
            print(f"Warning: Image file not found: {full_path}")
            return None

        try:
            image = pygame.image.load(str(full_path))
            if convert_alpha:
                image = image.convert_alpha()
            else:
                image = image.convert()
            self._image_cache[relative_path] = image
            return image
        except pygame.error as e:
            print(f"Error loading image {full_path}: {e}")
            return None

    def load_font(self, font_name: Optional[str], size: int) -> pygame.font.Font:
        key = f"{font_name}_{size}"
        if key in self._font_cache:
            return self._font_cache[key]
            
        if font_name:
            full_path = self.base_path / "fonts" / font_name
            if full_path.exists():
                font = pygame.font.Font(str(full_path), size)
            else:
                # Fallback to system/default
                font = pygame.font.Font(None, size)
        else:
            font = pygame.font.Font(None, size)
            
        self._font_cache[key] = font
        return font
