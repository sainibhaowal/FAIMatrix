#!/bin/bash
# =============================================================================
# FAIM Development Runner
# =============================================================================
# Run FAIM with production-identical Docker setup for local development.
# All services (Postgres, Redis, Qdrant, API, Web) start together.
#
# Usage:
#   ./dev.sh          - Start all services
#   ./dev.sh build    - Rebuild and start
#   ./dev.sh logs     - View logs
#   ./dev.sh down     - Stop all services
#   ./dev.sh reset    - Stop and remove all data
# =============================================================================

set -e

COMPOSE_FILE="docker-compose.dev.yml"

case "${1:-up}" in
  up|start)
    echo "🚀 Starting FAIM (Production-identical development mode)..."
    docker compose -f $COMPOSE_FILE up -d
    echo ""
    echo "✅ FAIM is running!"
    echo "   API:      http://localhost:8000"
    echo "   Web:      http://localhost:3000"
    echo "   Postgres: localhost:5432"
    echo "   Redis:    localhost:6379"
    echo "   Qdrant:   http://localhost:6333"
    echo ""
    echo "📝 Logs: ./dev.sh logs"
    echo "🛑 Stop: ./dev.sh down"
    ;;

  build)
    echo "🔨 Rebuilding and starting FAIM..."
    docker compose -f $COMPOSE_FILE up --build -d
    echo "✅ FAIM rebuilt and running!"
    ;;

  logs)
    docker compose -f $COMPOSE_FILE logs -f
    ;;

  down|stop)
    echo "🛑 Stopping FAIM..."
    docker compose -f $COMPOSE_FILE down
    echo "✅ FAIM stopped."
    ;;

  reset)
    echo "⚠️  This will delete ALL data (Postgres, Redis, Qdrant)!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      docker compose -f $COMPOSE_FILE down -v
      echo "✅ FAIM stopped and all data removed."
    else
      echo "Cancelled."
    fi
    ;;

  status)
    docker compose -f $COMPOSE_FILE ps
    ;;

  migrate)
    echo "🗄️ Running database migrations..."
    docker compose -f $COMPOSE_FILE exec api alembic upgrade head
    echo "✅ Migrations complete."
    ;;

  shell)
    docker compose -f $COMPOSE_FILE exec api bash
    ;;

  *)
    echo "Usage: ./dev.sh [up|build|logs|down|reset|status|migrate|shell]"
    exit 1
    ;;
esac
