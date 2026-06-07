#!/bin/bash

if [[ -z "$1" ]] || ! [[ "$1" =~ ^[0-9]+$ ]]; then
    echo "Usage: $0 <seconds>"
    exit 1
fi

TOTAL_SECONDS=$1
TOPIC="lab/pi/status"
PUB_CMD="docker exec mosquitto mosquitto_pub"

echo "Setting a timer for $TOTAL_SECONDS seconds"

for ((i = TOTAL_SECONDS ; i >= 0 ; i--)); do
	min=$(($i / 60))
	sec=$(($i % 60))

	printf -v timer "%02d:%02d" "$min" "$sec"
    	echo "Time remaining: $timer"

	payload="{\"c\":\"TIMER ACTIVE|TIME LEFT: $timer\"}"
	$PUB_CMD -h localhost -t "$TOPIC" -m "$payload"


	if [ $i -gt 0 ]; then
        	sleep 1
    	fi
done

echo "TIMER FINISHED"
$PUB_CMD -h localhost -t "$TOPIC" -m "{\"a\": 2, \"c\":\"!!TIMER FIN!!\"}"

echo "Waiting 10s for physical alert..."
sleep 10

echo "TIMER CLEARED"
$PUB_CMD -h localhost -t "$TOPIC" -m "{\"a\": 3, \"c\":\"TIMER CLR\"}"
