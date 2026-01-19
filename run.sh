#!/bin/bash
# Master Control Script - One Command Interface
# Principle: "If it can be typed, it MUST be scripted"
# UX: Interactive menu, zero complexity, full automation

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

# Banner
show_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   🚀 CALLBACK PLATFORM - MASTER CONTROL                              ║
║                                                                       ║
║   One command to rule them all                                       ║
║   Principle: "If it can be typed, it MUST be scripted"               ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

# Show menu
show_menu() {
    echo -e "${MAGENTA}${BOLD}MAIN MENU${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    echo -e "${GREEN}${BOLD}Quick Actions:${NC}"
    echo -e "  ${CYAN}[1]${NC} ${BOLD}Quick Start${NC}        - Build, start, and test everything (recommended)"
    echo -e "  ${CYAN}[2]${NC} ${BOLD}Monitor Dashboard${NC}  - Real-time monitoring with live updates"
    echo -e "  ${CYAN}[3]${NC} ${BOLD}Run Tests${NC}          - Execute full test suite (Levels 3-5)"
    echo -e "  ${CYAN}[4]${NC} ${BOLD}Troubleshoot${NC}       - Automatic diagnosis and fixes"
    
    echo -e "\n${YELLOW}${BOLD}Service Management:${NC}"
    echo -e "  ${CYAN}[5]${NC} Start Services      - Start Docker containers"
    echo -e "  ${CYAN}[6]${NC} Stop Services       - Stop Docker containers"
    echo -e "  ${CYAN}[7]${NC} Restart Services    - Restart Docker containers"
    echo -e "  ${CYAN}[8]${NC} View Logs           - Show live container logs"
    
    echo -e "\n${BLUE}${BOLD}Development:${NC}"
    echo -e "  ${CYAN}[9]${NC} Rebuild Image       - Rebuild Docker image from scratch"
    echo -e "  ${CYAN}[10]${NC} Clean Everything    - Remove all containers, images, volumes"
    echo -e "  ${CYAN}[11]${NC} Health Check        - Quick health endpoint test"
    
    echo -e "\n${MAGENTA}${BOLD}Information:${NC}"
    echo -e "  ${CYAN}[12]${NC} Show Status         - Display current system status"
    echo -e "  ${CYAN}[13]${NC} Show Documentation  - Open README and guides"
    
    echo -e "\n${RED}${BOLD}Exit:${NC}"
    echo -e "  ${CYAN}[0]${NC} Exit\n"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Execute choice
execute_choice() {
    local choice=$1
    
    case $choice in
        1)
            echo -e "${GREEN}${BOLD}Running Quick Start...${NC}\n"
            chmod +x scripts/quick-start.sh
            ./scripts/quick-start.sh
            ;;
        2)
            echo -e "${GREEN}${BOLD}Starting Monitor Dashboard...${NC}\n"
            chmod +x scripts/monitor-dashboard.sh
            ./scripts/monitor-dashboard.sh
            ;;
        3)
            echo -e "${GREEN}${BOLD}Running Test Suite...${NC}\n"
            chmod +x scripts/test-runner.sh
            ./scripts/test-runner.sh
            ;;
        4)
            echo -e "${GREEN}${BOLD}Running Troubleshooter...${NC}\n"
            chmod +x scripts/troubleshoot.sh
            ./scripts/troubleshoot.sh
            ;;
        5)
            echo -e "${GREEN}${BOLD}Starting Services...${NC}\n"
            docker compose up -d
            echo -e "\n${GREEN}✅ Services started${NC}"
            ;;
        6)
            echo -e "${YELLOW}${BOLD}Stopping Services...${NC}\n"
            docker compose down
            echo -e "\n${GREEN}✅ Services stopped${NC}"
            ;;
        7)
            echo -e "${YELLOW}${BOLD}Restarting Services...${NC}\n"
            docker compose restart
            echo -e "\n${GREEN}✅ Services restarted${NC}"
            ;;
        8)
            echo -e "${GREEN}${BOLD}Showing Live Logs (Ctrl+C to exit)...${NC}\n"
            docker logs -f callback-backend
            ;;
        9)
            echo -e "${YELLOW}${BOLD}Rebuilding Image...${NC}\n"
            docker compose build --no-cache
            echo -e "\n${GREEN}✅ Image rebuilt${NC}"
            ;;
        10)
            echo -e "${RED}${BOLD}⚠ WARNING: This will remove all containers, images, and volumes${NC}"
            read -p "Are you sure? (yes/no): " confirm
            if [ "$confirm" = "yes" ]; then
                docker compose down -v
                docker system prune -af
                echo -e "\n${GREEN}✅ Everything cleaned${NC}"
            else
                echo -e "\n${YELLOW}Cancelled${NC}"
            fi
            ;;
        11)
            echo -e "${GREEN}${BOLD}Running Health Check...${NC}\n"
            if curl -sf http://localhost:8501/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Health check PASSED${NC}"
                curl -s http://localhost:8501/health | jq '.' 2>/dev/null || curl -s http://localhost:8501/health
            else
                echo -e "${RED}❌ Health check FAILED${NC}"
                echo -e "${YELLOW}Run option [4] to troubleshoot${NC}"
            fi
            ;;
        12)
            echo -e "${GREEN}${BOLD}System Status:${NC}\n"
            echo -e "${CYAN}Docker:${NC}"
            docker --version
            echo ""
            echo -e "${CYAN}Containers:${NC}"
            docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo ""
            echo -e "${CYAN}Images:${NC}"
            docker images | grep callback || echo "No callback images found"
            ;;
        13)
            echo -e "${GREEN}${BOLD}Documentation:${NC}\n"
            echo -e "${CYAN}Available documentation:${NC}"
            echo -e "  • README.md - Main documentation"
            echo -e "  • TESTING_GUIDE.md - Testing instructions"
            echo -e "  • PROJECT_STATUS.md - Current status"
            echo -e "  • FINAL_SUMMARY.md - Complete overview"
            echo ""
            read -p "Open README.md? (y/n): " open_readme
            if [ "$open_readme" = "y" ]; then
                less README.md || cat README.md
            fi
            ;;
        0)
            echo -e "\n${GREEN}${BOLD}Goodbye! 👋${NC}\n"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${NC}"
            ;;
    esac
}

# Main loop
main() {
    # Make scripts executable
    chmod +x scripts/*.sh 2>/dev/null || true
    
    while true; do
        show_banner
        show_menu
        
        read -p "$(echo -e ${CYAN}${BOLD}Enter your choice: ${NC})" choice
        echo ""
        
        execute_choice "$choice"
        
        echo ""
        read -p "$(echo -e ${CYAN}Press Enter to continue...${NC})"
    done
}

# Run
main "$@"

