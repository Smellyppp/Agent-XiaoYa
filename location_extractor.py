# location_extractor.py
import re
from typing import List, Optional

class LocationExtractor:
    def __init__(self, cities_file: str = "data/chinese_cities.txt"):
        """
        初始化地点提取器
        :param cities_file: 城市名单文件路径
        """
        self.city_set = set()
        self.city_patterns = []
        self.load_cities(cities_file)
    
    def load_cities(self, file_path: str):
        """加载城市名单并构建高效查找结构"""
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                city = line.strip()
                if city:
                    self.city_set.add(city)
                    # 为"北京市"和"北京"这种格式创建映射
                    if city.endswith('市'):
                        self.city_set.add(city[:-1])
        
        # 按长度降序排序，优先匹配长名称（如"北京市"优先于"北京"）
        self.city_list = sorted(self.city_set, key=len, reverse=True)
        
        # 预编译常用匹配模式
        self.patterns = [
            re.compile(rf'({city})(?:的?天气|气候|温度)') 
            for city in self.city_list[:100]  # 只对高频城市预编译
        ]
    
    def extract_location(self, text: str, default: str = "东莞") -> Optional[str]:
        """
        从文本中提取城市名称
        :param text: 输入文本
        :param default: 默认城市
        :return: 提取到的城市或默认值
        """
        # 方法1：使用预编译模式匹配高频城市
        for pattern in self.patterns:
            match = pattern.search(text)
            if match:
                return match.group(1)
        
        # 方法2：全量城市集合查找
        for city in self.city_list:
            if city in text:
                return city
        
        # 方法3：处理常见表达方式
        common_phrases = {
            '本地': default,
            '这里': default,
            '当地': default,
            '本市': default
        }
        for phrase, city in common_phrases.items():
            if phrase in text:
                return city
        
        return default