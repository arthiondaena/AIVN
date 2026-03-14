import asyncio
import json
import logging
import wave
import os
from tenacity import retry, stop_after_attempt, wait_exponential

from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse
from langsmith.wrappers import wrap_gemini

from core.config import settings
from prompts.image_generation_prompt import CHARACTER_USER_PROMPT, CHARACTER_SYSTEM_PROMPT, BACKGROUND_USER_PROMPT, \
    BACKGROUND_SYSTEM_PROMPT
from prompts.story_outline_prompt import STORY_OUTLINE_SYSTEM_PROMPT, STORY_OUTLINE_USER_PROMPT
from prompts.chapter_generation_prompt import CHAPTER_GENERATION_SYSTEM_PROMPT, CHAPTER_GENERATION_USER_PROMPT
from prompts.scene_generation_prompt import SCENE_SYSTEM_PROMPT, SCENE_USER_PROMPT
from prompts.character_pose_prompt import CHARACTER_POSE_SYSTEM_PROMPT, CHARACTER_POSE_USER_PROMPT
from models.story_outline_models import MainStoryOutline, ChapterToScenes
from models.story_detailed_models import SceneElaborator, CharacterPoseSet

# Configure logging
logger = logging.getLogger(__name__)


def extract_image_from_response(response: GenerateContentResponse):
    if not getattr(response, 'parts', None):
        return None
    try:
        for part in response.parts:
            if part.inline_data:
                image = part.as_image()
                return image
    except Exception as e:
        logger.warning(f"Error extracting image from response: {e}")
        return None
    return None


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)


