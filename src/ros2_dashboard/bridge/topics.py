TOPIC_REGISTRY = {
    "odom": "/odom",
    "imu": "/imu/data",
    "battery": "/battery/state",
    "cmd_vel": "/cmd_vel",
    "logs": "/rosout",
    "map": "/map",
}


class RateLimiter:
    def __init__(self, max_per_sec: int = 10):
        self.max = max_per_sec
        self._times = []

    def allow(self):
        import time

        now = time.monotonic()
        self._times = [t for t in self._times if now - t < 1]
        if len(self._times) >= self.max:
            return False
        self._times.append(now)
        return True
