.PHONY: sql-console

sql-console:
	docker compose exec penny python -m sqlite3 /app/data/penny.db
