== curl ==
# GET  /api/topics
# POST /api/record  {"name":"run1","topics":["odom","imu"]}
# POST /api/recordings/1/stop
# GET  /api/recordings
# GET  /ws  (relay handshake; the socket itself: python -m web.ws)

== session plan ==
# Session 1: ros_bridge (mock rosbridge server) + rate limiter → tests
# Session 2: record/replay JSONL → tests
# Session 3: web telemetry + joystick → screenshots (mock data)
# Session 4: map view + launch files → README → tag (real robot demo on internship box)
