"""
AirPods Auto-Switch — Handoff Listener
Listens for remote "yield" signals via ntfy.sh (free cloud relay).
When an iPhone Shortcuts automation opens an app, it sends a POST
to ntfy.sh, which this listener picks up and triggers a yield.

No same-network requirement — works from anywhere with internet.
"""

import threading
import logging
import json
import time

log = logging.getLogger(__name__)

# ntfy.sh uses HTTP streaming (Server-Sent Events style)
NTFY_BASE = "https://ntfy.sh"


class HandoffListener:
    """Background listener that subscribes to a ntfy.sh topic for yield signals."""

    def __init__(self, engine, topic: str):
        """
        Args:
            engine: AutoSwitchEngine instance (must have .yield_to_phone() method)
            topic: The ntfy.sh topic name (e.g. 'airpods-abc123')
        """
        self.engine = engine
        self.topic = topic
        self._running = False
        self._thread = None

    @property
    def subscribe_url(self) -> str:
        return f"{NTFY_BASE}/{self.topic}/json"

    @property
    def publish_url(self) -> str:
        """URL that the iPhone Shortcuts automation should POST to."""
        return f"{NTFY_BASE}/{self.topic}"

    def start(self):
        if self._running:
            return
        if not self.topic:
            log.warning("No handoff topic configured — remote yield disabled.")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="HandoffListener"
        )
        self._thread.start()
        log.info(f"Handoff listener started on topic: {self.topic}")

    def stop(self):
        self._running = False
        log.info("Handoff listener stopped.")

    def _listen_loop(self):
        """Subscribe to ntfy.sh using HTTP streaming with reconnect logic."""
        import urllib.request
        import urllib.error

        while self._running:
            try:
                url = f"{self.subscribe_url}?poll=0"
                req = urllib.request.Request(url, headers={
                    "User-Agent": "AirPodsAutoSwitch/1.0",
                })
                log.info(f"Connecting to ntfy.sh stream: {self.topic}")

                with urllib.request.urlopen(req, timeout=90) as response:
                    for line in response:
                        if not self._running:
                            break
                        line = line.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                            if msg.get("event") == "message":
                                message_text = msg.get("message", "")
                                log.info(f"Received handoff signal: {message_text}")
                                self.engine.yield_to_phone()
                        except json.JSONDecodeError:
                            pass

            except Exception as e:
                if self._running:
                    log.warning(f"Handoff listener connection lost: {e}. Reconnecting in 5s...")
                    time.sleep(5)
