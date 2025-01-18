import random

class QuizSystem:
    def __init__(self, database):
        self.db = database

    def start_quiz(self, questions):
        score = 0
        total = len(questions)
        
        for i, question in enumerate(questions, 1):
            print(f"\n问题 {i}/{total}:")
            print(question['title'])
            
            for j, option in enumerate(question['options'], 1):
                print(f"{j}. {option}")
            
            while True:
                try:
                    answer = int(input("\n请选择答案(输入选项编号): "))
                    if 1 <= answer <= len(question['options']):
                        break
                    print("无效的选择，请重试")
                except ValueError:
                    print("请输入数字")
            
            if question['options'][answer-1] == question['answer']:
                print("回答正确！")
                score += 1
            else:
                print(f"回答错误。正确答案是: {question['answer']}")
                self.db.record_wrong_answer(question['id'])
        
        print(f"\n测试完成！得分: {score}/{total}")
        return score 