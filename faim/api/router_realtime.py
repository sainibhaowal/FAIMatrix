"""
FAIM Real-Time Updates Router (WebSockets)

=============================================================================
REAL-TIME COMMUNICATION STRATEGY
=============================================================================

This project supports TWO real-time communication mechanisms:

1. **SSE (Server-Sent Events)** - PRIMARY
   - Endpoint: /api/v1/stream
   - Used by: Dashboard, Monitor, Graph views (via useFaimStream hook)
   - Best for: One-way server-to-client updates, auto-reconnect, simpler protocol
   - Implementation: faim/api/app.py (stream endpoint) + faim/api/events.py

2. **WebSocket** - SECONDARY (this router)
   - Endpoint: /api/v1/realtime/ws/{graph_id}
   - Used by: Future bidirectional features (e.g., collaborative editing)
   - Best for: Bidirectional communication, lower latency requirements
   - Implementation: This file (router_realtime.py)

CURRENT STATUS:
- SSE is fully wired and used by the frontend
- WebSocket is wired but NOT currently consumed by frontend
- Keep both for flexibility; WebSocket ready for future features

TO USE WEBSOCKET FROM FRONTEND:
  const ws = new WebSocket(`ws://${host}/api/v1/realtime/ws/${graphId}`);
  ws.onmessage = (event) => { console.log(JSON.parse(event.data)); };
=============================================================================
"""

from typing import List, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from faim.core.events import subscribe_node_created
import asyncio
import json

router = APIRouter(prefix="/realtime", tags=["Realtime"])


class ConnectionManager:
    def __init__(self):
        # graph_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, graph_id: str):
        await websocket.accept()
        if graph_id not in self.active_connections:
            self.active_connections[graph_id] = []
        self.active_connections[graph_id].append(websocket)

    def disconnect(self, websocket: WebSocket, graph_id: str):
        if graph_id in self.active_connections:
            try:
                self.active_connections[graph_id].remove(websocket)
                if not self.active_connections[graph_id]:
                    del self.active_connections[graph_id]
            except ValueError:
                pass

    async def broadcast(self, graph_id: str, message: dict):
        if graph_id in self.active_connections:
            # Broadcast to all connected clients for this graph
            dead_sockets = []
            for connection in self.active_connections[graph_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_sockets.append(connection)

            # Cleanup dead sockets
            for ds in dead_sockets:
                self.disconnect(ds, graph_id)


manager = ConnectionManager()


main_loop = None


@router.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()


# Global event handler that bridges Core Events -> WebSocket Broadcast
# This runs in the main event loop OR in a worker thread
def handle_node_created(graph_id: str, node_id: str, timestamp: float):
    global main_loop
    # We need to run the async broadcast from this sync callback
    try:
        msg = {
            "type": "node_created",
            "graph_id": graph_id,
            "node_id": node_id,
            "timestamp": timestamp,
        }

        if main_loop and main_loop.is_running():
            asyncio.run_coroutine_threadsafe(manager.broadcast(graph_id, msg), main_loop)
    except Exception:
        pass


# Subscribe to core events
subscribe_node_created(handle_node_created)


@router.websocket("/ws/{graph_id}")
async def websocket_endpoint(websocket: WebSocket, graph_id: str):
    await manager.connect(websocket, graph_id)
    try:
        while True:
            # Keep connection alive and handle client messages if any
            # For now we essentially just listen for pings or ignore input
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, graph_id)
    except Exception:
        manager.disconnect(websocket, graph_id)
