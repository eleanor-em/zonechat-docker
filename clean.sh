#!/bin/bash
sudo docker stop zonechat
sudo docker rm zonechat
sudo docker rmi zonechat
sudo docker volume rm zonechat-data
