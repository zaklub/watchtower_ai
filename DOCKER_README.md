# 🐳 Watchtower AI - Docker Guide

This guide explains how to containerize and run your Watchtower AI application using Docker.

## 📋 Prerequisites

- Docker installed and running
- Docker Compose (usually comes with Docker Desktop)
- Git (to clone the repository)

## 🏗️ Building the Docker Image

### Option 1: Using the Build Script (Recommended)

**Windows:**
```bash
build.bat
```

**Linux/Mac:**
```bash
chmod +x build.sh
./build.sh
```

### Option 2: Manual Docker Build

```bash
docker build -t watchtower-ai:latest .
```

## 🚀 Running the Application

### Option 1: Using Docker Compose (Recommended)

```bash
# Start the application in the background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

### Option 2: Direct Docker Run

```bash
# Run the container
docker run -d --name watchtower-ai -p 8000:8000 watchtower-ai:latest

# View logs
docker logs -f watchtower-ai

# Stop the container
docker stop watchtower-ai
docker rm watchtower-ai
```

## 🌐 Accessing the Application

Once running, your application will be available at:
- **API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API Documentation**: http://localhost:8000/docs

## 🔧 Configuration

### Environment Variables

The following environment variables can be set in `docker-compose.yml`:

```yaml
environment:
  - PYTHONPATH=/app
  - PYTHONUNBUFFERED=1
  # Add your database connection strings here
  - DATABASE_URL=postgresql://user:pass@host:port/db
```

### Volume Mounts

The `docker-compose.yml` includes these volume mounts:
- `./config.py:/app/config.py:ro` - Read-only config file
- `./logs:/app/logs` - Persistent logs directory

## 📊 Monitoring and Health Checks

The Docker container includes health checks:
- **Health Check Endpoint**: `/health`
- **Check Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## 🐛 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using port 8000
   netstat -ano | findstr :8000
   
   # Kill the process or change the port in docker-compose.yml
   ```

2. **Database Connection Issues**
   - Ensure your database is accessible from the container
   - Check firewall settings
   - Verify connection strings in config.py

3. **Permission Issues**
   ```bash
   # If you get permission errors, run as administrator
   # or check file ownership
   ```

### Viewing Logs

```bash
# Docker Compose logs
docker-compose logs -f watchtower-ai

# Direct Docker logs
docker logs -f watchtower-ai

# Last 100 lines
docker logs --tail 100 watchtower-ai
```

### Debugging

```bash
# Run container in interactive mode
docker run -it --rm -p 8000:8000 watchtower-ai:latest /bin/bash

# Execute commands in running container
docker exec -it watchtower-ai /bin/bash
```

## 🔄 Development Workflow

### Rebuilding After Code Changes

```bash
# Stop the current container
docker-compose down

# Rebuild the image
docker build -t watchtower-ai:latest .

# Start again
docker-compose up -d
```

### Hot Reload (Development)

For development with hot reload, you can mount your source code:

```yaml
volumes:
  - .:/app
```

## 🚀 Production Deployment

### Multi-Stage Build

For production, consider using a multi-stage build:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
# ... build dependencies

# Production stage
FROM python:3.11-slim
# ... copy only necessary files
```

### Environment-Specific Configs

Create different docker-compose files:
- `docker-compose.yml` - Development
- `docker-compose.prod.yml` - Production
- `docker-compose.test.yml` - Testing

## 📁 File Structure

```
watchtower_ai/
├── Dockerfile              # Main Docker image definition
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore          # Files to exclude from Docker build
├── build.sh               # Linux/Mac build script
├── build.bat              # Windows build script
├── requirements.txt       # Python dependencies
├── main.py               # FastAPI application
└── ...                   # Other application files
```

## 🔒 Security Considerations

- The container runs as a non-root user (`app`)
- Health checks prevent unhealthy containers from receiving traffic
- Config files are mounted as read-only
- System packages are cleaned up after installation

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Docker Guide](https://fastapi.tiangolo.com/deployment/docker/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)

## 🆘 Support

If you encounter issues:
1. Check the logs: `docker-compose logs -f`
2. Verify Docker is running: `docker info`
3. Check container status: `docker ps -a`
4. Ensure all required ports are available
