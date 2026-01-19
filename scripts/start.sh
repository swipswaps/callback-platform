#!/bin/bash
# Start Callback Platform with port conflict resolution
# Based on receipts-ocr and claude reference implementations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_PID_FILE="/tmp/callback_backend.pid"
FRONTEND_PID_FILE="/tmp/callback_frontend.pid"
BACKEND_LOG="/tmp/backend.log"
FRONTEND_LOG="/tmp/frontend.log"

# Default ports
BACKEND_PORT=8501
FRONTEND_PORT=3000

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}━━━ Callback Platform Start ━━━${NC}"
echo -e "  Backend port:  ${GREEN}$BACKEND_PORT${NC}"
echo -e "  Frontend port: ${GREEN}$FRONTEND_PORT${NC}"
echo ""

# Check if port is in use (returns 0 if in use, 1 if free)
check_port() {
    local port=$1
    # Use ss to check if port is listening (doesn't require sudo)
    if ss -tln | grep -q ":${port} "; then
        return 0  # Port in use
    fi
    return 1  # Port free
}

# Kill process on port using fuser
kill_port_process() {
    local port=$1

    echo -e "  ${YELLOW}⚠${NC} Port $port in use"
    echo -e "  ${YELLOW}⚠${NC} Attempting to kill process on port $port..."

    # Use fuser to kill the process (may require sudo)
    if fuser -k ${port}/tcp 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Killed process on port $port"
        sleep 2
    elif sudo fuser -k ${port}/tcp 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Killed process on port $port (required sudo)"
        sleep 2
    else
        echo -e "  ${RED}✗${NC} Failed to kill process on port $port"
        echo -e "  ${RED}✗${NC} Please stop manually and try again"
        exit 1
    fi
}

# 1. Check and clear backend port
echo -n "  Checking backend port $BACKEND_PORT... "
if check_port $BACKEND_PORT; then
    echo -e "${YELLOW}in use${NC}"
    kill_port_process $BACKEND_PORT
else
    echo -e "${GREEN}available${NC}"
fi

# 2. Check and clear frontend port
echo -n "  Checking frontend port $FRONTEND_PORT... "
if check_port $FRONTEND_PORT; then
    echo -e "${YELLOW}in use${NC}"
    kill_port_process $FRONTEND_PORT
else
    echo -e "${GREEN}available${NC}"
fi

echo ""
echo -e "${GREEN}━━━ Starting Services ━━━${NC}"

# 3. Start backend
echo -e "  ${BLUE}Starting backend...${NC}"
cd "$PROJECT_DIR/backend"
python app.py 2>&1 | tee $BACKEND_LOG &
BACKEND_PID=$!
echo $BACKEND_PID > "$BACKEND_PID_FILE"

# Wait for backend to start
sleep 3
if curl -s --max-time 2 http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Backend running (PID: $BACKEND_PID)"
else
    echo -e "  ${RED}✗${NC} Backend failed to start. Check $BACKEND_LOG"
    tail -20 $BACKEND_LOG
    exit 1
fi

# 4. Start frontend
echo -e "  ${BLUE}Starting frontend...${NC}"
cd "$PROJECT_DIR/frontend"
python -m http.server $FRONTEND_PORT 2>&1 | tee $FRONTEND_LOG &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$FRONTEND_PID_FILE"

sleep 2
if curl -s --max-time 2 http://localhost:$FRONTEND_PORT/ > /dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Frontend running (PID: $FRONTEND_PID)"
else
    echo -e "  ${RED}✗${NC} Frontend failed to start. Check $FRONTEND_LOG"
    exit 1
fi

# 5. Show URLs
LOCAL_IP=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^172\.' | head -1)
echo ""
echo -e "${GREEN}━━━ Services Running ━━━${NC}"
echo -e "  Frontend:  ${BLUE}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  Network:   ${BLUE}http://$LOCAL_IP:$FRONTEND_PORT${NC}"
echo -e "  Backend:   ${BLUE}http://localhost:$BACKEND_PORT${NC}"
echo ""
echo -e "  Logs:"
echo -e "    Backend:  ${BLUE}$BACKEND_LOG${NC}"
echo -e "    Frontend: ${BLUE}$FRONTEND_LOG${NC}"
echo ""
echo -e "  Stop with: ${BLUE}./scripts/stop.sh${NC}"
echo ""

