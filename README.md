# CertScraper - Microsoft Certification Material PDF Generator

A self-hostable web app to scrape official Microsoft Learn study materials and save them as PDFs.

## Technical Stack
- **Backend**: Python, FastAPI, Playwright
- **Deployment**: Docker
- **Infrastructure**: Docker Host (Nidavellir), Cloudflare Tunnel (`certscraper.holocronlabs.net`)

## Structure
- `backend/`: FastAPI application and scraping logic.
- `Dockerfile`: Multi-stage build for Python and Playwright.

## Installation
1. Build the image:
   ```bash
   docker build -t certscraper .
   ```
2. Run the container:
   ```bash
   docker run -p 8000:8000 certscraper
   ```
