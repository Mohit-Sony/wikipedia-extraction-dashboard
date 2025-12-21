#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Wikipedia Dashboard...${NC}"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}Shutdown complete${NC}"
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}Starting Backend...${NC}"
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 2

# Start Frontend
echo -e "${GREEN}Starting Frontend...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}Backend running on: http://localhost:8000${NC}"
echo -e "${GREEN}Frontend running on: http://localhost:5173${NC}"
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Press Ctrl+C to stop both services${NC}"

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
