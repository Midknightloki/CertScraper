from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
import subprocess  # Added missing import

app = Flask(__name__)

CERTIFICATIONS_PAGE = "https://learn.microsoft.com/en-us/certifications/"
SCREENSHOT_DIR = os.path.join(os.getcwd(), "screenshots")
BASE_DOMAIN = "https://certscraper.holocronlabs.net"

@app.route("/api/certifications")
def search_certifications():
    q = request.args.get("q")
    if not q:
        return jsonify(
            error="Missing query parameter",
            details="Use ?q=<search_term>"
        ), 400

    results = []
    total_pages = 1  # Static number of pages per certification

    for page in range(1, total_pages + 1):
        url = f"{CERTIFICATIONS_PAGE}/?q={q}&page={page}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract certification cards
        cert_cards = soup.find_all("article", class_="certification-card")
        for card in cert_cards:
            title = card.find("h3").text.strip()
            summary = card.find("p").text.strip()

            # Save screenshot of certification page
            page_url = f"{BASE_DOMAIN}/certification/{len(results)}"
            subprocess.run(
                ["wkhtmltoimage", "--width=1024", "--width=1024", "--crop-w=1024", "--crop-h=1024", page_url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Find linked modules from certification page
            module_links = []
            module_response = requests.get(page_url)
            module_soup = BeautifulSoup(module_response.text, "html.parser")
            for module_link in module_soup.find_all("a", href=True):
                if module_link.get("href").startswith("/learn/"):
                    module_url = f"{BASE_DOMAIN}{module_link.get('href')}"  # Fixed quotes
                    module_data = {
                        "url": module_url,
                        "num_pages": total_pages
                    }
                    module_links.append(module_data)

            results.append({
                "title": title,
                "summary": summary,
                "related_modules": module_links,
                "direct_url": page_url
            })

    return jsonify(certifications=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)