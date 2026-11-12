# Service Health Check Endpoints

All services in the DesignSynapse platform implement standardized health check endpoints for monitoring and orchestration.

## Endpoints

### `/health` - Liveness Probe

**Purpose**: Basic health check that returns service status without checking dependencies.

**Use Case**: Container orchestration liveness probes (Kubernetes, Docker Swarm, etc.)

**Response Format**:
```json
{
  "status": "healthy",
  "service": "service-name",
  "version": "1.0.0"
}
```

**HTTP Status**: Always returns `200 OK` if the service is running.

**Characteristics**:
- Fast response (no external dependencies checked)
- Should always succeed if the service process is running
- Used to determine if the container should be restarted

---

### `/ready` - Readiness Probe

**Purpose**: Comprehensive readiness check that verifies the service can accept requests.

**Use Case**: Container orchestration readiness probes to determine if traffic should be routed to the service.

**Response Format**:
```json
{
  "service": "service-name",
  "version": "1.0.0",
  "status": "ready",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    }
  }
}
```

**HTTP Status**: Returns `200 OK` when ready, but may return `200 OK` with `status: "not_ready"` if dependencies fail.

**Characteristics**:
- Checks critical dependencies (database, external services)
- May take longer to respond than `/health`
- Used to determine if the service should receive traffic

---

## Service-Specific Checks

### User Service

**Endpoints**: `/health`, `/ready`

**Readiness Checks**:
- ✅ Database connectivity (PostgreSQL)

**Example**:
```bash
# Health check
curl http://localhost:8001/health

# Readiness check
curl http://localhost:8001/ready
```

---

### Project Service

**Endpoints**: `/health`, `/ready`

**Readiness Checks**:
- ✅ Database connectivity (PostgreSQL)

**Example**:
```bash
# Health check
curl http://localhost:8003/health

# Readiness check
curl http://localhost:8003/ready
```

---

### Knowledge Service

**Endpoints**: `/health`, `/ready`

**Readiness Checks**:
- ✅ Database connectivity (PostgreSQL)
- ✅ Pinecone API configuration status
- ✅ OpenAI API configuration status

**Example**:
```bash
# Health check
curl http://localhost:8002/health

# Readiness check
curl http://localhost:8002/ready
```

**Note**: External service checks (Pinecone, OpenAI) only verify configuration, not actual connectivity, to avoid rate limiting on health checks.

---

## Kubernetes Configuration Example

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: user-service
spec:
  containers:
  - name: user-service
    image: user-service:latest
    ports:
    - containerPort: 8001
    livenessProbe:
      httpGet:
        path: /health
        port: 8001
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /ready
        port: 8001
      initialDelaySeconds: 15
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
```

---

## Docker Compose Configuration Example

```yaml
version: '3.8'
services:
  user-service:
    image: user-service:latest
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## Monitoring Integration

### Prometheus

Health check endpoints can be monitored using Prometheus with the `blackbox_exporter`:

```yaml
scrape_configs:
  - job_name: 'health-checks'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
        - http://user-service:8001/health
        - http://project-service:8003/health
        - http://knowledge-service:8002/health
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
```

### Uptime Monitoring

Services like UptimeRobot, Pingdom, or StatusCake can monitor the `/health` endpoint for uptime tracking.

---

## Best Practices

1. **Liveness Probe (`/health`)**:
   - Should be lightweight and fast
   - Should not check external dependencies
   - Should only fail if the service needs to be restarted

2. **Readiness Probe (`/ready`)**:
   - Should check all critical dependencies
   - Can take longer to respond
   - Should fail if the service cannot handle requests

3. **Timeouts**:
   - Set appropriate timeouts for health checks
   - Readiness checks may need longer timeouts than liveness checks

4. **Failure Thresholds**:
   - Configure appropriate failure thresholds to avoid false positives
   - Consider using different thresholds for liveness vs readiness

5. **Startup Time**:
   - Set `initialDelaySeconds` to account for service startup time
   - Consider using `startupProbe` in Kubernetes for slow-starting services

---

## Troubleshooting

### Service Not Ready

If `/ready` returns `status: "not_ready"`, check the `checks` object for details:

```json
{
  "status": "not_ready",
  "checks": {
    "database": {
      "status": "unhealthy",
      "message": "Database connection failed: connection refused"
    }
  }
}
```

**Common Issues**:
- Database not running or not accessible
- Incorrect database credentials
- Network connectivity issues
- External service API keys not configured

### Service Not Healthy

If `/health` fails or returns errors:
- Check service logs for errors
- Verify the service process is running
- Check for resource constraints (CPU, memory)
- Verify network connectivity to the service

---

## Implementation Details

All health check endpoints are implemented in the `main.py` file of each service:

- **User Service**: `apps/user-service/src/main.py`
- **Project Service**: `apps/project-service/src/main.py`
- **Knowledge Service**: `apps/knowledge-service/knowledge_service/main.py`

The endpoints use FastAPI's route decorators and return JSON responses with appropriate status codes.
