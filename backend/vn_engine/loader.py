import json
from pathlib import Path
from typing import Dict, Any, Optional, List

class StoryLoader:
    def __init__(self, screenplay_path: str):
        self.screenplay_path = Path(screenplay_path)
        self.data = self._load_screenplay()
        self.base_dir = self.screenplay_path.parent

    def _load_screenplay(self) -> Dict[str, Any]:
        if not self.screenplay_path.exists():
            raise FileNotFoundError(f"Screenplay file not found: {self.screenplay_path}")
        
        with open(self.screenplay_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.data.get("metadata", {})

    @property
    def title(self) -> str:
        return self.metadata.get("title", "Untitled Story")

    def get_asset_path(self, asset_type: str, key: str) -> Optional[str]:
        """
        Get the full path to an asset.
        asset_type: 'characters', 'backgrounds', 'audio', 'poses'
        key: The key used in the assets dictionary (usually filename without ext)
        """
        assets = self.data.get("assets", {})
        type_assets = assets.get(asset_type, {})
        relative_path = type_assets.get(key)
        
        if relative_path:
            return str(self.base_dir / relative_path)
        return None

    def get_chapters(self) -> List[Dict[str, Any]]:
        return self.data.get("story", {}).get("chapters", [])

    def get_chapter(self, chapter_id: str) -> Optional[Dict[str, Any]]:
        for chapter in self.get_chapters():
            if chapter.get("id") == chapter_id:
                return chapter
        return None

    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        for chapter in self.get_chapters():
            for scene in chapter.get("scenes", []):
                if scene.get("id") == scene_id:
                    return scene
        return None

    def get_scene_content(self, scene_id: str) -> Optional[Dict[str, Any]]:
        scene = self.get_scene(scene_id)
        if scene:
            return scene.get("content")
        return None

    def get_first_scene(self) -> Optional[Dict[str, Any]]:
        chapters = self.get_chapters()
        if chapters:
            first_chapter = chapters[0]
            scenes = first_chapter.get("scenes", [])
            if scenes:
                return scenes[0]
        return None
