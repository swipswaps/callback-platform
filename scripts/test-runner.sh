#!/bin/bash
# Automated Test Runner - Callback Platform
# Principle: "If it can be typed, it MUST be scripted"
# UX: Full transparency, complexity abstracted, no rabbit holes

set -euo pipefail

# Colors for UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Logging directory
LOG_DIR="/tmp/callback-tests"
mkdir -p "$LOG_DIR"

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} ${BOLD}$1${NC}"
}

log_success() {
    echo -e "${GREEN}✅${NC} ${BOLD}$1${NC}"
}

log_error() {
    echo -e "${RED}❌${NC} ${BOLD}$1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} ${BOLD}$1${NC}"
}

log_step() {
    echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}$1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))
    
    printf "\r${CYAN}[${NC}"
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "${CYAN}]${NC} ${percent}%% - ${message}"
}

wait_for_service() {
    local url=$1
    local max_wait=${2:-30}
    local waited=0
    
    log_info "Waiting for service at $url (max ${max_wait}s)..."
    
    while [ $waited -lt $max_wait ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo ""
            log_success "Service is ready!"
            return 0
        fi
        show_progress $waited $max_wait "Waiting for service..."
        sleep 1
        waited=$((waited + 1))
    done
    
    echo ""
    log_error "Service did not start within ${max_wait}s"
    return 1
}

save_logs() {
    local test_name=$1
    local log_file="$LOG_DIR/${test_name}_$(date +%Y%m%d_%H%M%S).log"
    
    log_info "Saving logs to: $log_file"
    docker logs callback-backend > "$log_file" 2>&1 || true
    echo "$log_file"
}

# Test Level 3: Service Startup
test_level_3() {
    log_step "LEVEL 3: SERVICE STARTUP TEST"
    
    log_info "Starting Docker Compose services..."
    docker compose up -d 2>&1 | tee "$LOG_DIR/docker-compose-up.log"
    
    if ! wait_for_service "http://localhost:8501/health" 30; then
        log_error "Service failed to start"
        save_logs "level3_failed"
        return 1
    fi
    
    log_info "Testing health endpoint..."
    local health_response=$(curl -s http://localhost:8501/health)
    echo "$health_response" | jq '.' 2>/dev/null || echo "$health_response"
    
    if echo "$health_response" | grep -q '"status":"healthy"'; then
        log_success "Health check PASSED"
    else
        log_error "Health check FAILED"
        save_logs "level3_health_failed"
        return 1
    fi
    
    log_info "Checking service logs for initialization..."
    docker logs callback-backend 2>&1 | tail -20
    
    local log_file=$(save_logs "level3_success")
    log_success "Level 3 COMPLETE - Logs: $log_file"
}

# Test Level 4: CAPTCHA Integration
test_level_4() {
    log_step "LEVEL 4: CAPTCHA INTEGRATION TEST"
    
    log_info "Test 1: Missing CAPTCHA token (should fail with 400)"
    local response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8501/request_callback \
        -H "Content-Type: application/json" \
        -d '{"visitor_number":"+15551234567","name":"Test User"}')
    
    local body=$(echo "$response" | head -n -1)
    local status=$(echo "$response" | tail -n 1)
    
    echo "Response: $body"
    echo "Status: $status"
    
    if [ "$status" = "400" ] && echo "$body" | grep -q "CAPTCHA"; then
        log_success "Missing CAPTCHA test PASSED"
    else
        log_error "Missing CAPTCHA test FAILED (expected 400, got $status)"
        save_logs "level4_captcha_missing_failed"
        return 1
    fi
    
    log_info "Test 2: Invalid CAPTCHA token (should fail with 400)"
    response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8501/request_callback \
        -H "Content-Type: application/json" \
        -d '{"visitor_number":"+15551234567","name":"Test User","recaptcha_token":"invalid_token"}')
    
    body=$(echo "$response" | head -n -1)
    status=$(echo "$response" | tail -n 1)
    
    echo "Response: $body"
    echo "Status: $status"
    
    if [ "$status" = "400" ] && echo "$body" | grep -q "CAPTCHA"; then
        log_success "Invalid CAPTCHA test PASSED"
    else
        log_error "Invalid CAPTCHA test FAILED (expected 400, got $status)"
        save_logs "level4_captcha_invalid_failed"
        return 1
    fi
    
    log_info "Checking logs for CAPTCHA failures..."
    docker logs callback-backend 2>&1 | grep -i captcha | tail -5
    
    local log_file=$(save_logs "level4_success")
    log_success "Level 4 COMPLETE - Logs: $log_file"
}

# Test Level 5: Phone Validation
test_level_5() {
    log_step "LEVEL 5: PHONE VALIDATION TEST"
    
    log_info "Test 1: Invalid phone number (should fail with 400)"
    local response=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8501/request_callback \
        -H "Content-Type: application/json" \
        -d '{"visitor_number":"invalid","name":"Test User","recaptcha_token":"test"}')
    
    local body=$(echo "$response" | head -n -1)
    local status=$(echo "$response" | tail -n 1)
    
    echo "Response: $body"
    echo "Status: $status"
    
    if [ "$status" = "400" ] && echo "$body" | grep -qi "phone"; then
        log_success "Invalid phone test PASSED"
    else
        log_error "Invalid phone test FAILED (expected 400, got $status)"
        save_logs "level5_phone_invalid_failed"
        return 1
    fi
    
    log_info "Checking logs for phone validation..."
    docker logs callback-backend 2>&1 | grep -i "phone" | tail -5
    
    local log_file=$(save_logs "level5_success")
    log_success "Level 5 COMPLETE - Logs: $log_file"
}

# Main execution
main() {
    log_step "🚀 AUTOMATED TEST RUNNER - CALLBACK PLATFORM"
    
    log_info "Test logs will be saved to: $LOG_DIR"
    log_info "Starting test suite..."
    
    # Run tests
    if test_level_3; then
        log_success "✅ Level 3: Service Startup - PASSED"
    else
        log_error "❌ Level 3: Service Startup - FAILED"
        exit 1
    fi
    
    if test_level_4; then
        log_success "✅ Level 4: CAPTCHA Integration - PASSED"
    else
        log_error "❌ Level 4: CAPTCHA Integration - FAILED"
        exit 1
    fi
    
    if test_level_5; then
        log_success "✅ Level 5: Phone Validation - PASSED"
    else
        log_error "❌ Level 5: Phone Validation - FAILED"
        exit 1
    fi
    
    log_step "🎉 ALL TESTS PASSED"
    log_info "Logs saved in: $LOG_DIR"
    log_info "To stop services: docker compose down"
}

# Run main
main "$@"

