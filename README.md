# GodsEye - Google AI Mode Scraper Microservices

## Architecture Overview

This project refactors a single-file Python scraper into a robust, scalable microservices architecture capable of handling 10,000+ concurrent requests.

### Services

- **Gateway Service (Go)**: High-performance REST API using Fiber framework
- **Message Broker (RabbitMQ)**: Job queue for decoupling API from workers
- **Worker Service (Python)**: Scalable Python workers executing scraping logic
- **PostgreSQL**: Database for job tracking and results

### Phase 1: Infrastructure Setup ✅

Created the foundational infrastructure:

- ✅ `docker-compose.yml` with all services configured
- ✅ Folder structure: `./gateway/`, `./worker/`, `./shared/`
- ✅ Infrastructure health check script (`check_infra.py`)
- ✅ Test script (`test_phase_1.ps1`)

### Service Configuration

- **RabbitMQ**: Management UI available at http://localhost:15672 (admin/admin123)
- **PostgreSQL**: localhost:5432 (postgres/postgres123)
- **API Gateway**: Will be available at http://localhost:8080
- **Worker Nodes**: 3 replicas by default

### Testing Phase 1

Run the infrastructure test:

```powershell
# On Windows
powershell -ExecutionPolicy Bypass -File test_phase_1.ps1

# Or manually:
docker-compose up -d
pip install psycopg2-binary pika
python check_infra.py
```

### Next Phases

- **Phase 2**: Implement Go API Gateway
- **Phase 3**: Implement Python Worker Service
- **Phase 4**: Integration and Load Testing

### Project Structure

```
├── docker-compose.yml          # Infrastructure definition
├── check_infra.py             # Health check script
├── test_phase_1.ps1           # Test script
├── gateway/                   # Go API Gateway
│   └── Dockerfile
├── worker/                    # Python Worker Service
│   ├── Dockerfile
│   └── requirements.txt
├── shared/                    # Shared configurations
└── main.py                    # Original scraper (reference)
```
