@echo off
setlocal enabledelayedexpansion

REM Watchtower AI Production Deployment Script for Windows
REM Version: 2.0.0

echo 🚀 Watchtower AI Production Deployment
echo Version: 2.0.0
echo.

REM Configuration
set APP_NAME=watchtower-ai
set VERSION=2.0.0
set DOCKER_IMAGE=%APP_NAME%:%VERSION%
set CONTAINER_NAME=%APP_NAME%-v2

REM Function to print colored output
:print_status
echo ✅ %~1
goto :eof

:print_warning
echo ⚠️  %~1
goto :eof

:print_error
echo ❌ %~1
goto :eof

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    call :print_error "Docker is not running. Please start Docker and try again."
    exit /b 1
)

call :print_status "Docker is running"

REM Check if docker-compose is available
docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :print_error "docker-compose is not installed. Please install it and try again."
    exit /b 1
)

call :print_status "docker-compose is available"

REM Create logs directory if it doesn't exist
if not exist "logs" (
    mkdir logs
    call :print_status "Created logs directory"
)

REM Stop and remove existing containers
call :print_status "Stopping existing containers..."
docker-compose down --remove-orphans >nul 2>&1

REM Remove old images to free up space
call :print_status "Cleaning up old images..."
docker image prune -f >nul 2>&1

REM Build the new image
call :print_status "Building Docker image..."
docker-compose build --no-cache
if errorlevel 1 (
    call :print_error "Build failed"
    exit /b 1
)

REM Start the services
call :print_status "Starting services..."
docker-compose up -d
if errorlevel 1 (
    call :print_error "Failed to start services"
    exit /b 1
)

REM Wait for the service to be healthy
call :print_status "Waiting for service to be healthy..."
set timeout=120
set counter=0
:health_check_loop
if %counter% geq %timeout% (
    call :print_warning "Service health check timeout. Checking logs..."
    docker-compose logs --tail=20
    exit /b 1
)

docker-compose ps | findstr "healthy" >nul
if not errorlevel 1 (
    call :print_status "Service is healthy!"
    goto :test_api
)

timeout /t 2 /nobreak >nul
set /a counter+=2
echo -n .
goto :health_check_loop

:test_api
REM Test the API
call :print_status "Testing API endpoint..."
curl -f http://localhost:8000/health >nul 2>&1
if errorlevel 1 (
    call :print_error "API is not responding. Checking logs..."
    docker-compose logs --tail=20
    exit /b 1
)

call :print_status "API is responding correctly"

REM Show deployment info
echo.
echo 🎉 Deployment Successful!
echo Service: %APP_NAME%
echo Version: %VERSION%
echo Container: %CONTAINER_NAME%
echo URL: http://localhost:8000
echo Health Check: http://localhost:8000/health
echo.

REM Show running containers
call :print_status "Running containers:"
docker-compose ps

echo.
call :print_status "Deployment completed successfully!"
call :print_warning "Use 'docker-compose logs -f' to monitor logs"
call :print_warning "Use 'docker-compose down' to stop the service"

pause
