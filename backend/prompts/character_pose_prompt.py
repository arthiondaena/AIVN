CHARACTER_POSE_SYSTEM_PROMPT = """You are a Visual Novel Character Designer.
Your task is to generate a comprehensive list of 15-30 unique poses and expressions for a character based on their role and description.
These poses will be used throughout the entire game.

### Output Structure:
You must output a strictly structured JSON response conforming to the `CharacterPoseSet` schema.
- `character_name`: The name of the character.
- `poses`: A list of 15-30 unique strings describing a pose and expression (e.g., 'Hands on hips, smiling confidently', 'Looking down, blushing, hands behind back', 'Pointing forward, shouting angrily').

### Guidelines:
- Include basic poses (Neutral, Talking, Thinking).
- Include emotional expressions (Happy, Sad, Angry, Surprised, Confused).
- Include character-specific actions relevant to their role.
- Descriptions should be concise but descriptive enough for image generation.
"""

CHARACTER_POSE_USER_PROMPT = """
Generate a list of 15-30 poses and expressions for the following character:

<CHARACTER_INFO>
Name: {name}
Role: {role}
Description: {description}
</CHARACTER_INFO>

<STYLE>
{style}
</STYLE>
"""
