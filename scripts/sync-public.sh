#!/bin/bash
# Sync stable main to public repo (github.com/fockus/cognitia)
#
# Usage: ./scripts/sync-public.sh [--tags]
#
# Prerequisites:
#   - On main branch
#   - Working tree clean
#   - All tests passing
#
# What it does:
#   1. Verifies main is clean and tested
#   2. Pushes main to public remote
#   3. Optionally pushes tags (--tags)

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check branch
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo -e "${RED}Error: Must be on main branch (currently on '$BRANCH')${NC}"
    exit 1
fi

# Check clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: Working tree not clean. Commit or stash changes first.${NC}"
    git status --short
    exit 1
fi

# Check public remote exists
if ! git remote get-url public &>/dev/null; then
    echo -e "${RED}Error: 'public' remote not configured.${NC}"
    echo "Run: git remote add public https://github.com/fockus/cognitia.git"
    exit 1
fi

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
if ! pytest -q 2>&1 | tail -3; then
    echo -e "${RED}Error: Tests failed. Fix before syncing to public.${NC}"
    exit 1
fi

# Push main to public
echo -e "${YELLOW}Pushing main to public...${NC}"
git push public main

# Push tags if requested
if [ "${1:-}" = "--tags" ]; then
    echo -e "${YELLOW}Pushing tags to public...${NC}"
    git push public --tags
fi

echo -e "${GREEN}Synced to public repo.${NC}"
echo "  Public: $(git remote get-url public)"
echo "  Branch: main"
echo "  Commit: $(git log --oneline -1)"
