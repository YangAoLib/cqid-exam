class ReviewSystem:
    def __init__(self, database):
        self.db = database

    def start_review(self):
        wrong_questions = self.db.get_wrong_questions()
        
        if not wrong_questions:
            print("没有需要复习的错题！")
            return
        
        print(f"共有 {len(wrong_questions)} 道错题需要复习")
        
        for i, question in enumerate(wrong_questions, 1):
            print(f"\n错题 {i} (错误次数: {question[4]}):")
            print(question[1])  # 题目
            
            options = eval(question[2])  # 将字符串转换回列表
            for j, option in enumerate(options, 1):
                print(f"{j}. {option}")
            
            input("\n按回车键查看答案...")
            print(f"正确答案: {question[3]}")
            
            review_result = input("这次答对了吗？(y/n): ").lower()
            if review_result != 'y':
                self.db.record_wrong_answer(question[0]) 