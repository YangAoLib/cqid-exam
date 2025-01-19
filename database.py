import sqlite3
from datetime import datetime
import threading
from flask import g
import logging
import sys
import random

class Database:
    def __init__(self, config):
        self.config = config
        self.database = config.DATABASE_FILE
        
        # 配置日志
        self.logger = logging.getLogger('database')
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # 文件处理器
        file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(config.LOG_FORMAT))
        self.logger.addHandler(console_handler)
        
        self._create_tables()

    def get_db(self):
        """获取当前线程的数据库连接"""
        if not hasattr(g, 'sqlite_db'):
            g.sqlite_db = sqlite3.connect(self.database)
        return g.sqlite_db

    def _create_tables(self):
        """创建数据库表"""
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        
        # 检查是否需要清理数据库
        should_clear = self.config.CLEAR_DATABASE
        
        if should_clear:
            self.logger.info("正在清理数据库...")
            # 删除所有表
            cursor.execute("DROP TABLE IF EXISTS wrong_answers")
            cursor.execute("DROP TABLE IF EXISTS user_progress")
            cursor.execute("DROP TABLE IF EXISTS users")
            cursor.execute("DROP TABLE IF EXISTS questions")
            conn.commit()
            self.logger.info("数据库清理完成")
        else:
            # 检查表是否存在
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND 
                name IN ('users', 'user_progress', 'questions', 'wrong_answers')
            ''')
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            # 如果所有表都存在，则直接返回
            if len(existing_tables) == 4:
                conn.close()
                return

        self.logger.info("开始创建数据库表...")
        
        # 创建用户表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'user',  -- 用户角色: user, admin, superadmin
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.logger.debug("用户表创建完成")
        
        # 创建超级管理员
        cursor.execute('''
        INSERT OR IGNORE INTO users (username, role) 
        VALUES (?, 'superadmin')
        ''', (self.config.SUPERADMIN_USERNAME,))
        self.logger.debug("超级管理员账户创建完成")
        
        # 创建用户进度表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            current_question INTEGER NOT NULL DEFAULT 1,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        self.logger.debug("用户进度表创建完成")
        
        # 创建题目表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number INTEGER UNIQUE,
            title TEXT NOT NULL,
            options TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.logger.debug("题目表创建完成")

        # 创建错题记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wrong_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            wrong_count INTEGER DEFAULT 1,
            last_review_time TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, question_id)
        )
        ''')
        self.logger.debug("错题记录表创建完成")
        
        conn.commit()
        conn.close()
        self.logger.info("所有数据库表创建完成")

    def add_question(self, title, options, answer, number=None):
        """添加或更新题目"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # 使用 INSERT OR REPLACE 来处理重复的题号
        cursor.execute('''
            INSERT OR REPLACE INTO questions 
            (number, title, options, answer) 
            VALUES (?, ?, ?, ?)
        ''', (number, title, str(options), answer))
        
        conn.commit()

    def record_wrong_answer(self, user_id, question_id):
        """记录错题"""
        conn = self.get_db()
        cursor = conn.cursor()
        now = datetime.now()
        
        # 先检查是否已存在记录
        cursor.execute('''
            SELECT wrong_count FROM wrong_answers 
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id))
        
        result = cursor.fetchone()
        if result:
            # 如果存在，更新错误次数
            cursor.execute('''
                UPDATE wrong_answers 
                SET wrong_count = wrong_count + 1,
                    last_review_time = ?
                WHERE user_id = ? AND question_id = ?
            ''', (now, user_id, question_id))
        else:
            # 如果不存在，创建新记录
            cursor.execute('''
                INSERT INTO wrong_answers 
                (user_id, question_id, wrong_count, last_review_time)
                VALUES (?, ?, 1, ?)
            ''', (user_id, question_id, now))
        
        conn.commit()

    def get_wrong_questions(self, user_id):
        """获取用户的错题"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # 修改查询语句，确保获取正确的错误次数
        cursor.execute('''
            SELECT 
                q.id,
                q.number,
                q.title,
                q.options,
                q.answer,
                w.wrong_count,
                w.last_review_time
            FROM questions q 
            JOIN wrong_answers w ON q.id = w.question_id 
            WHERE w.user_id = ?
            ORDER BY w.last_review_time DESC, w.wrong_count DESC
        ''', (user_id,))
        
        questions = cursor.fetchall()
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'id': q[0],
                'number': q[1],
                'title': q[2],
                'options': eval(q[3]),
                'answer': q[4],
                'wrong_count': q[5],
                'last_review_time': q[6]
            })
        return formatted_questions

    def get_questions(self, limit=None):
        """获取题目，可选择限制数量"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        if limit:
            cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM questions ORDER BY number')  # 按题号排序
        
        questions = cursor.fetchall()
        
        # 将数据库记录转换为字典格式
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'id': q[0],
                'number': q[1],  # 添加题号
                'title': q[2],
                'options': eval(q[3]),
                'answer': q[4]
            })
        return formatted_questions

    def get_questions_count(self):
        """获取题目总数"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM questions')
        return cursor.fetchone()[0]

    def get_questions_page(self, page=1, per_page=20):
        """获取分页的题目"""
        conn = self.get_db()
        cursor = conn.cursor()
        offset = (page - 1) * per_page
        cursor.execute('''
            SELECT * FROM questions 
            ORDER BY number ASC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        questions = cursor.fetchall()
        formatted_questions = []
        for q in questions:
            formatted_questions.append({
                'id': q[0],
                'number': q[1],
                'title': q[2],
                'options': eval(q[3]),
                'answer': q[4]
            })
        return formatted_questions 

    def get_question_by_number(self, number):
        """根据题号获取题目"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM questions WHERE number = ?', (number,))
            question = cursor.fetchone()
            
            self.logger.debug(f"查询题号 {number} 结果: {question}")
            
            if question:
                # 获取选项和答案
                options = eval(question[3])
                answer = question[4]
                
                # 记录答案的原始索引
                answer_index = options.index(answer)
                
                # 打乱选项顺序
                shuffled_options = options.copy()
                random.shuffle(shuffled_options)
                
                # 获取答案在打乱后的新索引
                new_answer_index = shuffled_options.index(answer)
                
                return {
                    'id': question[0],
                    'number': question[1],
                    'title': question[2],
                    'options': shuffled_options,
                    'answer': answer,
                    'answer_index': new_answer_index
                }
            return None
            
        except Exception as e:
            self.logger.error(f"获取题目出错: {str(e)}")
            return None

    def get_question_by_id(self, question_id):
        """根据ID获取题目"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
        question = cursor.fetchone()
        
        if question:
            # 获取选项和答案
            options = eval(question[3])
            answer = question[4]
            
            # 记录答案的原始索引
            answer_index = options.index(answer)
            
            # 打乱选项顺序
            shuffled_options = options.copy()
            random.shuffle(shuffled_options)
            
            # 获取答案在打乱后的新索引
            new_answer_index = shuffled_options.index(answer)
            
            return {
                'id': question[0],
                'number': question[1],
                'title': question[2],
                'options': shuffled_options,
                'answer': answer,
                'answer_index': new_answer_index
            }
        return None

    def get_or_create_user(self, username):
        """获取或创建用户"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # 检查用户名是否是超级管理员用户名
        if username == self.config.SUPERADMIN_USERNAME:
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if user:
                # 确保超级管理员也有进度记录
                cursor.execute('SELECT * FROM user_progress WHERE user_id = ?', (user[0],))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO user_progress (user_id, current_question)
                        VALUES (?, 1)
                    ''', (user[0],))
                    conn.commit()
                
                return {
                    'id': user[0],
                    'username': user[1],
                    'role': user[2],
                    'created_at': user[3]
                }
            else:
                self.logger.warning(f"尝试使用超级管理员用户名 {username} 创建普通用户")
                return None
        
        # 非超级管理员用户名，获取或创建用户
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, role) 
            VALUES (?, 'user')
        ''', (username,))
        conn.commit()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        # 初始化用户进度
        cursor.execute('SELECT * FROM user_progress WHERE user_id = ?', (user[0],))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO user_progress (user_id, current_question)
                VALUES (?, 1)
            ''', (user[0],))
            conn.commit()
        
        return {
            'id': user[0],
            'username': user[1],
            'role': user[2],
            'created_at': user[3]
        }

    def get_user_progress(self, user_id):
        """获取用户进度"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT current_question FROM user_progress WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 1

    def update_user_progress(self, user_id, question_number):
        """更新用户进度"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_progress 
            SET current_question = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (question_number, user_id))
        conn.commit()

    def reset_user_progress(self, user_id, question_number):
        """重置用户进度到指定题号"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE user_progress 
            SET current_question = ?, last_updated = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (question_number, user_id))
        conn.commit() 

    def get_all_users(self):
        """获取所有用户"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, role FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        return [{'id': u[0], 'username': u[1], 'role': u[2]} for u in users]

    def set_user_role(self, user_id, role):
        """设置用户角色"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
        conn.commit()

    def get_user_role(self, user_id):
        """获取用户角色"""
        conn = self.get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else None 

    def remove_wrong_question(self, user_id, question_id):
        """从错题记录中移除一道题目"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM wrong_answers 
            WHERE user_id = ? AND question_id = ?
        ''', (user_id, question_id))
        
        conn.commit()
    
    def get_wrong_questions_count(self, user_id):
        """获取用户的错题数量"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM wrong_answers 
            WHERE user_id = ?
        ''', (user_id,))
        
        return cursor.fetchone()[0]
    
    def get_next_wrong_question(self, user_id, current_number):
        """获取下一道错题"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # 先尝试获取比当前题号大的错题
        cursor.execute('''
            SELECT 
                q.id,
                q.number,
                q.title,
                q.options,
                q.answer,
                w.wrong_count
            FROM questions q 
            JOIN wrong_answers w ON q.id = w.question_id 
            WHERE w.user_id = ? AND q.number > ?
            ORDER BY q.number
            LIMIT 1
        ''', (user_id, current_number))
        
        question = cursor.fetchone()
        
        if not question:
            # 如果没有更大题号的错题，则从头开始
            cursor.execute('''
                SELECT 
                    q.id,
                    q.number,
                    q.title,
                    q.options,
                    q.answer,
                    w.wrong_count
                FROM questions q 
                JOIN wrong_answers w ON q.id = w.question_id 
                WHERE w.user_id = ?
                ORDER BY q.number
                LIMIT 1
            ''', (user_id,))
            question = cursor.fetchone()
        
        if question:
            return {
                'id': question[0],
                'number': question[1],
                'title': question[2],
                'options': eval(question[3]),
                'answer': question[4],
                'wrong_count': question[5]
            }
        return None 

    def get_first_wrong_question(self, user_id):
        """获取用户的第一道错题"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                q.id,
                q.number,
                q.title,
                q.options,
                q.answer,
                w.wrong_count
            FROM questions q 
            JOIN wrong_answers w ON q.id = w.question_id 
            WHERE w.user_id = ?
            ORDER BY q.number
            LIMIT 1
        ''', (user_id,))
        
        question = cursor.fetchone()
        
        if question:
            return {
                'id': question[0],
                'number': question[1],
                'title': question[2],
                'options': eval(question[3]),
                'answer': question[4],
                'wrong_count': question[5]
            }
        return None 