#!/bin/bash

docker run -d --name node-manager --net=host -p 5001:5001 -p 27017:27017 -ti node-manager:latest