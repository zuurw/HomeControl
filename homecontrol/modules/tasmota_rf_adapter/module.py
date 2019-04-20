from contextlib import suppress
import json
from functools import reduce
import asyncio


class TasmotaRFAdapter:
    sending: asyncio.Event

    async def init(self):
        self.sending = asyncio.Event()
        self.sending.set()

        @event("mqtt_connected")
        async def on_mqtt_connected(event, mqtt_adapter):
            if mqtt_adapter == self.cfg["mqtt_adapter"]:
                self.cfg["mqtt_adapter"].client.subscribe(self.cfg["topic"]+"/tele/RESULT")

        @event("mqtt_message_received")
        async def on_mqtt_message_received(event, mqtt_adapter, message):
            if mqtt_adapter == self.cfg["mqtt_adapter"]:
                with suppress(json.decoder.JSONDecodeError):
                    data = json.loads(message.payload)
                    if data.get("RfReceived"):
                        code = data["RfReceived"].get("Data", 0)
                        bits = bin(int(code, 16))[2:][::2]
                        self.core.event_engine.broadcast("rf_code_received", code=int(bits, 2), length=len(bits))

    async def action_send_code(self, code) -> None:
        await self.sending.wait()
        self.sending.clear()
        binary = bin(int(code))[2:]
        data = "#"+hex(int("".join(reduce(lambda x, y: x+y, zip(["0"]*len(binary), binary))), 2))[2:]
        self.cfg["mqtt_adapter"].client.publish(self.cfg["topic"]+"/cmnd/RfCode", data)
        self.core.loop.call_later(self.cfg["tx_interval"], self.sending.set)

    async def send_code(self, code: int) -> None:
        asyncio.ensure_future(self.action_send_code(code))


    async def stop(self):
        self.cfg["mqtt_adapter"].client.unsubscribe(self.cfg["topic"]+"/tele/RESULT")
