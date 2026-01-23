# SSL Certificate Generation for Development

## Self-Signed Certificate (Development)

This directory will contain SSL certificates for development.

To generate a self-signed certificate for local development:

```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/cert.key \
  -out nginx/ssl/cert.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

## Let's Encrypt (Production)

For production deployment with Let's Encrypt:

1. Uncomment the certbot service in docker-compose.yml
2. Update nginx/conf.d/default.conf to uncomment the HTTPS server block
3. Replace "your-domain.com" with your actual domain
4. Run the following to obtain certificates:

```bash
docker-compose run --rm certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  -d your-domain.com \
  -d www.your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email
```

5. Restart nginx:

```bash
docker-compose restart nginx
```

Certificates will auto-renew via the certbot container.
