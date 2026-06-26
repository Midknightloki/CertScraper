from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import re
import asyncio
import logging
from typing import List, Set, Tuple
from urllib.parse import urlparse, urljoin, urldefrag
from playwright.async_api import async_playwright
from collections import deque
import hashlib
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Determine base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Serve static files (relative paths)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates directory (relative to project root)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Certification list (example subset)
CERTIFICATIONS = {
    "az-104": {"name": "Microsoft Azure Fundamentals"},
    "pl-900": {"name": "Microsoft Power Platform Fundamentals"},
    "ai-900": {"name": "Microsoft Azure AI Fundamentals"},
    "sc-900": {"name": "Microsoft Security, Compliance, and Identity Fundamentals"},
    "m365sc-101": {"name": "Microsoft 365 Messaging"},
    "m365si-101": {"name": "Microsoft 365 Identity and Access Administrator"},
    "m365se-101": {"name": "Microsoft 365 Security Administrator"},
    "m365se-102": {"name": "Microsoft 365 Security Operator"}
}

# Directory where PDFs are stored
OUTPUT_DIR = BASE_DIR / "pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Status file to persist scraping state across restarts
STATUS_FILE = BASE_DIR / "scraping_status.json"

# Load scraping status from file if exists, otherwise initialize empty dict
if STATUS_FILE.exists():
    try:
        with open(STATUS_FILE, "r") as f:
            scraping_status: dict = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load scraping status: {e}")
        scraping_status = {}
else:
    scraping_status = {}

def save_scraping_status():
    """Persist scraping status to disk."""
    try:
        with open(STATUS_FILE, "w") as f:
            json.dump(scraping_status, f)
    except Exception as e:
        logger.error(f"Failed to save scraping status: {e}")

# ... [rest of the content remains the same]  # ( Conserved unchanged )  