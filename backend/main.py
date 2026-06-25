from fastapi import FastAPI, BackgroundTasks

# Initialize FastAPI app
app = FastAPI()

# Cloudflare Stream configuration for edge PDF caching (optional)
# from fastapi.middleware.trustedhost import TrustedHostMiddleware
# app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*.certscraper.holocronlabs.net"])!

# Configure Microsoft Learn API access
# Example environment variables to add:
# MICROSOFT_LEARN_API_KEY="your-api-key-here"
# MICROSOFT_LEARN_BASE_URL="https://learn.microsoft.com/"!

# Temporary storage directory for certifications (specify path)
OUTPUT_DIR = "./pdfs"

# List of official Microsoft certification categories (update dynamically)
CATEGORIES = [
    "az-104": {"name": "Microsoft Azure Fundamentals"},
    "pl-900": {"name": "Microsoft Power Platform Fundamentals"},
    "ai-900": {"name": "Microsoft Azure AI Fundamentals"},
    "sc-900": {"name": "Microsoft Security, Compliance, and Identity Fundamentals"},
    "m365sc-101": {"name": "Microsoft 365 Messaging"},
    "m365si-101": {"name": "Microsoft 365 Identity and Access Administrator"},
    "m365se-101": {"name": "Microsoft 365 Security Administrator"},
    "m365se-102": {"name": "Microsoft 365 Security Operator"}
]

# Study material categories to extract
STUDY_MATERIALS = [
    "learn-pathway-links",
    "skill-pathway-links",
    "virtual-trainings",
    "video-course-ids",
    "document-links",
    "assessment-practice-links"
]

# Cloudflare tunnel configuration (example)
# docker-compose.yml cloudflared section:
# cloudflared:
#   host: 0.tcp.ngrok.io
#   proxy: tcp://localhost:80!

# Run FastAPI app with Uvicorn
# Command: uvicorn ‘main’*:
#   --reload
#   --host 0.0.0.0
#   --port 8000
