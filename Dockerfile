FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    WORKERS=4 \
    TIMEOUT=120 \
    MAX_REQUESTS=1000

# 创建必要的目录
RUN mkdir -p /app/data/cache /app/logs

# 复制项目文件
COPY requirements.txt .
RUN pip install -i https://mirror.nju.edu.cn/pypi/web/simple --no-cache-dir -r requirements.txt \
    && pip install -i https://mirror.nju.edu.cn/pypi/web/simple --no-cache-dir gunicorn

COPY . .

# 暴露端口
EXPOSE 5000

# 使用gunicorn启动
CMD ["sh", "-c", "gunicorn --workers ${WORKERS} --timeout ${TIMEOUT} --max-requests ${MAX_REQUESTS} --bind 0.0.0.0:5000 --access-logfile - --error-logfile - main:app"] 