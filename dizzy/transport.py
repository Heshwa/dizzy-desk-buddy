"""Threaded network clients keep the Webots simulation loop responsive."""
import asyncio
import json
import os
import queue
import threading
import time

import paho.mqtt.client as mqtt
from websockets.asyncio.client import connect


class Link:
    def __init__(self, device_id, partner_id):
        self.id = device_id
        self.partner = partner_id
        self.inbox = queue.Queue()
        self.responses = queue.Queue()
        self.snapshot = {}
        self.stop = threading.Event()
        self.mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f'dizzy-{device_id}')
        self.prefix = os.getenv('DIZZY_MQTT_PREFIX', 'dizzy/demo')
        self.last_heartbeat = 0
        user = os.getenv('DIZZY_MQTT_USERNAME')
        if user:
            self.mqtt.username_pw_set(user, os.getenv('DIZZY_MQTT_PASSWORD'))
        if os.getenv('DIZZY_MQTT_TLS') == '1':
            self.mqtt.tls_set()
        self.mqtt.will_set(self.topic(self.id, 'presence'), 'offline', qos=1, retain=True)
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message
        self.mqtt.on_disconnect = lambda *a: self.inbox.put(('presence', False))
        self.mqtt.reconnect_delay_set(1, 10)
        self.mqtt.connect_async(os.getenv('DIZZY_MQTT_HOST', '127.0.0.1'), int(os.getenv('DIZZY_MQTT_PORT', '18884')), 10)
        self.mqtt.loop_start()
        threading.Thread(target=lambda: asyncio.run(self.run_websocket()), daemon=True).start()

    def topic(self, device, kind):
        return f'{self.prefix}/{device}/{kind}'

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            return
        for device, kind in ((self.id, 'gesture'), (self.id, 'ack'), (self.partner, 'presence')):
            client.subscribe(self.topic(device, kind), qos=1)
        self.publish('presence', {'online': True, 'at': time.time()}, retain=True)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            if msg.topic.endswith('/presence'):
                online = isinstance(data, dict) and data.get('online') and time.time() - data.get('at', 0) < 8
                self.inbox.put(('presence', bool(online)))
            elif isinstance(data, dict):
                self.inbox.put((msg.topic.rsplit('/', 1)[1], data))
        except (ValueError, TypeError):
            self.inbox.put(('presence', False))

    def publish(self, kind, data, target=None, retain=False):
        self.mqtt.publish(self.topic(target or self.id, kind), json.dumps(data), qos=1, retain=retain)

    async def run_websocket(self):
        url = os.getenv('DIZZY_SERVICE_URL', 'ws://127.0.0.1:8765') + f'/device/{self.id}'
        while not self.stop.is_set():
            try:
                async with connect(url, max_size=10_000_000) as ws:
                    async def send():
                        while not self.stop.is_set():
                            await ws.send(json.dumps({'type': 'status', 'state': self.snapshot}))
                            while not self.responses.empty():
                                await ws.send(json.dumps(self.responses.get_nowait()))
                            await asyncio.sleep(0.1)
                    sender = asyncio.create_task(send())
                    try:
                        async for message in ws:
                            self.inbox.put(('command', json.loads(message)))
                    finally:
                        sender.cancel()
                        await asyncio.gather(sender, return_exceptions=True)
                        self.inbox.put(('service_offline', True))
            except Exception:
                self.inbox.put(('service_offline', True))
                # The robot retains its clock and alarms during service outages.
                await asyncio.sleep(1)

    def close(self):
        self.stop.set()
        self.publish('presence', {'online': False, 'at': time.time()}, retain=True)
        self.mqtt.disconnect()
        self.mqtt.loop_stop()
