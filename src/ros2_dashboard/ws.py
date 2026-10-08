"""rosbridge relay: the socket half of the /ws endpoint.

web/app.py answers a plain GET on /ws with the handshake metadata (transport,
path, protocol, upstream command).  Flask has no websocket transport of its
own, so the socket lives here and is started explicitly:

    python -m web.ws --listen 127.0.0.1:9091 --upstream ws://127.0.0.1:9090

Every accepted client is paired with one upstream rosbridge connection and the
frames are forwarded in both directions.  When the upstream cannot be reached
the client is told why and the socket is closed -- nothing is simulated
locally.  The "websockets" package (requirements.txt) is imported inside the
functions, so importing this module on a bare interpreter still works.
"""
import argparse
import asyncio
import json
import os

DEFAULT_LISTEN = os.environ.get("ROSBRIDGE_RELAY_LISTEN", "127.0.0.1:9091")
DEFAULT_UPSTREAM = os.environ.get("ROSBRIDGE_URL", "ws://127.0.0.1:9090")

def split_hostport(value):
    """'host:port' -> (host, port); a bare port means localhost."""
    host, sep, port = value.rpartition(":")
    if not sep:
        return "127.0.0.1", int(host or 9091)
    return (host or "127.0.0.1"), int(port or 9091)

def _status(level, msg):
    return json.dumps({"op": "status", "level": level, "msg": msg})

async def pump_to_upstream(client, upstream):
    """client -> rosbridge"""
    async for message in client:
        await upstream.send(message)

async def pump_to_client(client, upstream):
    """rosbridge -> client"""
    async for message in upstream:
        await client.send(message)

async def relay(client, upstream_url):
    """Attach one client to one upstream rosbridge socket."""
    import websockets

    try:
        upstream = await websockets.connect(upstream_url, ping_interval=10)
    except Exception as exc:
        await client.send(_status("error", "rosbridge unreachable at %s: %s" % (upstream_url, exc)))
        await client.close()
        return
    try:
        await client.send(_status("info", "relay attached to %s" % upstream_url))
        tasks = [asyncio.create_task(pump_to_upstream(client, upstream)),
                 asyncio.create_task(pump_to_client(client, upstream))]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for task in done:
            task.exception()  # mark retrieved; a dropped peer is not an error
    finally:
        await upstream.close()

async def serve(listen, upstream_url):
    """Run the relay until cancelled."""
    import websockets

    host, port = split_hostport(listen)
    async with websockets.serve(lambda client: relay(client, upstream_url), host, port):
        print("ros2-dash relay ws://%s:%d -> %s" % (host, port, upstream_url))
        await asyncio.Future()

def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m web.ws",
        description="rosbridge relay behind the /ws handshake served by web/app.py.")
    parser.add_argument("--listen", default=DEFAULT_LISTEN,
                        help="interface to bind (default: $ROSBRIDGE_RELAY_LISTEN or 127.0.0.1:9091)")
    parser.add_argument("--upstream", default=DEFAULT_UPSTREAM,
                        help="rosbridge url (default: $ROSBRIDGE_URL or ws://127.0.0.1:9090)")
    args = parser.parse_args(argv)
    asyncio.run(serve(args.listen, args.upstream))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
