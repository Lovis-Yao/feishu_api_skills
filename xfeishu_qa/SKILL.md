---
name: xfeishu_qa
description: 飞书「知识问答」API 调用套件——端到端问答（带引用的生成式答案）、向量搜索、答案图片下载。当用户要求"问飞书知识库/企业知识问答/检索飞书文档语义片段/下载问答答案里的图片"时使用。处理 token 授权、续期、错误码排错。
---

# xfeishu_qa：飞书知识问答 API 调用

本 skill 封装飞书「知识问答」三个 API 的完整调用链。**所有功能已验证可用**——
使用时直接调脚本取结果，按「输出约定」返回答案即可，无需先检查状态或汇报过程。
所有脚本零第三方依赖（纯 Python 标准库），凭证从注册表 `HKCU:\Environment`
的 `APP_ID`/`APP_SECRET` 读取。

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/feishu_oauth_qa.py` | 首次授权全流程：本机 8723 起回调服务 → 弹浏览器授权 → 换 token 存 `scripts/user_token.json` → 试调一次 |
| `scripts/qa_refresh.py` | token 过期时用 refresh_token 无感续期（覆盖写回 user_token.json） |
| `scripts/qa_call.py` | 端到端问答：`qa_call.py "问题" [scope] [wiki节点token]` |
| `scripts/qa_search_try.py` | 向量检索（返回片段+相似度，不生成答案） |
| `scripts/qa_img_test.py` | enable_image 问答 + 正则提取答案里的 image_key |

脚本目录即工作目录：token 文件 `user_token.json` 落在 scripts/ 下。
本 skill 运行在 Windows，Python 路径 `C:/Users/<user>/AppData/Local/Programs/Python/Python314/python.exe`（不存在时用 `py`）。

## 目录约定（重要：skill 目录只读）

- **skill 目录是纯代码，运行时禁止写入**——不得把 token、图片、答案等任何产物写进
  `~\.claude\skills\xfeishu_qa\`（它会被同步/分发，混入凭证和数据是安全事故）；
- **运行时工作目录**：`FEISHU_QA_HOME` 环境变量指定，默认 `D:\TRAE\claude_work\feishu_qa`：
  - `user_token.json`（凭证缓存，权限等同用户身份，勿入 git/勿分发）
  - `last_answer_img.json`（最近一次带图答案原文）
  - `downloads\<时间戳>\img_N.<ext>`（下载的图片，按次归档，扩展名按 Content-Type 定）；
- 脚本已内置该路径逻辑（读 `FEISHU_QA_HOME`，不存在则自动创建），无需手动建目录。

## 三个 API 速查

| API | 方法与路径 | 说明 |
|---|---|---|
| 端到端问答 | `POST /open-apis/search/v2/knowledge_qa/answer` | 生成式答案+引用（references.enterprise_refs），耗 AI 额度 |
| 向量搜索 | `POST /open-apis/search/v2/knowledge_qa/search` | 只检索：`passages[]{content,url,...}`；2026-09-28 已验证可用（不耗生成额度，返回原文片段最可信） |
| 图片下载 | `GET /open-apis/search/v2/knowledge_qa/images/<image_key>` | 2026-09-28 已闭环验证：200=图片二进制流（jpeg/png）；14001=image_key 无效 |

域名一律 `https://open.feishu.cn`（文档 curl 示例里的 fsopen.bytedance.net 是旧写法）。
认证一律 **user_access_token**（tenant token 会报 99991663），Header：
`Authorization: Bearer <token>` + `Content-Type: application/json; charset=utf-8`。

端到端请求体模板：

```jsonc
{
  "query": "问题（1~1000字符）",
  "knowledge_scope": "enterprise",        // enterprise/internet/llm/hybrid
  "enterprise_knowledge_source": {        // scope=enterprise/hybrid 时必填(否则100013)
    "wiki": { "searchable": true,
              "filter": { "node_tokens": ["<wiki节点token>"] } } }  // filter 可省
  "model_type": "doubao",                 // doubao/deepseek/doubao_thinking/doubao_auto_thinking
  "enable_image": false
}
```

