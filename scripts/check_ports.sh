#!/bin/bash

# --- SETTINGS ---
START_PORT=8000
END_PORT=9000
COUNT_TO_SHOW=5

# --- COLORS ---
GREEN='\033[01;32m'
YELLOW='\033[01;33m'
CYAN='\033[01;36m'
NONE='\033[00m'

echo -e "${CYAN}=== HomeLab Port Scanner ===${NONE}"

# Gathers used ports by looking for numbers following a colon
# We also filter for ports > 0 just in case
USED_PORTS=$(ss -H -tuln | grep -oP '(?<=:)\d+(?=\s|$)' | awk '$1 > 0' | sort -nu)

echo -e "${YELLOW}Currently Taken Ports:${NONE}"
echo "$USED_PORTS" | xargs | sed 's/ /, /g'
echo ""

echo -e "${GREEN}Next $COUNT_TO_SHOW Available Ports (starting at $START_PORT):${NONE}"
found=0
port=$START_PORT

while [ $found -lt $COUNT_TO_SHOW ] && [ $port -le $END_PORT ]; do
    if ! echo "$USED_PORTS" | grep -qxw "$port"; then
        echo -e "  -> $port"
        ((found++))
    fi
    ((port++))
done
echo -e "${CYAN}============================${NONE}"
