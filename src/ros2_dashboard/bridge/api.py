from flask import Blueprint, jsonify, request

from ..models import Recording, db
from .ros_bridge import RosBridge
from .topics import TOPIC_REGISTRY

bp = Blueprint("bridge", __name__)
_bridge = None


def get_bridge():
    global _bridge
    if _bridge is None:
        _bridge = RosBridge()
    return _bridge


@bp.get("/api/topics")
def topics():
    return jsonify(
        {"topics": [{"name": k, "type": v, "rate": 10} for k, v in TOPIC_REGISTRY.items()]}
    )


@bp.post("/api/record")
def start_record():
    d = request.get_json(force=True, silent=True) or {}
    rec = Recording(name=d.get("name", "run1"), topics_json=str(d.get("topics", ["odom", "imu"])))
    db.session.add(rec)
    db.session.commit()
    return jsonify({"id": rec.id, "status": "recording"})


@bp.post("/api/recordings/<id>/stop")
def stop_record(id):
    rec = Recording.query.get_or_404(int(id))
    rec.status = "saved"
    db.session.commit()
    return jsonify({"status": "saved", "size": rec.size})


@bp.get("/ws")
def ws_endpoint():
    """Handshake half of the rosbridge relay documented at /ws.

    The OpenAPI document documents /ws as a GET that returns the rosbridge
    relay handshake metadata.  Flask has no websocket transport of its own,
    so the socket itself is served by web/ws.py -- an asyncio relay built on
    the project's websockets dependency, started with "python -m web.ws".
    This route is the handshake half: it answers the plain GET that a client
    or a health check makes before opening the socket.
    """
    return jsonify(
        {
            "transport": "websocket",
            "path": "/ws",
            "protocol": "rosbridge",
            "relay": "web.ws:main",
            "command": "python -m web.ws",
            "topics": sorted(TOPIC_REGISTRY.values()),
        }
    )


@bp.get("/api/recordings")
def recordings():
    return jsonify(
        {
            "recordings": [
                {"id": r.id, "name": r.name, "size": r.size, "status": r.status}
                for r in Recording.query.all()
            ]
        }
    )
