#!/bin/bash

# Wikipedia Dashboard Deployment Script for EC2 - SAFE VERSION
# This script handles deployment of both backend and frontend

# DON'T use set -e - we handle errors manually
set -u  # Exit on undefined variables

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Wikipedia Dashboard - EC2 Deployment (Safe)${NC}"
echo -e "${BLUE}================================================${NC}"

# Track if we encountered any errors
ERRORS=0

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to handle errors
handle_error() {
    echo -e "${RED}❌ Error: $1${NC}"
    ERRORS=$((ERRORS + 1))
}

# Check if running in correct directory
if [ ! -f "ecosystem.config.js" ]; then
    echo -e "${RED}Error: ecosystem.config.js not found. Are you in the project root?${NC}"
    exit 1
fi

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists python3; then
    handle_error "Python3 is not installed!"
    exit 1
fi

if ! command_exists node; then
    handle_error "Node.js is not installed!"
    exit 1
fi

if ! command_exists npm; then
    handle_error "npm is not installed!"
    exit 1
fi

if ! command_exists pm2; then
    echo -e "${YELLOW}PM2 not found. Installing PM2...${NC}"
    if sudo npm install -g pm2; then
        echo -e "${GREEN}✓ PM2 installed${NC}"
    else
        handle_error "Failed to install PM2. Try: sudo npm install -g pm2"
        exit 1
    fi
fi

# Load environment variables safely using dotenv approach
if [ -f ".env" ]; then
    echo -e "${GREEN}Loading environment variables from .env${NC}"
    set -a
    source .env 2>/dev/null || echo -e "${YELLOW}Warning: Could not source .env file${NC}"
    set +a
fi

# Create logs directory
mkdir -p logs

# ==========================
# BACKEND DEPLOYMENT
# ==========================
echo -e "\n${BLUE}📦 Deploying Backend...${NC}"

if [ ! -d "backend" ]; then
    handle_error "backend/ directory not found"
    exit 1
fi

cd backend

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    handle_error "requirements.txt not found in backend/"
    cd ..
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    if python3 -m venv venv; then
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    else
        handle_error "Failed to create virtual environment"
        cd ..
        exit 1
    fi
fi

# Activate virtual environment and install dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
source venv/bin/activate

# Upgrade pip (don't fail if this doesn't work)
pip install --upgrade pip 2>/dev/null || echo -e "${YELLOW}Warning: Could not upgrade pip${NC}"

# Install requirements
if pip install -r requirements.txt; then
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    handle_error "Failed to install Python dependencies"
    deactivate
    cd ..
    exit 1
fi

# REMOVED DANGEROUS DATABASE INITIALIZATION
# Database will be initialized automatically when backend starts via PM2

deactivate
cd ..

# ==========================
# FRONTEND DEPLOYMENT
# ==========================
echo -e "\n${BLUE}📦 Deploying Frontend...${NC}"

if [ ! -d "frontend" ]; then
    handle_error "frontend/ directory not found"
    exit 1
fi

cd frontend

# Check if package.json exists
if [ ! -f "package.json" ]; then
    handle_error "package.json not found in frontend/"
    cd ..
    exit 1
fi

# Install dependencies
echo -e "${GREEN}Installing Node.js dependencies...${NC}"
if npm install; then
    echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
else
    handle_error "Failed to install Node.js dependencies"
    cd ..
    exit 1
fi

# Build production bundle
echo -e "${GREEN}Building frontend for production...${NC}"
if npm run build; then
    echo -e "${GREEN}✓ Frontend build successful${NC}"
else
    handle_error "Frontend build failed"
    cd ..
    exit 1
fi

# Install serve if not present
if ! command_exists serve; then
    echo -e "${YELLOW}Installing serve globally...${NC}"
    if sudo npm install -g serve; then
        echo -e "${GREEN}✓ serve installed${NC}"
    else
        echo -e "${YELLOW}Warning: Could not install serve globally. PM2 will handle serving.${NC}"
    fi
