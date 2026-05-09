import httpx
from bs4 import BeautifulSoup

DEST_URL = "https://wwwnc.cdc.gov/travel/destinations/traveler/none/{slug}"
NOTICES_URL = "https://wwwnc.cdc.gov/travel/notices"


async def fetch_cdc(parsed: dict) -> dict:
    slug = parsed["slugs"]["cdc"]
    url = DEST_URL.format(slug=slug)

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
    except httpx.HTTPStatusError as e:
        return {"available": False, "source": "US CDC", "url": url,
                "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        return {"available": False, "source": "US CDC", "url": url, "error": str(e)}

    soup = BeautifulSoup(r.text, "lxml")

    # Travel notices / alerts on the page
    notices = []
    for sel in ["div.travel-notice", "div.alert", "ul.notice-list li"]:
        items = soup.select(sel)
        for item in items[:5]:
            text = item.get_text(separator=" ", strip=True)
            if len(text) > 20:
                notices.append(text)
        if notices:
            break

    # Vaccines section
    vaccines = []
    for heading in soup.find_all(["h2", "h3"]):
        if "vaccin" in heading.get_text(strip=True).lower():
            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ("h2", "h3"):
                if sibling.name in ("ul", "ol"):
                    for li in sibling.find_all("li"):
                        vaccines.append(li.get_text(strip=True))
                sibling = sibling.find_next_sibling()
            break

    # General summary from first paragraphs
    summary_parts = []
    main = soup.find("main") or soup.find("div", {"id": "main_content"})
    if main:
        for p in main.find_all("p")[:5]:
            text = p.get_text(separator=" ", strip=True)
            if len(text) > 50:
                summary_parts.append(text)

    return {
        "available": True,
        "source": "US Centers for Disease Control and Prevention (CDC)",
        "url": url,
        "summary": " ".join(summary_parts)[:1000],
        "notices": notices[:5],
        "vaccines": vaccines[:8],
    }
