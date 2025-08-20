.PHONY: help demo up down logs clean run-client setup-auth test

# Default target
help:
	@echo "MLflow Secrets Auth Demo - Available Commands:"
	@echo ""
	@echo "  demo         - Run complete demo (setup + client + open browser)"
	@echo "  up           - Start all services (vault, nginx, mlflow)"
	@echo "  down         - Stop and remove all services"
	@echo "  logs         - Show logs for all services"
	@echo "  run-client   - Run the demo client script"
	@echo "  setup-auth   - Generate auth files (htpasswd)"
	@echo "  test         - Validate demo setup"
	@echo "  clean        - Remove all containers, volumes, and generated files"
	@echo ""
	@echo "URLs:"
	@echo "  MLflow UI:   http://localhost:8080"
	@echo "  Vault UI:    http://localhost:8200"
	@echo ""

# Run the complete demo
demo: setup-auth
	@echo "🚀 Starting MLflow Secrets Auth Demo..."
	@docker-compose up --build -d vault nginx mlflow
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@docker-compose up vault-setup
	@echo "🔧 Running demo client..."
	@docker-compose up --build client
	@echo ""
	@echo "✅ Demo completed! View results at:"
	@echo "   MLflow UI: http://localhost:8080"
	@echo "   Vault UI:  http://localhost:8200"
	@echo ""
	@echo "Use 'make logs' to view service logs"
	@echo "Use 'make down' to stop all services"

# Start all services
up: setup-auth
	@echo "🚀 Starting all services..."
	@docker-compose up --build -d
	@echo "✅ All services started!"
	@echo "   MLflow UI: http://localhost:8080"
	@echo "   Vault UI:  http://localhost:8200"

# Stop all services
down:
	@echo "🛑 Stopping all services..."
	@docker-compose down
	@echo "✅ All services stopped!"

# Show logs for all services
logs:
	@docker-compose logs -f

# Run just the client demo
run-client:
	@echo "🔧 Running demo client..."
	@docker-compose up --build client

# Generate authentication files
setup-auth:
	@echo "🔐 Setting up authentication files..."
	@mkdir -p auth
	@./scripts/htpasswd_gen.sh

# Clean everything
clean:
	@echo "🧹 Cleaning up..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@rm -rf auth/
	@echo "✅ Cleanup completed!"

# Individual service logs
logs-vault:
	@docker-compose logs -f vault

logs-nginx:
	@docker-compose logs -f nginx

logs-mlflow:
	@docker-compose logs -f mlflow

logs-client:
	@docker-compose logs -f client

# Health checks
health:
	@echo "🩺 Checking service health..."
	@echo "Vault:   $$(curl -s http://localhost:8200/v1/sys/health | jq -r '.sealed // "Error"')"
	@echo "MLflow:  $$(curl -s http://localhost:8080/health | jq -r '.status // "Error"')"

# Test setup
test:
	@echo "🧪 Testing demo stack setup..."
	@./scripts/test_setup.sh
