import os
import yaml
from pathlib import Path
import logging

class Config:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.CONFIG_FILE = os.path.join(self.BASE_DIR, 'config.yml')
        self.DATABASE_FILE = os.path.join(self.BASE_DIR, 'data', 'questions.db')
        self.CACHE_DIR = os.path.join(self.BASE_DIR, 'data', 'cache')

        # 加载配置文件
        self._load_config()

        # 确保必要的目录存在
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        os.makedirs(self.LOG_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.DATABASE_FILE), exist_ok=True)

    def init_app(self, app):
        """初始化应用配置"""
        # 确保必要的目录存在
        for directory in [self.CACHE_DIR, self.LOG_DIR, os.path.dirname(self.DATABASE_FILE)]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # 设置 Flask 应用配置
        app.config['SECRET_KEY'] = self.SECRET_KEY
        app.config['DEBUG'] = self.DEBUG
        app.config['DATABASE_FILE'] = self.DATABASE_FILE
        app.config['CACHE_DIR'] = self.CACHE_DIR
        app.config['LOG_DIR'] = self.LOG_DIR

    def _load_config(self):
        """加载配置文件"""
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 基础配置
        self.SECRET_KEY = config['base']['secret_key']

        # 用户配置
        users_config = config.get('users', {})
        self.SUPERADMIN_USERNAME = users_config.get('superadmin', 'yangao')

        # 日志配置
        logging_config = config.get('logging', {})
        self.LOG_LEVEL = logging_config.get('level', 'INFO')
        self.LOG_FORMAT = logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.LOG_DIR = os.path.join(self.BASE_DIR, logging_config.get('directory', 'logs'))
        self.LOG_FILE = os.path.join(self.LOG_DIR, logging_config.get('file', 'app.log'))

        # 爬虫配置
        scraper_config = config['scraper']
        self.SCRAPER_BASE_URL = scraper_config['base_url']
        self.SCRAPER_HEADERS = scraper_config['headers']
        self.SCRAPER_REQUEST_TIMEOUT = scraper_config.get('request_timeout', 10)
        self.SCRAPER_DELAY = scraper_config.get('delay', 1)
        self.SCRAPER_QUESTION_TYPE = scraper_config.get('question_type', 'A')

        # 题库配置
        questions_config = config['questions']
        self.QUESTIONS_PER_PAGE = questions_config['per_page']
        self.AUTO_NEXT_DELAY = questions_config['auto_next_delay']

        # 缓存配置
        cache_config = config['cache']
        self.CACHE_ENABLED = cache_config['enabled']
        self.CACHE_EXPIRE_DAYS = cache_config['expire_days']

        # 数据库配置
        database_config = config.get('database', {})
        self.CLEAR_DATABASE = database_config.get('clear_database', False)

        # 环境配置
        env = os.getenv('ENV', 'development')
        env_config = config['environments'].get(env, {})
        self.DEBUG = env_config.get('debug', True)
        self.USE_CACHE = env_config.get('use_cache', True)
        self.CONFIRM_UPDATE = env_config.get('confirm_update', False)
        self.CLEAR_DATABASE = env_config.get('clear_database', self.CLEAR_DATABASE)

class ProductionConfig(Config):
    def __init__(self):
        super().__init__()
        env = 'production'
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        env_config = config['environments'][env]
        
        self.DEBUG = env_config['debug']
        self.CONFIRM_UPDATE = env_config['confirm_update']
        # 从环境变量获取密钥
        self.SECRET_KEY = os.getenv('SECRET_KEY', env_config['secret_key'])

class DevelopmentConfig(Config):
    def __init__(self):
        super().__init__()
        env = 'development'
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        env_config = config['environments'][env]
        
        self.DEBUG = env_config['debug']
        self.CONFIRM_UPDATE = env_config['confirm_update']

class TestingConfig(Config):
    def __init__(self):
        super().__init__()
        env = 'testing'
        with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        env_config = config['environments'][env]
        
        self.TESTING = env_config['testing']
        self.DATABASE_FILE = os.path.join(self.BASE_DIR, env_config['database'])

config = {
    'development': DevelopmentConfig(),
    'production': ProductionConfig(),
    'testing': TestingConfig(),
    'default': DevelopmentConfig()
} 