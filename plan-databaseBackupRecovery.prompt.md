# Plan: Database & .env Backup / Recovery System

The project already has a working `backup.sh` that dumps PostgreSQL, copies `.env`, archives media, writes a manifest, and prunes files older than 30 days. The plan fills four specific gaps identified in research: hardcoded credentials in the backup script, no restore automation, no cron installer, and no consolidated recovery documentation.

## Steps

### 1. Fix credential sourcing in `backup.sh`

Sources `.env` at the top of the script (via a safe `set -a; source .env; set +a` block), then replaces the two hardcoded literals (`iss_user`, `iss_portal_db`) with `${POSTGRES_USER}` and `${POSTGRES_DB}`. Adds a preflight check that errors out with a clear message if `.env` is missing. Also adds exit-code checking after the `pg_dump` step so a failed dump doesn't silently create a corrupt `.gz` file.

### 2. Create `restore.sh`

An interactive restoration script placed alongside the other shell scripts at the project root. Workflow:

- Parse available backup timestamps from the `backups/` directory and present a numbered menu.
- Confirm with the user which backup set to restore (DB dump, `.env`, media — each separately toggleable).
- Stop the `web` container only (`docker-compose stop web`) so the DB stays reachable.
- For DB restore: drop all connections, `dropdb` + `createdb` (using credentials from `.env`), then pipe the `.sql.gz` back through `psql` inside the `db` container.
- For `.env` restore: copy the chosen `backups/.env_<timestamp>` back to `.env`, with a warning to restart all services afterward.
- For media restore: extract the `.tar.gz` over the `media/` directory.
- Restart `web` (`docker-compose start web`) and run `docker-compose exec web python manage.py migrate --run-syncdb` as a sanity check.
- Exit with clear success/failure messaging.

### 3. Create `setup-cron.sh`

A one-time idempotent script that:

- Checks the user is running with sufficient privileges.
- Detects the current working directory and uses it as the absolute install path (e.g. `/opt/iss-portal`).
- Checks if a crontab entry for `backup.sh` already exists (via `crontab -l | grep`) to avoid duplicates.
- Installs `0 2 * * * cd /opt/iss-portal && ./backup.sh >> /var/log/iss-portal-backup.log 2>&1` into the root crontab.
- Creates `/var/log/iss-portal-backup.log` with correct permissions if it doesn't exist.
- Prints a confirmation showing the installed entry and how to verify with `crontab -l`.

### 4. Create `BACKUP_RECOVERY.md`

Single reference document covering:

- What gets backed up (DB SQL dump, `.env`, media), where it's stored (`backups/`), and the 30-day local retention policy.
- **Setup**: run `setup-cron.sh` once after deployment.
- **Manual backup**: `./backup.sh` and what to expect in the output.
- **Verifying a backup**: how to check the manifest file and test-decompress the `.sql.gz` (`gunzip -t`).
- **Restore procedure**: run `./restore.sh` and follow the prompts; note that `.env` changes require a full `docker-compose down && docker-compose up -d`.
- **Disaster recovery** (bare metal loss): steps to reinstall Docker, clone/copy the project, place `.env`, run `docker-compose up -d db`, then `./restore.sh`.
- **Expanding to off-site storage**: placeholder section with rsync and S3 `aws s3 cp` one-liners for when that's needed later.

### 5. Update `README.md` or `DEPLOYMENT.md`

Add a short "Backup & Recovery" section that points to `BACKUP_RECOVERY.md` and mentions running `setup-cron.sh` as a post-deployment step.

---

## Verification

- Run `./backup.sh` manually and confirm files appear in `backups/` with correct names and non-zero sizes.
- Run `gunzip -t backups/db_backup_*.sql.gz` to confirm the dump is valid.
- Run `./restore.sh` on a non-production copy and confirm the DB and media restore cleanly.
- Run `setup-cron.sh` twice to confirm the second run detects the existing entry and skips it.
- Check `crontab -l` to verify the scheduled entry.

## Decisions

- Local-only retention (no off-site scripting now, placeholder docs for later).
- Failures surface via log file at `/var/log/iss-portal-backup.log`, captured by cron — no email daemon dependency.
- Credentials are sourced from `.env` at runtime so the script stays correct even if values are rotated.
