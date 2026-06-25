from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import re
import asyncio
import logging
from typing import List, Set
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Serve static files (adjusted to match Docker WORKDIR /app)
app.mount("/static", StaticFiles(directory="/app/static"), name="static")
# Templates directory (relative to project root)
templates = Jinja2Templates(directory="/app/templates")

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

# Directory where PDFs are stored
OUTPUT_DIR = Path("/app/pdfs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In‑memory scraping status
scraping_status: dict = {}

def sanitize_filename(text: str) -> str:
    """Create a filesystem‑safe filename from a URL."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_")

def normalize_url(href: str) -> str:
    """Resolve relative URLs against the Microsoft Learn base URL."""
    return urljoin("https://learn.microsoft.com", href)

async def scrape_certification(cert_id: str) -> List[Path]:
    """Recursively crawl a certification's Learn pages and save each as a PDF.

    The crawler is constrained to URLs that start with the certification's
    module path to avoid crawling the entire Microsoft documentation site.
    """
    cert_folder = OUTPUT_DIR / cert_id
    cert_folder.mkdir(parents=True, exist_ok=True)
    scraping_status[cert_id] = {"status": "in_progress", "pdfs": []}

    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    # The Learn navigation for a cert uses the path /en-us/learn/certifications/<cert_id>/... 
    allowed_prefix = f"/en-us/learn/certifications/{cert_id}"

    pdf_paths: List[Path] = []
    visited: Set[str] = set()
    queue: List[str] = [start_url]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        while queue:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(0.5)
                # Extract anchors
                anchors = await page.query_selector_all("a[href]")
                for a in anchors:
                    href = await a.get_attribute("href")
                    if not href:
                        continue
                    full = normalize_url(href)
                    parsed = urlparse(full)
                    if parsed.netloc != "learn.microsoft.com":
                        continue
                    if not parsed.path.startswith(allowed_prefix):
                        continue
                    if full not in visited:
                        queue.append(full)
                # Generate PDF for current page
                pdf_name = sanitize_filename(url) + ".pdf"
                pdf_path = cert_folder / pdf_name
                pdf_page = await browser.new_page()
                await pdf_page.goto(url, wait_until="networkidle")
                await pdf_page.pdf(path=str(pdf_path), timeout=60000)
                await pdf_page.close()
                pdf_paths.append(pdf_path)
                logger.info(f"Saved PDF %s", pdf_path)
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                continue
        await browser.close()

    scraping_status[cert_id] = {"status": "completed", "pdfs": [p.name for p in pdf_paths]}
    return pdf_paths

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the landing page with certification list and status."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "certifications": CERTIFICATIONS,
            "scraping_status": scraping_status,
        },
    )

@app.post("/{cert_id}/scrape")
async def initiate_scrape(cert_id: str, background_tasks: BackgroundTasks):
    if cert_id not in CERTIFICATIONS:
        return JSONResponse({"error": "Invalid certification ID"}, status_code=400)
    if scraping_status.get(cert_id, {}).get("status") in {"queued", "in_progress"}:
        return JSONResponse({"error": "Scrape already queued or in progress"}, status_code=409)
    scraping_status[cert_id] = {"status": "queued"}
    background_tasks.add_task(scrape_certification, cert_id)
    return {"status": "queued", "cert_id": cert_id}

@app.get("/{cert_id}/status")
async def get_scrape_status(cert_id: str):
    if cert_id not in CERTIFICATIONS:
        return JSONResponse({"error": "Invalid certification ID"}, status_code=400)
    return scraping_status.get(cert_id, {"status": "not_started"})

@app.get("/pdfs/{cert_id}/{filename}", response_class=FileResponse)
async def download_pdf(cert_id: str, filename: str):
    """Download a PDF generated for a specific certification.

    Path traversal is prevented using Path.is_relative_to (Python 3.9+).
    """
    file_path = (OUTPUT_DIR / cert_id / filename).resolve()
    try:
        # Ensure the file is inside the OUTPUT_DIR
        if not file_path.is_relative_to(OUTPUT_DIR.resolve()):
            raise ValueError("Path traversal detected")
    except Exception:
        return JSONResponse({"error": "Invalid file path"}, status_code=400)
    if not file_path.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(file_path)
