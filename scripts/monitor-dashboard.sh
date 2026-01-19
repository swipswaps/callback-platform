#!/bin/bash
# Real-time Monitoring Dashboard
# Principle: "If it can be typed, it MUST be scripted"
# UX: Live updates, color-coded status, instant visibility

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Clear screen and hide cursor
clear
tput civis

# Restore cursor on exit
trap 'tput cnorm; exit' INT TERM EXIT

# Get metrics
get_health() {
    curl -sf http://localhost:8501/health 2>/dev/null || echo '{"status":"down"}'
}

get_container_status() {
    if docker ps --format "{{.Status}}" --filter "name=callback-backend" 2>/dev/null | grep -q "Up"; then
        echo "running"
    else
        echo "stopped"
    fi
}

get_container_uptime() {
    docker ps --format "{{.Status}}" --filter "name=callback-backend" 2>/dev/null | sed 's/Up //' | awk '{print $1, $2}'
}

get_memory_usage() {
    docker stats --no-stream --format "{{.MemUsage}}" callback-backend 2>/dev/null || echo "N/A"
}

get_cpu_usage() {
    docker stats --no-stream --format "{{.CPUPerc}}" callback-backend 2>/dev/null || echo "N/A"
}

get_request_count() {
    docker logs callback-backend 2>&1 | grep -c "request_callback" || echo "0"
}

get_error_count() {
    docker logs callback-backend 2>&1 | grep -ci "error\|exception" || echo "0"
}

# Draw dashboard
draw_dashboard() {
    local health=$(get_health)
    local container_status=$(get_container_status)
    local uptime=$(get_container_uptime)
    local memory=$(get_memory_usage)
    local cpu=$(get_cpu_usage)
    local requests=$(get_request_count)
    local errors=$(get_error_count)
    
    # Clear screen
    tput cup 0 0
    
    # Header
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}🚀 CALLBACK PLATFORM - LIVE MONITORING DASHBOARD${NC}                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}Updated: $(date '+%Y-%m-%d %H:%M:%S')${NC}                                      ${CYAN}║${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Service Status
    echo -e "${MAGENTA}${BOLD}SERVICE STATUS${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if echo "$health" | grep -q '"status":"healthy"'; then
        echo -e "  ${GREEN}●${NC} Health Status:    ${GREEN}${BOLD}HEALTHY${NC}"
    else
        echo -e "  ${RED}●${NC} Health Status:    ${RED}${BOLD}DOWN${NC}"
    fi
    
    if [ "$container_status" = "running" ]; then
        echo -e "  ${GREEN}●${NC} Container:        ${GREEN}${BOLD}RUNNING${NC}"
        echo -e "  ${BLUE}●${NC} Uptime:           ${BOLD}$uptime${NC}"
    else
        echo -e "  ${RED}●${NC} Container:        ${RED}${BOLD}STOPPED${NC}"
        echo -e "  ${YELLOW}●${NC} Uptime:           ${BOLD}N/A${NC}"
    fi
    
    echo ""
    
    # Resource Usage
    echo -e "${MAGENTA}${BOLD}RESOURCE USAGE${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BLUE}●${NC} CPU:              ${BOLD}$cpu${NC}"
    echo -e "  ${BLUE}●${NC} Memory:           ${BOLD}$memory${NC}"
    echo ""
    
    # Request Metrics
    echo -e "${MAGENTA}${BOLD}REQUEST METRICS${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BLUE}●${NC} Total Requests:   ${BOLD}$requests${NC}"
    
    if [ "$errors" -gt 0 ]; then
        echo -e "  ${YELLOW}●${NC} Errors:           ${YELLOW}${BOLD}$errors${NC}"
    else
        echo -e "  ${GREEN}●${NC} Errors:           ${GREEN}${BOLD}$errors${NC}"
    fi
    echo ""
    
    # Recent Logs
    echo -e "${MAGENTA}${BOLD}RECENT LOGS (Last 5 lines)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if [ "$container_status" = "running" ]; then
        docker logs callback-backend --tail 5 2>&1 | while IFS= read -r line; do
            if echo "$line" | grep -qi "error\|exception"; then
                echo -e "  ${RED}${line:0:70}${NC}"
            elif echo "$line" | grep -qi "warning"; then
                echo -e "  ${YELLOW}${line:0:70}${NC}"
            elif echo "$line" | grep -qi "info"; then
                echo -e "  ${BLUE}${line:0:70}${NC}"
            else
                echo -e "  ${line:0:70}"
            fi
        done
    else
        echo -e "  ${YELLOW}Container not running${NC}"
    fi
    echo ""
    
    # Quick Actions
    echo -e "${MAGENTA}${BOLD}QUICK ACTIONS${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BLUE}[R]${NC} Restart   ${BLUE}[L]${NC} Full Logs   ${BLUE}[T]${NC} Run Tests   ${BLUE}[Q]${NC} Quit"
    echo ""
    
    # Footer
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Press Ctrl+C to exit${NC}"
}

# Handle user input
handle_input() {
    read -t 0.1 -n 1 key 2>/dev/null || true
    
    case "$key" in
        r|R)
            echo -e "\n${YELLOW}Restarting services...${NC}"
            docker compose restart
            sleep 2
            ;;
        l|L)
            tput cnorm
            echo -e "\n${YELLOW}Opening full logs (Ctrl+C to return)...${NC}"
            docker logs -f callback-backend
            tput civis
            ;;
        t|T)
            tput cnorm
            echo -e "\n${YELLOW}Running tests...${NC}"
            ./scripts/test-runner.sh
            echo -e "\n${GREEN}Press Enter to return to dashboard${NC}"
            read
            tput civis
            ;;
        q|Q)
            tput cnorm
            echo -e "\n${GREEN}Exiting dashboard...${NC}"
            exit 0
            ;;
    esac
}

# Main loop
main() {
    echo -e "${CYAN}${BOLD}Starting monitoring dashboard...${NC}"
    sleep 1
    
    while true; do
        draw_dashboard
        handle_input
        sleep 2
    done
}

# Run
main "$@"

