#!/bin/bash

# ==============================================================================
# HomeLab - Automated Backup Suite
# Target: Raspberry Pi 5 (NVMe) -> External 512GB HDD
# Description: Performs atomic DB snapshots and recursive filesystem rsync.
# ==============================================================================

# --- CONFIGURATION ---
USER_HOME="/home/USERNAME_REPLACEHERE"
DATE=$(date +%Y-%m-%d_%H-%M)
DEST_BASE="/mnt/external/backups"
BACKUP_PATH="$DEST_BASE/$DATE"
RETENTION_DAYS=7

# Source Paths
DOCKER_DIR="/opt/stacks"
HOME_DOCKER="$USER_HOME/docker"
SCRIPTS_DIR="$USER_HOME/scripts"
NOTES_DIR="$USER_HOME/notes"
SYNC_DIR="$USER_HOME/vault_sync"

# Vaultwarden Internal Paths
VW_DB="/opt/stacks/vaultwarden/data/db.sqlite3"
VW_KEYS="/opt/stacks/vaultwarden/data"

# --- PREP ---
mkdir -p "$BACKUP_PATH"
echo "--- Starting Home Lab Backup: $DATE ---"

# --- 1. SAFE DATABASE SNAPSHOTS ---
echo "[1/3] Initializing Database Snapshots..."

# Vaultwarden (SQLite Atomic Snapshot)
if [ -f "$VW_DB" ]; then
    sqlite3 "$VW_DB" ".backup '$BACKUP_PATH/vaultwarden_db_backup.sqlite3'"
    cp "$VW_KEYS"/rsa_key* "$BACKUP_PATH/" 2>/dev/null
    echo "    [OK] Vaultwarden snapshot saved"
else
    echo "    [ERROR] Vaultwarden DB not found at $VW_DB"
fi

# PostgreSQL (Full Global Dump)
sudo -u postgres pg_dumpall > "$BACKUP_PATH/postgres_full_dump.sql"
if [ -s "$BACKUP_PATH/postgres_full_dump.sql" ]; then
    echo "    [OK] PostgreSQL export successful"
else
    echo "    [ERROR] PostgreSQL export failed or file is empty"
fi

# --- 2. FILESYSTEM SYNCHRONIZATION ---
echo "[2/3] Syncing Filesystems via Rsync..."

# Exclude sockets and caches to prevent rsync errors
EXCLUDES=(
    "--exclude=*.sock"
    "--exclude=wayland-*"
    "--exclude=.cache"
    "--exclude=.next"
)

rsync -av --quiet "${EXCLUDES[@]}" "$DOCKER_DIR" "$BACKUP_PATH/"
rsync -av --quiet "${EXCLUDES[@]}" "$HOME_DOCKER" "$BACKUP_PATH/"
rsync -av --quiet "$SCRIPTS_DIR" "$BACKUP_PATH/"
rsync -av --quiet "$NOTES_DIR" "$BACKUP_PATH/"

echo "    [OK] Sync complete"

# --- 3. MAINTENANCE & REDUNDANCY ---
echo "[3/3] Performing Maintenance..."

# Cleanup old backups based on retention policy
find "$DEST_BASE" -type d -mtime +$RETENTION_DAYS -exec rm -rf {} +
echo "    [OK] Rotated backups (Retention: $RETENTION_DAYS days)"

# Update the Syncthing folder for off-site redundancy
if [ -f "$BACKUP_PATH/vaultwarden_db_backup.sqlite3" ]; then
    mkdir -p "$SYNC_DIR"
    cp "$BACKUP_PATH/vaultwarden_db_backup.sqlite3" "$SYNC_DIR/"
    cp "$BACKUP_PATH"/rsa_key* "$SYNC_DIR/" 2>/dev/null
    echo "    [OK] Syncthing vault updated"
fi

# --- 4. FINAL LOGGING ---
echo "--- Backup Process Complete ---"
echo "Location: ${BACKUP_PATH}"
echo "----------------------------------------------------"
ls -lh "$BACKUP_PATH"
echo "----------------------------------------------------"