import os
from flask import Flask, render_template, request, redirect, url_for, flash, g, session, jsonify
from scraper import QuestionScraper
from database import Database
from quiz import QuizSystem
from review import ReviewSystem
from config import config
from functools import wraps
import random

# 根据环境变量选择配置
config_instance = config

app = Flask(__name__)
app.config.from_object(config_instance)
config_instance.init_app(app)

app.secret_key = config_instance.SECRET_KEY

db = Database(config_instance)
scraper = QuestionScraper(config_instance)
quiz_system = QuizSystem(db)
review_system = ReviewSystem(db)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        
        user_role = db.get_user_role(session['user_id'])
        if user_role not in ['admin', 'superadmin']:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        
        user_role = db.get_user_role(session['user_id'])
        if user_role != 'superadmin':
            flash('需要超级管理员权限', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quiz')
def quiz():
    try:
        # 获取URL参数中的题号
        page_number = request.args.get('page', type=int)
        
        # 获取当前题号，未登录用户从session获取，已登录用户从数据库获取
        if 'user_id' in session:
            current_number = page_number or db.get_user_progress(session['user_id'])
        else:
            current_number = page_number or session.get('current_number', 1)
        
        print(f"当前题号: {current_number}")
        
        # 获取指定题号的题目
        question = db.get_question_by_number(current_number)
        print(f"获取到的题目: {question}")
        
        if not question:
            # 检查题库是否为空
            total_questions = db.get_questions_count()
            if total_questions == 0:
                print("题库为空")  # 调试日志
                
                # 判断用户角色
                is_admin = session.get('role') in ['admin', 'superadmin']
                
                if is_admin:
                    print("管理员用户，自动获取题目")  # 调试日志
                    try:
                        # 自动调用爬虫获取题目
                        questions = scraper.get_all_questions()
                        if questions:
                            success_count = 0
                            for q in questions:
                                try:
                                    db.add_question(
                                        q['title'],
                                        q['options'],
                                        q['answer'],
                                        q['number']
                                    )
                                    success_count += 1
                                except Exception as e:
                                    print(f"保存题目失败: {str(e)}")
                                    continue
                            
                            if success_count > 0:
                                flash(f'已自动更新 {success_count} 道题目', 'success')
                                # 重新获取当前题目
                                question = db.get_question_by_number(current_number)
                                if question:
                                    return render_template('quiz.html', 
                                                         question=question,
                                                         current_number=current_number)
                        else:
                            flash('获取题目失败，请手动更新题库', 'danger')
                            return redirect(url_for('index'))
                    except Exception as e:
                        print(f"自动获取题目失败: {str(e)}")
                        flash('获取题目失败，请手动更新题库', 'danger')
                        return redirect(url_for('index'))
                else:
                    print("非管理员用户，提示联系管理员")  # 调试日志
                    flash('题库暂无题目，请联系管理员维护题目', 'warning')
                    return redirect(url_for('index'))
            
            # 如果是已完成所有题目
            if current_number > total_questions:
                flash('恭喜！你已完成所有题目')
                session.pop('current_number', None)  # 清除session中的题号
                return redirect(url_for('index'))
            
            flash('题库异常，请联系管理员维护题目', 'warning')
            return redirect(url_for('index'))
        
        return render_template('quiz.html', 
                             question=question,
                             current_number=current_number)
                             
    except Exception as e:
        print(f"答题出错: {str(e)}")
        flash('系统错误，请重试')
        return redirect(url_for('index'))

@app.route('/practice_wrong')
def practice_wrong():
    if 'user_id' not in session:
        flash('请先登录后再练习错题', 'warning')
        return redirect(url_for('login'))
    
    # 获取特定题目ID
    question_id = request.args.get('question_id')
    
    if question_id:
        # 练习特定错题
        question = db.get_question_by_id(question_id)
        if not question:
            flash('题目不存在', 'danger')
            return redirect(url_for('review'))
        current_number = question['number']
    else:
        # 获取所有错题
        wrong_questions = db.get_wrong_questions(session['user_id'])
        if not wrong_questions:
            flash('没有需要练习的错题', 'info')
            return redirect(url_for('review'))
        
        # 随机选择一道错题
        question = random.choice(wrong_questions)
        current_number = question['number']
    
    return render_template('quiz.html', 
                         question=question,
                         current_number=current_number,
                         is_practice_mode=True)

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    data = request.get_json()
    question_id = data.get('question_id')
    answer_index = data.get('answer_index')
    current_number = data.get('current_number', 1)
    is_practice_mode = data.get('is_practice_mode', False)
    
    question = db.get_question_by_id(question_id)
    if not question:
        return jsonify({'status': 'error', 'message': '题目不存在'})
    
    is_correct = question['options'][answer_index] == question['answer']
    
    # 获取下一题的题号
    if is_practice_mode:
        # 在练习模式下，如果答对了就从错题记录中移除
        if is_correct and 'user_id' in session:
            db.remove_wrong_question(session['user_id'], question_id)
            # 获取剩余错题数量
            remaining_count = db.get_wrong_questions_count(session['user_id'])
            if remaining_count == 0:
                return jsonify({
                    'status': 'success',
                    'correct': is_correct,
                    'answer': question['answer'],
                    'message': '恭喜！你已完成所有错题练习',
                    'redirect_url': url_for('index')  # 修改为返回首页
                })
        # 获取下一道错题
        next_question = db.get_next_wrong_question(session['user_id'], current_number)
        next_number = next_question['number'] if next_question else None
        
        # 如果没有下一题（但还有未答对的题目），返回到第一道错题
        if next_number is None and db.get_wrong_questions_count(session['user_id']) > 0:
            first_wrong = db.get_first_wrong_question(session['user_id'])
            if first_wrong:
                next_number = first_wrong['number']
    else:
        next_number = current_number + 1 if current_number else 2
    
    if not is_correct:
        if 'user_id' in session:
            # 已登录用户，记录到数据库
            db.record_wrong_answer(session['user_id'], question_id)
        else:
            # 未登录用户，记录到session
            wrong_answers = session.get('wrong_answers', {})
            wrong_answers[str(question_id)] = {
                'count': wrong_answers.get(str(question_id), {}).get('count', 0) + 1,
                'question': question
            }
            session['wrong_answers'] = wrong_answers
    
    # 更新进度（仅在非练习模式下）
    if not is_practice_mode:
        if 'user_id' in session:
            db.update_user_progress(session['user_id'], next_number)
        session['current_number'] = next_number
    
    return jsonify({
        'status': 'success',
        'correct': is_correct,
        'answer': question['answer'],
        'next_number': next_number,
        'auto_next_delay': config_instance.AUTO_NEXT_DELAY
    })

@app.route('/review')
def review():
    if 'user_id' in session:
        # 已登录用户，从数据库获取错题
        wrong_questions = db.get_wrong_questions(session['user_id'])
    else:
        # 未登录用户，从session获取错题
        wrong_answers = session.get('wrong_answers', {})
        wrong_questions = [
            {**data['question'], 'wrong_count': data['count']}
            for data in wrong_answers.values()
        ]
    
    return render_template('review.html', wrong_questions=wrong_questions)

@app.route('/update')
@admin_required
def update():
    # 在生产环境下需要二次确认
    if config_instance.CONFIRM_UPDATE and not request.args.get('confirmed'):
        return render_template('confirm_update.html')
        
    try:
        questions = scraper.get_all_questions()
        if not questions:
            flash('未获取到任何题目，请检查网站结构是否变化', 'warning')
            return redirect(url_for('index'))
            
        success_count = 0
        for question in questions:
            try:
                db.add_question(
                    question['title'],
                    question['options'],
                    question['answer'],
                    question['number']
                )
                success_count += 1
            except Exception as e:
                print(f"保存题目失败: {str(e)}")
                continue
                
        if success_count > 0:
            flash(f'成功更新 {success_count} 道题目', 'success')
        else:
            flash('未能成功保存任何题目', 'danger')
            
    except Exception as e:
        flash(f'更新失败: {str(e)}', 'danger')
        print(f"详细错误: {str(e)}")
        
    return redirect(url_for('index'))

@app.route('/questions')
def view_questions():
    page = request.args.get('page', 1, type=int)
    per_page = app.config['QUESTIONS_PER_PAGE']
    
    # 获取总题目数和分页数据
    total_questions = db.get_questions_count()
    questions = db.get_questions_page(page, per_page)
    total_pages = (total_questions + per_page - 1) // per_page
    
    # 传递用户角色信息到模板
    is_admin = session.get('role') in ['admin', 'superadmin']
    
    return render_template('questions.html',
                         questions=questions,
                         current_page=page,
                         total_pages=total_pages,
                         is_admin=is_admin,
                         max=max,
                         min=min)

@app.teardown_appcontext
def close_db(error):
    """关闭数据库连接"""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        if username:
            user = db.get_or_create_user(username)
            if user is None:
                flash('用户名不可用', 'danger')
                return redirect(url_for('login'))
                
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            # 如果有临时的错题记录，转移到数据库
            if 'wrong_answers' in session:
                for question_id, data in session['wrong_answers'].items():
                    for _ in range(data['count']):
                        db.record_wrong_answer(user['id'], int(question_id))
                session.pop('wrong_answers')  # 清除临时记录
            
            # 如果有进度记录，更新到数据库
            if 'current_number' in session:
                db.update_user_progress(user['id'], session['current_number'])
            
            flash(f'欢迎, {username}!', 'success')
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    # 保留进度和错题记录
    current_number = session.get('current_number')
    wrong_answers = session.get('wrong_answers')
    
    # 清除登录信息
    session.clear()
    
    # 恢复进度和错题记录
    if current_number:
        session['current_number'] = current_number
    if wrong_answers:
        session['wrong_answers'] = wrong_answers
        
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

@app.route('/reset_progress', methods=['POST'])
def reset_progress():
    question_number = request.form.get('question_number', type=int)
    if question_number:
        total_questions = db.get_questions_count()
        if 1 <= question_number <= total_questions:
            if 'user_id' in session:
                # 已登录用户，更新数据库
                db.reset_user_progress(session['user_id'], question_number)
            # 所有用户都更新session
            session['current_number'] = question_number
            flash(f'进度已重置到第 {question_number} 题', 'success')
        else:
            flash('无效的题号', 'danger')
    return redirect(url_for('quiz'))

@app.route('/admin/users')
@superadmin_required
def manage_users():
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)

@app.route('/admin/set_role', methods=['POST'])
@superadmin_required
def set_role():
    user_id = request.form.get('user_id', type=int)
    role = request.form.get('role')
    
    if not user_id or role not in ['user', 'admin']:
        flash('无效的请求', 'danger')
        return redirect(url_for('manage_users'))
    
    db.set_user_role(user_id, role)
    flash('用户角色已更新', 'success')
    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    # 从环境变量获取主机和端口
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    
    # 根据环境变量配置决定是否开启调试模式
    debug = config_instance.DEBUG
    
    app.run(host=host, port=port, debug=debug) 