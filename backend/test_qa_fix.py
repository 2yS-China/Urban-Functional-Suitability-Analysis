"""测试修复后的问答问题类型识别"""
import requests, json

BASE = "http://localhost:8000/api/projects/osm_test_20260920_122458/qa"

tests = [
    ("多少个适宜的位置", "overview", "无功能类型的泛查询→overview"),
    ("哪些区域适合商业", "query", "含功能类型→query"),
    ("整体分析结果如何", "overview", "显式概览词→overview"),
    ("绿地休闲适合在哪些地方", "query", "含功能类型→query"),
    ("统计一下结果", "overview", "显式统计词→overview"),
]

for question, expected, desc in tests:
    r = requests.post(BASE, json={"question": question})
    data = r.json().get("data", {})
    qt = data.get("question_type", "ERROR")
    status = "OK" if qt == expected else f"FAIL (got {qt})"
    print(f"[{status}] '{question}' → {qt} | {desc}")
    if qt == "overview":
        mu = data.get("metadata", {})
        print(f"        metadata: total={mu.get('total_units')}, with_func={mu.get('units_with_function')}, related={len(data.get('related_units', []))}")
    elif qt == "query":
        print(f"        metadata: {data.get('metadata')}")
    print()