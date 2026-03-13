#!/bin/bash
docker build -t iaanalyzer .
docker-compose down && docker-compose up -d