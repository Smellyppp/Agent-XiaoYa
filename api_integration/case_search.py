#python -m api_integration.case_search 

import re
import requests
from bs4 import BeautifulSoup
from langchain_community.utilities import SearxSearchWrapper
from config import SEARX_CONFIG  # 导入配置

def search_and_extract(query):
    """执行搜索并提取第一个成功的网页内容前500字"""
    # 创建 Searx 搜索实例
    search = SearxSearchWrapper(
        searx_host=SEARX_CONFIG["host"],
        k=SEARX_CONFIG["max_results"]
    )

    # 执行搜索获取结构化结果
    results = search.results(
        query=query,
        num_results=SEARX_CONFIG["max_results"]
    )

    if not results:
        return "未找到相关搜索结果"

    # 尝试从多个结果中提取内容，返回第一个成功的
    failed_results = []
    for i, result in enumerate(results):
        result_url = result.get("link")
        if not result_url:
            failed_results.append(f"结果 {i+1}: 缺少有效URL")
            continue
            
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(
                result_url, 
                headers=headers, 
                timeout=SEARX_CONFIG["timeout"]
            )
            response.raise_for_status()
            
            # 设置正确的编码
            if response.encoding == "ISO-8859-1":
                response.encoding = response.apparent_encoding or "utf-8"
            
            # 使用BeautifulSoup解析内容
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 尝试使用常见的选择器提取正文内容
            possible_selectors = [
                "div.article-content", "div.content", "article", 
                "div.main-content", "div.article", "main", "section.content",
                "div.post-content", "div.entry-content", "div.text"
            ]
            
            main_text = ""
            for selector in possible_selectors:
                if content_element := soup.select_one(selector):
                    main_text = content_element.get_text(strip=True, separator=" ")
                    if main_text:  # 如果找到有效内容则退出循环
                        break
            
            # 如果以上选择器都找不到内容，使用整个body
            if not main_text and soup.body:
                main_text = soup.body.get_text(strip=True, separator=" ")
            
            # 清理文本
            if main_text:
                clean_text = re.sub(r'\s+', ' ', main_text).strip()
                clean_text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', clean_text)  # 移除控制字符
                
                # 添加来源信息
                source = result.get('source', '未知来源')
                title = result.get('title', '无标题')
                content = f"来源: {source}\n标题: {title}\n内容: {clean_text[:500]}"
                if len(clean_text) > 500:
                    content += "..."
                
                return content
            else:
                failed_results.append(f"结果 {i+1}: 无法提取正文内容")
                    
        except requests.exceptions.RequestException as e:
            failed_results.append(f"结果 {i+1}: 请求失败 - {str(e)}")
        except Exception as e:
            failed_results.append(f"结果 {i+1}: 处理失败 - {str(e)}")
    
    # 所有结果都失败时返回失败信息
    return "所有网页检索失败:\n" + "\n".join(failed_results)

if __name__ == "__main__":
    print("🔍 网页内容搜索工具（输入'exit'退出）")
    while True:
        query = input("\n请输入搜索关键词: ").strip()
        if query.lower() in ['exit', 'quit']:
            break
        
        if not query:
            print("⚠ 请输入有效搜索词")
            continue
        
        try:
            print(f"\n正在搜索: {query}")
            result = search_and_extract(query)
            print("\n【搜索结果】")
            print(result)
        except Exception as e:
            print(f"搜索失败: {str(e)}")