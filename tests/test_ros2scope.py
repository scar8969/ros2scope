"""C1 ros2-dashboard — tests. Run: pytest test_ros2scope.py"""
import sys, os, json

import pytest

def test_rate_limiter():
    from ros2_dashboard.bridge.topics import RateLimiter
    rl = RateLimiter(max_per_sec=3)
    assert rl.allow()
    assert rl.allow()
    assert rl.allow()
    assert not rl.allow()  # 4th in same second

def test_recorder_roundtrip(tmp_path):
    from ros2_dashboard.bridge.record import Recorder, replay
    p = str(tmp_path / "run.jsonl")
    rec = Recorder(p)
    rec.start()
    rec.write("odom", {"x": 1.0, "y": 2.0})
    rec.write("imu", {"yaw": 15.2})
    size = rec.stop()
    assert size > 0
    msgs = list(replay(p))
    assert len(msgs) == 2
    assert msgs[0][0] == "odom"
    assert msgs[0][1]["x"] == 1.0

def test_topic_registry():
    from ros2_dashboard.bridge.topics import TOPIC_REGISTRY
    assert TOPIC_REGISTRY["odom"] == "/odom"
    assert "cmd_vel" in TOPIC_REGISTRY
