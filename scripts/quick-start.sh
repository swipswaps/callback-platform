#!/bin/bash
# Quick Start Script - One Command to Rule Them All
# Principle: "If it can be typed, it MUST be scripted"
# UX: Zero configuration, full transparency, instant feedback

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
    echo -e "${CYAN}"
    cat << "EOF"
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🚀 CALLBACK PLATFORM - QUICK START                     ║
║                                                           ║
║   One command to build, start, and test everything       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

log_info() { echo -e "${BLUE}ℹ${NC} ${BOLD}$1${NC}"; }
log_success() { echo -e "${GREEN}✅${NC} ${BOLD}$1${NC}"; }
log_error() { echo -e "${RED}❌${NC} ${BOLD}$1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠${NC} ${BOLD}$1${NC}"; }
log_step() {
    echo -e "\n${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${MAGENTA}${BOLD}STEP $1: $2${NC}"
    echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Check prerequisites
check_prerequisites() {
    log_step 1 "Checking Prerequisites"
    
    local missing=0
    
    if command -v docker &> /dev/null; then
        log_success "Docker installed: $(docker --version)"
    else
        log_error "Docker not found - please install Docker"
        missing=1
    fi
    
    if command -v docker compose &> /dev/null || command -v docker-compose &> /dev/null; then
        log_success "Docker Compose installed"
    else
        log_error "Docker Compose not found - please install Docker Compose"
        missing=1
    fi
    
    if command -v curl &> /dev/null; then
        log_success "curl installed"
    else
        log_error "curl not found - please install curl"
        missing=1
    fi
    
    if command -v jq &> /dev/null; then
        log_success "jq installed"
    else
        log_warning "jq not found - JSON output will be raw (optional)"
    fi
    
    if [ $missing -eq 1 ]; then
        log_error "Missing required tools - please install them first"
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

# Build Docker image
build_image() {
    log_step 2 "Building Docker Image"
    
    log_info "Building backend image (this may take 1-2 minutes)..."
    if docker compose build 2>&1 | tee /tmp/docker-build.log; then
        log_success "Docker image built successfully"
    else
        log_error "Docker build failed - check /tmp/docker-build.log"
        exit 1
    fi
}

# Start services
start_services() {
    log_step 3 "Starting Services"
    
    log_info "Starting Docker Compose services..."
    docker compose up -d
    
    log_info "Waiting for backend to be ready..."
    local waited=0
    while [ $waited -lt 30 ]; do
        if curl -sf http://localhost:8501/health > /dev/null 2>&1; then
            log_success "Backend is ready!"
            return 0
        fi
        printf "."
        sleep 1
        waited=$((waited + 1))
    done
    
    echo ""
    log_error "Backend did not start within 30 seconds"
    log_info "Showing recent logs:"
    docker logs callback-backend --tail 20
    exit 1
}

# Run health check
health_check() {
    log_step 4 "Running Health Check"
    
    log_info "Testing health endpoint..."
    local response=$(curl -s http://localhost:8501/health)
    
    if command -v jq &> /dev/null; then
        echo "$response" | jq '.'
    else
        echo "$response"
    fi
    
    if echo "$response" | grep -q '"status":"healthy"'; then
        log_success "Health check PASSED"
    else
        log_error "Health check FAILED"
        exit 1
    fi
}

# Run quick tests
quick_tests() {
    log_step 5 "Running Quick Tests"
    
    log_info "Test 1: Invalid phone number (should reject)"
    local response=$(curl -s -X POST http://localhost:8501/request_callback \
        -H "Content-Type: application/json" \
        -d '{"visitor_number":"invalid","name":"Test"}')
    
    if echo "$response" | grep -qi "phone"; then
        log_success "Phone validation working ✓"
    else
        log_warning "Phone validation response: $response"
    fi
    
    log_info "Test 2: Missing CAPTCHA (should reject)"
    response=$(curl -s -X POST http://localhost:8501/request_callback \
        -H "Content-Type: application/json" \
        -d '{"visitor_number":"+15551234567","name":"Test"}')
    
    if echo "$response" | grep -qi "captcha"; then
        log_success "CAPTCHA validation working ✓"
    else
        log_warning "CAPTCHA validation response: $response"
    fi
    
    log_success "Quick tests complete!"
}

# Show next steps
show_next_steps() {
    log_step 6 "Next Steps"
    
    echo -e "${GREEN}${BOLD}🎉 Platform is running!${NC}\n"
    
    echo -e "${CYAN}${BOLD}Access Points:${NC}"
    echo -e "  ${BLUE}•${NC} Backend API:  ${BOLD}http://localhost:8501${NC}"
    echo -e "  ${BLUE}•${NC} Health Check: ${BOLD}http://localhost:8501/health${NC}"
    echo -e "  ${BLUE}•${NC} Frontend:     ${BOLD}Open frontend/index.html in browser${NC}"
    
    echo -e "\n${CYAN}${BOLD}Useful Commands:${NC}"
    echo -e "  ${BLUE}•${NC} View logs:        ${BOLD}docker logs -f callback-backend${NC}"
    echo -e "  ${BLUE}•${NC} Run full tests:   ${BOLD}./scripts/test-runner.sh${NC}"
    echo -e "  ${BLUE}•${NC} Stop services:    ${BOLD}docker compose down${NC}"
    echo -e "  ${BLUE}•${NC} Restart services: ${BOLD}docker compose restart${NC}"
    
    echo -e "\n${CYAN}${BOLD}Test the API:${NC}"
    echo -e "  ${BOLD}curl http://localhost:8501/health${NC}"
    
    echo -e "\n${CYAN}${BOLD}Logs Location:${NC}"
    echo -e "  ${BLUE}•${NC} Build logs:  ${BOLD}/tmp/docker-build.log${NC}"
    echo -e "  ${BLUE}•${NC} Test logs:   ${BOLD}/tmp/callback-tests/${NC}"
    
    echo -e "\n${YELLOW}${BOLD}⚠ Production Setup:${NC}"
    echo -e "  ${BLUE}1.${NC} Get reCAPTCHA keys: ${BOLD}https://www.google.com/recaptcha/admin${NC}"
    echo -e "  ${BLUE}2.${NC} Get Twilio credentials: ${BOLD}https://www.twilio.com/console${NC}"
    echo -e "  ${BLUE}3.${NC} Copy .env.example to .env and configure"
    echo -e "  ${BLUE}4.${NC} Restart: ${BOLD}docker compose restart${NC}"
    
    echo ""
}

# Main execution
main() {
    show_banner
    
    check_prerequisites
    build_image
    start_services
    health_check
    quick_tests
    show_next_steps
    
    log_success "Quick start complete! 🚀"
}

# Run
main "$@"

