#!/bin/bash

# 获取当前用户的UID和GID
export USER_UID=$(id -u)
export USER_GID=$(id -g)

# 停止并删除现有容器
docker compose down

# 重新构建并启动容器
docker compose up -d

# 显示容器日志
docker compose logs -f 