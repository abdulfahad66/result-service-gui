"""Resource module for main view."""
import logging

from aiohttp import web
import aiohttp_jinja2

from .utils import check_login, get_event


class Dashboard(web.View):
    """Class representing the main view."""

    async def get(self) -> web.Response:
        """Get route function that return the dashboards page."""
        try:
            event_id = self.request.rel_url.query["event_id"]
        except Exception:
            event_id = ""
        try:
            informasjon = self.request.rel_url.query["informasjon"]
        except Exception:
            informasjon = ""
        try:
            create_new = False
            new = self.request.rel_url.query["new"]
            if new != "":
                create_new = True
        except Exception:
            create_new = False

        try:
            user = await check_login(self)
            event = await get_event(user["token"], event_id)

            return await aiohttp_jinja2.render_template_async(
                "dashboard.html",
                self.request,
                {
                    "create_new": create_new,
                    "lopsinfo": "Dashboard",
                    "event": event,
                    "event_id": event_id,
                    "informasjon": informasjon,
                    "username": user["username"],
                },
            )
        except Exception as e:
            logging.error(f"Error: {e}. Redirect to main page.")
            return web.HTTPSeeOther(location=f"/?informasjon={e}")
