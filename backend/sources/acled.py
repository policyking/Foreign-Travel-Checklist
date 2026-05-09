import httpx
import os
from datetime import date, timedelta

API_URL = "https://api.acleddata.com/acled/read/"
REGISTER_URL = "https://developer.acleddata.com/"


async def fetch_acled(parsed: dict) -> dict:
    api_key = os.getenv("ACLED_API_KEY")
    api_email = os.getenv("ACLED_EMAIL")
    country = parsed.get("country", "")

    if not api_key or not api_email:
        return {
            "available": False,
            "source": "ACLED (Armed Conflict Location & Event Data)",
            "url": REGISTER_URL,
            "error": "ACLED credentials not configured. Free registration at developer.acleddata.com — add ACLED_API_KEY and ACLED_EMAIL to your .env file.",
        }

    end_date = date.today()
    start_date = end_date - timedelta(days=180)

    params = {
        "key": api_key,
        "email": api_email,
        "country": country,
        "event_date": f"{start_date.isoformat()}|{end_date.isoformat()}",
        "event_date_where": "BETWEEN",
        "limit": 30,
        "fields": "event_date|event_type|sub_event_type|actor1|actor2|admin1|admin2|location|fatalities|notes",
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(API_URL, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {
            "available": False,
            "source": "ACLED (Armed Conflict Location & Event Data)",
            "url": REGISTER_URL,
            "error": str(e),
        }

    events = data.get("data", [])

    # Aggregate by event type
    by_type: dict[str, int] = {}
    total_fatalities = 0
    for ev in events:
        et = ev.get("event_type", "Unknown")
        by_type[et] = by_type.get(et, 0) + 1
        try:
            total_fatalities += int(ev.get("fatalities") or 0)
        except (ValueError, TypeError):
            pass

    # Five most recent notable events
    recent = []
    for ev in events[:5]:
        actor_str = ev.get("actor1", "")
        if ev.get("actor2"):
            actor_str += f" vs {ev['actor2']}"
        location = ", ".join(filter(None, [ev.get("location"), ev.get("admin1")]))
        recent.append({
            "date": ev.get("event_date", ""),
            "type": ev.get("event_type", ""),
            "sub_type": ev.get("sub_event_type", ""),
            "location": location,
            "actors": actor_str,
            "fatalities": ev.get("fatalities", 0),
            "notes": (ev.get("notes") or "")[:250],
        })

    return {
        "available": True,
        "source": "ACLED (Armed Conflict Location & Event Data)",
        "url": "https://acleddata.com/data-export-tool/",
        "period": f"{start_date.isoformat()} to {end_date.isoformat()}",
        "total_events": len(events),
        "total_fatalities": total_fatalities,
        "by_type": by_type,
        "recent_events": recent,
    }
