# -*- coding: utf-8 -*-
"""端到端问答 enable_image=true, 找出答案中的 image_key。"""
import json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
TMP = os.environ.get("FEISHU_QA_HOME", r"D:\TRAE\claude_work\feishu_qa")
os.makedirs(TMP, exist_ok=True)
DL = os.path.join(TMP, "downloads")
os.makedirs(DL, exist_ok=True)
ut = json.load(open(os.path.join(TMP, "user_token.json")))["access_token"]

query = sys.argv[1] if len(sys.argv) > 1 else "CU模块架构框图是怎样的，有哪些组成部分"
node = sys.argv[2] if len(sys.argv) > 2 else "CBlZwb1oRi3spekx9I1cjv03nBe"
body = {
    "query": query,
    "knowledge_scope": "enterprise",
    "enterprise_knowledge_source": {
        "wiki": {"searchable": True,
                 "filter": {"node_tokens": [node]}}
    },
    "model_type": "doubao",
    "enable_image": True,
}
req = urllib.request.Request("https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer",
    data=json.dumps(body).encode("utf-8"),
    headers={"Content-Type": "application/json; charset=utf-8",
             "Authorization": "Bearer " + ut})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
except urllib.error.HTTPError as e:
    r = {"_http": e.code, "_body": e.read().decode("utf-8", "replace")}

print("status_code:", r.get("status_code"), "|", r.get("status_message", "")[:200])
ans = r.get("answer", "")
print("answer length:", len(ans))
print("answer head:", ans[:600])
# 找 image_key 形态的 token
import re
keys = re.findall(r"img_v3_[A-Za-z0-9_\-]+", json.dumps(r, ensure_ascii=False))
keys = sorted(set(keys))
print("image_keys found:", keys)
json.dump(r, open(os.path.join(TMP, "last_answer_img.json"), "w"), ensure_ascii=False)

# 下载图片到 <HOME>/downloads/<时间戳>/，扩展名按 Content-Type 定
if keys:
    import time
    sub = os.path.join(DL, time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(sub, exist_ok=True)
    ext_by_ct = {"image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
                 "image/webp": ".webp"}
    for i, key in enumerate(keys, 1):
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/search/v2/knowledge_qa/images/" + key,
            headers={"Authorization": "Bearer " + ut})
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            data = resp.read()
            ext = ext_by_ct.get(resp.headers.get("Content-Type", ""), ".png")
            fn = os.path.join(sub, "img_%d%s" % (i, ext))
            open(fn, "wb").write(data)
            print("[dl]", len(data), "bytes ->", fn)
        except urllib.error.HTTPError as e:
            print("[dl][fail] key", i, "HTTP", e.code,
                  e.read().decode("utf-8", "replace")[:150])
