from typing import List, Literal

from pydantic import BaseModel

from pydantic import BaseModel, Field
from typing import List, Optional

class CharacterSpriteInfo(BaseModel):
    name: str = Field(..., description="Full name of the character.")
    role: str = Field(..., description="Role (e.g., Protagonist, Antagonist, Sidekick).")
    gender: Literal["male", "female"] = Field(..., description="Gender of the character.")
    appearance: str = Field(..., description="Detailed physical description for generating the base character sprite.")

class ChapterOutline(BaseModel):
    chapter_id: str = Field(..., description="Unique identifier for the chapter (e.g., 'act1_chapter1').")
    title: str = Field(..., description="A short, descriptive title for the chapter.")
    primary_location: str = Field(..., description="The main location where this chapter takes place.")
    plot_summary: str = Field(..., description="A highly detailed summary of the events, conflicts, and resolutions that occur in this chapter.")

class MainStoryOutline(BaseModel):
    title: str = Field(..., description="The title of the visual novel.")
    logline: str = Field(..., description="A compelling one-sentence summary of the story.")
    main_characters: List[CharacterSpriteInfo] = Field(..., description="Information required to create sprites for the main cast.")
    side_characters: List[CharacterSpriteInfo] = Field(default_factory=list, description="Information required to create sprites for any side characters that appear in the story.")
    main_chapters: List[ChapterOutline] = Field(..., description="The sequential outline of all major chapters in the game.")

class SceneOutline(BaseModel):
    scene_id: str = Field(..., description="The ID of the scene.")
    title: str = Field(..., description="A short, descriptive title for the scene.")
    primary_location: str = Field(..., description="The main location where this scene takes place.")
    scene_summary: str = Field(..., description="A highly detailed summary of the events, conflicts, and resolutions that occur in this scene.")

class ChapterToScenes(BaseModel):
    chapter_id: str = Field(..., description="ID matching the ChapterOutline this expands upon.")
    scenes: List[SceneOutline] = Field(..., description="The list of scenes in the given chapter.")