# Quick Start: Deploy to Ubuntu Server

This is a simplified guide to get your Wikipedia Dashboard running on Ubuntu quickly.

## Prerequisites
- Ubuntu 20.04 or 22.04 server
- SSH access with sudo privileges
- At least 2GB RAM

## Step 1: Upload Files to Server

From your **local machine**, upload the project to your server:

```bash
# Option A: Using SCP
scp -r /path/to/wikipedia-dashboard username@your-server-ip:~/apps/

# Option B: Using Git (if you have a repository)
# SSH into server first, then:
ssh username@your-server-ip
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/yourusername/wikipedia-dashboard.git
```

## Step 2: Run Automated Deployment Script

SSH into your server and run the deployment script:

```bash
# Connect to server
ssh username@your-server-ip

# Navigate to project directory
cd ~/apps/wikipedia-dashboard

# Make script executable (if not already)
chmod +x deploy-ubuntu.sh

# Run deployment script
./deploy-ubuntu.sh
```

The script will automatically:
- ✅ Install Python, Node.js, Nginx, PM2
- ✅ Setup backend with virtual environment
- ✅ Build frontend for production
- ✅ Configure Nginx as reverse proxy
- ✅ Start application with PM2
- ✅ Configure firewall
- ✅ Setup automatic startup on reboot

## Step 3: Access Your Application

Once deployment completes, access your dashboard:

- **Frontend**: `http://your-server-ip`
- **API Docs**: `http://your-server-ip/api/v1/docs`
- **Health Check**: `http://your-server-ip/health`

## Manual Deployment (Alternative)

If you prefer manual control, follow the detailed guide in `UBUNTU_DEPLOYMENT_GUIDE.md`.

### Quick Manual Steps:

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install dependencies
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx git
sudo npm install -g pm2

# 3. Setup backend
cd ~/apps/wikipedia-dashboard/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p ../database ../logs ../wikipedia_data

# 4. Setup frontend
cd ../frontend
npm install
npm run build

# 5. Start with PM2
cd ..
pm2 start ecosystem.config.js
pm2 save
pm2 startup

# 6. Configure Nginx (see UBUNTU_DEPLOYMENT_GUIDE.md for config)
sudo nano /etc/nginx/sites-available/wikipedia-dashboard
sudo ln -s /etc/nginx/sites-available/wikipedia-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Common Commands

```bash
# View application logs
pm2 logs wikipedia-backend

# Restart application
pm2 restart wikipedia-backend

# Stop application
pm2 stop wikipedia-backend

# Check status
pm2 status

# View Nginx logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

## Troubleshooting

### Application won't start
```bash
# Check logs
pm2 logs wikipedia-backend

# Ensure port 8000 is free
sudo lsof -i :8000
```

### Can't access from browser
```bash
# Check firewall
sudo ufw status

# Allow HTTP traffic
sudo ufw allow 80/tcp

# Check Nginx status
sudo systemctl status nginx
```

### Database errors
```bash
# Check permissions
ls -la ~/apps/wikipedia-dashboard/database/

# Fix permissions
chmod 755 ~/apps/wikipedia-dashboard/database
```

## Optional: Setup SSL (HTTPS)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate (replace with your domain)
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is configured automatically
```

## Need More Help?

See the comprehensive guide: `UBUNTU_DEPLOYMENT_GUIDE.md`

---

**That's it! Your Wikipedia Dashboard should now be running on Ubuntu! 🚀**
