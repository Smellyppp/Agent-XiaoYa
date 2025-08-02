#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG检索性能评估系统

功能指标：
1. 检索速度测试（响应延迟、吞吐量）
2. 检索质量评估（命中率、相似度分布）
3. 准确率验证（人工标注对比）
4. 元数据过滤效率测试

使用方式：
直接运行脚本即可执行评估
"""

import time
import json
import os
import numpy as np
from typing import List, Dict
from collections import defaultdict
from chromadb.utils import embedding_functions
import chromadb

# ================================
# 配置文件路径（请根据实际情况修改）
# ================================
VECTOR_DB_PATH = "./vector_db/chroma_data"  # 向量数据库路径
EMBEDDING_MODEL_PATH = "../embedding_model/all-MiniLM-L6-v2"  # 嵌入模型路径
GOLDEN_SET_PATH = "./golden_set.json"  # 人工标注数据集路径
COLLECTION_NAME = "law_documents"  # 集合名称

# ================================
# 默认测试数据集（当GOLDEN_SET_PATH不存在时使用）
# ================================
DEFAULT_GOLDEN_SET = [
    {
        "query": "合同无效的情形",
        "expected_sections": ["合同编"],
        "expected_articles": [58, 144]
    },
    {
        "query": "离婚财产分割",
        "expected_sections": ["婚姻家庭编"],
        "expected_articles": [1087, 1088]
    },
    {
        "query": "侵权责任的构成要件",
        "expected_sections": ["侵权责任编"],
        "expected_articles": [1165, 1166]
    },
    {
        "query": "遗嘱的有效条件",
        "expected_sections": ["继承编"],
        "expected_articles": [1134, 1139]
    },
    {
        "query": "不动产物权登记效力",
        "expected_sections": ["物权编"],
        "expected_articles": [209, 214]
    }
]

class RAGEvaluator:
    def __init__(self):
        """初始化评估器"""
        # 创建嵌入模型
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL_PATH
        )
        
        # 加载向量数据库
        self.collection = self._load_vector_db()
        
        # 加载测试数据集
        self.test_queries = self._load_test_queries()
        
        print(f"评估系统初始化完成，共加载 {len(self.test_queries)} 个测试查询")

    def _load_vector_db(self):
        """加载向量数据库集合"""
        try:
            # 创建持久化客户端
            client = chromadb.PersistentClient(path=VECTOR_DB_PATH)
            
            # 获取集合
            collection = client.get_collection(
                name=COLLECTION_NAME,
                embedding_function=self.embedding_fn
            )
            
            print(f"成功加载向量数据库: {VECTOR_DB_PATH}")
            print(f"集合 '{COLLECTION_NAME}' 包含 {collection.count()} 个文档")
            return collection
        except Exception as e:
            print(f"加载向量数据库失败: {str(e)}")
            print("请检查路径配置或先创建向量数据库")
            exit(1)

    def _load_test_queries(self) -> List[Dict]:
        """加载测试查询集"""
        # 检查是否存在标注数据集文件
        if os.path.exists(GOLDEN_SET_PATH):
            try:
                with open(GOLDEN_SET_PATH, 'r', encoding='utf-8') as f:
                    golden_data = json.load(f)
                print(f"从文件加载测试数据集: {GOLDEN_SET_PATH}")
                return golden_data
            except Exception as e:
                print(f"加载测试数据集失败: {str(e)}，使用内置默认数据")
        
        # 如果文件不存在或加载失败，使用默认数据集
        print("使用内置默认测试数据集")
        return DEFAULT_GOLDEN_SET

    def evaluate_speed(self, num_runs: int = 5) -> Dict:
        """评估检索速度"""
        print("\n=== 开始检索速度评估 ===")
        latencies = []
        
        for i in range(num_runs):
            for query in self.test_queries:
                start_time = time.perf_counter()
                
                # 执行查询
                self.collection.query(
                    query_texts=[query["query"]],
                    n_results=3,
                    include=["distances"]
                )
                
                latency = (time.perf_counter() - start_time) * 1000  # 毫秒
                latencies.append(latency)
                print(f"查询: '{query['query'][:15]}...' 延迟: {latency:.2f}ms")
        
        avg_latency = np.mean(latencies)
        throughput = 1000 / avg_latency if avg_latency > 0 else float('inf')
        
        results = {
            "avg_latency_ms": avg_latency,
            "min_latency_ms": np.min(latencies),
            "max_latency_ms": np.max(latencies),
            "throughput_qps": throughput,
            "num_queries": len(self.test_queries) * num_runs
        }
        
        print(f"平均延迟: {avg_latency:.2f}ms | 吞吐量: {throughput:.2f} QPS")
        return results

    def evaluate_quality(self) -> Dict:
        """评估检索质量"""
        print("\n=== 开始检索质量评估 ===")
        similarity_scores = []
        hit_counts = defaultdict(int)
        total_results = 0
        
        for query in self.test_queries:
            results = self.collection.query(
                query_texts=[query["query"]],
                n_results=3,
                include=["metadatas", "distances"]
            )
            
            # 记录相似度分数
            distances = results["distances"][0]
            similarities = [1 - d for d in distances]
            similarity_scores.extend(similarities)
            
            # 检查是否命中预期章节
            for i, meta in enumerate(results["metadatas"][0]):
                total_results += 1
                for sec in query["expected_sections"]:
                    if sec in meta.get("section1", ""):
                        hit_counts["section_hits"] += 1
                        print(f"✅ 查询: '{query['query']}' - 结果{i+1}命中预期章节")
                        break
                else:
                    print(f"❌ 查询: '{query['query']}' - 结果{i+1}未命中预期章节")
        
        section_hit_rate = hit_counts["section_hits"] / total_results if total_results > 0 else 0
        
        results = {
            "avg_similarity": np.mean(similarity_scores),
            "top1_similarity": np.mean([s[0] for s in np.array_split(similarity_scores, len(self.test_queries))]),
            "section_hit_rate": section_hit_rate,
            "similarity_distribution": {
                "min": np.min(similarity_scores),
                "max": np.max(similarity_scores),
                "std": np.std(similarity_scores)
            }
        }
        
        print(f"平均相似度: {results['avg_similarity']:.4f} | 章节命中率: {section_hit_rate:.2%}")
        return results

    def evaluate_accuracy(self) -> Dict:
        """对比人工标注结果评估准确率"""
        print("\n=== 开始检索准确率评估 ===")
        correct_counts = 0
        total_queries = len(self.test_queries)
        
        for query in self.test_queries:
            results = self.collection.query(
                query_texts=[query["query"]],
                n_results=1,
                include=["metadatas"]
            )
            
            # 提取法条ID（简化版）
            found_articles = []
            for meta in results["metadatas"][0]:
                # 从元数据中提取法条ID（实际应根据文档结构实现）
                article_id = self._extract_article_id(meta)
                if article_id is not None:
                    found_articles.append(article_id)
            
            # 检查是否命中预期法条
            if any(aid in query["expected_articles"] for aid in found_articles):
                correct_counts += 1
                print(f"✅ 查询: '{query['query']}' - 命中预期法条")
            else:
                print(f"❌ 查询: '{query['query']}' - 未命中预期法条")
        
        accuracy = correct_counts / total_queries if total_queries > 0 else 0
        print(f"准确率: {accuracy:.2%} ({correct_counts}/{total_queries})")
        return {
            "accuracy": accuracy,
            "correct_counts": correct_counts,
            "total_queries": total_queries
        }
    
    def _extract_article_id(self, metadata: Dict) -> int:
        """从元数据中提取法条ID（示例实现）"""
        # 实际实现应基于具体的元数据结构
        # 这里只是一个示例，您需要根据实际情况修改
        content = metadata.get("content", "")
        if "第" in content and "条" in content:
            try:
                # 尝试提取法条编号
                start_idx = content.index("第") + 1
                end_idx = content.index("条", start_idx)
                article_num = content[start_idx:end_idx].strip()
                return int(article_num) if article_num.isdigit() else None
            except:
                return None
        return None

    def evaluate_filters(self) -> Dict:
        """评估元数据过滤效率"""
        print("\n=== 开始元数据过滤效率评估 ===")
        base_time = []
        filtered_time = []
        
        for query in self.test_queries:
            if not query["expected_sections"]:
                continue
                
            # 无过滤基准测试
            start = time.perf_counter()
            self.collection.query(
                query_texts=[query["query"]],
                n_results=3
            )
            base_time.append(time.perf_counter() - start)
            
            # 带过滤测试
            start = time.perf_counter()
            self.collection.query(
                query_texts=[query["query"]],
                n_results=3,
                where={"section1": query["expected_sections"][0]}
            )
            filtered_time.append(time.perf_counter() - start)
        
        avg_base_time = np.mean(base_time) * 1000 if base_time else 0
        avg_filtered_time = np.mean(filtered_time) * 1000 if filtered_time else 0
        overhead = avg_filtered_time - avg_base_time
        
        results = {
            "avg_base_time_ms": avg_base_time,
            "avg_filtered_time_ms": avg_filtered_time,
            "filter_overhead_ms": overhead
        }
        
        print(f"基础查询时间: {avg_base_time:.2f}ms | 带过滤查询时间: {avg_filtered_time:.2f}ms")
        print(f"过滤开销: {overhead:.2f}ms ({overhead/avg_base_time*100:.1f}%)")
        return results

    def run_full_evaluation(self) -> Dict:
        """执行完整评估流程"""
        print("\n" + "="*50)
        print("开始RAG系统性能评估")
        print("="*50)
        print(f"向量数据库: {VECTOR_DB_PATH}")
        print(f"嵌入模型: {EMBEDDING_MODEL_PATH}")
        print(f"测试数据集: {GOLDEN_SET_PATH if os.path.exists(GOLDEN_SET_PATH) else '内置默认数据集'}")
        
        start_time = time.perf_counter()
        
        metrics = {
            "speed": self.evaluate_speed(),
            "quality": self.evaluate_quality(),
            "accuracy": self.evaluate_accuracy(),
            "filter_efficiency": self.evaluate_filters(),
            "evaluation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vector_db_path": VECTOR_DB_PATH,
            "embedding_model": EMBEDDING_MODEL_PATH
        }
        
        total_time = time.perf_counter() - start_time
        
        print("\n" + "="*50)
        print("评估结果摘要")
        print("="*50)
        print(f"平均延迟: {metrics['speed']['avg_latency_ms']:.2f}ms")
        print(f"平均相似度: {metrics['quality']['avg_similarity']:.4f}")
        print(f"章节命中率: {metrics['quality']['section_hit_rate']:.2%}")
        print(f"准确率: {metrics['accuracy']['accuracy']:.2%}")
        print(f"过滤开销: {metrics['filter_efficiency']['filter_overhead_ms']:.2f}ms")
        print(f"总评估时间: {total_time:.2f}秒")
        
        # 保存详细结果
        metrics["total_evaluation_time_sec"] = total_time
        output_file = "rag_evaluation_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        print(f"\n详细评估结果已保存至: {output_file}")
        return metrics

if __name__ == "__main__":
    # 确保向量数据库目录存在
    os.makedirs(os.path.dirname(VECTOR_DB_PATH), exist_ok=True)
    
    # 确保嵌入模型目录存在
    os.makedirs(os.path.dirname(EMBEDDING_MODEL_PATH), exist_ok=True)
    
    # 如果标注数据集不存在，创建默认数据集
    if not os.path.exists(GOLDEN_SET_PATH):
        with open(GOLDEN_SET_PATH, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_GOLDEN_SET, f, indent=2, ensure_ascii=False)
        print(f"创建默认标注数据集: {GOLDEN_SET_PATH}")
    
    # 执行评估
    evaluator = RAGEvaluator()
    evaluator.run_full_evaluation()