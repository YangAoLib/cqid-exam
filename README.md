# CQID 考试系统

一个基于 Flask 的在线考试系统，专门用于业余无线电操作证考试（A/B/C）练习。系统自动从官方题库抓取最新题目，支持在线答题、错题重练、进度记录等功能。

## 功能特点

- 🚀 自动抓取最新无线电考试题库
- 📝 在线答题练习（支持 A/B/C 类）
- 🔄 错题重练功能
- 📊 答题进度记录
- 🎯 针对性练习
- 🌐 多用户支持
- 🔒 管理员功能

## 快速开始

### 方式一：使用 Docker（推荐）

1. 克隆仓库
```bash
git clone git@github.com:YangAoLib/cqid-exam.git
cd cqid-exam
```

2. 创建必要的目录和文件
```bash
# 创建数据和日志目录
mkdir -p data/cache logs

# 复制配置文件
cp config.example.yml config.yml
```

3. 配置环境变量
```bash
# 生成随机密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 将生成的密钥复制到 .env 文件的 SECRET_KEY 中
# 根据需要修改其他配置
```

4. 使用 Docker Compose 启动服务
```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f web
```

### 方式二：传统部署

1. 克隆仓库
```bash
git clone git@github.com:YangAoLib/cqid-exam.git
cd cqid-exam
```

2. 创建并激活虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 配置系统
```bash
# 复制配置文件样例并根据需要修改
cp config.example.yml config.yml
# ⚠️ 特别注意：在生产环境中必须修改 secret_key 和 superadmin 用户名

# 生成随机密钥（可选）
python -c "import secrets; print(secrets.token_hex(32))"
```

5. 运行应用
```bash
# 开发环境
python main.py

# 生产环境（推荐）
pip install gunicorn  # Linux/Mac
pip install waitress  # Windows

# Linux/Mac
gunicorn -w 4 -b 0.0.0.0:5000 main:app

# Windows
waitress-serve --host=0.0.0.0 --port=5000 main:app
```

## 配置说明

### 环境变量配置（.env）

生产环境的配置可以通过环境变量或 .env 文件设置：

```bash
# Flask应用配置
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
PORT=5000

# Gunicorn服务器配置
WORKERS=4                # 建议设置为 CPU 核心数 * 2 + 1
TIMEOUT=120             # 请求超时时间（秒）
MAX_REQUESTS=1000       # 工作进程最大请求数

# 日志配置
LOG_LEVEL=INFO          # 可选：DEBUG, INFO, WARNING, ERROR, CRITICAL

# 数据库配置
CLEAR_DATABASE=false    # 生产环境禁止自动清空数据库

# 题库配置
QUESTIONS_PER_PAGE=50   # 每页显示题目数
AUTO_NEXT_DELAY=2       # 答对后自动跳转延迟（秒）

# 缓存配置
CACHE_ENABLED=true      # 是否启用缓存
CACHE_EXPIRE_DAYS=0     # 缓存过期天数，0表示永不过期
```

### 应用配置（config.yml）

详细的应用配置在 `config.yml` 文件中：

```yaml
base:
  secret_key: 'your-secret-key'  # Flask 密钥

users:
  superadmin: 'change-this-username'  # 超级管理员用户名

logging:
  level: INFO  # 日志级别
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: 'app.log'
  directory: 'logs'

# 更多配置请参考 config.example.yml
```

## 项目结构

```
cqid-exam/
├── main.py           # 应用入口
├── config.py         # 配置加载
├── database.py       # 数据库操作
├── scraper.py        # 题库爬虫
├── quiz.py           # 答题逻辑
├── review.py         # 复习功能
├── templates/        # 页面模板
├── static/           # 静态文件
├── data/            # 数据存储
└── logs/            # 日志文件
```

## 生产环境部署建议

1. 安全配置
- 修改 `SECRET_KEY` 为安全的随机字符串
- 修改超级管理员用户名
- 使用 HTTPS
- 配置防火墙

2. 性能优化
- 调整 Gunicorn 工作进程数（WORKERS）
- 启用缓存
- 配置合适的日志级别

3. 监控
- 使用 Docker 的健康检查
- 配置日志收集
- 设置资源限制

## 开发说明

### 目录说明
- `templates/`: HTML 模板文件
- `static/`: CSS、JavaScript 等静态文件
- `data/`: 数据库和缓存文件
  - `data/cache/`: 题库缓存目录（需要手动创建）
  - `data/questions.db`: SQLite 数据库文件（自动创建）
- `logs/`: 日志文件目录（需要手动创建）
  - `logs/app.log`: 应用程序日志文件
- `config.yml`: 应用配置文件（从 config.example.yml 复制）

### 主要模块
- `main.py`: Flask 应用主程序
- `config.py`: 配置管理
- `database.py`: 数据库操作

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m '添加一些特性'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。 