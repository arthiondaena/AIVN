import argparse
import asyncio
import sys
import os
import logging
import uvicorn

from core.logging_config import setup_logging
from core.database import SessionLocal
from services.story_workflow import StoryWorkflowService

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

def main():
    parser = argparse.ArgumentParser(description="AIVN: AI Visual Novel Generator Backend")
    parser.add_argument("--synopsis", type=str, help="Short summary of the story to generate")
    parser.add_argument("--style", type=str, default="anime style, high quality", help="Visual style for backgrounds and characters")
    parser.add_argument("--story_id", type=int, help="Optional: Skip generation and use existing story ID")
    parser.add_argument("--cli", action="store_true", help="Run via CLI to generate story instead of starting server")
    
    args = parser.parse_args()

    if not args.cli:
        logger.info("Starting AIVN Web Server...")
        uvicorn.run("api_app:app", host="0.0.0.0", port=8000, reload=True)
        return

    # CLI Generation Logic
    story_id = args.story_id
    if not story_id:
        if not args.synopsis:
            logger.error("Error: --synopsis is required if --story_id is not provided.")
            return
        story_id = asyncio.run(run_workflow(args.synopsis, args.style))

if __name__ == "__main__":
    main()
