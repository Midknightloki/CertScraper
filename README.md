# CertScraper: Microsoft Certification Material Scraper

A self-hosted web application that scrapes and generates PDFs of Microsoft certification study materials for easy offline studying and integration with Notebook LM.

## Overview

CertScraper provides a searchable interface to access official Microsoft certification materials. Once a certification is selected, it recursively scrapes all study materials from Microsoft Learn and generates PDFs for offline access.

## Features

- **Searchable Certification List**: Browse all Microsoft certifications
- **Recursive Material Scraping**: Extract all study materials from Microsoft Learn
- **PDF Generation**: Convert web content to PDFs for offline use
- **Docker Deployment**: Easy deployment to Docker hosts
- **Cloudflare Integration**: Publish via Cloudflare tunnel

## Quick Start

### Prerequisites

- Docker with Docker Compose
- Cloudflare account with tunnel access

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd CertScraper
   ```

2. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access the application:
   ```
   http://localhost:8000
   ```

### Usage

1. Browse available certifications from the homepage
2. Search for a specific certification
3. Select a certification to generate study materials
4. Download the generated PDF files

### Deployment

For production deployment, update the `CATEGORIES` list in `backend/main.py` with all available Microsoft certifications. The system will automatically scrape and generate PDFs for each certification path.

#### Docker-specific notes:

- The application runs on port 8000
- Generated PDFs are stored in the `./pdfs` directory (persistent across restarts)
- Cloudflare tunnel configuration is in `cloudflared/config.yml`
- The terminal logs from `backend/main.py` are streamed via Cocker, which must be configured in `docker-compose.yml` for persistent logging.

## File Structure

- `app.py`: Primary FastAPI backend application (handles scraping and PDF generation)
- `backend/`: API implementation
- `frontend/`: HTML frontend interface
- `static/`: CSS and JavaScript files
- `templates/`: HTML templates for dynamic pages
- `certifications_page.html`: Alternative static page for certification display
- `Dockerfile`: Docker configuration for application container
- `backend/requirements.txt`: Backend dependencies
- `requirements.txt`: Application dependencies
- `docker-compose.yml`: Docker container orchestration
- `cloudflared/config.yml`: Cloudflare tunnel configuration

## Architecture

The application is built using:

1. **FastAPI**: Backend framework for API endpoints
2. **Playwright**: Web scraping engine for Microsoft Learn
3. **wkhtmltopdf**: PDF generation tool
4. **BeautifulSoup**: HTML parsing
5. **Docker**: Containerization for deployment

## License

This project is licensed under the MIT License.

## Technologies

- Frontend: HTML5, CSS3, JavaScript
- Backend: Python 3.9+, FastAPI, Playwright
- Build Tools: Docker, Docker Compose
- Deployment: Cloudflare Tunnel
- Development: Cocker terminal logging