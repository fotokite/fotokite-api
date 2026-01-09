.PHONY: check format fix-checks lint-format lint-checks lint-types lint run_system run_flight run_notifications run_camera run_demo_flight run_demo_sequential run_ffmpeg_streamer run_gstreamer_streamer
dest = .
action = "info"
secret = ""
secret_type = "token"

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
	poetry run python -m fotokite_api.system.system --action=$(action) --secret=$(secret) --secret_type=$(secret_type)

run_flight:
	poetry install
	poetry run python -m fotokite_api.flight.flight --action=$(action) --secret=$(secret) --secret_type=$(secret_type)

run_notifications:
	poetry install
	poetry run python -m fotokite_api.notifications.notifications --action=$(action) --secret=$(secret) --secret_type=$(secret_type)

run_camera:
	poetry install
	poetry run python -m fotokite_api.camera.camera --action=$(action) --secret=$(secret) --secret_type=$(secret_type)

run_demo_flight:
	poetry install
	poetry run python -m fotokite_api.demo_flight --secret=$(secret) --secret_type=$(secret_type)

run_demo_sequential:
	poetry install
	poetry run python -m fotokite_api.demo_sequential --secret=$(secret) --secret_type=$(secret_type)

run_ffmpeg_streamer:
	poetry install
	poetry run python -m fotokite_api.streamer.ffmpeg

run_gstreamer_streamer:
	poetry install
	poetry run python -m fotokite_api.streamer.gstreamer
