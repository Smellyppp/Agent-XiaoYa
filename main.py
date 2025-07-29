# main.py
# 法律顾问助手系统
# 功能：基于Qwen模型的法律助手系统

import time
from transformers import AutoModelForCausalLM, AutoTokenizer
from my_knowledge_base.vector_db import search_vector_db
from prompt_templates import construct_prompt_template
import api_integration.case_search as case_search  # 导入搜索引擎模块

class LegalAdvisor:
    def __init__(self, 
                 model_path="./model/Qwen3-0.6B", 
                 embedding_model_path="./embedding_model/all-MiniLM-L6-v2",
                 vector_db_path="./my_knowledge_base/vector_db/faiss_index",
                 context_chunks=3,
                 max_new_tokens=1024):
        """初始化法律顾问系统"""
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
        """判断是否为需要网络搜索的问题"""
        # 需要网络搜索的情况：最新案例、政策变化、具体事件等
        search_keywords = ['最新', '最近', '新闻', '案例', '事件', '政策', '变化', '更新', '发生', '具体','近期']
        return any(keyword in query for keyword in search_keywords)
    
    def handle_search_query(self, query):
        """处理需要网络搜索的问题"""
        print(f"🔍 正在搜索最新信息...")
        
        # 调用搜索引擎获取最新信息
        search_result = case_search.search_and_extract(query)
        
        # 打印搜索结果
        print("\n【搜索引擎返回结果】")
        print(search_result)
        
        # 使用搜索结果构建提示
        prompt = construct_prompt_template(search_result, query)
        response = self._generate_response(prompt)
        
        return response, {"service": "search"}

    def handle_law_query(self, query):
        """处理法律咨询"""
        context, results = self.retrieve_context(query)
        
        print("\n【检索到的法律条文】")
        for i, result in enumerate(results):
            print(f"[条文 {i+1}]: {result['content']}\n")
        
        prompt = construct_prompt_template(context, query)
        response = self._generate_response(prompt)
        
        return response, {"service": "law"}
    
    def _generate_response(self, prompt):
        """通用回答生成方法"""
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
        """从向量数据库检索法律上下文"""
        results = search_vector_db(
            query=query,
            vector_db_path=self.vector_db_path,
            embedding_model_path=self.embedding_model_path,
            k=self.context_chunks
        )
        
        context = "检索到的相关法律条文:\n\n"
        for i, result in enumerate(results):
            context += f"[条文 {i+1}]: {result['content']}\n\n"
        
        return context, results

if __name__ == "__main__":
    advisor = LegalAdvisor()
    print("法律顾问助手已启动（输入'exit'退出）")
    print("温馨提示：我可以回答法律问题，也可以搜索最新案例和事件")
    
    while True:
        user_input = input("\n请输入您的问题: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        
        if not user_input:
            print("⚠ 请输入有效问题")
            continue
        
        try:
            start_time = time.time()
            
            if advisor.is_search_query(user_input):
                response, _ = advisor.handle_search_query(user_input)
                service_type = "案例搜索"
            else:
                response, _ = advisor.handle_law_query(user_input)
                service_type = "法律咨询"
            
            print(f"\n【{service_type}结果】")
            print(response)
            print(f"\n[系统统计] 处理时间: {time.time()-start_time:.2f}s")
            
        except Exception as e:
            print(f"处理问题时出错: {str(e)}")

    print("助手服务结束")