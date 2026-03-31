.PHONY: check format fix-checks lint-format lint-checks lint-types lint run_system run_flight run_notifications run_camera run_demo_flight run_demo_sequential run_ffmpeg_streamer run_gstreamer_streamer run_tls test_tls build_tls_image run_docker_tls_test
dest = .
action = "info"
secret = ""
secret_type = "token"
public_key = "" # Example TXGEHuBaJE31UETqrgHYCLD2FgiKndLVhfvz64uv6/I=
IMAGE_NAME = fotokite-api-tls-test
gs_ip = 192.168.2.100
gs_name = "" # Example: "g2211ZR"
hostname = $(gs_name).sigma.fotokite-system.com

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

run_tls:
	poetry install
	poetry run python -m fotokite_api.tls.tls --action=$(action) --secret=$(secret) --secret_type=$(secret_type) --hostname=${gs_name} --public_key=${public_key}

test_tls: build_tls_image
	@echo "Running TLS Tests"

	@echo "\nVerifying Present Day Connectivity using Hostname... Expected: Success"
	$(MAKE) run_docker_tls_test action=hostname FAKETIME="" public_key=""

	@echo "\nVerifying Future Day Connectivity using Hostname... Expected: Failure"
	$(MAKE) run_docker_tls_test action=hostname FAKETIME="+2y" public_key=""

	@echo "\nVerifying Past Day Connectivity using Hostname... Expected: Failure"
	$(MAKE) run_docker_tls_test action=hostname FAKETIME="-2y" public_key=""

	@echo "\nVerifying Present Day Connectivity using Pinned Key... Expected: Success"
	$(MAKE) run_docker_tls_test action=pinned_key FAKETIME="" public_key=$(public_key)

	@echo "\nVerifying Future Day Connectivity using Pinned Key... Expected: Success"
	$(MAKE) run_docker_tls_test action=pinned_key FAKETIME="+2y" public_key=$(public_key)

	@echo "\nVerifying Past Day Connectivity using Pinned Key... Expected: Success"
	$(MAKE) run_docker_tls_test action=pinned_key FAKETIME="-2y" public_key=$(public_key)
	@echo "\nVerifying Present Day Connectivity using Invalid Pinned Key... Expected: Failure"
	$(MAKE) run_docker_tls_test action=pinned_key FAKETIME="" public_key="INVALID_PUBLIC_KEY"

build_tls_image:
	@docker build -t $(IMAGE_NAME) -f Dockerfile.test .

run_docker_tls_test:
	@echo "Running TLS Test with Action: $(action), FAKETIME: $(FAKETIME), PUBLIC_KEY: $(public_key) hostname: $(hostname) and IP: $(gs_ip)"
	@docker run --rm \
		--add-host=$(hostname):$(gs_ip) \
		$(if $(FAKETIME),-e FAKETIME="$(FAKETIME)",) \
		$(IMAGE_NAME) \
		poetry run python -m fotokite_api.tls.tls --action="$(action)" --secret=$(secret) --secret_type=$(secret_type) --hostname=$(gs_name) --public_key=$(public_key)
