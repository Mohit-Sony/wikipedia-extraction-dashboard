#!/bin/bash

# Wikipedia Dashboard Deployment Script for EC2
# This script handles deployment of both backend and frontend

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Wikipedia Dashboard - EC2 Deployment${NC}"
echo -e "${BLUE}================================================${NC}"

# Check if running in correct directory
if [ ! -f "ecosystem.config.js" ]; then
    echo -e "${RED}Error: ecosystem.config.js not found. Are you in the project root?${NC}"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command_exists python3; then
    echo -e "${RED}Python3 is not installed!${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}Node.js is not installed!${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}npm is not installed!${NC}"
    exit 1
fi

if ! command_exists pm2; then
    echo -e "${YELLOW}PM2 not found. Installing PM2...${NC}"
    npm install -g pm2
fi

# Load environment variables if .env exists
if [ -f ".env" ]; then
    echo -e "${GREEN}Loading environment variables from .env${NC}"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create logs directory
mkdir -p logs

# ==========================
# BACKEND DEPLOYMENT
# ==========================
echo -e "\n${BLUE}📦 Deploying Backend...${NC}"

cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo -e "${GREEN}Installing Python dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Initialize database if needed
if [ ! -f "wikipedia.db" ]; then
    echo -e "${YELLOW}Initializing database...${NC}"
    python main.py &
    sleep 5
    pkill -f "python main.py"
fi

deactivate
cd ..

# ==========================
# FRONTEND DEPLOYMENT
# ==========================
echo -e "\n${BLUE}📦 Deploying Frontend...${NC}"

cd frontend

# Install dependencies
echo -e "${GREEN}Installing Node.js dependencies...${NC}"
npm install

# Build production bundle
echo -e "${GREEN}Building frontend for production...${NC}"
npm run build

# Install serve if not present
if ! npm list -g serve >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing serve globally...${NC}"
    npm install -g serve
fi

cd ..

# ==========================
# PM2 PROCESS MANAGEMENT
# ==========================
echo -e "\n${BLUE}🔄 Managing PM2 processes...${NC}"

# Check if processes are already running
if pm2 list | grep -q "wikipedia-backend\|wikipedia-frontend"; then
    echo -e "${YELLOW}Restarting existing PM2 processes...${NC}"
    pm2 restart ecosystem.config.js
else
    echo -e "${GREEN}Starting PM2 processes...${NC}"
    pm2 start ecosystem.config.js
fi

# Save PM2 configuration
pm2 save

# Setup PM2 startup script (run only once)
if ! pm2 startup | grep -q "PM2 resurrect"; then
    echo -e "${YELLOW}Setting up PM2 startup script...${NC}"
    pm2 startup | tail -n 1 | bash
fi

# ==========================
# DEPLOYMENT COMPLETE
# ==========================
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}================================================${NC}"

echo -e "\n${BLUE}Service Status:${NC}"
pm2 list

echo -e "\n${BLUE}Application URLs:${NC}"
echo -e "${GREEN}Backend:  http://localhost:${BACKEND_PORT:-8000}${NC}"
echo -e "${GREEN}Frontend: http://localhost:${FRONTEND_PORT:-5173}${NC}"

echo -e "\n${BLUE}Useful Commands:${NC}"
echo -e "  ${YELLOW}pm2 status${NC}          - Check process status"
echo -e "  ${YELLOW}pm2 logs${NC}            - View all logs"
echo -e "  ${YELLOW}pm2 restart all${NC}     - Restart all processes"
echo -e "  ${YELLOW}pm2 stop all${NC}        - Stop all processes"
echo -e "  ${YELLOW}pm2 monit${NC}           - Monitor processes"

echo ""
