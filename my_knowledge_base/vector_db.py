#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量数据库构建与搜索系统

功能概述：
1. 从分块后的JSON元数据文件创建FAISS向量数据库
2. 支持两种操作模式：新建/覆盖数据库 或 追加到现有数据库
3. 提供交互式搜索功能，用户可输入查询并获取相似结果（包含相似度分数和完整内容）
4. 使用HuggingFace的嵌入模型进行文本向量化

主要功能函数：
1. create_vector_db - 创建或更新向量数据库
2. search_vector_db - 在向量数据库中执行相似性搜索（返回带分数的结果）
3. interactive_search - 提供交互式搜索界面（显示完整内容和相似度）

使用方式：
直接运行脚本，按提示选择操作模式（创建/追加数据库或执行搜索）
"""

import json
import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document

def create_vector_db(metadata_path, embedding_model_path, vector_db_path, mode='create'):
    """创建或更新向量数据库
    
    参数:
        metadata_path: 包含分块数据的JSON文件路径
        embedding_model_path: 嵌入模型路径
        vector_db_path: 向量数据库保存路径
        mode: 操作模式 ('create'新建/覆盖 或 'append'追加)
    """
    # 加载分块数据
    with open(metadata_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    # 准备文档数据
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["text"],
            metadata=chunk["metadata"]
        )
        documents.append(doc)
    
    # 初始化嵌入模型（使用CPU设备）
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_path,
        model_kwargs={'device': 'cpu'}
    )
    
    # 处理数据库操作模式
    if mode == 'append' and os.path.exists(vector_db_path):
        # 追加模式：加载现有数据库并添加新文档
        vector_db = FAISS.load_local(
            folder_path=vector_db_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True
        )
        vector_db.add_documents(documents)
        print(f"已向现有数据库追加 {len(documents)} 个文档")
    else:
        # 创建模式（新建或覆盖）
        if mode == 'append':
            print("警告：未找到现有数据库，将创建新数据库")
        vector_db = FAISS.from_documents(documents, embeddings)
        print(f"已创建包含 {len(documents)} 个文档的新数据库")
    
    # 保存数据库
    os.makedirs(os.path.dirname(vector_db_path), exist_ok=True)
    vector_db.save_local(vector_db_path)
    print(f"向量数据库已保存至: {vector_db_path}")

def search_vector_db(query, vector_db_path, embedding_model_path, k=3):
    """在向量数据库中执行相似性搜索（带分数）
    
    参数:
        query: 查询文本
        vector_db_path: 向量数据库路径
        embedding_model_path: 嵌入模型路径
        k: 返回的最相似结果数量
    
    返回:
        包含搜索结果的列表，每个结果包含排名、内容、元数据和相似度分数
    """
    # 检查数据库是否存在
    if not os.path.exists(vector_db_path):
        print(f"错误：未找到向量数据库 {vector_db_path}")
        return []
    
    # 加载嵌入模型
    embeddings = HuggingFaceEmbeddings(
        model_name=embedding_model_path,
        model_kwargs={'device': 'cpu'}
    )
    
    # 安全加载向量数据库
    vector_db = FAISS.load_local(
        folder_path=vector_db_path,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )
    
    # 执行带分数的相似性搜索
    results = vector_db.similarity_search_with_score(query, k=k)
    
    # 整理结果
    search_results = []
    for i, (doc, score) in enumerate(results):
        search_results.append({
            "rank": i+1,
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score)  # 将numpy.float32转换为Python float
        })
    
    return search_results

def interactive_search(vector_db_path, embedding_model_path):
    """提供交互式搜索界面（显示完整内容和相似度）
    
    参数:
        vector_db_path: 向量数据库路径
        embedding_model_path: 嵌入模型路径
    """
    print("\n=== 进入交互式搜索模式 ===")
    print("输入'退出'或'quit'可结束搜索")
    
    while True:
        # 获取用户查询
        query = input("\n请输入搜索内容: ").strip()
        
        # 检查退出条件
        if query.lower() in ['退出', 'quit']:
            print("结束搜索")
            break
        
        if not query:
            print("搜索内容不能为空")
            continue
        
        # 执行带分数的搜索
        results = search_vector_db(
            query=query,
            vector_db_path=vector_db_path,
            embedding_model_path=embedding_model_path,
            k=3  # 返回前3个最相似结果
        )
        
        # 显示完整结果
        if not results:
            print("未找到相关结果")
        else:
            print(f"\n找到 {len(results)} 个相关结果:")
            for result in results:
                print("\n" + "=" * 80)
                print(f"排名: {result['rank']}")
                print(f"相似距离: {result['score']:.4f}")  # 显示4位小数
                print(f"来源: {result['metadata'].get('source', '未知')}")
                print("\n完整内容:")
                print(result['content'])
                print("=" * 80)

if __name__ == "__main__":
    # 配置路径
    METADATA_PATH = "./chunk_output/docx/劳动法/metadata.json"
    EMBEDDING_MODEL_PATH = "../embedding_model/all-MiniLM-L6-v2"
    VECTOR_DB_PATH = "./vector_db/faiss_index"
    
    # 主交互界面
    while True:
        print("\n=== 向量数据库系统 ===")
        print("1. 新建/覆盖数据库")
        print("2. 追加到现有数据库")
        print("3. 执行搜索")
        print("4. 退出")
        
        user_input = input("请选择操作(1/2/3/4): ").strip()
        
        if user_input == '1':
            # 创建/覆盖数据库模式
            create_vector_db(
                metadata_path=METADATA_PATH,
                embedding_model_path=EMBEDDING_MODEL_PATH,
                vector_db_path=VECTOR_DB_PATH,
                mode='create'
            )
        elif user_input == '2':
            # 追加到现有数据库模式
            create_vector_db(
                metadata_path=METADATA_PATH,
                embedding_model_path=EMBEDDING_MODEL_PATH,
                vector_db_path=VECTOR_DB_PATH,
                mode='append'
            )
        elif user_input == '3':
            # 进入交互式搜索模式
            interactive_search(
                vector_db_path=VECTOR_DB_PATH,
                embedding_model_path=EMBEDDING_MODEL_PATH
            )
        elif user_input == '4':
            print("退出系统")
            break
        else:
            print("无效输入，请重新选择")