# 🐳 Watchtower AI - Docker Guide

This guide explains how to containerize and run your Watchtower AI application using Docker with the **NEW Two-Level Classification System**.

## 🆕 What's New in v2.0.0

- **🔍 Two-Level Classification**: First classifies the group, then determines the specific table or analytics within that group
- **🤖 Enhanced Tool Selection**: More granular tool selection based on the two-level classification
- **📊 Better Response Handling**: Improved chart, text, and table response formatting
- **🧠 Analytics Integration**: Better integration with analytics tools for complex queries

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
docker run -d --name watchtower-ai-new-architecture -p 8000:8000 watchtower-ai:latest

# View logs
docker logs -f watchtower-ai-new-architecture

# Stop the container
docker stop watchtower-ai-new-architecture
docker rm watchtower-ai-new-architecture
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
  - WATCHTOWER_ARCHITECTURE=new_two_level_classification
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
docker-compose logs -f watchtower-ai-new-architecture

# Direct Docker logs
docker logs -f watchtower-ai-new-architecture

# Last 100 lines
docker logs --tail 100 watchtower-ai-new-architecture
```

### Debugging

```bash
# Run container in interactive mode
docker run -it --rm -p 8000:8000 watchtower-ai:latest /bin/bash

# Execute commands in running container
docker exec -it watchtower-ai-new-architecture /bin/bash
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
├── Dockerfile              # Main Docker image definition (Updated for v2.0.0)
├── docker-compose.yml      # Docker Compose configuration (Updated for v2.0.0)
├── .dockerignore          # Files to exclude from Docker build
├── build.sh               # Linux/Mac build script
├── build.bat              # Windows build script
├── requirements.txt       # Python dependencies
├── main.py               # FastAPI application (NEW Two-Level Classification)
├── agents/               # Agent implementations
│   └── new_tool_selector_agent.py  # NEW Two-Level Tool Selector
├── intent/               # Intent classification
│   ├── classify_group.py           # NEW First-level classification
│   └── classify_table_within_group.py  # NEW Second-level classification
└── tools/                # Tool implementations (organized by group)
    ├── monitor_group/    # Monitor-related tools
    ├── facts_group/      # Facts-related tools
    ├── rules_group/      # Rules-related tools
    └── actions_group/    # Actions-related tools
```

## 🔒 Security Considerations

- The container runs as a non-root user (`app`)
- Health checks prevent unhealthy containers from receiving traffic
- Config files are mounted as read-only
- System packages are cleaned up after installation
- Unnecessary files (__pycache__, .git, venv) are removed during build

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
5. Ensure all required ports are available

## 🧪 Testing the New Architecture

The new two-level classification system can be tested using:

```bash
# Test a query with the new system
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all monitors"}'
```
