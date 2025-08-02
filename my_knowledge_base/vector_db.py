#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
向量数据库构建与搜索系统（ChromaDB + MiniLM）

功能特点：
1. 使用轻量级ChromaDB向量数据库，支持本地持久化
2. 直接集成Sentence Transformers的MiniLM嵌入模型
3. 元数据过滤优化，利用法律文档结构信息
4. 支持增量更新和高效搜索
5. 低显存占用（<1GB内存处理百万级向量）

使用方式：
直接运行脚本，按提示选择操作模式
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Union

# 配置常量
EMBEDDING_MODEL_NAME = "../embedding_model/ChatLaw-Text2Vec"
VECTOR_DB_PATH = "./vector_db/chroma_data"
COLLECTION_NAME = "law_documents"

def create_vector_db(metadata_path: str, vector_db_path: str, mode: str = 'create') -> None:
    """创建或更新ChromaDB向量数据库
    
    参数:
        metadata_path: 包含分块数据的JSON文件路径
        vector_db_path: 向量数据库保存路径
        mode: 操作模式 ('create'新建/覆盖 或 'append'追加)
    """
    # 加载分块数据
    with open(metadata_path, 'r', encoding='utf-8') as f:
        chunks = json.load(f)
    
    print(f"加载 {len(chunks)} 个文档块...")
    
    # 准备ChromaDB数据
    documents = []
    metadatas = []
    ids = []
    
    for idx, chunk in enumerate(chunks):
        documents.append(chunk["text"])
        metadatas.append({
            "source": chunk["metadata"]["source"],
            "file_type": chunk["metadata"]["file_type"],
            "original_name": chunk["metadata"]["original_name"],
            "title": chunk["metadata"]["title"],
            "section0": chunk["metadata"]["section0"],
            "section1": chunk["metadata"]["section1"],
            "section2": chunk["metadata"]["section2"],
            "section3": chunk["metadata"]["section3"],
            "content_type": chunk["metadata"]["content_type"],
            "chunk_path": chunk["metadata"]["chunk_path"],
            "char_count": chunk["metadata"]["char_count"]
        })
        ids.append(f"doc_{idx}")

    # 初始化Chroma客户端和嵌入模型
    client = chromadb.PersistentClient(path=vector_db_path)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL_NAME
    )
    
    # 处理操作模式
    if mode == 'create':
        # 创建新集合（覆盖现有）
        try:
            client.delete_collection(COLLECTION_NAME)
        except:
            pass  # 集合不存在
        
        collection = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=sentence_transformer_ef,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )
        print(f"创建新集合: {COLLECTION_NAME}")
    else:
        # 追加模式
        try:
            collection = client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=sentence_transformer_ef
            )
            print(f"加载现有集合: {COLLECTION_NAME}")
        except:
            print("集合不存在，创建新集合")
            collection = client.create_collection(
                name=COLLECTION_NAME,
                embedding_function=sentence_transformer_ef
            )
    
    # 批量添加文档
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        
        collection.add(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )
        print(f"添加文档: {i+1}-{min(i+batch_size, len(documents))}/{len(documents)}")
    
    print(f"向量数据库已保存至: {vector_db_path}")
    print(f"集合统计: {collection.count()} 个文档")

def search_vector_db(
    query: str, 
    vector_db_path: str, 
    k: int = 3,
    filter_conditions: Dict[str, Union[str, int]] = None,
    embedding_model_path: str = None  # 添加新参数
) -> List[Dict]:
    """在向量数据库中执行相似性搜索
    
    参数:
        query: 查询文本
        vector_db_path: 向量数据库路径
        k: 返回的最相似结果数量
        filter_conditions: 元数据过滤条件
        embedding_model_path: 嵌入模型路径（可选）
    """
    # 使用传入的模型路径，如果没有则使用默认值
    model_name = embedding_model_path if embedding_model_path else EMBEDDING_MODEL_NAME
    
    # 初始化Chroma客户端
    client = chromadb.PersistentClient(path=vector_db_path)
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name  # 使用动态模型路径
    )
    
    try:
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=sentence_transformer_ef
        )
    except:
        print(f"错误：未找到集合 {COLLECTION_NAME}")
        return []
    
    # 构建查询条件
    where_clause = {}
    if filter_conditions:
        for key, value in filter_conditions.items():
            where_clause[key] = value
    
    # 执行查询
    results = collection.query(
        query_texts=[query],
        n_results=k,
        where=where_clause if where_clause else None,
        include=["documents", "metadatas", "distances"]
    )
    
    # 处理结果
    search_results = []
    for i in range(len(results["ids"][0])):
        doc_id = results["ids"][0][i]
        content = results["documents"][0][i]
        metadata = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        
        # 转换距离为相似度分数 (1 - 余弦距离)
        similarity = 1 - distance
        
        search_results.append({
            "rank": i+1,
            "content": content,
            "metadata": metadata,
            "similarity": float(similarity)  # 转换为Python float
        })
    
    return search_results

