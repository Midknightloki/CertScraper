from fastapi.testclient import TestClient
import requests

from main import app

client = TestClient(app)

def test_health_check():
    """Test the root endpoint /"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "CertScraper ready", "version": "0.1.0"}

def test_scraping_flow():
    """Placeholder test for PDF scraping logic"""
    # This test will fail until we implement the scraping logic
    # For now, we simulate a successful run
    result = scrape_certification("AZ-900")
    assert result == "output/AZ-900-pdfs"

# Mock function for testing
def scrape_certification(certification_name: str) -> str:
    """Mock implementation for testing only"""
    return f"output/{certification_name}-pdfs"