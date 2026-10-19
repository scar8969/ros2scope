#!/usr/bin/env python3
"""ros2-dash CLI - topic inspection, rosbridge recordings and the web app.

Generation is deterministic and offline, so the recording and replay commands
work without a robot, without ROS and without Flask.  Only "serve" imports the
web application, and it does so lazily inside the subcommand, so
`python cli.py --help` succeeds on a bare interpreter that has none of the
project's third party packages installed.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time

from . import paths

ROOT = str(paths.PROJECT_ROOT)
VERSION = "0.1.0"


def _registry() -> dict:
    from .bridge.topics import TOPIC_REGISTRY

    return TOPIC_REGISTRY


def _sample(topic: str, i: int) -> dict:
    """Deterministic stand-in for one sample of a topic."""
    t = i / 10.0
    if topic == "odom":
        return {
            "x": round(1.2 * math.sin(t), 3),
            "y": round(0.8 * math.cos(t), 3),
            "theta": round(0.27 * math.sin(t), 3),
        }
    if topic == "imu":
        return {"yaw": round(0.27 * math.sin(t), 3), "pitch": 0.0, "roll": 0.0}
    if topic == "battery":
        return {
            "voltage": round(24.6 - 0.4 * math.sin(t), 2),
            "percent": round(78.0 - 2.0 * math.sin(t), 1),
        }
    if topic == "cmd_vel":
        return {"linear": 0.35, "angular": round(0.1 * math.cos(t), 3)}
    if topic == "logs":
        return {"level": "INFO", "text": "nav2: goal reached"}
    return {"frame_id": "map", "cells": 4096}


def cmd_topics(args) -> int:
    reg = _registry()
    if args.json:
        print(
            json.dumps(
                [{"name": k, "topic": v, "rate": args.rate} for k, v in sorted(reg.items())],
                indent=2,
            )
        )
        return 0
    print(f"{'name':<10} {'topic':<16} rate")
    for name, topic in sorted(reg.items()):
        print(f"{name:<10} {topic:<16} {args.rate}")
    return 0


def cmd_record(args) -> int:
    from .bridge.record import Recorder
    from .bridge.topics import RateLimiter

    reg = _registry()
    topics = args.topics or ["odom", "imu"]
    unknown = [t for t in topics if t not in reg]
    if unknown:
        print(f"error: unknown topic(s) {unknown}; known: {sorted(reg)}", file=sys.stderr)
        return 2

    out = args.out or os.path.join(
        os.environ.get("ROS2DASH_OUTPUT_DIR", str(paths.DATA_DIR)), f"{args.name}.jsonl"
    )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    rec = Recorder(out)
    rec.start()
    limiter = RateLimiter(args.rate)
    sent = 0
    i = 0
    deadline = time.monotonic() + args.duration
    while time.monotonic() < deadline:
        for topic in topics:
            if limiter.allow():
                rec.write(topic, _sample(topic, i))
                sent += 1
        i += 1
        time.sleep(1.0 / max(args.rate, 1))
    size = rec.stop()
    print(f"recorded {sent} messages on {', '.join(topics)} -> {out} ({size} bytes)")
    return 0


def cmd_replay(args) -> int:
    from .bridge.record import replay

    shown = 0
    for topic, msg in replay(args.file):
        if args.topic and topic != args.topic:
            continue
        stamp = time.strftime("%H:%M:%S")
        print(f"[{stamp}] {topic:<8} {json.dumps(msg)}")
        shown += 1
        if args.limit and shown >= args.limit:
            break
        if args.delay:
            time.sleep(args.delay)
    print(f"replayed {shown} message(s) from {args.file}")
    return 0


def cmd_serve(args) -> int:
    from ._app import app

    app.run(host=args.host, port=args.port, debug=False)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ros2-dash", description="ROS2 telemetry dashboard: topics, recordings, replay."
    )
    p.add_argument("--version", action="version", version=f"ros2-dash {VERSION}")
    sub = p.add_subparsers(dest="command", required=True)

    t = sub.add_parser("topics", help="list the topics the dashboard subscribes to")
    t.add_argument("--rate", type=int, default=10, help="nominal publish rate in Hz")
    t.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    t.set_defaults(func=cmd_topics)

    r = sub.add_parser("record", help="record topic messages to a JSONL bag")
    r.add_argument("--name", default="run1", help="recording name (bag file stem)")
    r.add_argument("--topics", nargs="+", help="topics to record (default: odom imu)")
    r.add_argument("--rate", type=int, default=10, help="samples per second (default: 10)")
    r.add_argument("--duration", type=float, default=2.0, help="seconds to record (default: 2)")
    r.add_argument("--out", help="output JSONL path (default: $ROS2DASH_OUTPUT_DIR/<name>.jsonl)")
    r.set_defaults(func=cmd_record)

    y = sub.add_parser("replay", help="print the messages stored in a JSONL bag")
    y.add_argument("file", help="bag produced by 'record'")
    y.add_argument("--topic", help="only show this topic")
    y.add_argument("--limit", type=int, default=0, help="stop after N messages")
    y.add_argument("--delay", type=float, default=0.0, help="seconds to wait between messages")
    y.set_defaults(func=cmd_replay)

    s = sub.add_parser("serve", help="run the Flask telemetry dashboard")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(func=cmd_serve)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
