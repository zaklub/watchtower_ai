# Watchtower AI Deployment Guide

## Overview

Watchtower AI is a sophisticated monitoring and analytics system with a two-level classification architecture. This guide covers production deployment using Docker and Docker Compose.

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine (Linux)
- Docker Compose
- At least 2GB RAM available
- PostgreSQL database (external or local)

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd watchtower_ai
```

### 2. Configure Database

Edit `config.py` to set your database connection:

```python
DATABASE_CONFIG = {
    "host": "your-db-host",
    "port": 5432,
    "database": "your-database",
    "user": "your-username", 
    "password": "your-password"
}
```

### 3. Deploy

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```cmd
deploy.bat
```

**Manual:**
```bash
docker-compose up -d
```

## 📋 System Requirements

### Minimum Requirements
- **CPU**: 1 core
- **RAM**: 512MB
- **Storage**: 1GB
- **Network**: Internet access for Ollama

### Recommended Requirements
- **CPU**: 2 cores
- **RAM**: 2GB
- **Storage**: 2GB
- **Network**: Stable internet connection

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONPATH` | Python path | `/app` |
| `PYTHONUNBUFFERED` | Python output buffering | `1` |
| `PYTHONHASHSEED` | Python hash seed | `random` |
| `WATCHTOWER_ARCHITECTURE` | System architecture | `new_two_level_classification` |
| `WATCHTOWER_VERSION` | Application version | `2.0.0` |

### Database Configuration

The application requires a PostgreSQL database with the following tables:
- `monitored_feeds`
- `monitor_rules`
- `monitor_rules_logs`
- `monitor_conditions`
- `action_executors`

## 🐳 Docker Configuration

### Dockerfile Features

- **Base Image**: Python 3.11-slim
- **Security**: Non-root user
- **Optimization**: Multi-stage build
- **Health Check**: Automatic monitoring
- **Logging**: Access logs enabled

### Docker Compose Services

```yaml
services:
  watchtower-ai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    volumes:
      - ./config.py:/app/config.py:ro
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📊 Monitoring & Health Checks

### Health Endpoint

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "watchtower-ai-new-classification",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Logs

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f watchtower-ai

# View last 50 lines
docker-compose logs --tail=50
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptoms**: Application fails to start, database errors in logs

**Solution**:
```bash
# Check database connectivity
docker-compose exec watchtower-ai python -c "
from database.db_connection import DatabaseConnection
db = DatabaseConnection()
db.test_connection()
"
```

#### 2. Ollama Connection Issues

**Symptoms**: LLM-related errors, response type detection failures

**Solution**:
- Ensure Ollama is running and accessible
- Check network connectivity
- Verify Ollama model is installed

#### 3. Memory Issues

**Symptoms**: Container restarts, out of memory errors

**Solution**:
```yaml
# Increase memory limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 1G
```

### Performance Tuning

#### 1. Worker Configuration

```bash
# Increase workers for better performance
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 2. Database Connection Pool

Edit `database/db_connection.py`:
```python
# Increase connection pool size
pool_size = 20
max_overflow = 30
```

## 🔒 Security Considerations

### Production Security

1. **Use Environment Variables** for sensitive data
2. **Enable HTTPS** with reverse proxy
3. **Restrict Network Access** with firewalls
4. **Regular Updates** of base images
5. **Monitor Logs** for suspicious activity

### Example Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  watchtower-ai:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OLLAMA_URL=${OLLAMA_URL}
    volumes:
      - ./logs:/app/logs
    networks:
      - internal
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - watchtower-ai
    networks:
      - internal
      - external

networks:
  internal:
    driver: bridge
  external:
    driver: bridge
```

## 📈 Scaling

### Horizontal Scaling

```bash
# Scale to multiple instances
docker-compose up -d --scale watchtower-ai=3
```

### Load Balancing

Use nginx or HAProxy for load balancing:

```nginx
upstream watchtower {
    server watchtower-ai:8000;
    server watchtower-ai:8001;
    server watchtower-ai:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://watchtower;
    }
}
```

## 🔄 Updates & Maintenance

### Updating the Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
./deploy.sh
```

### Backup Strategy

```bash
# Backup database
pg_dump your_database > backup.sql

# Backup logs
tar -czf logs_backup.tar.gz logs/
```

### Monitoring

Recommended monitoring tools:
- **Prometheus** + **Grafana** for metrics
- **ELK Stack** for log aggregation
- **Health checks** for availability

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Verify configuration: `docker-compose config`
3. Test connectivity: `curl http://localhost:8000/health`
4. Review system resources: `docker stats`

## 📝 Changelog

### Version 2.0.0
- ✅ New two-level classification system
- ✅ Enhanced response formatting (Table, Chart, Text)
- ✅ Production-ready Docker configuration
- ✅ Comprehensive health checks
- ✅ Resource limits and monitoring
- ✅ Security improvements
