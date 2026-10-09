# 飞书API使用说明

> 面向 0 基础读者的飞书开放平台 API 从零打通教程。
> 按章节顺序操作即可跑通；每章末尾附报错对照表，卡住时先查表。
>
> - 第 0 章：通用准备（所有 API 共用，只做一次）
> - 第 1 章：知识问答三件套——端到端问答 / 向量搜索 / 答案图片下载（已打通）

---

## 第 0 章 通用准备

本章配置一次，之后所有 API 章节共用。

### 0.1 先搞懂五个词（一页纸版）

| 概念 | 通俗解释 | 类比 |
|---|---|---|
| **应用（app）** | 你在飞书开放平台注册的"程序身份"，有一对凭证 | 一张工牌 |
| **APP_ID / APP_SECRET** | 应用的账号密码，证明"请求来自这个应用" | 工牌编号 + 门禁密码 |
| **tenant_access_token** | 以**应用**身份调 API 的临时通行证（约 2 小时有效） | 工牌本身的门禁功能 |
| **user_access_token** | 以**某个用户**身份调 API 的临时通行证（约 2 小时有效），需用户本人在浏览器点授权 | 你本人刷脸临时授权别人替你去办事 |
| **scope（授权范围）** | token 实际允许做的事的清单。**实际权限 = 应用已开通权限 ∩ 用户授权的 scope** | 门禁卡开了哪些门 |

**关键判断：用哪种 token？** 看 API 文档「请求头 → Authorization」一栏：
- 标 `tenant_access_token`（绿色标签）→ 简单模式，脚本自动获取，零交互；
- 标 `user_access_token` → 必须走本章 1.3 的浏览器授权流程。

> 踩坑记录：知识问答三个 API 的文档都标注 user_access_token。拿 tenant token 去调会报 `99991663 Invalid access token`——不是 token 坏了，是类型不对。

### 0.2 找到应用凭证并存入注册表

1. 浏览器打开 https://open.feishu.cn/app ，登录后点进你的应用；
2. 左侧「凭证与基础信息」→ 复制 **App ID** 和 **App Secret**；
3. 存入本机注册表（之后的脚本都从这里读，避免写死在代码里）：

```powershell
# PowerShell 执行（把引号里换成你的值）
[Environment]::SetEnvironmentVariable("APP_ID",  "cli_xxxxxx", "User")
[Environment]::SetEnvironmentVariable("APP_SECRET", "xxxxxxxx", "User")
```

验证：重开一个终端执行 `echo %APP_ID%`（cmd）能打印出来即成功。

### 0.3 Python 环境

- 本机已装 Python 3.14：`C:/Users/<用户名>/AppData/Local/Programs/Python/Python314/python.exe`
- **无需安装任何第三方库**——示例脚本只用 Python 标准库（urllib / json / winreg / http.server）。

### 0.4 实用技巧：抓飞书文档的正文

`open.feishu.cn/document/...` 页面是 JS 动态渲染的，直接抓取只有空壳。两个办法：
1. 在原 URL 末尾加 `.md` 后缀（如 `.../answer.md`），能拿到 markdown 源；
2. 不行就截图文档页的「请求」（基本信息 + 请求头 + 请求体）和「请求示例」部分。

### 0.5 本机环境注意

- 公司终端装了 EsafeNet 透明加密：**脚本里别用重定向 `>` 写文件**（会写成密文），中间文件走 Python 脚本本身或 Write 工具；
- 脚本打印中文时加 GBK→UTF-8 包装，否则控制台乱码。

---

## 第 1 章 知识问答 API（端到端问答 / 向量搜索 / 答案图片下载）

### 1.1 这三个 API 是什么

都属于飞书「知识问答」能力，各管一段：

