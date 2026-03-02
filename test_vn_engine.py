import unittest
from unittest.mock import MagicMock
from backend.vn_engine.state_manager import SceneManager, GameState
from backend.vn_engine.loader import StoryLoader

class TestSceneManager(unittest.TestCase):
    def setUp(self):
        # Mock data structure
        self.mock_story_data = {
            "story": {
                "chapters": [
                    {
                        "id": "ch1",
                        "scenes": [
                            {"id": "scene1", "title": "Scene 1"},
                            {"id": "scene2", "title": "Scene 2"}
                        ]
                    },
                    {
                        "id": "ch2",
                        "scenes": [
                            {"id": "scene3", "title": "Scene 3"}
                        ]
                    }
                ]
            }
        }
        
        # Mock scene content
        self.mock_scene_content = {
            "scene1": {
                "scene_id": "scene1",
                "initial_location_name": "Classroom",
                "initial_bgm": "happy_tune.mp3",
                "main_dialogue": [
                    {"dialogue_id": "d1", "speaker": "Alice", "text": "Hello!", "character_pose_expression": "smile"},
                    {"dialogue_id": "d2", "speaker": "Bob", "text": "Hi Alice.", "character_pose_expression": "neutral"}
                ],
                "choices_and_branches": [
                    {
                        "choice_text": "Be nice",
                        "branching_dialogue": [
                            {"dialogue_id": "b1", "speaker": "Bob", "text": "Nice weather today."}
                        ],
                        "leads_to_scene_id": "scene2"
                    },
                    {
                        "choice_text": "Be mean",
                        "branching_dialogue": [
                            {"dialogue_id": "b2", "speaker": "Bob", "text": "Go away."}
                        ],
                        # No leads_to_scene_id, should fall through to next linear scene (scene2)
                    }
                ]
            },
            "scene2": {
                "scene_id": "scene2",
                "initial_location_name": "Hallway",
                "main_dialogue": [
                    {"dialogue_id": "d3", "speaker": "Narrator", "text": "Walking down the hall."}
                ]
            },
            "scene3": {
                "scene_id": "scene3",
                "main_dialogue": [
                    {"dialogue_id": "d4", "speaker": "Alice", "text": "Chapter 2 starts."}
                ]
            }
        }

        # Mock Loader
        self.loader = MagicMock(spec=StoryLoader)
        self.loader.data = self.mock_story_data
        self.loader.get_scene_content.side_effect = lambda sid: self.mock_scene_content.get(sid)
        
        self.manager = SceneManager(self.loader)

    def test_start_story(self):
        frame = self.manager.start_story()
        
        self.assertEqual(frame["scene_id"], "scene1")
        self.assertEqual(frame["background"], "Classroom")
        self.assertEqual(frame["bgm"], "happy_tune.mp3")
        self.assertEqual(frame["dialogue"]["text"], "Hello!")
        self.assertEqual(frame["characters"]["Alice"], "smile")
        
    def test_linear_progression(self):
        self.manager.start_story() # Shows "Hello!"
        
        # Next line
        frame = self.manager.next()
        self.assertEqual(frame["dialogue"]["text"], "Hi Alice.")
        self.assertEqual(frame["characters"]["Bob"], "neutral")
        
        # End of main dialogue -> Choices
        frame = self.manager.next()
        self.assertTrue(frame["is_choice"])
        self.assertEqual(len(frame["choices"]), 2)
        self.assertEqual(frame["choices"][0]["text"], "Be nice")
        # Should still show last dialogue
        self.assertEqual(frame["dialogue"]["text"], "Hi Alice.")
        
    def test_make_choice_and_branch(self):
        self.manager.start_story()
        self.manager.next() # "Hi Alice."
        self.manager.next() # Choices
        
        # Choose "Be nice"
        frame = self.manager.make_choice(0)
        self.assertFalse(frame["is_choice"])
        self.assertEqual(frame["dialogue"]["text"], "Nice weather today.")
        
        # End of branch -> Jump to scene2
        frame = self.manager.next()
        self.assertEqual(frame["scene_id"], "scene2")
        self.assertEqual(frame["background"], "Hallway")
        self.assertEqual(frame["dialogue"]["text"], "Walking down the hall.")

    def test_make_choice_fallback(self):
        self.manager.start_story()
        self.manager.next() # "Hi Alice."
        self.manager.next() # Choices
        
        # Choose "Be mean" (no explicit jump)
        frame = self.manager.make_choice(1)
        self.assertEqual(frame["dialogue"]["text"], "Go away.")
        
        # End of branch -> Fallback to next linear scene (scene2)
        frame = self.manager.next()
        self.assertEqual(frame["scene_id"], "scene2")

    def test_chapter_transition(self):
        # Setup state to be at end of scene2
        self.manager.start_story()
        self.manager.state.current_chapter_index = 0
        self.manager.state.current_scene_index = 1
        self.manager.state.current_scene_id = "scene2"
        self.manager.state.current_dialogue_index = 0 
        
        # scene2 has 1 line. next() should finish it.
        frame = self.manager.next()
        # scene2 has no choices, so it should go to next scene (scene3 in ch2)
        self.assertEqual(frame["scene_id"], "scene3")
        self.assertEqual(frame["dialogue"]["text"], "Chapter 2 starts.")
        self.assertEqual(self.manager.state.current_chapter_index, 1)

if __name__ == '__main__':
    unittest.main()
