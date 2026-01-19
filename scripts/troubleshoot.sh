#!/bin/bash
# Troubleshooting Script - Full Transparency
# Principle: "If it can be typed, it MUST be scripted"
# UX: Automatic diagnosis, clear explanations, actionable fixes

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

log_info() { echo -e "${BLUE}ℹ${NC} ${BOLD}$1${NC}"; }
log_success() { echo -e "${GREEN}✅${NC} ${BOLD}$1${NC}"; }
log_error() { echo -e "${RED}❌${NC} ${BOLD}$1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠${NC} ${BOLD}$1${NC}"; }
log_section() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Banner
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🔍 TROUBLESHOOTING ASSISTANT                           ║
║                                                           ║
║   Automatic diagnosis with full transparency             ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# Check 1: Docker Status
log_section "1. DOCKER STATUS"

if docker info > /dev/null 2>&1; then
    log_success "Docker daemon is running"
    docker --version
else
    log_error "Docker daemon is not running"
    echo -e "${YELLOW}Fix:${NC} Start Docker Desktop or run: ${BOLD}sudo systemctl start docker${NC}"
    exit 1
fi

# Check 2: Container Status
log_section "2. CONTAINER STATUS"

if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "callback-backend"; then
    log_success "Backend container is running"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "callback-backend"
else
    log_warning "Backend container is not running"
    
    if docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -q "callback-backend"; then
        log_info "Container exists but is stopped"
        echo -e "${YELLOW}Fix:${NC} Run: ${BOLD}docker compose up -d${NC}"
    else
        log_info "Container does not exist"
        echo -e "${YELLOW}Fix:${NC} Run: ${BOLD}./scripts/quick-start.sh${NC}"
    fi
fi

# Check 3: Port Availability
log_section "3. PORT AVAILABILITY"

if lsof -i :8501 > /dev/null 2>&1 || netstat -tuln 2>/dev/null | grep -q ":8501"; then
    log_success "Port 8501 is in use (backend should be listening)"
    lsof -i :8501 2>/dev/null || netstat -tuln 2>/dev/null | grep ":8501"
else
    log_warning "Port 8501 is not in use"
    echo -e "${YELLOW}This means:${NC} Backend is not listening on port 8501"
    echo -e "${YELLOW}Fix:${NC} Check container logs: ${BOLD}docker logs callback-backend${NC}"
fi

# Check 4: Health Endpoint
log_section "4. HEALTH ENDPOINT"

if curl -sf http://localhost:8501/health > /dev/null 2>&1; then
    log_success "Health endpoint is responding"
    curl -s http://localhost:8501/health | jq '.' 2>/dev/null || curl -s http://localhost:8501/health
else
    log_error "Health endpoint is not responding"
    echo -e "${YELLOW}Possible causes:${NC}"
    echo -e "  ${BLUE}•${NC} Backend crashed on startup"
    echo -e "  ${BLUE}•${NC} Port mapping issue"
    echo -e "  ${BLUE}•${NC} Flask app failed to initialize"
    echo -e "${YELLOW}Fix:${NC} Check logs below ↓"
fi

# Check 5: Recent Logs
log_section "5. RECENT LOGS (Last 30 lines)"

if docker ps -a --format "{{.Names}}" | grep -q "callback-backend"; then
    docker logs callback-backend --tail 30 2>&1
else
    log_warning "No container logs available (container doesn't exist)"
fi

# Check 6: Error Detection
log_section "6. ERROR DETECTION"

if docker ps -a --format "{{.Names}}" | grep -q "callback-backend"; then
    local errors=$(docker logs callback-backend 2>&1 | grep -i "error\|exception\|failed\|traceback" | tail -10)
    
    if [ -n "$errors" ]; then
        log_error "Found errors in logs:"
        echo "$errors"
        
        # Common error patterns
        if echo "$errors" | grep -qi "port.*already.*use"; then
            echo -e "\n${YELLOW}Diagnosis:${NC} Port 8501 is already in use by another process"
            echo -e "${YELLOW}Fix:${NC} Stop the other process or change the port in docker-compose.yml"
        fi
        
        if echo "$errors" | grep -qi "module.*not.*found\|importerror"; then
            echo -e "\n${YELLOW}Diagnosis:${NC} Missing Python dependencies"
            echo -e "${YELLOW}Fix:${NC} Rebuild image: ${BOLD}docker compose build --no-cache${NC}"
        fi
        
        if echo "$errors" | grep -qi "permission.*denied"; then
            echo -e "\n${YELLOW}Diagnosis:${NC} Permission issue"
            echo -e "${YELLOW}Fix:${NC} Check file permissions or run with appropriate privileges"
        fi
    else
        log_success "No obvious errors found in logs"
    fi
else
    log_warning "Cannot check for errors (container doesn't exist)"
fi

# Check 7: Environment Configuration
log_section "7. ENVIRONMENT CONFIGURATION"

if [ -f ".env" ]; then
    log_success ".env file exists"
    log_info "Configured variables:"
    grep -v "^#" .env | grep -v "^$" | sed 's/=.*/=***/' || echo "  (empty or all comments)"
else
    log_warning ".env file not found (using defaults)"
    echo -e "${YELLOW}Note:${NC} For production, copy .env.example to .env and configure"
fi

# Check 8: Disk Space
log_section "8. DISK SPACE"

local disk_usage=$(df -h . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -lt 90 ]; then
    log_success "Sufficient disk space (${disk_usage}% used)"
else
    log_warning "Low disk space (${disk_usage}% used)"
    echo -e "${YELLOW}Fix:${NC} Free up disk space or clean Docker: ${BOLD}docker system prune${NC}"
fi

# Summary and Recommendations
log_section "9. SUMMARY & RECOMMENDATIONS"

echo -e "${BOLD}Quick Fixes:${NC}"
echo -e "  ${BLUE}1.${NC} Restart everything:     ${BOLD}docker compose restart${NC}"
echo -e "  ${BLUE}2.${NC} Rebuild from scratch:   ${BOLD}docker compose down && docker compose build --no-cache && docker compose up -d${NC}"
echo -e "  ${BLUE}3.${NC} View live logs:         ${BOLD}docker logs -f callback-backend${NC}"
echo -e "  ${BLUE}4.${NC} Check all tests:        ${BOLD}./scripts/test-runner.sh${NC}"

echo -e "\n${BOLD}Get Help:${NC}"
echo -e "  ${BLUE}•${NC} Full logs saved to:     ${BOLD}/tmp/callback-tests/${NC}"
echo -e "  ${BLUE}•${NC} Documentation:          ${BOLD}README.md${NC}"
echo -e "  ${BLUE}•${NC} Testing guide:          ${BOLD}TESTING_GUIDE.md${NC}"

echo -e "\n${GREEN}${BOLD}Troubleshooting complete!${NC}"