fi

cd ..

# ==========================
# PM2 PROCESS MANAGEMENT
# ==========================
echo -e "\n${BLUE}🔄 Managing PM2 processes...${NC}"

# Check if processes are already running
if pm2 list | grep -q "wikipedia-backend\|wikipedia-frontend"; then
    echo -e "${YELLOW}Reloading existing PM2 processes...${NC}"
    if pm2 reload ecosystem.config.js; then
        echo -e "${GREEN}✓ PM2 processes reloaded${NC}"
    else
        echo -e "${YELLOW}Reload failed, trying restart...${NC}"
        pm2 restart ecosystem.config.js
    fi
else
    echo -e "${GREEN}Starting PM2 processes...${NC}"
    if pm2 start ecosystem.config.js; then
        echo -e "${GREEN}✓ PM2 processes started${NC}"
    else
        handle_error "Failed to start PM2 processes"
        exit 1
    fi
fi

# Save PM2 configuration
pm2 save

# Setup PM2 startup script (only if not already configured)
echo -e "${YELLOW}Checking PM2 startup configuration...${NC}"
if ! systemctl is-enabled pm2-$(whoami) >/dev/null 2>&1; then
    echo -e "${YELLOW}Setting up PM2 startup script...${NC}"
    pm2 startup systemd -u $(whoami) --hp $(eval echo ~$(whoami)) | grep "sudo" | bash || \
        echo -e "${YELLOW}Note: Run 'pm2 startup' and follow instructions to enable auto-start${NC}"
else
    echo -e "${GREEN}✓ PM2 startup already configured${NC}"
fi

# ==========================
# VERIFY DEPLOYMENT
# ==========================
echo -e "\n${BLUE}🔍 Verifying deployment...${NC}"

sleep 3  # Give services time to start

# Check if processes are running
if pm2 list | grep -q "online.*wikipedia-backend"; then
    echo -e "${GREEN}✓ Backend is running${NC}"
else
    handle_error "Backend is not running"
fi

if pm2 list | grep -q "online.*wikipedia-frontend"; then
    echo -e "${GREEN}✓ Frontend is running${NC}"
else
    handle_error "Frontend is not running"
fi

# ==========================
# DEPLOYMENT COMPLETE
# ==========================
if [ $ERRORS -eq 0 ]; then
    echo -e "\n${GREEN}================================================${NC}"
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo -e "${GREEN}================================================${NC}"
else
    echo -e "\n${YELLOW}================================================${NC}"
    echo -e "${YELLOW}⚠️  Deployment completed with $ERRORS warning(s)${NC}"
    echo -e "${YELLOW}================================================${NC}"
fi

echo -e "\n${BLUE}Service Status:${NC}"
pm2 list

echo -e "\n${BLUE}Application URLs:${NC}"
echo -e "${GREEN}Backend:  http://localhost:${BACKEND_PORT:-8000}${NC}"
echo -e "${GREEN}Frontend: http://localhost:${FRONTEND_PORT:-5173}${NC}"

echo -e "\n${BLUE}View Logs:${NC}"
echo -e "  ${YELLOW}pm2 logs${NC}                    - View all logs"
echo -e "  ${YELLOW}pm2 logs wikipedia-backend${NC}  - View backend logs"
echo -e "  ${YELLOW}pm2 logs wikipedia-frontend${NC} - View frontend logs"

echo -e "\n${BLUE}Useful Commands:${NC}"
echo -e "  ${YELLOW}pm2 status${NC}          - Check process status"
echo -e "  ${YELLOW}pm2 restart all${NC}     - Restart all processes"
echo -e "  ${YELLOW}pm2 stop all${NC}        - Stop all processes"
echo -e "  ${YELLOW}pm2 monit${NC}           - Monitor processes"

echo ""

exit $ERRORS
