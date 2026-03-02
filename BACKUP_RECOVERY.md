# ISS Portal — Backup & Recovery Guide

This document covers everything needed to back up the ISS Portal and recover from a backup, including scheduled automation, manual procedures, and disaster recovery from total server loss.

## Table of Contents

1. [What Gets Backed Up](#what-gets-backed-up)
2. [First-Time Setup](#first-time-setup)
3. [Running a Manual Backup](#running-a-manual-backup)
4. [Verifying a Backup](#verifying-a-backup)
5. [Restore Procedure](#restore-procedure)
6. [Disaster Recovery (Full Server Loss)](#disaster-recovery-full-server-loss)
7. [Encryption Key Safety](#encryption-key-safety)
8. [Expanding to Off-Site Storage](#expanding-to-off-site-storage)

---

## What Gets Backed Up

| Item | File in `backups/` | Notes |
|---|---|---|
| PostgreSQL database | `db_backup_YYYYMMDD_HHMMSS.sql.gz` | Full pg_dump, gzip-compressed |
| Environment config | `.env_YYYYMMDD_HHMMSS` | Contains `SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, DB credentials |
| Media uploads | `media_YYYYMMDD_HHMMSS.tar.gz` | Only created when `media/` is non-empty |
| Restore manifest | `backup_YYYYMMDD_HHMMSS.manifest` | Human-readable summary with restore instructions |

**Retention policy:** Files older than **30 days** are automatically deleted at the end of each backup run. Adjust `RETENTION_DAYS` in `backup.sh` to change this.

**Storage location:** `<install-dir>/backups/` on the host server.

---

## First-Time Setup

Run this once after initial deployment to install a daily 2 AM cron job:

```bash
sudo ./setup-cron.sh
```

The script is **idempotent** — running it again will detect the existing entry and skip without making changes.

Verify the scheduled entry:

```bash
crontab -l
```

Watch the live log:

```bash
tail -f /var/log/iss-portal-backup.log
```

---

## Running a Manual Backup

```bash
./backup.sh
```

Expected output confirms each step and lists the files created:

```
========================================
ISS Portal - Backup
========================================

Backing up database...
✓ Database backed up: backups/db_backup_20260220_021500.sql.gz (2.3M)

Backing up configuration...
✓ Configuration backed up: backups/.env_20260220_021500

...

Backup Complete!
```

---

## Verifying a Backup

### Check the manifest

```bash
cat backups/backup_<TIMESTAMP>.manifest
```

### Test-decompress the database dump (no extraction — reads only)

```bash
gunzip -t backups/db_backup_<TIMESTAMP>.sql.gz && echo "OK — dump is intact"
```

### List the contents of a media archive

```bash
tar -tzf backups/media_<TIMESTAMP>.tar.gz | head -20
```

---

## Restore Procedure

The interactive `restore.sh` script guides you through the restore process:

```bash
./restore.sh
```

It will:

1. List all available backup timestamps found in `backups/`, sorted newest first.
2. Ask which backup set to restore.
3. Ask which components to restore (database, `.env`, media — independently).
4. Warn you and ask for explicit confirmation before overwriting anything.
5. For a database restore:
   - Stops the `web` container to release connections.
   - Drops and recreates the database.
   - Loads the backup.
   - Restarts `web` and runs `manage.py migrate --run-syncdb`.
6. Print a clear summary of what was restored.

### Important notes

- If you restore the `.env` file, you **must** restart all services afterward:
  ```bash
  docker-compose down && docker-compose up -d
  ```
- Restoring the database overwrites **all current data** — ensure you have confirmed you are restoring to the correct backup before proceeding.

---

## Disaster Recovery (Full Server Loss)

Use this procedure when the server is gone and you are starting from scratch with backup files only.

### Prerequisites
- A fresh Linux server (Ubuntu 22.04 LTS recommended)
- Docker and Docker Compose installed
- Your backup files (at minimum: `db_backup_<TIMESTAMP>.sql.gz` and `.env_<TIMESTAMP>`)

### Steps

**1. Install Docker**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

**2. Place the application files**

Copy the ISS Portal project directory to the new server (or redeploy from the deployment package):

```bash
# Example: extract a deployment package
tar -xzf iss-portal-v1.0.0.tar.gz -C /opt/
mv /opt/iss-portal-v1.0.0 /opt/iss-portal
cd /opt/iss-portal
```

**3. Place the backup files**

```bash
mkdir -p backups
cp /path/to/your/backup/db_backup_<TIMESTAMP>.sql.gz  backups/
cp /path/to/your/backup/.env_<TIMESTAMP>              backups/
cp /path/to/your/backup/media_<TIMESTAMP>.tar.gz      backups/   # if applicable
```

**4. Restore the `.env` file**

```bash
cp backups/.env_<TIMESTAMP> .env
```

Verify the critical fields are present:

```bash
grep -E "SECRET_KEY|FIELD_ENCRYPTION_KEY|DATABASE_URL" .env
```

**5. Start the database container only**

```bash
docker-compose up -d db
sleep 10  # allow Postgres to initialise
```

**6. Run the interactive restore**

```bash
./restore.sh
```

Select the database backup (and media if applicable). The script will handle dropping/recreating the DB and restoring data.

**7. Start the full stack**

```bash
docker-compose up -d
```

**8. Verify**

```bash
./status.sh
```

Navigate to `http://<server-ip>` and confirm the application loads and data is present.

**9. Re-install the cron schedule**

```bash
sudo ./setup-cron.sh
```

---

## Encryption Key Safety

> ⚠️ **Critical:** Without `FIELD_ENCRYPTION_KEY` from `.env`, encrypted records **cannot be decrypted**. A database backup without its matching key is unrecoverable for encrypted fields.

Best practices:

- Store `.env` backups (or at minimum the `FIELD_ENCRYPTION_KEY` value) in a **separate, secure location** from the database backups — e.g. a password manager, secrets vault, or separately encrypted file.
- Never commit `.env` to version control.
- If you rotate the encryption key, run `backup.sh` immediately before and after the rotation.

---

## Expanding to Off-Site Storage

The current setup keeps backups locally with 30-day retention. When you are ready to add off-site storage, the following patterns cover the most common destinations:

### Option A — rsync to a remote server

```bash
# Add to a crontab entry after backup.sh, or call from a wrapper script
rsync -avz --delete backups/ user@backup-server:/backups/iss-portal/
```

### Option B — AWS S3 (or any S3-compatible storage)

```bash
# Requires AWS CLI installed and credentials configured
aws s3 sync backups/ s3://your-bucket-name/iss-portal/
```

### Option C — Backblaze B2 via rclone

```bash
# Requires rclone configured with a "b2" remote
rclone sync backups/ b2:your-bucket/iss-portal/
```

### Wrapper script pattern

Create a `backup-and-push.sh` that calls `./backup.sh` and then performs the off-site sync. Schedule that via cron instead of `backup.sh` directly. Update `setup-cron.sh` accordingly.
