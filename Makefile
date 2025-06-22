# Makefile para gestión del proyecto
.PHONY: help up down logs build clean status shell

# Ayuda por defecto
help:
	@echo "Comandos disponibles:"
	@echo "  make up      - Iniciar todos los servicios"
	@echo "  make down    - Detener todos los servicios"
	@echo "  make logs    - Ver logs en tiempo real"
	@echo "  make build   - Reconstruir contenedores"
	@echo "  make clean   - Limpiar todo (incluyendo volúmenes)"
	@echo "  make status  - Ver estado de los servicios"
	@echo "  make shell   - Entrar al contenedor del backend"

# Iniciar servicios
up:
	docker compose up -d
	@echo "\n✅ Servicios iniciados:"
	@echo "   - Frontend: http://localhost"
	@echo "   - Backend: http://localhost:2690/docs"
	@echo "   - ChromaDB: http://localhost:8050"

# Detener servicios
down:
	docker compose down

# Ver logs
logs:
	docker compose logs -f

# Reconstruir
build:
	docker compose build --no-cache

# Limpiar todo
clean:
	docker compose down -v
	docker system prune -a -f

# Estado
status:
	docker compose ps

# Shell del backend
shell:
	docker compose exec backend bash