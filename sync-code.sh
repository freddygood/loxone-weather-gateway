#!/usr/bin/env sh -x

rsync -av --delete --exclude=venv --exclude="*.pyc" ./ pi:loxone-weather-gateway/
