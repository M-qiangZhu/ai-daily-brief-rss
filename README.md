# 每日AI资讯

一个面向中英文信息源的 AI 新闻检索与静态页面生成工具。项目优先监控 AI 企业的官方产品、研究、工程、API、GitHub 和 Hugging Face 动态，并以中文媒体、政策搜索和技术社区作为补充。

## 功能概览

- 从 AI 垂直媒体、科技媒体、政策源、南通本地动态、运营商新闻、综合 RSS 和社区源检索 AI 资讯。
- 监控 OpenAI、Google/DeepMind、Anthropic、Meta、Microsoft、NVIDIA、DeepSeek、Qwen、Kimi、MiniMax、字节 Seed 等官方渠道。
- 支持 RSS/Atom、HTML 列表页、GitHub Releases、Hugging Face API 和百度新闻搜索。
- 官方资讯优先保留，英文标题和摘要保持原文。
- 支持 RSS/Atom 数据源，包括阮一峰博客、IT之家、V2EX、新智元等。
- 使用关键词过滤，只保留人工智能、模型、Agent、AI 编程、算力芯片、智能驾驶、机器人、AI 硬件、AI 安全等相关内容。
- 每天按中国时间自然日生成当日资讯，并永久保存每日 JSON 归档。
- 同时生成今日页面、历史归档页面、归档索引、前端 JSON 数据和本地 latest 数据。
- 前端为纯静态页面，支持桌面端、移动端和深/浅色切换。
- 分类正文使用单开式手风琴，并提供吸顶分类导航和 URL hash 深链。
- 记录每个信源的成功时间、收录数、错误与连续失败次数。

## 环境要求

- Python 3.11 或更高版本
- uv

如果还没有安装 uv，可以参考官方安装方式；本项目的依赖由 `pyproject.toml` 和 `uv.lock` 管理。

## 安装依赖

在项目根目录执行：

```bash
uv sync
```

这条命令会根据 `pyproject.toml` 和 `uv.lock` 创建或更新本地虚拟环境，并安装运行所需依赖：

- `httpx`：请求 RSS、Atom 和百度新闻页面。
- `feedparser`：解析 RSS/Atom feed。
- `beautifulsoup4`：清洗摘要 HTML、解析百度新闻结果页。
- `pytest`：开发测试依赖。

## 生成资讯数据和页面

推荐使用项目提供的命令行入口。默认会按 `Asia/Shanghai` 中国时间自然日抓取当天资讯：

```bash
uv run ai-daily-brief
```

命令解释：

- `uv run`：在 uv 管理的项目环境中运行命令，确保使用项目依赖。
- `ai-daily-brief`：`pyproject.toml` 中注册的命令行脚本，实际入口是 `src.main:main`。
- 默认日期口径：`Asia/Shanghai` 当天 00:00:00 到 23:59:59。
- 每天生成的新资讯会合并写入 `docs/archive/YYYY-MM-DD.json`，历史 JSON 永久保留。

也可以直接运行根目录入口文件：

```bash
uv run python main.py
```

这和上面的命令效果基本一致，适合本地调试。

常用参数：

```bash
uv run ai-daily-brief --date 2026-05-17
```

抓取指定中国自然日的资讯，适合补跑某一天。

```bash
uv run ai-daily-brief --config data/sources.json --docs-dir docs
```

显式指定数据源配置文件和静态页面输出目录。

```bash
uv run ai-daily-brief --json-only
```

只在终端输出当天抓取后的 JSON，不写入 `docs` 页面文件，适合调试检索结果。

```bash
uv run ai-daily-brief --days 7
```

手动抓取最近 7 天窗口，适合初始化或重建一段历史；日常定时任务不建议使用这个模式。

## 本地预览

生成页面后执行：

```bash
cd docs
python3 -m http.server 4173
```

命令解释：

- `cd docs`：进入静态站点输出目录。
- `python3 -m http.server 4173`：用 Python 启动一个本地静态文件服务，端口为 `4173`。

然后访问：

- 今日页面：`http://127.0.0.1:4173/ai-news.html`
- 历史归档：`http://127.0.0.1:4173/ai-news-archive.html`

