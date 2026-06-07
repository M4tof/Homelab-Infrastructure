#!/bin/bash
LOG_FILE="/opt/stacks/decoy-web/logs/access.log"

tail -n 0 -F "$LOG_FILE" | while read -r LINE
do
  if echo "$LINE" | grep -qE "admin|admin_portal"; then
    IP=$(echo "$LINE" | awk '{print $1}')
    MSG="INTRUDER ALERT: Scanner found the trap! IP: $IP"
    curl -s -d "$MSG" ntfy.sh/TOPIC_NAME_REPLACE_HERE > /dev/null
  fi
done
