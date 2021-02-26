#!/bin/bash

DISCORD_BOT_SECRET=mysecret

if [ $DISCORD_BOT_SECRET == "mysecret" ]; then
    echo "Must set secret first!"
    exit
fi

cd src

HAS_IMAGE=`sudo docker images | grep zonechat | wc -l`
HAS_VOLUME=`sudo docker volume ls | grep zonechat-data | wc -l`
HAS_CONTAINER=`sudo docker container ls | grep zonechat | wc -l`

if [ $HAS_IMAGE -eq 0 ]; then
    echo "Building image..."
    sudo docker build -t zonechat .
fi
if [ $HAS_VOLUME -eq 0 ]; then
    echo "Creating volume..."
    sudo docker volume create zonechat-data
fi
if [ $HAS_VOLUME -ne 0 ]; then
    echo "Removing existing container..."
    sudo docker rm --force zonechat
fi

sudo docker run -v zonechat-data:/data -e DISCORD_BOT_SECRET=$DISCORD_BOT_SECRET --name zonechat -d zonechat
