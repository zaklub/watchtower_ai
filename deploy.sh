#!/bin/bash

# Watchtower AI Production Deployment Script
# Version: 2.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="watchtower-ai"
VERSION="2.0.0"
DOCKER_IMAGE="${APP_NAME}:${VERSION}"
CONTAINER_NAME="${APP_NAME}-v2"

echo -e "${BLUE}🚀 Watchtower AI Production Deployment${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

print_status "Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

print_status "docker-compose is available"

# Create logs directory if it doesn't exist
if [ ! -d "./logs" ]; then
    mkdir -p ./logs
    print_status "Created logs directory"
fi

# Stop and remove existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true

# Remove old images to free up space
print_status "Cleaning up old images..."
docker image prune -f > /dev/null 2>&1 || true

# Build the new image
print_status "Building Docker image..."
docker-compose build --no-cache

# Start the services
print_status "Starting services..."
docker-compose up -d

# Wait for the service to be healthy
print_status "Waiting for service to be healthy..."
timeout=120
counter=0
while [ $counter -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        print_status "Service is healthy!"
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

if [ $counter -ge $timeout ]; then
    print_warning "Service health check timeout. Checking logs..."
    docker-compose logs --tail=20
    exit 1
fi

# Test the API
print_status "Testing API endpoint..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_status "API is responding correctly"
else
    print_error "API is not responding. Checking logs..."
    docker-compose logs --tail=20
    exit 1
fi

# Show deployment info
echo ""
echo -e "${BLUE}🎉 Deployment Successful!${NC}"
echo -e "${BLUE}Service: ${APP_NAME}${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo -e "${BLUE}Container: ${CONTAINER_NAME}${NC}"
echo -e "${BLUE}URL: http://localhost:8000${NC}"
echo -e "${BLUE}Health Check: http://localhost:8000/health${NC}"
echo ""

# Show running containers
print_status "Running containers:"
docker-compose ps

echo ""
print_status "Deployment completed successfully!"
print_warning "Use 'docker-compose logs -f' to monitor logs"
print_warning "Use 'docker-compose down' to stop the service"
