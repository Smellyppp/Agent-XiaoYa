import sys
from pathlib import Path

# 获取项目根目录路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from flask import Flask, request, jsonify
from legal_advisor import LegalAdvisor
from flask_cors import CORS  
import time
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # 添加这行，启用CORS
advisor = LegalAdvisor()



@app.route('/log', methods=['POST'])
def log_message():
    try:
        data = request.get_json()
        action = data.get('action', '未知操作')
        details = data.get('details', '无详情')
        web_search = data.get('web_search', False)
        
        # 使用当前时间而不是解析前端发送的时间戳
        log_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 创建日志消息
        log_msg = f"[{log_time}] 操作: {action}, 详情: {details}, 联网搜索: {'是' if web_search else '否'}"
        
        # 打印到终端
        print(log_msg)
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"日志记录错误: {str(e)}")
        return jsonify({"error": "日志记录失败"}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question', '').strip()
    web_search = data.get('web_search', False)  # 获取联网搜索选项
    print(web_search)
    
    if not question:
        return jsonify({"error": "问题不能为空"}), 400
    
    try:
        start_time = time.time()   
        raw_results = None
        vec_results = None
        db_results = None
        
        if advisor.is_search_query(question) or web_search == True:
            print("联网搜索")
            response, _ ,raw_results = advisor.handle_search_query(question)
            print(f"response 类型: {type(response)}")
            print(f"raw_results 类型: {type(raw_results)}")
            print(raw_results)
            
        elif advisor.is_database_query(question):
            print("MySQL")
            response, _ ,db_results = advisor.handle_database_query(question)
            print(f"response 类型: {type(response)}")
            print(f"db_results 类型: {type(db_results)}")
            print(db_results)
            
        else:
            print("Chroma")
            response, _ ,vec_results = advisor.handle_vector_query(question)
            print(f"response 类型: {type(response)}")
            print(f"vec_results 类型: {type(vec_results)}") 
            print(vec_results)     
        
        return jsonify({
            "answer": response,
            "time": f"{time.time()-start_time:.2f}s",
            "search_results": raw_results,
            "vector_results": vec_results,  
            "database_results": db_results           
        })
    
    except Exception as e:
        return jsonify({"error": f"处理问题时出错: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)