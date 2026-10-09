# -*- coding: utf-8 -*-
"""OAuth 获取 user_access_token 并调用知识问答端到端 API。
流程: 本机起回调服务 -> 自动开浏览器授权 -> 收 code 换 token -> 调 knowledge_qa/answer。
用法: feishu_oauth_qa.py [query] [scope] [node_token]
"""
import winreg, json, io, sys, os, threading, webbrowser, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

APP_ID, APP_SECRET = None, None
k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
APP_ID, _ = winreg.QueryValueEx(k, "APP_ID")
APP_SECRET, _ = winreg.QueryValueEx(k, "APP_SECRET")

REDIRECT = "http://localhost:8723/callback"
PORT = 8723
TMP = os.environ.get("FEISHU_QA_HOME", r"D:\TRAE\claude_work\feishu_qa")
os.makedirs(TMP, exist_ok=True)
TOKEN_FILE = os.path.join(TMP, "user_token.json")

query = sys.argv[1] if len(sys.argv) > 1 else "你好，请介绍一下你自己"
scope = sys.argv[2] if len(sys.argv) > 2 else "llm"
node = sys.argv[3] if len(sys.argv) > 3 else None


def http_json(url, payload, hdrs={}):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8", **hdrs})
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        return {"_http": e.code, "_body": e.read().decode("utf-8", "replace")}


def exchange_token(code):
    """授权码换 user_access_token (accounts.feishu.cn/oauth/v3/token)"""
    r = http_json("https://accounts.feishu.cn/oauth/v3/token", {
        "grant_type": "authorization_code",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "code": code,
        "redirect_uri": REDIRECT,
    })
    if r.get("code") == 0:
        json.dump(r, open(TOKEN_FILE, "w"), ensure_ascii=False)
        print("[ok] user_access_token 已获取并保存到", TOKEN_FILE)
        print("[ok] 有效期", r.get("expires_in"), "秒  scope:", r.get("scope"))
    else:
        print("[fail] 换 token 失败:", json.dumps(r, ensure_ascii=False))
    return r


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        code = qs.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if code:
            self.wfile.write("<h2>授权成功，已收到 code，可关闭此页面回到终端。</h2>".encode())
            threading.Thread(target=exchange_token, args=(code,)).start()
            threading.Thread(target=lambda: (server.shutdown())).start()
        else:
            self.wfile.write(("授权失败: " + self.path).encode())

    def log_message(self, *a):
        pass


# 1. 起回调服务
server = HTTPServer(("localhost", PORT), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
print("[..] 回调服务已启动:", REDIRECT)

# 2. 打开授权页（不传 scope，默认授权应用已开通的权限）
auth_url = "https://accounts.feishu.cn/open-apis/authen/v1/authorize?" + urlencode({
    "app_id": APP_ID, "redirect_uri": REDIRECT,
    "scope": "search:knowledge_qa:read offline_access"})
print("[..] 正在打开浏览器授权页，请在页面登录并点击授权...")
webbrowser.open(auth_url)

# 3. 等待回调（最多 5 分钟）
server.timeout = 300
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass

ut = None
for _ in range(30):
    if os.path.exists(TOKEN_FILE):
        ut = json.load(open(TOKEN_FILE)).get("access_token")
        break
    import time; time.sleep(1)
if not ut:
    print("[fail] 未拿到 user_access_token，退出")
    sys.exit(1)

# 4. 调知识问答 API 验证
body = {"query": query, "knowledge_scope": scope, "model_type": "doubao", "enable_image": False}
if node:
    body["enterprise_knowledge_source"] = {
        "wiki": {"searchable": True, "filter": {"node_tokens": [node]}}}
r = http_json("https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer", body,
              {"Authorization": "Bearer " + ut})
print("[qa] 请求:", json.dumps(body, ensure_ascii=False))
print("[qa] 响应:")
print(json.dumps(r, ensure_ascii=False, indent=1)[:5000])
