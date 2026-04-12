#!/bin/bash

# ReelSearch Transcription Service - Complete GCP Setup (All-in-One)
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/rohit204k/reelsearch-transcription-service/main/setup-service.sh | bash

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
APP_DIR="/opt/reelsearch-transcription"
VENV_DIR="$APP_DIR/.venv"
SERVICE_NAME="reelsearch-transcription"
REPO_URL="https://github.com/rohit204k/reelsearch-transcription-service.git"

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════╗"
echo "║ ReelSearch Transcription Service - GCP Setup       ║"
echo "╚════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Step 1: Update system packages
echo -e "${YELLOW}[1/8]${NC} Updating system packages..."
sudo apt update
sudo apt install -y python3-pip python3-venv ffmpeg git curl

# Step 2: Create application directory
echo -e "${YELLOW}[2/8]${NC} Creating application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Step 3: Clone repository
echo -e "${YELLOW}[3/8]${NC} Cloning repository from GitHub..."
echo "You will be prompted for your GitHub credentials (username and Personal Access Token)"
echo ""

if [ -d "$APP_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull origin main
else
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

git config --global --add safe.directory $APP_DIR

# Step 4: Create Python virtual environment
echo -e "${YELLOW}[4/8]${NC} Creating Python virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Step 5: Install Python dependencies
echo -e "${YELLOW}[5/8]${NC} Installing Python dependencies..."
echo "This may take a few minutes (downloading Whisper model)..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Step 6: Create .env file
echo -e "${YELLOW}[6/8]${NC} Setting up environment variables..."
echo ""
echo -e "${BLUE}┌─ .env FILE SETUP ─────────────────────────────────┐${NC}"
echo ""
echo "Paste your .env file contents below."
echo "Required variables:"
echo "  SUPABASE_URL=..."
echo "  SUPABASE_SERVICE_KEY=..."
echo ""
echo "Press Ctrl+D (on a new line) when done:"
echo ""
echo -e "${BLUE}└──────────────────────────────────────────────────────┘${NC}"
echo ""

ENV_CONTENT=$(cat)

cat > $APP_DIR/.env <<EOF
$ENV_CONTENT
EOF

chmod 600 $APP_DIR/.env
echo -e "${GREEN}✓${NC} .env file created at $APP_DIR/.env"

# Step 7: Create systemd service
echo -e "${YELLOW}[7/8]${NC} Creating systemd service..."

CURRENT_USER=$USER

sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<SYSTEMD_EOF
[Unit]
Description=ReelSearch Transcription Service
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$VENV_DIR/bin/python3 $APP_DIR/server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF

echo -e "${GREEN}✓${NC} Systemd service created"

# Step 8: Enable and start service
echo -e "${YELLOW}[8/8]${NC} Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

sleep 3

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║ Setup Complete! ✓                                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════╝${NC}"
echo ""

if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service is RUNNING${NC}"
else
    echo -e "${YELLOW}⚠ Service may be starting (Whisper downloads model on first run)${NC}"
fi

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "───────────────────────────────────────────────────"
echo ""
echo "1. Check service status:"
echo -e "   ${YELLOW}sudo systemctl status $SERVICE_NAME${NC}"
echo ""
echo "2. View live logs:"
echo -e "   ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo ""
echo "3. Open firewall port 3001 in GCP Console:"
echo "   - Go to: VPC Network → Firewall → Create Firewall Rule"
echo "   - Name: allow-transcription-api"
echo "   - Direction: Ingress"
echo "   - Source IPv4 ranges: 0.0.0.0/0"
echo "   - Protocols and ports: tcp:3001"
echo ""
echo "4. Get your VM's external IP:"
echo "   - Go to: Compute Engine → VM instances"
echo "   - Copy the External IP"
echo ""
echo "5. Update Vercel environment variable:"
echo -e "   ${YELLOW}VITE_TRANSCRIPTION_API_URL=http://<YOUR_EXTERNAL_IP>:3001${NC}"
echo ""
echo "6. Redeploy frontend on Vercel"
echo ""
echo -e "${BLUE}Service Details:${NC}"
echo "───────────────────────────────────────────────────"
echo "Port: 3001"
echo "Endpoint: http://localhost:3001/api/submit"
echo "Health: http://localhost:3001/api/health"
echo "Logs: journalctl -u $SERVICE_NAME -f"
echo "Config: $APP_DIR/.env"
echo ""
