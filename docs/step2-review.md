# MyNoteTaking — 第 2 步检查与修复记录

检查日期：2026-10-11（Asia/Shanghai）
项目：`D:\task11\MyNoteTaking1`
仓库：https://github.com/sherming824/MyNoteTaking1

## 结论

原应用能够运行，正常的笔记增删改查和搜索可用。检查复现了自动保存前切换导致修改丢失、错误状态码不准确和输入校验不足等问题。本轮已完成针对性修复及本地回归验证，可继续规划翻译模块。

本轮没有添加翻译、迁移云数据库或部署 Vercel；改动保留在本地，未提交或推送 GitHub。

## 修改前的现状

环境已配置为 Python 3.12.15、项目独立 venv，原 requirements.txt 的锁定依赖可安装且通过 pip check。

独立内存数据库中的基线测试共 12 个场景：5 个正常操作通过，7 个异常场景不符合预期。

| 场景 | 原结果 | 修复后 |
|---|---|---|
| 新增、读取、编辑、按内容搜索、删除 | 正常 | 保持正常 |
| 更新不存在的笔记 | 500 | 404 JSON |
| 删除不存在的笔记 | 500 | 404 JSON |
| 提交 JSON 数组 | 500 | 400 JSON |
| 标题为 null | 500，暴露数据库错误细节 | 400 JSON |
| 标题超过 200 字符 | SQLite 接受并保存 | 400 JSON |
| JSON 格式损坏 | 500 | 400 JSON |
| Content-Type 为 text/plain | 500 | 415 JSON |

浏览器还复现：修改测试笔记 B 后，不等 2 秒自动保存就切换到 A，再返回 B，刚才的修改消失。新建但未保存的笔记也会显示无效的 Delete 按钮。

## 本轮修复

- 切换笔记或创建下一条笔记前保存未保存的编辑内容；失败时留在原编辑器并保留输入。
- 保存和删除请求进行期间暂时禁用编辑操作，避免重复提交、响应回来时覆盖另一条笔记的状态；请求设有超时。
- 未保存的新笔记隐藏 Delete；删除时取消待执行的自动保存。
- 搜索条件在保存和切换后继续生效；保留正文的缩进及换行。
- 后端校验 JSON 对象、字符串类型、标题长度和空内容；请求体限制为 1 MiB。
- HTTP 错误保留正确状态码并统一返回 JSON；数据库错误回滚，响应不再直接暴露 SQL 和异常详情。
- 不存在的 API 路径返回 404，不再返回首页 HTML；搜索中的 `%`、`_` 按文本处理。
- 消息用 textContent 显示，避免将未来模型/API 返回的错误字符串作为 HTML 插入。
- 默认仅监听 127.0.0.1，调试模式默认关闭；移除硬编码 SECRET_KEY，改从环境读取。当前功能不使用 session，所以本轮不要求设置该值。
- 前后端同源，不再开启全局 CORS；取消注册未被笔记界面使用的用户 CRUD 模板。它原本也不构成登录系统。
- 修正 UTC 时间在浏览器中的解析及日期标签；同步 README 中数据库路径、调试开关和测试说明。

涉及文件：`requirements.txt`、`README.md`、`src/main.py`、`src/routes/note.py`、`src/static/index.html`；新增 `tests/test_notes.py`、`tests/frontend.test.cjs` 和本记录的仓库副本。

## 依赖检查

仅更新两个有明确安全公告的组件：

| 组件 | 修改前 | 修改后 | 依据与实际关联 |
|---|---|---|---|
| Flask | 3.1.1 | 3.1.3 | session 的 Vary: Cookie 处理修复。当前应用尚未使用 session，相关利用条件未在此应用中复现。 |
| Werkzeug | 3.1.3 | 3.1.9 | Windows 特殊设备名路径过滤修复；本项目运行于 Windows，使用 send_from_directory。没有执行可能挂起服务的漏洞利用请求。 |

