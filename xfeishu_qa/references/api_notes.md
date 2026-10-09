# 飞书知识问答 API 详细参考（xfeishu_qa skill）

实测整理于 2026-09-28。所有结论均来自真实调用验证，未验证项已标注。

## 1. 通用

- 认证：`Authorization: Bearer <user_access_token>`，**不支持 tenant_access_token**（报 99991663）
- token 获取：OAuth 授权码模式
  - 授权页：`https://accounts.feishu.cn/open-apis/authen/v1/authorize?app_id=...&redirect_uri=http://localhost:8723/callback&scope=search:knowledge_qa:read offline_access`
  - 换 token：`POST https://accounts.feishu.cn/oauth/v3/token`，body
    `{grant_type: "authorization_code", client_id, client_secret, code, redirect_uri}`
  - 刷新：同端点，`{grant_type: "refresh_token", client_id, client_secret, refresh_token}`
  - code 5 分钟有效、一次性；user_token 7200s；refresh_token 7 天、一次性
- scope 回显验证：换 token 响应的 `scope` 字段应含
  `auth:user.id:read offline_access search:knowledge_qa:read`
- **token 实际权限 = 应用已开通权限 ∩ 用户授权 scope**。授权 URL 不传 scope → 授权为空 → 调 API 报 99991679

## 2. 端到端问答 answer

`POST https://open.feishu.cn/open-apis/search/v2/knowledge_qa/answer`（频率 100 次/分）

### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| query | string | 是 | 1~1000 字符 |
| knowledge_scope | string | 是 | enterprise / internet / llm / hybrid |
| enterprise_knowledge_source | object | scope=enterprise/hybrid 时必填 | 知识源开关集合，见下 |
| model_type | string | 是 | doubao / deepseek / doubao_thinking / doubao_auto_thinking |
| enable_image | boolean | 否 | 默认 false；true 则答案含图片 |

enterprise_knowledge_source 子结构（每个类型独立开关）：`doc / docx / sheet / bitable /
mindnote / file / helpdesk / mail / calendar / moment / minute` 均为 `{searchable: bool}`；
`wiki` 支持 `filter: {node_tokens: [], space_ids: []}`；`drive`/`space` 支持
`filter: {doc_tokens: [], folder_tokens: []}`；`message` 支持
`filter: {chat_ids: [], time_range: {start, end}, reject: {...}}`。filter 可省，省略=该类型全量授权范围。

### 成功响应（status_code=0）

```jsonc
{
  "answer": "...内嵌 [[1]](引用链接)...",
  "reasoning_content": "",            // 思考模型的思考过程
  "references": { "enterprise_refs": [
    { "id": "...", "title": "文档名", "content": "原文片段",
      "source_type": 2, "url": "https://...feishu.cn/wiki/..." } ] },
  "extra": { "submit_quota_record_id": "..." },
  "status_code": 0, "status_message": ""
}
```

### 验证记录

- 2026-09-28：`query="SOC架构文档里有哪些CU"` + wiki 节点过滤 → 返回 14 CU（12 BPC + 2 harvest）、
  19.2MB SPM、32GB GMEM，附 2 条 wiki 引用，与原文通读结论一致 ✅

## 3. 向量搜索 search

`POST https://open.feishu.cn/open-apis/search/v2/knowledge_qa/search`（频率 10 次/秒）

- 权限同端到端（执行飞书知识问答能力），user token
- 请求体：`query`（非必填，≤1000 字符）+ `enterprise_knowledge_source`（非必填，结构同上）
- 响应：`{"data": {"passages": [{"id","title","content","source_type"(1=space/wiki/message/helpdesk/lingo),"url","score"}]}, "code": 0, "msg": "success"}`

### 状态

- 2026-09-28 上午：端点存在、认证通过，但返回 200 空 `{}`（当时灰度未开）；
- 2026-09-28 下午：**灰度开通，验证可用** ✅。`query="CIM300 的 D2D 带宽是多少"` + wiki 节点过滤
  → 返回 passages，片段为文档**原文**（含 "D2D bandwidth: 128 GB/s, UCIE-S x 4" 原句及上下文）。
  用法注意：passages 是原文片段，可信度高于生成式答案；200 空 `{}` 若再现则为灰度回退或范围内无匹配。

## 4. 答案图片下载 images

`GET https://open.feishu.cn/open-apis/search/v2/knowledge_qa/images/<image_key>`
（频率 1000 次/分、50 次/秒）

- image_key：端到端问答 `enable_image: true` 时答案中返回的 `img_v3_` 前缀 key
- 成功：HTTP 200，响应体为图片二进制流
- 依赖：端到端问答可用（有额度）；文档标注"需开通灰度"

### 验证记录

- 2026-09-28：**完整闭环 ✅**。enable_image 问答返回 3 个真实 image_key → 逐一 GET 下载均 HTTP 200
  （341KB jpeg / 68KB png / 254KB png），内容确为 D2D Subsys 架构框图（UCIE + D2D NOC + AMAP）。
  注意 Content-Type 是实际图片类型（jpeg/png），保存扩展名按 Content-Type 定。
- 此前假 key 探测返回 `400 code 14001`（非 404）→ 端点存在、认证通过、在校验 key。
- 文档 curl 示例中的 `fsopen.bytedance.net` 为旧域名，以 open.feishu.cn 为准

## 5. 错误码对照（全部实测或文档核实）

| 错误码 | 含义 | 处理 |
|---|---|---|
| 99991663 | token 类型不对 | 只认 user token，改走 OAuth |
| 99991679 | 用户授权缺 scope（错误体点名缺哪个） | 后台开权限 + 授权 URL scope 补上该标识，重新授权 |
| 99991677 | token 过期 | qa_refresh.py 刷新，失败则重新授权 |
| 20071 | redirect_uri 与授权时不一致 | 与后台登记一字不差 |
| 20010 | 用户不在应用可用范围 | 后台加入可用范围 |
| 20003/20004/20065 | code 无效/过期/已用 | 重新发起授权（code 5 分钟、一次性） |
| 100013 | enterprise 范围缺 enterprise_knowledge_source | 补知识源参数 |
| 100016 | AI 额度用完 | 管理员购买 AI 增值权益；停止重试 |
| 14001 | image_key 无效 | 用答案返回的真实 key |
| 404 page not found | 路径不存在 | 核对 URL（注意 /v2/） |

## 6. 后台一次性配置（首次使用）

1. 权限管理：开通「知识问答」能力权限 + `offline_access`（后台权限是中文名，
   从 API 文档「权限要求」链接点进去最准；搜英文 scope 标识搜不到）
2. 开发配置 → 安全设置 → 重定向 URL：添加 `http://localhost:8723/callback`（保存即生效）
3. 开发配置 → 可用范围：包含使用者
4. 本机注册表 `HKCU:\Environment` 写入 `APP_ID` / `APP_SECRET`

概念详解与人类视角从零教程：`D:\TRAE\claude_work\feishu_api\飞书API使用说明.md`