class GenAIClient:
    def __init__(self):
        self.client = genai.Client(vertexai=True, location="global")
        self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Try to wrap client with langsmith
        try:
            self.client = wrap_gemini(self.client)
            # self.vertex_client = wrap_gemini(self.vertex_client)
        except Exception as e:
            logger.warning(f"Could not wrap client with langsmith: {e}")

        # self.client = genai.Client(vertexai=True)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_story_structure(self, story_text: str, style: str):
        prompt = STORY_OUTLINE_USER_PROMPT.format(story_text=story_text, style=style)
        system_instruction = STORY_OUTLINE_SYSTEM_PROMPT.format(background_count=settings.BACKGROUND_COUNT)
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL, # fast model for structure
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=system_instruction,
                response_schema=MainStoryOutline
            )
        )
        return json.loads(response.text)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_chapter_scenes(self, chapter_id: str, title: str, summary: str, style: str, available_backgrounds: str):
        prompt = CHAPTER_GENERATION_USER_PROMPT.format(chapter_id=chapter_id, title=title, plot_summary=summary, available_backgrounds=available_backgrounds, style=style)
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=CHAPTER_GENERATION_SYSTEM_PROMPT,
                response_schema=ChapterToScenes
            )
        )
        return json.loads(response.text)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def elaborate_scene(self, scene_id: str, title: str, summary: str, primary_location: str, characters_info: str, style: str, available_backgrounds: str):
        prompt = SCENE_USER_PROMPT.format(
            scene_id=scene_id, title=title, scene_summary=summary,
            primary_location=primary_location, characters=characters_info, available_backgrounds=available_backgrounds, style=style
        )
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=SCENE_SYSTEM_PROMPT,
                response_schema=SceneElaborator
            )
        )
        return json.loads(response.text)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_character_pose_list(self, name: str, role: str, description: str, style: str, pose_count: str = "15-30"):
        prompt = CHARACTER_POSE_USER_PROMPT.format(name=name, role=role, description=description, style=style, pose_count=pose_count)
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=CHARACTER_POSE_SYSTEM_PROMPT,
                response_schema=CharacterPoseSet
            )
        )
        return json.loads(response.text)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=30, max=90),
        reraise=True
    )
    async def generate_character_image(self, description: str, style: str, pose: str = None, reference_image_path: str = None, model: str = None, fallback_model: str = None):
        pose = pose if pose else "Full body"
        prompt = CHARACTER_USER_PROMPT.format(character_description=description, pose=pose, style=style)
        
        contents = [prompt]
        
        if reference_image_path and os.path.exists(reference_image_path):
            try:
                with open(reference_image_path, "rb") as f:
                    image_data = f.read()
                    # Create a Part object for the image
                    image_part = types.Part.from_bytes(data=image_data, mime_type="image/png")
                    contents.append(image_part)
            except Exception as e:
                logger.warning(f"Could not load reference image at {reference_image_path}: {e}")

        if model is None:
            model = settings.IMAGE_MODEL_MAIN

        try:
            response = await self.gemini_client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    system_instruction=CHARACTER_SYSTEM_PROMPT
                )
            )
            return extract_image_from_response(response)

        except Exception as e:
            if fallback_model:
                logger.warning(f"Error with primary model {model}, falling back to {fallback_model}: {e}")
                try:
                    response = await self.gemini_client.aio.models.generate_content(
                        model=fallback_model,
                        contents=contents,
                        config=types.GenerateContentConfig(
                            response_modalities=['IMAGE'],
                            system_instruction=CHARACTER_SYSTEM_PROMPT
                        )
                    )
                    return extract_image_from_response(response)
                except Exception as fallback_e:
                    logger.error(f"Error generating character image with fallback model: {fallback_e}")
                    raise fallback_e
            else:
                logger.error(f"Error generating character image: {e}")
                raise e

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_background_image(self, description: str, style: str):
        prompt = BACKGROUND_USER_PROMPT.format(description=description, style=style)
        try:
            response = await self.gemini_client.aio.models.generate_content(
                model=settings.IMAGE_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    system_instruction=BACKGROUND_SYSTEM_PROMPT
                )
            )
            return extract_image_from_response(response)

        except Exception as e:
            logger.error(f"Error generating background image: {e}")
            raise e

    async def generate_scene_audio(self, scene_data: dict, voice_map: dict, output_dir_callback):
        """
        Generates audio for all dialogue lines in a scene.
        output_dir_callback: function(filename) -> full_path
        """
        tasks = []
        
        # Helper to process a list of dialogue lines
        async def process_lines(lines):
            for line in lines:
                speaker = line.get("speaker")
                text = line.get("text")
                dialogue_id = line.get("dialogue_id")
                
                if not text or not speaker or speaker == "Narrator":
                    continue
                    
                voice_name = voice_map.get(speaker, "Puck")
                scene_id = scene_data.get('id') or scene_data.get('scene_id')
                filename = f"{scene_id}_{dialogue_id}.wav"
                full_path = output_dir_callback(filename)
                
                # We can run these in parallel
                tasks.append(self.generate_audio(text, full_path, voice_name))

        # 1. Main Dialogue
        await process_lines(scene_data.get("main_dialogue") or [])
        
        # 2. Branches
        for choice in (scene_data.get("choices_and_branches") or []):
            await process_lines(choice.get("branching_dialogue") or [])
            
        # Execute all audio generation tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Log errors
            for res in results:
                if isinstance(res, Exception):
                    logger.error(f"Error generating audio task: {res}")
        
        return len(tasks)

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def generate_audio_sync(self, text: str, file_path: str, voice_name: str = "Puck") -> str:
        """
        Synchronous version of audio generation that saves to a specific path.
        """
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        logger.info(f"Generating audio (sync) to: {file_path}")
        
        try:
            # Use the synchronous client (no .aio)
            response = self.client.models.generate_content(
                model=settings.AUDIO_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
        except Exception as e:
            logger.warning(f"Error with primary model {settings.AUDIO_MODEL}, falling back to {settings.AUDIO_FALLBACK_MODEL}: {e}")
            try:
                response = self.client.models.generate_content(
                    model=settings.AUDIO_FALLBACK_MODEL,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        )
                    )
                )
            except Exception as fallback_e:
                logger.error(f"Error generating audio with fallback: {fallback_e}")
                raise fallback_e
            
        # Extract audio bytes
        if response.candidates and response.candidates[0].content.parts:
            data = response.candidates[0].content.parts[0].inline_data.data
            wave_file(file_path, data)
            return file_path
        else:
            logger.error("No audio content in response")
            return None

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_audio_stream(self, text: str, voice_name: str = "Puck"):
        """
        Generates audio for the given text using streaming and yields audio chunks.
        """
        logger.info(f"Generating audio (streaming) for: {text[:20]}...")
        
        try:
            # When using generate_content_stream for audio, we need to ensure the client treats it correctly.
            # The error "Model tried to generate text" suggests it might need a specific prompt structure or just the text.
            # For TTS specifically, usually we just send the text.
            
            # Using a system instruction to enforce audio only might help?
            # Or ensuring we don't ask it to "generate" text.
            
            stream = await self.client.aio.models.generate_content_stream(
                model=settings.AUDIO_MODEL,
                contents=text, 
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    system_instruction="You are a text-to-speech system. Your only task is to generate audio for the provided text. Do not generate any text response.",
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
        except Exception as e:
            logger.warning(f"Error with primary model {settings.AUDIO_MODEL}, falling back to {settings.AUDIO_FALLBACK_MODEL}: {e}")
            try:
                stream = await self.client.aio.models.generate_content_stream(
                    model=settings.AUDIO_FALLBACK_MODEL,
                    contents=text, 
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        system_instruction="You are a text-to-speech system. Your only task is to generate audio for the provided text. Do not generate any text response.",
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        )
                    )
                )
            except Exception as fallback_e:
                logger.error(f"Error generating audio stream with fallback: {fallback_e}")
                raise fallback_e
            
        async for chunk in stream:
            if chunk.candidates and chunk.candidates[0].content.parts:
                # Yield the raw bytes of the audio chunk
                yield chunk.candidates[0].content.parts[0].inline_data.data

    @retry(
        stop=stop_after_attempt(8),
        wait=wait_exponential(multiplier=1, min=30, max=90),
        reraise=True
    )
    async def generate_audio(self, text: str, file_path: str, voice_name: str = "Puck"):
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Assuming it's used via generate_content with audio modality or speech config
        try:
            response = await self.client.aio.models.generate_content(
                model=settings.AUDIO_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
        except Exception as e:
            logger.warning(f"Error with primary model {settings.AUDIO_MODEL}, falling back to {settings.AUDIO_FALLBACK_MODEL}: {e}")
            response = await self.client.aio.models.generate_content(
                model=settings.AUDIO_FALLBACK_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
        
        # Extract audio bytes from any part that contains inline_data
        audio_data = None
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    audio_data = part.inline_data.data
                    break
        
        if audio_data:
            wave_file(file_path, audio_data)
            return file_path
        else:
            # Log the response text if available for debugging
            resp_text = getattr(response, 'text', 'No text in response')
            logger.error(f"No audio content in response for file: {file_path}. Response text: {resp_text[:100]}")
            raise Exception(f"No audio content in response for file: {file_path}")

if __name__ == "__main__":
    import asyncio
    client = GenAIClient()
    description = "Haru’s younger sister, aged 14. She has long, flowing silver hair adorned with small, glowing star-shaped hairpins. She wears a traditional white yukata with a modern twist, featuring patterns of koi fish that appear to swim across the fabric. In the dream world, she is often surrounded by translucent, glowing butterflies. Her expression is ethereal and serene, though her eyes appear glassy and distant while trapped in the dream-state."
    img = asyncio.run(client.generate_character_image(description, "anime", "full body"))
    img.save("character_image.png")
    # asyncio.run(client.generate_audio("Hello, testing 1,2,3", "test.wav"))