## 使用流程（智能路由，用户无感）

### 路由决策（调用前由 AI 按问题语义判断）

| 问题类型 | 判断特征 | 路径 |
|---|---|---|
| **数值/参数查询** | 问"多少/多高/几"类具体值 | 向量搜索先行：命中含明确值 → 直接返回原文片段（免额度、无幻觉） |
| **概念/原理/对比/怎么做** | 问"是什么/为什么/区别/如何" | 端到端问答（向量片段仅作上下文参考，不作答） |
| **结构/框图/连接关系** | 问"架构/组成/框图/怎么连" | 端到端问答 + 必附图（见图片策略） |
| **判断不了/向量未命中或片段不足以回答** | — | 自动升级端到端问答；升级对用户透明，不汇报"先试了A再试B" |

- **enable_image 默认 true**：不额外耗生成额度，返回与否由飞书按相关性决定——
  有 image_key 就下载附上（输出本地路径+一句话图注），没有就不提图；
- node_token 过滤：用户指明文档/知识库时带上；未指明时省略 filter（全量授权范围检索）。

### 执行（错误处理决策树）

1. **token 是否有效？** `scripts/user_token.json` 不存在 → 跳第 4 步。
2. **调用**：报 `99991677`（过期）→ 先跑 `qa_refresh.py` 再重试；刷新也失败 → 跳第 4 步。
3. **按业务错误码处理**：
   - `100016` 额度用完 → 停止重试，告知用户找飞书管理员购买 AI 增值权益（管理后台增值服务页），间歇性可用属正常配额；
   - `100013` → enterprise 范围必须带 `enterprise_knowledge_source`，补参数；
   - `99991679` → 用户授权缺 scope（错误体会点名缺哪个）。指引：后台开对应权限 → 重跑 `feishu_oauth_qa.py`（授权 URL 的 scope 参数需加上缺的标识，知识问答默认 scope 为 `search:knowledge_qa:read offline_access`）。
4. **无 token / 刷新失效**：后台运行 `feishu_oauth_qa.py`（run_in_background），让用户在弹出的浏览器页面点授权，授权后轮询 `user_token.json` 出现即完成。**授权 URL 必须带 scope，否则白授权**。
5. **首次使用前置检查**（用户首次跑此 skill 时确认一次，通过后不必重复）：
   - 开发者后台已开通「知识问答」能力权限 + `offline_access`；
   - 安全设置里登记了重定向 URL `http://localhost:8723/callback`（一字不差）；
   - 用户在应用可用范围内。
   - 注册表有 APP_ID/APP_SECRET（`HKCU:\Environment`）。

## 输出约定（对用户呈现）

- **直接返回答案**：命中即给结论+关键数值+出处（文档名/链接），不汇报调用过程、token 状态、
  错误码流水、脚本执行细节、路由选择；续期、重试、升级等中间步骤静默完成，用户无感；
- 图片直接给下载后的本地文件路径 + 一句话图注；
- **仅失败时才报告**：所有自动恢复手段（刷新/重试）用尽仍失败，才说明报错和需要用户做的动作
  （如充值额度、后台开权限、重新点授权）；
- 生成式答案与向量搜索原文片段冲突时，以原文片段为准并指出差异；
- 数值用于正式结论（如 testplan 审查依据）前仍需按引用回原文核验（生成式答案有幻觉风险）。

## 结果使用原则（内部判断用，不向用户复述）
- 图片下载闭环依赖端到端 `enable_image: true` 的答案给出真实 image_key（`img_v3_` 前缀），假 key 会报 14001。

## 详细参考

三个 API 的完整参数说明、请求/返回示例、10 个实测错误码对照表、后台配置逐步说明，
读 [references/api_notes.md](references/api_notes.md)。
面向人类读者的从零搭建教程（含概念讲解）：`D:\TRAE\claude_work\feishu_api\飞书API使用说明.md`。
