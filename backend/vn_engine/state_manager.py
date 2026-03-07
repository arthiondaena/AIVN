import os
from typing import Dict, Any, List, Optional
import threading
import logging
from dataclasses import dataclass, field
from .loader import StoryLoader


logger = logging.getLogger(__name__)

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
        
        # Audio Prefetching
        self.genai_client = None
        self._init_genai_client()
        self.prefetch_queue = [] # List of (text, voice) to process
        self.prefetch_lock = threading.Lock()

    def _init_genai_client(self):
        try:
            from backend.services.genai_services import GenAIClient
            self.genai_client = GenAIClient()
        except ImportError:
            logger.warning("Could not import GenAIClient. TTS will be disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize GenAIClient: {e}")

    def _get_voice_for_speaker(self, speaker_name: str) -> str:
        """
        Maps a speaker name to a voice ID using metadata from the story.
        """
        voices = self.loader.metadata.get("voices", {})
        
        # Exact match
        if speaker_name in voices:
            return voices[speaker_name]
            
        # Partial match (fallback)
        for name, voice in voices.items():
            if name in speaker_name or speaker_name in name:
                return voice
                
        # Hardcoding fallback for specific known names if still missing
        if "Haruka" in speaker_name:
            return "Kore" 
        if "Kenji" in speaker_name:
            return "Puck"
        if "Tanaka" in speaker_name:
            return "Fenrir"
            
        return "Puck"

    def _trigger_scene_prefetch(self, scene_id: str):
        """
        Prefetches audio for the entire scene using async generation in a background thread.
        """
        if not self.genai_client:
            return

        content = self.loader.get_scene_content(scene_id)
        if not content:
            return
            
        # Ensure scene_id is present in the data passed to the generator
        if isinstance(content, dict):
            content["scene_id"] = scene_id

        # Prepare voice map
        voice_map = {}
        speakers = set()
        for line in content.get("main_dialogue", []):
            if line.get("speaker"):
                speakers.add(line["speaker"])
        for branch in content.get("choices_and_branches", []):
            for line in branch.get("branching_dialogue", []):
                if line.get("speaker"):
                    speakers.add(line["speaker"])
        
        for speaker in speakers:
            voice_map[speaker] = self._get_voice_for_speaker(speaker)

        def run_async_prefetch():
            import asyncio
            from backend.services.genai_services import GenAIClient
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create a fresh client instance bound to THIS thread's event loop
            local_genai_client = GenAIClient()
            
            def get_audio_path(filename):
                return str(self.loader.screenplay_path.parent / "audio" / filename)

            try:
                loop.run_until_complete(local_genai_client.generate_scene_audio(
                    content,
                    voice_map,
                    get_audio_path
                ))
            except Exception as e:
                logger.error(f"Error in async prefetch for scene {scene_id}: {e}")
            finally:
                loop.close()

        # Start a thread to run the async task
        t = threading.Thread(target=run_async_prefetch, daemon=True)
        t.start()

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
        next_frame = self.next()
        
        # Trigger prefetch for the NEXT scene (background generation)
        # We assume the first scene is already generated by the workflow.
        # So we look ahead to the second scene.
        self._prefetch_next_scene()
        
        return next_frame

    def _prefetch_next_scene(self):
        # Determine next scene
        current_chapter = self.story_structure[self.state.current_chapter_index]
        scenes = current_chapter.get("scenes", [])
        next_scene_index = self.state.current_scene_index + 1
        
        if next_scene_index < len(scenes):
            next_scene_id = scenes[next_scene_index].get("id")
            self._trigger_scene_prefetch(next_scene_id)
        else:
            # Check next chapter
            next_chapter_index = self.state.current_chapter_index + 1
            if next_chapter_index < len(self.story_structure):
                next_chapter = self.story_structure[next_chapter_index]
                if next_chapter.get("scenes"):
                    next_scene_id = next_chapter["scenes"][0].get("id")
                    self._trigger_scene_prefetch(next_scene_id)

    def _check_prefetch(self):
        """
        Looks ahead and triggers prefetching for the next few lines.
        """
        # We are now doing scene-level prefetching in _transition_to_scene, 
        # but keeping this for branches or immediate next lines is fine.
        pass

    def _init_scene_state(self, scene_id: str):
        """Sets up initial background, music, etc. for a new scene."""
        content = self.loader.get_scene_content(scene_id)
        if not content:
            return

        # Set initial background
        if content.get("initial_location_name"):
            self.state.current_background = content.get("initial_location_name") 

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
        
        # Trigger prefetch for the NEXT scene
        self._prefetch_next_scene()

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
            choices_data = content.get("choices_and_branches") or []
            frame["choices"] = [
                {"index": i, "text": c.get("choice_text")} 
                for i, c in enumerate(choices_data)
            ]
            main_dialogue = content.get("main_dialogue") or []
            if main_dialogue and self.state.current_dialogue_index < len(main_dialogue):
                frame["dialogue"] = main_dialogue[self.state.current_dialogue_index]
            return frame

        # Determine which dialogue line to show
        current_line = None
        
        if self.state.current_branch_dialogue:
            if 0 <= self.state.current_branch_dialogue_index < len(self.state.current_branch_dialogue):
                current_line = self.state.current_branch_dialogue[self.state.current_branch_dialogue_index]
        else:
            main_dialogue = content.get("main_dialogue") or []
            if 0 <= self.state.current_dialogue_index < len(main_dialogue):
                current_line = main_dialogue[self.state.current_dialogue_index]

        audio_path = None
        if current_line:
            speaker = current_line.get("speaker")
            pose = current_line.get("character_pose_expression")
            text = current_line.get("text")
            
            if speaker and speaker != "Narrator":
                # Only keep the current speaker in character_states
                self.state.character_states = {speaker: pose or "default"}
                
                # 1. Try to find pre-generated audio asset
                audio_key = current_line.get("audio_key")
                if audio_key:
                    rel_path = self.loader.get_asset_path("audio", audio_key)
                    if rel_path:
                        potential_path = os.path.join(self.loader.base_dir, rel_path)
                        if os.path.exists(potential_path):
                            audio_path = potential_path

                # 2. Check if the audio file exists at the expected path
                if not audio_path:
                    dialogue_id = current_line.get("dialogue_id")
                    filename = f"{self.state.current_scene_id}_{dialogue_id}.wav"
                    expected_path = self.loader.screenplay_path.parent / "audio" / filename
                    if expected_path.exists():
                        audio_path = str(expected_path)

                # 3. Get audio path from TTS generation if not found
                if not audio_path and self.genai_client and text:
                    voice_name = self._get_voice_for_speaker(speaker)
                    dialogue_id = current_line.get("dialogue_id")
                    filename = f"{self.state.current_scene_id}_{dialogue_id}.wav"
                    expected_path = str(self.loader.screenplay_path.parent / "audio" / filename)
                    try:
                        audio_path = self.genai_client.generate_audio_sync(text, expected_path, voice_name)
                    except Exception as e:
                        logger.error(f"Failed to get audio path: {e}")
            else:
                self.state.character_states = {}

        frame = {
            "scene_id": self.state.current_scene_id,
            "background": self.state.current_background,
            "bgm": self.state.current_bgm,
            "characters": self.state.character_states,
            "is_choice": self.state.is_waiting_for_choice,
            "dialogue": current_line,
            "choices": [],
            "audio_path": audio_path
        }

        # If waiting for choice, return the choices
        if self.state.is_waiting_for_choice:
            choices_data = content.get("choices_and_branches") or []
            frame["choices"] = [
                {"index": i, "text": c.get("choice_text")} 
                for i, c in enumerate(choices_data)
            ]
            return frame
        
        return frame

    def next(self) -> Dict[str, Any]:
        """Advances the story state."""
        # Trigger prefetch for subsequent lines
        self._check_prefetch()

        if self.state.is_waiting_for_choice:
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
