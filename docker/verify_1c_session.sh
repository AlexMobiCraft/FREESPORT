#!/bin/bash
# Script to verify 1C Session Fragmentation Fix
# Usage: ./verify_1c_session.sh [host]

HOST=${1:-"http://localhost:8001"}
API_URL="$HOST/api/integration/1c/exchange/"
USER="admin"
PASS="admin"  # Replace with actual admin credentials if different

echo "Targeting: $API_URL"

# 1. CheckAuth - Get Cookie and SessionID
echo "----------------------------------------"
echo "1. Step: CheckAuth (Basic Auth)"
response=$(curl -s -D headers.txt -u "$USER:$PASS" "$API_URL?mode=checkauth")
echo "Response: $response"
COOKIE_VAL=$(grep -oP 'sessionid=\K[^;]+' headers.txt)
SESSID=$(echo "$response" | sed -n '3p')
echo "Extracted Cookie: $COOKIE_VAL"
echo "Extracted SessID: $SESSID"

if [ -z "$SESSID" ]; then
    echo "ERROR: Failed to get SessID"
    exit 1
fi

# 2. Init - Verify Strict Linkage (Using URL param ONLY)
echo "----------------------------------------"
echo "2. Step: Init (URL Param Priority)"
# We intentionally DO NOT send cookie, only URL param to test strict linkage AC 1
response=$(curl -s "$API_URL?mode=init&sessid=$SESSID")
echo "Response:"
echo "$response"

if [[ "$response" != *"sessid=$SESSID"* ]]; then
    echo "FAIL: Init response did not confirm correct sessid"
else
    echo "PASS: Init verified sessid from URL"
fi

# 3. Import - Concurrent Request Simulation
echo "----------------------------------------"
echo "3. Step: Import (Concurrency/Idempotency Check)"
# Send first import command
echo "Sending Import #1..."
curl -s "$API_URL?mode=import&filename=import.xml&sessid=$SESSID" > /dev/null &
PID1=$!

# Send second import command immediately (Simulate race)
echo "Sending Import #2 (Duplicate)..."
response2=$(curl -s "$API_URL?mode=import&filename=import.xml&sessid=$SESSID")
echo "Response Import #2: $response2"

wait $PID1

if [[ "$response2" == *"success"* ]]; then
    echo "PASS: Duplicate request returned success (Idempotent)"
else
    echo "FAIL: Duplicate request failed"
fi

echo "----------------------------------------"
echo "Verification Complete. Check logs for 'Duplicate import request' message."
rm headers.txt
