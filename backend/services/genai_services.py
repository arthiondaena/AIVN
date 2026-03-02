import base64
import json
import logging
import wave
import os

from google import genai
from google.genai import types
from google.genai.types import GenerateContentResponse
from langfuse import get_client
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

from core.config import settings
from prompts.image_generation_prompt import CHARACTER_USER_PROMPT, CHARACTER_SYSTEM_PROMPT, BACKGROUND_USER_PROMPT, \
    BACKGROUND_SYSTEM_PROMPT
from prompts.story_outline_prompt import STORY_OUTLINE_SYSTEM_PROMPT, STORY_OUTLINE_USER_PROMPT
from prompts.chapter_generation_prompt import CHAPTER_GENERATION_SYSTEM_PROMPT, CHAPTER_GENERATION_USER_PROMPT
from prompts.scene_generation_prompt import SCENE_SYSTEM_PROMPT, SCENE_USER_PROMPT
from models.story_outline_models import MainStoryOutline, ChapterToScenes
from models.story_detailed_models import SceneElaborator

langfuse = get_client()
assert langfuse.auth_check(), "Langfuse auth failed - check your keys ✋"

GoogleGenAIInstrumentor().instrument()

# Configure logging
logger = logging.getLogger(__name__)


def extract_image_from_response(response: GenerateContentResponse):
    for part in response.parts:
        if part.inline_data:
            image = part.as_image()
            return image
    return None


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
   with wave.open(filename, "wb") as wf:
      wf.setnchannels(channels)
      wf.setsampwidth(sample_width)
      wf.setframerate(rate)
      wf.writeframes(pcm)


class GenAIClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.VERTEX_API_KEY)
        # self.client = genai.Client(vertexai=True)

    async def generate_story_structure(self, story_text: str, style: str):
        prompt = STORY_OUTLINE_USER_PROMPT.format(story_text=story_text, style=style)
        # await self.client.aio.models.list() # list is likely sync or needed? Maybe skip listing.
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL, # fast model for structure
            contents=prompt,
            config=types.GenerateContentConfig(
                # response_mime_type="application/json"
                system_instruction=STORY_OUTLINE_SYSTEM_PROMPT,
                response_schema=MainStoryOutline
            )
        )
        return json.loads(response.text)

    async def generate_chapter_scenes(self, chapter_id: str, title: str, summary: str, style: str):
        prompt = CHAPTER_GENERATION_USER_PROMPT.format(chapter_id=chapter_id, title=title, plot_summary=summary, style=style)
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=CHAPTER_GENERATION_SYSTEM_PROMPT,
                response_schema=ChapterToScenes
            )
        )
        return json.loads(response.text)

    async def elaborate_scene(self, scene_id: str, title: str, summary: str, primary_location: str, characters: list, style: str):
        prompt = SCENE_USER_PROMPT.format(
            scene_id=scene_id, title=title, scene_summary=summary,
            primary_location=primary_location, characters=json.dumps(characters), style=style
        )
        response = await self.client.aio.models.generate_content(
            model=settings.STORY_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SCENE_SYSTEM_PROMPT,
                response_schema=SceneElaborator
            )
        )
        return json.loads(response.text)

    async def generate_character_image(self, description: str, style: str, pose: str = None, reference_image_path: str = None):
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

        try:
            response = await self.client.aio.models.generate_content(
                model=settings.IMAGE_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                    system_instruction=CHARACTER_SYSTEM_PROMPT
                )
            )
            return extract_image_from_response(response)

        except Exception as e:
            logger.error(f"Error generating character image: {e}")

    async def generate_background_image(self, description: str, style: str):
        prompt = BACKGROUND_USER_PROMPT.format(description=description, style=style)
        try:
            response = await self.client.aio.models.generate_content(
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

    async def generate_audio(self, text: str, file_path: str, voice_name: str = "Puck"):
        # Assuming it's used via generate_content with audio modality or speech config
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
        # Extract audio bytes
        # response.parts[0].inline_data.data (bytes)
        data = response.candidates[0].content.parts[0].inline_data.data
        wave_file(file_path, data)
        return file_path

    async def get_embedding(self, text: str):
        # client = genai.Client(vertexai=True)
        if not text:
            logger.warning("get_embedding called with empty text.")
            raise ValueError("No embedding input is provided.")

        logger.info(f"Generating embedding for text length: {len(text)}")
        try:
            response = await self.client.aio.models.embed_content(
                model=settings.EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=768
                )
            )
            # Handle potential different response structures
            if hasattr(response, 'embeddings') and response.embeddings:
                return response.embeddings[0].values
            return response.embeddings
        except Exception as e:
            logger.error(f"Error in get_embedding: {e}")
            raise e

if __name__ == "__main__":
    import asyncio
    client = GenAIClient()
    description = "Haru’s younger sister, aged 14. She has long, flowing silver hair adorned with small, glowing star-shaped hairpins. She wears a traditional white yukata with a modern twist, featuring patterns of koi fish that appear to swim across the fabric. In the dream world, she is often surrounded by translucent, glowing butterflies. Her expression is ethereal and serene, though her eyes appear glassy and distant while trapped in the dream-state."
    img = asyncio.run(client.generate_character_image(description, "anime", "full body"))
    img.save("character_image.png")