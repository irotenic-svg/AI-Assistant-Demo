# 医疗知识问答助手 (Medical RAG Assistant)

基于 **LangChain + RAG（检索增强生成）** 技术构建的医疗知识问答 Demo，支持中英文双语医学问题检索与回答。

> 本项目的学习目标：熟悉 LangChain 核心模块（LLM、VectorStore、Retriever、Chain、Memory），掌握 RAG 技术在不同数据类型下的应用。

## 技术架构

```
┌──────────────────────────────────────┐
│       Vue 3 + Element Plus           │
│       (Vite :5173)                   │
│       聊天界面 + 历史记录 + 来源引用    │
└──────────────┬───────────────────────┘
               │ HTTP (Axios)
┌──────────────▼───────────────────────┐
│       Flask REST API (:5000)          │
│       POST /api/chat                 │
│       GET  /api/history              │
└──────────────┬───────────────────────┘
               │
┌──────────────▼───────────────────────┐
│       LangChain RAG Chain             │
│  ┌─────────────────────────────────┐ │
│  │ ConversationBufferWindowMemory  │ │
│  ├─────────────────────────────────┤ │
│  │ create_retrieval_chain          │ │
│  │  ├── Retriever: Chroma (top-5)  │ │
│  │  ├── PromptTemplate             │ │
│  │  └── LLM: DeepSeek V4 Pro       │ │
│  ├─────────────────────────────────┤ │
│  │ Embedding: BGE-M3 (1024维)      │ │
│  │ VectorStore: Chroma (持久化)    │ │
│  └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| **LLM** | DeepSeek V4 Pro | 通过 OpenAI 兼容接口调用 |
| **Embedding** | BAAI/bge-m3 | 本地 GPU 推理，中英双语，1024 维 |
| **VectorStore** | Chroma | LangChain 集成，HNSW 索引 |
| **RAG Framework** | LangChain | create_retrieval_chain + Memory |
| **后端** | Flask + flask-cors | REST API |
| **前端** | Vue 3 + Element Plus | Vite 构建，SPA 架构 |
| **环境** | conda (Python 3.12) + nvm (Node.js 22) | |

## 数据集

| 数据集 | 语言 | 规模 | 来源 |
|--------|------|------|------|
| **cMedQA2** | 中文 | 108K 问 / 188K 答 | 中文社区医疗问答 |
| **webMedQA** | 中文 | 63K 问 / 12K 答 | 在线医疗咨询网站 |
| **PubMedQA** | 英文 | 1,000 条 | PubMed 生物医学文献 |

预处理后共 **202,138** 条记录，切分为 **213,540** 个文档块存入 Chroma。

## 项目结构

```
├── .env                        # API Key 和环境变量
├── .env.example                # 环境变量模板
├── requirements.txt            # Python 依赖
├── README.md                   # 本文件
├── backend/                    # 后端
│   ├── app.py                  # Flask 入口 + API 路由
│   ├── assistant/              # 核心模块
│   │   ├── config.py           # 配置管理 (Settings)
│   │   ├── llm.py              # LLM 封装 (ChatOpenAI → DeepSeek)
│   │   ├── embeddings.py       # BGE-M3 嵌入模型
│   │   ├── vectorstore.py      # Chroma 向量存储操作
│   │   ├── chain.py            # LangChain RAG Chain 组装
│   │   └── prompts.py          # Prompt 模板
│   ├── scripts/
│   │   ├── preprocess_data.py  # 数据预处理
│   │   ├── build_vectordb.py   # 构建向量库
│   │   └── resume_vectordb.py  # 断点续建
│   └── data/
│       ├── processed/          # 预处理后的 JSONL
│       └── chroma/             # Chroma 持久化索引
├── frontend/                   # 前端
│   ├── src/
│   │   ├── views/ChatView.vue  # 主聊天页面
│   │   ├── components/         # 组件
│   │   │   ├── ChatMessage.vue # 消息气泡
│   │   │   ├── ChatInput.vue   # 输入框
│   │   │   └── SourcePanel.vue # 检索来源面板
│   │   ├── api/chat.js         # Axios 封装
│   │   └── router/index.js     # Vue Router
│   └── vite.config.js          # Vite 配置 (含 API 代理)
└── prompts/
    └── rag_system.txt          # System Prompt
