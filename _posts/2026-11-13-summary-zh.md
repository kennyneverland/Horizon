---
layout: default
title: "Horizon Summary: 2026-11-13 (ZH)"
date: 2026-11-13
lang: zh
---

> 从 121 条内容中筛选出 21 条重要资讯。

---

**科技新闻**
1. [英伟达 CEO 黄仁勋辞职，继任与出口管制成焦点](#item-tech-news-1) ⭐️ 8.0/10
2. [Rust 1.100 稳定 never 类型与 Allocator API](#item-tech-news-2) ⭐️ 8.0/10
3. [谷歌发布 Gemini 4 Hydrogen 与 Orchestrator](#item-tech-news-3) ⭐️ 8.0/10
4. [Apple Foundation Models 框架：设备端与 Private Cloud Compute 访问](#item-tech-news-4) ⭐️ 8.0/10
5. [Anthropic IPO 传获六倍超额认购](#item-tech-news-5) ⭐️ 8.0/10
6. [Edge0-145B 宣称 145B 模型可本地运行](#item-tech-news-6) ⭐️ 7.0/10
7. [PostgreSQL 类型混淆原语被指可致 RCE](#item-tech-news-7) ⭐️ 7.0/10
8. [llm-gemini 0.37 与 Gemini 4 Hydrogen 定价](#item-tech-news-8) ⭐️ 7.0/10
9. [OpenAI 发布 Codex Security CLI 与 TypeScript SDK](#item-tech-news-9) ⭐️ 7.0/10
10. [Meta 开源 Astryx Beta 设计系统](#item-tech-news-10) ⭐️ 7.0/10
11. [VulnCheck：Glasswing 发现多但修复少](#item-tech-news-11) ⭐️ 7.0/10

**财经新闻**
1. [礼来口服减重药在华获批](#item-finance-news-1) ⭐️ 8.0/10
2. [美联储 2027 年 10 月会议不投票决定利率](#item-finance-news-2) ⭐️ 7.0/10
3. [AI 股票收窄跌幅，英伟达 CEO 离职影响待评估](#item-finance-news-3) ⭐️ 7.0/10
4. [三家 AI 公司遭诉要求停止前沿 AI 开发](#item-finance-news-4) ⭐️ 7.0/10
5. [印度 Clean Max 拟投 53 亿美元清洁能源支持 AI 算力设施](#item-finance-news-5) ⭐️ 7.0/10
6. [SpaceX 拟投逾 740 亿美元建得州与亚利桑那州 AI 园区](#item-finance-news-6) ⭐️ 7.0/10
7. [思科上调全年营收预期](#item-finance-news-7) ⭐️ 7.0/10
8. [应用材料公司季度营收指引高于预期](#item-finance-news-8) ⭐️ 7.0/10
9. [美国 10 月预算赤字创纪录](#item-finance-news-9) ⭐️ 7.0/10
10. [美国 10 月成屋销售创 16 年多新低](#item-finance-news-10) ⭐️ 7.0/10

---

## 科技新闻

<a id="item-tech-news-1"></a>
### [英伟达 CEO 黄仁勋辞职，继任与出口管制成焦点](https://apnews.com/article/nvidia-megaspeed-china-singapore-huang-5403f152a601cf82ce939f1d24fffa0f) ⭐️ 8.0/10

该条目称英伟达 CEO 黄仁勋辞职，相关来源链接指向 NVIDIA 新闻稿、路透社和《纽约时报》的 CEO 变动报道。提供的正文未给出辞职原因、继任者、生效时间或公司声明细节。社区评论将讨论扩展到中国出口管制、政府关系传闻和市场影响，但这些并非已证实事实。

hackernews · lldb · 11月12日 13:52 · [社区讨论](https://news.ycombinator.com/item?id=50467087)

**「背景」** 黄仁勋的辞职建立在先前披露之上：《纽约时报》2026 年 10 月报道其婚外情，11 月他承认后英伟达董事会宣布调查。路透社称，包括涉及疑似中国间谍的婚外情在内的披露使英伟达陷入危机。

**「影响」** 对依赖英伟达 AI 加速器的客户和投资者而言，领导层更替可能增加对出口合规、产品路线图和中国市场供应策略的不确定性；相关报道也可能引发对 AI 芯片与中国出口管制主题股票的重新定价。

**「社区讨论」** 评论区主要分歧在于事件动因：有人将黄仁勋的离任与所谓中国出口管制规避和私人关系传闻联系起来，也有人质疑这是媒体与政治博弈的“时机问题”，并强调这些说法多为未经证实的猜测。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/nvidia-ceo-jensen-huang-step-down-big-blow-ai-boom-2026-11-12/">Nvidia CEO Jensen Huang resigns in blow to AI boom he helped ...</a></li>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live ...</a></li>

</ul>
</details>

**标签**: `#NVIDIA`, `#AI chips`, `#China AI industry`, `#export controls`, `#A-share catalysts`

---

<a id="item-tech-news-2"></a>
### [Rust 1.100 稳定 never 类型与 Allocator API](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 已发布，官方博客称其稳定了 never 类型和 Allocator API 的核心部分，并让 Cargo 能够报告未使用的依赖。该版本还包含更多未逐项列出的语言与工具链变化。

hackernews · mbStavola · 11月12日 18:39 · [社区讨论](https://news.ycombinator.com/item?id=50472038)

**「版本稳定化背景」** Rust 的版本发布通常会把此前尚未稳定的语言或标准库能力转为稳定特性。社区讨论将 1.100 描述为长期等待的特性集中落地，包括 never type、Allocator API 核心部分以及 Cargo 的未使用依赖报告。

**「影响」** 对 Rust 开发者和库维护者而言，never 类型与 Allocator API 的稳定使这些能力更可用于正式项目；Cargo 的未使用依赖报告则可能要求维护者检查并清理 Cargo.toml 中的陈旧依赖。

**「社区讨论」** 社区评论把 never 类型、自定义分配器、minimum publish age 依赖冷却和 cargo install 默认使用 .crate 锁文件视为亮点，并补充称 bool::toggle、Box::map 等 API 也已稳定但未被博客重点提及。另有用户询问编译速度和 cargo clean 临时文件占用，这属于个人体验而非发布说明中的性能承诺。

**标签**: `#Rust`, `#programming languages`, `#open source`, `#developer tooling`, `#Cargo`

---

<a id="item-tech-news-3"></a>
### [谷歌发布 Gemini 4 Hydrogen 与 Orchestrator](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) ⭐️ 8.0/10

谷歌宣布推出面向日常编程和智能体工作流的 Gemini 4 Hydrogen，并提及 Orchestrator；当前来源未说明 Orchestrator 的具体能力或发布状态。开发者、企业和普通用户可访问该模型，统一报价为每百万输入 token 1.5 美元、每百万输出 token 7.5 美元。谷歌称其速度较 Gemini 3.8 Flash 提升 2.5 倍，Terminal-Bench 4.1 得分从 18.2% 升至 57%，默认档在 Artificial Analysis 指数上超过 Argon；这些均为厂商说法，尚无独立基准或部署证据。

hackernews · jonbaer · 11月12日 18:52 · [社区讨论](https://news.ycombinator.com/item?id=50472260)

**「背景」** Gemini 3.8 Flash 是本次发布用来对比的上一代快速执行模型档，因此新模型的终端基准分数、速度倍数和 token 价格会直接影响开发者是否替换它。Orchestrator 指协调多个模型或智能体调用的机制，理解该概念有助于判断此次发布为何同时强调模型执行与智能体工作流。

**「行动建议」** 对使用 Google Antigravity 的开发者而言，Gemini 4 Hydrogen 的开放和统一定价意味着可以立即在编码与智能体工作流中评估更快的执行路径，但需要重新核算推理成本：当前每百万 token 输入 1.5 美元、输出 7.5 美元，而社区讨论提到 1 月 1 日起谷歌模型可能涨价一倍。如果开发者基于 Orchestrator 构建多模型工作流，社区讨论也提示缓存和计费规则可能不直观，因此应先验证缓存命中、输出 token 计费以及订阅和剩余额度是否可用，再决定是否重新订阅或迁移工作负载。

**「社区讨论」** 评论者一方面调侃 Gemini 命名，另一方面欢迎更快的 Flash 类模型，并抱怨 Argon 和 Carbon 太慢；也有人将这一编排思路与 Anthropic advisor 模式、GitHub HydraFusion 多模型流水线类比，关注缓存计费如何工作。另有用户称 Google 定价页显示 1 月 1 日起所有 Google 模型价格翻倍，并讨论取消 Antigravity 订阅后余额仍需有效订阅才能使用的问题。

**标签**: `#AI models`, `#Google Gemini`, `#AI agents`, `#inference cost`, `#developer tools`

---

<a id="item-tech-news-4"></a>
### [Apple Foundation Models 框架：设备端与 Private Cloud Compute 访问](https://developer.apple.com/foundation-models-framework/) ⭐️ 8.0/10

Hacker News 讨论了 Apple 的 Foundation Models framework，重点包括设备端 AI、Private Cloud Compute 访问和开发者工具。评论区引用 Apple 文档称，参与 App Store Small Business Program 且首次 App Store 下载少于 200 万的开发者，可在 Apple Intelligence 可用地区无云端 API 费用使用运行在 Private Cloud Compute 上的 Apple Foundation Models，并通过 TestFlight 或 ad hoc 分发测试。

hackernews · kermatt · 11月12日 21:13 · [社区讨论](https://news.ycombinator.com/item?id=50474361)

**「背景」** Foundation Models framework 是 Apple 提供的原生 Swift API，面向开发者访问驱动 Apple Intelligence 的设备端模型，并可接入符合规范的云端或其他模型。其相关 Private Cloud Compute 路径允许符合条件的 App Store 小型企业计划开发者，在首次 App Store 下载量低于两百万时使用运行在 PCC 上的 Apple Foundation Models，并免除云端 API 费用。

**「影响」** 对开发者而言，如果这些资格限制属实，小型 App Store 开发者可在 Apple Intelligence 可用地区以无云端 API 费用测试 Private Cloud Compute 模型，但需要满足 Small Business Program、首次下载少于 200 万以及 TestFlight 或 ad hoc 分发等条件。

**「社区讨论」** 社区讨论主要关注缺少公开基准和实际集成方式：有用户希望看到该设备端模型与 Gemma 4 E4B、Qwen 3.5 4B 等相近规模模型对比，也有人提到 Apple CoreAI 仓库正在把开放权重模型适配到 Swift。另有评论把 App Attest、Firebase 以及终端本地模型辅助命令视为与 Apple Foundation Models 相关的实践方向。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://developer.apple.com/private-cloud-compute/">Private Cloud Compute - Apple Developer</a></li>
<li><a href="https://developer.apple.com/wwdc26/guides/apple-intelligence/">WWDC26 Apple Intelligence guide - Apple Developer</a></li>
<li><a href="https://techcrunch.com/2026/06/08/apple-bets-cheaper-ai-will-woo-small-developers/">Apple bets cheaper AI will woo small developers - TechCrunch</a></li>

</ul>
</details>

**标签**: `#Apple AI`, `#Foundation Models`, `#on-device inference`, `#Private Cloud Compute`, `#developer framework`

---

<a id="item-tech-news-5"></a>
### [Anthropic IPO 传获六倍超额认购](https://www.bloomberg.com/news/videos/2026-11-13/anthropic-ipo-said-to-be-six-times-oversubscribed-video) ⭐️ 8.0/10

据 Bloomberg 报道，Anthropic 的 IPO 已吸引约六倍于可售股份的订单，消息来自熟悉情况的人士，显示对这家 Claude 模型公司首次公开募股的需求强劲。公司及其联合创始人的文件显示，IPO 拟融资最多 644 亿美元，另有 260 亿美元私募；若最终完成，合计规模可能超过 SpaceX 的 IPO，并成为史上最大上市。该报道依赖匿名消息人士和 Bloomberg 视频，最终定价、分配和完成情况仍待确认。

rss · Bloomberg Technology · 11月13日 06:54

**「背景」** 在大型科技公司上市中，公开 IPO 与私募配售常同时出现：前者面向公开市场投资者发行股份，后者向特定机构出售股份。Anthropic 将两者合并计算，并与 SpaceX 的上市规模比较，因此超额认购之外，市场也在关注其合计融资是否可能成为新的纪录。

**「影响」** 若超额认购属实，Anthropic 的 IPO 可能成为迄今最大首次股票出售，使投资者面临更激烈的股份分配和更高的定价不确定性。

**标签**: `#AI IPO`, `#Anthropic`, `#AI commercialization`, `#capital markets`, `#Claude`

---

<a id="item-tech-news-6"></a>
### [Edge0-145B 宣称 145B 模型可本地运行](https://edge0.ai/blog/introducing-edge0-145b-frontier-ai-capabilities-on-your-own-computer) ⭐️ 7.0/10

Edge0 在博客中展示 Edge0-145B，宣称这是一个 145B 参数的本地 AI 模型，可在约 29GB 峰值内存下运行。其描述称采用共享专家矩阵：每 64 个专家共享两个大矩阵，每个专家仅保留少量差异参数，并展示 Blender 等工具使用示例。目前这些信息主要来自厂商博客，社区对其是否只是既有模型的量化或衍生版本仍存疑。

hackernews · sroussey · 11月12日 23:06 · [社区讨论](https://news.ycombinator.com/item?id=50475713)

**「背景」** 混合专家模型通常包含多个专家网络，而共享专家矩阵通过让多组专家共用大型权重矩阵来减少存储和搬运量；这解释了为何 145B 参数模型可能以较低峰值内存运行。社区评论同时质疑它是否只是已有模型的量化或衍生版本，因此背景信息需区分技术思路、厂商宣称和可验证结果。

**「影响」** 该公告把 145B 参数模型的本地运行门槛描述为约 29GB 峰值内存，可能影响高端笔记本用户；但部署前应核验量化、权重来源、许可证和基准。

**「社区讨论」** 评论者称共享矩阵方案让 145B 参数模型可在像 MacBook Pro 这样的机器上运行，并对 Blender 示例感兴趣。也有人怀疑它只是既有模型的量化或品牌化版本，并担心 agent 生成的 Blender 场景仍需大量人工清理。

**标签**: `#AI models`, `#local inference`, `#MoE`, `#tool use`, `#inference efficiency`

---

<a id="item-tech-news-7"></a>
### [PostgreSQL 类型混淆原语被指可致 RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 7.0/10

一篇关于 CVE-2026-6460 的技术文章称，一个存在约 22 年的 PostgreSQL 类型混淆原语可被发展为远程代码执行。HN 评论中概括的关键路径是：在表上创建 prepared statement，随后修改表，再执行本应随表变化而更新却未更新的语句，从而触发类型混淆。在原文未直接提供的情况下，这些细节主要来自标题与评论转述。

hackernews · ozirus · 11月12日 18:22 · [社区讨论](https://news.ycombinator.com/item?id=50471761)

**「背景」** CVE-2026-6460 被描述为 PostgreSQL 在 DDL 操作后出现的类型混淆：数据库对已跟踪的类型值更新不足，使有权限创建或修改数据库对象的用户可以通过 ALTER ... SET DATA TYPE 等命令触发错误。PostgreSQL 安全通告称，该问题可能导致以运行数据库的操作系统用户身份执行任意代码。

**「影响」** 若该路径成立，数据库管理员和共享或多租户 PostgreSQL 服务需要关注已认证数据库账户能否通过 prepared statement 与表变更交互获得更高服务端执行能力。在更多细节公开前，限制不受信任账户对表的修改权限并隔离共享实例是直接的缓解方向。

**「社区讨论」** 评论者对严重性存在分歧：logophobia 和 jmuguy 认为它更像需要已认证远程访问的权限提升，主要影响多租户数据库，而非广泛意义上的远程代码执行。ahartmetz 则认为利用路径精巧，核心是 prepared statement 未随表变更而正确更新。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>
<li><a href="https://access.redhat.com/security/cve/cve-2026-6460">CVE-2026-6460 - Red Hat Customer Portal</a></li>

</ul>
</details>

**标签**: `#PostgreSQL`, `#Security`, `#Database Internals`, `#Exploit Research`, `#Open Source`

---

<a id="item-tech-news-8"></a>
### [llm-gemini 0.37 与 Gemini 4 Hydrogen 定价](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

llm-gemini 0.37 发布，Simon Willison 同时介绍 Google 新推出的 Gemini 4 Hydrogen，称其为 Gemini 4 家族中最低成本的成员，并指出它已成为新的免费层模型、将支撑 Google Search 的 AI 功能。定价表显示，Hydrogen 为每百万输入 $1.50、缓存输入 $0.075、输出 $7.50；Carbon 和 Argon 在 2026 年 11 月 30 日前同为 $2/$0.10/$10，12 月 1 日起同为 $4/$0.20/$20。Willison 认为这套定价令人困惑，因为 Hydrogen 当前仅比 Carbon 和 Argon 便宜约 25%，到 12 月 1 日后才相当于约 75% 折扣；Google 则称 Argon 与 Carbon 同价，但响应更快、每轮 token 消耗更低。他的“鹈鹕骑车”测试显示 Hydrogen 输出明显更简单、成本和时间更低，但价格仍远高于 Claude Haiku 5.5 和 GPT-6 Luna 的 $0.10/$0.50。

rss · Simon Willison · 11月12日 22:55

**「背景」** llm-gemini 是用于在 LLM 命令行工具中调用 Google Gemini 模型的插件。Gemini 4 家族分为 Carbon、Argon、Hydrogen 三档，其中 Hydrogen 被描述为低成本档，也是新的免费档，并将为 Google 搜索中的 AI 功能提供支持。

**「影响」** 依赖 llm-gemini 或 Gemini 4 做推理的应用开发者应在 12 月 1 日前重新核算成本：Carbon 和 Argon 当前同价且将翻倍，而 Hydrogen 虽成为免费层和 Google 搜索 AI 功能模型，但示例输出质量明显较低，且价格仍约为 Claude Haiku 5.5 和 GPT-6 Luna 的 15 倍。

**标签**: `#Gemini`, `#LLM tooling`, `#AI pricing`, `#Inference cost`, `#Model release`

---

<a id="item-tech-news-9"></a>
### [OpenAI 发布 Codex Security CLI 与 TypeScript SDK](https://github.com/openai/codex-security) ⭐️ 7.0/10

OpenAI 发布了 Codex Security CLI 和 TypeScript SDK（npm 包 @openai/codex-security）；官方文档称其可用于发现、验证并修复代码安全漏洞。该工具支持扫描仓库、指定路径或 Git 变更，提供 Standard/Deep 扫描、补丁生成、修复验证、SECURITY.md 草案、第三方扫描器结果导入、SARIF/JSON/CSV 导出，以及 Linear、Jira、GitHub 跟踪。它要求 Node.js 22.13.0+（22.x）、24.x 或 26.x，以及 Python 3.10+（3.10 还需 tomli）；CI 需设置 OPENAI\_API\_KEY 或 CODEX\_API\_KEY，部分网络安全请求和受保护发现需要 Trusted Access for Cyber，Codex Security Cloud 为可选连接。

rss · GitHub Trending - Daily · 11月13日 09:14

**「背景」** Codex Security 是 OpenAI 在 Codex 代码工具链中推出的安全审查能力，既可在 Codex 会话中使用，也可通过 npm 包 @openai/codex-security 在终端、TypeScript 项目或 CI 中调用。其本地扫描需要 Node.js 和 Python 运行环境，并围绕仓库、指定路径或 Git 差异生成报告、验证候选漏洞和补丁。

**「落地注意事项」** 受影响开发者需要确认环境满足 Node.js 22.13.0+（22.x）、24.x 或 26.x 与 Python 3.10+，并为 CI 配置 OPENAI\_API\_KEY 或 CODEX\_API\_KEY；涉及受保护发现或特定网络安全请求时，还需 Trusted Access for Cyber 或 Daybreak 访问。该工具可直接嵌入扫描、验证、修复和工单跟踪流程，因此团队应优先控制扫描范围、密钥权限和导出格式，以避免误报、重复发现和敏感代码暴露。

**标签**: `#openai`, `#ai-coding-tools`, `#developer-security`, `#typescript`, `#github-trending`

---

<a id="item-tech-news-10"></a>
### [Meta 开源 Astryx Beta 设计系统](https://github.com/meta/astryx) ⭐️ 7.0/10

Meta 开源了 Astryx 设计系统，目前处于 Beta，基于 React 19+ 与 StyleX，提供 150+ 可访问组件、主题、模板和 CLI。项目称其 API、文档和 CLI 面向人与 AI 代理共同构建，并支持通过 className 覆盖样式而不强制采用特定样式库。该包要求 react 和 react-dom 作为 peer dependencies，图表等部分包仍只有 canary 版本。

rss · GitHub Trending - Daily · 11月13日 09:14

**「项目背景」** Astryx 是 Meta 将其内部长期使用的 React 设计系统对外开源的 beta 版本，项目称其在 Meta 内部支撑 13,000+ 应用。它基于 React 19+ 和 StyleX，强调可组合组件、主题定制和 CLI，并试图让人类开发者与 AI 编程助手使用同一套工具链。

**「影响」** 对于已有 React 19 应用的团队，Astryx 可能降低引入设计系统的构建配置成本，但 Beta 状态、React 19+ 依赖和未稳定发布的相关包要求先评估兼容性与生产可用性。

**标签**: `#open-source`, `#AI agents`, `#design systems`, `#React`, `#Meta`

---

<a id="item-tech-news-11"></a>
### [VulnCheck：Glasswing 发现多但修复少](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck 的 Patrick Garrity 分析 Anthropic Project Glasswing 自 4 月 7 日启动以来的漏洞发现，指出项目报告 37,966 项发现中仅 7,349 项公开，而公开项里只有 217 项被标记修复。该分析还称有 1,654 项被标记为重复、419 项被撤回，并质疑账本将真阳性率从 90.8% 升至 94.2%，却与低修复、高重复和撤回情况不匹配。Garrity 认为，这些结果把安全分诊负担转移给 Glasswing 原本声称要帮助的开源维护者。

rss · LWN.net · 11月12日 16:26

**「项目背景」** Anthropic 的 Project Glasswing 是一个由 AI 辅助发现软件漏洞的项目，自 4 月 7 日启动后持续公布大量漏洞 findings。VulnCheck 的 11 月分析基于该项目公开数据，评估这些漏洞是否被公开、修复、重复或撤回，因此需要理解其发布机制和开源维护者分诊负担。

**「影响」** 对开源维护者而言，大量重复、撤回和未公开发现意味着需要额外验证和分诊，可能延缓真正修复；该分析也显示，以原始发现数量衡量 Glasswing 成效会掩盖低公开率和低修复率。

**标签**: `#AI-security`, `#vulnerability-discovery`, `#open-source-maintainers`, `#Anthropic-Glasswing`, `#security-triage`

---

## 财经新闻

<a id="item-finance-news-1"></a>
### [礼来口服减重药在华获批](https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/) ⭐️ 8.0/10

中国国家药监局 11 月 12 日批准礼来每日一次、不受饮食饮水限制的口服 GLP-1 减重药奥氟格列隆钙片（商品名穆优达）上市，用于伴至少一种体重相关合并症的肥胖或超重成人，成为国内首个获批的口服 GLP-1 减重药。其 2 型糖尿病适应证仍在审评中，价格和上市时间未公布。

telegram · zaihuapd · 11月12日 10:09

**「背景」** GLP-1 是一类用于体重管理的药物，此前在华获批的同类减重药多为每周注射；奥氟格列隆成为首个获批的口服 GLP-1 减重药，使礼来在相对诺和诺德等注射剂竞争者时获得早期优势。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/">Eli Lilly becomes first drugmaker to have a GLP-1 weight-loss ...</a></li>
<li><a href="https://www.globaltimes.cn/page/202611/1374192.shtml">China approves first oral GLP-1 weight-loss drug - Global Times</a></li>

</ul>
</details>

**标签**: `#China healthcare regulation`, `#GLP-1 obesity drugs`, `#Eli Lilly`, `#China biotech competition`, `#pharmaceutical market`

---

<a id="item-finance-news-2"></a>
### [美联储 2027 年 10 月会议不投票决定利率](https://www.cnbc.com/2026/11/12/in-policy-switch-fed-says-its-october-2027-meeting-will-not-see-a-vote-on-interest-rates.html) ⭐️ 7.0/10

美联储利率决策机构 FOMC 将不会在 2027 年 10 月 26-27 日的会议上投票决定利率，而是把该次会议用于讨论货币政策战略；2027 年因此有七次投票会议，年末会议改到 11 月。

rss · CNBC Finance · 11月12日 19:05

**「背景」** 美联储通常每年举行八次政策会议并投票决定利率；Warsh 上月已预告将精简沟通，2027 年改为七次投票会议，并计划到 2028 年在八次年度会议中安排两次用于策略讨论。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-06/fed-s-new-fomc-schedule-turns-back-the-clock-for-strategy-sessions">Fed’s New FOMC Schedule Turns Back the Clock for ‘Strategy ...</a></li>
<li><a href="https://economictimes.indiatimes.com/markets/us-stocks/news/us-fed-sets-new-meeting-schedule-for-2027-as-foretold-by-chairman-kevin-warsh/articleshow/135781878.cms">US Fed sets new meeting schedule for 2027, as foretold by ...</a></li>

</ul>
</details>

**标签**: `#Federal Reserve`, `#monetary policy`, `#FOMC schedule`, `#market communication`, `#Kevin Warsh`

---

<a id="item-finance-news-3"></a>
### [AI 股票收窄跌幅，英伟达 CEO 离职影响待评估](https://news.google.com/rss/articles/CBMiuwFBVV95cUxOTDc4NU9Ycko1b01GTVdRT1lMVzJWaEhrLS1OSU92el9GTTRMSEhyTW5VbThOZEhoVGNCbHNBU19EZS1UUlNiTW0wVU41RUdBVkJpQlNRazBvaHJFQ2VnT2FJU183NE9ub1RKQU5wMFp6N1luX3lrMFZubFVIaHJ0TWhZRVkyUzhJVjBsaDRlMEpKNUFLeWtITVhLRVhqOERFMzh0azNJeVlqVzI0ZUowcnV4Z3VYMUdXcFY0?oc=5) ⭐️ 7.0/10

路透社报道，投资者评估英伟达首席执行官离职带来的影响，AI 相关股票随后收窄跌幅；该报道未披露具体涨跌幅或离职细节。

google\_news · Reuters · 11月12日 20:57

**「背景」** 据路透社报道，周四英伟达首席执行官 Jensen Huang 离职消息引发投资者评估其对人工智能相关股票的影响；标准普尔 500 指数和纳斯达克指数也走低，油价上涨进一步促使市场观望。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/global-ai-stocks-sink-nvidia-crisis-deepens-sector-selloff-2026-11-12/">AI stocks pare losses as investors assess fallout of Nvidia ...</a></li>
<li><a href="https://www.kitco.com/news/off-the-wire/2026-11-12/sp-500-nasdaq-fall-nvidia-ceos-exit-rattles-ai-stocks">S&amp;P 500, Nasdaq fall as Nvidia CEO&#x27;s exit rattles AI stocks</a></li>

</ul>
</details>

**标签**: `#Nvidia`, `#AI stocks`, `#CEO exit`, `#market reaction`, `#AI supply chain`

---

<a id="item-finance-news-4"></a>
### [三家 AI 公司遭诉要求停止前沿 AI 开发](https://news.google.com/rss/articles/CBMivwFBVV95cUxPWTR4ak5BdnRmV3hzYTZOcVhBYklWU01YRmtLak03b2hmeC1PMTd5blRQWUkxR2Q1ZXZWRC0xNkNxVDVoN2VOdTVlX1hFMXgwS1Y5TW1fUGt4NThQaEhRVFdna1YxUDhLTnBYUFJ6WTlFajlLM1BZTTRwNk5sWFMydkZtMlJNUnU4MWlDcUN6QmNtVHdUT1pLNXd6QXc4QVk0WmMtM1JxWU5XVC1PUGRIMVJNY2wzN1Z1d2N6WWJkbw?oc=5) ⭐️ 7.0/10

路透社报道，OpenAI、谷歌和 Anthropic 被起诉，原告寻求停止前沿 AI（最先进人工智能）开发；报道未披露法院、法律依据或胜诉可能性。

google\_news · Reuters · 11月12日 20:35

**「背景」** OpenAI、谷歌和 Anthropic 均为主要前沿 AI 模型开发商；该诉讼旨在暂停这类能力最强的新一代模型开发，但报道未披露原告、法院、法律依据或案件进展。

**标签**: `#AI regulation`, `#frontier AI litigation`, `#AI industry economics`, `#OpenAI`, `#Anthropic`

---

<a id="item-finance-news-5"></a>
### [印度 Clean Max 拟投 53 亿美元清洁能源支持 AI 算力设施](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

印度清洁能源公司 Clean Max 计划投资 53 亿美元建设清洁能源设施，为人工智能计算中心供电。该金额为计划投资，尚未说明是否已完成融资或落地执行。

google\_news · Reuters · 11月12日 13:39

**「背景」** 人工智能计算设施通常指承载 AI 运算的数据中心，耗电量高，需要长期、稳定的电力供应；因此清洁能源企业常通过新建或扩建发电项目为其供电。

**标签**: `#AI infrastructure`, `#clean energy`, `#capital expenditure`, `#India`, `#data centers`

---

<a id="item-finance-news-6"></a>
### [SpaceX 拟投逾 740 亿美元建得州与亚利桑那州 AI 园区](https://news.google.com/rss/articles/CBMixAFBVV95cUxQdlQwLUxxTENmenRpSFFXVlNUeVkzeURtNWxCZ1RuVEQwdENKV0g3MndreVZsZFYwVGtpT3Q3SDJZU0pHTGI1WFFYWERreFJmbzVjaUtOR2NjUURRMTVHNVlKdGE0VkdRVzRvekpIcHdmRGdOV2kwRXVmbWl1blRIV1VKSjQ4c19FSVFTUWZNM2ptQ0ZaMW96a2UyTFphWjNsSnc3ZmJZdWhHNWpiS19hTDhYSk9vNkpkeng1N3prZ1Y3b1lI?oc=5) ⭐️ 7.0/10

路透社报道，SpaceX 计划在得克萨斯州和亚利桑那州建设 AI 园区，拟投入超过 740 亿美元。该金额属于公司披露的投资计划，报道未说明是否已最终承诺、资金来源或具体时间表。

google\_news · Reuters · 11月12日 20:23

**「背景」** SpaceX 是马斯克旗下火箭与人工智能公司，其计划中的得州和亚利桑那州园区属于超算设施，即用于大规模 AI 计算的算力中心。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/media-telecom/spacex-invest-over-74-billion-supercompute-facilities-texas-arizona-2026-11-12/">SpaceX plans over $74 billion investment in Texas, Arizona AI ...</a></li>
<li><a href="https://finance.yahoo.com/technology/ai/articles/spacex-build-74b-ai-supercomputing-222425804.html?fr=sycsrp_catchall">SpaceX to build $74B AI supercomputing facilities in Texas ...</a></li>

</ul>
</details>

**标签**: `#SpaceX`, `#AI infrastructure`, `#capital expenditure`, `#data centers`, `#Reuters`

---

<a id="item-finance-news-7"></a>
### [思科上调全年营收预期](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

路透社报道，思科因人工智能网络设备需求强劲上调全年营收预期，但未披露具体数字。

google\_news · Reuters · 11月12日 23:18

**「背景」** 此前在 2026 年 8 月，Cisco 已因 AI 网络设备需求强劲而给出高于分析师预估的 2027 财年收入预测。最新公告则是在第一财季业绩好于预估后上调本财年收入指引；指引是公司管理层对未来的收入预测。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/media-telecom/cisco-raises-annual-revenue-forecast-strong-ai-networking-demand-2026-11-12/">Cisco lifts annual revenue forecast on strong AI networking ...</a></li>
<li><a href="https://www.reuters.com/technology/cisco-forecasts-upbeat-annual-revenue-2026-08-12/">Cisco forecasts annual revenue above estimates on sustained ...</a></li>

</ul>
</details>

**标签**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#technology earnings`, `#Reuters`

---

<a id="item-finance-news-8"></a>
### [应用材料公司季度营收指引高于预期](https://news.google.com/rss/articles/CBMivgFBVV95cUxNeVJYSC1hal9odmptblkwc25YV0pZQXBaaTd0SGFyMW5tT1ZtNzZaTlN0OGFnY2I0dnI3ZmZRaXpwUThvZW5kay1tMElieklOVVZLTDFBTmtQbkpiSWpUZzlLNnZPRmlJSkxoWVZhZGlveTdzNjVsN0ZtZUVMMnk2REQtYmRHRzQwMDhNMVBYQXVQbjBpcHNNYnFWWldTbUItYV9pT1hMYkwwZi1jS0pvZXp4eHJhbHE4OEp6RW13?oc=5) ⭐️ 7.0/10

路透社报道，应用材料公司对季度营收给出的指引高于市场普遍预期，原因是人工智能芯片需求强劲。

google\_news · Reuters · 11月12日 23:44

**「背景」** Applied Materials 刚公布截至 2026 年 10 月 25 日的第四财季和全年业绩，其最新季度收入指引押注 AI 芯片需求继续带动相关设备支出。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/applied-materials-forecasts-quarterly-revenue-above-estimates-strong-ai-chip-2026-11-12/">Applied Materials forecasts quarterly revenue above estimates ...</a></li>
<li><a href="https://www.appliedmaterials.com/us/en/newsroom/press-releases/111226-applied-materials-announces-fourth-qtr-fiscal-year-end-2026-results.html">Applied Materials Announces Fourth Quarter and Fiscal Year ...</a></li>

</ul>
</details>

**标签**: `#Applied Materials`, `#AI chips`, `#semiconductor equipment`, `#earnings guidance`, `#Reuters`

---

<a id="item-finance-news-9"></a>
### [美国 10 月预算赤字创纪录](https://news.google.com/rss/articles/CBMiugFBVV95cUxPSDdFRmlLcWNxcWNRVHRGN05hM2dMcmpEeW1IY1gyVkM0R2NPQVpfWU1ObHZMX08xZHFFYXhGbllpTW9abFR2SGxoNUprSFdxYTR1OXF1N3d2RGRNNGRzelRRdzhSOF8tMmM2U2I3clNQR0trbDZrLWN4QlVyNXlKOTJsdXp2NU5aWUxHR3AyQndrNFc5dFhBQS1MWHdZZHQ5c0thakE1b1Y1OTdhcFNHb1U1cmlZbjNyQWc?oc=5) ⭐️ 7.0/10

路透社报道，美国 2027 财年首个月——10 月——的联邦预算赤字为 4040 亿美元，创下有记录以来同期最高水平。

google\_news · Reuters · 11月12日 20:18

**「背景」** 美国联邦财政年度从每年 10 月开始，赤字指政府支出超过收入的部分；财政部数据显示，2027 财年首月赤字达 4040 亿美元，创同月纪录，较上年同期扩大约 1200 亿美元或 42%。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/us-starts-2027-fiscal-year-with-record-october-budget-deficit-404-billion-2026-11-12/">US starts 2027 fiscal year with record October budget deficit ...</a></li>
<li><a href="https://finchannel.com/u-s-budget-deficit-reaches-404-billion-as-fiscal-2027-begins/141433/americas/america/2026/11/">U.S. budget deficit reaches $404 billion as fiscal 2027 ...</a></li>

</ul>
</details>

**标签**: `#US fiscal policy`, `#budget deficit`, `#macroeconomic data`, `#global markets`, `#Reuters`

---

<a id="item-finance-news-10"></a>
### [美国 10 月成屋销售创 16 年多新低](https://news.google.com/rss/articles/CBMipgFBVV95cUxQTG4zNkNsSG5RNkJsdlhCZ0prLXlLTTRDZFdmLWEta3QwVGd3YXN3dnZpd0h2R3duS1N5WEx4eE85THlmT0VYZ0tlQ0ZJUlB4bHJPNnpfQnZTM0dqM1Y4eEJYNlJPX0xhNWxxYXMxMW1ncjZOclhSMmpINlVBOTJtYVc5bXJGRVhjU1lEb2ZZWkFOaXRXZDl0b3dETFFLVlA3ZUVLalpn?oc=5) ⭐️ 7.0/10

路透报道，美国 10 月成屋销售降至 16 年多来的最低水平，但所给内容未提供具体销售量或价格数据。

google\_news · Reuters · 11月12日 15:03

**「背景」** “现有住房销售年率”是把当月二手房成交量经季节调整后折算成全年速度；10 月降至 375 万套，为 2010 年 8 月以来最低。按揭利率上升、房价仍偏高，使潜在买家观望。

**「市场影响」** 高房贷利率和通胀上升正在抑制购房需求，可能继续拖累住宅销售链条，并让依赖房产交易的购房者和相关行业承压。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/us-existing-home-sales-slump-more-than-16-year-low-october-2026-11-12/">Reuters | US existing home sales slump to more than 16-year ...</a></li>
<li><a href="https://www.nar.realtor/newsroom/existing-home-sales-decreased-5-5-percent-october-nar-report">Existing-Home Sales Decreased 5.5% in October, According to ...</a></li>
<li><a href="https://www.realtor.com/news/trends/existing-home-sales-data-nar-october-2026/">Home Sales Plunge to 16-Year Low as High Mortgage Rates ...</a></li>
<li><a href="https://www.realtor.com/news/trends/existing-home-sales-data-nar-october-2026/">Home Sales Plunge to 16-Year Low as High Mortgage Rates ...</a></li>
<li><a href="https://www.wsj.com/economy/housing/home-sales-in-october-plummet-to-16-year-low-16adebc0">Home Sales in October Plummet to 16-Year Low - WSJ</a></li>
<li><a href="https://www.theguardian.com/business/2026/nov/12/home-sales-october-low">Home sales hit 16-year low in October amid record-high ...</a></li>

</ul>
</details>

**标签**: `#US housing`, `#existing home sales`, `#macroeconomic data`, `#interest rates`, `#consumer economy`

---