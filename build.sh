#!/usr/bin/env bash
sudo docker compose build --no-cache
sudo docker compose down
sudo docker compose up -d
sleep 5
sudo docker logs api-monitizer
sudo docker logs nginx
