import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from agent import WebAgent

app = FastAPI()

# Allow all CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent instance
agent = None
# Active WebSocket connections
active_connections = []

@app.on_event("startup")
async def startup_event():
    global agent
    agent = WebAgent(logger=broadcast_log)
    # Start the browser immediately
    asyncio.create_task(agent.start_browser())

async def broadcast_log(message, type="info"):
    dead_connections = []
    payload = json.dumps({"type": "log", "message": message, "logType": type})
    for websocket in active_connections:
        try:
            await websocket.send_text(payload)
        except:
            dead_connections.append(websocket)
    
    for dead in dead_connections:
        if dead in active_connections:
            active_connections.remove(dead)

async def broadcast_status(status):
    """Broadcast agent status (idle/running) to all clients."""
    dead_connections = []
    payload = json.dumps({"type": "status", "status": status})
    for websocket in active_connections:
        try:
            await websocket.send_text(payload)
        except:
            dead_connections.append(websocket)
    
    for dead in dead_connections:
        if dead in active_connections:
            active_connections.remove(dead)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            message = json.loads(data)
            if message.get("type") == "start_task":
                task = message.get("task")
                api_key = message.get("api_key")
                asyncio.create_task(run_agent_task(task, api_key))
            elif message.get("type") == "pause":
                if agent:
                    agent.paused = True
                    await broadcast_log("Agent paused.", "warning")
            elif message.get("type") == "resume":
                if agent:
                    agent.paused = False
                    await broadcast_log("Agent resumed.", "info")
            elif message.get("type") == "stop":
                if agent:
                    agent.stopped = True
                    await broadcast_log("Agent stopping...", "warning")
            elif message.get("type") == "reset":
                if agent:
                    agent.stopped = True
                    agent.history = []
                    await broadcast_log("Agent reset. History cleared.", "warning")
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

async def run_agent_task(task, api_key=None):
    global agent
    await broadcast_status("running")
    await broadcast_log(f"Starting task: {task}", "info")
    try:
        if not agent:
            agent = WebAgent(logger=broadcast_log)
        await agent.run(task, api_key=api_key)
    except Exception as e:
        await broadcast_log(f"Agent error: {str(e)}", "error")
    finally:
        await broadcast_status("idle")

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
