# Ubuntu Cloud Server Deployment Guide

This guide will help you deploy the Wikipedia Extraction Dashboard on an Ubuntu cloud server via SSH.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Install Dependencies](#install-dependencies)
4. [Deploy Application](#deploy-application)
5. [Configure Web Server (Nginx)](#configure-web-server-nginx)
6. [Process Management](#process-management)
7. [Security & Firewall](#security--firewall)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You Need
- Ubuntu 20.04 or 22.04 cloud server
- SSH access with sudo privileges
- Domain name (optional, but recommended)
- At least 2GB RAM and 20GB storage

### Local Machine Requirements
- SSH client installed
- Git installed (to clone repository)

---

## Initial Server Setup

### 1. Connect to Your Server

```bash
# Connect via SSH
ssh username@your-server-ip

# Example:
ssh ubuntu@192.168.1.100
```

### 2. Update System Packages

```bash
# Update package list
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y
```

### 3. Create Application User (Optional but Recommended)

```bash
# Create a dedicated user for the application
sudo adduser wikiapp

# Add user to sudo group
sudo usermod -aG sudo wikiapp

# Switch to the new user
su - wikiapp
```

---

## Install Dependencies

### 1. Install Python 3.10+

```bash
# Check Python version
python3 --version

# If Python 3.10+ is not installed:
sudo apt install python3 python3-pip python3-venv -y

# Verify installation
python3 --version
pip3 --version
```

### 2. Install Node.js and npm

```bash
# Install Node.js 18.x (LTS)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version
npm --version
```

### 3. Install Git

```bash
sudo apt install git -y
git --version
```

### 4. Install Nginx (Web Server)

```bash
sudo apt install nginx -y
sudo systemctl status nginx
```

### 5. Install PM2 (Process Manager)

```bash
# Install PM2 globally
sudo npm install -g pm2

# Verify installation
pm2 --version
```

---

## Deploy Application

### 1. Clone Repository

```bash
# Navigate to home directory
cd ~

# Create application directory
mkdir -p apps
cd apps

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/wikipedia-dashboard.git

# Or upload files using SCP from your local machine:
# scp -r /path/to/local/wikipedia-dashboard username@server-ip:~/apps/
```

### 2. Setup Backend

```bash
# Navigate to project directory
cd ~/apps/wikipedia-dashboard/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create required directories
mkdir -p ../database ../logs ../wikipedia_data

# Test backend
python main.py
# Press Ctrl+C after verifying it starts successfully
```

### 3. Setup Frontend

```bash
# Navigate to frontend directory
cd ~/apps/wikipedia-dashboard/frontend

# Install dependencies
npm install

# Build production version
npm run build

# The build output will be in the 'dist' folder
```

---

## Configure Web Server (Nginx)

### 1. Create Nginx Configuration

```bash
# Create nginx configuration file
sudo nano /etc/nginx/sites-available/wikipedia-dashboard
```

### 2. Add Configuration

Paste the following configuration:

```nginx
# Backend API Server
upstream backend_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain or server IP

    # Frontend - Serve static files
    location / {
        root /home/wikiapp/apps/wikipedia-dashboard/frontend/dist;
        try_files $uri $uri/ /index.html;
        
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
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket Support
    location /api/v1/ws {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://backend_api;
    }
}
```

### 3. Enable Configuration

```bash
# Create symbolic link to enable site
sudo ln -s /etc/nginx/sites-available/wikipedia-dashboard /etc/nginx/sites-enabled/

# Remove default nginx site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## Process Management

### Option 1: Using PM2 (Recommended)

#### 1. Create PM2 Ecosystem File

```bash
# Navigate to project root
cd ~/apps/wikipedia-dashboard

# Create PM2 configuration
nano ecosystem.config.js
```

Add the following content:

```javascript
module.exports = {
  apps: [
    {
      name: 'wikipedia-backend',
      cwd: '/home/wikiapp/apps/wikipedia-dashboard/backend',
      script: 'venv/bin/python',
      args: 'main.py',
      interpreter: 'none',
      env: {
        PYTHONUNBUFFERED: '1'
      },
      error_file: '/home/wikiapp/apps/wikipedia-dashboard/logs/backend-error.log',
      out_file: '/home/wikiapp/apps/wikipedia-dashboard/logs/backend-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s'
    }
  ]
};
```

#### 2. Start Application with PM2

```bash
# Start the application
pm2 start ecosystem.config.js

# Check status
pm2 status

# View logs
pm2 logs wikipedia-backend

# Save PM2 configuration
pm2 save

# Setup PM2 to start on system boot
pm2 startup
# Follow the instructions provided by the command
```

#### 3. PM2 Management Commands

```bash
# Stop application
pm2 stop wikipedia-backend

# Restart application
pm2 restart wikipedia-backend

# Delete from PM2
pm2 delete wikipedia-backend

# Monitor in real-time
pm2 monit
```

### Option 2: Using Systemd Service

#### 1. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/wikipedia-backend.service
```

Add the following content:

```ini
[Unit]
Description=Wikipedia Extraction Dashboard Backend
After=network.target

[Service]
Type=simple
User=wikiapp
WorkingDirectory=/home/wikiapp/apps/wikipedia-dashboard/backend
Environment="PATH=/home/wikiapp/apps/wikipedia-dashboard/backend/venv/bin"
ExecStart=/home/wikiapp/apps/wikipedia-dashboard/backend/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable wikipedia-backend

# Start the service
sudo systemctl start wikipedia-backend

# Check status
sudo systemctl status wikipedia-backend

# View logs
sudo journalctl -u wikipedia-backend -f
```

---

## Security & Firewall

### 1. Configure UFW Firewall

```bash
# Enable UFW
sudo ufw enable

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS (if using SSL)
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### 2. Setup SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### 3. Update Frontend API URL

```bash
# Edit frontend environment file
cd ~/apps/wikipedia-dashboard/frontend
nano .env
```

Update the API URL:
```
VITE_API_URL=http://your-domain.com/api/v1
# Or for HTTPS:
# VITE_API_URL=https://your-domain.com/api/v1
```

Rebuild frontend:
```bash
npm run build
```

---

## Updating the Application

### Pull Latest Changes

```bash
# Navigate to project directory
cd ~/apps/wikipedia-dashboard

# Pull latest code
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Update frontend
cd ../frontend
npm install
npm run build

# Restart services
pm2 restart wikipedia-backend
# Or if using systemd:
# sudo systemctl restart wikipedia-backend
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check logs
pm2 logs wikipedia-backend
# Or for systemd:
# sudo journalctl -u wikipedia-backend -n 50

# Common issues:
# 1. Port 8000 already in use
sudo lsof -i :8000
sudo kill -9 <PID>

# 2. Permission issues
sudo chown -R wikiapp:wikiapp ~/apps/wikipedia-dashboard
chmod -R 755 ~/apps/wikipedia-dashboard

# 3. Missing dependencies
cd ~/apps/wikipedia-dashboard/backend
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend Not Loading

```bash
# Check nginx status
sudo systemctl status nginx

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# Verify build exists
ls -la ~/apps/wikipedia-dashboard/frontend/dist

# Rebuild if necessary
cd ~/apps/wikipedia-dashboard/frontend
npm run build
```

### Database Issues

```bash
# Check database file permissions
ls -la ~/apps/wikipedia-dashboard/database/

# Reset database (WARNING: deletes all data)
rm ~/apps/wikipedia-dashboard/database/entities.db
# Restart backend to recreate
pm2 restart wikipedia-backend
```

### WebSocket Connection Issues

```bash
# Check nginx configuration
sudo nginx -t

# Ensure WebSocket proxy settings are correct
sudo nano /etc/nginx/sites-available/wikipedia-dashboard

# Reload nginx
sudo systemctl reload nginx
```

### Check System Resources

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Check running processes
ps aux | grep python
```

---

## Monitoring & Maintenance

### Setup Log Rotation

```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/wikipedia-dashboard
```

Add:
```
/home/wikiapp/apps/wikipedia-dashboard/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 wikiapp wikiapp
    sharedscripts
}
```

### Backup Database

```bash
# Create backup script
nano ~/backup-db.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cp ~/apps/wikipedia-dashboard/database/entities.db $BACKUP_DIR/entities_$DATE.db
# Keep only last 7 backups
ls -t $BACKUP_DIR/entities_*.db | tail -n +8 | xargs rm -f
```

Make executable and add to crontab:
```bash
chmod +x ~/backup-db.sh

# Add to crontab (daily at 2 AM)
crontab -e
# Add line:
# 0 2 * * * /home/wikiapp/backup-db.sh
```

---

## Quick Reference Commands

```bash
# Start application
pm2 start ecosystem.config.js

# Stop application
pm2 stop wikipedia-backend

# Restart application
pm2 restart wikipedia-backend

# View logs
pm2 logs wikipedia-backend

# Check nginx status
sudo systemctl status nginx

# Reload nginx
sudo systemctl reload nginx

# Check application status
curl http://localhost:8000/health

# Monitor system
htop  # Install with: sudo apt install htop
```

---

## Access Your Application

Once everything is set up:

- **Frontend**: `http://your-domain.com` or `http://your-server-ip`
- **Backend API**: `http://your-domain.com/api/v1`
- **API Docs**: `http://your-domain.com/api/v1/docs`
- **Health Check**: `http://your-domain.com/health`

---

## Support & Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/)
- [Ubuntu Server Guide](https://ubuntu.com/server/docs)

Your Wikipedia Extraction Dashboard is now deployed! 🚀
