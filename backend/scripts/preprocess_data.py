"""
数据预处理脚本
处理三个医疗问答数据集：cMedQA2, webMedQA, PubMedQA
输出统一的 JSONL 格式到 backend/data/processed/
"""
import csv
import json
import os
import re
import sys
import zipfile
from io import TextIOWrapper
from pathlib import Path
from typing import List, Dict, Any

# 确保 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── 配置 ────────────────────────────────────────────
RAW_DATA_DIR = Path(os.getenv("RAW_DATA_DIR", "E:/ProgramData/DataSet"))
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 工具函数 ────────────────────────────────────────

def clean_text(text: str) -> str:
    """清洗文本：去除 HTML 标签、多余空白、特殊字符"""
    if not text:
        return ""
    # 去除 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 替换 HTML 实体
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    # 去除多余空白
    text = re.sub(r"\s+", " ", text)
    # 去除不可见字符
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def is_valid_record(content: str, min_length: int = 10) -> bool:
    """检查记录是否有效"""
    if not content or len(content) < min_length:
        return False
    # 过滤纯数字/符号记录
    if re.match(r"^[\d\s\.,;:!?()（）\-—+=*/\#@\$%^&\|\[\]{}]+$", content):
        return False
    return True


def write_jsonl(records: List[Dict[str, Any]], filename: str) -> None:
    """写入 JSONL 文件"""
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"  [OK] Saved {len(records)} records to {path}")


# ── 数据集处理 ──────────────────────────────────────

def preprocess_cmedqa2() -> List[Dict[str, Any]]:
    """
    处理 cMedQA2 数据集
    从 zip 中提取 answer.csv 和 question.csv，关联后输出
    """
    print("\n" + "=" * 60)
    print("处理 cMedQA2 数据集 (中文医疗社区问答)")
    print("=" * 60)

    data_dir = RAW_DATA_DIR / "cMedQA2-master"
    records = []

    try:
        # 读取答案数据
        print("  解压 answer.csv...")
        answers = {}
        with zipfile.ZipFile(data_dir / "answer.zip", "r") as zf:
            with zf.open("answer.csv") as f:
                reader = csv.DictReader(
                    TextIOWrapper(f, encoding="utf-8", errors="replace")
                )
                for row in reader:
                    ans_id = row.get("ans_id", "")
                    content = clean_text(row.get("content", ""))
                    q_id = row.get("question_id", "")
                    if ans_id and content:
                        answers[ans_id] = {
                            "content": content,
                            "question_id": q_id,
                        }
        print(f"  已读取 {len(answers)} 条答案")

        # 读取问题数据
        print("  解压 question.csv...")
        questions = {}
        with zipfile.ZipFile(data_dir / "question.zip", "r") as zf:
            with zf.open("question.csv") as f:
                reader = csv.DictReader(
                    TextIOWrapper(f, encoding="utf-8", errors="replace")
                )
                for row in reader:
                    q_id = row.get("question_id", "")
                    content = clean_text(row.get("content", ""))
                    if q_id and content:
                        questions[q_id] = content
        print(f"  已读取 {len(questions)} 条问题")

        # 读取候选数据 (train + dev + test) — 获取正面答案
        print("  解压候选文件...")
        positive_pairs = set()  # (question_id, answer_id) for positive answers
        for candidate_zip in ["train_candidates.zip", "dev_candidates.zip", "test_candidates.zip"]:
            zip_path = data_dir / candidate_zip
            if not zip_path.exists():
                continue
            with zipfile.ZipFile(zip_path, "r") as zf:
                name = zf.namelist()[0]
                with zf.open(name) as f:
                    reader = csv.DictReader(
                        TextIOWrapper(f, encoding="utf-8", errors="replace")
                    )
                    for row in reader:
                        q_id = row.get("question_id", "").strip()
                        pos_ans_id = row.get("pos_ans_id", "").strip()
                        if q_id and pos_ans_id:
                            positive_pairs.add((q_id, pos_ans_id))
        print(f"  已读取 {len(positive_pairs)} 个正面问答对")

        # 关联问题与答案，生成记录
        print("  关联问答对...")
        for q_id, ans_id in positive_pairs:
            if q_id in questions and ans_id in answers:
                question = questions[q_id]
                answer = answers[ans_id]["content"]
                content = f"问题：{question}\n回答：{answer}"
                if is_valid_record(content):
                    records.append({
                        "id": f"cmedqa2_{q_id}_{ans_id}",
                        "content": content,
                        "metadata": {
                            "source": "cMedQA2",
                            "type": "medical_qa",
                            "question": question,
                            "answer": answer,
                            "question_id": q_id,
                            "dataset": "cMedQA2",
                        },
                    })

        print(f"  生成 {len(records)} 条有效记录")

    except Exception as e:
        print(f"  [ERROR] cMedQA2: {e}")

    return records


