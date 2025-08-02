# 智能法律顾问 Agent

本项目是一个基于 Qwen3-0.6B 大模型的智能法律顾问系统(框架)，集成了法律咨询、数据库搜索、知识库检索等功能，支持自然语言交互和多工具调用，适合法律服务、智能问答等场景。

---

## 项目说明

- **法律智能问答**：目前主要支持民法典的智能检索与专业解答。
- **案例搜索**：可自动联网检索最新法律案例，辅助用户了解相关事件。
- **知识库管理**：支持文档解析、分块、向量化、检索等全流程。
- **多模态前端**：提供网页端交互界面，体验友好。
- **可扩展性强**：API、模型、知识库均可灵活替换和扩展。

---


## 项目演示

➡️[查看交互式演示](https://smellyppp.github.io/Agent-XiaoYa/demo/demo.html)
---

## 主要技术栈

| 技术/库               | 作用                       |
|-----------------------|----------------------------|
| Python               | 主开发语言                 |
| PyTorch              | 深度学习框架               |
| Transformers         | NLP模型库                  |
| Qwen3-0.6B           | 大语言模型                 |
| sentence-transformers| 文本嵌入模型               |
| Chroma               | 向量数据库                 |
| LangChain            | 文档处理/分块/加载         |
| Requests             | HTTP请求                   |
| Flask/FastAPI        | 后端API服务                |
| HTML/CSS/JS          | 前端页面                   |
| searxng              | 免费搜索引擎（可API）       |
---

## 项目结构

```
Agent/
├── main.py                      # 项目主入口
├── config.py                    # 配置文件（API密钥等）
├── prompt_templates.py          # 统一提示词模板
├── api_integration/             # 外部API集成
│   ├── case_search.py           # 法律案例API
│   ├── weather_api.py           # 天气API（暂未接入）
├── my_knowledge_base/           # 知识库相关
│   ├── file_processor.py        # 文档预处理
│   ├── text_chunker.py          # 文本分块
│   ├── vector_db.py             # 向量数据库管理
│   ├── parsed_document/         # 预处理结果
│   ├── chunk_output/            # 分块结果
│   └── vector_db/               # 向量数据库文件
├── embedding_model/             # 嵌入模型
│   └── ChatLaw-Text2Vec/        # 句向量模型
├── model/
│   └── Qwen3-0.6B/              # 大语言模型文件
├── backend/                     # 后端API服务
│   ├── app.py                   # API主程序
│   ├── legal_advisor.py         # 法律顾问核心
├── frontend/                    # 前端页面与资源
│   ├── index.html
│   ├── style.css
│   ├── script.js
├── tests/                       # 某些测试脚本
├── requirements.txt             # 依赖包列表
├── README.md                    # 项目说明文档
```

---

---

## 快速开始

1. 安装 Python 3.10+，建议使用虚拟环境。
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 下载并放置 Qwen3-0.6B 模型于 `model/Qwen3-0.6B/` 目录。
4. 下载 `ChatLaw-Text2Vec` 嵌入模型于 `embedding_model/all-MiniLM-L6-v2/`。
5. 下载`searxng` 搜索引擎并且配置
6. 在 `config.py` 中填写API密钥以及数据库配置。
7. 启动后端服务：
   ```
   python backend/app.py
   ```
8. 打开 `frontend/index.html` 体验网页端。

---

## 其他说明
- **扩展**：支持自定义知识库文档、API工具、提示词模板等。
- **安全与隐私**：请勿将敏感数据上传至公有环境，API密钥请妥善保管。
- **优化**： 后续可以添加意图识别、长期记忆以及RAG等模块的优化。

---

## License

本项目仅供学习与研究使用，禁止商用