import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select

from vn_engine.headless import HeadlessGameEngine
from core.database import get_db
from core.orm import Story, Character, Chapter
from services.story_workflow import StoryWorkflowService
from vn_engine.converter import StoryConverter
from models.story_outline_models import MainStoryOutline

logger = logging.getLogger(__name__)

app = FastAPI(title="AIVN Web Game Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "output"


def _image_to_data_uri(relative_path: Optional[str]) -> Optional[str]:
    """Read an image from disk and return a base64 PNG data URI."""
    if not relative_path:
        return None
    full_path = os.path.join(OUTPUT_DIR, relative_path)
    try:
        with open(full_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    except FileNotFoundError:
        logger.warning(f"Image file not found: {full_path}")
        return None


os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/assets", StaticFiles(directory="output"), name="assets")

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

ArtStyle = Literal[
    "anime",
    "american cartoon style",
    "western comic style",
    "korean manhwa style",
    "chibi style",
]


class StoryOutlineRequest(BaseModel):
    synopsis: str = Field(..., description="Story synopsis written by the user.")
    art_style: ArtStyle = Field(..., description="Visual art style for the entire story.")

class UpdateOutlineRequest(BaseModel):
    story_outline: MainStoryOutline = Field(..., description="Full story outline with any user edits applied.")

class CharacterImageRequest(BaseModel):
    appearance: str = Field(..., description="Updated appearance description for the character.")
    art_style: ArtStyle = Field(..., description="Art style to use when regenerating the character image.")


class StoryOutlineResponse(BaseModel):
    story_id: int = Field(..., description="Database ID of the newly created story.")
    outline: MainStoryOutline = Field(..., description="AI-generated story outline including characters and chapters.")
    character_images: Dict[str, str] = Field(
        ...,
        description="Map of character name to base64-encoded PNG data URI (e.g. 'data:image/png;base64,...'). "
                    "Can be set directly as the src of an <img> tag.",
    )

class CharacterImageResponse(BaseModel):
    status: str = Field(..., description="'success' on completion.")
    image_data: Optional[str] = Field(
        None,
        description="Base64-encoded PNG data URI of the regenerated character image. "
                    "Can be set directly as the src of an <img> tag.",
    )

class UpdateOutlineResponse(BaseModel):
    status: str = Field(..., description="'success' on completion.")
    story_id: int = Field(..., description="ID of the updated story.")

class StatusResponse(BaseModel):
    status: str = Field(..., description="'success' on completion.")
    message: str = Field(..., description="Human-readable result description.")

class SceneDetail(BaseModel):
    id: int = Field(..., description="Database ID of the scene.")
    title: str = Field(..., description="Scene title.")
    dialogue: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of dialogue lines as generated, each containing speaker, text, and pose fields."
    )

class ChapterWithScenes(BaseModel):
    id: int = Field(..., description="Database ID of the chapter.")
    title: Optional[str] = Field(None, description="Chapter title.")
    scenes: List[SceneDetail] = Field(..., description="All scenes belonging to this chapter.")

class StorySummary(BaseModel):
    id: int = Field(..., description="Database ID of the story.")
    title: Optional[str] = Field(None, description="Story title.")
    logline: Optional[str] = Field(None, description="One-sentence story summary.")
    style: str = Field(..., description="Art style used for this story.")


@app.post(
    "/api/story/outline",
    response_model=StoryOutlineResponse,
    summary="Create story outline",
    description=(
        "Generates a story outline from the user's synopsis and art style. "
        "Base character images (neutral standing pose) are generated for every character. "
        "Returns the outline and a map of character images for the user to review."
    ),
)
async def create_story_outline(req: StoryOutlineRequest, db: Session = Depends(get_db)):
    workflow = StoryWorkflowService(db)
    story, outline = await workflow.generate_story_outline_only(req.synopsis, req.art_style)

    characters = db.scalars(select(Character).where(Character.story_id == story.id)).all()
    char_images = {
        c.name: _image_to_data_uri(c.base_image_gcs_path)
        for c in characters
        if c.base_image_gcs_path and _image_to_data_uri(c.base_image_gcs_path)
    }

    return StoryOutlineResponse(story_id=story.id, outline=outline, character_images=char_images)


@app.post(
    "/api/story/{story_id}/character/{character_id}/regenerate-base",
    response_model=CharacterImageResponse,
    summary="Regenerate character base image",
    description=(
        "Regenerates the neutral standing pose image for a specific character. "
        "Use this after the user edits the character's appearance description or changes the art style."
    ),
)
async def regenerate_character_base(
    story_id: int,
    character_id: int,
    req: CharacterImageRequest,
    db: Session = Depends(get_db),
):
    workflow = StoryWorkflowService(db)
    char_obj = await workflow.regenerate_character_image(story_id, character_id, req.appearance, req.art_style)
    if not char_obj:
        raise HTTPException(status_code=404, detail="Character not found")
    return CharacterImageResponse(
        status="success",
        image_data=_image_to_data_uri(char_obj.base_image_gcs_path),
    )


@app.put(
    "/api/story/{story_id}/outline",
    response_model=UpdateOutlineResponse,
    summary="Update story outline",
    description=(
        "Persists user edits to the story outline (title, logline, character descriptions, "
        "chapter summaries, or art style). Pass the full updated outline in the request body."
    ),
)
async def update_story_outline(
    story_id: int,
    req: UpdateOutlineRequest,
    db: Session = Depends(get_db),
):
    workflow = StoryWorkflowService(db)
    story = await workflow.update_story_outline(story_id, req.story_outline.model_dump())
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return UpdateOutlineResponse(status="success", story_id=story_id)


@app.post(
    "/api/story/{story_id}/generate-pipeline",
    response_model=StatusResponse,
    summary="Generate full story pipeline",
    description=(
        "Triggers the complete generation pipeline: character pose sets, chapter breakdowns, "
        "detailed scene dialogue, background images, and voice assignments. "
        "This is a long-running operation. Call after the user has approved the outline."
    ),
)
async def generate_pipeline(story_id: int, db: Session = Depends(get_db)):
    workflow = StoryWorkflowService(db)
    story = await workflow.generate_story_pipeline(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return StatusResponse(status="success", message="Pipeline generated successfully")


# 6. Convert generated assets to screenplay.json
@app.post(
    "/api/story/{story_id}/convert",
    response_model=StatusResponse,
    summary="Convert story to screenplay",
    description=(
        "Compiles all generated scenes, assets, and metadata from the database into a single "
        "`screenplay.json` file required by the game engine. Must be called before playing."
    ),
)
def convert_story(story_id: int):
    converter = StoryConverter(str(story_id))
    converter.convert()
    return StatusResponse(status="success", message="Screenplay generated.")


@app.get(
    "/api/story/{story_id}/scenes",
    response_model=List[ChapterWithScenes],
    summary="Get story scenes",
    description=(
        "Returns all chapters and their scenes for a given story, including the generated "
        "dialogue content so the user can review the story before playing."
    ),
)
def get_story_scenes(story_id: int, db: Session = Depends(get_db)):
    chapters = db.scalars(
        select(Chapter).where(Chapter.story_id == story_id).options(joinedload(Chapter.scenes))
    ).unique().all()

    return [
        ChapterWithScenes(
            id=c.id,
            title=c.title,
            scenes=[
                SceneDetail(id=s.id, title=s.title, dialogue=s.dialogue_content)
                for s in c.scenes
            ],
        )
        for c in chapters
    ]


@app.get(
    "/api/stories",
    response_model=List[StorySummary],
    summary="List all stories",
    description="Returns a summary list of every story that has been generated, for the user to select from.",
)
def list_stories(db: Session = Depends(get_db)):
    stories = db.scalars(select(Story)).all()
    return [
        StorySummary(id=s.id, title=s.title, logline=s.logline, style=s.style)
        for s in stories
    ]


@app.get("/play/{story_id}", response_class=HTMLResponse, include_in_schema=False)
async def play_story(story_id: str):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AIVN Player</title>
        <style>
            body {{ margin: 0; overflow: hidden; background: #000; }}
            iframe {{ width: 100vw; height: 100vh; border: none; }}
        </style>
    </head>
    <body>
        <iframe src="/static/game.html?story_id={story_id}"></iframe>
    </body>
    </html>
    """


@app.websocket("/ws/game/{story_id}")
async def game_websocket(websocket: WebSocket, story_id: str):
    """
    WebSocket endpoint for real-time game playback.

    Client sends JSON actions:
    - `{"action": "advance"}` — advance to the next dialogue line.
    - `{"action": "choice", "index": <int>}` — select a story branch by index.

    Server responds with a frame object on each event containing the current
    background, character sprites, speaker, dialogue text, and any available choices.
    Pass `resume_line` in the first advance payload to restore a previous session position.
    """
    await websocket.accept()
    screenplay_path = f"output/{story_id}/screenplay.json"
    if not os.path.exists(screenplay_path):
        await websocket.send_json({"error": f"Screenplay not found for story ID {story_id}"})
        await websocket.close()
        return

    engine = HeadlessGameEngine(screenplay_path)
    try:
        initial_frame = engine.start()
        await websocket.send_json(initial_frame)

        while True:
            data = await websocket.receive_text()
            action_data = json.loads(data)
            action = action_data.get("action")
            frame = None

            if action == "advance":
                frame = engine.advance()
            elif action == "choice":
                index = action_data.get("index")
                if index is not None:
                    frame = engine.make_choice(index)

            if frame:
                await websocket.send_json(frame)

    except WebSocketDisconnect:
        logger.info(f"Client disconnected from story {story_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()