ISS Portal - Distribution Package
==================================

Version: 1.0.0
Build Date: 2026-01-21 14:40:30

Quick Start:
1. Extract this package to /opt/iss-portal on your Linux server
2. Follow instructions in DEPLOYMENT.md

Requirements:
- Ubuntu 22.04 LTS (or similar Linux distribution)
- Docker 24.0+
- Docker Compose 2.20+
- 2GB RAM minimum (4GB recommended)
- 20GB disk space minimum

Installation:
  sudo mkdir -p /opt/iss-portal
  sudo tar -xzf iss-portal-v1.0.0.tar.gz -C /opt/
  cd /opt/iss-portal-v1.0.0
  cp .env.example .env
  nano .env  # Configure environment (IMPORTANT: Set encryption key!)
  ./deploy.sh

Documentation:
  See DEPLOYMENT.md for complete installation and configuration guide

Support:
  Check application logs: docker-compose logs -f web
  Check status: ./status.sh
  
IMPORTANT:
  - Generate encryption key before deployment
  - Set strong passwords in .env
  - Keep encryption key backed up securely
