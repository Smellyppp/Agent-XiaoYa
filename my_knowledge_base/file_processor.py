"""
文件处理器 (file_processor.py)

功能概述：
1. 支持多种文档格式的解析（TXT、PDF、DOCX）
2. 对文档内容进行结构化处理，添加标签标记标题、目录、章节和条款
3. 将处理后的结果保存为结构化TXT文件
4. 支持批量处理目录下的所有文档

主要功能：
- load_and_save_document: 主入口函数，处理文件或目录
- process_single_file: 根据文件类型调用对应的解析器
- parse_pdf/pdf_docx: PDF/DOCX文件解析器
- preprocess_text: 核心处理逻辑，添加结构化标签
- chinese_to_number: 中文数字转换工具

使用方式：
python file_processor.py （自动处理./original_data目录下的文件）

输出：
在./parsed_document目录下生成结构化TXT文件
"""

import os
from PyPDF2 import PdfReader
from docx import Document
from langchain_community.document_loaders import TextLoader
import re

def load_and_save_document(file_path, output_dir="parsed_document"):
    """
    主处理函数：加载、解析文档并保存处理结果
    参数：
        file_path: 输入文件/目录路径
        output_dir: 输出目录（默认parsed_document）
    """
    os.makedirs(output_dir, exist_ok=True)  # 确保输出目录存在
    
    if os.path.isdir(file_path):
        # 处理目录下的所有文件
        for root, _, files in os.walk(file_path):
            for file in files:
                full_path = os.path.join(root, file)
                try:
                    # 三步处理流程：解析->预处理->保存
                    parsed_text = process_single_file(full_path)
                    preprocessed_text = preprocess_text(parsed_text)
                    save_parsed_data(preprocessed_text, full_path, output_dir)
                except ValueError as e:
                    print(f"跳过不支持的文件: {full_path}。错误: {e}")
    else:
        # 处理单个文件
        parsed_text = process_single_file(file_path)
        preprocessed_text = preprocess_text(parsed_text)
        save_parsed_data(preprocessed_text, file_path, output_dir)

