from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import re
from typing import List

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

# Output directory for PDFs (mounted volume)
OUTPUT_DIR = Path("/app/pdfs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def sanitize_filename(text: str) -> str:
    # Replace any non-alphanumeric character with underscore
    return re.sub(r'\W+', '_', text)

def scrape_certification(cert_id: str) -> List[str]:
    """Scrape Microsoft Learn pages for a certification and generate PDFs."""
    from playwright.sync_api import sync_playwright

    pdf_paths = []
    # URLs to explore
    start_url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(start_url)

        # Collect all links that look like study material
        links = page.query_selector_all("a[href]")
        study_urls = set()
        for link in links:
            href = link.get_attribute("href")
            if href and "learn.microsoft.com" in href and (
                "training" in href or "documentation" in href or "learning-path" in href
            ):
                full_url = "https://learn.microsoft.com" + href if href.startswith("/") else href
                study_urls.add(full_url)

        # Generate PDF for each study URL
        for url in study_urls:
            page.goto(url, wait_until="networkidle")
            filename = sanitize_filename(url) + ".pdf"
            pdf_path = OUTPUT_DIR / filename
            page.pdf(path=pdf_path, timeout=60000)
            pdf_paths.append(pdf_path.name)

        browser.close()
    return pdf_paths

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # List all PDF files generated so far
    pdf_files = [
        f.name for f in OUTPUT_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".pdf"
    ]
    # Remove tracking file if present
    pdf_files = [name for name in pdf_files if name != "last_scrape.txt"]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "certifications": CERTIFICATIONS,
            "generated_pdfs": pdf_files,
        },
    )

@app.get("/scrape")
async def scrape_endpoint(cert_id: str):
    if cert_id not in CERTIFICATIONS:
        return {"error": "Invalid certification ID"}
    # Run scraping (blocking) – acceptable for demo purposes
    generated_pdfs = scrape_certification(cert_id)
    return {
        "status": "Scraping completed",
        "cert_id": cert_id,
        "generated_pdfs": generated_pdfs,
    }

@app.get("/pdfs/{filename}", response_class=FileResponse)
async def download_pdf(filename: str):
    pdf_path = OUTPUT_DIR / filename
    if not pdf_path.exists():
        return {"error": "File not found"}
    return FileResponse(pdf_path)