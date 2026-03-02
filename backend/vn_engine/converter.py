import json
import os
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional

class StoryConverter:
    def __init__(self, story_id: str, base_output_dir: str = "backend/services/output"):
        self.story_id = story_id
        self.base_dir = Path(base_output_dir) / str(story_id)
        self.screenplay: Dict[str, Any] = {
            "metadata": {},
            "assets": {
                "characters": {},
                "backgrounds": {},
                "audio": {},
                "poses": {}
            },
            "story": {
                "chapters": []
            }
        }

    def load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: File not found: {path}")
            return None
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {path}")
            return None

    def scan_assets(self, asset_type: str, extensions: List[str]):
        asset_dir = self.base_dir / asset_type
        if not asset_dir.exists():
            return

        for ext in extensions:
            for file_path in asset_dir.glob(f"*{ext}"):
                # Key is the filename without extension, or potentially part of the filename
                # For characters/backgrounds, using filename (minus ext) as key seems appropriate
                # For audio, filename matches dialogue_id presumably
                key = file_path.stem
                # Store relative path from base_dir for portability
                relative_path = file_path.relative_to(self.base_dir).as_posix()
                self.screenplay["assets"][asset_type][key] = relative_path

    def build_metadata(self):
        outline_path = self.base_dir / "story_outline.json"
        outline = self.load_json(outline_path)
        if not outline:
            return

        self.screenplay["metadata"] = {
            "title": outline.get("title", ""),
            "logline": outline.get("logline", ""),
            "author": "AI", # Placeholder or extract if available
            "version": "1.0",
            "main_characters": outline.get("main_characters", [])
        }
        return outline

    def build_story(self, outline: Dict[str, Any]):
        chapters_meta = outline.get("main_chapters", [])
        
        for index, chapter_meta in enumerate(chapters_meta):
            chapter_id = chapter_meta.get("chapter_id")
            chapter_title = chapter_meta.get("title")
            
            print(f"Processing chapter: {chapter_id}")

            chapter_data = {
                "id": chapter_id,
                "title": chapter_title,
                "order": index + 1,
                "scenes": []
            }

            # Load chapter scenes list
            chapter_scenes_path = self.base_dir / "chapters" / f"{chapter_id}_scenes.json"
            chapter_scenes_data = self.load_json(chapter_scenes_path)

            if chapter_scenes_data and "scenes" in chapter_scenes_data:
                for scene_meta in chapter_scenes_data["scenes"]:
                    scene_id = scene_meta.get("scene_id")
                    print(f"  Processing scene: {scene_id}")
                    
                    scene_entry = {
                        "id": scene_id,
                        "title": scene_meta.get("title"),
                        "summary": scene_meta.get("scene_summary"), # Keep summary at top level for easy access
                        "content": None
                    }

                    # Try to load detailed scene
                    detailed_scene_path = self.base_dir / "scenes" / f"{scene_id}_detailed.json"
                    detailed_scene = self.load_json(detailed_scene_path)

                    if detailed_scene:
                        scene_entry["content"] = detailed_scene
                    else:
                        print(f"    Detailed scene not found for {scene_id}, using placeholder.")
                        scene_entry["content"] = {
                            "scene_id": scene_id,
                            "text": scene_meta.get("scene_summary"),
                            "is_placeholder": True
                        }

                    chapter_data["scenes"].append(scene_entry)
            
            self.screenplay["story"]["chapters"].append(chapter_data)

    def convert(self):
        print(f"Starting conversion for story {self.story_id}...")
        
        # 1. Build Metadata
        outline = self.build_metadata()
        if not outline:
            print("Failed to load story outline. Aborting.")
            return

        # 2. Scan Assets
        self.scan_assets("characters", [".png", ".jpg", ".webp"])
        self.scan_assets("backgrounds", [".png", ".jpg", ".webp"])
        self.scan_assets("audio", [".wav", ".mp3", ".ogg"])
        self.scan_assets("poses", [".png", ".jpg", ".webp"])

        # 3. Build Story Structure
        self.build_story(outline)

        # 4. Save Screenplay
        output_path = self.base_dir / "screenplay.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.screenplay, f, indent=2)
        
        print(f"Screenplay generated at: {output_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert story files to screenplay.json")
    parser.add_argument("story_id", help="ID of the story to convert")
    parser.add_argument("--base_dir", default="backend/services/output", help="Base directory for story outputs")
    
    args = parser.parse_args()
    
    converter = StoryConverter(args.story_id, args.base_dir)
    converter.convert()
