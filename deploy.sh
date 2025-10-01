#!/bin/bash

# Deployment script for SFEDUNET12 Bot
set -e

echo "🚀 Starting deployment of SFEDUNET12 Bot..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Please don't run this script as root"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/sfedunet-bot"
SERVICE_USER="botuser"
VENV_DIR="$PROJECT_DIR/venv"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    print_error "Please create .env.production with your production settings"
    exit 1
fi

# Check if BOT_TOKEN is set
if ! grep -q "BOT_TOKEN=" .env.production; then
    print_error "BOT_TOKEN not found in .env.production"
    exit 1
fi

# Create project directory
print_status "Creating project directory..."
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR

# Copy files
print_status "Copying application files..."
cp -r . $PROJECT_DIR/
cd $PROJECT_DIR

# Copy production environment
cp .env.production .env

# Create virtual environment
print_status "Setting up Python virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install dependencies
print_status "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
print_status "Creating required directories..."
mkdir -p data logs
chmod 755 data logs

# Initialize state file if not exists
if [ ! -f "data/state.json" ]; then
    echo "{}" > data/state.json
fi

# Create systemd service files
print_status "Creating systemd service files..."

# Bot service
sudo tee /etc/systemd/system/sfedunet-bot.service > /dev/null <<EOF
[Unit]
Description=SFEDUNET12 Telegram Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR/data $PROJECT_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

# Admin service
sudo tee /etc/systemd/system/sfedunet-admin.service > /dev/null <<EOF
[Unit]
Description=SFEDUNET12 Admin Panel
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$VENV_DIR/bin/python admin_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR/data $PROJECT_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable services
print_status "Enabling systemd services..."
sudo systemctl daemon-reload
sudo systemctl enable sfedunet-bot.service
sudo systemctl enable sfedunet-admin.service

# Start services
print_status "Starting services..."
sudo systemctl start sfedunet-bot.service
sudo systemctl start sfedunet-admin.service

# Check service status
sleep 3
print_status "Checking service status..."

if sudo systemctl is-active --quiet sfedunet-bot.service; then
    print_status "✅ Bot service is running"
else
    print_error "❌ Bot service failed to start"
    sudo systemctl status sfedunet-bot.service
fi

if sudo systemctl is-active --quiet sfedunet-admin.service; then
    print_status "✅ Admin service is running"
else
    print_error "❌ Admin service failed to start"
    sudo systemctl status sfedunet-admin.service
fi

# Setup log rotation
print_status "Setting up log rotation..."
sudo tee /etc/logrotate.d/sfedunet-bot > /dev/null <<EOF
$PROJECT_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF

# Create backup script
print_status "Creating backup script..."
tee $PROJECT_DIR/backup.sh > /dev/null <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/sfedunet-bot-backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/sfedunet-bot/data/state.json $BACKUP_DIR/state_$DATE.json

# Keep only last 30 backups
find $BACKUP_DIR -name "state_*.json" -type f -mtime +30 -delete

echo "Backup created: $BACKUP_DIR/state_$DATE.json"
EOF

chmod +x $PROJECT_DIR/backup.sh

# Setup cron for backups
print_status "Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * $PROJECT_DIR/backup.sh") | crontab -

print_status "🎉 Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
echo "  Bot: $(sudo systemctl is-active sfedunet-bot.service)"
echo "  Admin: $(sudo systemctl is-active sfedunet-admin.service)"
echo ""
echo "🌐 Access Points:"
echo "  Admin Panel: http://localhost:5001"
echo "  Logs: journalctl -u sfedunet-bot.service -f"
echo "  Data: $PROJECT_DIR/data/"
echo ""
echo "🔧 Management Commands:"
echo "  sudo systemctl status sfedunet-bot.service"
echo "  sudo systemctl restart sfedunet-bot.service"
echo "  sudo systemctl logs -f sfedunet-bot.service"
echo "  $PROJECT_DIR/backup.sh"
echo ""
print_warning "Don't forget to configure your firewall and set up SSL if needed!"