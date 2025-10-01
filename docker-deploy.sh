#!/bin/bash

# Docker deployment script for SFEDUNET12 Bot
set -e

echo "🐳 Starting Docker deployment of SFEDUNET12 Bot..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    print_error "Please install Docker first: https://docs.docker.com/install/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed!"
    print_error "Please install Docker Compose first"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.production" ]; then
        print_status "Copying .env.production to .env"
        cp .env.production .env
    else
        print_error ".env file not found!"
        print_error "Please create .env file with your settings"
        print_error "You can copy .env.example as a starting point"
        exit 1
    fi
fi

# Check BOT_TOKEN
if ! grep -q "BOT_TOKEN=" .env || grep -q "your_telegram_bot_token_here" .env; then
    print_error "Please set a valid BOT_TOKEN in .env file"
    exit 1
fi

# Create required directories
print_status "Creating required directories..."
mkdir -p data logs ssl

# Initialize state file if not exists
if [ ! -f "data/state.json" ]; then
    print_status "Initializing state.json..."
    echo "{}" > data/state.json
fi

# Set proper permissions
chmod 755 data logs
chmod 644 data/state.json 2>/dev/null || true

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Build and start containers
print_status "Building and starting containers..."
docker-compose up -d --build

# Wait for services to start
print_status "Waiting for services to start..."
sleep 10

# Check container status
print_status "Checking container status..."
if docker-compose ps | grep -q "Up"; then
    print_status "✅ Containers are running"

    # Show container status
    echo ""
    echo "📊 Container Status:"
    docker-compose ps

    echo ""
    echo "🌐 Access Points:"
    echo "  Admin Panel: http://localhost:5001"
    if docker-compose ps | grep nginx | grep -q "Up"; then
        echo "  Nginx Proxy: http://localhost:80"
    fi

    echo ""
    echo "📝 Useful Commands:"
    echo "  View logs: docker-compose logs -f"
    echo "  Stop: docker-compose down"
    echo "  Restart: docker-compose restart"
    echo "  Update: docker-compose pull && docker-compose up -d"

    echo ""
    echo "🔍 Health Check:"
    sleep 5
    if curl -s http://localhost:5001/health > /dev/null 2>&1; then
        print_status "✅ Health check passed"
    else
        print_warning "⚠️ Health check failed - service may still be starting"
    fi

else
    print_error "❌ Some containers failed to start"
    echo ""
    echo "📋 Container Status:"
    docker-compose ps
    echo ""
    echo "📝 Logs:"
    docker-compose logs --tail=20
    exit 1
fi

# Show final instructions
echo ""
print_status "🎉 Docker deployment completed successfully!"
echo ""
print_warning "📋 Next Steps:"
echo "  1. Open http://localhost:5001 to access admin panel"
echo "  2. Configure your bot settings"
echo "  3. Test bot functionality"
echo "  4. For production: configure SSL and domain in nginx.conf"
echo "  5. Monitor logs: docker-compose logs -f"