```

## 快速开始

### 前置要求

- Python 3.12+ (conda)
- Node.js 22+ (nvm)
- CUDA GPU (可选，CPU 也可运行)
- DeepSeek API Key

### 1. 环境配置

```powershell
# 创建 conda 环境
conda create -n medrag python=3.12 -y
conda activate medrag

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 CUDA 版 PyTorch (可选，加速嵌入)
pip install torch --index-url https://download.pytorch.org/whl/cu126

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 DEEPSEEK_API_KEY

# 安装前端依赖
cd frontend
npm install
```

### 2. 数据预处理

```powershell
cd backend
python scripts/preprocess_data.py
```

输出：`backend/data/processed/all_documents.jsonl`（约 200K 条）

### 3. 构建向量数据库

```powershell
# 设置离线模式（如果 HuggingFace 连接不稳定）
$env:HF_HUB_OFFLINE = '1'

# 构建向量库（首次运行需下载 BGE-M3 模型，约 2GB）
python scripts/build_vectordb.py
```

构建完成后 `backend/data/chroma/` 约为 1.5 GB，包含 213,540 个文档嵌入。

### 4. 启动服务

```powershell
# 终端 1：启动后端
$env:HF_HUB_OFFLINE = '1'
python backend/app.py
# → http://localhost:5000

# 终端 2：启动前端
cd frontend
npm run dev
# → http://localhost:5173
```

## API 文档

### GET /api/health

健康检查，返回向量库状态。

```json
{
  "status": "ok",
  "rag_ready": true,
  "vector_store_docs": 213540
}
```

### POST /api/chat

发送问题并获取回答。

**请求:**
```json
{
  "question": "Do mitochondria play a role in programmed cell death?",
  "session_id": "default"
}
```

**响应:**
```json
{
  "answer": "是的，根据所提供的上下文信息...",
  "sources": [
    {
      "content": "...",
      "source": "PubMedQA",
      "question": "..."
    }
  ],
  "session_id": "default"
}
```

### GET /api/history?session_id=default

获取对话历史。

### DELETE /api/history

清空对话历史。

## 关键技术点

### 1. LangChain 核心模块

| 模块 | 本项目实现 |
|------|-----------|
| **LLM** | `ChatOpenAI` → DeepSeek API（base_url 重定向） |
| **VectorStore** | `langchain_chroma.Chroma` + HNSW + Cosine 相似度 |
| **Retriever** | `similarity_search` (top-5) |
| **Chain** | `create_retrieval_chain` + `create_stuff_documents_chain` |
| **Memory** | `ConversationBufferWindowMemory` (K=10) |

### 2. RAG 流程

```
用户提问 → Embedding 向量化 → Chroma 相似度检索 (top-5)
    → 检索文档作为 Context → System Prompt + Context + Question
    → DeepSeek LLM 生成回答 → 返回 Answer + Sources
```

### 3. 数据处理

- cMedQA2 / webMedQA：GBK → UTF-8 转码，question_id 关联问答
- PubMedQA：JSON 解析，提取 QUESTION + CONTEXTS + LONG_ANSWER
- 数据清洗：去 HTML 标签、特殊字符、空白行
- 文档切分：`RecursiveCharacterTextSplitter`（chunk_size=500, overlap=50）

## 许可证

本项目仅用于学习研究目的。数据集版权归原作者所有：
- cMedQA2: [IEEE Access](https://ieeexplore.ieee.org/abstract/document/8548603)
- webMedQA: [BMC Medical Informatics](https://bmcmedinformdecismak.biomedcentral.com/articles/10.1186/s12911-019-0761-8)
- PubMedQA: [EMNLP-IJCNLP 2019](https://aclanthology.org/D19-1259/)
