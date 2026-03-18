#!/usr/bin/env bash
#
# Test harness for rick_db examples.
#
# Usage:
#   ./examples/run_tests.sh          # run all tests (starts/stops docker)
#   ./examples/run_tests.sh sqlite   # run only SQLite + query builder tests (no docker)
#   ./examples/run_tests.sh --no-teardown  # keep containers running after tests
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Detect python
if [ -x "$PROJECT_DIR/.venv_test/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv_test/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    PYTHON="python"
fi

PYTEST="$PYTHON -m pytest"
TEARDOWN=1
MODE="all"

for arg in "$@"; do
    case "$arg" in
        sqlite)      MODE="sqlite" ;;
        --no-teardown) TEARDOWN=0 ;;
        *)           echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

cleanup() {
    if [ "$TEARDOWN" -eq 1 ] && [ "$MODE" = "all" ]; then
        echo ""
        echo "==> Stopping docker services..."
        docker compose -f "$COMPOSE_FILE" down --volumes --remove-orphans 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "==> Using python: $PYTHON"
$PYTHON --version

if [ "$MODE" = "all" ]; then
    echo ""
    echo "==> Starting docker services..."
    docker compose -f "$COMPOSE_FILE" up -d --wait

    echo ""
    echo "==> Running all example tests..."
    $PYTEST "$SCRIPT_DIR/test_examples.py" -v
else
    echo ""
    echo "==> Running SQLite and query builder tests only (no docker)..."
    $PYTEST "$SCRIPT_DIR/test_examples.py" -v \
        -k "TestSqliteExamples or TestQueryBuilderExamples"
fi
