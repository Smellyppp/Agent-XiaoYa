#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
法律文档结构化分块处理器

功能概述：
1. 加载具有特定标记结构的法律文档（支持txt格式）
2. 解析文档中的标题、章节和法条内容
3. 根据文档结构进行智能分块处理
4. 保存分块结果及元数据信息

文档结构要求：
[title]文档标题[/title]
[content]目录内容[/content]
[section0]编标题[/section0]  (可选)
[section1]章标题[/section1]
[section2]节标题[/section2]
[section3]小节标题[/section3]  (可选)
[article]法条内容[/article]

输出结果：
1. 每个法条块包含完整的层级信息
2. 目录内容作为单独分块
3. 每个分块保存为独立文本文件
4. 生成包含所有分块元数据的JSON文件

使用方式：
python text_chunker.py

配置参数：
- parsed_dir: 输入文件目录（默认为"parsed_document"）
- output_dir: 输出目录（默认为"chunk_output"）
"""

import os
import json
import re
from langchain.docstore.document import Document
from langchain_community.document_loaders.base import BaseLoader

class LawDocumentLoader(BaseLoader):
    """法律文档加载器，用于处理具有特定标记结构的法律文本"""
    
    def __init__(self, file_path: str):
        """初始化加载器
        参数:
            file_path: 要加载的文件路径
        """
        self.file_path = file_path
        
    def load(self):
        """加载并解析文档，保留结构信息
        
        返回:
            包含文档结构和内容的Document对象列表
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        documents = []  # 存储解析后的文档块
        current_title = ""  # 当前文档标题
        current_section0 = ""  # 当前编标题
        current_section1 = ""  # 当前章标题
        current_section2 = ""  # 当前节标题
        current_section3 = ""  # 当前小节标题
        
        # 定义用于匹配各种标签的正则表达式
        title_pattern = re.compile(r'^\[title\](.+?)\[/title\]$')  # 匹配文档标题
        content_pattern = re.compile(r'^\[content\](.+?)\[/content\]$', re.DOTALL)  # 匹配目录内容
        section0_pattern = re.compile(r'^\[section0\](.+?)\[/section0\]$')  # 匹配编标题
        section1_pattern = re.compile(r'^\[section1\](.+?)\[/section1\]$')  # 匹配章标题
        section2_pattern = re.compile(r'^\[section2\](.+?)\[/section2\]$')  # 匹配节标题
        section3_pattern = re.compile(r'^\[section3\](.+?)\[/section3\]$')  # 匹配小节标题
        article_pattern = re.compile(r'^\[article\](.+?)\[/article\]$', re.DOTALL)        
        # 状态变量
        current_articles = []  # 当前收集的法条内容
        has_section3 = False   # 当前节下是否有小节
        
        def create_chunk():
            """创建并添加一个法条块"""
            if current_articles:
                # 构建块内容
                chunk_content = ""
                if current_title:
                    chunk_content += f"【标题】{current_title}\n"
                if current_section0:
                    chunk_content += f"【编】{current_section0}\n"
                if current_section1:
                    chunk_content += f"【章】{current_section1}\n"
                if current_section2:
                    chunk_content += f"【节】{current_section2}\n"
                if current_section3:
                    chunk_content += f"【小节】{current_section3}\n"
                
                # 添加所有法条内容
                chunk_content += "\n".join(current_articles)
                
                # 构建元数据
                metadata = {
                    'title': current_title,
                    'section0': current_section0,
                    'section1': current_section1,
                    'section2': current_section2,
                    'section3': current_section3,
                    'content_type': 'law_chunk',  # 标记为法律块
                    'articles': current_articles[:]  # 保存原始法条列表
                }
                
                documents.append(Document(
                    page_content=chunk_content,
                    metadata=metadata
                ))
        
        
        # 逐行处理文档内容
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检查是否为文档标题
            title_match = title_pattern.match(line)
            if title_match:
                current_title = title_match.group(1).strip()
                i += 1
                continue
                
            # 检查是否为目录内容
            content_match = content_pattern.match(line)
            if content_match:
                # 创建目录内容文档块
                content_text = content_match.group(1).strip()
                metadata = {
                    'title': current_title,
                    'section0': '',
                    'section1': '',
                    'section2': '',
                    'section3': '',
                    'content_type': 'table_of_contents'  # 标记为目录内容
                }
                documents.append(Document(
                    page_content=f"{current_title}\n{content_text}",
                    metadata=metadata
                ))
                i += 1
                continue
                
            # 检查是否为编标题
            section0_match = section0_pattern.match(line)
            if section0_match:
                # 编变化时完成当前块
                create_chunk()
                current_articles = []
                current_section0 = section0_match.group(1).strip()
                current_section1 = ""
                current_section2 = ""
                current_section3 = ""
                has_section3 = False
                i += 1
                continue
                
            # 检查是否为章标题
            section1_match = section1_pattern.match(line)
            if section1_match:
                # 章变化时完成当前块
                create_chunk()
                current_articles = []
                current_section1 = section1_match.group(1).strip()
                current_section2 = ""
                current_section3 = ""
                has_section3 = False
                i += 1
                continue
                
            # 检查是否为节标题
            section2_match = section2_pattern.match(line)
            if section2_match:
                # 节变化时完成当前块
                create_chunk()
                current_articles = []
                current_section2 = section2_match.group(1).strip()
                current_section3 = ""
                has_section3 = False  # 重置小节状态
                i += 1
                continue
                
            # 检查是否为小节标题
            section3_match = section3_pattern.match(line)
            if section3_match:
                # 小节变化时完成当前块
                create_chunk()
                current_articles = []
                current_section3 = section3_match.group(1).strip()
                has_section3 = True  # 标记存在小节
                i += 1
                continue
                
            # 检查是否为法条内容
            article_match = article_pattern.match(line)
            if article_match:
                article_text = article_match.group(1).strip()
                # 去除原始标签格式
                current_articles.append(article_text)
                i += 1
                continue
                
            # 处理未标记的文本行（添加到当前法条）
            if current_articles and line:
                # 添加到最后一个法条
                current_articles[-1] += "\n" + line
                
            i += 1  # 处理下一行
        
        # 处理最后一个块
        create_chunk()
        
        return documents

