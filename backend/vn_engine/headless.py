import logging
from typing import Optional, Dict, Any, List
from vn_engine.loader import StoryLoader
from vn_engine.state_manager import SceneManager

logger = logging.getLogger(__name__)

class HeadlessGameEngine:
    """
    Headless version of GameEngine that doesn't use pygame.
    Yields frame data (JSON serializable) for the web client.
    """
    def __init__(self, screenplay_path: str):
        logger.info("Initializing HeadlessGameEngine...")
        self.story_loader = StoryLoader(screenplay_path)
        self.scene_manager = SceneManager(self.story_loader)
        self.current_frame: Optional[Dict[str, Any]] = None

    def start(self) -> Dict[str, Any]:
        """Initializes game state and returns the first frame."""
        self.current_frame = self.scene_manager.start_story()
        return self._format_frame(self.current_frame)

    def advance(self) -> Dict[str, Any]:
        """Advances the story by one step and returns the new frame."""
        if not self.current_frame:
            return {"error": "Engine not started"}
            
        if self.current_frame.get("scene_id") == "END":
            return {"scene_id": "END"}
            
        if self.current_frame.get("is_choice", False):
            # Cannot advance if waiting for choice
            return self._format_frame(self.current_frame)

        self.current_frame = self.scene_manager.next()
        return self._format_frame(self.current_frame)

    def make_choice(self, index: int) -> Dict[str, Any]:
        """Makes a choice and returns the new frame."""
        if not self.current_frame or not self.current_frame.get("is_choice", False):
            return {"error": "Not waiting for a choice"}
            
        try:
            self.current_frame = self.scene_manager.make_choice(index)
            return self._format_frame(self.current_frame)
        except Exception as e:
            logger.error(f"Error making choice {index}: {e}")
            return {"error": str(e)}

    def _format_frame(self, frame: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats paths in the frame to be accessible via the web server.
        """
        if not frame or "error" in frame or frame.get("scene_id") == "END":
            return frame

        formatted = frame.copy()
        
        # Format background path using the story loader's asset dictionary
        bg_name = formatted.get("background")
        if bg_name:
            bg_path = self.story_loader.get_asset_path("backgrounds", bg_name)
            if bg_path:
                # bg_path is typically something like "2/backgrounds/..."
                # our web server serves the whole output dir as /assets
                formatted["background_url"] = f"/assets/{bg_path.replace(chr(92), '/')}"
            else:
                # If we don't have it in assets, just try a generic guess
                story_id = self.story_loader.screenplay_path.parent.name
                formatted["background_url"] = f"/assets/{story_id}/backgrounds/{bg_name}.png"
                
        # Format character paths
        chars = formatted.get("characters", {})
        formatted_chars = {}
        for char_name, pose in chars.items():
            pose_path = self.story_loader.get_asset_path("poses", pose)
            if not pose_path:
                pose_path = self.story_loader.get_asset_path("poses", f"{char_name}_{pose}")
                logger.info(f"Pose path for {char_name} (with underscores): {pose_path}")

            if not pose_path:
                # One last try: if pose contains specific character info or is a full description, 
                # we might be unable to map it directly if the generator missed it.
                # Try to find a matching pose in the assets dictionary by checking if pose is in the key
                assets = self.story_loader.data.get("assets", {}).get("poses", {})
                for k, v in assets.items():
                    if pose in k or k in pose:
                        # Re-run get_asset_path with the correct key to get the transparent path
                        pose_path = self.story_loader.get_asset_path("poses", k)
                        break

            if pose_path:
                formatted_chars[char_name] = f"/assets/{pose_path.replace(chr(92), '/')}"
            else:
                # If all else fails, log it and don't send a broken URL
                logger.warning(f"Could not find pose asset for {char_name}: {pose}")
                
        formatted["characters"] = formatted_chars
            
        # Format audio path
        audio = formatted.get("audio_path")
        if audio:
            # We just want to serve the relative path from output directory.
            # Example audio path might be an absolute path like D:\\...\\output\\11\\audio\\scene1.wav
            try:
                # Ensure it's a string and convert slashes
                audio_str = str(audio).replace('\\', '/')
                if '/output/' in audio_str:
                    parts = audio_str.split('/output/')
                    formatted["audio_url"] = f"/assets/{parts[-1]}"
                else:
                    # Maybe it's already relative? Let's check if it starts with the story id
                    # Since we are running in backend root, 'audio' could be relative to output
                    # Let's try parsing from story_id
                    story_id = self.story_loader.screenplay_path.parent.name
                    if story_id in audio_str:
                        # Extract everything from story_id onwards
                        parts = audio_str.split(f'/{story_id}/')
                        if len(parts) > 1:
                            formatted["audio_url"] = f"/assets/{story_id}/{parts[-1]}"
                        else:
                            formatted["audio_url"] = f"/assets/{audio_str}"
                    else:
                        formatted["audio_url"] = f"/assets/{audio_str}"
            except Exception as e:
                logger.error(f"Error formatting audio path: {e}")
                pass

        return formatted
