from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import re
import asyncio
import logging
from typing import List, Set
from playwright.async_api import async_playwright

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
    if href.startswith("/"):
        return "https://learn.microsoft.com" + href
    return href

async def scrape_certification_page(url: str, save_dir: Path, browser, visited_urls: Set[str]) -> List[Path]:
    """Scrape a Microsoft Learn page and all linked study material pages."""
    pdf_paths = []
    
    page = await browser.new_page()
    
    try:
        # Navigate to the page and extract all links
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(2)  # Give time for content to load
        
        # Get all links on the page
        links = await page.query_selector_all("a[href]")
        
        # Process each link that looks like study material
        for link in links:
            href = await link.get_attribute("href")
            
            # Check if this is a valid Microsoft Learn URL (includes relative paths)
            if not href:
                continue
            
            # Normalize URL to handle relative paths
            full_url = normalize_url(href)
            
            # Skip URLs that aren't from Microsoft Learn
            if "learn.microsoft.com" not in full_url:
                continue
            
            # Skip already visited URLs to avoid loops and duplicates
            if full_url in visited_urls:
                continue
            
            visited_urls.add(full_url)
            
            # Generate PDF for this URL
            try:
                filename = sanitize_filename(full_url) + ".pdf"
                pdf_path = save_dir / filename
                
                # Reuse existing browser instance - just create a new page
                pdf_page = await browser.new_page()
                await pdf_page.goto(full_url, wait_until="networkidle")
                await pdf_page.pdf(path=str(pdf_path), timeout=60000)
                await pdf_page.close()
                
                pdf_paths.append(pdf_path)
                logger.info(f"Generated PDF: {pdf_path}")
                
            except Exception as e:
                logger.error(f"Failed to generate PDF for {full_url}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to scrape page {url}: {e}")
    finally:
        await page.close()
    
    return pdf_paths

async def scrape_certification(cert_id: str) -> List[Path]:
    """Scrape Microsoft Learn pages for a certification and generate PDFs."""
    global scraping_status
    
    pdf_paths = []
    cert_folder = OUTPUT_DIR / cert_id
    cert_folder.mkdir(parents=True, exist_ok=True)
    
    # Update status
    scraping_status[cert_id] = {"status": "in_progress", "pdfs": []}

    # Start with the certification page
    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            # Track visited URLs to prevent loops
            visited_urls: Set[str] = set()
            
            # Scrape main page
            main_pdfs = await scrape_certification_page(start_url, cert_folder, browser, visited_urls)
            pdf_paths.extend(main_pdfs)
            
            await browser.close()
        
        scraping_status[cert_id] = {"status": "completed", "pdfs": [p.name for p in pdf_paths]}
        
    except Exception as e:
        logger.error(f"Scraping failed for {cert_id}: {e}")
        scraping_status[cert_id] = {"status": "failed", "error": str(e)}
    
    return pdf_paths

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """List all PDF files generated so far."""
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
        return {"error": "Invalid certification ID"}
    
    # Run scraping in background
    scraping_status[cert_id] = {"status": "queued"}
    background_tasks.add_task(scrape_certification, cert_id)
    
    return {"status": "Scraping job initiated", "cert_id": cert_id}

@app.get("/{cert_id}/status")
async def get_scrape_status(cert_id: str):
    """Get the current scraping status for a certification."""
    if cert_id not in CERTIFICATIONS:
        return {"error": "Invalid certification ID"}
    
    status = scraping_status.get(cert_id, {"status": "not_started"})
    return status

@app.get("/pdfs/{filename}", response_class=FileResponse)
async def download_pdf(filename: str):
    """Search in certification subfolders and return the PDF file."""
    for cert_id in CERTIFICATIONS:
        cert_folder = OUTPUT_DIR / cert_id
        pdf_path = cert_folder / filename
        if pdf_path.exists():
            return FileResponse(pdf_path)
    return {"error": "File not found"}