#python -m api_integration.case_search 

import re
import requests
from bs4 import BeautifulSoup
from langchain_community.utilities import SearxSearchWrapper
from config import SEARX_CONFIG  # 导入配置

def format_structured_results(raw_results):
    """调用search_and_extract并返回结构化结果"""
    # 调用search_and_extract获取原始结果
    raw_result = raw_results
    
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
    print("请选择输出格式：")
    print("1. 结构化输出")
    print("2. 字符串输出")
    
    while True:
        output_format = input("\n请选择输出格式(1/2): ").strip()
        if output_format in ['exit', 'quit']:
            break
            
        if output_format not in ['1', '2']:
            print("⚠ 请输入有效选项(1或2)")
            continue
            
        while True:
            query = input("\n请输入搜索关键词(输入'back'返回格式选择): ").strip()
            if query.lower() in ['exit', 'quit']:
                exit()
            if query.lower() == 'back':
                break
                
            if not query:
                print("⚠ 请输入有效搜索词")
                continue
                
            try:
                print(f"\n正在搜索: {query}")
                raw_results = search_and_extract(query)
                    
                if output_format == '1':
                    # 结构化输出
                    results = format_structured_results(raw_results)
                    print("\n【结构化搜索结果】")
                    print(results)
                
                else:
                    print("\n【字符串搜索结果】")
                    print(raw_results)
                    
            except Exception as e:
                print(f"搜索失败: {str(e)}")