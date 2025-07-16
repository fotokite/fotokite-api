.PHONY: run_system_info
dest = .
action = "info"

check: lint test

format:
	poetry run ruff check --select I --fix $(dest)
	poetry run ruff format $(dest)

fix-checks:
	poetry run ruff check --fix $(dest)

lint-format:
	poetry run ruff format --check $(dest)

lint-checks:
	poetry run ruff check $(dest)

lint-types:
	poetry run mypy --soft-error-limit=-1 .

lint: lint-format lint-checks lint-types

run_system:
	poetry install
	poetry run python -m fotokite_api.system.system --action=$(action)

run_flight:
	poetry install
	poetry run python -m fotokite_api.flight.flight --action=$(action)

run_notifications:
	poetry install
	poetry run python -m fotokite_api.notifications.notifications --action=$(action)

run_demo_flight:
	poetry install
	poetry run python -m fotokite_api.demo_flight

run_ffmpeg_streamer:
	poetry install
	poetry run python -m fotokite_api.streamer.ffmpeg

run_gstreamer_streamer:
	poetry install
	poetry run python -m fotokite_api.streamer.gstreamer
