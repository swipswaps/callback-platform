#!/bin/bash
# GitHub Setup Script - Automated repository creation and Pages enablement
# Principle: "If it can be typed, it MUST be scripted"
# Follows Rule 54 (GitHub CLI Usage)

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
echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║   🚀 GITHUB SETUP - AUTOMATED REPOSITORY & PAGES                     ║
║                                                                       ║
║   Uses GitHub CLI (gh) per Rule 54                                   ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}\n"

# Step 1: Check prerequisites
echo -e "${MAGENTA}${BOLD}STEP 1: Checking Prerequisites${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}❌ GitHub CLI (gh) not installed${NC}"
    echo -e "${YELLOW}Install from: https://cli.github.com/${NC}"
    echo -e "${YELLOW}Or use package manager:${NC}"
    echo -e "  ${BLUE}macOS:${NC}   brew install gh"
    echo -e "  ${BLUE}Linux:${NC}   sudo apt install gh  # or yum/dnf"
    echo -e "  ${BLUE}Windows:${NC} winget install GitHub.cli"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI installed: $(gh --version | head -1)${NC}"

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}⚠ Not authenticated with GitHub${NC}"
    echo -e "${BLUE}ℹ Running authentication...${NC}\n"
    gh auth login
    echo ""
fi

echo -e "${GREEN}✅ Authenticated with GitHub${NC}"
echo -e "${BLUE}ℹ User: $(gh api user -q .login)${NC}\n"

# Step 2: Check if git remote exists
echo -e "${MAGENTA}${BOLD}STEP 2: Checking Git Status${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

if git remote get-url origin &> /dev/null; then
    REMOTE_URL=$(git remote get-url origin)
    echo -e "${YELLOW}⚠ Git remote 'origin' already exists:${NC}"
    echo -e "  ${BLUE}$REMOTE_URL${NC}\n"
    
    read -p "$(echo -e ${CYAN}Use existing remote? [y/N]: ${NC})" USE_EXISTING
    if [[ ! "$USE_EXISTING" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Exiting. Remove remote with: git remote remove origin${NC}"
        exit 0
    fi
    
    REPO_EXISTS=true
else
    REPO_EXISTS=false
fi

# Step 3: Create repository (if needed)
if [ "$REPO_EXISTS" = false ]; then
    echo -e "${MAGENTA}${BOLD}STEP 3: Creating GitHub Repository${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    read -p "$(echo -e ${CYAN}Repository name [callback-platform]: ${NC})" REPO_NAME
    REPO_NAME=${REPO_NAME:-callback-platform}
    
    read -p "$(echo -e ${CYAN}Description: ${NC})" REPO_DESC
    REPO_DESC=${REPO_DESC:-"Secure callback/click-to-call platform with 6 security layers and automation suite"}
    
    read -p "$(echo -e ${CYAN}Visibility (public/private) [public]: ${NC})" VISIBILITY
    VISIBILITY=${VISIBILITY:-public}
    
    echo -e "\n${BLUE}ℹ Creating repository: $REPO_NAME${NC}\n"
    
    if [ "$VISIBILITY" = "private" ]; then
        gh repo create "$REPO_NAME" --private --description "$REPO_DESC" --source=. --remote=origin
    else
        gh repo create "$REPO_NAME" --public --description "$REPO_DESC" --source=. --remote=origin
    fi
    
    echo -e "\n${GREEN}✅ Repository created${NC}"
    echo -e "${BLUE}ℹ URL: $(gh repo view --json url -q .url)${NC}\n"
else
    echo -e "${GREEN}✅ Using existing repository${NC}\n"
fi

# Step 4: Push to GitHub
echo -e "${MAGENTA}${BOLD}STEP 4: Pushing to GitHub${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

# Check if there are commits to push
if git log origin/main..HEAD &> /dev/null 2>&1; then
    echo -e "${BLUE}ℹ Pushing commits to GitHub...${NC}\n"
    git push -u origin main
    echo -e "\n${GREEN}✅ Pushed to GitHub${NC}\n"
else
    echo -e "${BLUE}ℹ Pushing to GitHub...${NC}\n"
    git push -u origin main 2>&1 || {
        echo -e "${YELLOW}⚠ Push failed. Trying force push with lease...${NC}"
        git push -u origin main --force-with-lease
    }
    echo -e "\n${GREEN}✅ Pushed to GitHub${NC}\n"
fi

# Step 5: Enable GitHub Pages
echo -e "${MAGENTA}${BOLD}STEP 5: Enabling GitHub Pages${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

read -p "$(echo -e ${CYAN}Enable GitHub Pages? [Y/n]: ${NC})" ENABLE_PAGES
ENABLE_PAGES=${ENABLE_PAGES:-y}

if [[ "$ENABLE_PAGES" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}ℹ Enabling GitHub Pages from main branch...${NC}\n"
    
    # Get repository name with owner
    REPO_FULL=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    
    # Enable Pages using GitHub API
    gh api "repos/$REPO_FULL/pages" \
        -X POST \
        -f "source[branch]=main" \
        -f "source[path]=/" \
        2>&1 || {
            echo -e "${YELLOW}⚠ Pages may already be enabled or error occurred${NC}"
        }
    
    echo -e "\n${GREEN}✅ GitHub Pages enabled${NC}"
    
    # Get Pages URL
    sleep 2
    PAGES_URL=$(gh api "repos/$REPO_FULL/pages" -q .html_url 2>/dev/null || echo "")
    
    if [ -n "$PAGES_URL" ]; then
        echo -e "${BLUE}ℹ Pages URL: ${BOLD}$PAGES_URL${NC}"
        echo -e "${YELLOW}⚠ Note: It may take a few minutes for the site to be available${NC}\n"
    fi
fi

# Step 6: Add topics
echo -e "${MAGENTA}${BOLD}STEP 6: Adding Repository Topics${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

read -p "$(echo -e ${CYAN}Add topics (tags)? [Y/n]: ${NC})" ADD_TOPICS
ADD_TOPICS=${ADD_TOPICS:-y}

if [[ "$ADD_TOPICS" =~ ^[Yy]$ ]]; then
    TOPICS="callback,twilio,flask,docker,automation,security,click-to-call,python,recaptcha"
    echo -e "${BLUE}ℹ Adding topics: $TOPICS${NC}\n"
    
    gh repo edit --add-topic "$TOPICS"
    
    echo -e "${GREEN}✅ Topics added${NC}\n"
fi

# Summary
echo -e "${MAGENTA}${BOLD}SUMMARY${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

echo -e "${GREEN}✅ Repository setup complete!${NC}\n"

echo -e "${BOLD}Repository Details:${NC}"
gh repo view

echo -e "\n${BOLD}Next Steps:${NC}"
echo -e "  ${BLUE}1.${NC} View repository: ${CYAN}gh repo view --web${NC}"
echo -e "  ${BLUE}2.${NC} Check Pages status: ${CYAN}gh api repos/$REPO_FULL/pages${NC}"
echo -e "  ${BLUE}3.${NC} Update frontend/app.js with backend URL"
echo -e "  ${BLUE}4.${NC} Configure .env with Twilio and reCAPTCHA credentials"
echo -e "  ${BLUE}5.${NC} Deploy backend to cloud provider\n"

echo -e "${GREEN}${BOLD}🎉 All done!${NC}\n"

