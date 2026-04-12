# Bybit AI Swing Trader - Production Deployment Guide

## 🚀 Quick Start

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd bybit-ai-swing-trader

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend
```

### Access Points
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090

## 📋 Prerequisites

### System Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB disk space

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=postgresql://trader:password@postgres:5432/bybit_trader

# Bybit API (Testnet)
BYBIT_API_KEY=your_testnet_api_key
BYBIT_API_SECRET=your_testnet_api_secret
BYBIT_TESTNET=true

# Security
SECURITY_SECRET_KEY=your-256-bit-secret-key
SECURITY_RATE_LIMIT_REQUESTS_PER_MINUTE=60

# Monitoring
GRAFANA_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │────│  React Frontend │────│ FastAPI Backend │
│   (Port 80)     │    │   (Port 3000)   │    │   (Port 8000)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   PostgreSQL   │
                    │   (Port 5432)  │
                    └─────────────────┘
                             │
                    ┌─────────────────┐
                    │     Redis       │
                    │   (Port 6379)  │
                    └─────────────────┘
                             │
               ┌─────────────┴─────────────┐
               │                          │
      ┌─────────────────┐        ┌─────────────────┐
      │   Prometheus    │        │    Grafana     │
      │   (Port 9090)  │        │   (Port 3001)  │
      └─────────────────┘        └─────────────────┘
```

## 🔧 Configuration

### Database Configuration
The application uses PostgreSQL with connection pooling. Default settings:
- **Host**: postgres
- **Port**: 5432
- **Database**: bybit_trader
- **User**: trader
- **Password**: password

### Redis Configuration
Used for caching and session management:
- **Host**: redis
- **Port**: 6379
- **Password**: Configurable via REDIS_PASSWORD

### Security Settings
- **Rate Limiting**: 60 requests/minute per IP
- **CORS**: Configured for frontend domain
- **Security Headers**: HSTS, CSP, X-Frame-Options enabled

## 📊 Monitoring & Metrics

### Prometheus Metrics
Available at `/metrics` endpoint:
- HTTP request/response metrics
- Database connection pool stats
- Application performance metrics
- Error rates and latency

### Grafana Dashboards
Pre-configured dashboards include:
- Application Performance
- Database Metrics
- API Response Times
- Error Rates

### Health Checks
- **Application**: `/health` endpoint
- **Database**: Automatic connection validation
- **Docker**: Container health checks

## 🔍 API Documentation

### Core Endpoints

#### Trading Signals
```bash
GET /api/signals/{symbol}
POST /api/signals/{symbol}
```

#### Backtesting
```bash
POST /api/backtest
GET /api/backtests
GET /api/backtests/{id}
```

#### ML Models
```bash
POST /api/ml/train-universal
GET /api/ml/models
```

#### Statistics
```bash
GET /api/stats
```

### Authentication
Currently uses API key authentication. Configure in environment variables.

## 🧪 Testing

### Run Tests
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest --cov=backend --cov-report=html
```

### Test Database
Tests use SQLite in-memory database for speed and isolation.

## 🚦 Deployment Modes

### Development Mode
```bash
docker-compose up -d
```

### Production Mode
```bash
docker-compose --profile production up -d
```

### Scaling
```bash
# Scale backend workers
docker-compose up -d --scale backend=3

# Scale database
docker-compose up -d postgres
```

## 🔧 Maintenance

### Database Backup
```bash
# Backup PostgreSQL
docker exec -t bybit-postgres pg_dump -U trader bybit_trader > backup.sql

# Restore
docker exec -i bybit-postgres psql -U trader bybit_trader < backup.sql
```

### Log Management
```bash
# View logs
docker-compose logs backend
docker-compose logs postgres

# Follow logs
docker-compose logs -f backend
```

### Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check database status
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up -d postgres
```

#### Application Won't Start
```bash
# Check application logs
docker-compose logs backend

# Check environment variables
docker-compose exec backend env

# Check health endpoint
curl http://localhost:8000/health
```

#### High Memory Usage
- Monitor with Grafana dashboards
- Check database connection pool settings
- Consider Redis cache configuration

### Performance Tuning

#### Database
- Adjust connection pool size in `DATABASE_POOL_SIZE`
- Enable query logging for optimization
- Consider database indexing

#### Application
- Increase worker count for high load
- Adjust rate limiting for API usage
- Configure Redis for caching

## 🔒 Security Considerations

### Production Deployment
- Change all default passwords
- Use strong SECRET_KEY (256-bit)
- Enable HTTPS with SSL certificates
- Configure firewall rules
- Regular security updates

### API Security
- Rate limiting protects against abuse
- Input validation prevents injection attacks
- CORS configuration limits cross-origin requests
- Security headers prevent common attacks

## 📈 Scaling Strategy

### Horizontal Scaling
- Add more backend workers with `--scale backend=N`
- Use load balancer for multiple instances
- Database read replicas for read-heavy workloads

### Vertical Scaling
- Increase container resource limits
- Upgrade database instance size
- Add Redis cluster for caching

### Monitoring Scaling
- Prometheus federation for multi-region
- Grafana with multiple data sources
- Alert manager for incident response

## 📞 Support

### Logs Location
- Application logs: `./backend/logs/`
- Docker logs: `docker-compose logs`
- Database logs: Container logs

### Health Checks
- Application health: `http://localhost:8000/health`
- Database health: PostgreSQL connection status
- Redis health: `redis-cli ping`

### Backup Strategy
- Daily database backups
- Model checkpoints saved to disk
- Configuration files version controlled

---

## 🎯 Performance Benchmarks

### Baseline Performance (Development)
- **API Response Time**: <100ms average
- **Database Queries**: <50ms average
- **Memory Usage**: <512MB per worker
- **Concurrent Users**: 100+ supported

### Production Targets
- **API Response Time**: <200ms P95
- **Database Queries**: <100ms P95
- **Uptime**: 99.9% SLA
- **Error Rate**: <0.1%

---

*This documentation is continuously updated. Check git history for latest changes.*