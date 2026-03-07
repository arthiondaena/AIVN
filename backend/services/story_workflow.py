import json
import os
import uuid
import logging
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.config import settings
from core.orm import Story, Chapter, Scene, Character, CharacterPose, Background
from services.genai_services import GenAIClient
from models.story_outline_models import MainStoryOutline
from models.story_detailed_models import SceneElaborator
from utils.voices_list import male as male_voices, female as female_voices
from utils.removebg import remove_background_v2_batch
from PIL import Image
import io
from thefuzz import process

logger = logging.getLogger(__name__)

VOICES = {
    "male": male_voices,
    "female": female_voices
}

class StoryWorkflowService:
    def __init__(self, db: Session):
        self.db = db
        self.genai_client = GenAIClient()
        self.output_dir = "output" # Base output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        # Cache for character voices within a session/run
        self.character_voices = {}

    def get_storage_path(self, story_id, category, filename):
        # Create folder structure: {story_id}/{category}/filename
        # category: "characters", "backgrounds", "audio", "poses"
        relative_path = os.path.join(str(story_id), category, filename)
        full_path = os.path.join(self.output_dir, relative_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path, relative_path

    def save_image(self, image_data, story_id, category, filename):
        full_path, relative_path = self.get_storage_path(story_id, category, filename)
        
        if hasattr(image_data, 'save'):
            image_data.save(full_path)
        else:
            with open(full_path, "wb") as f:
                f.write(image_data)
        
        # Return relative path to simulate GCS key or full local path if needed.
        # For DB, we usually store the GCS key/URL. Here returning relative path as "key".
        return relative_path

    def save_json(self, data, story_id, category, filename):
        full_path, relative_path = self.get_storage_path(story_id, category, filename)
        
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, default=str)
        
        return relative_path

    async def generate_full_story(self, synopsis: str, style: str):
        logger.info("Starting story generation...")
        
        # 1. Generate Main Story Outline
        outline_data = await self.genai_client.generate_story_structure(synopsis, style)
        
        story = Story(
            title=outline_data.get("title"),
            logline=outline_data.get("logline"),
            original_text=synopsis,
            style=style
        )
        self.db.add(story)
        self.db.commit()
        self.db.refresh(story)
        
        self.save_json(outline_data, story.id, "", "story_outline.json")

        # 2. Generate Base Characters
        await self._generate_characters(story.id, outline_data.get("main_characters", []), style)
        
        # 3. Create Chapter Outline & Scenes
        await self._generate_chapters(story.id, outline_data.get("main_chapters", []), style)
        
        return story

    async def _generate_characters(self, story_id, characters_data, style):
        logger.info(f"Generating {len(characters_data)} characters...")
        used_voices = set()

        for char_data in characters_data:
            # Generate base image (neutral pose)
            description = char_data.get("appearance")
            image = await self.genai_client.generate_character_image(description, style, pose="Neutral, standing")
            
            image_filename = f"{char_data.get('name').replace(' ', '_')}_base.png"
            image_path = ""
            if image:
                # story_id/characters/filename
                image_path = self.save_image(image, story_id, "characters", image_filename)
                
                # Create transparent version
                # try:
                #     transparent_images = remove_background_v2_batch([image])
                #     if transparent_images:
                #         trans_filename = f"{char_data.get('name').replace(' ', '_')}_base_transparent.png"
                #         self.save_image(transparent_images[0], story_id, "characters", trans_filename)
                # except Exception as e:
                #     logger.error(f"Failed to generate transparent image for {char_data.get('name')}: {e}")
            
            # Assign voice
            gender = char_data.get("gender", "female").lower()
            voice_options = VOICES.get(gender, VOICES["female"])
            # Simple round-robin or first available
            selected_voice = next((v for v in voice_options if v not in used_voices), voice_options[0])
            used_voices.add(selected_voice)
            
            character = Character(
                story_id=story_id,
                name=char_data.get("name"),
                role=char_data.get("role"),
                gender=gender,
                voice_id=selected_voice,
                description=description,
                base_image_gcs_path=image_path
            )
            self.db.add(character)
            self.db.commit() 
            self.db.refresh(character)
            
            # Add base image as the first pose
            if image_path:
                base_pose = CharacterPose(
                    character_id=character.id,
                    pose_description="Neutral, standing",
                    image_gcs_path=image_path
                )
                self.db.add(base_pose)
                self.db.commit()

            # Generate the list of poses for this character
            logger.info(f"Generating pose list for {character.name}...")
            pose_set = await self.genai_client.generate_character_pose_list(
                character.name, character.role, character.description, style
            )
            
            # Pre-generate all poses
            for pose_desc in pose_set.get("poses", []):
                logger.info(f"Pre-generating pose: {pose_desc} for {character.name}")
                await self._get_or_create_character_pose(character, pose_desc, style, story_id)

            self.character_voices[character.id] = selected_voice
            logger.info(f"Assigned voice {selected_voice} to {character.name}")

    async def _generate_chapters(self, story_id, chapters_data, style):
        logger.info(f"Generating {len(chapters_data)} chapters...")
        
        for i, chap_data in enumerate(chapters_data):
            chapter = Chapter(
                story_id=story_id,
                chapter_cid=chap_data.get("chapter_id"),
                title=chap_data.get("title"),
                primary_location=chap_data.get("primary_location"),
                plot_summary=chap_data.get("plot_summary"),
                sequence_number=i + 1
            )
            self.db.add(chapter)
            self.db.commit()
            self.db.refresh(chapter)
            
            # Generate Scenes for this chapter
            scene_breakdown = await self.genai_client.generate_chapter_scenes(
                chapter.chapter_cid, chapter.title, chapter.plot_summary, style
            )
            
            self.save_json(scene_breakdown, story_id, "chapters", f"{chapter.chapter_cid}_scenes.json")

            for j, scene_data in enumerate(scene_breakdown.get("scenes", [])):
                scene = Scene(
                    chapter_id=chapter.id,
                    scene_sid=scene_data.get("scene_id"),
                    title=scene_data.get("title"),
                    primary_location=scene_data.get("primary_location"),
                    scene_summary=scene_data.get("scene_summary"),
                    sequence_number=j + 1
                )
                self.db.add(scene)
                self.db.commit()
                self.db.refresh(scene)
                
                # 4. Elaborate Scene
                # Only generate audio for the very first scene of the first chapter
                generate_audio = (i == 0 and j == 0)
                await self._elaborate_scene(scene, style, generate_audio)

    async def _elaborate_scene(self, scene: Scene, style: str, generate_audio: bool = False):
        logger.info(f"Elaborating scene {scene.scene_sid}...")
        
        story_chars = self.db.scalars(
            select(Character).where(Character.story_id == scene.chapter.story_id)
        ).all()
        
        # Format character information with available poses
        char_info_list = []
        for char in story_chars:
            poses = [p.pose_description for p in char.poses]
            char_info = f"Name: {char.name}\nRole: {char.role}\nAvailable Poses: {', '.join(poses)}"
            char_info_list.append(char_info)
        
        characters_info = "\n\n".join(char_info_list)
        
        detailed_scene_data = await self.genai_client.elaborate_scene(
            scene.scene_sid, scene.title, scene.scene_summary, scene.primary_location, characters_info, style
        )
        
        self.save_json(detailed_scene_data, scene.chapter.story_id, "scenes", f"{scene.scene_sid}_detailed.json")

        # Save detailed content
        scene.initial_location_name = detailed_scene_data.get("initial_location_name")
        scene.initial_location_description = detailed_scene_data.get("initial_location_description")
        scene.initial_bgm = detailed_scene_data.get("initial_bgm")
        scene.dialogue_content = detailed_scene_data.get("main_dialogue") 
        scene.choices_content = detailed_scene_data.get("choices_and_branches")
        scene.location_changes = detailed_scene_data.get("mid_scene_location_changes")
        
        self.db.commit()
        
        # 6. Generate Background
        await self._get_or_create_background(
            scene.chapter.story_id, 
            scene.initial_location_name, 
            scene.initial_location_description, 
            style
        )
        
        # 5. Process Characters (Poses & Voice Mapping Prep)
        dialogue_lines = detailed_scene_data.get("main_dialogue", [])
        
        # Pre-calculate voice map for the scene
        voice_map = {}
        for char in story_chars:
            if char.voice_id:
                voice_map[char.name] = char.voice_id
            elif char.id in self.character_voices:
                voice_map[char.name] = self.character_voices[char.id]
        
        # Process poses for characters appearing in the scene
        # We iterate to ensure poses exist, even if we don't generate audio
        for line in dialogue_lines:
            speaker_name = line.get("speaker")
            pose = line.get("character_pose_expression")
            
            if speaker_name != "Narrator":
                character = next((c for c in story_chars if c.name == speaker_name), None)
                if character and pose:
                    await self._get_or_create_character_pose(character, pose, style, scene.chapter.story_id, create_if_missing=False)

        # 8. Generate Audio (Only if requested)
        if generate_audio:
            logger.info(f"Generating full audio for scene {scene.scene_sid}...")
            
            def get_audio_path(filename):
                full_path, _ = self.get_storage_path(scene.chapter.story_id, "audio", filename)
                return full_path

            await self.genai_client.generate_scene_audio(
                detailed_scene_data,
                voice_map,
                get_audio_path
            )

    async def _get_or_create_character_pose(self, character: Character, pose_description: str, style: str, story_id: int, create_if_missing: bool = True):
        # Check for exact match first
        existing_exact = self.db.scalars(
             select(CharacterPose).where(CharacterPose.character_id == character.id, CharacterPose.pose_description == pose_description)
        ).first()
        
        if existing_exact:
            return existing_exact

        # Check for similar pose using fuzzy match
        all_poses = self.db.scalars(
            select(CharacterPose).where(CharacterPose.character_id == character.id)
        ).all()
        
        if all_poses:
            pose_dict = {p.pose_description: p for p in all_poses}
            best_match_desc, score = process.extractOne(pose_description, pose_dict.keys())
            
            # If we are NOT allowed to create new poses, return the best match
            if not create_if_missing:
                logger.info(f"Fuzzy matching: '{pose_description}' -> '{best_match_desc}' (score: {score})")
                return pose_dict[best_match_desc]
            
            # If allowed to create but high score match exists (> 90), reuse it
            if score > 90:
                logger.info(f"Fuzzy matching (high score): '{pose_description}' -> '{best_match_desc}' (score: {score})")
                return pose_dict[best_match_desc]

        if not create_if_missing:
             return None
            
        # Get base image path for reference (if local file exists)
        reference_path = None
        if character.base_image_gcs_path:
             # Construct full path from stored relative path
             reference_path = os.path.join(self.output_dir, character.base_image_gcs_path)

        # Generate Image
        image = await self.genai_client.generate_character_image(
            character.description, 
            style, 
            pose=pose_description, 
            reference_image_path=reference_path,
            model=settings.POSE_MODEL
        )
        if image:
            base_filename = f"pose_{character.id}_{uuid.uuid4().hex[:8]}"
            filename = f"{base_filename}.png"
            # story_id/poses/filename
            path = self.save_image(image, story_id, "poses", filename)

            pil_image = Image.open(io.BytesIO(image.image_bytes))
            
            # Create transparent version
            try:
                transparent_images = remove_background_v2_batch([pil_image])
                if transparent_images:
                    trans_filename = f"{base_filename}_transparent.png"
                    self.save_image(transparent_images[0], story_id, "poses", trans_filename)
            except Exception as e:
                logger.error(f"Failed to generate transparent pose image: {e}")
            
            new_pose = CharacterPose(
                character_id=character.id,
                pose_description=pose_description,
                image_gcs_path=path
            )
            self.db.add(new_pose)
            self.db.commit()
            return new_pose
        return None

    async def _get_or_create_background(self, story_id, name, description, style):
        bg = self.db.scalars(
            select(Background)
            .where(Background.story_id == story_id)
            .where(Background.name == name)
        ).first()
        
        if bg:
            return bg
            
        # Generate
        image = await self.genai_client.generate_background_image(description, style)
        if image:
            filename = f"{name.replace(' ', '_')}.png"
            path = self.save_image(image, story_id, "backgrounds", filename)
            
            bg = Background(
                story_id=story_id,
                name=name,
                description=description,
                image_gcs_path=path
            )
            self.db.add(bg)
            self.db.commit()
            return bg
        return None

if __name__ == "__main__":
    # Example usage
    from core.database import SessionLocal
    db = SessionLocal()
    
    workflow = StoryWorkflowService(db)
    
    synopsis = "In a world where dreams can be shared, a young dreamer discovers they can enter others' dreams and must navigate a surreal landscape to save their loved ones."
    synopsis = "Create a simple 1 chapter story with 2 main characters. The story should be a romantic comedy set in a high school. The main characters are a shy bookworm and a popular athlete who are forced to work together on a school project. They start off disliking each other but eventually fall in love. Include some humorous situations and heartfelt moments."
    style = "anime"
    asyncio.run(workflow.generate_full_story(synopsis, style))