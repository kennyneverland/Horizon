---
layout: default
title: "Horizon Summary: 2026-11-13 (ZH)"
date: 2026-11-13
lang: zh
---

> 从 121 条内容中筛选出 20 条重要资讯。

---

**科技新闻**
1. [Rust 1.100 发布：稳定 never 类型与 Cargo 依赖卫生](#item-tech-news-1) ⭐️ 8.0/10
2. [Anthropic IPO 据报超额认购六倍，拟募资或创纪录](#item-tech-news-2) ⭐️ 8.0/10
3. [彭博称 Nvidia 罢免 CEO 黄仁勋，硅谷震动](#item-tech-news-3) ⭐️ 8.0/10
4. [Google Antigravity 讨论 Gemini 4 Hydrogen 与编排器](#item-tech-news-4) ⭐️ 7.0/10
5. [Apple Foundation Models 框架支持本地与 PCC 推理](#item-tech-news-5) ⭐️ 7.0/10
6. [黄仁勋辞职传闻涉中国出口管制，证据未证实](#item-tech-news-6) ⭐️ 7.0/10
7. [PostgreSQL 类型混淆被称转化为 RCE](#item-tech-news-7) ⭐️ 7.0/10
8. [Edge0-145B 宣称 29GB 内存本地运行](#item-tech-news-8) ⭐️ 7.0/10
9. [llm-gemini 0.37 与 Gemini 4 Hydrogen 定价](#item-tech-news-9) ⭐️ 7.0/10
10. [OpenAI 发布 Codex Security CLI 与 TypeScript SDK](#item-tech-news-10) ⭐️ 7.0/10
11. [addyosmani/agent-skills 提供 AI 编码代理技能](#item-tech-news-11) ⭐️ 7.0/10
12. [Glasswing 分析：发现多但修复少，维护者负担加重](#item-tech-news-12) ⭐️ 7.0/10

**财经新闻**
1. [英伟达宣布黄仁勋辞任 CEO，克雷斯任临时 CEO](#item-finance-news-1) ⭐️ 9.0/10
2. [AI 股收窄跌幅，投资者评估英伟达 CEO 离任影响](#item-finance-news-2) ⭐️ 8.0/10
3. [SpaceX 拟投逾 740 亿美元建得州与亚利桑那 AI 园区](#item-finance-news-3) ⭐️ 8.0/10
4. [黄仁勋辞职与作证或加剧中美科技紧张](#item-finance-news-4) ⭐️ 7.0/10
5. [特朗普涉伊朗言论推高油价](#item-finance-news-5) ⭐️ 7.0/10
6. [印度 Clean Max 拟投 53 亿美元清洁能源供 AI 算力设施](#item-finance-news-6) ⭐️ 7.0/10
7. [思科上调年度营收预期](#item-finance-news-7) ⭐️ 7.0/10
8. [美国 2027 财年 10 月预算赤字创纪录](#item-finance-news-8) ⭐️ 7.0/10

---

## 科技新闻

<a id="item-tech-news-1"></a>
### [Rust 1.100 发布：稳定 never 类型与 Cargo 依赖卫生](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 已发布，官方博客列出的主要变化包括 never 类型稳定、核心 Allocator API 部分落地，以及 Cargo 报告未使用依赖。这些变化属于语言与工具链层面的正式更新，而非仅宣布计划。评论还补充提到依赖冷却期配置、cargo install 默认使用锁文件等行为，但这些细节需以官方发布说明核实。

hackernews · mbStavola · 11月12日 18:39 · [社区讨论](https://news.ycombinator.com/item?id=50472038)

**「背景」** Rust 的版本发布长期采用渐进稳定策略：never type 和自定义分配器等底层特性此前处于实验或不完整状态，1.100 将其纳入稳定语言与标准库能力。Cargo 的未使用依赖警告和依赖冷却配置则是在既有依赖解析机制上增加构建卫生约束，用于更早发现清单冗余并控制新发布依赖被自动采用。

**「影响」** 对 Rust 项目维护者而言，未使用依赖报告可在 Cargo.toml 中直接暴露多余依赖，便于清理依赖树；不过既有项目可能因此新增警告，若 CI 将警告视为错误，开发者需要评估是否移除依赖或调整 lint 配置。

**「社区讨论」** 评论将 never 类型、自定义分配器、依赖冷却期和 cargo install 锁文件行为视为亮点，并指出 bool::toggle\(\)、Box::map\(\) 等稳定 API 未在博客中提及。同时有开发者抱怨编译耗时和大量临时文件，形成对发布内容与实际开发体验的不同关注点。

**标签**: `#Rust`, `#programming languages`, `#open source`, `#developer tooling`, `#software engineering`

---

<a id="item-tech-news-2"></a>
### [Anthropic IPO 据报超额认购六倍，拟募资或创纪录](https://www.bloomberg.com/news/videos/2026-11-13/anthropic-ipo-said-to-be-six-times-oversubscribed-video) ⭐️ 8.0/10

据彭博援引知情人士称，Anthropic 的 IPO 已收到约六倍于可发售股份的认购订单，显示投资者对这家 Claude AI 模型公司的上市兴趣升温。公司文件显示，Anthropic 及其联合创始人拟在 IPO 中最多募资 644 亿美元，并在私募配售中再募集 260 亿美元。两项融资若按文件完成，将超过 SpaceX 的 IPO，成为史上最大规模上市融资。

rss · Bloomberg Technology · 11月13日 06:54

**「融资机制与规模背景」** 超额认购指投资者申购数量超过可发行股份，通常反映市场对该次上市的需求较强。私募配售则是向特定投资者出售股份，与公开发行共同构成 Anthropic 此次融资的总规模。由于 Anthropic 是 Claude 模型的开发公司，其 IPO 规模也被视为观察大型 AI 公司资本化进程的重要指标。

**「影响」** 对投资者而言，这意味着一个可能超过 SpaceX IPO 规模的新股认购机会；对 Anthropic 而言，若 IPO 与私募配售均完成，公司及其联合创始人最多可新增 904 亿美元资金。

**标签**: `#AI commercialization`, `#IPO`, `#Anthropic`, `#capital markets`, `#AI industry`

---

<a id="item-tech-news-3"></a>
### [彭博称 Nvidia 罢免 CEO 黄仁勋，硅谷震动](https://www.bloomberg.com/news/articles/2026-11-12/-dark-day-silicon-valley-mourns-nvidia-s-decision-to-oust-ceo) ⭐️ 8.0/10

彭博报道，两名知情人士称 Nvidia 董事会已罢免 CEO 黄仁勋。报道称，罢免与两段婚外情有关，其中一名女性被疑为中国从事间谍活动，另一段涉及一名员工。该决定在硅谷引发强烈反应，风险投资人和创始人批评董事会并担忧更广泛的行业影响。

rss · Bloomberg Technology · 11月12日 19:07

**「背景」** 据彭博报道，英伟达董事会在黄仁勋被指涉及两段私生活风波后将其罢免，其中一段关系涉及一名被怀疑为中国从事间谍活动的女性。黄仁勋此前一直担任英伟达 CEO，因此他的去留被视为理解该公司治理和 AI 业务稳定性的关键背景。

**「影响」** 对依赖 Nvidia 芯片的 AI 开发者、云厂商和企业客户而言，这一尚未由 Nvidia 官方确认的高管变动报道会立即引发对算力供应连续性、市场信心和安全合规审查的关注。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/-dark-day-silicon-valley-mourns-nvidia-s-decision-to-oust-ceo">‘Dark Day’: Silicon Valley Mourns Nvidia’s Decision to Oust ...</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/jensen-huang-nvidia-affair-ceo.html">Jensen Huang: Analysts weigh in on Nvidia&#x27;s future - CNBC</a></li>

</ul>
</details>

**标签**: `#Nvidia`, `#AI hardware`, `#China security`, `#corporate governance`, `#semiconductors`

---

<a id="item-tech-news-4"></a>
### [Google Antigravity 讨论 Gemini 4 Hydrogen 与编排器](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) ⭐️ 7.0/10

Google 的 Antigravity 博客条目围绕 Gemini 4 Hydrogen 和 orchestrator 展开，面向使用 Google AI 编码代理的开发者。现有材料没有给出正文，因此无法判断它是已发布能力、预告还是博客说明，也没有版本、可用范围、兼容条件或实测性能。社区评论提到 Hydrogen 可能属于新的 Flash 类模型、Argon/Carbon 速度较慢、1 月 1 日起 Google 模型价格可能翻倍，但这些均为评论观点，需要以官方页面核实。

hackernews · jonbaer · 11月12日 18:52 · [社区讨论](https://news.ycombinator.com/item?id=50472260)

**「背景」** Google Antigravity 是面向编码与代理工作流的 Gemini 使用场景；公开材料称，Gemini 4 Hydrogen 被定位为更快的执行模型，Orchestrator 则把 Carbon 的推理能力与 Hydrogen 的执行能力结合。这些能力被描述为面向 Google AI Pro/Ultra 付费订阅，其中 Orchestrator 供 Ultra 使用，企业则可通过 API、模型选择器和 Google Sheets 中的 Gemini 使用。

**「影响」** 对开发者而言，采用前需要确认 Gemini 4 Hydrogen 的模型层级、Antigravity 兼容性和 orchestrator 的缓存/token 计费；若评论提到的 1 月 1 日 Google 模型价格翻倍属实，编码代理的成本评估也需要重新计算。

**「社区讨论」** 社区评论主要围绕命名、速度和成本：有人称 Argon/Carbon 太慢并转向 3.8 Flash，也有人提到 1 月 1 日起 Google 模型价格可能翻倍。另一派讨论把 orchestrator 类比为 Anthropic advisor 模式和 GitHub HydraFusion 多模型流水线，但质疑缓存与 token 计费如何工作。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/">Gemini 4 Hydrogen and Orchestrator | Google Antigravity Blog</a></li>
<li><a href="https://thehype.news/gemini-4-hydrogen/">Gemini 4 Hydrogen : Benchmarks, Price and Availability</a></li>
<li><a href="https://interestingengineering.com/ai-robotics/google-gemini-4-hydrogen-coding-benchmark">Google launches Gemini 4 Hydrogen for faster coding and agentic...</a></li>

</ul>
</details>

**标签**: `#Gemini`, `#AI coding agents`, `#model orchestration`, `#inference pricing`, `#Google Antigravity`

---

<a id="item-tech-news-5"></a>
### [Apple Foundation Models 框架支持本地与 PCC 推理](https://developer.apple.com/foundation-models-framework/) ⭐️ 7.0/10

Apple 的 Foundation Models 框架面向开发者提供设备端和 Private Cloud Compute 上的 AI 推理支持。评论引用 Apple 文档称，参与 App Store Small Business Program 且首次下载量少于 200 万的开发者，可在 Apple Intelligence 可用地区将 Private Cloud Compute 上的 Apple Foundation Models 用于 App Store 分发应用，并通过 TestFlight 或 ad hoc 测试，无需支付云端 API 费用。社区还提到该框架可在 Apple Silicon 本地使用，例如在 8GB M1 上通过终端辅助纠错和建议命令。

hackernews · kermatt · 11月12日 21:13 · [社区讨论](https://news.ycombinator.com/item?id=50474361)

**「背景」** Apple Foundation Models framework 是面向开发者的 AI 接口，允许应用调用 Apple 提供的基础模型，并涉及设备端推理与 Private Cloud Compute 服务端模型。2026 年 WWDC26 指南和相关报道指出，参与 App Store Small Business Program 且首次 App Store 下载少于 200 万的开发者，可无云 API 费用使用 Private Cloud Compute 上的下一代 Apple Foundation Models，并获得增强 AI 能力与更长上下文窗口。

**「影响」** 对开发者而言，最直接的影响是可在满足 Small Business Program、下载量门槛、Apple Intelligence 可用地区以及 App Store 或 TestFlight/ad hoc 分发等条件时，免费访问 Private Cloud Compute 推理；不符合条件的开发者仍需要评估其他云端或本地推理成本。本地 Apple Silicon 使用则受设备内存和模型适配限制，评论中的 8GB M1 经验只能说明轻量终端场景可行，不能推广为所有模型或任务都能稳定运行。

**「社区讨论」** 讨论中最有用的观点是引用 Apple 文档，把免费 PCC 访问限定在 Small Business Program 且首次下载量少于 200 万的开发者，并强调需要 Apple Intelligence 可用和 App Store/TestFlight/ad hoc 分发。另有用户认为 Apple CoreAI 仓库把开源权重模型适配到 Swift 原生运行，以及 8GB M1 终端纠错体验“超出预期”，但这些属于个人观察或社区看法，不是官方性能承诺。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://developer.apple.com/private-cloud-compute/">Private Cloud Compute - Apple Developer</a></li>
<li><a href="https://developer.apple.com/wwdc26/guides/apple-intelligence/">WWDC26 Apple Intelligence guide - Apple Developer</a></li>
<li><a href="https://techcrunch.com/2026/06/08/apple-bets-cheaper-ai-will-woo-small-developers/">Apple bets cheaper AI will woo small developers - TechCrunch</a></li>

</ul>
</details>

**标签**: `#Apple Foundation Models`, `#Private Cloud Compute`, `#on-device inference`, `#AI developer tools`, `#inference cost`

---

<a id="item-tech-news-6"></a>
### [黄仁勋辞职传闻涉中国出口管制，证据未证实](https://apnews.com/article/nvidia-megaspeed-china-singapore-huang-5403f152a601cf82ce939f1d24fffa0f) ⭐️ 7.0/10

Hacker News 讨论指向多家媒体报道称 NVIDIA CEO 黄仁勋辞职，并涉及中国、新加坡及出口管制相关指控。当前来源内容仅显示链接标题和讨论评论，未提供可独立核实的 NVIDIA 官方声明、辞职日期、原因或调查结论。因此该事件仍应视为未经完全证实的领导层变动传闻。

hackernews · lldb · 11月12日 13:52 · [社区讨论](https://news.ycombinator.com/item?id=50467087)

**「背景」** 黄仁勋自 1993 年英伟达创立以来长期担任首席执行官，被视为推动 AI 算力生态发展的核心人物。此次辞职源于多家媒体报道其婚外情，其中一名对象被美国情报机构指认为疑似中国间谍；英伟达将由首席财务官 Colette Kress 临时接任，直至选出正式继任者。

**「影响」** 如果 NVIDIA 官方确认黄仁勋辞职，依赖 NVIDIA 平台的企业和开发者需要关注继任安排、合规调查和供应连续性，但不应基于未证实传闻立即调整采购或技术路线。

**「社区讨论」** 部分评论者认为讨论焦点应是 NVIDIA 是否规避出口管制以及为何此时曝光，而非私人关系；另一些评论者强调，即使指控未经证实，黄仁勋作为 NVIDIA 稳定象征的感知风险也足以影响 AI 经济信心。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.techpowerup.com/354732/nvidia-co-founder-and-ceo-jensen-huang-officially-resigns?cp=12">NVIDIA Co-Founder and CEO Jensen Huang Officially Resigns</a></li>
<li><a href="https://www.theguardian.com/technology/2026/nov/12/nvidia-ceo-jensen-huang-resigns">Jensen Huang resigns as Nvidia CEO after alleged... | The Guardian</a></li>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live Updates</a></li>

</ul>
</details>

**标签**: `#NVIDIA`, `#Jensen Huang`, `#AI hardware`, `#export controls`, `#China AI supply chain`

---

<a id="item-tech-news-7"></a>
### [PostgreSQL 类型混淆被称转化为 RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 7.0/10

对 PostgreSQL 管理员和安全研究人员而言，Hacker News 上的一篇漏洞利用文章声称，一个存在 22 年的类型混淆原语可被转化为远程代码执行（RCE），文章链接标注 CVE-2026-6460。由于未提供原文内容，该说法仍需按作者披露的利用条件和验证状态理解。社区评论将技术路径描述为在表上创建 prepared statement、随后修改表并执行未同步更新的语句，从而触发类型混淆。

hackernews · ozirus · 11月12日 18:22 · [社区讨论](https://news.ycombinator.com/item?id=50471761)

**「背景」** 这一讨论围绕 CVE-2026-6460：PostgreSQL 在 ALTER ... SET DATA TYPE 等路径下存在类型混淆，官方描述称对象创建者可借此以数据库进程的操作系统用户身份执行任意代码。作者称该修复属于包含 52 个 CVE 的发布，是类型混淆问题的伞形修复，并引入复合属性版本化。

**「影响」** 如果攻击确实需要已认证数据库账户，它更接近权限提升而非未认证远程攻击；管理员应重点评估多租户 PostgreSQL 环境中的账户权限、prepared statement 缓存行为和表结构变更暴露面。

**「社区讨论」** 社区讨论中最有价值的分歧是，一些评论者认为这更像需要数据库访问权限的权限提升，而非真正 RCE，并主要影响多租户数据库。另一条评论则称赞利用思路，并将其概括为 prepared statement 在表变更后未更新而触发类型混淆。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL : CVE - 2026 - 6460 : PostgreSQL type confusion after...</a></li>
<li><a href="https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/">Part 3/6 | How I Ended Up Turning a 22-Year-Old PostgreSQL ...</a></li>
<li><a href="https://security-tracker.debian.org/tracker/CVE-2026-6460">CVE - 2026 - 6460</a></li>

</ul>
</details>

**标签**: `#PostgreSQL`, `#database security`, `#CVE`, `#open source`, `#software engineering`

---

<a id="item-tech-news-8"></a>
### [Edge0-145B 宣称 29GB 内存本地运行](https://edge0.ai/blog/introducing-edge0-145b-frontier-ai-capabilities-on-your-own-computer) ⭐️ 7.0/10

Edge0 在博客中宣称推出 Edge0-145B，一个 145B 参数模型，称可在兼容个人电脑（例如 MacBook Pro）上运行，峰值内存约 29GB。其介绍称通过共享矩阵在保持专家数量不变的情况下减少权重存储与移动：每组 64 个专家共享两个大矩阵，每个专家保留少量差异参数。这些能力目前主要来自 Edge0 的宣称，社区还质疑其是否可能是 Qwen 3.8 Flash Next 等模型的量化或品牌化变体。

hackernews · sroussey · 11月12日 23:06 · [社区讨论](https://news.ycombinator.com/item?id=50475713)

**「背景」** Edge0-145B 是 Edge0 开源的 145B 参数端侧模型，与 Edge0-120B、统一推理框架和部署工具一同发布，厂商称其可在兼容个人电脑上运行编码、推理和 agent 能力。大模型本地运行通常受权重存储、内存/显存占用和推理速度限制，因此 Edge0 报告约 29GB 峰值内存、80+ tokens/s 生成和 1100+ tokens/s prompt 处理，是判断其是否真正适合个人设备的关键指标。

**「影响」** Edge0-145B 声称以约 29GB 峰值内存运行 145B 参数模型，因此本地推理开发者在采用前需要验证目标笔记本是否满足该内存条件，并确认它是否为 Qwen 3.8 Flash Next 等稀疏激活或量化变体的重新品牌版本。若用于工具调用场景，应先在本地硬件上测试精度、稳定性和内存占用，而不是直接假设具备同等前沿能力。

**「社区讨论」** 评论中，有人认可 145B 参数与约 29GB 峰值内存的组合，也赞赏 Blender 工具使用示例；但也有人怀疑它只是 Qwen 3.8 Flash Next 或类似模型的量化品牌版。另有讨论指出，所谓个人电脑可能并不普通，且智能体生成的设计仍可能需要人工清理。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://edge0.ai/blog/introducing-edge0-145b-frontier-ai-capabilities-on-your-own-computer">Edge0-145B: Open-Source On-Device AI with 145B Parameters</a></li>
<li><a href="https://dev.to/shakeelahmed/a-145b-open-model-that-runs-on-your-laptop-edge0-145b-explained-31a2">A 145B Open Model That Runs on Your Laptop: Edge0-145B ...</a></li>
<li><a href="https://daily.dev/posts/edge0-145b-frontier-ai-capabilities-on-your-own-computer-lb0gy6vjq">Edge0-145B: Frontier AI Capabilities on Your Own Computer</a></li>
<li><a href="https://www.mindstudio.ai/blog/qwen-3-8-flash-next-strata-1000-build">Qwen 3 . 8 Flash Next on a $1,000 Dual-3060 PC: Quantization Tested</a></li>
<li><a href="https://ollama.com/library/qwen3.8-flash-next">qwen 3 . 8 - flash - next</a></li>

</ul>
</details>

**标签**: `#local-inference`, `#model-efficiency`, `#inference-cost`, `#AI-agents`, `#model-release`

---

<a id="item-tech-news-9"></a>
### [llm-gemini 0.37 与 Gemini 4 Hydrogen 定价](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

llm-gemini 0.37 发布，Simon Willison 同时指出 Google 已推出 Gemini 4 系列中最低成本的 Hydrogen 模型。Hydrogen 定价为每百万输入 token $1.50、缓存输入 $0.075、输出 $7.50；Carbon 和 Argon 在 2026 年 11 月 30 日前同为 $2.00/$0.10/$10.00，但 12 月 1 日起翻倍为 $4.00/$0.20/$20.00。Google 称 Argon 比 Carbon 响应更快、每轮 token 更少，而 Hydrogen 将作为新的免费层模型并驱动 Google Search 的 AI 功能。

rss · Simon Willison · 11月12日 22:55

**「背景」** Gemini 4 是 Google 的模型家族，包含 Carbon、Argon 和 Hydrogen；Hydrogen 被定位为低成本成员。Carbon 与 Argon 在 2026 年 11 月 30 日前定价相同，并计划从 12 月 1 日起价格翻倍，这使 Hydrogen 的相对低价要到 12 月才更明显。

**「影响」** 对开发者而言，12 月 1 日起 Carbon 和 Argon 价格翻倍，需要重新评估按 token 计费的应用成本；对普通用户而言，Hydrogen 成为免费层并驱动 Google Search AI 功能，意味着更低成本访问，但 Simon 的生成测试显示其输出明显简化，可能不适合需要高质量复杂输出的任务。

**标签**: `#Gemini 4`, `#llm-gemini`, `#model pricing`, `#inference cost`, `#AI tooling`

---

<a id="item-tech-news-10"></a>
### [OpenAI 发布 Codex Security CLI 与 TypeScript SDK](https://github.com/openai/codex-security) ⭐️ 7.0/10

OpenAI 提供 Codex Security CLI 和 TypeScript SDK，npm 包名为 @openai/codex-security，用于帮助开发者查找、验证和修复代码中的安全漏洞。该工具支持扫描整个仓库、指定路径或 Git 变更，并可生成补丁、验证已有修复、导出 SARIF/JSON/CSV，以及接入 CI、容器和 GitHub Action。CLI 运行环境要求 Node.js 22.13.0+（22.x）、24.x 或 26.x，以及 Python 3.10+；Python 3.10 还需 tomli。部分网络安全请求和受保护发现需要 Trusted Access for Cyber，Codex Security Cloud 为可选连接。

rss · GitHub Trending - Daily · 11月13日 08:20

**「背景」** Codex Security 是 Codex 会话中的安全插件/工作流，并通过 CLI、TypeScript SDK 和 GitHub Action 扩展到终端与自动化。其 GitHub Releases 提到 0.9.0 源包因 macOS 签名中断未发布到 npm，并建议已签名 CLI/SDK 使用 0.9.1，而 npm 页面当前显示最新版本为 0.1.29，说明不同发布渠道的版本信息需以具体安装页面为准。

**「影响」** 团队可把 Codex Security 作为仓库级或 CI 安全扫描入口，并将结果接入 Linear、Jira、GitHub 或导出 SARIF/JSON/CSV；落地前需确认 Node.js 版本、Python 依赖、登录或 API 密钥配置，以及部分请求所需的 Trusted Access for Cyber 限制。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://github.com/openai/codex-security/releases">Releases · openai/codex-security · GitHub</a></li>
<li><a href="https://www.npmjs.com/package/@openai/codex-security">@openai/codex-security - npm</a></li>

</ul>
</details>

**标签**: `#openai`, `#codex`, `#security-tooling`, `#developer-tools`, `#ai-code-generation`

---

<a id="item-tech-news-11"></a>
### [addyosmani/agent-skills 提供 AI 编码代理技能](https://github.com/addyosmani/agent-skills) ⭐️ 7.0/10

GitHub Trending 于 2026-11-13 收录 addyosmani/agent-skills，仓库 README 描述其为 AI 编码代理提供 25 个工程技能和 9 个开发生命周期命令。可用命令包括 /spec、/plan、/build、/test、/constraints、/review、/webperf、/code-simplify 和 /ship，并通过 npx skills add、Claude Code 插件市场或各代理本地目录安装。README 说明 /build auto 会在批准计划后自主实现任务，但仍逐任务测试和提交；单独安装一个技能时只复制 skills/&lt;name&gt;/，不会获得 references/ 共享清单，且同名内置命令在 Claude Code 中需改用 /agent-skills:review。

rss · GitHub Trending - Daily · 11月13日 08:20

**「背景」** 该项目依托“技能包”这一做法，把资深工程师的开发流程、质量门禁和审查清单打包成 AI 编码代理可安装的命令与规则，而不是直接扩展模型能力。它通过 Vercel 的 skills CLI 以及 Claude Code、Cursor 等代理的原生集成分发，使这些工作流能在不同编码代理中复用。

**「影响」** 对采用 AI 编码代理的开发者而言，该仓库把规格、计划、测试、审查、Web 性能和发布门禁等资深工程流程封装成可跨 70+ 代理安装的技能，但安装方式会改变可用文件：需要共享清单时应整仓安装或手动复制 references/，并在 Cursor、Antigravity CLI 等工具中按各自目录和命名空间配置。

**标签**: `#AI coding agents`, `#developer tools`, `#software engineering workflows`, `#agent skills`, `#GitHub trending`

---

<a id="item-tech-news-12"></a>
### [Glasswing 分析：发现多但修复少，维护者负担加重](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck 在 LWN 发布的分析称，Anthropic 的 Project Glasswing 自 4 月 7 日启动以来报告了 37,966 项发现，但其中仅 7,349 项已公开、217 项被标记为已修复。该分析还指出，1,654 项被标记为重复、419 项被撤回，重复数量约为修复数量的 7.5 倍，并质疑项目账本中 94.2% 的真实阳性率与实际修复进展不一致。对开源维护者而言，Glasswing 的漏洞分诊负担并未如项目承诺般明显减轻。

rss · LWN.net · 11月12日 16:26

**「背景」** Project Glasswing 是 Anthropic 的 AI 漏洞发现项目，于 4 月 7 日启动，目标是帮助发现软件安全问题。VulnCheck 的 Patrick Garrity 随后统计其自启动以来的发现、修复、重复和撤回情况，因此这篇报道关注项目实际产出与开源维护者分诊负担之间的关系。

**「影响」** 该分析提示，依赖 Glasswing 生成漏洞线索或 CVE 候选项的团队，可能需要额外验证重复项、撤回项和未公开项，并把更多资源投入维护者分诊，而不是直接获得可立即修复的漏洞清单。

**标签**: `#AI security`, `#vulnerability management`, `#Anthropic Glasswing`, `#open source maintainers`, `#software supply chain`

---

## 财经新闻

<a id="item-finance-news-1"></a>
### [英伟达宣布黄仁勋辞任 CEO，克雷斯任临时 CEO](https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition) ⭐️ 9.0/10

英伟达宣布，黄仁勋已辞去总裁、CEO 及董事职务并立即生效，现任执行副总裁兼 CFO 科莱特·克雷斯出任临时 CEO 并继续兼任 CFO，董事会已启动永久继任者搜寻；公司称运营、客户承诺和产品路线不会中断，三季度财报仍按原计划于 11 月 17 日发布。

telegram · zaihuapd · 11月12日 13:52

**「背景」** 黄仁勋自 1993 年起担任英伟达 CEO，被视为 AI 基础设施热潮的关键人物；英伟达此次同时任命首位董事会主席，意味着领导层变动伴随治理结构调整。

**「影响」** 黄仁勋辞职消息公布后，英伟达股价周四下跌 4.34%，市场重新审视其 AI 基础设施供应链与治理连续性。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition">NVIDIA Announces CEO Transition | NVIDIA Newsroom</a></li>
<li><a href="https://www.techpowerup.com/354732/nvidia-co-founder-and-ceo-jensen-huang-officially-resigns?cp=12">NVIDIA Co-Founder and CEO Jensen Huang Officially Resigns</a></li>
<li><a href="https://edition.cnn.com/2026/11/12/tech/jensen-huang-nvidia-resigns">CFO Colette Kress to serve as interim leader after Nvidia CEO ...</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/nvidia-nvda-jensen-huang-second-affair.html">Nvidia stock closes down over 4% after CEO Jensen Huang ...</a></li>
<li><a href="https://www.theguardian.com/technology/2026/nov/12/jensen-huang-built-an-ai-kingdom-now-hes-gone-will-nvidias-ramparts-be-breached">Jensen Huang built an AI kingdom. Now he’s gone, will Nvidia ...</a></li>

</ul>
</details>

**标签**: `#NVIDIA`, `#AI supply chain`, `#corporate leadership`, `#A-share themes`, `#semiconductors`

---

<a id="item-finance-news-2"></a>
### [AI 股收窄跌幅，投资者评估英伟达 CEO 离任影响](https://news.google.com/rss/articles/CBMiuwFBVV95cUxOTDc4NU9Ycko1b01GTVdRT1lMVzJWaEhrLS1OSU92el9GTTRMSEhyTW5VbThOZEhoVGNCbHNBU19EZS1UUlNiTW0wVU41RUdBVkJpQlNRazBvaHJFQ2VnT2FJU183NE9ub1RKQU5wMFp6N1luX3lrMFZubFVIaHJ0TWhZRVkyUzhJVjBsaDRlMEpKNUFLeWtITVhLRVhqOERFMzh0azNJeVlqVzI0ZUowcnV4Z3VYMUdXcFY0?oc=5) ⭐️ 8.0/10

路透标题称，AI 股票在投资者评估英伟达 CEO 离任影响后收窄跌幅；该摘要未给出具体股价、跌幅或离任细节。

google\_news · Reuters · 11月12日 20:57

**「背景」** 英伟达长期由黄仁勋主导，其个人形象与 AI 行业叙事高度绑定，因此其离职消息会直接影响投资者对 AI 供应链和板块估值的预期。

**「影响」** 英伟达处于 AI 芯片供应链核心，CEO 退出引发的担忧可能外溢至全球芯片和 AI 基础设施相关股票，促使投资者重新评估该链条的信心。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.abc.net.au/news/2026-11-13/asx-markets-business-news-live-updates-nov-13/107337368">Markets live: ASX to fall as Nvidia shares dive after Jensen...</a></li>
<li><a href="https://www.theguardian.com/business/live/2026/nov/09/nvidia-jensen-huang-scandal-investigation-ai-industry-tech-stocks-recovery-slump-latest-news-updates">Nvidia ’s value tumbles after ‘honeytrap’ investigation... | The Guardian</a></li>
<li><a href="https://www.globaltimes.cn/page/202611/1374224.shtml">Analysis: Nvidia CEO ’s exit highlights mounting... - Global Times</a></li>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/12/nvidia-ceo-jensen-huang-affairs-share-price-plunges-live-latest?page=with:block-6af53b548f08bed8cbc53c06">Nvidia turmoil continues as Jensen Huang resigns over... | The Guardian</a></li>

</ul>
</details>

**标签**: `#Nvidia`, `#AI stocks`, `#leadership change`, `#AI supply chain`, `#market reaction`

---

<a id="item-finance-news-3"></a>
### [SpaceX 拟投逾 740 亿美元建得州与亚利桑那 AI 园区](https://news.google.com/rss/articles/CBMixAFBVV95cUxQdlQwLUxxTENmenRpSFFXVlNUeVkzeURtNWxCZ1RuVEQwdENKV0g3MndreVZsZFYwVGtpT3Q3SDJZU0pHTGI1WFFYWERreFJmbzVjaUtOR2NjUURRMTVHNVlKdGE0VkdRVzRvekpIcHdmRGdOV2kwRXVmbWl1blRIV1VKSjQ4c19FSVFTUWZNM2ptQ0ZaMW96a2UyTFphWjNsSnc3ZmJZdWhHNWpiS19hTDhYSk9vNkpkeng1N3prZ1Y3b1lI?oc=5) ⭐️ 8.0/10

据路透社报道，SpaceX 计划投资逾 740 亿美元，在得克萨斯州和亚利桑那州建设人工智能园区。

google\_news · Reuters · 11月12日 20:23

**「背景」** 据路透社报道，SpaceX 计划投资逾 740 亿美元建设得克萨斯州 Starbase 和亚利桑那州科奇斯县的人工智能/超级计算园区；其中亚利桑那园区约 500 亿美元，并拟采用干式冷却以减少用水。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://interestingengineering.com/ai-robotics/spacex-arizona-supercomputing-campus-dry-cooling">SpaceX &#x27;s 6-gigawatt campus will use dry cooling, skip groundwater use</a></li>
<li><a href="https://www.finam.ru/publications/item/spacex-vlozhit-74-mlrd-v-sozdanie-superkompyuternykh-kompleksov-v-tekhase-i-arizone-20261112-2203/">SpaceX вложит $ 74 млрд в создание... — Финам</a></li>

</ul>
</details>

**标签**: `#SpaceX`, `#AI infrastructure`, `#capital expenditure`, `#data centers`, `#global technology`

---

<a id="item-finance-news-4"></a>
### [黄仁勋辞职与作证或加剧中美科技紧张](https://www.cnbc.com/2026/11/13/jensen-huang-nvidia-us-china-relations.html) ⭐️ 7.0/10

英伟达前 CEO 黄仁勋周四辞职，并同意在 11 月 26 日感恩节前就涉嫌中国间谍丑闻向国会作证；CNBC 引述分析师称，国会可能在今年年底前收紧对华半导体出口管制。

rss · CNBC Finance · 11月13日 02:56

**「背景」** 英伟达前 CEO 黄仁勋因被指与一名据称涉嫌为中国从事情报活动的女性有不当关系而辞职，公司首席财务官 Colette Kress 临时接任，黄仁勋同意在 11 月 26 日前赴国会作证。此事发生在中美围绕芯片出口管制和 AI 供应链持续博弈的背景下，也正值美国国会加强对华科技政策审查之际。

**「影响」** 分析师预计，黄仁勋事件可能促使美国国会收紧对华先进芯片出口审查，并波及向客户提供受限芯片的离岸数据中心，同时增加中国以稀土等供应反制的风险，令芯片出口商、数据中心运营方和半导体/AI 投资者面临更高政策不确定性。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.theguardian.com/technology/2026/nov/13/nvidia-scandal-sparks-us-national-security-concerns-china">Nvidia scandal sparks US national security furore and... | The Guardian</a></li>
<li><a href="https://techcrunch.com/2026/11/12/nvidia-ceo-jensen-huangs-affair-with-alleged-chinese-spy-a-timeline/">The unfolding Jensen Huang scandal: a timeline | TechCrunch</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/nvidia-trump-jensen-chip-export-controls-china-xi-.html">Nvidia fallout revives push for chip curbs ahead of China summit</a></li>
<li><a href="https://www.nytimes.com/2025/05/29/business/china-us-export-controls.html">Export Controls Are Endangering the Fragile U.S.- China Truce - The...</a></li>

</ul>
</details>

**标签**: `#US-China tech policy`, `#Nvidia`, `#semiconductor export controls`, `#AI supply chain`, `#rare earths`

---

<a id="item-finance-news-5"></a>
### [特朗普涉伊朗言论推高油价](https://www.cnbc.com/2026/11/12/oil-prices-jump-after-trump-says-no-iran-deal-needed-weve-got-their-strait.html) ⭐️ 7.0/10

布伦特原油结算价上涨 3.3%至 95.82 美元/桶，美国西德克萨斯中质原油（WTI）上涨 2.6%至 88.74 美元/桶；此前特朗普称无需与伊朗达成协议，并声称美国控制霍尔木兹海峡，重新引发市场对中东供应中断的担忧。

rss · CNBC Finance · 11月13日 00:01

**「背景」** 霍尔木兹海峡是全球关键石油和液化天然气（LNG）海运通道，2025 年约 2000 万桶石油及石油产品每日经此运输，短暂中断也会显著冲击油价。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.iea.org/about/oil-security-and-emergency-response/strait-of-hormuz">Strait of Hormuz - About - IEA</a></li>
<li><a href="https://www.bbc.com/news/articles/c78n6p09pzno">Iran war: What is the Strait of Hormuz and why does it matter?</a></li>

</ul>
</details>

**标签**: `#Oil prices`, `#Geopolitical risk`, `#Energy markets`, `#Middle East conflict`, `#Commodities`

---

<a id="item-finance-news-6"></a>
### [印度 Clean Max 拟投 53 亿美元清洁能源供 AI 算力设施](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

路透社报道，印度 Clean Max 计划投资 53 亿美元建设清洁能源，为 AI 计算设施供电。

google\_news · Reuters · 11月12日 13:39

**「背景」** 人工智能计算设施需要大量电力；有研究警告，到 2027 年 AI 行业可能消耗相当于荷兰规模的电力，这为清洁能源企业投资 AI 计算供电提供了背景。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.bbc.com/news/technology-67053139">Warning AI industry could use as much energy as the Netherlands</a></li>

</ul>
</details>

**标签**: `#AI infrastructure`, `#clean energy`, `#capital expenditure`, `#India`, `#AI supply chain`

---

<a id="item-finance-news-7"></a>
### [思科上调年度营收预期](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

据路透社报道，思科因 AI 网络设备需求强劲上调全年营收预测，但报道未给出具体金额或增幅。

google\_news · Reuters · 11月12日 23:18

**「背景」** 思科此次上调的是 2027 财年展望，其财年与常见日历年不同；增长主要来自云服务商和企业客户对数据中心及网络设备的投资。思科还与英伟达扩大 AI 网络合作，以支持这一需求。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://finance.yahoo.com/markets/stocks/articles/cisco-shares-climb-4-strong-214347073.html">Cisco shares climb 4% on strong earnings beat and raised outlook</a></li>
<li><a href="https://mezha.net/eng/bukvy/b4bfbf59_cisco_forecasts_stronger/">Cisco Forecasts Stronger 2027 Revenue as AI Network Demand ...</a></li>
<li><a href="https://www.linkedin.com/posts/notreload-ai_cisco-lifts-forecast-as-ai-spending-boosts-activity-7394488950117142528-H-Wm">Cisco Systems reports strong Q results, raises outlook due to AI and...</a></li>

</ul>
</details>

**标签**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#Reuters`, `#AI supply chain`

---

<a id="item-finance-news-8"></a>
### [美国 2027 财年 10 月预算赤字创纪录](https://news.google.com/rss/articles/CBMiugFBVV95cUxPSDdFRmlLcWNxcWNRVHRGN05hM2dMcmpEeW1IY1gyVkM0R2NPQVpfWU1ObHZMX08xZHFFYXhGbllpTW9abFR2SGxoNUprSFdxYTR1OXF1N3d2RGRNNGRzelRRdzhSOF8tMmM2U2I3clNQR0trbDZrLWN4QlVyNXlKOTJsdXp2NU5aWUxHR3AyQndrNFc5dFhBQS1MWHdZZHQ5c0thakE1b1Y1OTdhcFNHb1U1cmlZbjNyQWc?oc=5) ⭐️ 7.0/10

据路透社报道，美国在 2027 财年首月（10 月）录得 4040 亿美元预算赤字，创该月份纪录。

google\_news · Reuters · 11月12日 20:18

**「背景」** 美国联邦财政年度从 10 月开始，财政部按月度公布预算执行数据；创纪录赤字出现在收入下降、支出大幅增加的背景下。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.forexfactory.com/news/1436074-us-starts-2027-fiscal-year-with-record-october">US starts 2027 fiscal year with record October budget deficit of $ 404 ...</a></li>
<li><a href="https://fiscaldata.treasury.gov/americas-finance-guide/federal-spending/">Federal Spending | U . S . Treasury Fiscal Data</a></li>

</ul>
</details>

**标签**: `#US fiscal deficit`, `#Treasury budget`, `#macroeconomic data`, `#interest rates`, `#Reuters`

---