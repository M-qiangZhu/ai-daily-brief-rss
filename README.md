# 每日AI资讯

一个面向中文信息源的 AI 新闻检索与静态页面生成工具。项目会从 RSS 和百度新闻搜索结果中抓取最近几天的资讯，用 AI 关键词做过滤、去重和分类，然后生成可直接部署的静态页面。

## 功能概览

- 从 AI 垂直媒体、科技媒体、政策源、运营商新闻、综合 RSS 和社区源检索 AI 资讯。
- 支持 RSS/Atom 数据源，包括阮一峰博客、IT之家、V2EX、新智元等。
- 使用关键词过滤，只保留人工智能、模型、Agent、AI 编程、算力芯片、智能驾驶、机器人、AI 硬件、AI 安全等相关内容。
- 同时生成今日页面、历史归档页面、前端 JSON 数据和本地 latest 数据。
- 前端为纯静态页面，支持桌面端、移动端和深/浅色切换。

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

推荐使用项目提供的命令行入口：

```bash
uv run ai-daily-brief --days 7
```

命令解释：

- `uv run`：在 uv 管理的项目环境中运行命令，确保使用项目依赖。
- `ai-daily-brief`：`pyproject.toml` 中注册的命令行脚本，实际入口是 `src.main:main`。
- `--days 7`：只保留最近 7 天内发布或抓取到的资讯。

也可以直接运行根目录入口文件：

```bash
uv run python main.py --days 7
```

这和上面的命令效果基本一致，适合本地调试。

常用参数：

```bash
uv run ai-daily-brief --days 3
```

只抓取最近 3 天内容。

```bash
uv run ai-daily-brief --config data/sources.json --docs-dir docs
```

显式指定数据源配置文件和静态页面输出目录。

```bash
uv run ai-daily-brief --days 7 --json-only
```

只在终端输出抓取后的 JSON，不写入 `docs` 页面文件，适合调试检索结果。

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

当前流程在 `src/domestic_ai_news.py` 中实现，主要分为六步：

1. 读取 `data/sources.json`。
2. 并发请求启用的 RSS/Atom feed 和百度新闻搜索。
3. 解析每条候选资讯的标题、链接、摘要、来源和发布时间。
4. 根据 `--days` 计算时间窗口，过滤掉窗口之外的旧内容。
5. 用内置 AI 关键词列表匹配标题和摘要，只保留相关内容。
6. 按链接去重、按发布时间倒序排序，并写入静态页面数据。
7. 同一天内按领导关注优先级排序：政策、运营商、算力芯片、AI 技术、AI 模型、AI Agent、智能驾驶、机器人、AI 硬件、安全监管、AI 编程、一般 AI 资讯。
8. 前端会进一步按领导视角聚合为：政策与监管、运营商与央国企动态、算力/数据中心/云基础设施、AI 模型与智能体技术、行业应用与商业化、AI 终端/机器人/硬件、投融资与竞争格局、风险安全与合规、技术社区观察。

## 领导简报视图

页面顶部会自动生成“领导摘要”，默认提炼三类信号：

- 政策信号：当天最值得优先关注的政策与监管动态。
- 电信关注：运营商、央国企、算力、数据中心和云基础设施相关动态。
- 技术趋势：模型、智能体、关键技术与可产品化方向。

正文不再只是按时间罗列新闻，而是按领导视角分类展示。每个分类会先给出一条“核心摘要”，再列出对应新闻，适合快速扫读和转写成邮件/PDF 简报。

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
docs/archive/YYYY-MM-DD.json
data/ai_news/latest.json
```

用途说明：

- `docs/ai-news.html`：今日资讯页面。
- `docs/ai-news-archive.html`：历史归档页面。
- `docs/assets/data/ai-news.json`：前端页面实际读取的数据。
- `docs/archive/YYYY-MM-DD.json`：按日期保存的归档数据。
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

调整抓取时间范围：修改运行命令中的 `--days`。

查看原始 JSON：使用 `--json-only`，或打开 `docs/assets/data/ai-news.json`。
