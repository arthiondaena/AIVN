import os
import json
import logging
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from vn_engine.headless import HeadlessGameEngine

logger = logging.getLogger(__name__)

app = FastAPI(title="AIVN Web Game Engine")

# Mount output directory as static assets
# Ensure output directory exists before mounting to avoid errors
os.makedirs("output", exist_ok=True)
app.mount("/assets", StaticFiles(directory="output"), name="assets")

# Optional: serve the static HTML frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Store active sessions
active_engines = {}

@app.get("/play/{story_id}", response_class=HTMLResponse)
async def play_story(story_id: str):
    """Parent page that embeds the iframe."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AIVN Player</title>
        <style>
            body {{ margin: 0; overflow: hidden; background: #000; }}
            iframe {{ width: 100vw; height: 100vh; border: none; }}
        </style>
    </head>
    <body>
        <iframe src="/static/game.html?story_id={story_id}"></iframe>
    </body>
    </html>
    """

@app.websocket("/ws/game/{story_id}")
async def game_websocket(websocket: WebSocket, story_id: str):
    await websocket.accept()
    
    # Locate screenplay.json
    screenplay_path = f"output/{story_id}/screenplay.json"
    if not os.path.exists(screenplay_path):
        await websocket.send_json({"error": f"Screenplay not found for story ID {story_id}"})
        await websocket.close()
        return

    # Initialize headless engine
    engine = HeadlessGameEngine(screenplay_path)
    
    try:
        # Start engine and send first frame
        initial_frame = engine.start()
        await websocket.send_json(initial_frame)
        
        while True:
            # Wait for client actions
            data = await websocket.receive_text()
            action_data = json.loads(data)
            action = action_data.get("action")
            
            frame = None
            if action == "advance":
                frame = engine.advance()
            elif action == "choice":
                index = action_data.get("index")
                if index is not None:
                    frame = engine.make_choice(index)
            
            if frame:
                await websocket.send_json(frame)
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from story {story_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()
