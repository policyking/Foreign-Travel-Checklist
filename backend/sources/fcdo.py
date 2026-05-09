import httpx
from bs4 import BeautifulSoup

API_URL = "https://www.gov.uk/api/content/foreign-travel-advice/{slug}"
PAGE_URL = "https://www.gov.uk/foreign-travel-advice/{slug}"


async def fetch_fcdo(parsed: dict) -> dict:
    slug = parsed["slugs"]["fcdo"]
    api_url = API_URL.format(slug=slug)
    page_url = PAGE_URL.format(slug=slug)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(
                api_url,
                headers={"User-Agent": "TravelRisk/1.0", "Accept": "application/json"},
            )
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        return {"available": False, "source": "UK FCDO", "url": page_url,
                "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"available": False, "source": "UK FCDO", "url": page_url, "error": str(e)}

    details = data.get("details", {})
    parts = details.get("parts", [])

    # Extract summary and safety sections
    sections = {}
    priority = ["summary", "safety-and-security", "health", "entry-requirements"]
    for part in parts:
        slug_part = part.get("slug", "")
        if slug_part in priority:
            body_html = part.get("body", "")
            text = BeautifulSoup(body_html, "lxml").get_text(separator=" ", strip=True)
            sections[slug_part] = {"title": part.get("title", slug_part), "text": text[:800]}

    last_updated = data.get("public_updated_at", "")
    if last_updated:
        last_updated = last_updated[:10]

    # Build section list in priority order
    ordered_sections = [sections[k] for k in priority if k in sections]

    return {
        "available": True,
        "source": "UK Foreign, Commonwealth & Development Office (FCDO)",
        "url": page_url,
        "sections": ordered_sections,
        "last_updated": last_updated,
    }
