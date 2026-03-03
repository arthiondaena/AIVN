from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from .loader import StoryLoader

@dataclass
class GameState:
    # Navigation pointers
    current_chapter_index: int = 0
    current_scene_index: int = 0
    current_scene_id: str = ""
    
    # Dialogue progress
    # We use -1 so the first 'next()' call advances to 0
    current_dialogue_index: int = -1
    
    # Branching state
    is_waiting_for_choice: bool = False
    # If we are inside a branch's dialogue (after making a choice)
    current_branch_dialogue: Optional[List[Dict]] = None 
    current_branch_dialogue_index: int = -1
    # If the branch has a target scene to jump to after its dialogue
    pending_scene_jump: Optional[str] = None
    
    # Visual/Audio state (persisted)
    current_background: str = ""
    current_bgm: str = ""
    # Map of character_name -> expression/pose string
    character_states: Dict[str, str] = field(default_factory=dict)
    
    flags: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)

class SceneManager:
    def __init__(self, loader: StoryLoader):
        self.loader = loader
        self.state = GameState()
        self.story_structure = self.loader.data.get("story", {}).get("chapters", [])

    def start_story(self):
        """Initializes the story at the first scene of the first chapter."""
        self.state = GameState()
        
        if not self.story_structure:
            raise ValueError("Story has no chapters.")
            
        first_chapter = self.story_structure[0]
        scenes = first_chapter.get("scenes", [])
        
        if not scenes:
            raise ValueError(f"Chapter {first_chapter.get('id')} has no scenes.")
            
        first_scene = scenes[0]
        self.state.current_chapter_index = 0
        self.state.current_scene_index = 0
        self.state.current_scene_id = first_scene.get("id")
        
        # Initialize scene-specific state (background, music)
        self._init_scene_state(self.state.current_scene_id)
        
        # Advance to first dialogue line
        return self.next()

    def _init_scene_state(self, scene_id: str):
        """Sets up initial background, music, etc. for a new scene."""
        content = self.loader.get_scene_content(scene_id)
        if not content:
            return

        # Set initial background
        if content.get("initial_location_name"):
            # Try to find asset path, or just use the name/desc
            bg_name = content.get("initial_location_name")
            # In a real app, we'd look up the file path from assets
            # self.state.current_background = self.loader.get_asset_path("backgrounds", bg_name)
            self.state.current_background = bg_name 

        # Set initial BGM
        if content.get("initial_bgm"):
            self.state.current_bgm = content.get("initial_bgm")
        
        # Reset dialogue counters
        self.state.character_states = {}
        self.state.current_dialogue_index = -1
        self.state.is_waiting_for_choice = False
        self.state.current_branch_dialogue = None
        self.state.current_branch_dialogue_index = -1
        self.state.pending_scene_jump = None

    def get_current_frame(self) -> Dict[str, Any]:
        """Returns the full state required to render the current moment."""
        content = self.loader.get_scene_content(self.state.current_scene_id)
        if not content:
            return {"error": "Scene content not found"}

        frame = {
            "scene_id": self.state.current_scene_id,
            "background": self.state.current_background,
            "bgm": self.state.current_bgm,
            "characters": self.state.character_states,
            "is_choice": self.state.is_waiting_for_choice,
            "dialogue": None,
            "choices": []
        }

        # If waiting for choice, return the choices
        if self.state.is_waiting_for_choice:
            choices_data = content.get("choices_and_branches", [])
            frame["choices"] = [
                {"index": i, "text": c.get("choice_text")} 
                for i, c in enumerate(choices_data)
            ]
            # When waiting for choice, we usually display the last dialogue line or a prompt
            # For now, let's assume we keep displaying the last main dialogue line
            main_dialogue = content.get("main_dialogue", [])
            if main_dialogue and self.state.current_dialogue_index < len(main_dialogue):
                frame["dialogue"] = main_dialogue[self.state.current_dialogue_index]
            return frame

        # Determine which dialogue line to show
        current_line = None
        
        if self.state.current_branch_dialogue:
            # We are in a branch
            if 0 <= self.state.current_branch_dialogue_index < len(self.state.current_branch_dialogue):
                current_line = self.state.current_branch_dialogue[self.state.current_branch_dialogue_index]
        else:
            # We are in main dialogue
            main_dialogue = content.get("main_dialogue", [])
            if 0 <= self.state.current_dialogue_index < len(main_dialogue):
                current_line = main_dialogue[self.state.current_dialogue_index]

        if current_line:
            # Update character state based on this line
            speaker = current_line.get("speaker")
            pose = current_line.get("character_pose_expression")
            if speaker and speaker != "Narrator":
                # Only keep the current speaker in character_states
                self.state.character_states = {speaker: pose or "default"}
            else:
                self.state.character_states = {}

        frame = {
            "scene_id": self.state.current_scene_id,
            "background": self.state.current_background,
            "bgm": self.state.current_bgm,
            "characters": self.state.character_states,
            "is_choice": self.state.is_waiting_for_choice,
            "dialogue": current_line,
            "choices": []
        }

        # If waiting for choice, return the choices
        if self.state.is_waiting_for_choice:
            choices_data = content.get("choices_and_branches", [])
            frame["choices"] = [
                {"index": i, "text": c.get("choice_text")} 
                for i, c in enumerate(choices_data)
            ]
            return frame
        
        return frame

    def next(self) -> Dict[str, Any]:
        """Advances the story state."""
        if self.state.is_waiting_for_choice:
            # Cannot advance if waiting for choice
            return self.get_current_frame()

        content = self.loader.get_scene_content(self.state.current_scene_id)
        if not content:
             return {"error": "Scene content missing"}

        # Check if we are processing a branch
        if self.state.current_branch_dialogue:
            self.state.current_branch_dialogue_index += 1
            if self.state.current_branch_dialogue_index < len(self.state.current_branch_dialogue):
                return self.get_current_frame()
            else:
                # Branch dialogue finished. Jump to next scene.
                jump_target = self.state.pending_scene_jump
                if jump_target:
                    self._transition_to_scene(jump_target)
                else:
                    # If no specific jump, go to next linear scene
                    self._transition_to_next_linear_scene()
                return self.get_current_frame()

        # Processing main dialogue
        main_dialogue = content.get("main_dialogue", [])
        self.state.current_dialogue_index += 1

        # Check for mid-scene background changes
        if self.state.current_dialogue_index > 0:
            prev_line_index = self.state.current_dialogue_index - 1
            if prev_line_index < len(main_dialogue):
                prev_line = main_dialogue[prev_line_index]
                self._check_location_changes(content, prev_line.get("dialogue_id"))

        if self.state.current_dialogue_index < len(main_dialogue):
            return self.get_current_frame()
        
        # Main dialogue finished. Check for choices.
        choices = content.get("choices_and_branches", [])
        if choices:
            self.state.is_waiting_for_choice = True
            # Step back the index so get_current_frame shows the last line + choices
            self.state.current_dialogue_index -= 1 
            return self.get_current_frame()
        
        # No choices, just linear progression
        self._transition_to_next_linear_scene()
        return self.get_current_frame()

    def make_choice(self, choice_index: int) -> Dict[str, Any]:
        if not self.state.is_waiting_for_choice:
            raise RuntimeError("Not currently waiting for a choice.")
            
        content = self.loader.get_scene_content(self.state.current_scene_id)
        choices = content.get("choices_and_branches", [])
        
        if choice_index < 0 or choice_index >= len(choices):
            raise ValueError(f"Invalid choice index: {choice_index}")
            
        selected_branch = choices[choice_index]
        
        # Setup branch state
        self.state.is_waiting_for_choice = False
        self.state.current_branch_dialogue = selected_branch.get("branching_dialogue", [])
        self.state.current_branch_dialogue_index = -1
        self.state.pending_scene_jump = selected_branch.get("leads_to_scene_id")
        
        # Start playing the branch dialogue
        return self.next()

    def _check_location_changes(self, content: Dict, prev_dialogue_id: str):
        changes = content.get("mid_scene_location_changes", [])
        if not changes:
            return
            
        for change in changes:
            if change.get("trigger_after_dialogue_id") == prev_dialogue_id:
                self.state.current_background = change.get("new_location_name")
                # visual_description is also available if we were generating images on the fly

    def _transition_to_scene(self, target_scene_id: str):
        """Finds the target scene (potentially in other chapters) and jumps to it."""
        # Simple search across all chapters
        for c_idx, chapter in enumerate(self.story_structure):
            for s_idx, scene in enumerate(chapter.get("scenes", [])):
                if scene.get("id") == target_scene_id:
                    self.state.current_chapter_index = c_idx
                    self.state.current_scene_index = s_idx
                    self.state.current_scene_id = target_scene_id
                    self._init_scene_state(target_scene_id)
                    # Don't call next() here, the caller will call it or we return get_current_frame()
                    # Actually, _init_scene_state resets index to -1.
                    # The caller of this function (next()) expects us to be ready to show the first line 
                    # OR simply set up the state so the *next* call to next() works?
                    # Let's align with next(): next() calls this, then returns get_current_frame().
                    # If we set index to -1, get_current_frame() will show nothing or error?
                    # get_current_frame checks indices. -1 is not valid for display.
                    # So we should probably advance to 0 immediately.
                    self.state.current_dialogue_index = 0
                    return
        
        print(f"Warning: Target scene {target_scene_id} not found.")
        # Fallback to linear
        self._transition_to_next_linear_scene()

    def _transition_to_next_linear_scene(self):
        """Moves to the next scene in the list, or next chapter."""
        current_chapter = self.story_structure[self.state.current_chapter_index]
        scenes = current_chapter.get("scenes", [])
        
        next_scene_index = self.state.current_scene_index + 1
        
        if next_scene_index < len(scenes):
            # Next scene in same chapter
            self.state.current_scene_index = next_scene_index
            self.state.current_scene_id = scenes[next_scene_index].get("id")
            self._init_scene_state(self.state.current_scene_id)
            self.state.current_dialogue_index = 0
        else:
            # Next chapter
            next_chapter_index = self.state.current_chapter_index + 1
            if next_chapter_index < len(self.story_structure):
                self.state.current_chapter_index = next_chapter_index
                self.state.current_scene_index = 0
                next_chapter = self.story_structure[next_chapter_index]
                if next_chapter.get("scenes"):
                    self.state.current_scene_id = next_chapter["scenes"][0].get("id")
                    self._init_scene_state(self.state.current_scene_id)
                    self.state.current_dialogue_index = 0
                else:
                    # Empty chapter? Skip or end?
                    print("Next chapter has no scenes. Ending story.")
                    self.state.current_scene_id = "END"
            else:
                # End of story
                self.state.current_scene_id = "END"