def split_law_chunk(doc, max_size=1000):
    """分割法律块，确保法条不被中断且每个分块包含完整标题信息"""
    chunks = []
    
    # 提取标题信息
    title_info = ""
    if doc.metadata['title']:
        title_info += f"【标题】{doc.metadata['title']}\n"
    if doc.metadata['section0']:
        title_info += f"【编】{doc.metadata['section0']}\n"
    if doc.metadata['section1']:
        title_info += f"【章】{doc.metadata['section1']}\n"
    if doc.metadata['section2']:
        title_info += f"【节】{doc.metadata['section2']}\n"
    if doc.metadata['section3']:
        title_info += f"【小节】{doc.metadata['section3']}\n"
    
    current_chunk = title_info
    articles = doc.metadata.get('articles', [])
    
    for article in articles:
        # 如果添加当前法条会超过限制，且当前块已有内容，则完成当前块
        if len(current_chunk) + len(article) > max_size and len(current_chunk) > len(title_info):
            chunks.append(current_chunk)
            current_chunk = title_info  # 新块以标题信息开头
        
        # 添加法条到当前块
        if current_chunk == title_info:  # 如果是新块的第一条
            current_chunk += article
        else:
            current_chunk += "\n" + article
    
    # 添加最后一个块
    if current_chunk != title_info:
        chunks.append(current_chunk)
    
    return chunks


