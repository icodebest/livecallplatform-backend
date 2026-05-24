from collections import defaultdict
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        """Track browser WebSockets by logical channel name."""
        self.active: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        """Accept a browser socket and subscribe it to a channel."""
        await websocket.accept()
        self.active[channel].add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        """Remove a browser socket from a channel."""
        self.active[channel].discard(websocket)

    async def broadcast(self, channel: str, message: dict) -> None:
        """Send JSON to every socket on the channel and remove dead sockets."""
        stale = []
        for websocket in self.active[channel]:
            try:
                await websocket.send_json(message)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(channel, websocket)


manager = ConnectionManager()
