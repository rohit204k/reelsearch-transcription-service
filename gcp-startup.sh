#!/bin/bash
# Google Cloud Platform Startup Script
# This script runs automatically when the VM boots
# Add this to VM metadata key: startup-script

set -e

# Log everything
exec > >(tee /var/log/reelsearch-startup.log)
exec 2>&1

echo "=== ReelSearch Auto-Startup $(date) ==="

# Wait for network
sleep 10

# Configuration
REPO_URL="https://github.com/rohit204k/reelsearch.git"
APP_DIR="/opt/reelsearch"
DEPLOY_SCRIPT="$APP_DIR/deploy.sh"

# Check if this is first boot
if [ ! -f "/opt/reelsearch-initialized" ]; then
    echo "First boot detected - running full deployment..."

    # Install dependencies
    apt update
    apt install -y python3-pip ffmpeg git curl

    # Clone repo
    if [ ! -d "$APP_DIR" ]; then
        git clone $REPO_URL $APP_DIR
    fi

    # Make deploy script executable
    chmod +x $APP_DIR/deploy.sh

    # Run deployment
    bash $APP_DIR/deploy.sh

    # Mark as initialized
    touch /opt/reelsearch-initialized

    echo "✓ Initial setup complete!"
else
    echo "Subsequent boot - restarting service..."

    # Update code
    cd $APP_DIR
    git fetch origin
    git reset --hard origin/main

    # Update dependencies (quick check)
    pip3 install -r requirements-dev.txt --no-cache-dir

    # Restart service
    systemctl restart reelsearch-transcription

    echo "✓ Service restarted!"
fi

echo "=== Startup complete $(date) ==="
