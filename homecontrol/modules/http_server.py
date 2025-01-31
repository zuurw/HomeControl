"""The http server"""

import os
import logging
import ssl

import voluptuous as vol
from aiohttp import web

SPEC = {
    "meta": {
        "name": "HTTP Server"
    }
}

CONFIG_SCHEMA = vol.Schema({
    vol.Required("host", default=None): vol.Any(str, None),
    vol.Required("port", default=8080): vol.Coerce(int),
    vol.Required("ssl", default=False): vol.Any(
        bool,
        {
            "certificate": str,
            "key": str,
        })
})

LOGGER = logging.getLogger(__name__)
logging.getLogger("aiohttp").setLevel(logging.WARNING)


class SSLLogFilter(logging.Filter):
    """Filter ssl.SSLError from logs"""
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter function"""
        return not (record.exc_info and record.exc_info[0] == ssl.SSLError)


class Module:
    """The HTTP server module"""
    handler: None
    server: "asyncio.Server"
    route_table_def: web.RouteTableDef
    main_app: web.Application

    """HTTPServer exposes HTTP endpoints for interaction from outside"""

    async def init(self):
        """Sets up an HTTPServer"""
        self.cfg = await self.core.cfg.register_domain(
            "http-server", self, schema=CONFIG_SCHEMA)

        if not self.core.start_args["verbose"]:
            logging.getLogger("asyncio").addFilter(SSLLogFilter())

        event("core_bootstrap_complete")(self.start)

    async def start(self, *args):
        """Start the HTTP server"""
        self.main_app = web.Application(loop=self.core.loop)

        self.route_table_def = web.RouteTableDef()

        await self.core.event_engine.gather(
            "http_add_main_routes",
            router=self.route_table_def)
        await self.core.event_engine.gather(
            "http_add_main_subapps",
            main_app=self.main_app)

        self.main_app.add_routes(self.route_table_def)
        self.handler = self.main_app.make_handler(loop=self.core.loop)

        if self.cfg["ssl"]:
            # context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            context.verify_mode = ssl.CERT_OPTIONAL

            context.load_cert_chain(
                self.cfg["ssl"]["certificate"],
                self.cfg["ssl"]["key"]
            )
        else:
            context = None

        # Windows doesn't support reuse_port
        self.server = await self.core.loop.create_server(
            self.handler,
            self.cfg["host"],
            self.cfg["port"],
            reuse_address=True,
            reuse_port=os.name != "nt",
            ssl=context)
        LOGGER.info("Started the HTTP server")

    async def stop(self):
        """Stop the HTTP server"""
        LOGGER.info("Stopping the HTTP server on %s:%s",
                    self.cfg["host"], self.cfg["port"])
        try:
            if self.main_app.frozen:
                await self.main_app.cleanup()
                self.server.close()
                await self.server.wait_closed()
        except AttributeError:
            return

    async def apply_new_configuration(self, domain, new_config) -> None:
        """Applies new configuration"""
        await self.stop()
        self.cfg = new_config
        await self.start()
