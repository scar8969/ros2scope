import asyncio
import json
from typing import Any


class RosBridge:
    def __init__(self, url: str = "ws://127.0.0.1:9090"):
        self.url = url
        self._subs: dict[str, Any] = {}

    async def connect(self):
        import websockets

        while True:
            try:
                self._ws = await websockets.connect(self.url, ping_interval=10)
                # resubscribe
                for topic, cb in self._subs.items():
                    await self._ws.send(json.dumps({"op": "subscribe", "topic": topic}))
                return
            except Exception:
                await asyncio.sleep(2)

    def subscribe(self, topic, cb):
        self._subs[topic] = cb

    async def publish(self, topic, msg):
        await self._ws.send(json.dumps({"op": "publish", "topic": topic, "msg": msg}))

    async def call_service(self, service, req):
        await self._ws.send(json.dumps({"op": "call_service", "service": service, "args": req}))
        while True:
            msg = json.loads(await self._ws.recv())
            if msg.get("op") == "service_response":
                return msg.get("values", {})

    async def _reader(self):
        while True:
            try:
                msg = json.loads(await self._ws.recv())
                topic = msg.get("topic")
                if topic in self._subs:
                    self._subs[topic](msg.get("msg", {}))
            except Exception:
                await self.connect()
