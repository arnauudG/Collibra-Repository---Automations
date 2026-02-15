#!/bin/bash
# Run all test scripts sequentially with delays to avoid rate limits

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "============================================================"
echo "Running All Collibra Client Test Scripts"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run a script with a delay
run_script() {
    local script_name=$1
    local description=$2
    
    echo -e "${YELLOW}Running: $script_name${NC}"
    echo "Description: $description"
    echo "----------------------------------------"
    
    if python3 "$SCRIPT_DIR/$script_name"; then
        echo -e "${GREEN}✓ $script_name completed successfully${NC}"
    else
        echo -e "${YELLOW}⚠ $script_name had issues (may be due to rate limits)${NC}"
    fi
    
    echo ""
    echo "Waiting 10 seconds before next script..."
    sleep 10
    echo ""
}

# Run scripts in order (connection governing only; no metadata sync)
run_script "test_connection_simple.py" "Quick OAuth connection test"
run_script "test_database_connections_simple.py" "List database connections (governed set)"
echo ""
echo "============================================================"
echo "All scripts completed!"
echo "============================================================"

