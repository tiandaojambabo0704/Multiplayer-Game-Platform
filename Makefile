.PHONY: install server developer player tests testc help

help:
	@echo "Available commands:"
	@echo "  make install     install requirements"
	@echo "  make server      open server"
	@echo "  make dev         developer mode"
	@echo "  make play        player mode"
	@echo "  make tests       test local server"
	@echo "  make testc       test local client"

install:
	pip install -r requirements.txt

server:
	cd server && python server.py

dev:
	cd developer && python developer_client.py

developer:
	cd developer && python developer_client.py

play:
	cd player && python player_client.py

player:
	cd player && python player_client.py

tests:
	cd developer/games/tic_tac_toe && python server.py

testc:
	cd developer/games/tic_tac_toe && python client.py