不要直接双击 HTML 文件预览，因为页面需要通过 `fetch('assets/data/ai-news.json')` 读取本地 JSON，浏览器的文件协议可能会拦截这个请求。

## 当前检索方式

当前流程在 `src/domestic_ai_news.py`、`src/page_generator.py` 中实现，主要分为以下步骤：

1. 读取 `data/sources.json` 中的统一信源注册表。
2. 并发请求启用的 RSS/Atom、HTML、GitHub Releases、Hugging Face 和百度新闻来源。
3. 解析每条候选资讯的标题、链接、摘要、来源和发布时间。
4. 默认按 `Asia/Shanghai` 计算当天自然日窗口，也可用 `--date` 补跑指定日期。
5. 用内置 AI 关键词列表匹配标题和摘要，只保留相关内容。
6. 按规范化链接和标题指纹去重，同一事件优先保留官方来源。
7. 更新 `docs/archive/index.json` 归档索引和最新一天的前端兼容数据。
8. 使用官方、媒体、社区分层配额，避免社区或聚合媒体挤占官方动态。
9. 同一天内按领导关注优先级排序：政策、运营商、算力芯片、AI 技术、AI 模型、AI Agent、智能驾驶、机器人、AI 硬件、安全监管、AI 编程、一般 AI 资讯。
10. 前端会进一步按领导视角聚合为：政策与监管、南通市官方 AI 动态、运营商与央国企动态、算力/数据中心/云基础设施、AI 技术与产业应用、投融资与竞争格局、风险安全与合规、技术社区观察。

缺少发布时间的内容不会每次都被当成新文章。程序会把首次发现时间保存在 `data/state/first_seen.json`，并使用该时间决定归档日期。信源健康状态保存在 `data/state/source_health.json`，页面发布时会同步为 `docs/assets/data/source-health.json`。

## 定时运行

部署示例使用 `deploy/ai-daily-brief.cron`，每天 `00:00、08:00、16:00` 抓取最近 48 小时内容并合并到每日归档，用于补偿晚间发布、源站延迟和临时网络失败。

企业微信摘要固定在每天 `09:00` 发送一次，直接读取 `08:00` 已生成的当日归档，不会额外触发检索。信源异常仅保留在后台日志中，不写入企业微信摘要。

南通本地动态会同时检索市级部门、区县政府和媒体转载。结果必须同时包含南通地域信号与明确的 AI、算力、大模型、机器人、智能制造等内容，避免普通本地新闻混入。

## 领导简报视图

页面顶部会自动生成“领导摘要”，默认提炼三类信号：

- 政策信号：当天最值得优先关注的政策与监管动态。
- 南通关注：南通市级、区县政府及媒体报道中的 AI 相关动态。
- 电信关注：运营商、央国企、算力、数据中心和云基础设施相关动态。
- 技术趋势：模型、智能体、行业应用、终端、机器人和可产品化方向。

正文不再只是按时间罗列新闻，而是按领导视角分类展示。每个分类会先给出一条“核心摘要”，再列出对应新闻，适合快速扫读和转写成邮件/PDF 简报。

页面上方的分类卡片可以直接跳转到对应详情板块。历史归档中原有的“AI模型与智能体技术”“行业应用与商业化”“AI终端、机器人与硬件”会在前端统一展示为“AI技术与产业应用”，无需改写历史 JSON。

命令执行时还会生成企业微信机器人可用的 markdown 摘要。设置 `WECHAT_WEBHOOK_URL` 并添加 `--notify` 后，会把公网页面链接和当天领导摘要推送到企业微信群。

RSS/Atom 来源会读取 feed 条目的标题、链接、发布时间和摘要/正文片段。百度新闻来源会访问搜索结果页，从结果块中提取标题、链接、来源、摘要和中文时间。

关键词匹配规则：

