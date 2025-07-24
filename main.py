# main.py
# 多功能秘书助手系统（法律+天气）
# 功能：基于Qwen模型的综合助手系统

import time
from transformers import AutoModelForCausalLM, AutoTokenizer
from my_knowledge_base.vector_db import search_vector_db
from prompt_templates import construct_prompt_template
from api_integration.weather_api import get_weather_forecast
from location_extractor import LocationExtractor  # 新增导入

class SecretaryAssistant:
    def __init__(self, 
                 model_path="./Qwen3-0.6B", 
                 embedding_model_path="./embedding_model/all-MiniLM-L6-v2",
                 vector_db_path="./my_knowledge_base/vector_db/faiss_index",
                 context_chunks=3,
                 max_new_tokens=1024):
        """初始化秘书助手系统"""
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
        self.location_extractor = LocationExtractor()  # 初始化地点提取器
    
    def is_weather_query(self, query):
        """判断是否为天气查询"""
        weather_keywords = ['天气', '气温', '预报', '下雨', '下雪', '温度', '湿度', '气象']
        return any(keyword in query for keyword in weather_keywords)
    
    def handle_weather_query(self, query):
        """处理天气查询"""
        location = self.location_extractor.extract_location(query)
        print(f"📍 识别地点: {location}")
        
        weather_info = get_weather_forecast(location)
        if weather_info["status"] == "error":
            return weather_info["formatted"], {}
        
        print(f"\n【{location}的天气数据】")
        print(weather_info["formatted"])
        
        prompt = construct_prompt_template(weather_info["formatted"], query)
        response = self._generate_response(prompt)
        
        return response, {"service": "weather", "location": location}

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
    assistant = SecretaryAssistant()
    print("多功能秘书助手已启动（法律咨询+天气查询，输入'exit'退出）")
    print("温馨提示：天气查询默认地点为东莞，可在提问中指定其他城市")
    
    while True:
        user_input = input("\n请输入您的问题: ").strip()
        if user_input.lower() in ['exit', 'quit']:
            break
        
        if not user_input:
            print("⚠ 请输入有效问题")
            continue
        
        try:
            start_time = time.time()
            
            if assistant.is_weather_query(user_input):
                response, info = assistant.handle_weather_query(user_input)
                service_type = f"{info.get('location', '')}天气查询"
            else:
                response, _ = assistant.handle_law_query(user_input)
                service_type = "法律咨询"
            
            print(f"\n【{service_type}结果】")
            print(response)
            print(f"\n[系统统计] 处理时间: {time.time()-start_time:.2f}s")
            
        except Exception as e:
            print(f"处理问题时出错: {str(e)}")

    print("助手服务结束")