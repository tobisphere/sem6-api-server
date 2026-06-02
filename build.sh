#!/usr/bin/env bash
sudo docker compose build --no-cache
sudo docker compose down
sudo docker rmi api-monitizer 2>/dev/null || sudo docker rmi $(sudo docker images -q api-monitizer)
sudo docker image prune -f
sudo docker compose up -d
sleep 5
sudo docker logs api-monitizer
sudo docker logs nginx
