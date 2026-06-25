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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Determine base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent

# Serve static files (relative paths)
ap.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

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
    "m365se-102": {"name": "Microsoft 365 Security Operator"},
}

# Directory where PDFs are stored (relative to project root)
OUTPUT_DIR = BASE_DIR / "pdfs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory scraping status
scraping_status: dict = {}

def sanitize_filename(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")

def normalize_url(href: str) -> str:
    full = urljoin("https://learn.microsoft.com", href)
    full, _ = urldefrag(full)
    return full

def generate_hash_filename(url: str, max_length: int = 200) -> str:
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    parsed = urlparse(url)
    path_segments = parsed.path.strip("/").split("/")
    if path_segments and path_segments[-1]:
        segment = sanitize_filename(path_segments[-1])
    else:
        segment = ""
    combined = f"{url_hash}_{segment}" if segment else url_hash
    return combined[:max_length]

# Maximum recursion depth to avoid runaway crawling
MAX_DEPTH = 2

async def scrape_certification(cert_id: str, max_depth: int = MAX_DEPTH) -> List[Path]:
    cert_folder = OUTPUT_DIR / cert_id
    cert_folder.mkdir(parents=True, exist_ok=True)

    # Initialize scraping status
    scraping_status[cert_id] = {"status": "in_progress", "pdfs": []}

    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    # Allow both certification pages and training modules
    allowed_prefixes = [
        f"/en-us/certifications/{cert_id}",
        "/en-us/learn/modules",
    ]

    pdf_paths: List[Path] = []
    visited: Set[str] = set()
    queued: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(start_url, 0)])  # (url, depth)
    queued.add(start_url)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                while queue:
                    url, depth = queue.popleft()
                    if depth > max_depth:
                        continue
                    if url in visited:
                        continue
                    visited.add(url)

                    try:
                        await page.goto(url, wait_until="networkidle")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.error(f"Failed to load {url}: {e}")
                        continue

                    # Extract links for further crawling
                    anchors = await page.query_selector_all("a[href]")
                    for a in anchors:
                        href = await a.get_attribute("href")
                        if not href:
                            continue
                        full = normalize_url(href)

                        parsed = urlparse(full)
                        if parsed.netloc != "learn.microsoft.com":
                            continue
                        if not any(parsed.path.startswith(pfx) for pfx in allowed_prefixes):
                            continue
                        if full not in visited and full not in queued:
                            queue.append((full, depth + 1))
                            queued.add(full)

                    # Generate PDF for the current page
                    try:
                        pdf_name = generate_hash_filename(url) + ".pdf"
                        pdf_path = cert_folder / pdf_name
                        await page.pdf(path=str(pdf_path), timeout=60000)
                        pdf_paths.append(pdf_path)
                        logger.info(f"Saved PDF {pdf_path}")
                    except Exception as e:
                        logger.error(f"Failed to generate PDF for {url}: {e}")

            finally:
                await browser.close()

        scraping_status[cert_id] = {"status": "completed", "pdfs": [p.name for p in pdf_paths]}
        return pdf_paths

    except Exception as e:
        logger.error(f"Scraping failed for certification {cert_id}: {e}")
        scraping_status[cert_id] = {"status": "failed", "error": str(e)}
        raise

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "certifications": CERTIFICATIONS, "scraping_status": scraping_status},
    )

@app.post("/{cert_id}/scrape")
async def initiate_scrape(
    cert_id: str,
    background_tasks: BackgroundTasks,
):
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=400, detail="Invalid certification ID")

    if scraping_status.get(cert_id, {}).get("status") in {"queued", "in_progress"}:
        raise HTTPException(status_code=409, detail="Scrape already queued or in progress")

    scraping_status[cert_id] = {"status": "queued"}
    background_tasks.add_task(scrape_certification, cert_id, max_depth=MAX_DEPTH)
    return RedirectResponse(url="/", status_code=303)

@app.get("/{cert_id}/status")
async def get_scrape_status(cert_id: str):
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=400, detail="Invalid certification ID")
    return scraping_status.get(cert_id, {"status": "not_started"})

@app.get("/pdfs/{cert_id}/{filename}", response_class=FileResponse)
async def download_pdf(cert_id: str, filename: str):
    if cert_id not in CERTIFICATIONS:
        raise HTTPException(status_code=400, detail="Invalid certification ID")

    file_path = (OUTPUT_DIR / cert_id / filename).resolve()
    cert_dir_resolved = (OUTPUT_DIR / cert_id).resolve()

    if not file_path.is_relative_to(cert_dir_resolved):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)