| API | 方法与路径 | 作用 | 输入 → 输出 |
|---|---|---|---|
| **端到端问答** | `POST /open-apis/search/v2/knowledge_qa/answer` | 检索企业知识 + 大模型生成**带引用的答案** | 问题 → 答案文本 + 引用文档列表 |
| **向量搜索** | `POST /open-apis/search/v2/knowledge_qa/search` | 只检索不生成，返回**相关片段 + 相似度分数** | 问题 → `passages[]`（title/content/url/score） |
| **答案图片下载** | `GET /open-apis/search/v2/knowledge_qa/images/<image_key>` | 下载端到端答案里的图片 | image_key → 图片二进制流 |

三者权限相同（「执行飞书知识问答能力」），认证相同（user_access_token），额度消耗集中在端到端问答（要跑大模型）。

### 1.2 后台配置（一次性，三件事）

开发者后台（https://open.feishu.cn/app）进入你的应用：

1. **开通权限**：「权限管理」→ 搜「知识问答」→ 开通对应能力权限；再开通 `offline_access`（为了拿 refresh_token，续期免重新授权）。
   > 技巧：API 文档页「请求 → 权限要求」里的蓝色链接可以直接跳到对应权限条目。后台权限是中文名，直接搜 `search:knowledge_qa:read` 这种英文标识搜不到。
2. **配置重定向 URL**：「开发配置 → 安全设置 → 重定向 URL」→ 添加 `http://localhost:8723/callback`。保存即生效，无需发版。
   > 必须一字不差（端口、路径都算），不一致授权时报 20071。localhost 指发起授权的那台机器本身，人人可用此入口，真正的门槛在 APP_SECRET 和应用可用范围。
3. **可用范围**：「开发配置 → 可用范围」确认使用者在范围内，否则授权报 20010。

### 1.3 授权拿 user_access_token（首次或 refresh 失效时）

运行脚本 `feishu_oauth_qa.py`（完整代码见附录 A），它会：

1. 本机 8723 端口起临时服务等回调；
2. 自动打开浏览器授权页（关键：URL 里**必须带 scope**）：

```
https://accounts.feishu.cn/open-apis/authen/v1/authorize
    ?app_id=<你的APP_ID>
    &redirect_uri=http%3A%2F%2Flocalhost%3A8723%2Fcallback
    &scope=search%3Aknowledge_qa%3Aread%20offline_access
```

3. 你在页面登录飞书、点「授权」；
4. 飞书把授权码 code 回调到 localhost:8723（5 分钟有效、只能用一次）；
5. 脚本拿 code + APP_ID + APP_SECRET 到 `POST https://accounts.feishu.cn/oauth/v3/token` 换出 token，存入脚本目录 `user_token.json`。

**验证授权是否成功**：看脚本打印的 `scope` 字段，必须包含：

```
auth:user.id:read offline_access search:knowledge_qa:read
```

> **最大的坑**：授权 URL 不传 scope 也能授权成功、也能拿到 token，但调 API 时报 99991679 缺权限——白授权一次。scope 是"用户实际授予的清单"，不写就没有。

### 1.4 调用端到端问答

日常调用脚本 `qa_call.py`（附录 B），核心请求：

```jsonc
POST https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer
Authorization: Bearer <user_access_token>
Content-Type: application/json; charset=utf-8

{
  "query": "SOC架构文档里有哪些CU",          // 必填，1~1000 字符
  "knowledge_scope": "enterprise",          // 必填: enterprise/internet/llm/hybrid
  "enterprise_knowledge_source": {           // scope=enterprise/hybrid 时必填
    "wiki": {
      "searchable": true,
      "filter": { "node_tokens": ["CBlZwb1oRi3spekx9I1cjv03nBe"] }  // 可选，限定wiki节点
    }
  },
  "model_type": "doubao",                   // 必填: doubao/deepseek/doubao_thinking/doubao_auto_thinking
  "enable_image": false                      // 可选，true 则答案带图片(image_key)
}
```

**返回结构**（成功时 `status_code: 0`）：

