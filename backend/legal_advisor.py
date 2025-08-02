# 从原始main.py中提取LegalAdvisor类，稍作修改
import time
from transformers import AutoModelForCausalLM, AutoTokenizer
from my_knowledge_base.vector_db import search_vector_db
from prompt_templates import construct_prompt_template
import api_integration.case_search as case_search 
from MySQL.search import search_law 
import re

class LegalAdvisor:
    def __init__(self, 
                 model_path="../model/Qwen3-0.6B", 
                 embedding_model_path="../embedding_model/ChatLaw-Text2Vec",
                 vector_db_path="../my_knowledge_base/vector_db/chroma_data",
                 context_chunks=3,
                 max_new_tokens=1024):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto"
        )
        self.embedding_model_path = embedding_model_path
        self.vector_db_path = vector_db_path
        self.context_chunks = context_chunks
        self.max_new_tokens = max_new_tokens
    
    def is_search_query(self, query):
        search_keywords = ['最新', '最近', '新闻', '案例', '事件', '政策', '变化', '更新', '发生', '具体','近期']
        return any(keyword in query for keyword in search_keywords)
    
    def is_database_query(self, query):
        db_keywords = [
            '条', '款', '项', '编', '章', '节', 
            '民法典', '规定', '法律', '法规', '条文','总则',
            '第[零一二三四五六七八九十百千]+条'  # 正则模式匹配条文编号
        ]
        return any(
            keyword in query if isinstance(keyword, str) 
            else re.search(keyword, query)
            for keyword in db_keywords
        )
    
    #联网搜索
    def handle_search_query(self, query):
        search_result = case_search.search_and_extract(query)
        prompt = construct_prompt_template(search_result, query)
        raw_resluts = self.format_search_results(search_result)
        response = self._generate_response(prompt)
        return response, {"service": "search"}, raw_resluts

    #数据库搜索
    def handle_database_query(self, query):
        database_results = search_law(query)      
        prompt = construct_prompt_template(database_results, query)
        db_results = self.format_db_results(database_results)
        response = self._generate_response(prompt)
        return response, {"service": "database"},db_results

    #向量数据库
    def handle_vector_query(self, query):
        vec_results = self.retrieve_context(query)
        prompt = construct_prompt_template(vec_results, query)
        # vec_results = self.format_vector_results(vec_results)
        response = self._generate_response(prompt)
        return response, {"service": "law"}, vec_results
    
    #AI生成
    def _generate_response(self, prompt):
        messages = [{"role": "user", "content": prompt}]
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=self.max_new_tokens
        )
        return self.tokenizer.decode(
            generated_ids[0][len(model_inputs.input_ids[0]):], 
            skip_special_tokens=True
        )

    def retrieve_context(self, query):
        results = search_vector_db(
            query=query,
            vector_db_path=self.vector_db_path,
            embedding_model_path=self.embedding_model_path,
            k=self.context_chunks
        )
        return results
    
    def format_db_results(self, results):
        """将数据库查询结果格式化为前端需要的结构化列表"""
        formatted = []
        
        if not results:
            return formatted
        
        # 检查结果类型（章节查询返回不同结构）
        if '条文内容' in results[0]:
            # 处理章节查询结果
            for row in results:
                if not row.get('条文内容'):
                    continue
                    
                articles = row['条文内容'].split('\n')
                for article in articles:
                    if article.strip():  # 跳过空行
                        # 提取条文编号和内容
                        article_parts = article.split(': ', 1)
                        article_number = article_parts[0].replace('第', '').replace('条', '').strip() if len(article_parts) > 0 else ''
                        article_content = article_parts[1].strip() if len(article_parts) > 1 else article.strip()
                        
                        formatted.append({
                            'title': f"第{article_number}条",
                            'content': article_content,
                            'source': row['位置']
                        })
        else:
            # 处理条文查询结果
            for row in results:
                formatted.append({
                    'title': f"第{row['条文编号']}条",
                    'content': row['内容'],
                    'source': row['位置']
                })
        
        return formatted
    
    def format_search_results(self , results):
        """将联网搜索查询结果格式化为前端需要的结构化列表"""
        raw_result = results
        
        # 处理字符串类型的返回结果
        if isinstance(raw_result, str):
            # 判断是否是错误信息
            if raw_result.startswith(("未找到", "所有网页检索失败")):
                return [{
                    'title': '搜索失败',
                    'content': raw_result,
                    'source': ''
                }]
            else:
                # 处理成功的字符串结果
                lines = raw_result.split('\n')
                source = lines[0].replace('来源: ', '') if len(lines) > 0 else '未知来源'
                title = lines[1].replace('标题: ', '') if len(lines) > 1 else '无标题'
                content = '\n'.join(lines[2:]) if len(lines) > 2 else raw_result
                
                return [{
                    'title': title,
                    'content': content,
                    'source': source
                }]
        
        # 如果已经是列表格式则直接返回
        elif isinstance(raw_result, dict):
            return [{
                'title': raw_result.get('title', '无标题'),
                'content': raw_result.get('content', '无内容'),
                'source': raw_result.get('source', '未知来源')
            }]
        
        # 默认返回错误结构
        return {
            'title': '未知错误',
            'content': '无法解析搜索结果',
            'source': ''
        }