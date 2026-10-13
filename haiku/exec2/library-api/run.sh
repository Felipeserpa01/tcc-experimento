#!/bin/bash

# Library API - Run Scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 is required but not installed.${NC}"
    exit 1
fi

echo -e "${GREEN}Library API - Management Scripts${NC}\n"

case "$1" in
    "install")
        echo -e "${YELLOW}Installing dependencies...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}Dependencies installed!${NC}"
        ;;
    "run")
        echo -e "${YELLOW}Starting API server...${NC}"
        echo -e "${GREEN}Access the API at: http://localhost:8000${NC}"
        echo -e "${GREEN}API Documentation: http://localhost:8000/docs${NC}"
        uvicorn app.main:app --reload
        ;;
    "test")
        echo -e "${YELLOW}Running tests...${NC}"
        python3 -m pytest tests/ -v
        ;;
    "test-coverage")
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        python3 -m pytest tests/ --cov=app --cov-report=html
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "clean")
        echo -e "${YELLOW}Cleaning up...${NC}"
        rm -f library.db
        rm -rf __pycache__ .pytest_cache htmlcov .coverage
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
        echo -e "${GREEN}Cleanup complete!${NC}"
        ;;
    "reset")
        echo -e "${YELLOW}Resetting database...${NC}"
        rm -f library.db test.db
        echo -e "${GREEN}Database reset! Start the server to create a new one.${NC}"
        ;;
    *)
        echo -e "${YELLOW}Usage:${NC}"
        echo "  ./run.sh install       - Install dependencies"
        echo "  ./run.sh run           - Start API server"
        echo "  ./run.sh test          - Run tests"
        echo "  ./run.sh test-coverage - Run tests with coverage report"
        echo "  ./run.sh clean         - Clean temporary files"
        echo "  ./run.sh reset         - Reset database"
        ;;
esac
