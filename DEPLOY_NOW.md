# Deploy to Your Server NOW

**Server IP**: `101.53.140.132`  
**User**: `root`

## Step 1: Upload Files to Server

From your **local machine** (in the project directory), run:

```bash
# Navigate to your project directory
cd "/Users/mohitsoni/work/The Indian History/ai pipieline/Wikiextraction v2/Extraction dashboard/wikipedia-dashboard"

# Upload entire project to server
scp -r . root@101.53.140.132:/root/wikipedia-dashboard
```

**Note**: This will upload all files to `/root/wikipedia-dashboard` on your server.

## Step 2: SSH into Server

```bash
ssh root@101.53.140.132
```

## Step 3: Run Automated Deployment

Once connected to the server, run:

```bash
# Navigate to project directory
cd /root/wikipedia-dashboard

# Make deployment script executable
chmod +x deploy-ubuntu.sh

# Run deployment (this will take 5-10 minutes)
./deploy-ubuntu.sh
```

The script will automatically:
- ✅ Install Python 3, Node.js, Nginx, PM2
- ✅ Setup backend with dependencies
- ✅ Build frontend
- ✅ Configure Nginx
- ✅ Start the application
- ✅ Setup firewall

## Step 4: Access Your Dashboard

After deployment completes, open in your browser:

- **Dashboard**: `http://101.53.140.132`
- **API Docs**: `http://101.53.140.132/api/v1/docs`
- **Health Check**: `http://101.53.140.132/health`

## Troubleshooting

### If upload fails:
```bash
# Make sure you're in the project directory first
cd "/Users/mohitsoni/work/The Indian History/ai pipieline/Wikiextraction v2/Extraction dashboard/wikipedia-dashboard"

# Try uploading again
scp -r . root@101.53.140.132:/root/wikipedia-dashboard
```

### If deployment script fails:
```bash
# Check what went wrong
cat /root/wikipedia-dashboard/logs/backend-error.log

# Or view PM2 logs
pm2 logs
```

### Check if services are running:
```bash
# Check PM2 status
pm2 status

# Check Nginx status
systemctl status nginx

# Check backend health
curl http://localhost:8000/health
```

## Quick Commands Reference

```bash
# View application logs
pm2 logs wikipedia-backend

# Restart application
pm2 restart wikipedia-backend

# Stop application
pm2 stop wikipedia-backend

# Restart Nginx
systemctl restart nginx
```

---

**That's it! Your dashboard should be live at http://101.53.140.132 🚀**
