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
        pygame.init()
        pygame.display.set_caption(settings.get_window_title())
        
        self.screen_size = settings.get_window_size()
        self.screen = pygame.display.set_mode(self.screen_size)
        self.clock = pygame.time.Clock()
        self.fps = settings.get_frames_per_second()
        
        # Initialize subsystems
        self.asset_loader = AssetLoader(str(Path(screenplay_path).parent))
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
            self._update_ui_state()
            
        except Exception as e:
            print(f"Error advancing story: {e}")
            import traceback
            traceback.print_exc()

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
