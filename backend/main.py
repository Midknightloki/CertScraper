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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Certification data
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

# Output directory for PDFs (relative to working directory)
OUTPUT_DIR = Path("./pdfs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# In-memory storage for scraping status
scraping_status = {}

def sanitize_filename(text: str) -> str:
    """Replace any non-alphanumeric character with underscore."""
    return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

def normalize_url(href: str) -> str:
    """Convert relative URLs to absolute URLs."""
    return urljoin("https://learn.microsoft.com", href)

async def scrape_certification(cert_id: str) -> List[Path]:
    """Scrape Microsoft Learn pages for a certification and generate PDFs recursively."""
    global scraping_status
    
    pdf_paths: List[Path] = []
    cert_folder = OUTPUT_DIR / cert_id
    cert_folder.mkdir(parents=True, exist_ok=True)
    
    # Update status
    scraping_status[cert_id] = {"status": "in_progress", "pdfs": []}

    # Start with the certification page
    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # Create a persistent browser context and page for link extraction
            context = await browser.new_context()
            page = await context.new_page()
            
            # BFS queue for recursive link discovery
            queue: List[str] = [start_url]
            visited_urls: Set[str] = set()
            
            while queue:
                url = queue.pop(0)
                if url in visited_urls:
                    continue
                visited_urls.add(url)
                
                # Navigate to the page to extract links
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(1)  # Allow content to render
                
                # Extract all links on the page
                anchors = await page.query_selector_all("a[href]")
                for anchor in anchors:
                    href = await anchor.get_attribute("href")
                    if not href:
                        continue
                    # Normalize and validate URL
                    full_url = normalize_url(href)
                    parsed = urlparse(full_url)
                    if parsed.netloc != "learn.microsoft.com":
                        continue
                    # Skip already visited URLs
                    if full_url not in visited_urls:
                        queue.append(full_url)
                
                # Generate PDF for the current URL
                try:
                    filename = sanitize_filename(url) + ".pdf"
                    pdf_path = cert_folder / filename
                    
                    # Create a dedicated page for PDF generation
                    pdf_page = await browser.new_page()
                    try:
                        await pdf_page.goto(url, wait_until="networkidle")
                        await pdf_page.pdf(path=str(pdf_path), timeout=60000)
                        pdf_paths.append(pdf_path)
                        logger.info(f"Generated PDF: {pdf_path}")
                    finally:
                        await pdf_page.close()
                except Exception as e:
                    logger.error(f"Failed to generate PDF for {url}: {e}")
                    continue
            
            await browser.close()
        
        # Mark as completed
        scraping_status[cert_id] = {"status": "completed", "pdfs": [p.name for p in pdf_paths]}
    
    except Exception as e:
        logger.error(f"Scraping failed for {cert_id}: {e}")
        scraping_status[cert_id] = {"status": "failed", "error": str(e)}
    
    return pdf_paths

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main page listing generated PDFs."""
    pdf_files = []
    for cert_id in CERTIFICATIONS:
        cert_folder = OUTPUT_DIR / cert_id
        if cert_folder.exists():
            pdf_files.extend([p for p in cert_folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"])
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "certifications": CERTIFICATIONS,
            "generated_pdfs": pdf_files,
            "scraping_status": scraping_status,
        },
    )

@app.post("/{cert_id}/scrape")
async def initiate_scrape(cert_id: str, background_tasks: BackgroundTasks):
    """Initiate scraping for a certification (non-blocking)."""
    if cert_id not in CERTIFICATIONS:
        return JSONResponse({"error": "Invalid certification ID"}, status_code=400)
    
    # Prevent duplicate queuing
    current_status = scraping_status.get(cert_id, {}).get("status")
    if current_status in ["queued", "in_progress"]:
        return JSONResponse({"error": "Scraping already queued or in progress"}, status_code=409)
    
    # Queue the scraping task
    scraping_status[cert_id] = {"status": "queued"}
    background_tasks.add_task(scrape_certification, cert_id)
    
    return {"status": "Scraping job initiated", "cert_id": cert_id}

@app.get("/{cert_id}/status")
async def get_scrape_status(cert_id: str):
    """Get the current scraping status for a certification."""
    if cert_id not in CERTIFICATIONS:
        return JSONResponse({"error": "Invalid certification ID"}, status_code=400)
    
    return scraping_status.get(cert_id, {"status": "not_started"})

@app.get("/pdfs/{filename}", response_class=FileResponse)
async def download_pdf(filename: str):
    """Serve a PDF file from the output directory with path traversal protection."""
    # Resolve the requested file path safely
    candidate = (OUTPUT_DIR / filename).resolve()
    # Ensure the resolved path is within OUTPUT_DIR
    if not str(candidate).startswith(str(OUTPUT_DIR.resolve())):
        return JSONResponse({"error": "Invalid file path"}, status_code=400)
    pdf_path = candidate
    if not pdf_path.is_file():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(pdf_path)