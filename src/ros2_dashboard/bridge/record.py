import json
import os
from typing import Any


class Recorder:
    def __init__(self, path: str):
        self.path = path
        self._f: Any = None

    def start(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._f = open(self.path, "a")

    def write(self, topic, msg):
        if self._f:
            self._f.write(json.dumps({"topic": topic, "msg": msg}) + "\n")

    def stop(self):
        if self._f:
            self._f.close()
            self._f = None
        return os.path.getsize(self.path) if os.path.exists(self.path) else 0


def replay(path):
    with open(path) as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                yield d["topic"], d["msg"]
