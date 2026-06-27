from fastapi import FastAPI
import os

app = FastAPI()

# Base output directory for PDFs
OUTPUT_DIR = "output"

# PDF scraping logic (placeholder implementation)
def scrape_certification(certification_name: str) -> str:
    """
    Saves all study material from Microsoft Learn for a certification as PDF
    
    Returns the path to the saved PDF directory
    """
    # In a real implementation, this would use Microsoft Learn's API or DOM scraping
    # with proper rate limiting and error handling
    
    # For now, return a placeholder
    return os.path.join(OUTPUT_DIR, f"{certification_name}-pdfs")

@app.get("/")
def root():
    """Root endpoint for health checks"""
    return {"status": "CertScraper ready", "version": "0.1.0"}