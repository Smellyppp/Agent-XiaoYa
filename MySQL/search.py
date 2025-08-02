#python -m MySQL.search

import mysql.connector
import re
from config import DB_CONFIG

# 中文数字转阿拉伯数字的函数（用于处理"第X条"的查询）
def chinese_to_arabic(chinese_num):
    """中文数字转阿拉伯数字"""
    num_map = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000
    }
    
    if chinese_num == '十':
        return 10
        
    result = 0
    temp = 0
    for char in chinese_num:
        if char in num_map:
            val = num_map[char]
            if val >= 10:
                if temp == 0:
                    temp = 1
                result += temp * val
                temp = 0
            else:
                temp = val
    result += temp
    return result

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)
    
def format_db_results(results):
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

def search_law(query):
    """智能查询民法典内容（限制返回5条结果）"""
    conn = None
    cursor = None
    results = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # 情况1：用户查询特定条文编号（如"第5条"）
        article_match = re.search(r'第([零一二三四五六七八九十百千0-9]+)条', query)
        if article_match:
            article_number_str = article_match.group(1)
            # 判断是中文数字还是阿拉伯数字
            if article_number_str.isdigit():
                article_number = int(article_number_str)
            else:
                article_number = chinese_to_arabic(article_number_str)
            sql = """
            SELECT a.article_number AS '条文编号', a.content AS '内容', 
                   CONCAT(c.part, ' > ', c.chapter, IFNULL(CONCAT(' > ', c.section), '')) AS '位置'
            FROM law_articles a
            JOIN catalog c ON a.catalog_id = c.id
            WHERE a.article_number = %s
            LIMIT 5
            """  # 添加LIMIT 5
            cursor.execute(sql, (article_number,))
            results = cursor.fetchall()
        
        # 情况2：用户查询章节内容（如"总则"、"自然人"）
        elif any(keyword in query for keyword in ["编", "章", "节", "总则", "自然人", "法人", "合同"]):
            sql = """
            SELECT 
                c.id AS '编目ID',
                CONCAT(c.part, ' > ', c.chapter, IFNULL(CONCAT(' > ', c.section), '')) AS '位置',
                GROUP_CONCAT(CONCAT('第', a.article_number, '条: ', a.content) SEPARATOR '\n') AS '条文内容'
            FROM catalog c
            LEFT JOIN law_articles a ON c.id = a.catalog_id
            WHERE c.part LIKE %s OR c.chapter LIKE %s OR c.section LIKE %s
            GROUP BY c.id
            ORDER BY c.id
            LIMIT 5
            """  # 添加LIMIT 5
            search_term = f"%{query}%"
            cursor.execute(sql, (search_term, search_term, search_term))
            results = cursor.fetchall()
        
        # 情况3：用户查询关键词（如"监护"、"合同"）
        else:
            sql = """
            SELECT a.article_number AS '条文编号', a.content AS '内容', 
                   CONCAT(c.part, ' > ', c.chapter, IFNULL(CONCAT(' > ', c.section), '')) AS '位置'
            FROM law_articles a
            JOIN catalog c ON a.catalog_id = c.id
            WHERE a.content LIKE %s
            ORDER BY a.article_number
            LIMIT 5
            """  # 添加LIMIT 5
            search_term = f"%{query}%"
            cursor.execute(sql, (search_term,))
            results = cursor.fetchall()
        
        return results
        
    except mysql.connector.Error as e:
        print(f"数据库错误: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def display_results(results):
    """格式化显示查询结果"""
    if not results:
        print("未找到匹配的条文内容")
        return
    
    # 检查结果类型（章节查询返回不同结构）
    if '条文内容' in results[0]:
        # 章节查询结果
        for row in results:
            print(f"\n===== {row['位置']} =====")
            print(row['条文内容'])
            print("-" * 50)
    else:
        # 条文查询结果
        for row in results:
            print(f"\n第{row['条文编号']}条 [{row['位置']}]")
            print(row['内容'])
            print("-" * 50)

def main_menu():
    """主菜单界面"""
    print("\n=== 民法典查询系统 ===")
    print("支持以下查询方式：")
    print("1. 条文编号查询（如：'第5条'）")
    print("2. 章节查询（如：'总则'、'自然人'）")
    print("3. 关键词查询（如：'监护'、'合同'）")
    print("输入 '退出' 结束程序")
    
    while True:
        query = input("\n请输入查询内容: ").strip()
        if query.lower() in ["退出", "exit", "quit"]:
            print("感谢使用，再见！")
            break
            
        if not query:
            print("请输入有效的查询内容")
            continue
            
        results = search_law(query)
        
        # results = display_results(results)
        results = format_db_results(results)
        print(results)
        print("-" * 50)

if __name__ == "__main__":
    main_menu()