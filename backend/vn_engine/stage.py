import pygame
import logging
from typing import Dict, Optional, List, Tuple, Any
from .graphics import Sprite, Render
from .utils import AssetLoader
from .loader import StoryLoader

logger = logging.getLogger(__name__)

class Character:
    """
    Visual representation of a character.
    Based on Source_code/Application/Assets/Scripts/Game_objects/Character.py
    """
    def __init__(self, name: str, asset_loader: AssetLoader):
        self.name = name
        self.asset_loader = asset_loader
        self.sprite: Optional[Sprite] = None
        self.current_pose = "default"
        self.position = "center" # left, center, right
        
        # Placeholder surface if no asset found
        self.default_surface = pygame.Surface((200, 400))
        self.default_surface.fill((255, 100, 100)) # Reddish for characters

    def set_pose(self, pose_name: str, asset_path: Optional[str] = None):
        self.current_pose = pose_name
        
        surface = None
        if asset_path:
             surface = self.asset_loader.load_image(asset_path)
        
        if not surface:
            # Try to construct path if not provided
            # Standard path: characters/{name}/{pose}.png
            # Or from the screenplay assets map which we don't strictly have access to here directly
            # For now, use placeholder
             surface = self.default_surface
             # Draw name on placeholder
             font = pygame.font.Font(None, 36)
             text = font.render(self.name, True, (255, 255, 255))
             surface.blit(text, (10, 10))

        if self.sprite:
            self.sprite.set_image(surface)
        else:
            self.sprite = Sprite(surface, (0, 0), layer=2, name=self.name)

        self._update_position()

    def set_position_name(self, pos_name: str, screen_width: int):
        self.position = pos_name.lower()
        self._update_position(screen_width)

    def _update_position(self, screen_width: int = 1280):
        if not self.sprite:
            return
            
        rect = self.sprite.rect
        y_pos = 720 - rect.height # Bottom aligned
        
        x_pos = (screen_width // 2) - (rect.width // 2) # Center default
        
        if self.position == "left":
            x_pos = (screen_width // 4) - (rect.width // 2)
        elif self.position == "right":
            x_pos = (screen_width * 3 // 4) - (rect.width // 2)
        
        self.sprite.set_position((x_pos, y_pos))

    def set_visible(self, visible: bool):
        if self.sprite:
            self.sprite.visible = visible


class Background:
    """
    Manages background image.
    Based on Source_code/Application/Assets/Scripts/Game_objects/Background.py
    """
    def __init__(self, asset_loader: AssetLoader, screen_size: Tuple[int, int]):
        self.asset_loader = asset_loader
        self.screen_size = screen_size
        self.sprite: Optional[Sprite] = None
        
        self.default_surface = pygame.Surface(screen_size)
        self.default_surface.fill((50, 50, 50)) # Gray default

    def set_image(self, image_name: str, asset_path: Optional[str] = None):
        surface = None
        if asset_path:
            surface = self.asset_loader.load_image(asset_path, convert_alpha=False)
        
        if not surface:
            # Placeholder
            surface = self.default_surface.copy()
            font = pygame.font.Font(None, 74)
            text = font.render(image_name, True, (200, 200, 200))
            text_rect = text.get_rect(center=(self.screen_size[0]//2, self.screen_size[1]//2))
            surface.blit(text, text_rect)

        # Scale to fit screen if needed
        if surface.get_size() != self.screen_size:
            surface = pygame.transform.scale(surface, self.screen_size)

        if self.sprite:
            self.sprite.set_image(surface)
        else:
            self.sprite = Sprite(surface, (0, 0), layer=0, name="background")


class StageDirector:
    """
    Manages the visual state of the game: Backgrounds, Characters, and Text.
    Based on Source_code/Application/Assets/Scripts/Core/Stage_Director.py
    """
    def __init__(self, render: Render, asset_loader: AssetLoader, story_loader: StoryLoader):
        self.render = render
        self.asset_loader = asset_loader
        self.story_loader = story_loader
        self.screen_size = render.screen.get_size()
        
        self.background = Background(asset_loader, self.screen_size)
        self.characters: Dict[str, Character] = {}
        
        # Dialogue box sprite
        self.textbox_sprite = self._create_textbox()
        self.render.add_sprite(self.textbox_sprite)
        
        # Text sprites
        self.name_text_sprite = Sprite(pygame.Surface((0,0)), (0,0), layer=3, name="name_text")
        self.dialogue_text_sprite = Sprite(pygame.Surface((0,0)), (0,0), layer=3, name="dialogue_text")
        self.render.add_sprite(self.name_text_sprite)
        self.render.add_sprite(self.dialogue_text_sprite)

    def _create_textbox(self) -> Sprite:
        width, height = self.screen_size
        box_height = int(height * 0.25)
        surface = pygame.Surface((width, box_height))
        surface.fill((0, 0, 0))
        surface.set_alpha(200) # Semi-transparent
        
        pos = (0, height - box_height)
        return Sprite(surface, pos, layer=3, name="textbox")

    def update_stage(self, frame_state: Dict[str, Any]):
        """
        Updates visual elements based on the current game state frame.
        """
        # 1. Update Background
        bg_name = frame_state.get("background")
        if bg_name:
            # Try to resolve path from story loader assets
            bg_path = self.story_loader.get_asset_path("backgrounds", bg_name)
            self.background.set_image(bg_name, bg_path)
            if self.background.sprite not in self.render.layers[0].sprites:
                self.render.add_sprite(self.background.sprite)

        # 2. Update Characters
        # Hide all first
        for char in self.characters.values():
            char.set_visible(False)
            
        char_states = frame_state.get("characters", {})
        dialogue = frame_state.get("dialogue")
        current_speaker = dialogue.get("speaker") if dialogue else None

        for name, pose in char_states.items():
            # Only show if they are the speaker (unless it's a special scene setup, 
            # but user requested to enforce only the character talking)
            if current_speaker and name != current_speaker:
                continue

            if name not in self.characters:
                self.characters[name] = Character(name, self.asset_loader)
            
            char = self.characters[name]
            
            # Construct key for pose lookup: "Name_PoseDescription"
            pose_key = f"{name}_{pose}"
            pose_path = self.story_loader.get_asset_path("poses", pose_key)
            
            # Fallback 1: If pose not found, try base character image
            if not pose_path:
                pose_path = self.story_loader.get_asset_path("characters", name)
            
            # Fallback 2: Try matching with underscores
            if not pose_path:
                normalized_name = name.replace(" ", "_")
                pose_path = self.story_loader.get_asset_path("characters", normalized_name)
                if not pose_path:
                    pose_path = self.story_loader.get_asset_path("characters", f"{normalized_name}_base")

            # Fallback 3: Search for any asset starting with character name
            if not pose_path:
                char_assets = self.story_loader.data.get("assets", {}).get("characters", {})
                for k, v in char_assets.items():
                    if k.lower().startswith(name.lower().split()[0]): # Match by first name
                        pose_path = v
                        break

            char.set_pose(pose, pose_path)
            char.set_position_name("center", self.screen_size[0]) # Default center for now
            char.set_visible(True)
            
            if char.sprite and char.sprite not in self.render.layers[2].sprites:
                self.render.add_sprite(char.sprite)

        # 3. Update Text
        dialogue = frame_state.get("dialogue")
        if dialogue:
            speaker = dialogue.get("speaker", "???")
            text = dialogue.get("text", "")
            self._render_text(speaker, text)
        else:
            self._render_text("", "")
            
        # 4. Choices (rendered as text buttons for now, logic elsewhere? or overlay)
        # For simplicity, render choices as text overlay if present
        is_choice = frame_state.get("is_choice", False)
        if is_choice:
            # We might need a "ChoiceRenderer" or specialized handling
            # Just clearing text box for now or showing last text
            pass

    def _render_text(self, name: str, text: str):
        font = self.asset_loader.load_font(None, 32)
        name_font = self.asset_loader.load_font(None, 40)
        
        # Render Name
        if name:
            name_surf = name_font.render(name, True, (255, 255, 100)) # Yellowish
            self.name_text_sprite.set_image(name_surf)
            # Position above textbox
            tb_rect = self.textbox_sprite.rect
            self.name_text_sprite.set_position((tb_rect.x + 20, tb_rect.y - 45))
            self.name_text_sprite.visible = True
        else:
            self.name_text_sprite.visible = False

        # Render Dialogue with word wrap
        if text:
            tb_rect = self.textbox_sprite.rect
            max_width = tb_rect.width - 60
            words = text.split(' ')
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                w, _ = font.size(test_line)
                if w <= max_width:
                    current_line.append(word)
                else:
                    lines.append(' '.join(current_line))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            # Create a combined surface for all lines
            line_height = font.get_linesize()
            total_height = max(1, line_height * len(lines))
            combined_surf = pygame.Surface((max_width, total_height), pygame.SRCALPHA)
            
            for i, line in enumerate(lines):
                line_surf = font.render(line, True, (255, 255, 255))
                combined_surf.blit(line_surf, (0, i * line_height))
                
            self.dialogue_text_sprite.set_image(combined_surf)
            self.dialogue_text_sprite.set_position((tb_rect.x + 30, tb_rect.y + 25))
            self.dialogue_text_sprite.visible = True
        else:
            self.dialogue_text_sprite.visible = False
