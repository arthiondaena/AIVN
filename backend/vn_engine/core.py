import pygame
import sys
from typing import Optional, Dict, List
from pathlib import Path

# Add project root to python path to allow imports from backend
# This is needed because `core.py` might be run directly or imported from `main.py` 
# which is inside the package.
import sys
sys.path.append(str(Path(__file__).parents[2]))

from backend.vn_engine.config import settings
from backend.vn_engine.utils import AssetLoader
from backend.vn_engine.loader import StoryLoader
from backend.vn_engine.state_manager import SceneManager, GameState
from backend.vn_engine.graphics import Render, Sprite
from backend.vn_engine.stage import StageDirector

class GameEngine:
    """
    Main engine class managing the game loop, input, and state updates.
    Based on Source_code/Application/Assets/Scripts/Core/Game_Master.py
    """
    def __init__(self, screenplay_path: str):
        print("DEBUG: GameEngine initialized", flush=True)
        pygame.init()
        # Initialize mixer with settings matching the generated audio (24kHz)
        pygame.mixer.init(frequency=24000, size=-16, channels=2, buffer=4096) 
        pygame.display.set_caption(settings.get_window_title())
        
        self.screen_size = settings.get_window_size()
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.fps = settings.get_frames_per_second()
        
        # Initialize subsystems
        self.asset_loader = AssetLoader("output")
        self.story_loader = StoryLoader(screenplay_path)
        self.render = Render(self.screen)
        
        # Logic
        self.scene_manager = SceneManager(self.story_loader)
        self.stage_director = StageDirector(self.render, self.asset_loader, self.story_loader)
        
        self.is_running = False
        self.current_frame: Optional[Dict] = None

        # UI State
        self.waiting_for_input = False
        self.choices_visible = False
        self.choice_buttons: List[Sprite] = []

    def start(self):
        """Initializes game state and starts the loop."""
        try:
            self.current_frame = self.scene_manager.start_story()
            self.stage_director.update_stage(self.current_frame)
            self._update_audio() # Play initial audio if any
            self._update_ui_state()
            self.is_running = True
            self._run_loop()
        except Exception as e:
            print(f"Failed to start engine: {e}")
            import traceback
            traceback.print_exc()

    def _run_loop(self):
        while self.is_running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(self.fps)

        pygame.quit()
        sys.exit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: # Left click
                    self._handle_click(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    self._advance_story()
                elif event.key == pygame.K_ESCAPE:
                    self.is_running = False
                elif event.key == pygame.K_1: # Debug choice 1
                    self._handle_choice(0)
                elif event.key == pygame.K_2: # Debug choice 2
                    self._handle_choice(1)

    def _handle_click(self, pos):
        # Check choice buttons if visible
        if self.choices_visible:
            for i, sprite in enumerate(self.choice_buttons):
                if sprite.rect.collidepoint(pos):
                    self._handle_choice(i)
                    return
        
        # Otherwise, advance dialogue
        self._advance_story()

    def _handle_choice(self, index: int):
        if not self.choices_visible:
            return
            
        try:
            # We need to find the actual index in the current frame choices list
            # The UI buttons correspond directly to the list
            choices = self.current_frame.get("choices", [])
            if 0 <= index < len(choices):
                self.current_frame = self.scene_manager.make_choice(index)
                self.stage_director.update_stage(self.current_frame)
                self._update_audio()
                self._update_ui_state()
        except Exception as e:
            print(f"Error making choice {index}: {e}")
            import traceback
            traceback.print_exc()

    def _advance_story(self):
        if self.choices_visible:
            return # Must make a choice

        try:
            # Check if scene ended (check next call)
            # Actually next() returns the *next* state.
            # If current frame says "END", we stop or show credits.
            if self.current_frame and self.current_frame.get("scene_id") == "END":
                print("Story Ended.")
                self.is_running = False
                return

            self.current_frame = self.scene_manager.next()
            self.stage_director.update_stage(self.current_frame)
            self._update_audio()
            self._update_ui_state()
            
        except Exception as e:
            print(f"Error advancing story: {e}")
            import traceback
            traceback.print_exc()

    def _update_audio(self):
        """Handles voiceover playback for the current frame."""
        print("DEBUG: _update_audio called", flush=True)
        if not self.current_frame:
            print("DEBUG: No current frame", flush=True)
            return

        # Stop previous voiceover
        # We might want to keep BGM playing, so we should use a specific channel for voice
        # But for now, pygame.mixer.music is usually BGM, and we can use Sound for voice.
        
        audio_path = self.current_frame.get("audio_path")
        print(f"DEBUG: Current state audio path: {audio_path}", flush=True)
        
        # Stop any currently playing voice on the dedicated voice channel
        # We'll reserve Channel 0 for voice
        voice_channel = pygame.mixer.Channel(0)
        if voice_channel.get_busy():
            voice_channel.stop()

        if audio_path:
            # Ensure path is absolute or correct relative to CWD
            # The engine runs from root, audio paths from cache might be relative to backend or absolute
            p_path = Path(audio_path)
            if not p_path.is_absolute():
                # Try to resolve relative to CWD
                if not p_path.exists():
                     # Try relative to backend if needed, though typically cache paths are absolute or relative to root
                     pass

            if p_path.exists():
                try:
                    print(f"DEBUG: Playing audio: {audio_path}", flush=True)
                    print(f"[DEBUG] Playing audio: {p_path}")
                    sound = pygame.mixer.Sound(str(p_path))
                    # Set volume explicitly just in case
                    sound.set_volume(1.0)
                    voice_channel.play(sound)
                except Exception as e:
                    print(f"Failed to play audio {audio_path}: {e}")
            else:
                print(f"[DEBUG] Audio file not found: {p_path}")
        else:
             pass # No audio for this line

    def _update_ui_state(self):
        if not self.current_frame:
            return

        self.choices_visible = self.current_frame.get("is_choice", False)
        
        # Clear old choice buttons
        for btn in self.choice_buttons:
            self.render.remove_sprite(btn)
        self.choice_buttons.clear()
        
        if self.choices_visible:
            choices = self.current_frame.get("choices", [])
            self._create_choice_buttons(choices)

    def _create_choice_buttons(self, choices: List[Dict]):
        # Simple vertical list of buttons in the center
        start_y = 200
        spacing = 60
        font = pygame.font.Font(None, 36)
        
        for i, choice in enumerate(choices):
            text = choice.get("text", f"Choice {i+1}")
            
            # Create button surface
            btn_w, btn_h = 600, 50
            surf = pygame.Surface((btn_w, btn_h))
            surf.fill((50, 50, 150)) # Blue
            
            # Render text centered
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(btn_w//2, btn_h//2))
            surf.blit(text_surf, text_rect)
            
            # Create sprite
            x = (self.screen_size[0] - btn_w) // 2
            y = start_y + (i * spacing)
            
            sprite = Sprite(surf, (x, y), layer=4, name=f"choice_{i}")
            self.choice_buttons.append(sprite)
            self.render.add_sprite(sprite)

    def _update(self):
        pass # Animations would go here

    def _draw(self):
        self.render.render()
