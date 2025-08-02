import re
import pymysql
from pymysql.cursors import DictCursor
from config import DB_CONFIG

def parse_civil_code(text):
    """解析民法典文本结构"""
    # 使用正则表达式匹配各级结构
    part_pattern = re.compile(r'\[section0\](.*?)\[\/section0\]')
    chapter_pattern = re.compile(r'\[section2\](.*?)\[\/section2\]')
    section_pattern = re.compile(r'\[section3\](.*?)\[\/section3\]')
    article_pattern = re.compile(r'\[article\](.*?)\[\/article\]')
    
    # 初始化数据结构
    structure = []
    current_part = None
    current_chapter = None
    current_section = None
    
    # 按行处理
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 匹配编
        part_match = part_pattern.match(line)
        if part_match:
            current_part = part_match.group(1).strip()
            current_chapter = None
            current_section = None
            continue
            
        # 匹配章
        chapter_match = chapter_pattern.match(line)
        if chapter_match:
            current_chapter = chapter_match.group(1).strip()
            current_section = None
            continue
            
        # 匹配节
        section_match = section_pattern.match(line)
        if section_match:
            current_section = section_match.group(1).strip()
            continue
            
        # 匹配条文
        article_match = article_pattern.match(line)
        if article_match:
            article_content = article_match.group(1).strip()
            # 提取条文编号和内容
            article_number_match = re.match(r'第([零一二三四五六七八九十百千]+)条', article_content)
            if article_number_match:
                article_number = chinese_to_arabic(article_number_match.group(1))
                structure.append({
                    'part': current_part,
                    'chapter': current_chapter,
                    'section': current_section,
                    'article_number': article_number,
                    'content': article_content,
                    'word_count': len(article_content)
                })
    
    return structure

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

def import_to_database(data):
    conn = None
    cursor = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 1. 清空表
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        cursor.execute("TRUNCATE TABLE law_articles")
        cursor.execute("TRUNCATE TABLE catalog")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        # 2. 按编目分组
        catalog_map = {}
        for item in data:
            key = (item['part'], item['chapter'], item['section'])
            if key not in catalog_map:
                catalog_map[key] = {
                    'part': item['part'],
                    'chapter': item['chapter'],
                    'section': item['section'],
                    'articles': [],
                    'min_article': item['article_number'],
                    'max_article': item['article_number']
                }
            else:
                if item['article_number'] < catalog_map[key]['min_article']:
                    catalog_map[key]['min_article'] = item['article_number']
                if item['article_number'] > catalog_map[key]['max_article']:
                    catalog_map[key]['max_article'] = item['article_number']
            catalog_map[key]['articles'].append(item)
        
        # 3. 插入数据
        catalog_ids = {}
        for key, catalog_data in catalog_map.items():            
            # 插入 catalog 表
            sql = """
            INSERT INTO catalog 
            (part, subpart, chapter, section, start_article, end_article)
            VALUES (%s, NULL, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                catalog_data['part'],
                catalog_data['chapter'],
                catalog_data['section'],
                catalog_data['min_article'],
                catalog_data['max_article']
            ))
            catalog_id = cursor.lastrowid
            catalog_ids[key] = catalog_id
            
            # 插入 law_articles 表
            for article in catalog_data['articles']:
                sql = """
                INSERT INTO law_articles 
                (catalog_id, article_number, content, word_count)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    catalog_id,
                    article['article_number'],
                    article['content'],
                    article['word_count']
                ))
        
        conn.commit()
        print(f"成功导入 {len(data)} 条法律条文，共 {len(catalog_map)} 个编目结构")
        
    except Exception as e:
        if conn: conn.rollback()
        print("导入失败:", e)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()        
        
if __name__ == '__main__':
    # 读取文件内容
    with open('../my_knowledge_base/parsed_document/docx/民法典.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 解析文本结构
    structured_data = parse_civil_code(text)
    
    # 导入数据库
    import_to_database(structured_data)