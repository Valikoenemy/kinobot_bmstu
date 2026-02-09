SHELL:=/bin/bash

DOCKER:=docker

REQUIREMENTS:=./requirements.txt
VENVDIR:=./venv
COMPOSE_FILE:=./deployment/docker-compose.yaml

start:
	source $(VENVDIR)/bin/activate && \
	python3 ./main.py

init-venv:
	python3 -m venv $(VENVDIR)
	$(VENVDIR)/bin/pip install -r $(REQUIREMENTS)
	
up:
	$(DOCKER) compose -f $(COMPOSE_FILE) up -d 

upd:
	$(DOCKER) compose -f $(COMPOSE_FILE) up -d --build 

upda: 
	$(DOCKER) compose -f $(COMPOSE_FILE) up --build 

down:
	$(DOCKER) compose -f $(COMPOSE_FILE) down

.PHONY: requirements
requirements:
	$(VENVDIR)/bin/pip freeze > $(REQUIREMENTS)
