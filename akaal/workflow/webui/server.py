"""WebUI Control Plane Server."""

from akaal.workflow.webui.renderer import VirtualizedGraphRenderer
from akaal.workflow.webui.streamer import WebSocketEventBroadcaster


class WebUiServer:
    """Web Control Plane static and streaming server facade."""

    def __init__(self) -> None:
        self.streamer = WebSocketEventBroadcaster()
        self.renderer = VirtualizedGraphRenderer()

    def get_dashboard_metrics(self) -> dict:
        return {
            "status": "HEALTHY",
            "active_clients": self.streamer.broadcast_event({}),
        }
