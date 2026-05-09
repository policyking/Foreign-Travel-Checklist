import httpx
import feedparser

RSS_URL = "https://www.who.int/feeds/entity/csr/don/en/rss.xml"
PAGE_URL = "https://www.who.int/emergencies/disease-outbreak-news"


async def fetch_who(parsed: dict) -> dict:
    country = (parsed.get("country") or "").lower()
    region = (parsed.get("region") or "").lower()
    city = (parsed.get("city") or "").lower()

    search_terms = [t for t in [country, city, region] if t]

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(RSS_URL, headers={"User-Agent": "TravelRisk/1.0"})
            r.raise_for_status()
        feed = feedparser.parse(r.text)
    except Exception as e:
        return {"available": False, "source": "WHO Disease Outbreak News", "url": PAGE_URL, "error": str(e)}

    relevant = []
    for entry in feed.entries[:100]:
        content = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
        if any(term in content for term in search_terms):
            relevant.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "")[:400],
                "url": entry.get("link", PAGE_URL),
                "date": entry.get("published", ""),
            })

    return {
        "available": True,
        "source": "World Health Organization — Disease Outbreak News",
        "url": PAGE_URL,
        "alerts": relevant[:6],
        "total_found": len(relevant),
    }
