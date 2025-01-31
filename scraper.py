import requests
from bs4 import BeautifulSoup
import time
import re
import os
import json
import logging
from datetime import datetime, timedelta

class QuestionScraper:
    def __init__(self, config):
        self.config = config
        self.base_url = config.SCRAPER_BASE_URL
        self.headers = config.SCRAPER_HEADERS
        self.question_type = config.SCRAPER_QUESTION_TYPE
        self.total_questions = None
        self.questions_per_page = None
        
        # 配置日志
        self.logger = logging.getLogger('scraper')
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
        
        # 创建日志处理器
        log_file = os.path.join(config.LOG_DIR, 'scraper.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        console_handler = logging.StreamHandler()
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def _get_cache_path(self, page):
        """获取缓存文件路径"""
        cache_key = f"type_{self.question_type}_page_{page}"
        return os.path.join(self.config.CACHE_DIR, f"{cache_key}.json")

    def _get_cache_info(self):
        """从缓存目录获取题目总数信息"""
        if not self.config.USE_CACHE or not os.path.exists(self.config.CACHE_DIR):
            return None, None

        try:
            # 获取所有缓存文件
            cache_files = [f for f in os.listdir(self.config.CACHE_DIR) 
                         if f.startswith(f"type_{self.question_type}_page_") and f.endswith('.json')]
            
            if not cache_files:
                return None, None

            # 获取最大题目编号和每页题目数
            max_number = 0
            questions_per_page = 0
            
            for cache_file in cache_files:
                file_path = os.path.join(self.config.CACHE_DIR, cache_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        questions = json.load(f)
                        if questions and len(questions) > 0:
                            questions_per_page = max(questions_per_page, len(questions))
                            for q in questions:
                                if 'number' in q:
                                    max_number = max(max_number, q['number'])
                except Exception as e:
                    self.logger.error(f"读取缓存文件 {cache_file} 失败: {str(e)}")
                    continue

            if max_number > 0 and questions_per_page > 0:
                total_questions = max_number
                self.logger.info(f"从缓存目录获取信息：最大题号={max_number}, 每页题数={questions_per_page}")
                return total_questions, questions_per_page

        except Exception as e:
            self.logger.error(f"获取缓存信息失败: {str(e)}")
        
        return None, None

    def _load_cache(self, page):
        """从缓存加载数据"""
        if not self.config.USE_CACHE:
            return None

        cache_path = self._get_cache_path(page)
        if not os.path.exists(cache_path):
            return None

        # 检查缓存是否过期
        if self.config.CACHE_EXPIRE_DAYS > 0:  # 只有当过期天数大于0时才检查
            file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
            expire_time = datetime.now() - timedelta(days=self.config.CACHE_EXPIRE_DAYS)
            if file_time < expire_time:
                return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"读取缓存失败: {str(e)}")
            return None

    def _save_cache(self, page, data):
        """保存数据到缓存"""
        if not self.config.USE_CACHE:
            return

        cache_path = self._get_cache_path(page)
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存缓存失败: {str(e)}")

    def _get_total_info(self, soup):
        """从页面获取题目总数和每页题目数"""
        if self.total_questions is None or self.questions_per_page is None:
            try:
                # 获取第一个题目的编号信息
                first_question = soup.find('span', class_='text-success')
                if first_question:
                    text = first_question.get_text(strip=True)
                    total_match = re.search(r'\d+/(\d+)', text)
                    if total_match:
                        self.total_questions = int(total_match.group(1))
                
                # 计算每页题目数
                cards = soup.find_all('div', class_='card', attrs={'data-num': True})
                self.questions_per_page = len(cards)
                
                self.logger.info(f"从页面获取信息：总题数={self.total_questions}, 每页题数={self.questions_per_page}")
            except Exception as e:
                self.logger.error(f"获取题目信息时出错: {str(e)}")
                # 设置默认值
                self.total_questions = 0
                self.questions_per_page = 10

    def get_questions(self, page=1):
        """获取指定页面的题目"""
        # 如果还没有题目信息，尝试从缓存目录获取
        if (self.total_questions is None or self.questions_per_page is None) and self.config.USE_CACHE:
            total_questions, questions_per_page = self._get_cache_info()
            if total_questions and questions_per_page:
                self.total_questions = total_questions
                self.questions_per_page = questions_per_page

        # 尝试从缓存加载
        cached_data = self._load_cache(page)
        if cached_data:
            self.logger.info(f"从缓存加载第{page}页的题目")
            return cached_data

        params = {
            'type': self.question_type,
            'page': page
        }
        try:
            self.logger.info(f"开始爬取第{page}页题目")
            response = requests.get(
                self.base_url, 
                params=params, 
                headers=self.headers, 
                timeout=self.config.SCRAPER_REQUEST_TIMEOUT
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取题目总数和每页题目数
            self._get_total_info(soup)
            
            questions = []
            cards = soup.find_all('div', class_='card', attrs={'data-num': True})
            
            for card in cards:
                try:
                    question_number = card.find('span', class_='text-success').get_text(strip=True)
                    question_number = int(re.search(r'(\d+)/\d+', question_number).group(1))
                    
                    title = card.find('div', class_='card-body').find('p', class_='card-text').get_text(strip=True)
                    title = re.sub(r'^\d+/\d+\s*', '', title)
                    
                    options = []
                    answer = None
                    options_div = card.find('div', class_='list-group')
                    
                    for option_item in options_div.find_all('div', class_='list-group-item'):
                        option_text = option_item.find('label').get_text(strip=True)
                        option_text = re.sub(r'^[A-D]\s*', '', option_text)
                        options.append(option_text)
                        
                        if 'bg-success' in option_item.get('class', []):
                            answer = option_text
                    
                    if title and options and answer:
                        questions.append({
                            'number': question_number,
                            'title': title,
                            'options': options,
                            'answer': answer
                        })
                        self.logger.debug(f"成功解析题目 {question_number}")
                
                except Exception as e:
                    self.logger.error(f"解析题目时出错: {str(e)}")
                    continue
            
            self.logger.info(f"成功获取第{page}页的 {len(questions)} 道题目")
            
            # 保存到缓存
            if questions:
                self._save_cache(page, questions)
                
            return questions
            
        except requests.RequestException as e:
            self.logger.error(f"请求失败: {str(e)}")
            return []
        except Exception as e:
            self.logger.error(f"爬取失败: {str(e)}")
            return []
        finally:
            time.sleep(self.config.SCRAPER_DELAY)

    def get_all_questions(self):
        """获取所有题目"""
        self.logger.info("开始获取所有题目")
        all_questions = []
        page = 1
        
        # 先获取第一页来确定总页数
        questions = self.get_questions(page)
        if not questions:
            self.logger.error("获取第一页失败，终止爬取")
            return []
            
        all_questions.extend(questions)
        page += 1
        
        # 计算总页数
        if self.total_questions and self.questions_per_page:
            total_pages = (self.total_questions + self.questions_per_page - 1) // self.questions_per_page
            self.logger.info(f"总页数：{total_pages}")
            
            while page <= total_pages:
                questions = self.get_questions(page)
                if not questions:
                    self.logger.warning(f"获取第{page}页失败，提前终止爬取")
                    break
                all_questions.extend(questions)
                page += 1
        
        self.logger.info(f"爬取完成，总共获取 {len(all_questions)} 道题目")
        return all_questions

    def debug_html(self, html_content):
        """用于调试的方法，打印HTML结构"""
        self.logger.debug("HTML内容预览:")
        self.logger.debug(html_content[:1000])  # 打印前1000个字符
        soup = BeautifulSoup(html_content, 'html.parser')
        self.logger.debug("\n页面结构:")
        self.logger.debug(soup.prettify()[:1000])  # 打印格式化后的前1000个字符 