来源：[Flask 官方公告](https://github.com/pallets/flask/security/advisories/GHSA-68rp-wp8r-4726)、[Werkzeug 官方公告](https://github.com/pallets/werkzeug/security/advisories/GHSA-g6x2-hccm-hh4m)。

逐版本查询 PyPI JSON API 的漏洞元数据：原 requirements.txt 中有 2 个受影响包；修复后检查了虚拟环境内全部 14 个已安装包（包含 Windows 间接依赖 colorama 和 pip），均未返回未撤销的已知漏洞记录。完整核查摘要见 `dependency-audit.json`。

这反映查询当时的数据，不代表软件不存在未知漏洞。pip-audit 工具查询未能完成，本报告的漏洞结论来自直接查询 PyPI 元数据并核对上述官方公告，不将工具未完成的扫描计为成功。

## 验证结果

- 后端 unittest：10 项通过，包含 CRUD、搜索、非法输入、状态码、数据库回滚和配置。
- 前端 Node 逻辑测试：9 项通过，包含异步保存、切换、失败恢复、重复提交、草稿、搜索、删除和消息转义。
- pip check：通过，无依赖冲突。
- 浏览器：创建/保存、修改后立即切换、自动保存、刷新后持久化、正文搜索、新笔记隐藏 Delete 均通过。
- 浏览器删除：点击测试笔记 B 的 Delete 后，原生确认框阻塞了自动化；用户操作关闭后，列表确认 B 已删除，编辑器回到初始状态。删除接口和前端逻辑另有自动化测试覆盖。
- 服务重启后实际响应头：`Werkzeug/3.1.9 Python/3.12.15`。浏览器未记录到脚本错误。
- 测试使用单独的内存数据库；浏览器使用本轮创建的 Review test A/B 测试笔记，未操作已有用户笔记。当前保留一条 Review test A 作为可删除的验证示例。

执行方式（在项目根目录，先激活 venv）：

```cmd
python -m unittest discover -s tests -v
node tests/frontend.test.cjs
python -m pip check
```

Node 默认 test runner 的子进程隔离被当前环境拒绝，因此使用 `node tests/frontend.test.cjs` 执行同一套 node:test 测试，9 项均通过。

## Vercel 上线前仍要处理

1. **数据库**：当前仍写项目根目录 `database/app.db`，启动时建表。需要确定 Neon/Supabase 等外部持久化方案，配置数据库连接和初始化流程；不能把 Vercel 临时目录作为长期数据库。
2. **应用入口**：当前为 `src/main.py`。部署时需使用受支持的入口文件，或按当时官方配置显式指定该应用。
3. **静态资源**：核对入口页面与 favicon 的托管方式；官方建议静态资源放入 `public/`，本轮尚未迁移。
4. **环境与打包**：指定支持的 Python 版本，云端配置模型/数据库密钥，排除本地 venv 和测试数据，确保不上传密钥或本地数据库。
5. **翻译调用**：后续实现服务端调用、超时与错误处理；完成本地测试后再进行 Vercel 实测。
6. **公开演示的数据范围**：目前没有登录和每用户隔离，所有访问者共用笔记。如果要用于个人笔记而非共享课堂演示，需要额外设计访问控制。这不是关闭 Vercel 部署保护可以解决的问题。
7. **验收**：公网链接无需 Vercel 登录，实际翻译可用，笔记刷新后仍存在，再截取作业所需的翻译界面。

依据：[Flask on Vercel](https://vercel.com/docs/frameworks/backend/flask)、[Vercel 文件系统说明](https://vercel.com/docs/functions/runtimes#file-system-support)。本轮未声称已完成云端部署验证。

## 非阻塞事项

Python 3.12 测试时出现模型使用 datetime.utcnow() 的弃用警告；当前 CRUD 正常。数据库迁移时可统一处理时区字段和模型时间函数，本轮未扩大到数据库结构重写。
