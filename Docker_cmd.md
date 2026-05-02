# Docker Commands (Production)
This file is for the production stack using:
- `docker-compose.yml`
- profile: `accel` (includes Qdrant)
Run all commands from repo root:
```bash
cd /home/sephi-asi/FAIM
```

## 1) Pull latest infra images
Use this when you want latest Postgres/Redis/Qdrant images.

```bash
docker compose -f docker-compose.yml --profile accel pull postgres redis qdrant
```



## 2) Full build (all app images)
Use this after large changes across backend/frontend/worker.

```bash
docker compose -f docker-compose.yml --profile accel build --pull api worker frontend migrate
```



## 3) Build only what changed
### Backend API only
Use this when you changed backend API code.
```bash
docker compose -f docker-compose.yml --profile accel build api
docker compose -f docker-compose.yml --profile accel up -d --no-deps api
```


### Frontend only
Use this when you changed frontend code.
```bash
docker compose -f docker-compose.yml --profile accel build frontend
docker compose -f docker-compose.yml --profile accel up -d --no-deps frontend
```

### Worker only
Use this when you changed worker/job code.
```bash
docker compose -f docker-compose.yml --profile accel build worker
docker compose -f docker-compose.yml --profile accel up -d --no-deps worker
```

### Migration service only
Use this when migration/DB-layer image changed.
```bash
docker compose -f docker-compose.yml --profile accel build migrate
```

## 4) Run migrations (when schema changed)
Run this after DB model/migration changes and before restarting API/worker.
```bash
docker compose -f docker-compose.yml --profile accel run --rm -e FAIM_AUTO_MIGRATE=true migrate
```

## 5) Start all servers
One command to run everything (postgres, redis, qdrant, api, worker, frontend).
```bash
docker compose -f docker-compose.yml --profile accel up -d
```

## 6) Stop/down all servers
One command to stop and remove all containers in this stack.
```bash
docker compose -f docker-compose.yml --profile accel down
```

## 7) Common safe update flows
### Backend change flow
```bash
docker compose -f docker-compose.yml --profile accel up -d postgres redis qdrant
docker compose -f docker-compose.yml --profile accel build api worker migrate
docker compose -f docker-compose.yml --profile accel run --rm -e FAIM_AUTO_MIGRATE=true migrate
docker compose -f docker-compose.yml --profile accel up -d --no-deps api worker
```

### Frontend change flow
```bash
docker compose -f docker-compose.yml --profile accel build frontend
docker compose -f docker-compose.yml --profile accel up -d --no-deps frontend
```

## 8) Quick checks
```bash
docker compose -f docker-compose.yml --profile accel ps
docker compose -f docker-compose.yml --profile accel logs -f api worker frontend
```

## 9) Hard reset (optional, destructive)
Use only when you want to delete containers, volumes, and start fresh.
```bash
docker compose -f docker-compose.yml --profile accel down -v
docker compose -f docker-compose.yml --profile accel up -d
```
