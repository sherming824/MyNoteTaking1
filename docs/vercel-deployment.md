# OpenRouter 与 Vercel 部署指南

## 当前状态

- 翻译界面、独立提示词、JSON 接口、Neon 适配与自动化测试已实现。
- 项目维护者已完成本地 Neon 初始化和手动笔记读写验证。
- `public/`、`vercel.json`、`.python-version` 已准备完成。
- 自动化测试之外，OpenRouter 已真实返回 HTTP 200 和正确的中文标题、正文与段落。
- 项目维护者确认原文保存、译文另存、刷新、Neon 查询和重启后的持久化全部通过。
- 本地验证完成，下一步提交并推送 GitHub，再部署 Vercel，最后验证线上行为。

## 1. 配置 OpenRouter

1. 在 https://openrouter.ai 注册或登录。
2. 打开 https://openrouter.ai/settings/keys，创建用于此项目的 API key。
3. 在项目根目录执行 `notepad .env`，同时替换以下四行；保留 Neon 配置不变：

```dotenv
LLM_API_URL="https://openrouter.ai/api/v1/chat/completions"
LLM_API_KEY="在本机填写新创建的 OpenRouter key"
LLM_MODEL="openrouter/free"
LLM_JSON_MODE="prompt"
```

学校提供的 key 只能用于学校接口，不能与 OpenRouter 地址混用。
`openrouter/free` 是官方免费模型路由，适合初步验证；不同请求可能选择不同模型，也可能限流。
固定演示模型时，在 https://openrouter.ai/models 选择模型并复制其完整 model ID 替换 `LLM_MODEL`。
使用付费模型前应先确认其价格和自己的账户预算。

资料：[API 快速入门](https://openrouter.ai/docs/quickstart)、[免费路由](https://openrouter.ai/openrouter/free)。

## 2. 本地验证真实翻译

在原 CMD 中 Ctrl+C 停止旧服务，然后执行：

```cmd
cd /d D:\task11\MyNoteTaking1
venv\Scripts\activate
python src/main.py
```

打开 http://localhost:5001 并刷新。使用一条普通测试笔记，例如标题 `Meeting plan`、
正文 `Please finish the project report by Friday.`，目标语言选择简体中文。
确认真实返回译文，另存后原文不变，刷新后两个笔记都存在。
也可在 OpenRouter Activity 中查看是否记录了此次请求。

如果返回 429，表示服务限流或额度限制；等待后重试或另选可用模型。
返回 401/403 时检查 key 和账户权限；402 表示额度不可用。
不要只看到页面打开就认定翻译功能已经验证。

## 3. 提交并推送 GitHub

提交前确认 `.env`、本地数据库和虚拟环境不在待提交文件中：

```cmd
git status --short
git check-ignore .env
git diff --check
```

在 Windows CMD 中对已检查的项目代码创建 Git 提交，再推送自己的仓库：

```cmd
git add .gitignore .env.example .python-version .vercelignore README.md requirements.txt vercel.json src public prompts tests docs
git diff --cached --check
git diff --cached --name-only
git commit -m "Add translation, Neon storage and Vercel configuration"
git push origin main
```

确认文件列表没有 `.env`、数据库文件或 `venv/`；`.env.example` 是无凭证模板，可以提交。
`src/static/` 文件移到 `public/`，Git 中出现旧路径删除和新路径新增是正常现象。

仓库地址：https://github.com/sherming824/MyNoteTaking1
推送遇到登录提示时使用自己的 GitHub 账号完成认证。

## 4. 导入 Vercel

1. 登录 https://vercel.com，选择 Add New / Project。
2. 连接 GitHub，导入 `sherming824/MyNoteTaking1`。
3. Root Directory 使用仓库根目录。
4. Framework Preset 应识别为 Flask；若没有，选择 Flask。
5. Build Command、Install Command 和 Output Directory 使用框架默认值，不填写 `python src/main.py`。
6. 在首次点击 Deploy 前配置下面环境变量。

| 变量 | 值 |
|---|---|
| `DATABASE_URL` | 已验证的 Neon pooled 连接串 |
| `LLM_API_URL` | `https://openrouter.ai/api/v1/chat/completions` |
| `LLM_API_KEY` | OpenRouter 的 key |
| `LLM_MODEL` | 本地已验证成功的 model ID |
| `LLM_JSON_MODE` | `prompt` |
| `FLASK_DEBUG` | `0` |

Vercel 控制台的值直接粘贴内容，**不要添加 `.env` 文件中外层的引号**。
`DATABASE_INIT_URL` 仅供本地显式建表，已有表时不需要部署到 Vercel。
当前应用没有用到会话，`SECRET_KEY` 暂非必填。
`VERCEL` 由平台设置，无需自行配置。

## 5. 部署与验收

点击 Deploy，检查构建结果。部署成功后：

1. 打开项目网址，确认页面、图标、语言选择可用。
2. 验证笔记新增、保存、编辑、搜索和删除。
3. 验证一次真实翻译及译文另存，确认原文不变。
4. 刷新页面并重新部署，确认笔记仍在 Neon 中。
5. 截取真实运行结果，用部署 URL 和截图作为作业材料。

以后推送到关联分支通常会触发新的部署。更改 Vercel 环境变量后，需要重新部署使其生效。
本应用仍是共享演示应用，没有登录或每用户笔记隔离。

## 配置说明

- Python 版本：`.python-version` 中的 `3.12`。
- Flask 入口：`src/main.py` 中的 `app`。
- 静态资源：`public/index.html`、`public/favicon.ico`，由 Vercel CDN 提供。
- 函数访问 `/` 时重定向到 `/index.html`；本地由 Flask 直接提供页面。
- `vercel.json` 设置函数最长 60 秒，并排除 `.env`、虚拟环境和本地数据库等文件。
- `.vercelignore` 防止日后 CLI 部署时上传本地凭证和开发数据。
- 提示词文件保留在函数中，云端不会写本地 SQLite 或自动建表。

官方参考：[Flask](https://vercel.com/docs/frameworks/backend/flask)、
[Python runtime](https://vercel.com/docs/functions/runtimes/python)、
[环境变量](https://vercel.com/docs/environment-variables)。
