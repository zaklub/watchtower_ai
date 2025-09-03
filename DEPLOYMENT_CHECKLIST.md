# 🚀 Watchtower AI Deployment Checklist

## Pre-Deployment Checklist

### ✅ Prerequisites
- [ ] Docker Desktop installed and running
- [ ] Docker Compose available
- [ ] At least 2GB RAM available
- [ ] PostgreSQL database accessible
- [ ] Internet connection for Ollama

### ✅ Configuration
- [ ] Database connection configured in `config.py`
- [ ] Environment variables set (if needed)
- [ ] Logs directory created (auto-created by script)

### ✅ Files Ready
- [ ] `Dockerfile` - Production optimized
- [ ] `docker-compose.yml` - Resource limits set
- [ ] `requirements.txt` - Pinned versions
- [ ] `deploy.sh` / `deploy.bat` - Deployment scripts
- [ ] `DEPLOYMENT.md` - Complete guide

## Deployment Steps

### 1. Quick Deploy
```bash
# Linux/Mac
./deploy.sh

# Windows
deploy.bat
```

### 2. Manual Deploy
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Verify Deployment
```bash
# Health check
curl http://localhost:8000/health

# API test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all rules"}'
```

## Post-Deployment Checklist

### ✅ Service Health
- [ ] Container running: `docker-compose ps`
- [ ] Health endpoint responding: `curl http://localhost:8000/health`
- [ ] API responding: Test with sample query
- [ ] Logs clean: `docker-compose logs --tail=20`

### ✅ Performance
- [ ] Response times acceptable (< 5 seconds)
- [ ] Memory usage reasonable (< 80% of limit)
- [ ] CPU usage stable
- [ ] Database connections working

### ✅ Security
- [ ] Non-root user running container
- [ ] No sensitive data in logs
- [ ] Resource limits enforced
- [ ] Health checks passing

## Troubleshooting

### Common Issues
- **Database Connection**: Check `config.py` settings
- **Ollama Issues**: Ensure Ollama service accessible
- **Memory Issues**: Increase limits in `docker-compose.yml`
- **Port Conflicts**: Change port in `docker-compose.yml`

### Useful Commands
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f watchtower-ai

# Restart service
docker-compose restart watchtower-ai

# Stop all services
docker-compose down

# Clean up
docker-compose down --volumes --remove-orphans
```

## Monitoring

### Health Checks
- **Endpoint**: `http://localhost:8000/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

### Logs
- **Location**: `./logs/` directory
- **Rotation**: Automatic via Docker
- **Level**: INFO and above

### Metrics
- **Memory**: Monitor via `docker stats`
- **CPU**: Monitor via `docker stats`
- **Network**: Monitor via `docker stats`

## Scaling

### Horizontal Scaling
```bash
# Scale to 3 instances
docker-compose up -d --scale watchtower-ai=3
```

### Vertical Scaling
Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2.0'
```

## Backup

### Database Backup
```bash
# PostgreSQL backup
pg_dump your_database > backup_$(date +%Y%m%d).sql
```

### Application Backup
```bash
# Config backup
cp config.py config_backup_$(date +%Y%m%d).py

# Logs backup
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

---

**🎯 Deployment Complete! Your Watchtower AI is now running in production.**