def chunk_and_save_parsed_files(parsed_dir="parsed_document", output_dir="chunk_output"):
    """处理解析后的文档文件，进行结构感知分块并保存"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 遍历所有文件类型目录（docx/pdf/txt）
    for file_type in ['docx', 'pdf', 'txt']:
        type_dir = os.path.join(parsed_dir, file_type)
        if not os.path.exists(type_dir):
            print(f"目录不存在: {type_dir}，跳过...")
            continue
            
        print(f"\n正在处理 {file_type.upper()} 文件:")
        for file_name in os.listdir(type_dir):
            if file_name.endswith('.txt'):
                file_path = os.path.join(type_dir, file_name)
                original_name = os.path.splitext(file_name)[0]
                
                # 使用自定义加载器加载文档
                loader = LawDocumentLoader(file_path)
                documents = loader.load()
                
                # 为当前文件创建输出目录
                file_output_dir = os.path.join(output_dir, file_type, original_name)
                os.makedirs(file_output_dir, exist_ok=True)
                
                # 处理并保存分块结果
                chunk_data = []
                chunk_counter = 1
                
                for doc in documents:
                    if doc.metadata['content_type'] == 'table_of_contents':
                        # 目录内容直接保存
                        chunk_file = os.path.join(file_output_dir, f"chunk_{chunk_counter}.txt")
                        with open(chunk_file, 'w', encoding='utf-8') as f:
                            cleaned_content = re.sub(r'\n{2,}', '\n\n', doc.page_content)
                            f.write(cleaned_content)
                        
                        # 构建分块元数据
                        chunk_info = {
                            'chunk_id': str(chunk_counter),
                            'text': doc.page_content,
                            'metadata': {
                                'source': file_path,
                                'chunk_path': chunk_file,
                                'file_type': file_type,
                                'original_name': original_name,
                                'title': doc.metadata.get('title', ''),
                                'section0': doc.metadata.get('section0', ''),
                                'section1': doc.metadata.get('section1', ''),
                                'section2': doc.metadata.get('section2', ''),
                                'section3': doc.metadata.get('section3', ''),
                                'content_type': doc.metadata.get('content_type', ''),
                                'char_count': len(doc.page_content)  # 添加字符数统计
                            }
                        }
                        chunk_data.append(chunk_info)
                        chunk_counter += 1
                    else:
                        # 法律内容需要分割
                        chunks = split_law_chunk(doc, max_size=1000)
                        
                        for chunk_content in chunks:
                            chunk_file = os.path.join(file_output_dir, f"chunk_{chunk_counter}.txt")
                            with open(chunk_file, 'w', encoding='utf-8') as f:
                                cleaned_content = re.sub(r'\n{2,}', '\n\n', chunk_content)
                                f.write(cleaned_content)
                            
                            # 构建分块元数据
                            chunk_info = {
                                'chunk_id': str(chunk_counter),
                                'text': chunk_content,
                                'metadata': {
                                    'source': file_path,
                                    'chunk_path': chunk_file,
                                    'file_type': file_type,
                                    'original_name': original_name,
                                    'title': doc.metadata.get('title', ''),
                                    'section0': doc.metadata.get('section0', ''),
                                    'section1': doc.metadata.get('section1', ''),
                                    'section2': doc.metadata.get('section2', ''),
                                    'section3': doc.metadata.get('section3', ''),
                                    'content_type': doc.metadata.get('content_type', ''),
                                    'char_count': len(chunk_content)  # 添加字符数统计
                                }
                            }
                            chunk_data.append(chunk_info)
                            chunk_counter += 1
                
                # 保存元数据到JSON文件
                metadata_file = os.path.join(file_output_dir, "metadata.json")
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(chunk_data, f, ensure_ascii=False, indent=2)
                
                print(f"已处理 {file_name}: 生成 {len(chunk_data)} 个分块")
def main():
    """主函数，执行文档分块处理流程"""
    # 设置输入输出目录
    parsed_dir = "parsed_document"  # 输入目录（已解析的文档）
    chunk_output = "chunk_output"   # 输出目录（分块结果）
    
    print(f"开始文档分块处理...")
    print(f"输入目录: {parsed_dir}")
    print(f"输出目录: {chunk_output}")
    
    # 执行分块处理
    chunk_and_save_parsed_files(parsed_dir, chunk_output)
    print("\n文档分块处理完成!")

if __name__ == "__main__":
    main()