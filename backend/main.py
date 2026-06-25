import os
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List
from pathlib import Path
from playwright.async_api import async_playwright

app = FastAPI()

CERT_LIST = [
    {"id": "az-900", "name": "Microsoft Azure Fundamentals"},
    {"id": "ai-102", "name": "Designing and Implementing an Azure AI Solution"},
    {"id": "dp-100", "name": "Microsoft Power Platform Data Analyst"},
    # Add more certifications as needed
]

class CertRequest(BaseModel):
    cert_id: str

@app.get("/certs", response_model=List[dict])
async def get_certs():
    return CERT_LIST

@app.post("/scrape")
async def scrape_cert(request: CertRequest, background_tasks: BackgroundTasks):
    cert = next((c for c in CERT_LIST if c["id"] == request.cert_id), None)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{cert['id']}.pdf"
    # Run scraping in background to avoid blocking request
    background_tasks.add_task(run_scrape, cert['id'], str(output_path))
    return {"message": "Scraping started", "output_path": str(output_path)}

async def run_scrape(cert_id: str, output_path: str):
    url = f"https://learn.microsoft.com/en-us/certifications/{cert_id}"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            # Wait for main content to load
            await page.wait_for_selector("main", timeout=60000)
            # Save as PDF
            await page.pdf(path=output_path, format="A4")
            await browser.close()
    except Exception as e:
        # Log error (in real app use proper logging)
        print(f"Error scraping {cert_id}: {e}")
