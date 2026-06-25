from fastapi import FastAPI

app = FastAPI()

@app.get("/certs")
async def get_certs():
    # TODO: Implement Microsoft cert search
    return {
        "message": "CertScraper API. Search endpoint not yet implemented."
    }

@app.get("/\{cert_id}/downloads")
async def get_cert_downloads(cert_id: str):
    # TODO: Implement recursive scraping and PDF generation
    return {
        "message": f"Downloads for \{cert_id\}. Scraper functionality not yet implemented."
    }