import argparse
import os
import sys
import logging
from pathlib import Path

# Add project root to python path to allow imports from backend
sys.path.append(str(Path(__file__).parents[2]))

from vn_engine.core import GameEngine

logger = logging.getLogger(__name__)

def run_game(screenplay_path: str = None):
    # Default for testing if not provided
    default_screenplay = "backend/services/output/2/screenplay.json"
    
    if screenplay_path:
        pass
    else:
        screenplay_path = default_screenplay
        if not os.path.exists(screenplay_path):
             logger.warning(f"Default screenplay not found at {screenplay_path}")
             # Search for any screenplay.json in output dir as fallback
             base_output = Path("backend/services/output")
             if base_output.exists():
                 found = list(base_output.glob("*/screenplay.json"))
                 if found:
                     screenplay_path = str(found[0])
                     logger.info(f"Found screenplay at {screenplay_path}, using it.")
                 else:
                     logger.error("No screenplay found. Please generate one first.")
                     return
             else:
                 logger.error("Output directory not found.")
                 return

    logger.info(f"Starting engine with screenplay: {screenplay_path}")
    
    try:
        engine = GameEngine(screenplay_path)
        engine.start()
    except KeyboardInterrupt:
        logger.info("Exiting...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Run the Visual Novel Engine")
    parser.add_argument("--screenplay", help="Path to screenplay.json file")
    
    args = parser.parse_args()
    run_game(args.screenplay)

if __name__ == "__main__":
    main()
