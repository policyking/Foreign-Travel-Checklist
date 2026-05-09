import httpx
from bs4 import BeautifulSoup

API_URL = "https://api.reliefweb.int/v1/reports"


async def fetch_reliefweb(parsed: dict) -> dict:
    country = parsed.get("country", "")
    country_slug = parsed["slugs"]["state_dept"]
    page_url = f"https://reliefweb.int/country/{country_slug}"

    payload = {
        "appname": "travel-risk-tool",
        "filter": {
            "operator": "AND",
            "conditions": [
                {"field": "country.name", "value": country},
                {
                    "field": "format.name",
                    "value": ["Situation Report", "Analysis", "Assessment", "Map"],
                    "operator": "OR",
                },
            ],
        },
        "sort": ["date:desc"],
        "limit": 6,
        "fields": {
            "include": ["title", "date", "url", "body-html", "source", "format"]
        },
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(
                API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return {"available": False, "source": "ReliefWeb (UN OCHA)", "url": page_url, "error": str(e)}

    reports = []
    for item in data.get("data", []):
        fields = item.get("fields", {})
        body_html = fields.get("body-html", "")
        snippet = ""
        if body_html:
            snippet = BeautifulSoup(body_html, "lxml").get_text(separator=" ", strip=True)[:400]

        reports.append({
            "title": fields.get("title", ""),
            "date": (fields.get("date") or {}).get("created", "")[:10],
            "url": fields.get("url") or f"https://reliefweb.int/report/{item.get('id')}",
            "sources": [s.get("name") for s in fields.get("source", [])],
            "snippet": snippet,
        })

    return {
        "available": True,
        "source": "ReliefWeb (UN OCHA)",
        "url": page_url,
        "reports": reports,
        "total_found": data.get("totalCount", 0),
    }
