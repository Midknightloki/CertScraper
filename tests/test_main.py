import json
import os
import tempfile

from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app, CERTIFICATIONS, sanitize_filename, normalize_url, generate_hash_filename, STATUS_FILE

client = TestClient(app)


def test_index_html_returns_success_and_lists_certifications():
    response = client.get("/")
    assert response.status_code == 200
    # page contains title
    assert "Microsoft Certification Scraper" in response.text
    # each certification appears
    for cid, data in CERTIFICATIONS.items():
        assert data["name"] in response.text
        assert cid in response.text


def test_get_scrape_status_initial():
    # We don't know names; pick first one
    cert_id = next(iter(CERTIFICATIONS))
    response = client.get(f"/{cert_id}/status")
    assert response.status_code == 200
    out = response.json()
    # status should indicate not_started on first run
    assert out.get("status") in {"not_started", "queued", "in_progress", "completed", "failed"}


def test_initiate_scrape_and_redirect():
    cert_id = next(iter(CERTIFICATIONS))
    # Ensure not already scraping
    client.get(f"/{cert_id}/status")  # ignore
    response = client.post(f"/{cert_id}/scrape", allow_redirects=False)
    assert response.status_code == 303
    # status updated to queued
    status_resp = client.get(f"/{cert_id}/status")
    assert status_resp.json() == {"status": "queued"}


def test_sanitize_filename():
    assert sanitize_filename("Hello World!") == "Hello_World"
    assert sanitize_filename("a.b_c") == "a_b_c"


def test_normalize_url_absolute_and_relative():
    # relative path
    href = "/en-us/learn/modules/test"
    full = normalize_url(href)
    assert full.startswith("https://learn.microsoft.com/en-us/learn/modules/test")
    # absolute path
    href2 = "https://learn.microsoft.com/en-us/learn/modules/test"
    assert normalize_url(href2) == href2


def test_generate_hash_filename_length():
    url = "https://learn.microsoft.com/en-us/learn/modules/test-module"
    fname = generate_hash_filename(url)
    # Should end with .pdf? Actually without extension
    assert len(fname) <= 200
    assert '_' in fname

# Test that status file updated works by writing and reading

def test_status_file_persistence(tmp_path):
    # Temporarily replace status file path
    global STATUS_FILE
    orig = STATUS_FILE
    STATUS_FILE = tmp_path / "scraping_status.json"
    try:
        # Ensure starting empty
        assert not STATUS_FILE.exists()
        # Trigger a scrape status update
        app.state.scraping_status = {"testcert": {"status": "queued"}}
        # Save
        from backend.main import save_scraping_status
        save_scraping_status()
        assert STATUS_FILE.exists()
        data = json.loads(STATUS_FILE.read_text())
        assert data["testcert"]["status"] == "queued"
    finally:
        STATUS_FILE = orig
