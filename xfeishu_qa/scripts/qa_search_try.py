# -*- coding: utf-8 -*-
"""向量搜索 API: 重试 open.feishu.cn search 路径, 打印 HTTP 状态。"""
import json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
TMP = os.environ.get("FEISHU_QA_HOME", r"D:\TRAE\claude_work\feishu_qa")
os.makedirs(TMP, exist_ok=True)
ut = json.load(open(os.path.join(TMP, "user_token.json")))["access_token"]

url = "https://open.feishu.cn/open-apis/search/v2/knowledge_qa/search"
query = sys.argv[1] if len(sys.argv) > 1 else "SOC架构里有哪些CU"
node = sys.argv[2] if len(sys.argv) > 2 else "CBlZwb1oRi3spekx9I1cjv03nBe"
body = {
    "query": query,
    "enterprise_knowledge_source": {
        "wiki": {"searchable": True, "filter": {"node_tokens": [node]}}
    },
}
req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8",
             "Authorization": "Bearer " + ut})
try:
    resp = urllib.request.urlopen(req, timeout=120)
    raw = resp.read().decode("utf-8", "replace")
    print("HTTP", resp.status)
    print("headers:", dict(resp.headers).get("Content-Type"))
    print(raw[:4000] if raw.strip() else "(empty body)")
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print(e.read().decode("utf-8", "replace")[:1500])
