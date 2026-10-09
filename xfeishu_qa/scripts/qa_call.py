# -*- coding: utf-8 -*-
"""用已保存的 user_token.json 调知识问答 API。用法: qa_call.py [query] [scope] [node_token]"""
import json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TMP = os.environ.get("FEISHU_QA_HOME", r"D:\TRAE\claude_work\feishu_qa")
os.makedirs(TMP, exist_ok=True)
ut = json.load(open(os.path.join(TMP, "user_token.json")))["access_token"]

query = sys.argv[1] if len(sys.argv) > 1 else "你好，请介绍一下你自己"
scope = sys.argv[2] if len(sys.argv) > 2 else "llm"
node = sys.argv[3] if len(sys.argv) > 3 else None

body = {"query": query, "knowledge_scope": scope, "model_type": "doubao", "enable_image": False}
if node:
    body["enterprise_knowledge_source"] = {
        "wiki": {"searchable": True, "filter": {"node_tokens": [node]}}}

req = urllib.request.Request("https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer",
    data=json.dumps(body).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer " + ut})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
except urllib.error.HTTPError as e:
    r = {"_http": e.code, "_body": e.read().decode("utf-8", "replace")}
print("[qa] query:", query, "| scope:", scope, "| node:", node)
print(json.dumps(r, ensure_ascii=False, indent=1)[:6000])
