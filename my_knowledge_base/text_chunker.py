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
[section1]章节标题[/section1]
[ssection2]法条内容[/ssection2]

输出结果：
1. 每个法条作为一个独立分块，包含所属章节和文档标题信息
2. 目录内容作为单独分块
3. 每个分块保存为独立文本文件
4. 生成包含所有分块元数据的JSON文件

使用方式：
python text_chunker.py

配置参数：
- parsed_dir: 输入文件目录（默认为"parsed_document"）
- output_dir: 输出目录（默认为"chunk_output"）
- chunk_size: 分块大小（默认为500字符）
- chunk_overlap: 分块重叠大小（默认为100字符）
"""

import os
import json
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
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
        current_section1 = ""  # 当前章节标题
        
        # 定义用于匹配各种标签的正则表达式
        title_pattern = re.compile(r'^\[title\](.+?)\[/title\]$')  # 匹配文档标题
        content_pattern = re.compile(r'^\[content\](.+?)\[/content\]$', re.DOTALL)  # 匹配目录内容
        section1_pattern = re.compile(r'^\[section1\](.+?)\[/section1\]$')  # 匹配章节标题
        ssection2_pattern = re.compile(r'^\[ssection2\](.+?)\[/ssection2\]$')  # 匹配法条内容
        
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
                    'section1': '',
                    'content_type': 'table_of_contents'  # 标记为目录内容
                }
                documents.append(Document(
                    page_content=f"{current_title}\n{content_text}",
                    metadata=metadata
                ))
                i += 1
                continue
                
            # 检查是否为章节标题
            section1_match = section1_pattern.match(line)
            if section1_match:
                current_section1 = section1_match.group(1).strip()
                i += 1
                continue
                
            # 检查是否为法条内容
            ssection2_match = ssection2_pattern.match(line)
            if ssection2_match:
                # 创建法条文档块（包含文档标题和章节标题）
                article_text = ssection2_match.group(1).strip()
                metadata = {
                    'title': current_title,
                    'section1': current_section1,
                    'content_type': 'law_article'  # 标记为法条内容
                }
                documents.append(Document(
                    page_content=f"{current_title}\n{current_section1}\n{article_text}",
                    metadata=metadata
                ))
                i += 1
                continue
                
            i += 1  # 处理下一行
        
        return documents

def chunk_and_save_parsed_files(parsed_dir="parsed_document", output_dir="chunk_output", 
                               chunk_size=500, chunk_overlap=100):
    """处理解析后的文档文件，进行结构感知分块并保存
    
    参数:
        parsed_dir: 已解析文档的输入目录
        output_dir: 分块结果输出目录
        chunk_size: 分块大小（字符数）
        chunk_overlap: 分块重叠大小（字符数）
    """
    os.makedirs(output_dir, exist_ok=True)  # 创建输出目录
    
    # 初始化文本分割器（用于处理非法条内容）
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True
    )
    
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
                original_name = os.path.splitext(file_name)[0]  # 获取原始文件名（不含扩展名）
                
                # 使用自定义加载器加载文档
                loader = LawDocumentLoader(file_path)
                documents = loader.load()
                
                # 为当前文件创建输出目录
                file_output_dir = os.path.join(output_dir, file_type, original_name)
                os.makedirs(file_output_dir, exist_ok=True)
                
                # 处理并保存分块结果
                chunk_data = []
                for doc_idx, doc in enumerate(documents):
                    # 法条内容不进行进一步分割
                    if doc.metadata['content_type'] == 'law_article':
                        chunks = [doc]  # 保持原样
                    else:
                        # 其他内容（如目录）使用分割器处理
                        chunks = text_splitter.split_documents([doc])
                    
                    # 处理每个分块
                    for chunk_idx, chunk in enumerate(chunks):
                        # 创建分块文件
                        chunk_file = os.path.join(file_output_dir, f"chunk_{doc_idx+1}_{chunk_idx+1}.txt")
                        with open(chunk_file, 'w', encoding='utf-8') as f:
                            # 处理多余的换行符：将连续多个换行符替换为单个换行符
                            cleaned_content = re.sub(r'\n{2,}', '\n', chunk.page_content)
                            f.write(cleaned_content)
                        
                        # 构建分块元数据
                        chunk_info = {
                            'chunk_id': f"{doc_idx+1}_{chunk_idx+1}",  # 分块ID
                            'text': chunk.page_content,  # 分块文本内容
                            'metadata': {
                                'source': file_path,  # 源文件路径
                                'chunk_path': chunk_file,  # 分块文件路径
                                'file_type': file_type,  # 文件类型
                                'original_name': original_name,  # 原始文件名
                                'title': chunk.metadata.get('title', ''),  # 文档标题
                                'section1': chunk.metadata.get('section1', ''),  # 章节标题
                                'content_type': chunk.metadata.get('content_type', ''),  # 内容类型
                                'start_index': chunk.metadata.get('start_index', 0),  # 起始位置
                                'end_index': chunk.metadata.get('end_index', len(chunk.page_content))  # 结束位置
                            }
                        }
                        chunk_data.append(chunk_info)
                
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
    
    # 设置分块参数
    chunk_size = 500    # 每个分块的最大字符数
    chunk_overlap = 100 # 分块间的重叠字符数
    
    # 执行分块处理
    chunk_and_save_parsed_files(parsed_dir, chunk_output, chunk_size, chunk_overlap)
    print("\n文档分块处理完成!")

if __name__ == "__main__":
    main()