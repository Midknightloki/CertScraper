import pytest
from main import scrape_certification, OUTPUT_DIR
from pathlib import Path

@pytest.fixture
async def mock_cert_data():
    # Dummy cert data for testing
    return {
        'az-104': {'name': 'Azure Fundamentals'},
    }

async def test_scrape_certification():
    # Test basic PDF generation
    cert_id = 'az-104'
    pdf_paths = await scrape_certification(cert_id)
    assert len(pdf_paths) > 0
    for pdf in pdf_paths:
        assert pdf.exists()
        assert pdf.suffix == '.pdf'

    # Test status persistence
    assert (OUTPUT_DIR / cert_id / 'az-104_0.pdf').exists()

    # Test status file update
    status_file = Path('scraping_status.json')
    assert status_file.exists()
    with open(status_file, 'r') as f:
        data = json.load(f)
        assert data[cert_id]['status'] == 'completed'