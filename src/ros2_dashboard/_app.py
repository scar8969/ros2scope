from .bridge.api import bp
from .bridge.topics import TOPIC_REGISTRY
from .models import Recording, db

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
import os
from . import paths

# Templates and static assets live at <project root>/templates and
# <project root>/static, next to web/, so resolve them from this file instead
# of the process working directory.

def build_app():
    """Build the application: configuration, database, then routes."""
    app = Flask(__name__, template_folder=str(paths.TEMPLATES_DIR), static_folder=str(paths.STATIC_DIR))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(paths.INSTANCE_DIR / "ros2dash.db")
    app.secret_key = os.environ.get("ROS2DASH_SECRET", "ros2-dash-dev-secret")
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.register_blueprint(bp)

    # State the operator created in this process.  Every template renders from
    # these values (or from SQLite), so the served page is never a mock-up.
    PAGE_STATE = {"recording_name": "run1", "selected_topics": ["odom", "imu"],
                  "log": "no recording started in this process yet",
                  "pose": {"x": 0.0, "y": 0.0, "theta": 0.0}}
    OUTPUT_DIR = os.environ.get("ROS2DASH_OUTPUT_DIR", str(paths.DATA_DIR))
    BRIDGE_ID = os.environ.get("ROSBRIDGE_ID", "rosbridge@127.0.0.1:9090")

    def _rows():
        return Recording.query.order_by(Recording.id).all()

    @app.context_processor
    def inject_state():
        """Per-request context built from SQLite + TOPIC_REGISTRY, not from literals."""
        rows = _rows()
        active = next((r for r in rows if r.status == "recording"), None)
        topics = []
        for key, channel in sorted(TOPIC_REGISTRY.items()):
            busy = len([r for r in rows if key in (r.topics_json or "")])
            topics.append({"name": key, "channel": channel, "rate": 10,
                           "recordings": busy,
                           "bar": int(round(100.0 * busy / len(rows))) if rows else 0})
        sizes = [r.size or 0 for r in rows]
        peak = max(sizes) if sizes else 0
        return {
            "app_name": "ros2-dash",
            "bridge_id": BRIDGE_ID,
            "bridge_state": active.status if active else "idle",
            "topics": topics,
            "recordings": [{"id": r.id, "name": r.name, "status": r.status or "",
                            "size": r.size or 0, "topics": r.topics_json or "",
                            "started_at": r.started_at} for r in rows],
            "chart": [max(4, int(round(100.0 * s / peak))) for s in sizes] if peak else [],
            "recording_name": request.args.get("name") or PAGE_STATE["recording_name"],
            "selected_topics": request.args.getlist("topic") or PAGE_STATE["selected_topics"],
            "active_recording": active.id if active else "",
            "output_dir": OUTPUT_DIR,
            "map_label": TOPIC_REGISTRY["map"],
            "pose": PAGE_STATE["pose"],
            "pose_source": "PAGE_STATE in web/app.py (no live rosbridge session attached)",
            "log": PAGE_STATE["log"],
        }

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/map")
    def map_view():
        return render_template("map.html")

    @app.post("/record")
    def start_recording():
        """Control-panel form target: it creates the Recording row the API also creates."""
        topics = [t.strip() for t in
                  (request.form.get("topic") or "").replace(",", " ").split() if t.strip()]
        rec = Recording(name=(request.form.get("name") or "run1").strip(),
                        topics_json=str(topics), status="recording")
        db.session.add(rec)
        db.session.flush()
        rec.file_path = os.path.join(OUTPUT_DIR, "rec%d.jsonl" % rec.id)
        db.session.commit()
        PAGE_STATE["recording_name"] = rec.name
        PAGE_STATE["selected_topics"] = topics
        PAGE_STATE["log"] = "started recording #%d (%s) -> %s" % (
            rec.id, ", ".join(topics) or "no topics", rec.file_path)
        flash("recording #%d started" % rec.id)
        return redirect(url_for("index"))

    @app.post("/recordings/<int:rid>/stop")
    def stop_recording(rid):
        rec = Recording.query.get_or_404(rid)
        size = 0
        if rec.file_path:
            try:
                with open(rec.file_path, "rb") as fh:
                    size = len(fh.read())
            except OSError:
                size = rec.size or 0
        rec.size = size
        rec.status = "saved"
        db.session.commit()
        PAGE_STATE["log"] = "stopped recording #%d: %d bytes on disk" % (rec.id, size)
        flash("recording #%d stopped" % rec.id)
        return redirect(url_for("index"))

    @app.get("/api/health")
    def api_health():
        return jsonify({"status": "ok", "app": "ros2-dash", "version": "0.1.0"})

    @app.get("/api/status")
    def api_status():
        """The same server-held state the templates render, for the UI to poll."""
        rows = _rows()
        active = next((r for r in rows if r.status == "recording"), None)
        return jsonify({"bridge": BRIDGE_ID, "output_dir": OUTPUT_DIR,
                        "recording_name": PAGE_STATE["recording_name"],
                        "selected_topics": PAGE_STATE["selected_topics"],
                        "active_recording": active.id if active else "",
                        "pose": PAGE_STATE["pose"],
                        "log": PAGE_STATE["log"],
                        "recordings": [{"id": r.id, "name": r.name, "status": r.status,
                                        "size": r.size or 0} for r in rows]})

    @app.get("/api/config")
    def api_config():
        """Effective runtime configuration (no secrets: the URL is read-only)."""
        return jsonify({"rosbridge_url": os.environ.get("ROSBRIDGE_URL", "ws://127.0.0.1:9090"),
                        "output_dir": OUTPUT_DIR,
                        "database": app.config["SQLALCHEMY_DATABASE_URI"],
                        "topics": sorted(TOPIC_REGISTRY.values())})

    if __name__ == "__main__":  # python -m web.app  (see Dockerfile CMD)
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))

    return app

app = build_app()
