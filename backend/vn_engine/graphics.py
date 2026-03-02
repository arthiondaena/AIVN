import pygame
from typing import List, Dict, Any, Tuple
from abc import ABC, abstractmethod

class Sprite:
    """
    Represents a visual element on screen.
    Based on Source_code/Application/Assets/Scripts/Render/Sprite.py
    """
    def __init__(self, 
                 image: pygame.Surface, 
                 position: Tuple[int, int], 
                 layer: int = 0,
                 name: str = "unnamed"):
        self.image = image
        self.rect = self.image.get_rect(topleft=position)
        self.layer = layer
        self.name = name
        self.visible = True
        self.alpha = 255

    def set_position(self, pos: Tuple[int, int]):
        self.rect.topleft = pos

    def set_image(self, image: pygame.Surface):
        old_center = self.rect.center
        self.image = image
        self.rect = self.image.get_rect(center=old_center)

    def draw(self, surface: pygame.Surface):
        if self.visible:
            if self.alpha < 255:
                self.image.set_alpha(self.alpha)
            surface.blit(self.image, self.rect)

class Layer:
    """
    Manages a collection of sprites at a specific z-index.
    Based on Source_code/Application/Assets/Scripts/Render/Layer.py
    """
    def __init__(self, z_index: int):
        self.z_index = z_index
        self.sprites: List[Sprite] = []

    def add(self, sprite: Sprite):
        if sprite not in self.sprites:
            self.sprites.append(sprite)
            # Sort by layer just in case, though layer usually holds sprites of same z-index
            # Actually, inside a layer, we might want to respect insertion order or y-sort

    def remove(self, sprite: Sprite):
        if sprite in self.sprites:
            self.sprites.remove(sprite)

    def draw(self, surface: pygame.Surface):
        for sprite in self.sprites:
            sprite.draw(surface)

    def clear(self):
        self.sprites.clear()

class Render:
    """
    Main renderer that manages layers and draws to the screen.
    Based on Source_code/Application/Assets/Scripts/Render/Render.py
    """
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.layers: Dict[int, Layer] = {}
        # Pre-define standard layers
        self.layers[0] = Layer(0) # Background
        self.layers[1] = Layer(1) # Characters (Back)
        self.layers[2] = Layer(2) # Characters (Front)
        self.layers[3] = Layer(3) # UI / Text

    def get_layer(self, z_index: int) -> Layer:
        if z_index not in self.layers:
            self.layers[z_index] = Layer(z_index)
            # Re-sort layers logic might be needed if we iterate dict keys, 
            # but dicts preserve insertion order in modern python. 
            # Better to sort when drawing.
        return self.layers[z_index]

    def add_sprite(self, sprite: Sprite):
        layer = self.get_layer(sprite.layer)
        layer.add(sprite)

    def remove_sprite(self, sprite: Sprite):
        if sprite.layer in self.layers:
            self.layers[sprite.layer].remove(sprite)

    def clear(self):
        for layer in self.layers.values():
            layer.clear()
        self.screen.fill((0, 0, 0))

    def render(self):
        self.screen.fill((0, 0, 0)) # Clear screen
        
        # Sort layers by z-index
        sorted_keys = sorted(self.layers.keys())
        for key in sorted_keys:
            self.layers[key].draw(self.screen)
        
        pygame.display.flip()
