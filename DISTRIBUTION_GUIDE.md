# ISS Portal - Distribution Guide

This guide explains how to maintain and distribute ISS Portal using both Git and Docker Hub.

## Overview

ISS Portal supports two distribution methods:

1. **Git Repository** - Source code for development and custom builds
2. **Docker Hub** - Pre-built images for fast production deployment

## Git Repository Distribution

### Repository Structure

```
iss-portal/
├── accounts/           # User management app
├── audit/              # Audit logging app  
├── core/               # Main application logic
├── reports/            # Reporting system
├── iss_portal/         # Django settings
├── nginx/              # Nginx configuration
├── static/             # Static files
├── templates/          # Django templates
├── docker-compose.yml  # Local build deployment
├── docker-compose.hub.yml  # Docker Hub deployment
├── docker-compose.prod.yml # Production overrides
├── Dockerfile          # Docker build instructions
├── build-package.sh    # Build deployment package
├── push-to-dockerhub.sh # Push to Docker Hub
└── README.md           # This file
```

### For Developers

**Clone and develop:**
```bash
git clone https://github.com/your-org/iss-portal.git
cd iss-portal
cp .env.example .env
# Edit .env with your settings
docker-compose up -d --build
```

**Make changes:**
```bash
# Edit code
git add .
git commit -m "Description of changes"
git push origin main
```

**Tag releases:**
```bash
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0
```

## Docker Hub Distribution

### Prerequisites

1. **Docker Hub Account:** Create at https://hub.docker.com
2. **Docker Logged In:** `docker login`

### Publishing to Docker Hub

**Step 1: Build and push images:**
```bash
# Push with version tag
./push-to-dockerhub.sh your-dockerhub-username 1.0.0

# The script will:
# - Build Docker image
# - Tag as version and latest
# - Push both tags to Docker Hub
# - Create docker-compose.hub.yml
# - Create DOCKERHUB_DEPLOYMENT.md
```

**Step 2: Create deployment package:**
```bash
# Build source package (includes Docker Hub files)
./build-package.sh 1.0.0

# This creates:
# - dist/iss-portal-v1.0.0.tar.gz (full source + Docker Hub configs)
```

**Step 3: Tag Git release:**
```bash
git add docker-compose.hub.yml DOCKERHUB_DEPLOYMENT.md
git commit -m "Add Docker Hub deployment for v1.0.0"
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin main --tags
```

### Docker Hub Repository Setup

**Repository Name:** `your-username/iss-portal`

**Description:**
```
ISS Portal - Inclusion Support Services Case Management System

Django-based web application for managing children's services with staff 
caseload management, visit tracking, reporting, and field-level encryption.

⭐ Features:
- Role-based access control
- Field-level PII encryption
- Comprehensive reporting
- Visit tracking and caseload management
- Docker-based deployment
- PostgreSQL database
- Nginx reverse proxy

📖 Documentation: https://github.com/your-org/iss-portal
🚀 Quick Start: See DOCKERHUB_DEPLOYMENT.md in package
```

**Tags:**
- `latest` - Most recent stable version
- `1.0.0`, `1.0.1`, etc. - Specific version tags
- `1.0` - Major.minor version (optional)

## Release Workflow

### Complete Release Process

1. **Update version in code**
2. **Test thoroughly**
3. **Update documentation**
4. **Build and push to Docker Hub:**
   ```bash
   ./push-to-dockerhub.sh your-username 1.0.0
   ```

5. **Build deployment package:**
   ```bash
   ./build-package.sh 1.0.0
   ```

6. **Commit Docker Hub files:**
   ```bash
   git add docker-compose.hub.yml DOCKERHUB_DEPLOYMENT.md
   git commit -m "Release v1.0.0"
   ```

