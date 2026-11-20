.PHONY: up down logs test bootstrap notebook
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f app

bootstrap:
	python -m scripts.bootstrap

test:
	pytest -q

notebook:
	jupyter notebook notebooks/fleettrack_analysis.ipynb
