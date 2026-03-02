from typing import Optional, List, Literal
from pydantic import BaseModel, Field

class DialogueLine(BaseModel):
    dialogue_id: str = Field(..., description="Unique identifier for the dialogue (e.g., 's1_line1').")
    speaker: str = Field(..., description="Name of the character speaking. Use 'Narrator' for internal thoughts or narration.")
    text: str = Field(..., description="The actual dialogue spoken or text displayed to the player. Can include markup tags like [sigh], [whispering], [sarcasm] etc.")
    tone: str = Field(..., description="The detailed tone of the dialogue line. example: The 'Vocal Smile'': You must hear the grin in the audio. The soft palate isalways raised to keep the tone bright, sunny, and explicitly inviting.")

    character_pose_expression: Optional[str] = Field(None, description="Pose and expression (e.g., 'hands on hips, pouting'). Null if speaker is Narrator.")
    stage_action: Optional[Literal["enter", "exit", "screen_shake", "flash"]] = Field(None, description="Optional stage direction triggered on this line.")
    trigger_sfx: Optional[str] = Field(None, description="Description of sound effect to play on this line (e.g., 'door slamming', 'sword clashing').")

class LocationChange(BaseModel):
    trigger_after_dialogue_id: str = Field(..., description="The string ID of the dialogue line AFTER which this background change occurs.")
    new_location_name: str = Field(..., description="The name of the new location.")
    visual_description: str = Field(..., description="Prompt-ready description of what the new background looks like.")

class StoryBranch(BaseModel):
    choice_text: str = Field(..., description="The exact text presented to the player on the choice button.")
    branching_dialogue: List[DialogueLine] = Field(..., description="Sequential dialogue/events occurring immediately after making this choice.")
    leads_to_scene_id: Optional[str] = Field(None, description="The ID of the next SceneOutline this branch routes to.")

class SceneElaborator(BaseModel):
    scene_id: str = Field(..., description="The ID of the scene.")
    characters_present: List[str] = Field(..., description="List of character names actively participating in this scene.")
    initial_location_name: str = Field(..., description="The starting location name for the background.")
    initial_location_description: str = Field(..., description="Prompt-ready description of the starting background art.")
    initial_bgm: Optional[str] = Field(None, description="The vibe of the background music to start playing (e.g., 'tense orchestral', 'upbeat slice of life').")

    main_dialogue: List[DialogueLine] = Field(..., description="Sequential dialogue lines playing before any choices are presented.")

    choices_and_branches: Optional[List[StoryBranch]] = Field(None, description="Player choices available at the end of the main dialogue.")

    mid_scene_location_changes: Optional[List[LocationChange]] = Field(None, description="Background changes occurring during the main dialogue.")