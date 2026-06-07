#!/bin/bash

# --- CONFIGURATION ---
MAC="REPLACE_WITH_MAC_OF_PC"
LOCAL_IP="REPLACE_WITH_MAC_OF_PC.119" # Ping the LOCAL IP for faster detection
BROADCAST="REPLACE_WITH_MAC_OF_PC.255" # Force packet to local physical network

# --- COLORS ---
GREEN='\033[01;32m'
YELLOW='\033[01;33m'
CYAN='\033[01;36m'
NONE='\033[00m'

echo -e "${CYAN}Sending Magic Packet to Blaszak ($MAC) via $BROADCAST...${NONE}"

# We use -i to force the packet out onto the local physical subnet
LC_ALL=C wakeonlan -i $BROADCAST $MAC > /dev/null 2>&1

echo -e "${YELLOW}Waiting for Blaszak to wake up (Local IP: $LOCAL_IP)...${NONE}"

count=0
while ! ping -c 1 -W 1 $LOCAL_IP > /dev/null; do
    printf "."
    sleep 2
    ((count++))
    if [ $count -gt 30 ]; then
        echo -e "\n${RED}Timeout: Blaszak is not responding to pings.${NONE}"
        exit 1
    fi
done

echo -e "\n${GREEN} Blaszak is ONLINE (Local)! Tailscale will be up shortly.${NONE}"
