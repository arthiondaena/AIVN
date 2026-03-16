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
import re
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
        
        self.semaphore = asyncio.Semaphore(5)
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

    async def generate_story_outline_only(self, synopsis: str, style: str):
        logger.info("Generating Main Story Outline only...")
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

        # Generate All Characters (Main + Side) base images only
        main_characters = outline_data.get("main_characters", [])
        side_characters = outline_data.get("side_characters", [])
        
        # await self._generate_characters_base_only(story.id, main_characters, style, is_side=False)
        # await self._generate_characters_base_only(story.id, side_characters, style, is_side=True)
        
        return story, outline_data

    async def _generate_characters_base_only(self, story_id, characters_data, style, is_side: bool = False):
        logger.info(f"Generating base images for {len(characters_data)} {'side' if is_side else 'main'} characters...")
        used_voices = set()
        char_tasks = []

        for char_data in characters_data:
            gender = char_data.get("gender", "female").lower()
            voice_options = VOICES.get(gender, VOICES["female"])
            selected_voice = next((v for v in voice_options if v not in used_voices), voice_options[0])
            used_voices.add(selected_voice)
            
            description = char_data.get("appearance")
            character = Character(
                story_id=story_id,
                name=char_data.get("name"),
                role=char_data.get("role"),
                gender=gender,
                voice_id=selected_voice,
                description=description,
                base_image_gcs_path=""
            )
            self.db.add(character)
            self.db.commit() 
            self.db.refresh(character)
            self.character_voices[character.id] = selected_voice

            async def process_character(char_obj):
                async with self.semaphore:
                    model_to_use = settings.IMAGE_MODEL if is_side else settings.IMAGE_MODEL_MAIN
                    image = await self.genai_client.generate_character_image(char_obj.description, style, pose="Neutral, standing", model=model_to_use, fallback_model=settings.IMAGE_MODEL)
                
                if image:
                    image_path = self.save_image(image, story_id, str(char_obj.id), "base.png")
                    char_obj.base_image_gcs_path = image_path
                    self.db.commit()
                    
                    base_pose = CharacterPose(
                        character_id=char_obj.id,
                        pose_description="Neutral, standing",
                        image_gcs_path=image_path
                    )
                    self.db.add(base_pose)
                    self.db.commit()

            char_tasks.append(process_character(character))

        await asyncio.gather(*char_tasks)

    async def update_story_outline(self, story_id: int, outline_data: dict):
        story = self.db.scalars(select(Story).where(Story.id == story_id)).first()
        if not story:
            return None
        
        if "style" in outline_data:
            story.style = outline_data["style"]
            
        self.save_json(outline_data, story.id, "", "story_outline.json")
        self.db.commit()
        return story

    async def regenerate_character_image(self, story_id: int, character_id: int, new_appearance: str, style: str):
        char_obj = self.db.scalars(
            select(Character).where(Character.id == character_id, Character.story_id == story_id)
        ).first()
        if not char_obj:
            return None
            
        char_obj.description = new_appearance
        self.db.commit()
        
        async with self.semaphore:
            image = await self.genai_client.generate_character_image(char_obj.description, style, pose="Neutral, standing")
            
        if image:
            image_path = self.save_image(image, story_id, str(char_obj.id), "base.png")
            char_obj.base_image_gcs_path = image_path
            self.db.commit()
            
            # Update the existing base pose path
            base_pose = self.db.scalars(
                select(CharacterPose).where(
                    CharacterPose.character_id == char_obj.id,
                    CharacterPose.pose_description == "Neutral, standing"
                )
            ).first()
            if base_pose:
                base_pose.image_gcs_path = image_path
                self.db.commit()
            
        return char_obj

    async def generate_story_pipeline(self, story_id: int):
        story = self.db.scalars(select(Story).where(Story.id == story_id)).first()
        if not story:
            return None
            
        # load outline
        outline_path = os.path.join(self.output_dir, str(story_id), "story_outline.json")
        with open(outline_path, "r", encoding="utf-8") as f:
            outline_data = json.load(f)
            
        # 1. Generate poses for existing characters
        characters = self.db.scalars(select(Character).where(Character.story_id == story_id)).all()
        
        # Populate cache
        for c in characters:
            if c.voice_id:
                self.character_voices[c.id] = c.voice_id
        
        pose_tasks = []
        for char_obj in characters:
            async def process_poses(c_obj):
                is_side_char = c_obj.role.lower() not in ["protagonist", "main character"] if c_obj.role else True
                pose_count = settings.SIDE_CHAR_POSE_COUNT if is_side_char else settings.MAIN_CHAR_POSE_COUNT
                async with self.semaphore:
                    pose_set = await self.genai_client.generate_character_pose_list(
                        c_obj.name, c_obj.role, c_obj.description, story.style, pose_count=pose_count
                    )
                c_pose_tasks = []
                for pose_desc in pose_set.get("poses", []):
                    c_pose_tasks.append(self._get_or_create_character_pose(c_obj, pose_desc, story.style, story_id))
                await asyncio.gather(*c_pose_tasks)
            pose_tasks.append(process_poses(char_obj))
            
        await asyncio.gather(*pose_tasks)
        
        # 2. Generate Chapters and Scenes
        main_chapters = outline_data.get("main_chapters", [])
        await self._generate_chapters(story.id, main_chapters, story.style, outline_data)
        
        return story

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

        # 2. Generate All Characters (Main + Side)
        main_characters = outline_data.get("main_characters", [])
        side_characters = outline_data.get("side_characters", [])
        
        await self._generate_characters(story.id, main_characters, style, is_side=False)
        await self._generate_characters(story.id, side_characters, style, is_side=True)
        
        # 3. Create Chapter Outline & Scenes
        await self._generate_chapters(story.id, outline_data.get("main_chapters", []), style, outline_data)
        
        return story

    async def _generate_characters(self, story_id, characters_data, style, is_side: bool = False):
        logger.info(f"Generating {len(characters_data)} {'side' if is_side else 'main'} characters...")
        used_voices = set()
        char_tasks = []

        # Pre-assign voices and create records sequentially to ensure IDs are available
        for char_data in characters_data:
            gender = char_data.get("gender", "female").lower()
            voice_options = VOICES.get(gender, VOICES["female"])
            selected_voice = next((v for v in voice_options if v not in used_voices), voice_options[0])
            used_voices.add(selected_voice)
            
            description = char_data.get("appearance")
            character = Character(
                story_id=story_id,
                name=char_data.get("name"),
                role=char_data.get("role"),
                gender=gender,
                voice_id=selected_voice,
                description=description,
                base_image_gcs_path=""
            )
            self.db.add(character)
            self.db.commit() 
            self.db.refresh(character)
            self.character_voices[character.id] = selected_voice

            async def process_character(char_obj, char_info, is_side_char):
                # Generate base image
                async with self.semaphore:
                    model_to_use = settings.IMAGE_MODEL if is_side_char else settings.IMAGE_MODEL_MAIN
                    image = await self.genai_client.generate_character_image(char_obj.description, style, pose="Neutral, standing", model=model_to_use, fallback_model=settings.IMAGE_MODEL)
                
                image_path = ""
                if image:
                    image_path = self.save_image(image, story_id, str(char_obj.id), "base.png")
                    char_obj.base_image_gcs_path = image_path
                    self.db.commit()
                    
                    base_pose = CharacterPose(
                        character_id=char_obj.id,
                        pose_description="Neutral, standing",
                        image_gcs_path=image_path
                    )
                    self.db.add(base_pose)
                    self.db.commit()

                # Generate pose list
                logger.info(f"Generating pose list for {char_obj.name}...")
                pose_count = settings.SIDE_CHAR_POSE_COUNT if is_side_char else settings.MAIN_CHAR_POSE_COUNT
                async with self.semaphore:
                    pose_set = await self.genai_client.generate_character_pose_list(
                        char_obj.name, char_obj.role, char_obj.description, style, pose_count=pose_count
                    )
                
                # Pre-generate all poses in parallel
                pose_tasks = []
                for pose_desc in pose_set.get("poses", []):
                    pose_tasks.append(self._get_or_create_character_pose(char_obj, pose_desc, style, story_id))
                
                await asyncio.gather(*pose_tasks)
                logger.info(f"Finished generating all assets for {char_obj.name}")

            char_tasks.append(process_character(character, char_data, is_side))

        await asyncio.gather(*char_tasks)

    async def _generate_chapters(self, story_id, chapters_data, style, outline_data):
        logger.info(f"Generating {len(chapters_data)} chapters...")
        
        # Pre-generate backgrounds from outline data if any
        available_backgrounds = outline_data.get("available_backgrounds", [])
        bg_tasks = []
        for bg in available_backgrounds:
            bg_tasks.append(self._get_or_create_background(story_id, bg.get("name"), bg.get("description"), style))
        await asyncio.gather(*bg_tasks)
        
        # Format backgrounds for prompt
        bg_info_list = [f"- {bg.get('name')}: {bg.get('description')}" for bg in available_backgrounds]
        available_backgrounds_str = "\n".join(bg_info_list) if bg_info_list else "None explicitly listed."
        
        chapter_tasks = []
        
        # Create chapter records first
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

            async def process_chapter(chap_obj, chap_info):
                # 1. Generate Chapter Scenes
                async with self.semaphore:
                    scene_breakdown = await self.genai_client.generate_chapter_scenes(
                        chap_obj.chapter_cid, chap_obj.title, chap_obj.plot_summary, style, available_backgrounds_str
                    )
                
                self.save_json(scene_breakdown, story_id, "chapters", f"{chap_obj.chapter_cid}_scenes.json")

                # 2. Create Scene records
                scene_tasks = []
                for j, scene_data in enumerate(scene_breakdown.get("scenes", [])):
                    scene = Scene(
                        chapter_id=chap_obj.id,
                        scene_sid=scene_data.get("scene_id"),
                        title=scene_data.get("title"),
                        primary_location=scene_data.get("primary_location"),
                        scene_summary=scene_data.get("scene_summary"),
                        sequence_number=j + 1
                    )
                    self.db.add(scene)
                    self.db.commit()
                    self.db.refresh(scene)
                    
                    # 4. Elaborate Scene (only first scene first chapter gets audio)
                    generate_audio = (chap_obj.sequence_number == 1 and j == 0)
                    scene_tasks.append(self._elaborate_scene(scene, style, generate_audio, available_backgrounds=available_backgrounds_str))
                
                await asyncio.gather(*scene_tasks)

            chapter_tasks.append(process_chapter(chapter, chap_data))
        
        await asyncio.gather(*chapter_tasks)

    async def _elaborate_scene(self, scene: Scene, style: str, generate_audio: bool = False, available_backgrounds: str = ""):
        logger.info(f"Elaborating scene {scene.scene_sid}...")
        
        story_chars = self.db.scalars(
            select(Character).where(Character.story_id == scene.chapter.story_id)
        ).all()
        
        # Format character information with available poses
        char_info_list = []
        for char in story_chars:
            poses = [p.pose_description for p in char.poses]
            char_info = f"Name: {char.name}\nRole: {char.role}\nAvailable Poses: {'; '.join(poses)}"
            char_info_list.append(char_info)
        
        characters_info = "\n\n".join(char_info_list)
        
        async with self.semaphore:
            detailed_scene_data = await self.genai_client.elaborate_scene(
                scene.scene_sid, scene.title, scene.scene_summary, scene.primary_location, characters_info, style, available_backgrounds
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
        
        # Process poses for characters appearing in the scene in parallel
        pose_ensure_tasks = []
        for line in dialogue_lines:
            speaker_name = line.get("speaker")
            pose = line.get("character_pose_expression")
            
            if speaker_name != "Narrator":
                character = next((c for c in story_chars if c.name == speaker_name), None)
                if character and pose:
                    pose_ensure_tasks.append(self._get_or_create_character_pose(character, pose, style, scene.chapter.story_id, create_if_missing=False))

        await asyncio.gather(*pose_ensure_tasks)

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

        clean_pose = re.sub(r'[^a-z0-9_]', '', pose_description.lower().replace(" ", "_"))[:50]
        if not clean_pose:
            clean_pose = uuid.uuid4().hex[:8]
            
        base_filename = f"pose_{clean_pose}"
        filename = f"{base_filename}.png"
        
        full_path, relative_path = self.get_storage_path(story_id, str(character.id), filename)
        
        if os.path.exists(full_path):
            logger.info(f"Pose image already exists locally for {character.name}: {relative_path}")
            new_pose = CharacterPose(
                character_id=character.id,
                pose_description=pose_description,
                image_gcs_path=relative_path
            )
            self.db.add(new_pose)
            self.db.commit()
            return new_pose
            
        # Get base image path for reference (if local file exists)
        reference_path = None
        if character.base_image_gcs_path:
             # Construct full path from stored relative path
             reference_path = os.path.join(self.output_dir, character.base_image_gcs_path)

        # Generate Image
        async with self.semaphore:
            image = await self.genai_client.generate_character_image(
                character.description, 
                style, 
                pose=pose_description, 
                reference_image_path=reference_path,
                model=settings.POSE_MODEL,
                fallback_model=settings.POSE_FALLBACK_MODEL
            )
        if image:
            # {story_id}/{character_id}/{filename}
            path = self.save_image(image, story_id, str(character.id), filename)

            pil_image = Image.open(io.BytesIO(image.image_bytes))
            
            # Create transparent version
            try:
                transparent_images = remove_background_v2_batch([pil_image])
                if transparent_images:
                    trans_filename = f"{base_filename}_transparent.png"
                    self.save_image(transparent_images[0], story_id, str(character.id), trans_filename)
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
            
        clean_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(" ", "_"))[:50]
        if not clean_name:
            clean_name = uuid.uuid4().hex[:8]
        filename = f"{clean_name}.png"
        
        full_path, relative_path = self.get_storage_path(story_id, "backgrounds", filename)
        
        if os.path.exists(full_path):
            logger.info(f"Background image already exists locally for {name}: {relative_path}")
            bg = Background(
                story_id=story_id,
                name=name,
                description=description,
                image_gcs_path=relative_path
            )
            self.db.add(bg)
            self.db.commit()
            return bg

        # Generate
        async with self.semaphore:
            image = await self.genai_client.generate_background_image(description, style)
        if image:
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
    
    # synopsis = "In a world where dreams can be shared, a young dreamer discovers they can enter others' dreams and must navigate a surreal landscape to save their loved ones."
    # synopsis = "Create a simple 1 chapter story with 2 main characters. The story should be a romantic comedy set in a high school. The main characters are a shy bookworm and a popular athlete who are forced to work together on a school project. They start off disliking each other but eventually fall in love. Include some humorous situations and heartfelt moments."
    with open('test.txt', 'r', encoding="utf-8") as f:
        synopsis = f.read()
    style = "Anime"
    asyncio.run(workflow.generate_full_story(synopsis, style))