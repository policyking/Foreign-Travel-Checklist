from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
import asyncio
import os
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from claude_parser import parse_travel_intent
from sources.state_dept import fetch_state_dept
from sources.fcdo import fetch_fcdo
from sources.cdc import fetch_cdc
from sources.who import fetch_who
from sources.reliefweb import fetch_reliefweb
from sources.acled import fetch_acled

app = FastAPI(title="Travel Risk Intelligence")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    destination_text: str
    dates_text: str


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    parsed = await parse_travel_intent(req.destination_text, req.dates_text)

    results = await asyncio.gather(
        fetch_state_dept(parsed),
        fetch_fcdo(parsed),
        fetch_cdc(parsed),
        fetch_who(parsed),
        fetch_reliefweb(parsed),
        fetch_acled(parsed),
        return_exceptions=True,
    )

    source_keys = ["state_dept", "fcdo", "cdc", "who", "reliefweb", "acled"]
    sources = {}
    for key, result in zip(source_keys, results):
        if isinstance(result, Exception):
            sources[key] = {"available": False, "error": str(result)}
        else:
            sources[key] = result

    return {"parsed": parsed, "sources": sources}


frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="static")