```jsonc
{
  "answer": "...答案文本，内嵌 [[1]](引用链接)...",
  "reasoning_content": "",                   // 思考模型的思考过程
  "references": { "enterprise_refs": [       // 引用文档列表
      { "title": "...", "url": "...", "content": "...原文片段..." } ] },
  "status_code": 0, "status_message": ""
}
```

经验值：
- `filter` 不传 = 在该类型全部授权范围内检索（仍受应用权限边界约束）；
- 答案里的数值用于正式结论前，按 `references` 里的 URL 回原文核验——生成式答案有措辞差异和幻觉风险，引用链接可直接用文档读取 API 取原文。

### 1.5 调用向量搜索

请求体与端到端几乎一致（`query` 和 `enterprise_knowledge_source` 均**非必填**）：

```jsonc
POST https://open.feishu.cn/open-apis/search/v2/knowledge_qa/search
Authorization: Bearer <user_access_token>

{
  "query": "SOC架构里有哪些CU",
  "enterprise_knowledge_source": {
    "wiki": { "searchable": true, "filter": { "node_tokens": ["..."] } }
  }
}
```

**返回**：`data.passages[]`，每条含 `id / title / content（片段内容）/ source_type（1=space/wiki/message/helpdesk/lingo）/ url / score（相似度）`。

> **状态（2026-10-09）**：✅ 已验证可用。9/28 曾因灰度未开返回 200 空 `{}`，同日灰度放行后实测命中
> （原文片段含 "D2D bandwidth: 128 GB/s, UCIE-S x 4"）。passages 为文档**原文切片**，可信度高于
> 生成式答案，数值类问题优先走这里；若再现 200 空返回，按灰度回退或范围内无匹配理解。

### 1.6 答案图片下载

**依赖关系**：先用端到端问答拿 image_key → 再下载。两步：

```jsonc
// 第一步：问答时开图片
{ "query": "CU模块架构框图", "enable_image": true, ... 其余同 1.4 }
// 答案/响应里找 img_v3_ 开头的 image_key（脚本 qa_img_test.py 自动提取）

// 第二步：下载
GET https://open.feishu.cn/open-apis/search/v2/knowledge_qa/images/<image_key>
Authorization: Bearer <user_access_token>
// HTTP 200 → 响应体即图片二进制流，直接写成 .png/.jpg 文件
```

> **判别技巧**（我们实测的结论）：
> - 路径对不对，看 404 还是 400：`404 page not found` = 路径不存在；`400 + 业务码` = 路径对、参数有误；
> - **闭环已验证（2026-09-28）**：enable_image 问答返回 3 个真实 image_key → 逐一 GET 均 HTTP 200
>   （341KB jpeg / 68KB png / 254KB png），内容核验为 D2D Subsys 架构框图；假 key 返回 `400 code 14001`；
> - 注意 Content-Type 是实际图片类型（jpeg/png），保存扩展名按它定；
> - 文档页 curl 示例里的 `fsopen.bytedance.net` 域名是旧写法，以「基本」表格里的 `open.feishu.cn` 路径为准。

### 1.7 token 过期与续期

user_access_token 约 7200 秒（2 小时）过期，过期报 `99991677`。两种续期方式：

| 方式 | 操作 | 适用 |
|---|---|---|
| **refresh_token 刷新**（推荐） | 跑 `qa_refresh.py`（附录 C），无感换新 | 授权时带了 `offline_access` |
| 重新授权 | 重跑 1.3 的授权脚本 | refresh_token 也失效（7 天）或没开 offline_access |

> refresh_token 只能用一次，刷新成功后脚本会自动把新 token 连同新 refresh_token 覆盖写入 `user_token.json`。

### 1.8 脚本清单与日常用法

三个脚本都在调试目录（建议挪到一个正式位置统一保存）：

| 脚本 | 用途 | 典型命令 |
|---|---|---|
| `feishu_oauth_qa.py` | 浏览器授权全流程（首次/兜底） | `python feishu_oauth_qa.py` |
| `qa_refresh.py` | 刷新过期 token | `python qa_refresh.py` |
| `qa_call.py` | 端到端问答调用 | `python qa_call.py "问题" enterprise <wiki节点token>` |
| `qa_search_try.py` | 向量搜索调用 | `python qa_search_try.py` |
| `qa_img_test.py` | 带图问答 + 提取 image_key | `python qa_img_test.py` |

