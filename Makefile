.PHONY: all build clean extract train ollama run test deploy-worker

all: extract train ollama build

build:
	./build.sh release

debug:
	./build.sh debug

extract:
	python3 engine/extract_turns.py

train:
	python3 engine/train_lora.py --speaker Eugenio --epochs 5

ollama:
	python3 engine/ollama_adapter.py --speaker Eugenio --test

run: build
	open Mimo.app

test:
	python3 -m unittest discover -s tests -p "test_*.py"

deploy-worker:
	cd worker && npx wrangler deploy
