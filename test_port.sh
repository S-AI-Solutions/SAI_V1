#!/bin/bash

echo "🧪 Testing Docker PORT variable handling..."

# Test 1: Default port
echo "Test 1: Testing default port (should be 8000)"
unset PORT
./start.sh &
SERVER_PID=$!
sleep 2
kill $SERVER_PID 2>/dev/null || true
echo ""

# Test 2: Custom port
echo "Test 2: Testing custom port (should be 9000)"
export PORT=9000
./start.sh &
SERVER_PID=$!
sleep 2
kill $SERVER_PID 2>/dev/null || true
echo ""

# Test 3: Invalid port
echo "Test 3: Testing invalid port (should fail)"
export PORT="not_a_number"
if ./start.sh 2>&1 | grep -q "Error: PORT must be a number"; then
    echo "✅ Invalid port handling works correctly"
else
    echo "❌ Invalid port handling failed"
fi
echo ""

echo "🏁 Port handling tests completed"
