import httpx
import re
from bs4 import BeautifulSoup

ADVISORY_URL = "https://travel.state.gov/content/travel/en/traveladvisories/traveladvisories/{slug}-travel-advisory.html"

LEVEL_META = {
    1: ("Exercise Normal Precautions", "#2d7d3a"),
    2: ("Exercise Increased Caution", "#b45309"),
    3: ("Reconsider Travel", "#c2410c"),
    4: ("Do Not Travel", "#b91c1c"),
}


async def fetch_state_dept(parsed: dict) -> dict:
    slug = parsed["slugs"]["state_dept"]
    url = ADVISORY_URL.format(slug=slug)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TravelRisk/1.0)"})
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        return {"available": False, "source": "US Department of State", "url": url,
                "error": f"HTTP {e.response.status_code} — advisory page not found for this destination."}
    except Exception as e:
        return {"available": False, "source": "US Department of State", "url": url, "error": str(e)}

    soup = BeautifulSoup(r.text, "lxml")

    # Detect advisory level
    level = None
    for i in range(1, 5):
        if re.search(rf"\bLevel\s*{i}\b", r.text):
            level = i
            break

    # Extract advisory summary text
    summary_parts = []
    for selector in [
        "div.tsg-rwd-emergency-alert-text",
        "div#advisory-summary",
        "div.page-body",
    ]:
        elems = soup.select(selector)
        if elems:
            for el in elems[:1]:
                for p in el.find_all("p")[:5]:
                    text = p.get_text(separator=" ", strip=True)
                    if len(text) > 40:
                        summary_parts.append(text)
            break

    # Fallback: grab first substantial paragraphs from main content
    if not summary_parts:
        for p in soup.find_all("p")[:10]:
            text = p.get_text(separator=" ", strip=True)
            if len(text) > 80:
                summary_parts.append(text)
            if len(summary_parts) >= 3:
                break

    # Last updated
    last_updated = None
    for tag in soup.find_all(string=re.compile(r"Last\s+Update", re.I)):
        parent = tag.parent
        if parent:
            last_updated = parent.get_text(strip=True)
            break

    level_text, level_color = LEVEL_META.get(level, (None, None))

    return {
        "available": True,
        "source": "US Department of State",
        "url": url,
        "level": level,
        "level_text": level_text,
        "level_color": level_color,
        "summary": " ".join(summary_parts)[:1500],
        "last_updated": last_updated,
    }
