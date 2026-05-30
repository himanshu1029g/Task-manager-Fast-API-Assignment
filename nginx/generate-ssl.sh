#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# generate-ssl.sh — Generate a self-signed SSL certificate for NGINX
#
# Usage (run once on your EC2 server):
#   chmod +x nginx/generate-ssl.sh
#   ./nginx/generate-ssl.sh
#
# For production with a real domain, use Certbot instead:
#   sudo apt install certbot python3-certbot-nginx
#   sudo certbot --nginx -d yourdomain.com
# ─────────────────────────────────────────────────────────────────

SSL_DIR="$(dirname "$0")/ssl"
mkdir -p "$SSL_DIR"

openssl req -x509 \
  -newkey rsa:4096 \
  -keyout "$SSL_DIR/key.pem" \
  -out    "$SSL_DIR/cert.pem" \
  -days   365 \
  -nodes \
  -subj "/C=IN/ST=Punjab/L=Mohali/O=DevOps Assignment/CN=task-manager"

echo ""
echo "✅ Self-signed SSL certificate generated:"
echo "   cert → $SSL_DIR/cert.pem"
echo "   key  → $SSL_DIR/key.pem"
echo ""
echo "⚠️  Browsers will show a warning (expected for self-signed certs)."
echo "   Add -k flag to curl to skip verification: curl -k https://your-ip/health"
