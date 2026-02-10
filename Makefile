PYTHON?=python3
PIP?=pip3

install:
	$(PIP) install -r requirements.txt

run:
	uvicorn app.main:create_app --factory --reload

run-pytest:
	pytest

lint-python:
	flake8 .

fmt-python:
	black . $(ARGS) --target-version py311

docker-build:
	docker build -t gc-signin-admin-site-ci-build ./
