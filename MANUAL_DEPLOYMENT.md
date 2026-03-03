# Manual EC2 Deployment Guide - Step by Step

Safer, manual deployment approach for Wikipedia Dashboard on EC2.

## 📋 Prerequisites on EC2

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Install PM2
sudo npm install -g pm2 serve

# Install Git
sudo apt install git -y

# Verify installations
python3 --version
node --version
npm --version
pm2 --version
```

---

## 🚀 Step-by-Step Deployment

### 1. Clone Repository

```bash
cd ~
git clone https://github.com/yourusername/wikipedia-dashboard.git
cd wikipedia-dashboard
```

### 2. Setup Environment Variables

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

**Minimum required:**
```env
BACKEND_PORT=8000
FRONTEND_PORT=5173
ENVIRONMENT=production
```

### 3. Deploy Backend

```bash
cd ~/wikipedia-dashboard/backend

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Deactivate
deactivate

cd ..
```

### 4. Deploy Frontend

```bash
cd ~/wikipedia-dashboard/frontend

# Install dependencies
npm install

# Build production bundle
npm run build

cd ..
```

### 5. Create Logs Directory

```bash
mkdir -p ~/wikipedia-dashboard/logs
```

### 6. Start Services with PM2

```bash
cd ~/wikipedia-dashboard

# Start both services
pm2 start ecosystem.config.js

# Save PM2 config
pm2 save

# Setup PM2 to start on boot
pm2 startup
# Copy and run the command it outputs (will be something like):
# sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu
```

### 7. Verify Everything is Running

```bash
# Check PM2 status
pm2 status

# View logs
pm2 logs

# Test backend
curl http://localhost:8000

# Test frontend
curl http://localhost:5173
```

---

## 🔄 Update Deployment (When Code Changes)

### Manual Update Process:

```bash
cd ~/wikipedia-dashboard

# Pull latest code
git pull origin master

# Update backend dependencies (if requirements.txt changed)
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# Update frontend
cd frontend
npm install
npm run build
cd ..

# Restart services
pm2 restart all

# Check status
pm2 status
```

### Or Use the Deploy Script:

**Only after you've verified everything works manually:**

```bash
cd ~/wikipedia-dashboard
chmod +x deploy.sh
./deploy.sh
```

---

## 🐛 Troubleshooting

### Check if Services are Running

```bash
pm2 status
pm2 logs
```

### Stop Everything

```bash
pm2 stop all
```

### Start Everything

```bash
pm2 start ecosystem.config.js
```

### Check Ports

```bash
sudo lsof -i :8000  # Backend
sudo lsof -i :5173  # Frontend
```

### View Real-time Logs

```bash
# All logs
pm2 logs

# Only backend
pm2 logs wikipedia-backend

# Only frontend
pm2 logs wikipedia-frontend
```

### Restart Individual Service

```bash
pm2 restart wikipedia-backend
# or
pm2 restart wikipedia-frontend
```

---

## ✅ Verification Checklist

After deployment, verify:

- [ ] `pm2 status` shows both services running
- [ ] Backend accessible: `curl http://localhost:8000`
- [ ] Frontend accessible: `curl http://localhost:5173`
- [ ] From browser: `http://YOUR_EC2_IP:8000` (backend)
- [ ] From browser: `http://YOUR_EC2_IP:5173` (frontend)
- [ ] API docs: `http://YOUR_EC2_IP:8000/docs`

---

## 🔐 Security Checklist

- [ ] EC2 security group configured correctly
- [ ] `.env` file created with proper values
- [ ] `credentials.json` uploaded (if using Google Drive)
- [ ] Never commit `.env`, `credentials.json`, or `.pem` files to Git

---

## 📝 Useful PM2 Commands

```bash
pm2 list              # List all processes
pm2 status            # Same as list
pm2 logs              # View all logs
pm2 monit             # Real-time monitoring
pm2 restart all       # Restart all services
pm2 stop all          # Stop all services
pm2 delete all        # Remove all processes
pm2 save              # Save current process list
pm2 resurrect         # Restore saved processes
```

---

**Recommendation:** Follow this manual process first. Once everything works, then you can use the automated `deploy.sh` script or GitHub Actions.