7. **Tag and push to Git:**
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin main --tags
   ```

8. **Create GitHub Release:**
   - Go to GitHub → Releases → Draft new release
   - Choose tag: v1.0.0
   - Upload: dist/iss-portal-v1.0.0.tar.gz
   - Upload: dist/iss-portal-v1.0.0.tar.gz.sha256
   - Upload: dist/iss-portal-v1.0.0-RELEASE_NOTES.txt
   - Publish release

## Deployment Methods for End Users

### Method 1: Docker Hub (Recommended)

**Advantages:**
- ✅ Fastest deployment (~2 minutes)
- ✅ No build time
- ✅ Consistent images
- ✅ Easy updates
- ✅ Minimal download

**Steps:**
```bash
# 1. Download minimal files or use docker-compose.hub.yml
# 2. Configure .env
# 3. Deploy
docker-compose -f docker-compose.hub.yml up -d
```

**Users need:**
- docker-compose.hub.yml
- nginx/ configuration
- .env file

### Method 2: Source Package

**Advantages:**
- ✅ Full source code control
- ✅ Customizable
- ✅ No Docker Hub dependency
- ✅ Air-gapped deployment

**Steps:**
```bash
# 1. Download and extract package
tar -xzf iss-portal-v1.0.0.tar.gz
cd iss-portal-v1.0.0

# 2. Run installer (auto-configures)
./install.sh

# 3. Or manually deploy
docker-compose up -d --build
```

## Maintenance

### Updating Docker Hub Images

When you make changes:
```bash
# Update code
git add .
git commit -m "Fix: description"
git push

# Build new version
./push-to-dockerhub.sh your-username 1.0.1

# Build new package
./build-package.sh 1.0.1

# Tag release
git tag -a v1.0.1 -m "Version 1.0.1"
git push --tags
```

### Hotfixes

For critical fixes:
```bash
# Create hotfix branch
git checkout -b hotfix-1.0.1

# Fix issue
git commit -m "Hotfix: critical security patch"

# Push to Docker Hub
./push-to-dockerhub.sh your-username 1.0.1-hotfix

# Merge and tag
git checkout main
git merge hotfix-1.0.1
git tag -a v1.0.1 -m "Hotfix 1.0.1"
git push --tags
```

### Security Updates

For security patches:
```bash
# Update dependencies in requirements.txt
# Rebuild and push immediately
./push-to-dockerhub.sh your-username 1.0.2-security
./build-package.sh 1.0.2

# Tag and document
git tag -a v1.0.2 -m "Security update: CVE-2024-XXXX"
git push --tags

# Notify users to update
```

## Multi-Environment Support

### Development
```bash
# Use docker-compose.yml with live code
docker-compose up -d
```

### Staging
```bash
# Use Docker Hub images
docker-compose -f docker-compose.hub.yml up -d
```

### Production
```bash
# Use Docker Hub + production config
docker-compose -f docker-compose.hub.yml -f docker-compose.prod.yml up -d
```

## Image Versioning Strategy

### Version Tags
- `latest` - Latest stable release (auto-updated)
- `1.0.0` - Specific version (immutable)
- `1.0` - Latest in 1.0 series (optional)
- `1.0.0-hotfix` - Hotfix releases
- `1.0.0-rc1` - Release candidates

### Best Practices
- Always tag with semantic version
- Keep latest tag updated
- Document breaking changes
- Test before pushing to latest
- Use pre-release tags for testing

## Distribution Checklist

Before each release:

- [ ] All tests passing
- [ ] Documentation updated
- [ ] DEPLOYMENT.md reviewed
- [ ] Version bumped in VERSION file
- [ ] CHANGELOG.md updated
- [ ] Docker image built and tested
- [ ] Pushed to Docker Hub
- [ ] Source package built
- [ ] Checksums generated
- [ ] Git tagged
- [ ] GitHub release created
- [ ] Release notes published

## Support Resources

### For Contributors
- Development setup in README.md
- Contributing guidelines in CONTRIBUTING.md
- Code style guide

### For Deployers
- DEPLOYMENT.md - Comprehensive deployment guide
- DOCKERHUB_DEPLOYMENT.md - Docker Hub specific guide
- PACKAGE_README.md - Package installation guide

### For End Users
- README.md in package - Quick start
- Documentation site (if available)
- Support channels

## Monitoring Deployments

### Docker Hub Stats
- Check pull statistics at https://hub.docker.com/r/your-username/iss-portal/tags
- Monitor download counts
- Review user feedback

### Git Repository
- Watch for issues
- Monitor pull requests
- Track stars/forks

---

**Last Updated:** February 2, 2026  
**Current Version:** 1.0.0  
**Docker Hub:** your-username/iss-portal  
**Git:** https://github.com/your-org/iss-portal
