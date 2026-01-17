# FAIM-Native TLS Deployment Guide

> Stage-11: Security Hardening

This guide explains how to deploy FAIM-Native with TLS encryption in transit.

## Overview

FAIM-Native should **always** be deployed behind a reverse proxy that handles TLS termination.

```
┌─────────────┐     HTTPS      ┌─────────────┐      HTTP      ┌─────────────┐
│   Client    │──────────────▶│  Nginx/     │───────────────▶│  FAIM API   │
│             │    (TLS 1.3)   │  Caddy      │  (localhost)   │  :8000      │
└─────────────┘                └─────────────┘                └─────────────┘
```

## Recommended Architecture

### Option 1: Cloudflare (Simplest)

1. Point your domain to Cloudflare
2. Enable "Full (Strict)" SSL mode
3. Deploy FAIM behind Cloudflare tunnel or direct with origin certificate

**Advantages:**

- Free SSL certificates
- DDoS protection
- No SSL configuration needed

### Option 2: Caddy (Self-Hosted)

Caddy automatically provisions Let's Encrypt certificates.

```yaml
# docker-compose.yml addition
services:
  caddy:
    image: caddy:2
    container_name: faim-caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    networks: [faim-net]
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
```

```Caddyfile
# Caddyfile
api.yourdomain.com {
    reverse_proxy faim-api:8000

    encode gzip

    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
    }
}
```

### Option 3: Nginx (Traditional)

```nginx
# /etc/nginx/sites-available/faim
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # TLS 1.2/1.3 only
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Database TLS

### PostgreSQL TLS

For remote databases, enable TLS:

```bash
# In .env
DATABASE_URL=postgresql://user:pass@db.example.com:5432/faim?sslmode=require
```

SSL Modes:

- `require` - Encrypt connection (minimum for production)
- `verify-ca` - Verify server certificate
- `verify-full` - Verify hostname matches certificate

### Redis TLS

For remote Redis:

```bash
REDIS_URL=rediss://user:pass@redis.example.com:6379
```

Note the `rediss://` scheme (with double 's').

## Security Headers

Required headers (set by reverse proxy):

| Header                      | Value                                 | Purpose               |
| --------------------------- | ------------------------------------- | --------------------- |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS           |
| `X-Content-Type-Options`    | `nosniff`                             | Prevent MIME sniffing |
| `X-Frame-Options`           | `DENY`                                | Prevent clickjacking  |
| `X-XSS-Protection`          | `1; mode=block`                       | XSS protection        |

## Certificate Management

### Let's Encrypt (Recommended)

Use Caddy (automatic) or certbot:

```bash
certbot certonly --webroot -w /var/www/html -d api.yourdomain.com
```

Renewal is automatic with systemd timer.

### Self-Signed (Development Only)

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout selfsigned.key \
    -out selfsigned.crt \
    -subj "/CN=localhost"
```

## Verification

Test your TLS configuration:

```bash
# Check TLS version
openssl s_client -connect api.yourdomain.com:443 -tls1_3

# Check headers
curl -I https://api.yourdomain.com/ready

# SSL Labs test
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=api.yourdomain.com
```

Expected grades:

- SSL Labs: A or A+
- Mozilla Observatory: A+

## Checklist

- [ ] TLS 1.2+ only (no TLS 1.0/1.1)
- [ ] HSTS enabled with long max-age
- [ ] HTTP redirects to HTTPS
- [ ] No HTTP endpoints exposed
- [ ] PostgreSQL connection uses SSL
- [ ] Redis connection uses SSL (if remote)
- [ ] Security headers configured
- [ ] Certificates auto-renew
