#!/bin/bash
#
# Custom Ubuntu Welcome Screen (MOTD Template)
#
# This file shows what gets installed to /etc/update-motd.d/00-custom-welcome
# You can customize this template and copy it directly to your server
#
# Installation:
#   1. Copy to server: scp motd-template.sh root@server:/etc/update-motd.d/00-custom-welcome
#   2. Make executable: ssh root@server "chmod +x /etc/update-motd.d/00-custom-welcome"
#   3. Install figlet: ssh root@server "apt-get install -y figlet"
#

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================

# Text to display as ASCII art (leave empty to use hostname)
WELCOME_TEXT=""

# ASCII font (standard, slant, banner, big, block, bubble, digital, lean, small)
ASCII_FONT="slant"

# Color code (31=red, 32=green, 33=yellow, 34=blue, 35=magenta, 36=cyan, 37=white)
COLOR_CODE="36"

# =============================================================================
# SCRIPT - MODIFY BELOW TO CHANGE WELCOME MESSAGE
# =============================================================================

# Use hostname if WELCOME_TEXT is empty
if [ -z "$WELCOME_TEXT" ]; then
    WELCOME_TEXT=$(hostname | tr '[:lower:]' '[:upper:]')
fi

# Print ASCII art banner with color
echo ""
echo -e "\033[1;${COLOR_CODE}m"
figlet -f "$ASCII_FONT" "$WELCOME_TEXT" 2>/dev/null || echo "$WELCOME_TEXT"
echo -e "\033[0m"

# =============================================================================
# WELCOME MESSAGE - EDIT BELOW TO CUSTOMIZE
# =============================================================================

echo ""
echo "Welcome to $(hostname)"
echo ""
echo "System Information:"
echo "  - IP Address: $(hostname -I | awk '{print $1}')"
echo "  - Uptime: $(uptime -p)"
echo "  - Memory: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "  - Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 " used)"}')"
echo "  - Load: $(cat /proc/loadavg | awk '{print $1, $2, $3}')"
echo "  - CPU: $(nproc) cores"
echo ""

# Show logged in users
USERS=$(who | wc -l)
echo "Currently logged in users: $USERS"
echo ""

# =============================================================================
# OPTIONAL: ADD CUSTOM MESSAGES BELOW
# =============================================================================

# Example: Show if Docker is running
# if command -v docker &> /dev/null; then
#     CONTAINERS=$(docker ps -q | wc -l)
#     echo "Docker containers running: $CONTAINERS"
# fi

# Example: Show a random quote
# QUOTES=(
#     "The best way to predict the future is to invent it."
#     "Code is like humor. When you have to explain it, it's bad."
#     "First, solve the problem. Then, write the code."
# )
# echo "${QUOTES[$RANDOM % ${#QUOTES[@]}]}"
# echo ""

# Example: Show security warnings
# UPDATES=$(apt list --upgradable 2>/dev/null | wc -l)
# if [ "$UPDATES" -gt 1 ]; then
#     echo -e "\033[33mWarning: $((UPDATES-1)) packages can be updated\033[0m"
# fi
