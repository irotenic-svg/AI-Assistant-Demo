"""
Flask API 入口 - 医疗知识问答助手后端
支持流式 (SSE) 与非流式问答
"""
import json
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, Response
from flask_cors import CORS

from assistant.config import load_settings
from assistant.embeddings import BGEM3Embeddings
from assistant.vectorstore import VectorStoreManager
from assistant.chain import RAGChain

# ── 初始化 ──────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])

settings = load_settings()

# 初始化 Embedding
print(f"[Init] Loading embedding model: {settings.embedding_model}...")
embedding = BGEM3Embeddings(
    model_name=settings.embedding_model,
    device=settings.embedding_device,
)

# 初始化 VectorStore
print(f"[Init] Connecting to Chroma at: {settings.chroma_dir}...")
vectorstore_manager = VectorStoreManager(
    persist_dir=settings.chroma_dir,
    embedding=embedding,
    collection_name="medical_knowledge",
)

# 初始化 RAG Chain
print("[Init] Setting up RAG Chain...")
rag_chain = RAGChain(settings)
print(f"[Init] LLM config check: model={rag_chain._llm.model_name}, "
      f"reasoning_effort={rag_chain._llm.reasoning_effort}, "
      f"extra_body={rag_chain._llm.extra_body}")

try:
    # 检查 Chroma 是否有数据
    stats = vectorstore_manager.get_collection_stats()
    if stats["count"] > 0:
        rag_chain.initialize(vectorstore_manager)
        print(f"[Init] RAG Chain ready. Vector store: {stats['count']} documents.")
    else:
        print("[Init] Warning: Vector store is empty. Run 'python scripts/build_vectordb.py' first.")
except Exception as e:
    print(f"[Init] Warning: Could not connect to vector store: {e}")
    print("[Init] Run 'python scripts/build_vectordb.py' to build the index.")


# ── API 路由 ────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health_check():
    """健康检查"""
    try:
        stats = vectorstore_manager.get_collection_stats()
        doc_count = stats["count"]
    except Exception:
        doc_count = 0

    return jsonify({
        "status": "ok",
        "rag_ready": rag_chain.is_ready,
        "vector_store_docs": doc_count,
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    问答接口
    接收 {"question": "...", "session_id": "..."(可选)}
    返回 {"answer": "...", "sources": [...], "session_id": "..."}
    """
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "缺少 question 参数"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    session_id = data.get("session_id", str(uuid.uuid4())[:8])

    # 如果 RAG Chain 未初始化，尝试初始化
    if not rag_chain.is_ready:
        try:
            stats = vectorstore_manager.get_collection_stats()
            if stats["count"] > 0:
                rag_chain.initialize(vectorstore_manager)
            else:
                return jsonify({
                    "answer": "知识库为空，请先运行数据预处理和向量库构建脚本。",
                    "sources": [],
                    "session_id": session_id,
                    "error": True,
                })
        except Exception as e:
            return jsonify({
                "answer": f"系统初始化失败: {str(e)}",
                "sources": [],
                "session_id": session_id,
                "error": True,
            }), 500

    result = rag_chain.ask(question, session_id=session_id)
    return jsonify(result)


@app.route("/api/chat/stream", methods=["POST"])
def chat_stream():
    """
    流式问答接口 (Server-Sent Events)
    接收 {"question": "...", "session_id": "..."(可选)}
    事件流:
      event: sources  → 检索到的来源文档
      event: token    → 逐字回答
      event: done     → 流结束
      event: error    → 错误信息
    """
    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "缺少 question 参数"}), 400

    question = data["question"].strip()
    if not question:
        return jsonify({"error": "问题不能为空"}), 400

    session_id = data.get("session_id", str(uuid.uuid4())[:8])

    # 如果 RAG Chain 未初始化，尝试初始化
    if not rag_chain.is_ready:
        try:
            stats = vectorstore_manager.get_collection_stats()
            if stats["count"] > 0:
                rag_chain.initialize(vectorstore_manager)
            else:
                def err_gen():
                    yield f"data: {json.dumps({'type': 'error', 'data': '知识库为空，请先运行数据预处理和向量库构建脚本。'}, ensure_ascii=False)}\n\n"
                return Response(
                    err_gen(),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
                )
        except Exception as e:
            err_msg = str(e)  # 捕获到局部变量，避免闭包中 e 被释放
            def err_gen():
                yield f"data: {json.dumps({'type': 'error', 'data': f'系统初始化失败: {err_msg}'}, ensure_ascii=False)}\n\n"
            return Response(
                err_gen(),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

    def generate():
        """SSE 事件生成器"""
        for event in rag_chain.ask_stream(question, session_id=session_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",
            "Pragma": "no-cache",
        },
    )


@app.route("/api/history", methods=["GET"])
def get_history():
    """获取会话历史"""
    session_id = request.args.get("session_id", "default")
    history = rag_chain.get_history(session_id)
    return jsonify({"session_id": session_id, "messages": history})


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    """清空会话历史"""
    data = request.get_json() or {}
    session_id = data.get("session_id", "default")
    rag_chain.clear_history(session_id)
    return jsonify({"status": "ok", "session_id": session_id})


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """列出所有活跃会话"""
    sessions = list(rag_chain._store.keys())
    return jsonify({"sessions": sessions})


# ── 错误处理 ────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "接口不存在"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "服务器内部错误"}), 500


# ── 启动入口 ────────────────────────────────────────

if __name__ == "__main__":
    from waitress import serve
    print(f"\n{'='*50}")
    print(f"  医疗知识问答助手 - Backend API")
    print(f"  http://{settings.flask_host}:{settings.flask_port}")
    print(f"  WSGI Server: waitress (streaming-enabled)")
    print(f"{'='*50}\n")
    serve(
        app,
        host=settings.flask_host,
        port=settings.flask_port,
        threads=4,                # 4 worker 线程，支持并发请求
        channel_timeout=120,      # SSE 长连接 120s 超时
        send_bytes=1,             # send 最小字节数 = 1，不等待积累，立即发送
    )
