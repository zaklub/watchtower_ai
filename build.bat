@echo off
echo 🐳 Building Watchtower AI Docker Image...

REM Build the Docker image
docker build -t watchtower-ai:latest .

if %ERRORLEVEL% EQU 0 (
    echo ✅ Docker image built successfully!
    echo.
    echo 🚀 To run the application:
    echo    docker run -p 8000:8000 watchtower-ai:latest
    echo.
    echo 🔧 Or use docker-compose:
    echo    docker-compose up -d
    echo.
    echo 📊 To view logs:
    echo    docker-compose logs -f
    echo.
    echo 🛑 To stop:
    echo    docker-compose down
) else (
    echo ❌ Docker build failed!
    exit /b 1
)