日常最短路径：token 没过期 → 直接 `qa_call.py`；报 99991677 → 先 `qa_refresh.py` 再调；刷新也失败 → `feishu_oauth_qa.py` 重新授权。

### 1.9 报错对照表（本章实测遇到过的全部错误）

| 错误码 | 含义 | 处理 |
|---|---|---|
| 99991663 | token 类型不对 | 这组 API 只认 user token，别用 tenant token |
| 99991679 | 用户授权缺 scope，错误体**直接点名缺哪个** | 授权 URL 的 scope 里加上它，重新授权；同时确认后台已开对应权限 |
| 99991677 | token 过期 | `qa_refresh.py` 刷新或重新授权 |
| 20071 | redirect_uri 与授权时不一致 | 后台登记的回调地址与代码一字不差 |
| 20010 | 用户不在应用可用范围 | 后台把用户加进可用范围 |
| 20003/20004/20065 | code 无效/过期/已用 | code 5 分钟有效且只能用一次，重新发起授权 |
| 20037 (invalid_grant) | refresh_token 已过期（7 天超期） | 重跑 feishu_oauth_qa.py 重新授权（实测 10/8 发生过） |
| 100013 | enterprise 范围缺 enterprise_knowledge_source | 补知识源参数 |
| 100016 | AI 额度用完 | 管理员在飞书管理后台购买 AI 增值权益；间歇性可用说明按量/按天配额 |
| 14001（图片下载） | image_key 无效 | 换答案返回的真实 image_key |
| 404 page not found | 路径不存在 | 核对 URL（注意有无 /v2/） |

---

## 附录 A feishu_oauth_qa.py（授权全流程）

```python
# -*- coding: utf-8 -*-
"""OAuth 获取 user_access_token 并调用知识问答 API。
流程: 本机起回调服务 -> 自动开浏览器授权 -> 收 code 换 token -> 调 API。
用法: feishu_oauth_qa.py [query] [scope] [node_token]
"""
import winreg, json, io, sys, os, threading, webbrowser, urllib.request, urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
APP_ID, _ = winreg.QueryValueEx(k, "APP_ID")
APP_SECRET, _ = winreg.QueryValueEx(k, "APP_SECRET")

REDIRECT = "http://localhost:8723/callback"
PORT = 8723
TMP = os.path.dirname(os.path.abspath(__file__))
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
    r = http_json("https://accounts.feishu.cn/oauth/v3/token", {
        "grant_type": "authorization_code", "client_id": APP_ID,
        "client_secret": APP_SECRET, "code": code, "redirect_uri": REDIRECT})
    if r.get("code") == 0:
        json.dump(r, open(TOKEN_FILE, "w"), ensure_ascii=False)
        print("[ok] token 已保存  有效期", r.get("expires_in"), "秒  scope:", r.get("scope"))
    else:
        print("[fail] 换 token 失败:", json.dumps(r, ensure_ascii=False))

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = parse_qs(urlparse(self.path).query).get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if code:
            self.wfile.write("<h2>授权成功，可关闭此页面。</h2>".encode())
            threading.Thread(target=exchange_token, args=(code,)).start()
            threading.Thread(target=server.shutdown).start()
        else:
            self.wfile.write(("授权失败: " + self.path).encode())
    def log_message(self, *a): pass

server = HTTPServer(("localhost", PORT), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
print("[..] 回调服务已启动:", REDIRECT)

# scope 必须显式传，否则用户授权为空，调 API 报 99991679
auth_url = "https://accounts.feishu.cn/open-apis/authen/v1/authorize?" + urlencode({
    "app_id": APP_ID, "redirect_uri": REDIRECT,
    "scope": "search:knowledge_qa:read offline_access"})
print("[..] 正在打开浏览器授权页，请登录并点击授权...")
webbrowser.open(auth_url)

server.timeout = 300
try: server.serve_forever()
except KeyboardInterrupt: pass

ut = None
import time
for _ in range(30):
    if os.path.exists(TOKEN_FILE):
        ut = json.load(open(TOKEN_FILE)).get("access_token"); break
    time.sleep(1)
if not ut:
    print("[fail] 未拿到 token，退出"); sys.exit(1)

body = {"query": query, "knowledge_scope": scope, "model_type": "doubao", "enable_image": False}
if node:
    body["enterprise_knowledge_source"] = {
        "wiki": {"searchable": True, "filter": {"node_tokens": [node]}}}
r = http_json("https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer", body,
              {"Authorization": "Bearer " + ut})
print(json.dumps(r, ensure_ascii=False, indent=1)[:5000])
```

