import json
import os
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.orm import Story, Chapter, Scene, Character, CharacterPose, Background

logger = logging.getLogger(__name__)

class StoryConverter:
    def __init__(self, story_id: str, base_output_dir: str = "backend/services/output"):
        self.story_id = int(story_id) # Ensure int for DB lookup
        self.base_dir = Path(base_output_dir) / str(story_id)
        self.db: Session = SessionLocal()
        
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
        
        # Cache for audio files found on disk
        self.audio_files: List[str] = []

    def load_json(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # logger.warning(f"File not found: {path}") # Reduce noise
            return None
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {path}")
            return None

    def fetch_metadata(self):
        story = self.db.get(Story, self.story_id)
        if not story:
            logger.error(f"Story {self.story_id} not found in database.")
            return False

        # Fetch character voices
        characters = self.db.scalars(
            select(Character).where(Character.story_id == self.story_id)
        ).all()
        voices = {char.name: char.voice_id for char in characters if char.voice_id}

        self.screenplay["metadata"] = {
            "title": story.title,
            "logline": story.logline,
            "author": "AI",
            "version": "1.0",
            # We could fetch main characters names here if needed, but the scene processing handles details
            "style": story.style,
            "voices": voices
        }
        return True

    def fetch_assets(self):
        logger.info("Fetching assets from database...")
        
        # 1. Characters and Poses
        characters = self.db.scalars(
            select(Character).where(Character.story_id == self.story_id)
        ).all()
        
        for char in characters:
            # Store base image if available
            if char.base_image_gcs_path:
                # Key: Character Name (sanitized)
                key = char.name
                self.screenplay["assets"]["characters"][key] = char.base_image_gcs_path
            
            # Store Poses
            for pose in char.poses:
                # Key: "CharacterName_PoseDescription" or just unique ID?
                # The engine likely needs to look up by (Character, Expression)
                # Let's use a composite key or a nested structure if the engine supports it.
                # Based on previous converter, it was flat key -> path.
                # Let's stick to flat key: "Name_Pose"
                # But wait, the detailed scene JSON has "character_pose_expression" which is the description.
                # So we need a way to map (Name, PoseDescription) -> Path.
                
                # Currently the engine might expect "Name_Expression" keys in assets['poses']?
                # Let's map: "Name_PoseDescription" -> Path
                pose_key = f"{char.name}_{pose.pose_description}"
                self.screenplay["assets"]["poses"][pose_key] = pose.image_gcs_path

        # 2. Backgrounds
        backgrounds = self.db.scalars(
            select(Background).where(Background.story_id == self.story_id)
        ).all()
        
        for bg in backgrounds:
            # Key: Background Name
            self.screenplay["assets"]["backgrounds"][bg.name] = bg.image_gcs_path

        # 3. Audio (Scan directory)
        audio_dir = self.base_dir / "audio"
        if audio_dir.exists():
            for file_path in audio_dir.glob("*.wav"): # Scan for wav, maybe mp3 too
                relative_path = file_path.relative_to(self.base_dir).as_posix()
                self.audio_files.append(relative_path)
                # Also add to assets map for reference by filename
                self.screenplay["assets"]["audio"][file_path.name] = relative_path
            
            # Also scan mp3/ogg if needed
            for ext in ["*.mp3", "*.ogg"]:
                 for file_path in audio_dir.glob(ext):
                    relative_path = file_path.relative_to(self.base_dir).as_posix()
                    self.audio_files.append(relative_path)
                    self.screenplay["assets"]["audio"][file_path.name] = relative_path

    def build_story(self):
        logger.info("Building story structure from database...")
        
        # Fetch chapters
        chapters = self.db.scalars(
            select(Chapter)
            .where(Chapter.story_id == self.story_id)
            .order_by(Chapter.sequence_number)
        ).all()
        
        for chapter in chapters:
            logger.info(f"Processing chapter: {chapter.title}")
            
            chapter_data = {
                "id": chapter.chapter_cid,
                "title": chapter.title,
                "order": chapter.sequence_number,
                "scenes": []
            }
            
            # Fetch Scenes
            scenes = self.db.scalars(
                select(Scene)
                .where(Scene.chapter_id == chapter.id)
                .order_by(Scene.sequence_number)
            ).all()
            
            for scene in scenes:
                logger.info(f"  Processing scene: {scene.title}")
                
                # Construct Scene Content
                # The Scene object has JSON fields: dialogue_content, choices_content, location_changes
                
                # We need to structure this into the "content" block the engine expects
                # If we have detailed content in DB, use it.
                
                content = {}
                if scene.dialogue_content:
                    # 1. Main Dialogue
                    content["main_dialogue"] = scene.dialogue_content
                    
                    # Match with existing audio files if present
                    # Workflow saves them as {scene_id}_{dialogue_id}.wav
                    for line in content.get("main_dialogue", []):
                        expected_filename = f"{scene.scene_sid}_{line.get('dialogue_id')}.wav"
                        expected_filename2 = f"None_{line.get('dialogue_id')}.wav"
                        if expected_filename in self.screenplay["assets"]["audio"]:
                            line["audio_key"] = expected_filename
                        if expected_filename2 in self.screenplay["assets"]["audio"]:
                            line["audio_key"] = expected_filename2

                    # 2. Choices
                    if scene.choices_content:
                        content["choices_and_branches"] = scene.choices_content
                        
                    # 3. Location Changes
                    if scene.location_changes:
                        content["mid_scene_location_changes"] = scene.location_changes
                    
                    # 4. Initial State
                    content["initial_location_name"] = scene.initial_location_name
                    content["initial_location_description"] = scene.initial_location_description
                    content["initial_bgm"] = scene.initial_bgm

                else:
                    # Fallback to summary if no detailed content
                    content = {
                        "text": scene.scene_summary,
                        "is_placeholder": True
                    }

                scene_entry = {
                    "id": scene.scene_sid,
                    "title": scene.title,
                    "summary": scene.scene_summary,
                    "content": content
                }
                
                chapter_data["scenes"].append(scene_entry)
            
            self.screenplay["story"]["chapters"].append(chapter_data)

    def convert(self):
        logger.info(f"Starting database conversion for story {self.story_id}...")
        
        if not self.fetch_metadata():
            return

        self.fetch_assets()
        self.build_story()
        
        # Save Screenplay
        output_path = self.base_dir / "screenplay.json"
        
        # Ensure directory exists (it should if story exists)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.screenplay, f, indent=2, default=str)
        
        logger.info(f"Screenplay generated at: {output_path}")
        return str(output_path)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert story from DB to screenplay.json")
    parser.add_argument("story_id", help="ID of the story to convert")
    parser.add_argument("--base_dir", default="output", help="Base directory for story outputs")
    
    args = parser.parse_args()
    
    converter = StoryConverter(args.story_id, args.base_dir)
    converter.convert()
