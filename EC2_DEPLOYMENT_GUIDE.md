# EC2 Deployment Guide - Wikipedia Dashboard

Complete guide for deploying the Wikipedia Dashboard to AWS EC2 with GitHub Actions automation.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [EC2 Instance Setup](#ec2-instance-setup)
3. [GitHub Secrets Configuration](#github-secrets-configuration)
4. [First-Time Deployment](#first-time-deployment)
5. [Automatic Deployments](#automatic-deployments)
6. [Troubleshooting](#troubleshooting)
7. [Useful Commands](#useful-commands)

---

## 🔧 Prerequisites

Before starting, ensure you have:

- ✅ AWS Account with EC2 access
- ✅ GitHub repository for this project
- ✅ SSH key pair for EC2 access
- ✅ Domain name (optional, for custom domain)

---

## 🖥️ EC2 Instance Setup

### Step 1: Launch EC2 Instance

1. **Launch Ubuntu Server 22.04 LTS**
   - Instance type: `t2.medium` or larger (min 2GB RAM)
   - Storage: 20GB minimum
   - Security group rules:
     ```
     SSH (22)         - Your IP
     HTTP (80)        - 0.0.0.0/0
     HTTPS (443)      - 0.0.0.0/0
     Custom (8000)    - 0.0.0.0/0  (Backend API)
     Custom (5173)    - 0.0.0.0/0  (Frontend)
     ```

2. **Download your SSH key pair** (e.g., `mykey.pem`)

### Step 2: Connect to EC2

```bash
ssh -i /path/to/mykey.pem ubuntu@your-ec2-ip
```

### Step 3: Install Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js and npm (using NodeSource)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install PM2 globally
sudo npm install -g pm2

# Install Git
sudo apt install git -y

# Verify installations
python3 --version
node --version
npm --version
pm2 --version
```

### Step 4: Setup GitHub SSH Access (For Private Repos)

```bash
# Generate SSH key on EC2
ssh-keygen -t ed25519 -C "your-email@example.com"

# Copy the public key
cat ~/.ssh/id_ed25519.pub

# Add this key to your GitHub account:
# GitHub → Settings → SSH and GPG keys → New SSH key
```

### Step 5: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone git@github.com:yourusername/wikipedia-dashboard.git
# OR for HTTPS:
# git clone https://github.com/yourusername/wikipedia-dashboard.git

cd wikipedia-dashboard
```

### Step 6: Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit with your values
nano .env
```

**Required environment variables:**
```env
BACKEND_PORT=8000
FRONTEND_PORT=5173
DATABASE_URL=sqlite:///./wikipedia.db
ENVIRONMENT=production
SECRET_KEY=your-secure-secret-key
```

### Step 7: Setup Google Drive Credentials (If needed)

```bash
# Copy your credentials.json to the EC2 instance
# From your local machine:
scp -i /path/to/mykey.pem credentials.json ubuntu@your-ec2-ip:~/wikipedia-dashboard/

# Authenticate Google Drive (run once)
cd ~/wikipedia-dashboard/backend
python3 -c "from services.file_service import FileService; FileService()"
```

### Step 8: Run Initial Deployment

```bash
cd ~/wikipedia-dashboard
chmod +x deploy.sh
./deploy.sh
```

---

## 🔐 GitHub Secrets Configuration

### Step 1: Add EC2 SSH Key to GitHub

1. Go to your GitHub repository
2. Navigate to: **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"**

Add the following secrets:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `EC2_HOST` | EC2 instance public IP or domain | `54.123.45.67` |
| `EC2_USER` | SSH username | `ubuntu` |
| `EC2_SSH_KEY` | Private SSH key content | Contents of `.pem` file |
| `EC2_SSH_PORT` | SSH port (optional) | `22` |
| `BACKEND_PORT` | Backend port | `8000` |
| `FRONTEND_PORT` | Frontend port | `5173` |

### Step 2: Get SSH Key Content

```bash
# On your local machine
cat /path/to/mykey.pem
```

Copy the **entire content** including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`

---

## 🚀 First-Time Deployment

After setting up EC2 and GitHub secrets:

1. **Push to master branch:**
   ```bash
   git add .
   git commit -m "Setup EC2 deployment"
   git push origin master
   ```

2. **GitHub Actions will automatically:**
   - Connect to your EC2 instance
   - Pull the latest code
   - Install dependencies
   - Build the frontend
   - Start services with PM2

3. **Monitor deployment:**
   - Go to GitHub → Actions tab
   - Watch the deployment workflow

4. **Access your application:**
   - Backend: `http://your-ec2-ip:8000`
   - Frontend: `http://your-ec2-ip:5173`
   - API Docs: `http://your-ec2-ip:8000/docs`

---

## 🔄 Automatic Deployments

Every push to the `master` branch triggers automatic deployment:

```bash
# Make changes to your code
git add .
git commit -m "Your changes"
git push origin master

# GitHub Actions automatically deploys to EC2
```

You can also trigger manual deployment:
- Go to GitHub → Actions
- Select "Deploy to EC2" workflow
- Click "Run workflow"

---

## 🐛 Troubleshooting

### Check Service Status

```bash
# SSH into EC2
ssh -i /path/to/mykey.pem ubuntu@your-ec2-ip

# Check PM2 processes
pm2 status

# View logs
pm2 logs

# View specific service logs
pm2 logs wikipedia-backend
pm2 logs wikipedia-frontend
```

### Common Issues

#### 1. **Services Not Starting**
```bash
# Check if ports are already in use
sudo lsof -i :8000
sudo lsof -i :5173

# Kill conflicting processes
sudo kill -9 <PID>

# Restart PM2
pm2 restart all
```

#### 2. **Database Issues**
```bash
cd ~/wikipedia-dashboard/backend
source venv/bin/activate
python main.py  # Check for errors
```

#### 3. **Frontend Build Fails**
```bash
cd ~/wikipedia-dashboard/frontend
npm install
npm run build
```

#### 4. **GitHub Actions SSH Connection Fails**
- Verify `EC2_SSH_KEY` secret is correct
- Check EC2 security group allows SSH from GitHub Actions IPs
- Ensure EC2 instance is running

#### 5. **Environment Variables Not Loaded**
```bash
# Check .env file exists
cat ~/wikipedia-dashboard/.env

# Restart services
pm2 restart all
```

### View Application Logs

```bash
# Backend logs
tail -f ~/wikipedia-dashboard/logs/backend-out.log
tail -f ~/wikipedia-dashboard/logs/backend-error.log

# Frontend logs
tail -f ~/wikipedia-dashboard/logs/frontend-out.log
tail -f ~/wikipedia-dashboard/logs/frontend-error.log

# System logs
tail -f ~/wikipedia-dashboard/logs/dashboard.log
```

---

## 📝 Useful Commands

### PM2 Management

```bash
# List all processes
pm2 list

# Restart all services
pm2 restart all

# Stop all services
pm2 stop all

# Start all services
pm2 start ecosystem.config.js

# Monitor in real-time
pm2 monit

# View detailed info
pm2 describe wikipedia-backend

# Delete all processes
pm2 delete all

# Save current process list
pm2 save

# Resurrect saved processes
pm2 resurrect
```

### System Maintenance

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Check disk space
df -h

# Check memory usage
free -h

# Check CPU usage
top

# Restart EC2 instance
sudo reboot
```

### Git Operations

```bash
cd ~/wikipedia-dashboard

# Pull latest changes manually
git pull origin master

# Check current branch
git branch

# View recent commits
git log --oneline -10

# Reset to specific commit
git reset --hard <commit-hash>
```

---

## 🔒 Security Best Practices

1. **Never commit sensitive files:**
   - Add to `.gitignore`:
     ```
     .env
     credentials.json
     token.json
     *.pem
     *.key
     ```

2. **Use environment variables** for all secrets

3. **Restrict EC2 security group:**
   - Only allow SSH from your IP
   - Consider using AWS Systems Manager Session Manager instead

4. **Enable AWS CloudWatch** for monitoring

5. **Setup SSL/TLS** using Nginx + Let's Encrypt:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   sudo certbot --nginx -d yourdomain.com
   ```

---

## 🌐 Optional: Custom Domain Setup

### With Nginx Reverse Proxy

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/wikipedia-dashboard
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/wikipedia-dashboard /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com
```

---

## 📊 Monitoring

### Setup PM2 Web Monitoring

```bash
# Install PM2 web interface
pm2 install pm2-server-monit

# View monitoring URL
pm2 monit
```

### CloudWatch Logs (Optional)

```bash
# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb
```

---

## 🎉 Deployment Complete!

Your Wikipedia Dashboard is now:
- ✅ Running on EC2
- ✅ Auto-deploying via GitHub Actions
- ✅ Managed with PM2
- ✅ Configured with environment secrets

**Access your application:**
- Frontend: `http://your-ec2-ip:5173`
- Backend API: `http://your-ec2-ip:8000`
- API Documentation: `http://your-ec2-ip:8000/docs`

---

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review application logs
3. Check GitHub Actions workflow logs
4. Review EC2 system logs

---

**Last Updated:** 2026-03-03
