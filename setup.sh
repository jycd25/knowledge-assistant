#!/bin/bash

# Setup script for Knowledge Assistant
# This script initializes the database and starts the application

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up Knowledge Assistant...${NC}"

# Create necessary directories
echo -e "${GREEN}Creating necessary directories...${NC}"
mkdir -p data/uploads data/lancedb data/nltk_data

# Check if tantivy is installed
echo -e "${GREEN}Checking for tantivy package...${NC}"
if pip list | grep -q "tantivy"; then
    echo -e "${GREEN}tantivy is already installed.${NC}"
else
    echo -e "${YELLOW}Installing tantivy for improved search capabilities...${NC}"
    pip install tantivy
fi

# Initialize the database
echo -e "${GREEN}Initializing database...${NC}"
python utils/init_db.py

# Check the exit code
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Database initialization successful!${NC}"
    
    # Start the application
    echo -e "${GREEN}Starting Knowledge Assistant...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the application when you're done.${NC}"
    streamlit run app/app_st.py
else
    echo -e "${RED}Database initialization failed. Please check the logs above.${NC}"
    exit 1
fi 