"""Utilities module for gui services."""
import datetime
import logging

from aiohttp import web
from aiohttp_session import get_session

from result_service_gui.services import (
    EventsAdapter,
    RaceplansAdapter,
    StartAdapter,
    TimeEventsAdapter,
    TimeEventsService,
    UserAdapter,
)


async def check_login(self) -> dict:
    """Check loging and return user credentials."""
    session = await get_session(self.request)
    loggedin = UserAdapter().isloggedin(session)
    if not loggedin:
        informasjon = "Logg inn for å se denne siden"
        return web.HTTPSeeOther(location=f"/login?informasjon={informasjon}")

    return {"name": session["username"], "token": session["token"]}


async def create_time_event(token: str, action: str, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    time_now = datetime.datetime.now()

    request_body = {
        "bib": "",
        "event_id": form["event_id"],
        "race": form["race"],
        "race_id": form["race_id"],
        "point": "",
        "rank": "",
        "registration_time": time_now.strftime("%X"),
        "next_race_id": "",
        "status": "OK",
        "changelog": "",
    }
    i = 0
    if action == "start_bib":
        # register start
        request_body["point"] = "Start"
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            if bib.count("x") > 0:
                request_body["point"] = "DNS"
                request_body[
                    "changelog"
                ] = f"{time_now.strftime('%X')}: DNS registrert. "
                request_body["bib"] = bib.replace("x", "")
                informasjon += f" {request_body['bib']}-DNS "
            else:
                request_body[
                    "changelog"
                ] = f"{time_now.strftime('%X')}: Start registrert. "
                request_body["bib"] = bib
                informasjon += f" {bib}-OK "
            i += 1
            id = await TimeEventsService().create_time_event(token, request_body)
    elif action == "start_check":
        for x in form.keys():
            if x.startswith("form_start_"):
                request_body["bib"] = x[11:]
                if form[x] == "DNS":
                    # register DNS
                    request_body["point"] = "DNS"
                    request_body[
                        "changelog"
                    ] = f"{time_now.strftime('%X')}: DNS registrert. "
                else:
                    # register normal start
                    request_body["point"] = "Start"
                    request_body[
                        "changelog"
                    ] = f"{time_now.strftime('%X')}: Start registrert. "
                i += 1
                id = await TimeEventsService().create_time_event(token, request_body)
                informasjon += f" {request_body['bib']}-{form[x]}. "
    elif action == "finish_bib1":
        request_body["point"] = "Finish"
        request_body[
            "changelog"
        ] = f"{time_now.strftime('%X')}: Målpassering registrert. "
        biblist = form["bib"].rsplit(" ")
        for bib in biblist:
            request_body["bib"] = bib
            i += 1
            id = await TimeEventsService().create_time_event(token, request_body)
            informasjon += f" {bib} "
    elif action == "finish_bib2":
        request_body["point"] = "Finish"
        for x in form.keys():
            if x.startswith("form_place_"):
                _bib = form[x]
                if _bib.isnumeric():
                    request_body["bib"] = _bib
                    request_body["rank"] = x[11:]
                    request_body[
                        "changelog"
                    ] = f"{time_now.strftime('%X')}: {request_body['rank']} plass i mål. "
                    i += 1
                    id = await TimeEventsService().create_time_event(
                        token, request_body
                    )
                    informasjon += (
                        f" {request_body['bib']}-{request_body['rank']} plass. "
                    )
    elif action == "finish_place":
        request_body["point"] = "Finish"
        for x in form.keys():
            if x.startswith("form_place_"):
                _place = form[x]
                if _place.isnumeric():
                    request_body["bib"] = x[11:]
                    request_body["rank"] = _place
                    request_body[
                        "changelog"
                    ] = f"{time_now.strftime('%X')}: {request_body['rank']} plass i mål. "
                    i += 1
                    id = await TimeEventsService().create_time_event(
                        token, request_body
                    )
                    informasjon += (
                        f" {request_body['bib']}-{request_body['rank']} plass. "
                    )
    logging.debug(f"Registrations: {informasjon}, last id: {id}")

    return f"Utført {i} registreringer: {informasjon}"


async def get_enchiced_startlist(token: str, race_id: str, start_entries: list) -> list:
    """Enrich startlist information."""
    startlist = []
    # get template time-events - for next race
    next_race_templates = await TimeEventsAdapter().get_time_events_by_race_id(
        token, race_id
    )

    if len(start_entries) > 0:
        for start_id in start_entries:
            start_entry = await StartAdapter().get_start_entry_by_id(
                token, race_id, start_id
            )
            for template in next_race_templates:
                if template["point"] == "Template":
                    if template["rank"] == start_entry["starting_position"]:
                        start_entry[
                            "next_race"
                        ] = f"{template['next_race']}-{template['next_race_position']}"
            startlist.append(start_entry)
    return startlist


async def get_event(token: str, event_id: str) -> dict:
    """Get event - return new if no event found."""
    event = {"id": event_id, "name": "Nytt arrangement", "organiser": "Ikke valgt"}
    if event_id != "":
        logging.debug(f"get_event {event_id}")
        event = await EventsAdapter().get_event(token, event_id)

    return event


def get_qualification_text(race: dict) -> str:
    """Generate a text with info about qualification rules."""
    text = ""
    for key, value in race["rule"].items():
        if key == "S":
            for x, y in value.items():
                if x == "A" and y > 0:
                    text += f"{y} til semi A. "
                elif x == "C" and y > 0:
                    text += "Resten til semi C. "
        elif key == "F":
            for x, y in value.items():
                if x == "A":
                    text += f"{y} til finale A. "
                elif x == "B" and y > 8:
                    text += "Resten til finale B. "
                elif x == "B":
                    text += f"{y} til finale B. "
                elif x == "C" and y > 8:
                    text += "Resten til finale C. "
                elif x == "C":
                    text += f"{y} til finale C. "
            if text.count("Resten") == 0:
                text += "Resten er ute. "
    logging.debug(f"Regel hele: {text}")
    return text


async def get_races_for_live_view(
    token: str, event_id: str, valgt_heat: int, number_of_races: int
) -> list:
    """Return races to display in live view."""
    filtered_racelist = []
    time_now = datetime.datetime.now().strftime("%X")
    i = 0
    # get races
    races = await RaceplansAdapter().get_all_races(token, event_id)
    for race in races:
        # from heat number (order) if selected
        if (valgt_heat != 0) and (race["order"] > valgt_heat) and (i < number_of_races):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1
        # show upcoming heats from now
        elif (time_now < race["start_time"][-8:]) and (i < number_of_races):
            race["next_race"] = get_qualification_text(race)
            race["start_time"] = race["start_time"][-8:]
            filtered_racelist.append(race)
            i += 1

    return filtered_racelist


async def update_time_event(token: str, action: str, form: dict) -> str:
    """Register time event - return information."""
    informasjon = ""
    time_now = datetime.datetime.now()
    request_body = await TimeEventsAdapter().get_time_event_by_id(token, form["id"])
    if "update" in form.keys():
        request_body[
            "changelog"
        ] += f"{time_now.strftime('%X')}: Oppdatering - tidligere informasjon: {request_body}. "
        request_body["point"] = form["point"]
        request_body["registration_time"] = form["registration_time"]
        request_body["rank"] = form["rank"]
    elif "delete" in form.keys():
        request_body[
            "changelog"
        ] += f"{time_now.strftime('%X')}: Status set to deleted "
        request_body["status"] = "Deleted"
    informasjon = await TimeEventsService().update_time_event(
        token, form["id"], request_body
    )
    logging.debug(f"Control result: {informasjon}")

    return f"Control result: Oppdatert - {informasjon}"
