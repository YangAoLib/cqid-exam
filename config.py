import os
import yaml
from pathlib import Path
import logging
import secrets

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
        app.config['QUESTIONS_PER_PAGE'] = self.QUESTIONS_PER_PAGE

    def _get_env_value(self, key, default=None, config_value=None, required=False):
        """从环境变量获取配置值，如果不存在则使用配置文件值或默认值"""
        value = os.getenv(key)
        if value is not None:
            return value
        if config_value is not None:
            return config_value
        if required and default is None:
            raise ValueError(f"必须设置环境变量 {key} 或在配置文件中提供相应的值")
        return default

    def _load_config(self):
        """加载配置文件"""
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            config = {}
            logging.warning(f"配置文件 {self.CONFIG_FILE} 不存在，使用默认配置")

        # 基础配置
        base_config = config.get('base', {})
        default_secret_key = secrets.token_hex(32)
        self.SECRET_KEY = self._get_env_value('SECRET_KEY', default_secret_key, 
            base_config.get('secret_key'), required=True)

        # 用户配置
        users_config = config.get('users', {})
        self.SUPERADMIN_USERNAME = self._get_env_value('SUPERADMIN_USERNAME', 'admin', 
            users_config.get('superadmin'), required=True)

        # 日志配置
        logging_config = config.get('logging', {})
        self.LOG_LEVEL = self._get_env_value('LOG_LEVEL', 'INFO', 
            logging_config.get('level'))
        self.LOG_FORMAT = self._get_env_value('LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
            logging_config.get('format'))
        self.LOG_DIR = os.path.join(
            self.BASE_DIR, 
            self._get_env_value('LOG_DIR', 'logs', logging_config.get('directory')))
        self.LOG_FILE = os.path.join(
            self.LOG_DIR, 
            self._get_env_value('LOG_FILE', 'app.log', logging_config.get('file')))

        # 爬虫配置
        scraper_config = config.get('scraper', {})
        self.SCRAPER_BASE_URL = self._get_env_value('SCRAPER_BASE_URL', 
            "https://www.cqid.cn/all/", 
            scraper_config.get('base_url'))
        self.SCRAPER_HEADERS = scraper_config.get('headers', {})
        self.SCRAPER_REQUEST_TIMEOUT = int(self._get_env_value('SCRAPER_REQUEST_TIMEOUT', 
            '10', 
            str(scraper_config.get('request_timeout'))))
        self.SCRAPER_DELAY = int(self._get_env_value('SCRAPER_DELAY', 
            '2', 
            str(scraper_config.get('delay'))))
        self.SCRAPER_QUESTION_TYPE = self._get_env_value('SCRAPER_QUESTION_TYPE', 
            'A', 
            scraper_config.get('question_type'))

        # 题库配置
        questions_config = config.get('questions', {})
        self.QUESTIONS_PER_PAGE = int(self._get_env_value('QUESTIONS_PER_PAGE', 
            '50', 
            str(questions_config.get('per_page'))))
        self.AUTO_NEXT_DELAY = int(self._get_env_value('AUTO_NEXT_DELAY', 
            '2', 
            str(questions_config.get('auto_next_delay'))))

        # 缓存配置
        cache_config = config.get('cache', {})
        self.CACHE_ENABLED = self._get_env_value('CACHE_ENABLED', 'true', 
            str(cache_config.get('enabled'))).lower() == 'true'
        self.CACHE_EXPIRE_DAYS = int(self._get_env_value('CACHE_EXPIRE_DAYS', 
            '0', 
            str(cache_config.get('expire_days'))))

        # 数据库配置
        database_config = config.get('database', {})
        self.CLEAR_DATABASE = self._get_env_value('CLEAR_DATABASE', 'false', 
            str(database_config.get('clear_database'))).lower() == 'true'

        # 环境配置
        env = self._get_env_value('ENV', 'development')
        env_config = config.get('environments', {}).get(env, {})
        self.DEBUG = self._get_env_value('DEBUG', 'true', 
            str(env_config.get('debug'))).lower() == 'true'
        self.USE_CACHE = self._get_env_value('USE_CACHE', 'true', 
            str(env_config.get('use_cache'))).lower() == 'true'
        self.CONFIRM_UPDATE = self._get_env_value('CONFIRM_UPDATE', 'false', 
            str(env_config.get('confirm_update'))).lower() == 'true'

config = Config()