#!/bin/bash
# ISS Portal - Cron Scheduler Setup
# Installs a daily 2 AM backup cron entry for the current install directory.
# Safe to run multiple times — will not add a duplicate entry.

set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/iss-portal-backup.log"
CRON_ENTRY="0 2 * * * cd $INSTALL_DIR && ./backup.sh >> $LOG_FILE 2>&1"
CRON_MARKER="backup.sh"

echo "========================================"
echo "ISS Portal - Backup Cron Setup"
echo "========================================"
echo ""
echo "Install directory : $INSTALL_DIR"
echo "Log file          : $LOG_FILE"
echo "Schedule          : daily at 2:00 AM"
echo ""

# ---------------------------------------------------------------------------
# Check privileges
# ---------------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (or with sudo) so the cron"
    echo "       entry is installed in the system/root crontab."
    echo ""
    echo "Usage:  sudo ./setup-cron.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# Verify backup.sh exists and is executable
# ---------------------------------------------------------------------------
if [ ! -f "$INSTALL_DIR/backup.sh" ]; then
    echo "ERROR: backup.sh not found in $INSTALL_DIR"
    exit 1
fi
chmod +x "$INSTALL_DIR/backup.sh"

# ---------------------------------------------------------------------------
# Create log file if absent
# ---------------------------------------------------------------------------
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
    chmod 640 "$LOG_FILE"
    echo "✓ Created log file: $LOG_FILE"
else
    echo "✓ Log file already exists: $LOG_FILE"
fi

# ---------------------------------------------------------------------------
# Check for duplicate cron entry
# ---------------------------------------------------------------------------
EXISTING=$(crontab -l 2>/dev/null | grep "$CRON_MARKER" || true)

if [ -n "$EXISTING" ]; then
    echo ""
    echo "A backup cron entry already exists:"
    echo "  $EXISTING"
    echo ""
    echo "No changes made. Run 'crontab -l' to review all entries."
    exit 0
fi

# ---------------------------------------------------------------------------
# Install cron entry
# ---------------------------------------------------------------------------
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -

echo "✓ Cron entry installed:"
echo "  $CRON_ENTRY"
echo ""
echo "Verify with:  crontab -l"
echo "View logs:    tail -f $LOG_FILE"
echo ""
echo "To remove the entry later:"
echo "  crontab -l | grep -v 'backup.sh' | crontab -"
echo ""
