import json
import httpx
from datetime import date

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

SYSTEM = """You are a travel intelligence parser. Extract structured destination and date information from freeform text.
Return ONLY valid JSON, no markdown fences, no explanation, nothing else."""


async def parse_travel_intent(destination_text: str, dates_text: str) -> dict:
    today = date.today().isoformat()

    prompt = f"""{SYSTEM}

Parse this travel information. Today is {today}.

DESTINATION: {destination_text}
DATES: {dates_text}

Return this exact JSON (null for unknown fields):
{{
  "country": "Full English country name",
  "city": "Primary city or null",
  "region": "Geographic region (e.g. Middle East, West Africa, Southeast Asia)",
  "slugs": {{
    "state_dept": "lowercase-hyphenated slug for travel.state.gov (e.g. france, united-kingdom, saudi-arabia)",
    "fcdo": "lowercase-hyphenated slug for gov.uk/foreign-travel-advice (e.g. france, jordan, south-korea)",
    "cdc": "lowercase-hyphenated slug for CDC destination pages (e.g. france, jordan, south-korea)"
  }},
  "dates": {{
    "departure": "YYYY-MM-DD or null",
    "return": "YYYY-MM-DD or null",
    "duration_days": integer or null
  }},
  "context": {{
    "purpose": "trip purpose or null",
    "notes": "any other relevant details or null"
  }}
}}"""

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        })
        r.raise_for_status()
        raw = r.json()["response"].strip()

    # Strip markdown fences if model adds them
    if "```" in raw:
        for block in raw.split("```"):
            block = block.strip().lstrip("json").strip()
            try:
                return json.loads(block)
            except Exception:
                continue

    return json.loads(raw)
