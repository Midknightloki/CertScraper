from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import re
import asyncio

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

def sanitize_filename(text: str) -> str:
    # Replace any non-alphanumeric character with underscore
    return re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_')

async def scrape_certification(cert_id: str) -> list[Path]:
    """Scrape Microsoft Learn pages for a certification and generate PDFs."""
    pdf_paths = []
    cert_folder = OUTPUT_DIR / cert_id
    cert_folder.mkdir(parents=True, exist_ok=True)

    # Start with the certification page
    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    
    async def _scrape_page(url: str):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            
            # Extract links that look like study material
            links = page.query_selector_all("a[href]")
            study_urls = set()
            for link in links:
                href = link.get_attribute("href")
                if href and "learn.microsoft.com" in href:
                    # Normalize URL
                    if href.startswith("/"):
                        full_url = "https://learn.microsoft.com" + href
                    else:
                        full_url = href
                    if any(keyword in href.lower() for keyword in ["training", "documentation", "learning-path"]):
                        study_urls.add(full_url)
            
            # Generate PDF for each study URL
            for url in study_urls:
                # Derive a filename based on URL path
                filename = sanitize_filename(url) + ".pdf"
                pdf_path = cert_folder / filename
                # Use Playwright to PDF the page
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    await page.goto(url, wait_until="networkidle")
                    await page.pdf(path=pdf_path, timeout=60000)
                    await browser.close()
                pdf_paths.append(pdf_path)
    
    # Schedule all page scrapes concurrently
    await _scrape_page(start_url)
    
    # Optionally, recursively follow pagination or additional links
    # For now, just process the direct links found on the certification page
    
    await browser.close()
    return pdf_paths

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # List all PDF files generated so far
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
        },
    )

@app.get("/{cert_id}/downloads")
async def get_cert_downloads(cert_id: str):
    if cert_id not in CERTIFICATIONS:
        return {"error": "Invalid certification ID"}
    
    # Run scraping (non-blocking)
    pdf_paths = await scrape_certification(cert_id)
    return {
        "status": "Scraping completed",
        "cert_id": cert_id,
        "generated_pdfs": [p.name for p in pdf_paths],
    }

@app.get("/pdfs/{filename}", response_class=FileResponse)
async def download_pdf(filename: str):
    # Search in certification subfolders
    for cert_id in CERTIFICATIONS:
        cert_folder = OUTPUT_DIR / cert_id
        pdf_path = cert_folder / filename
        if pdf_path.exists():
            return FileResponse(pdf_path)
    return {"error": "File not found"}