- 中文关键词使用子串匹配，例如 `人工智能`、`大模型`、`具身智能`。
- 英文关键词使用大小写不敏感的词边界匹配，例如 `AI` 不会误命中 `Daily`。
- 每条资讯只要标题或摘要命中任一关键词，就会被收录。
- 对 IT之家、V2EX 这类综合源会启用更严格的二次过滤：内容需要命中更强的 AI 信号，避免普通科技、账号价格、推广和闲聊内容混入。
- V2EX 会额外过滤 `[推广]`、中转站、充值、接码、地区价格、宣传付费类帖子；对 `[分享发现]`、`[程序员]`、`[问与答]` 等节点，会要求正文具有明确的 AI 技术、项目、模型或工具上下文。

当前关键词覆盖方向包括：

- 核心 AI：AI、AIGC、AGI、生成式 AI、大模型、智能体、多模态、RAG、Embedding 等。
- LLM / 模型技术：LLM、VLM、MoE、Transformer、Diffusion、长上下文、CoT、MCP 等。
- AI 编程：Copilot、Cursor、Windsurf、Claude Code、Codex、Cline、Aider 等。
- Agent / 工作流：AI Agent、Multi-Agent、LangGraph、AutoGen、Dify、n8n、Browser Use 等。
- 主要模型公司与产品：OpenAI、ChatGPT、Claude、Gemini、DeepSeek、Qwen、豆包、Kimi、GLM 等。
- 算力与硬件：NVIDIA、CUDA、Blackwell、H100、GB200、昇腾、TPU、AI PC、AI 手机等。
- 行业方向：自动驾驶、机器人、具身智能、AI SaaS、AI 搜索、AI 安全、AI 监管等。

## 数据源配置

数据源配置文件：

```text
data/sources.json
```

配置分为两类：

- `feeds`：RSS/Atom 来源。
- `searches`：百度新闻搜索来源。

RSS 示例：

```json
{
  "name": "IT之家",
  "url": "https://www.ithome.com/rss/",
  "category": null,
  "enabled": true,
  "max_entries": 30
}
```

字段解释：

- `name`：页面中展示的来源名称。
- `url`：RSS/Atom 地址。
- `category`：可选固定分类；为 `null` 时由程序根据标题和摘要自动分类。
- `enabled`：是否启用该来源。
- `max_entries`：每次最多读取多少条 feed 项。

百度新闻搜索示例：

```json
{
  "name": "主流财经科技媒体",
  "query": "AI 大模型 人工智能 算力 智能体 36氪 财联社 第一财经 每日经济新闻 21世纪经济报道 澎湃 证券时报",
  "category": null,
  "enabled": true,
  "max_results": 12
}
```

字段解释：

- `query`：传给百度新闻搜索的关键词组合。
- `max_results`：每个搜索入口最多读取多少条结果。

## 输出文件

生成后会写入：

```text
docs/ai-news.html
docs/ai-news-archive.html
docs/assets/data/ai-news.json
docs/archive/index.json
docs/archive/YYYY-MM-DD.json
data/ai_news/latest.json
```

用途说明：

- `docs/ai-news.html`：今日资讯页面。
- `docs/ai-news-archive.html`：历史归档页面。
- `docs/assets/data/ai-news.json`：最新有数据日期的兼容数据副本。
- `docs/archive/index.json`：历史归档索引，包含日期、数量、分类计数和重点标题。
- `docs/archive/YYYY-MM-DD.json`：按日期永久保存的归档数据，前端点击日期时动态读取。
- `data/ai_news/latest.json`：最近一次生成的完整数据副本，方便其他脚本读取。

## 测试

运行测试：

```bash
uv run pytest
```

这会执行 `tests` 目录中的单元测试，覆盖 RSS 解析、AI 关键词过滤、百度新闻结果解析和页面数据写入。

## 常见调整

新增 RSS 来源：编辑 `data/sources.json` 的 `feeds` 数组，加入新的 `name` 和 `url`。

临时关闭某个来源：把对应配置的 `enabled` 改为 `false`。

补跑指定日期：使用 `--date YYYY-MM-DD`。

初始化一段历史：使用 `--days 7` 等窗口参数，日常定时任务建议保持默认当天模式。

查看原始 JSON：使用 `--json-only`，或打开 `docs/assets/data/ai-news.json`。
