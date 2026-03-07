import argparse
import os
import sys
from pathlib import Path

# Add project root to python path to allow imports from backend
sys.path.append(str(Path(__file__).parents[2]))

from backend.vn_engine.core import GameEngine

def main():
    # Force stdout to be unbuffered
    import logging
    # logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)

    parser = argparse.ArgumentParser(description="Run the Visual Novel Engine")
    parser.add_argument("--screenplay", help="Path to screenplay.json file")
    
    args = parser.parse_args()
    
    # Default for testing if not provided
    default_screenplay = "backend/services/output/2/screenplay.json"
    
    if args.screenplay:
        screenplay_path = args.screenplay
    else:
        screenplay_path = default_screenplay
        if not os.path.exists(screenplay_path):
             print(f"Default screenplay not found at {screenplay_path}")
             # Search for any screenplay.json in output dir as fallback
             base_output = Path("backend/services/output")
             if base_output.exists():
                 found = list(base_output.glob("*/screenplay.json"))
                 if found:
                     screenplay_path = str(found[0])
                     print(f"Found screenplay at {screenplay_path}, using it.")
                 else:
                     print("No screenplay found. Please generate one first.")
                     return
             else:
                 print("Output directory not found.")
                 return

    print(f"Starting engine with screenplay: {screenplay_path}")
    
    try:
        engine = GameEngine(screenplay_path)
        engine.start()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