def preprocess_webmedqa() -> List[Dict[str, Any]]:
    """
    处理 webMedQA 数据集
    从 zip 中提取 TSV 文件，仅保留正面答案
    train.zip 已损坏，使用 test.zip + valid.zip
    """
    print("\n" + "=" * 60)
    print("处理 webMedQA 数据集 (在线医疗咨询问答)")
    print("=" * 60)

    data_dir = RAW_DATA_DIR / "webMedQA-master"
    records = []

    # 按问题分组，收集所有答案后只保留正面(标签=1)的
    question_groups: Dict[str, Dict[str, Any]] = {}

    try:
        for zip_name in ["test.zip", "valid.zip"]:
            zip_path = data_dir / zip_name
            if not zip_path.exists():
                print(f"  跳过不存在的文件: {zip_name}")
                continue

            print(f"  解压 {zip_name}...")
            with zipfile.ZipFile(zip_path, "r") as zf:
                # 文件名: medQA.test.txt 或 medQA.valid.txt
                name = zf.namelist()[0]
                with zf.open(name) as f:
                    line_count = 0
                    for line in TextIOWrapper(f, encoding="utf-8", errors="replace"):
                        line_count += 1
                        line = line.strip()
                        if not line:
                            continue

                        parts = line.split("\t")
                        if len(parts) < 5:
                            continue

                        category = parts[0].strip()
                        label = parts[1].strip()
                        q_id = parts[2].strip()
                        question = clean_text(parts[3])
                        answer = clean_text(parts[4])

                        if not is_valid_record(question, min_length=5) or not is_valid_record(answer, min_length=5):
                            continue

                        if q_id not in question_groups:
                            question_groups[q_id] = {
                                "question": question,
                                "category": category,
                                "positive_answers": [],
                            }

                        # 只保留正面答案 (label=1)
                        if label == "1":
                            question_groups[q_id]["positive_answers"].append(answer)

            print(f"  已读取 {line_count} 行")

        # 生成记录
        print("  生成记录...")
        for q_id, group in question_groups.items():
            question = group["question"]
            category = group["category"]
            for i, answer in enumerate(group["positive_answers"]):
                content = f"问题：{question}\n回答：{answer}"
                records.append({
                    "id": f"webmedqa_{q_id}_{i}",
                    "content": content,
                    "metadata": {
                        "source": "webMedQA",
                        "type": "medical_qa",
                        "category": category,
                        "question": question,
                        "answer": answer,
                        "question_id": q_id,
                        "dataset": "webMedQA",
                    },
                })

        print(f"  生成 {len(records)} 条有效记录")

    except Exception as e:
        print(f"  [ERROR] webMedQA: {e}")

    return records


def preprocess_pubmedqa() -> List[Dict[str, Any]]:
    """
    处理 PubMedQA 数据集
    从 JSON 中提取 QUESTION + CONTEXTS + LONG_ANSWER
    """
    print("\n" + "=" * 60)
    print("处理 PubMedQA 数据集 (生物医学文献问答)")
    print("=" * 60)

    data_dir = RAW_DATA_DIR / "pubmedqa-master"
    json_path = data_dir / "data" / "ori_pqal.json"
    records = []

    if not json_path.exists():
        print(f"  [ERROR] File not found: {json_path}")
        return records

    try:
        print(f"  加载 {json_path}...")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  已读取 {len(data)} 条文献记录")

        for pmid, item in data.items():
            question = clean_text(item.get("QUESTION", ""))
            contexts = item.get("CONTEXTS", [])
            long_answer = clean_text(item.get("LONG_ANSWER", ""))
            labels = item.get("LABELS", [])
            meshes = item.get("MESHES", [])
            final_decision = item.get("final_decision", "")
            year = item.get("YEAR", "")

            if not is_valid_record(question):
                continue

            # 将上下文合并
            context_text = " ".join([clean_text(c) for c in contexts])

            # 构建内容：问题 + 上下文 + 答案
            content_parts = [f"Question: {question}"]
            if context_text:
                content_parts.append(f"Context: {context_text}")
            if long_answer:
                content_parts.append(f"Answer: {long_answer}")

            content = "\n".join(content_parts)

            if is_valid_record(content):
                records.append({
                    "id": f"pubmedqa_{pmid}",
                    "content": content,
                    "metadata": {
                        "source": "PubMedQA",
                        "type": "biomedical_qa",
                        "pmid": pmid,
                        "question": question,
                        "context": context_text,
                        "long_answer": long_answer,
                        "labels": labels,
                        "meshes": meshes,
                        "final_decision": final_decision,
                        "year": year,
                        "dataset": "PubMedQA",
                    },
                })

        print(f"  生成 {len(records)} 条有效记录")

    except Exception as e:
        print(f"  [ERROR] PubMedQA: {e}")

    return records


# ── 主流程 ──────────────────────────────────────────

def main():
    """主预处理流程"""
    print("=" * 60)
    print("  医疗知识数据集预处理")
    print("=" * 60)

    ensure_output_dir()

    all_records = []

    # 处理三个数据集
    all_records.extend(preprocess_cmedqa2())
    all_records.extend(preprocess_webmedqa())
    all_records.extend(preprocess_pubmedqa())

    # 保存合并结果
    print("\n" + "=" * 60)
    print("保存预处理结果")
    print("=" * 60)
    write_jsonl(all_records, "all_documents.jsonl")

    # 统计
    source_counts = {}
    for r in all_records:
        src = r["metadata"]["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    print(f"\n预处理完成！总计 {len(all_records)} 条记录")
    for src, count in source_counts.items():
        print(f"  - {src}: {count} 条")


if __name__ == "__main__":
    main()
