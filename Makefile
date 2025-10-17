.PHONY: clean build

REGISTRY := registry.marx.guide/amb-public
REPO := amb-feedback-bot
VERSION := 1.0.0
LOCAL_LATEST := $(REPO):latest
LOCAL_VERSION := $(REPO):$(VERSION)
REGISTRY_LATEST := $(REGISTRY)/$(REPO):latest
REGISTRY_VERSION := $(REGISTRY)/$(REPO):$(VERSION)

COMPOSE_DEV := -f ./docker-compose.yml

# Image

clean:
	docker rmi $(LOCAL_LATEST)

build:
	docker build --platform linux/amd64 -f ./Dockerfile -t $(LOCAL_LATEST) .

tag:
	docker tag $(LOCAL_LATEST) $(LOCAL_VERSION)
	docker tag $(LOCAL_LATEST) $(REGISTRY_LATEST)
	docker tag $(LOCAL_VERSION) $(REGISTRY_VERSION)

push:
	docker push $(REGISTRY_VERSION)
	docker push $(REGISTRY_LATEST)

stop:
	docker compose $(COMPOSE_DEV) stop && docker-compose $(COMPOSE_DEV) rm -f

start: stop
	docker compose $(COMPOSE_DEV) up -d feedback-bot

# Development Targets

bash:
	docker compose $(COMPOSE_DEV) run -i --rm feedback-bot bash


# Deployment

deploy:
	export $(awk -F= '{output=output" "$1"="$2} END {print output}' .env) && \
	cd ansible && \
	ansible-playbook -i production.yaml deploy.yaml