def process_single_file(file_path):
    """
    根据文件类型调用对应的解析器
    参数：
        file_path: 文件路径
    返回：
        文件文本内容字符串
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.txt':
        # 处理TXT文件（使用langchain TextLoader）
        loader = TextLoader(file_path, encoding='utf-8')
        documents = loader.load()
        return "\n".join([doc.page_content for doc in documents])
    elif ext == '.pdf':
        return parse_pdf(file_path)  # PDF解析
    elif ext == '.docx':
        return parse_docx(file_path)  # DOCX解析
    else:
        raise ValueError(f"不支持的文件类型: {ext}")

def parse_pdf(file_path):
    """
    PDF文件解析器
    使用PyPDF2逐页提取文本
    """
    full_text = []
    with open(file_path, 'rb') as file:
        pdf_reader = PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            if text.strip():  # 忽略空白页
                full_text.append(text)
    return "\n".join(full_text)

def parse_docx(file_path):
    """
    DOCX文件解析器
    使用python-docx提取段落文本
    """
    full_text = []
    doc = Document(file_path)
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:  # 忽略空段落
            full_text.append(text)
    return "\n".join(full_text)

def preprocess_text(text):
    """
    核心预处理函数：添加结构化标签
    处理流程：
    1. 识别主标题
    2. 识别目录部分
    3. 识别章节和条款
    4. 添加对应的XML风格标签
    
    标签说明：
    [title]...[/title] - 文档主标题
    [content]...[/content] - 目录部分
    [section1]...[/section1] - 章节标题（第一章等）
    [ssection2]...[/ssection2] - 条款内容（第一条等）
    """
    lines = text.split('\n')
    processed_lines = []
    current_article = []  # 当前正在处理的条款内容
    in_content = False   # 是否处于目录部分
    
    # 1. 主标题处理（第一行包含特定标题时）
    if lines and "中华人民共和国劳动法" in lines[0]:
        processed_lines.append("[title]中华人民共和国劳动法[/title]")
        lines = lines[1:]  # 移除已处理的行
    
    # 2. 目录部分处理
    content_start, content_end = detect_content_range(lines)
    
    if content_start is not None:
        processed_lines.append("[content]")
        # 添加目录内容（原样输出，不加其他标签）
        for line in lines[content_start:content_end]:
            if line.strip():
                processed_lines.append(line.strip())
        processed_lines.append("[/content]")
        lines = lines[content_end:]  # 移除已处理的目录行
    
    # 3. 正文处理（章节和条款）
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 3.1 章节标题处理（如"第一章 总则"）
        chapter_match = re.match(r'^(第[一二三四五六七八九十百]+章)\s*(.*)', line)
        if chapter_match:
            if current_article:  # 关闭上一个章节的条款
                # 移除内部换行，用空格连接
                processed_lines.append("[ssection2]" + " ".join(current_article) + "[/ssection2]")
                current_article = []
            # 添加章节标签
            processed_lines.append(f"[section1]{chapter_match.group(1)} {chapter_match.group(2)}[/section1]")
            continue
            
        # 3.2 条款处理（如"第一条 内容..."）
        article_match = re.match(r'^(第[一二三四五六七八九十百零]+条)\s*(.*)', line)
        if article_match:
            if current_article:  # 关闭上一个条款
                processed_lines.append("[ssection2]" + " ".join(current_article) + "[/ssection2]")
            current_article = [f"{article_match.group(1)} {article_match.group(2)}"]
        elif current_article:
            # 当前条款的后续内容（去除换行）
            current_article.append(line)
        else:
            # 不属于任何结构的普通行
            processed_lines.append(line)
    
    # 4. 处理最后一个未关闭的条款
    if current_article:
        processed_lines.append("[ssection2]" + " ".join(current_article) + "[/ssection2]")
    
    return '\n'.join(processed_lines)

def detect_content_range(lines):
    """
    目录范围检测辅助函数
    返回：(start_index, end_index)
    逻辑：
    1. 找到"目　　录"行作为开始
    2. 持续收集直到：
       - 章节号不连续
       - 遇到非章节标题行
    """
    content_start = None
    content_end = None
    last_chapter_num = 0
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        if "目　　录" in line:
            content_start = i
            continue
            
        if content_start is not None and content_end is None:
            # 检查是否是章节标题
            chapter_match = re.match(r'^第([一二三四五六七八九十百]+)章', line)
            if chapter_match:
                current_num = chinese_to_number(chapter_match.group(1))
                # 连续章节号继续目录
                if current_num == last_chapter_num + 1:
                    last_chapter_num = current_num
                    continue
                else:
                    # 非连续章节号结束目录
                    content_end = i
            elif last_chapter_num > 0:
                # 非章节标题行结束目录
                content_end = i
    
    return content_start, content_end

def chinese_to_number(chinese_str):
    """
    中文数字转阿拉伯数字
    支持范围：0-100
    示例：
      "三" -> 3
      "十二" -> 12
      "二十一" -> 21
    """
    chinese_num = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
        '十六': 16, '十七': 17, '十八': 18, '十九': 19, '二十': 20,
        '三十': 30, '四十': 40, '五十': 50, '六十': 60, '七十': 70,
        '八十': 80, '九十': 90, '百': 100
    }
    # 处理复合数字（如"二十一"=20+1）
    if len(chinese_str) > 1 and chinese_str not in chinese_num:
        total = 0
        for char in chinese_str:
            total += chinese_num.get(char, 0)
        return total
    return chinese_num.get(chinese_str, 0)

def save_parsed_data(parsed_text, original_path, output_dir):
    """
    保存处理结果到文件
    文件按原始格式分类存储（如pdf子目录）
    """
    base_name = os.path.basename(original_path)
    file_ext = os.path.splitext(base_name)[1].lower()[1:]  # 提取扩展名
    
    # 创建格式分类子目录
    sub_dir = os.path.join(output_dir, file_ext)
    os.makedirs(sub_dir, exist_ok=True)
    
    # 生成输出文件名（同名的.txt文件）
    output_name = f"{os.path.splitext(base_name)[0]}.txt"
    output_path = os.path.join(sub_dir, output_name)
    
    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(parsed_text)
    
    print(f"解析结果已保存至: {output_path}")

if __name__ == "__main__":
    # 默认输入输出路径
    input_path = "./original_data"  # 输入目录
    output_dir = "./parsed_document"  # 输出目录
    
    print(f"开始处理文档目录: {input_path}")
    load_and_save_document(input_path, output_dir)
    print("所有文档处理完成!")