def interactive_search(vector_db_path: str) -> None:
    """提供交互式搜索界面（显示完整内容和相似度）"""
    print("\n=== 法律文档交互式搜索 ===")
    print("输入'退出'或'quit'可结束搜索")
    print("输入'过滤'可添加元数据过滤条件")
    
    # 当前过滤条件
    current_filters = {}
    
    while True:
        # 获取用户查询
        query = input("\n请输入搜索内容: ").strip()
        
        # 检查退出条件
        if query.lower() in ['退出', 'quit']:
            print("结束搜索")
            break
        
        if query.lower() == '过滤':
            print("\n当前过滤条件:", current_filters if current_filters else "无")
            print("可用的过滤字段: title, section0, section1, section2, section3, content_type")
            field = input("输入过滤字段: ").strip()
            value = input(f"输入 {field} 的过滤值: ").strip()
            
            if field and value:
                current_filters[field] = value
                print(f"已添加过滤条件: {field}={value}")
            continue
        
        if not query:
            print("搜索内容不能为空")
            continue
        
        # 执行搜索
        results = search_vector_db(
            query=query,
            vector_db_path=vector_db_path,
            k=3,
            filter_conditions=current_filters
        )
        
        # 显示结果
        if not results:
            print("\n未找到相关结果")
        else:
            print(f"\n找到 {len(results)} 个相关结果:")
            for result in results:
                print("\n" + "=" * 80)
                print(f"排名: {result['rank']}")
                print(f"相似度: {result['similarity']:.4f}")
                print(f"标题: {result['metadata'].get('title', '')}")
                
                # 显示层级信息
                hierarchy = []
                if result['metadata'].get('section0'):
                    hierarchy.append(f"编: {result['metadata']['section0']}")
                if result['metadata'].get('section1'):
                    hierarchy.append(f"章: {result['metadata']['section1']}")
                if result['metadata'].get('section2'):
                    hierarchy.append(f"节: {result['metadata']['section2']}")
                if result['metadata'].get('section3'):
                    hierarchy.append(f"小节: {result['metadata']['section3']}")
                
                if hierarchy:
                    print("层级: " + " → ".join(hierarchy))
                
                print(f"来源: {result['metadata'].get('source', '未知')}")
                print("\n内容预览:")
                # 显示前200个字符的预览
                preview = result['content'][:200] + ('...' if len(result['content']) > 200 else '')
                print(preview)
                print("=" * 80)
                
                # 提供查看完整内容的选项
                full_content = input("输入 'f' 查看完整内容，或直接回车继续: ").strip()
                if full_content.lower() == 'f':
                    print("\n" + "=" * 80)
                    print("完整内容:")
                    print(result['content'])
                    print("=" * 80)

def main_menu():
    """主菜单界面"""
    while True:
        print("\n=== 法律文档向量数据库系统 ===")
        print("1. 新建/覆盖数据库")
        print("2. 追加到现有数据库")
        print("3. 执行搜索")
        print("4. 退出系统")
        
        choice = input("请选择操作(1-4): ").strip()
        
        if choice == '1':
            metadata_path = input("输入元数据JSON路径(默认: ./chunk_output/民法典/metadata.json): ") \
                or "./chunk_output/docx/民法典/metadata.json"
            create_vector_db(metadata_path, VECTOR_DB_PATH, 'create')
        elif choice == '2':
            metadata_path = input("输入元数据JSON路径(默认: ./chunk_output/民法典/metadata.json): ") \
                or "./chunk_output/docx/民法典/metadata.json"
            create_vector_db(metadata_path, VECTOR_DB_PATH, 'append')
        elif choice == '3':
            interactive_search(VECTOR_DB_PATH)
        elif choice == '4':
            print("退出系统")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    # 检查并创建向量数据库目录
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    
    # 启动主菜单
    main_menu()