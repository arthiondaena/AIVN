import argparse
import asyncio
import sys
import os
import logging
from pathlib import Path

from core.logging_config import setup_logging
from core.database import SessionLocal
from services.story_workflow import StoryWorkflowService
from vn_engine.converter import StoryConverter
from vn_engine.main import run_game

# Initialize Logger
setup_logging()
logger = logging.getLogger("AIVN_Main")

async def run_workflow(synopsis: str, style: str):
    logger.info("--- Phase 1: Story Generation ---")
    db = SessionLocal()
    try:
        workflow = StoryWorkflowService(db)
        story = await workflow.generate_full_story(synopsis, style)
        story_id = story.id
        logger.info(f"Story generated with ID: {story_id}")
        return story_id
    finally:
        db.close()

def run_conversion(story_id: int):
    logger.info("--- Phase 2: Database to Screenplay Conversion ---")
    # Note: StoryWorkflowService currently saves outputs to "output" relative to where it's run.
    # We should ensure the paths match.
    converter = StoryConverter(str(story_id), base_output_dir="output")
    screenplay_path = converter.convert()
    if screenplay_path:
        logger.info(f"Screenplay successfully generated at: {screenplay_path}")
        return screenplay_path
    else:
        logger.error("Failed to generate screenplay.")
        return None

def main():
    parser = argparse.ArgumentParser(description="AIVN: AI Visual Novel Generator & Engine")
    parser.add_argument("--synopsis", type=str, help="Short summary of the story to generate")
    parser.add_argument("--style", type=str, default="anime style, high quality", help="Visual style for backgrounds and characters")
    parser.add_argument("--story_id", type=int, help="Optional: Skip generation and use existing story ID")
    parser.add_argument("--skip_game", action="store_true", help="Only generate the story and screenplay, don't run the game")
    
    args = parser.parse_args()

    # Step 1: Story Generation
    story_id = args.story_id
    if not story_id:
        if not args.synopsis:
            logger.error("Error: --synopsis is required if --story_id is not provided.")
            return
        story_id = asyncio.run(run_workflow(args.synopsis, args.style))

    # Step 2: Conversion
    screenplay_path = run_conversion(story_id)
    if not screenplay_path:
        return

    # Step 3: Run Game
    if not args.skip_game:
        logger.info("--- Phase 3: Launching Game Engine ---")
        run_game(screenplay_path)
    else:
        logger.info("Generation complete. Game launch skipped.")

if __name__ == "__main__":
    main()
