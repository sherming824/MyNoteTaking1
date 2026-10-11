# 翻译功能与 Neon 配置

## 已实现的行为

- 翻译当前编辑器中的标题和正文，也支持尚未保存的新笔记。
- 自动识别源语言；目标语言为简体中文、繁体中文、英语、日语、韩语、法语、德语、西班牙语。
- 点击 Translate 后显示只读预览，不覆盖原文。点击 Save as new note 才新增译文笔记。
- 译文保存后仍停留在原文编辑器，避免丢失未保存的原文。
- 原文或目标语言改变后，旧预览不能保存；切换笔记后不会显示旧请求迟到的结果。
- 原有笔记自动保存行为保留；翻译动作本身不会自动保存新建的原文草稿。
- 单次源文本最多 6,000 个 Unicode 字符，标题最多 200 个字符。
- 模型调用失败、超时、限流、输出格式错误或截断时显示错误，并保留原文。
- 提示词位于 `prompts/translate_prompt.md`；服务层在 `src/services/translation.py`。

## 本地运行

Windows CMD，在项目根目录执行：

```cmd
cd /d D:\task11\MyNoteTaking1
venv\Scripts\activate
python -m pip install -r requirements.txt
python src/main.py
```

打开 http://localhost:5001。更新 Python 代码或 `.env` 后，需要 Ctrl+C 停止旧进程，再重新启动。
当前本机 `.env` 已切换到 OpenRouter 并通过真实翻译验证；不要用示例文件覆盖已有 `.env`。
新克隆的仓库可从 `.env.example` 复制生成 `.env`，再自行填写凭证。

校园接口配置（仅供需要切回校园接口时参考）：

```dotenv
LLM_API_URL=https://genai.comp.polyu.edu.hk/api/v1/chat/completions
LLM_MODEL=DeepSeek-V4-Flash
LLM_API_KEY=
LLM_JSON_MODE=prompt
```

密钥只由 Flask 服务端读取，使用 `Authorization: Bearer ...` 调用上述接口；浏览器不接收密钥。
`.env` 已被 Git 忽略，`.env.example` 只包含空白凭证字段。

**按学校提供的说明，该接口仅校园网可访问。** 本机目前不在校园网，真实测试请求超时。
因此，自动化测试和模拟界面测试通过不等于 DeepSeek 已成功返回真实译文。
后续已使用 OpenRouter 完成真实调用，并由项目维护者确认 Neon 保存与持久化验证通过。
回到校园网后，用一小段普通文本验证标题、段落、目标语言及保存结果。

## API

`POST /api/translate`，JSON 请求示例：

```json
{"title":"Meeting plan","content":"Please finish the report by Friday.","target_language":"zh-CN"}
```

成功返回三个字段：`title`、`content`、`target_language`；失败返回 `error` 和相应 HTTP 状态。
该接口不写数据库。保存预览调用原有 `POST /api/notes`。

## Neon 持久化

本项目维护者已配置 Neon，并确认初始化和笔记读写测试通过。新克隆的项目若没有
`DATABASE_URL`，本地仍默认使用 `database/app.db`，需要自行配置自己的连接串。

1. 在 Neon 创建 PostgreSQL 项目，在连接面板取得 **pooled** 连接串。
2. 将完整连接串写入本地 `.env` 的 `DATABASE_URL`。不要将数据库密码提交到仓库。
3. 可将 **direct** 连接串写入 `DATABASE_INIT_URL`，供初始化命令使用。
4. 执行 `python -m flask --app src.main init-db` 创建表，再启动应用验证新增和重新加载。
5. 日后在 Vercel 的环境变量中配置相同的 `DATABASE_URL`；初始化连接无需用于普通请求。

代码将 PostgreSQL URL 规范化为 Psycopg 3 驱动，要求 SSL，使用 `NullPool` 避免应用连接池与
Neon pooled 连接叠加。连接参数保留，连接超时设为 10 秒。云端启动不自动建表。
Vercel 缺少外部数据库配置时会明确报错，不会退回临时 SQLite。

**切换数据库不会自动迁移已有 SQLite 笔记。** 原文件保留；需要迁移时另做导入和数量核对。

## 上线前仍需完成

- 校园网限制意味着不能假设 Vercel 能访问校内模型。应为线上环境配置公网可访问的服务。
- 如采用课件中的 OpenRouter，将 `LLM_API_URL` 改为 `https://openrouter.ai/api/v1/chat/completions`，
  设置该服务提供的模型 ID 和它自己的 API key。校园密钥不能用于 OpenRouter。
- `public/` 静态资源和 Vercel 运行配置已完成，本地测试通过；实际云端构建尚未验证。
- 本地 Neon 已验证；仍需验证部署后刷新及重新部署时笔记仍然存在。
- 原应用是共享演示应用，没有账号隔离。公开上线前确定访问和调用额度限制。

详细的 OpenRouter 配置与 Vercel 操作见 [部署指南](vercel-deployment.md)。

## 验证

```cmd
python -m unittest discover -s tests -v
node tests/frontend.test.cjs
python -m pip check
```

后端测试使用内存 SQLite 和模拟 LLM HTTP 响应，不改动本地笔记、不消耗模型额度。
前端测试覆盖保存竞争、预览、另存、失败重试及迟到响应。
独立浏览器测试使用 5002 端口和临时内存数据库，页面带 UI TEST 标记；测试页面不属于提交用演示。
