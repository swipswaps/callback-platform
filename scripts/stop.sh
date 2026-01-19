#!/bin/bash
# Stop Callback Platform services
# Based on receipts-ocr reference implementation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_PID_FILE="/tmp/callback_backend.pid"
FRONTEND_PID_FILE="/tmp/callback_frontend.pid"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}━━━ Callback Platform Stop ━━━${NC}"

# Stop backend
if [ -f "$BACKEND_PID_FILE" ]; then
    BACKEND_PID=$(cat "$BACKEND_PID_FILE")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        PROC_CMD=$(ps -p $BACKEND_PID -o comm= 2>/dev/null)
        if [[ "$PROC_CMD" == "python"* ]] || [[ "$PROC_CMD" == "waitress"* ]]; then
            kill $BACKEND_PID 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Stopped backend (PID: $BACKEND_PID)"
        else
            echo -e "  ${YELLOW}⚠${NC} PID $BACKEND_PID is not backend (is: $PROC_CMD), skipping"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Backend already stopped"
    fi
    rm -f "$BACKEND_PID_FILE"
else
    echo -e "  ${YELLOW}⚠${NC} No backend PID file found"
fi

# Stop frontend
if [ -f "$FRONTEND_PID_FILE" ]; then
    FRONTEND_PID=$(cat "$FRONTEND_PID_FILE")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        PROC_CMD=$(ps -p $FRONTEND_PID -o comm= 2>/dev/null)
        if [[ "$PROC_CMD" == "python"* ]]; then
            kill $FRONTEND_PID 2>/dev/null
            echo -e "  ${GREEN}✓${NC} Stopped frontend (PID: $FRONTEND_PID)"
        else
            echo -e "  ${YELLOW}⚠${NC} PID $FRONTEND_PID is not frontend (is: $PROC_CMD), skipping"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Frontend already stopped"
    fi
    rm -f "$FRONTEND_PID_FILE"
else
    echo -e "  ${YELLOW}⚠${NC} No frontend PID file found"
fi

echo ""
echo -e "${GREEN}━━━ Cleanup Complete ━━━${NC}"
echo ""

