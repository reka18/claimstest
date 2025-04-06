#!/bin/bash

# Define the test-specific Docker Compose file
DOCKER_COMPOSE_TEST_FILE="docker-compose-test.yml"

# Set the test database URL
export DATABASE_URL="postgresql+asyncpg://test_user:test_password@db_test/test_claims_db"

# Debug: Confirm the DATABASE_URL
echo "Using test database URL: $DATABASE_URL"

# Bring up the test environment using the test-specific Compose file
echo "Starting test environment..."
docker-compose -f $DOCKER_COMPOSE_TEST_FILE down -v
docker-compose -f $DOCKER_COMPOSE_TEST_FILE up --build -d

# Wait for the app to be ready by checking its /health endpoint
echo "Waiting for the test app to be ready..."
while ! curl -s http://0.0.0.0:8001/health | grep "OK" > /dev/null; do
   echo "Test app is not ready yet. Retrying in 1 second..."
   sleep 1
done
echo "Test app is ready!"

# Run tests using pytest
echo "Running tests..."
pytest tests/ --tb=short -q

# Capture the pytest exit code
TEST_EXIT_CODE=$?

# Cleanup: Stop and remove containers after testing
echo "Stopping and removing test containers..."
docker-compose -f $DOCKER_COMPOSE_TEST_FILE down -v

# Provide test result summary
if [ $TEST_EXIT_CODE -eq 0 ]; then
   echo "All tests passed successfully."
else
   echo "Some tests failed. Check the logs for details."
fi

# Exit with the pytest exit code
exit $TEST_EXIT_CODE