## 附录 B qa_call.py（日常调用）

```python
# -*- coding: utf-8 -*-
"""用已保存的 user_token.json 调端到端问答。用法: qa_call.py [query] [scope] [node_token]"""
import json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
TMP = os.path.dirname(os.path.abspath(__file__))
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
print(json.dumps(r, ensure_ascii=False, indent=1)[:6000])
```

## 附录 C qa_refresh.py（token 续期）

```python
# -*- coding: utf-8 -*-
"""用 refresh_token 刷新 user_access_token。"""
import winreg, json, io, sys, os, urllib.request, urllib.error

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
TMP = os.path.dirname(os.path.abspath(__file__))
TF = os.path.join(TMP, "user_token.json")

k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
APP_ID, _ = winreg.QueryValueEx(k, "APP_ID")
APP_SECRET, _ = winreg.QueryValueEx(k, "APP_SECRET")

old = json.load(open(TF))
req = urllib.request.Request("https://accounts.feishu.cn/oauth/v3/token",
    data=json.dumps({"grant_type": "refresh_token", "client_id": APP_ID,
                     "client_secret": APP_SECRET,
                     "refresh_token": old["refresh_token"]}).encode(),
    headers={"Content-Type": "application/json; charset=utf-8"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=30).read())
except urllib.error.HTTPError as e:
    r = {"_http": e.code, "_body": e.read().decode("utf-8", "replace")}

if r.get("code") == 0:
    json.dump(r, open(TF, "w"), ensure_ascii=False)
    print("[ok] token 已刷新  expires_in:", r.get("expires_in"), " scope:", r.get("scope"))
else:
    print("[fail]", json.dumps(r, ensure_ascii=False)[:500])
    print("       refresh_token 失效，请重跑 feishu_oauth_qa.py 重新授权")
```

---

## 变更记录

| 日期 | 内容 |
|---|---|
| 2026-10-09 | **三件套全部验证闭环**：端到端问答 ✅（多次实测含引用答案）、向量搜索 ✅（灰度开通，原文片段命中）、图片下载 ✅（真实 image_key 下载并核验内容）。补充 token 双过期场景：refresh_token 7 天超期报 20037，重新授权即可 |
| 2026-09-28 | 首版。第 0 章通用准备 + 第 1 章知识问答三件套（当时端到端已验证；向量搜索灰度未开返回空；图片下载端点通过、待真实 image_key 闭环） |

## 总状态（2026-10-09）

| API | 状态 | 备注 |
|---|---|---|
| 端到端问答 | ✅ 可用 | 耗 AI 额度（100016=额度尽，间歇性属正常配额） |
| 向量搜索 | ✅ 可用 | 原文片段检索，免额度，数值类问题优先 |
| 图片下载 | ✅ 可用 | 依赖端到端 enable_image 返回的 image_key |

配套资产：skill `xfeishu_qa`（`~\.claude\skills\xfeishu_qa\`，智能路由+输出约定，运行时产物在
`D:\TRAE\claude_work\feishu_qa\`）；脚本三件套源码见附录 A/B/C。
