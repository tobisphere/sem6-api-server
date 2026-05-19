#!/usr/bin/env bash
sudo docker compose build --no-cache
sudo docker compose down
sudo docker compose up -d
sleep 5
sudo docker logs fastapi
sudo docker logs nginx
