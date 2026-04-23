#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Navigate to project root (3 levels up from tests/client/ansible/)
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../.." && pwd )"

# Enable health endpoint
export ENABLE_HEALTH_ENDPOINT="True"

cd "$PROJECT_ROOT"

echo "Starting Ansible role integration test..."
echo "Project root: $PROJECT_ROOT"

# Cleanup
pkill -f "python -m fact_inventory" 2>/dev/null || true
rm -f /tmp/${USER}_fact_inventory_testing.sqlite

# Setup - ensure DEPLOYMENT is set
export DEPLOYMENT=testing

echo "Ensure needed libraries..."
uv sync

echo "Running database migrations..."
uv run litestar --app fact_inventory:app database upgrade --no-prompt

# Start app in background
echo "Starting application..."
uv run python -m fact_inventory > /tmp/app-test.log 2>&1 &
APP_PID=$!
trap "kill $APP_PID 2>/dev/null || true" EXIT

# Wait for app to be ready
echo "Waiting for application to be ready..."
sleep 2

if ! ps -p $APP_PID > /dev/null 2>&1; then
  echo "ERROR: Application process died during startup"
  tail -20 /tmp/app-test.log
  exit 1
fi

for i in {1..30}; do
  if curl --output /dev/null -f http://localhost:8000/fact_inventory/health 2>/dev/null; then
    echo "Application is ready on port 8000"
    break
  fi

  if ! ps -p $APP_PID > /dev/null 2>&1; then
    echo "ERROR: Application process died while waiting for readiness"
    tail -20 /tmp/app-test.log
    exit 1
  fi

  if [ $i -eq 1 ] || [ $((i % 5)) -eq 0 ]; then
    echo "Still waiting... ($i/30)"
  fi
  sleep 1
done

# Final check
if ! curl --output /dev/null -f http://localhost:8000/fact_inventory/health 2>/dev/null; then
  echo "ERROR: Application failed to become ready after 30 seconds"
  echo "Last 20 lines of app log:"
  tail -20 /tmp/app-test.log
  exit 1
fi

# Run test playbook with collections path set
# Disable become for testing (since we're localhost and don't need sudo)
echo "Running Ansible playbook..."
export ANSIBLE_COLLECTIONS_PATH="$PROJECT_ROOT/client/ansible_collections"
ansible-playbook \
  -e "fact_inventory_gather_facts_become=false" \
  -e "fact_inventory_gather_audit_become=false" \
  "$SCRIPT_DIR/playbooks/test-ansible-role.yml"
