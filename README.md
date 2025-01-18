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

### 环境要求

- Python 3.8+
- SQLite 3
- pip

### 安装步骤

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
python main.py
```

访问 http://localhost:5000 开始使用。

## 配置说明

配置文件 `config.yml` 包含以下主要部分：

### 基础配置
```yaml
base:
  secret_key: 'your-secret-key'  # Flask 密钥，用于：
                                # 1. 会话加密
                                # 2. 保护表单免受 CSRF 攻击
                                # 3. 用户会话安全
                                # 建议使用随机字符串，在生产环境中必须修改
```

### 用户配置
```yaml
users:
  superadmin: 'yangao'  # 超级管理员用户名
                       # ⚠️ 安全警告：在生产环境中必须修改此用户名
                       # 默认用户名仅用于开发环境，使用默认值可能导致安全风险
```

### 日志配置
```yaml
logging:
  level: INFO  # 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: 'app.log'  # 日志文件名
  directory: 'logs'  # 日志目录
```

### 爬虫配置
```yaml
scraper:
  base_url: "https://www.cqid.cn/all/"
  question_type: "A"  # 题目类型：A/B/C
  request_timeout: 10
  delay: 2
```

### 缓存配置
```yaml
cache:
  enabled: true
  expire_days: 0  # 0或-1表示永不过期
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

## 开发说明

### 目录说明
- `templates/`: HTML 模板文件
- `static/`: CSS、JavaScript 等静态文件
- `data/`: 数据库和缓存文件
- `logs/`: 日志文件

### 主要模块
- `main.py`: Flask 应用主程序
- `config.py`: 配置管理
- `database.py`: 数据库操作
- `scraper.py`: 题库爬虫
- `quiz.py`: 答题功能
- `review.py`: 复习功能

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