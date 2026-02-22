#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.." || exit 1

IMAGE_NAME="hive-test"

# Build the test image securely
echo "=== Building Docker Image ==="
docker build -t "$IMAGE_NAME" -f "$WORK_DIR/tests/Dockerfile.test" "$WORK_DIR/.."

echo ""
echo "=== Running 'hive onboard' ==="
docker run --name hive-test-run "$IMAGE_NAME" onboard
echo "=== 'hive onboard' complete ==="

echo ""
echo "=== Running 'hive status' ==="
STATUS_OUTPUT=$(docker commit hive-test-run hive-test-onboarded > /dev/null && \
    docker run --rm hive-test-onboarded status 2>&1) || true

echo "$STATUS_OUTPUT"

echo ""
echo "=== Validating output ==="
PASS=true

check() {
    if echo "$STATUS_OUTPUT" | grep -q "$1"; then
        echo "  PASS: found '$1'"
    else
        echo "  FAIL: missing '$1'"
        PASS=false
    fi
}

check "Hive Status"
check "Config:"
check "Workspace:"
check "Model:"
check "OpenRouter API:"
check "Anthropic API:"
check "OpenAI API:"

echo ""
if $PASS; then
    echo "=== All checks passed ==="
else
    echo "=== Some checks FAILED ==="
    exit 1
fi

# Cleanup
echo ""
echo "=== Cleanup ==="
docker rm -f hive-test-run 2>/dev/null || true
docker rmi -f hive-test-onboarded 2>/dev/null || true
docker rmi -f "$IMAGE_NAME" 2>/dev/null || true
echo "Done."
