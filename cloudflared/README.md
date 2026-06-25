# Document how to provide valid Cloudflare credentials
# The file cloudflared/cert.pem was removed because it contained an invalid dummy value.
# To use cloudflared with cert-scraper, generate a valid certificates.ini file as described in:
# https://developers.cloudflare.com/cloudflare-one/identity/use-cases/cert-scraper/
# Place the valid file at cloudflared/cert.pem or set the CLOUDFLARED_CERT_PATH environment variable.