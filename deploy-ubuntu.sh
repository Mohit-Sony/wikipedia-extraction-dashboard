#!/bin/bash

# Wikipedia Dashboard - Ubuntu Server Deployment Script
# This script automates the deployment process on Ubuntu 20.04/22.04

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="wikipedia-dashboard"
APP_DIR="$HOME/apps/$APP_NAME"
BACKEND_PORT=8000
DOMAIN="${DOMAIN:-localhost}"  # Set DOMAIN environment variable before running

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Wikipedia Dashboard Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"

# Function to print status messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${YELLOW}[i]${NC} $1"
}

# Check if running on Ubuntu
if [ ! -f /etc/lsb-release ]; then
    print_error "This script is designed for Ubuntu. Exiting."
    exit 1
fi

print_status "Running on Ubuntu"

# Update system packages
print_info "Updating system packages..."
sudo apt update
sudo apt upgrade -y
print_status "System packages updated"

# Install Python 3 and pip
print_info "Installing Python 3 and pip..."
sudo apt install -y python3 python3-pip python3-venv
print_status "Python installed: $(python3 --version)"

# Install Node.js and npm
print_info "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install -y nodejs
fi
print_status "Node.js installed: $(node --version)"
print_status "npm installed: $(npm --version)"

# Install Git
print_info "Installing Git..."
sudo apt install -y git
print_status "Git installed: $(git --version)"

# Install Nginx
print_info "Installing Nginx..."
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
print_status "Nginx installed and started"

# Install PM2
print_info "Installing PM2..."
sudo npm install -g pm2
print_status "PM2 installed: $(pm2 --version)"

# Create application directory
print_info "Setting up application directory..."
mkdir -p "$APP_DIR"
print_status "Application directory created: $APP_DIR"

# Check if application files exist
if [ ! -f "$APP_DIR/backend/main.py" ]; then
    print_error "Application files not found in $APP_DIR"
    print_info "Please upload your application files to $APP_DIR first"
    print_info "You can use: scp -r /local/path/wikipedia-dashboard username@server:~/apps/"
    exit 1
fi

# Setup Backend
print_info "Setting up backend..."
cd "$APP_DIR/backend"

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create required directories
mkdir -p ../database ../logs ../wikipedia_data

print_status "Backend setup complete"

# Setup Frontend
print_info "Setting up frontend..."
cd "$APP_DIR/frontend"

# Install npm dependencies
npm install

# Build production version
npm run build

print_status "Frontend build complete"

# Create PM2 ecosystem file
print_info "Creating PM2 configuration..."
cat > "$APP_DIR/ecosystem.config.js" << EOF
module.exports = {
  apps: [
    {
      name: 'wikipedia-backend',
      cwd: '$APP_DIR/backend',
      script: 'venv/bin/python',
      args: 'main.py',
      interpreter: 'none',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '$APP_DIR/logs/backend-error.log',
      out_file: '$APP_DIR/logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    }
  ]
};
EOF

print_status "PM2 configuration created"

# Start application with PM2
print_info "Starting application with PM2..."
cd "$APP_DIR"
pm2 start ecosystem.config.js
pm2 save
print_status "Application started with PM2"

# Setup PM2 to start on boot
print_info "Configuring PM2 startup..."
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u $USER --hp $HOME
print_status "PM2 startup configured"

# Configure Nginx
print_info "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/$APP_NAME > /dev/null << EOF
# Backend API Server
upstream backend_api {
    server 127.0.0.1:$BACKEND_PORT;
}

server {
    listen 80;
    server_name $DOMAIN;

    # Frontend - Serve static files
    location / {
        root $APP_DIR/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket Support
    location /api/v1/ws {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://backend_api;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx

print_status "Nginx configured and reloaded"

# Configure Firewall
print_info "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
print_status "Firewall configured"

# Create backup script
print_info "Creating backup script..."
cat > "$HOME/backup-db.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cp ~/apps/wikipedia-dashboard/database/entities.db $BACKUP_DIR/entities_$DATE.db
# Keep only last 7 backups
ls -t $BACKUP_DIR/entities_*.db 2>/dev/null | tail -n +8 | xargs rm -f 2>/dev/null
echo "Database backed up to $BACKUP_DIR/entities_$DATE.db"
EOF

chmod +x "$HOME/backup-db.sh"
print_status "Backup script created at $HOME/backup-db.sh"

# Print summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Application URLs:${NC}"
echo -e "  Frontend:    http://$DOMAIN"
echo -e "  Backend API: http://$DOMAIN/api/v1"
echo -e "  API Docs:    http://$DOMAIN/api/v1/docs"
echo -e "  Health:      http://$DOMAIN/health"
echo ""
echo -e "${GREEN}Useful Commands:${NC}"
echo -e "  View logs:        pm2 logs wikipedia-backend"
echo -e "  Restart app:      pm2 restart wikipedia-backend"
echo -e "  Stop app:         pm2 stop wikipedia-backend"
echo -e "  App status:       pm2 status"
echo -e "  Nginx status:     sudo systemctl status nginx"
echo -e "  Backup database:  ~/backup-db.sh"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Test the application: curl http://localhost/health"
echo -e "  2. Access the dashboard in your browser"
echo -e "  3. (Optional) Setup SSL: sudo certbot --nginx -d $DOMAIN"
echo ""
