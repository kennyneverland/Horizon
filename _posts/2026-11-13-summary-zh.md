---
layout: default
title: "Horizon Summary: 2026-11-13 (ZH)"
date: 2026-11-13
lang: zh
---

> 从 128 条内容中筛选出 20 条重要资讯。

---

**科技新闻**
1. [Rust 1.100 发布：语言特性与 Cargo 供应链改进](#item-tech-news-1) ⭐️ 8.0/10
2. [PostgreSQL 22 年类型混淆原语被利用为 RCE](#item-tech-news-2) ⭐️ 8.0/10
3. [谷歌据称发布 Gemini 4 Hydrogen，主打编程与智能体](#item-tech-news-3) ⭐️ 8.0/10
4. [Apple Foundation Models 开发者访问与本地 AI 讨论](#item-tech-news-4) ⭐️ 7.0/10
5. [开源项目称 16B LLM 可运行于 1GB 内存旧设备](#item-tech-news-5) ⭐️ 7.0/10
6. [llm-gemini 0.37 记录 Gemini 4 Hydrogen 定价与测试](#item-tech-news-6) ⭐️ 7.0/10
7. [VulnCheck 称 Glasswing 修复少、重复多加重维护者负担](#item-tech-news-7) ⭐️ 7.0/10
8. [ISO 首次拒绝批准 C++26 标准文档](#item-tech-news-8) ⭐️ 7.0/10
9. [马来西亚调查 Megaspeed 是否转口 AI 芯片](#item-tech-news-9) ⭐️ 7.0/10
10. [黄仁勋离开英伟达或引发 AI 芯片竞争](#item-tech-news-10) ⭐️ 7.0/10
11. [UMAP 0.6 发布新初始化与优化器，提升大规模降维性能](#item-tech-news-11) ⭐️ 7.0/10
12. [苹果详解 Secure Exclaves：硬件验证录音指示器](#item-tech-news-12) ⭐️ 7.0/10

**财经新闻**
1. [礼来口服 GLP-1 减重药获中国批准](#item-finance-news-1) ⭐️ 8.0/10
2. [英伟达 CEO 黄仁勋辞职](#item-finance-news-2) ⭐️ 8.0/10
3. [黄仁勋辞职或加剧中美科技紧张](#item-finance-news-3) ⭐️ 7.0/10
4. [印度拟禁止私募股权机构控制多家非银行放贷机构](#item-finance-news-4) ⭐️ 7.0/10
5. [UForce 完成 7 亿美元融资，估值 60 亿美元](#item-finance-news-5) ⭐️ 7.0/10
6. [印度 Clean Max 拟投 53 亿美元建清洁能源 AI 算力设施](#item-finance-news-6) ⭐️ 7.0/10
7. [京东拟借 Ceconomy 交易拓展欧洲电子零售](#item-finance-news-7) ⭐️ 7.0/10
8. [思科上调年度营收预测](#item-finance-news-8) ⭐️ 7.0/10

---

## 科技新闻

<a id="item-tech-news-1"></a>
### [Rust 1.100 发布：语言特性与 Cargo 供应链改进](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100 发布，稳定了 never 类型和自定义分配器，并引入 Cargo 的依赖冷却配置与未使用依赖警告。启用 minimum publish age 后，解析器会忽略比设定时间更新发布的版本，除非它们已存在于 Cargo.lock；cargo install 现在默认使用 .crate tarball 中的现有 lockfile，--locked 成为 no-op。

hackernews · mbStavola · 11月12日 18:39 · [社区讨论](https://news.ycombinator.com/item?id=50472038)

**「背景」** Rust 1.100 的发布说明将 never type、Allocator API、Cargo 未使用依赖报告以及 min-publish-age 列为稳定或新增能力。其中，never type \`\!\` 表示永不返回值的发散计算，min-publish-age 则是用于限制过新依赖版本的发布冷却配置。

**「影响」** 这些变化会改变依赖解析、安装和警告的默认行为，开发者可能需要审查 Cargo.toml、Cargo.lock 和 CI 中 --locked 的使用，并在供应链敏感项目中考虑启用依赖冷却。

**「社区讨论」** 社区评论普遍欢迎 never 类型、自定义分配器和依赖冷却等变化，但有人质疑依赖冷却并非完整解决方案，因为恶意 crate 可延迟触发。另有评论指出 bool::toggle、Box::map 等稳定化 API 可能未被发布说明充分提及。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/">Announcing Rust 1 . 100 . 0 | Rust Blog</a></li>
<li><a href="https://www.phoronix.com/news/Rust-1.100-Released">Rust 1 . 100 Released With The &quot; Never &quot; Type Finally Stable - Phoronix</a></li>
<li><a href="https://github.com/rust-lang/rust/issues/163811">Draft release notes for 1 . 100 . 0 · Issue #163811 · rust -lang/ rust · GitHub</a></li>

</ul>
</details>

**标签**: `#Rust`, `#programming languages`, `#open source`, `#software engineering`, `#supply-chain security`

---

<a id="item-tech-news-2"></a>
### [PostgreSQL 22 年类型混淆原语被利用为 RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 8.0/10

安全研究者发布博客，称其把 PostgreSQL 中一个存在约 22 年的类型混淆原语发展为远程代码执行，并在标题中关联 CVE-2026-6460。该材料没有给出受影响版本、补丁状态或独立验证结果，因此具体可用性仍需以原始文章和后续公告为准。对数据库安全读者而言，重点是作者展示的从内部类型混淆原语到服务器端代码执行的利用链。

hackernews · ozirus · 11月12日 18:22 · [社区讨论](https://news.ycombinator.com/item?id=50471761)

**「PostgreSQL 类型混淆与 CVE-2026-6460」** PostgreSQL 内部需要把值与其类型标识正确绑定；一旦类型混淆，数据库对象创建者可能通过 DDL 操作触发内存类型错误。CVE-2026-6460 描述的就是 ALTER ... SET DATA TYPE 等路径下，对象创建者能够以运行数据库的操作系统用户身份执行任意代码。因此，这项分析讨论的是把一个长期存在的类型混淆原语进一步转化为任意代码执行影响。

**「影响」** 若该利用链成立，运行多租户或共享 PostgreSQL 实例的组织需要重新评估数据库账户的隔离边界：一个可连接数据库的账户可能成为获取服务器权限的跳板。用户应关注 CVE-2026-6460 的修复或缓解信息，并检查最小权限、插件或扩展以及内部类型处理相关变更。

**「社区讨论」** 评论者对命名分歧明显：logophobia 和 jmuguy 认为这更像需要数据库账户访问的权限提升，主要影响多租户数据库，而非无认证 RCE；amluto 则把 PostgreSQL 内部 Datum 与类型 ID 分离的设计视为值得警惕的代码风险。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>
<li><a href="https://www.thehackerwire.com/vulnerability/CVE-2026-6460/">CVE-2026-6460: PostgreSQL Remote Code Execution (RCE ...</a></li>

</ul>
</details>

**标签**: `#postgresql`, `#security`, `#exploit-development`, `#database-internals`, `#open-source`

---

<a id="item-tech-news-3"></a>
### [谷歌据称发布 Gemini 4 Hydrogen，主打编程与智能体](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/) ⭐️ 8.0/10

据来源称，谷歌发布 Gemini 4 Hydrogen，面向日常编程与智能体工作流，并向开发者、企业和普通用户开放。定价为每百万输入 token 1.5 美元、每百万输出 token 7.5 美元。来源还称其相较 Gemini 3.8 Flash 速度提升 2.5 倍，Terminal-Bench 4.1 得分从 18.2% 升至 57%，默认档在 Artificial Analysis 指数上超过 Argon；这些均为来源报告的发布与基准说法。

telegram · zaihuapd · 11月13日 02:02

**「背景」** Gemini 4 Hydrogen 是谷歌推出的新独立模型，面向日常编程和智能体工作流；官方博客将其与 Argon、Gemini 3.8 Flash 等既有模型作比较，称默认高思考档在 Artificial Analysis 指数上超过 Argon，并提供不同推理深度与性能档位。

**「影响」** 对需要低延迟智能体工作流的开发者，若来源中的定价与速度成立，该模型可能成为 Gemini 3.8 Flash 的候选替代品；但应自行验证 Terminal-Bench 4.1 与 Artificial Analysis 结果以及实际可用性。

**「社区讨论」** Hacker News 评论者欢迎更快的 Flash 档，并抱怨 Argon 和 Carbon 在智能体任务中太慢。也有人质疑新命名混乱，并担心把子代理模型选择交给模型可能因模型过度乐观而不可靠。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/">Introducing Gemini 4 Hydrogen for Agentic Workflows</a></li>
<li><a href="https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity">Gemini 4 Hydrogen and Orchestrator | Google Antigravity Blog</a></li>
<li><a href="https://artificialanalysis.ai/models/releases/gemini-4-hydrogen">Gemini 4 Hydrogen: Release Intelligence, Performance &amp; Price</a></li>

</ul>
</details>

**标签**: `#AI models`, `#Google Gemini`, `#inference pricing`, `#agentic workflows`, `#benchmarking`

---

<a id="item-tech-news-4"></a>
### [Apple Foundation Models 开发者访问与本地 AI 讨论](https://developer.apple.com/foundation-models-framework/) ⭐️ 7.0/10

该条目指向 Apple 的 Foundation Models framework 开发者页面；社区讨论称，参与 App Store 小型企业计划且首次下载数低于两百万的开发者，可在 Apple Intelligence 可用地区通过 Private Cloud Compute 使用 Apple Foundation Models，免云 API 成本，并通过 TestFlight 或 ad hoc 分发测试相关功能。另有评论提到 Apple 的 CoreAI 仓库正在将开放权重模型适配为 Swift 原生格式，以及开发者在 M1 8GB 等设备上运行本地终端 AI 的体验。由于缺少源页正文，这些能力是否已正式开放、覆盖范围和具体限制仍需以 Apple 文档为准。

hackernews · kermatt · 11月12日 21:13 · [社区讨论](https://news.ycombinator.com/item?id=50474361)

**「背景」** Apple 的 Foundation Models framework 提供对大语言模型的访问，包括用于 Apple Intelligence 的设备端模型和 Private Cloud Compute 服务器端模型。Apple 表示，符合条件的 App Store Small Business Program 开发者可在应用中使用 Private Cloud Compute 模型，且无需支付云 API 费用；2026 年 6 月的报道提到，首次下载量低于 200 万的开发者可访问这些服务器端基础模型。

**「影响」** 对符合条件的开发者而言，这降低了在 Apple 平台上使用 Foundation Models 与 Private Cloud Compute 的推理成本门槛，但资格受小型企业计划、下载量阈值、Apple Intelligence 可用地区以及 App Store/TestFlight/ad hoc 分发方式限制；不符合条件者仍需评估其他本地或云端方案。

**「社区讨论」** 评论主要围绕访问资格、CoreAI 开放权重模型适配和终端本地 AI 体验展开。有人引用小型企业计划与两百万首次下载限制，有人称 CoreAI 仓库支持 Swift 原生运行，也有人基于个人使用认为 M1 8GB 可运行本地 AI；这些均为评论观点，不等于官方确认。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://developer.apple.com/private-cloud-compute/">Private Cloud Compute - Apple Developer</a></li>
<li><a href="https://developer.apple.com/documentation/foundationmodels">Foundation Models | Apple Developer Documentation</a></li>
<li><a href="https://techcrunch.com/2026/06/08/apple-bets-cheaper-ai-will-woo-small-developers/">Apple bets cheaper AI will woo small developers - TechCrunch</a></li>

</ul>
</details>

**标签**: `#Apple AI`, `#Foundation Models`, `#Private Cloud Compute`, `#Developer Tools`, `#Local AI`

---

<a id="item-tech-news-5"></a>
### [开源项目称 16B LLM 可运行于 1GB 内存旧设备](https://github.com/hyperionaidev/smolmaxxing/) ⭐️ 7.0/10

GitHub 项目 smolmaxxing 公开了 kernels、复现结果和 Hugging Face 上的修改模型，面向想在低内存设备上运行大语言模型的开发者。作者 mrashad74 声称 16B 参数模型可在 iPad Air 一代和小米电视盒上运行，两者可用内存均不足 1GB。该能力目前来自项目自述，缺少独立基准或第三方验证。

hackernews · mrashad74 · 11月12日 15:23 · [社区讨论](https://news.ycombinator.com/item?id=50468888)

**「背景」** smolmaxxing 的前提是，电视盒、旧手机、单板计算机和路由器通常拥有闲置的 CPU、RAM 和闪存，但运行大模型仍受可用内存和权重加载限制。该项目试图通过自定义内核、更智能的内存使用和权重流式传输来解锁这些硬件。公开资料还列出两个约 1GB 可用内存的目标设备：小米电视盒和 2013 年 iPad Air。

**「影响」** 开发者可据此复现低内存 16B 推理路径，但采用前需自行测量 token/s、内存占用和任务质量，因为旧设备兼容性与作者给出的速度仅为主观描述。

**「社区讨论」** 作者 mrashad74 报告了旧设备运行 16B 模型的结果；Farmadupe2 认为推理主要依赖乘法、难点在获取旧硬件，而 yjftsjthsd-h 和 cjdell 则关注小模型实用性与旧 GPU 实验结果不一。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://github.com/hyperionaidev/smolmaxxing">GitHub - hyperionaidev/smolmaxxing: maxxing the ability to ...</a></li>
<li><a href="https://ai-tldr.dev/tools/smolmaxxing/">smolmaxxing GitHub: LLMs on a TV box and an old iPad | AI/TLDR</a></li>

</ul>
</details>

**标签**: `#edge-AI`, `#LLM-inference`, `#open-source`, `#quantization`, `#hardware-efficiency`

---

<a id="item-tech-news-6"></a>
### [llm-gemini 0.37 记录 Gemini 4 Hydrogen 定价与测试](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

llm-gemini 0.37 发布，为 LLM 用户和开发者记录了 Google 新推出的 Gemini 4 Hydrogen：输入 1.50 美元/百万 token、缓存输入 0.075 美元/百万 token、输出 7.50 美元/百万 token。Google 将 Hydrogen 定位为低成本日常执行模型，并称其成为新的免费层模型、驱动 Google Search 的 AI 功能；Gemini 4 Carbon 和 Argon 在 2026 年 12 月 1 日前同价，之后价格翻倍。Willison 的对比测试显示，Hydrogen 生成的“骑自行车的鹈鹕”更简单，耗时和成本更低，但当前仍明显贵于 Claude Haiku 5.5 和 GPT-6 Luna。

rss · Simon Willison · 11月12日 22:55

**「背景」** llm-gemini 是 Simon Willison 维护的 LLM 命令行工具插件，用于接入 Google Gemini 模型；此次 0.37 发布围绕 Google 新推出的 Gemini 4 Hydrogen 展开。Gemini 4 家族还包括 Carbon 和 Argon，Google 将 Hydrogen 定位为低成本、快速执行的模型，并把它设为新的免费层及 Google 搜索 AI 功能模型。

**「影响」** 对使用 llm-gemini 或规划 Gemini 4 成本的开发者，12 月 1 日的价格变化会改变模型选择：Hydrogen 在 Carbon/Argon 涨价后才形成 75% 折扣，而在此之前它与同级模型的价格差距较小；同时 Hydrogen 输出质量在简单测试中明显低于 Carbon/Argon，因此复杂任务可能仍需保留更昂贵模型。

**标签**: `#Gemini`, `#AI pricing`, `#LLM tooling`, `#inference cost`, `#Google`

---

<a id="item-tech-news-7"></a>
### [VulnCheck 称 Glasswing 修复少、重复多加重维护者负担](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck 分析称，Anthropic 报告 Project Glasswing 自 4 月 7 日启动以来已产生 37,966 项漏洞发现，但仅 7,349 项公开、217 项标记修复；1,654 项被标记为重复，419 项被撤回。分析质疑其 94.2% 真实阳性率的统计口径，因为撤回和重复数量超过修复，可能意味着分诊率统计缺少反馈。该分析面向开源维护者和软件供应链安全，认为 Glasswing 的产出尚未兑现减少维护者负担的叙事。

rss · LWN.net · 11月12日 16:26

**「背景」** Anthropic 的 Project Glasswing 是一个用 AI 自动发现软件漏洞并推动修复的项目，自 4 月 7 日启动以来向开源维护者提交了大量发现。VulnCheck 的评估关注这些发现是否真正进入公开披露、重复、撤回和修复流程，因此该项目的实际安全贡献需要结合维护者的分诊负担来判断。

**「影响」** 对开源维护者而言，Glasswing 当前可能主要带来重复、撤回和公开披露压力，而不是可落地的修复；维护者需要额外甄别大量 AI 生成发现，这会消耗有限的安全响应资源。

**标签**: `#AI security`, `#vulnerability management`, `#Anthropic Project Glasswing`, `#open-source maintainers`, `#software supply chain`

---

<a id="item-tech-news-8"></a>
### [ISO 首次拒绝批准 C++26 标准文档](https://lwn.net/Articles/1105400/) ⭐️ 7.0/10

ISO 于 10 月 23 日首次拒绝批准 WG21 提交的 C++26 标准文档，使该标准的未来走向不确定。这一决定源于围绕拟议“contracts”特性的争议，该特性计划在函数签名中加入前置条件和后置条件。WG21 负责审议和整合 C++ 语言修订，并将文档提交 ISO 表决。

rss · LWN.net · 11月12日 14:29

**「背景」** C++ 标准通常由 ISO 的 WG21 工作组整合提案后，提交给 ISO 国家团体投票批准。此前 C++26 草案在国际标准草案投票中未获得所需的三分之二多数，争议主要集中在 P2900 合约提案上。

**「影响」** C++26 的正式批准时间表因此变得不确定，依赖 contracts 的编译器实现和用户代码计划都不能再假定该特性会按原提案进入已批准标准。由于 WG21 是负责 C++ 语言标准化的工作组，后续结果将取决于它如何处理 contracts 争议并重新推进文档批准流程。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://sitem.co/public/summary/6215/c-26-dis-ballot-rejected-due-to-contracts-controversy">C++26 DIS Ballot Rejected Due to Contracts Controversy</a></li>
<li><a href="https://www.margo.com/en/blog-en/cpp26-rejected-iso-standard/">C++26 Rejected: Why Is the Standard Blocked? - margo.com</a></li>
<li><a href="https://open-std.org/jtc1/sc22/wg21/">ISO/IEC JTC1/SC22/ WG 21 - The C++ Standards Committee - ISOCPP</a></li>

</ul>
</details>

**标签**: `#C++26`, `#ISO standardization`, `#contracts`, `#programming languages`, `#software engineering`

---

<a id="item-tech-news-9"></a>
### [马来西亚调查 Megaspeed 是否转口 AI 芯片](https://www.bloomberg.com/news/articles/2026-11-13/malaysia-checks-whether-chips-were-reexported-by-megaspeed-unit) ⭐️ 7.0/10

马来西亚表示正在调查新加坡 Megaspeed International Pte 下属机构进口的 AI 芯片是否随后被转运至海外。此举加强了对该公司的审查，而该公司正处于导致英伟达 Jensen Huang 辞职的丑闻中心。

rss · Bloomberg Technology · 11月13日 03:21

**「背景」** 先进 AI 芯片进口后若被转运至其他地区，可能引发出口管制或合规层面的审查。马来西亚此次调查聚焦新加坡 Megaspeed International Pte 旗下关联公司，背景是与 Nvidia 首席执行官黄仁勋辞职有关的丑闻。

**「影响」** 对依赖 Megaspeed 渠道获取 AI 芯片的企业而言，调查可能带来更严格的出口管制、供应链追溯和合规审查压力。

**标签**: `#AI chips`, `#export controls`, `#Nvidia`, `#supply chain`, `#regulatory investigation`

---

<a id="item-tech-news-10"></a>
### [黄仁勋离开英伟达或引发 AI 芯片竞争](https://www.bloomberg.com/news/videos/2026-11-12/can-huang-s-exit-create-chip-competition-video) ⭐️ 7.0/10

彭博报道，黄仁勋离开英伟达引发市场讨论：竞争对手能否削弱其在 AI 半导体市场的主导地位。彭博智能分析师 Robert Schiffman 和 Mandeep Singh 认为，AI 算力需求仍然强劲，但黄仁勋离职可能为博通、AMD 和谷歌等厂商创造机会，因为客户会寻找替代方案并可能抵制英伟达的高价。该判断来自视频分析摘要，未提供具体离职细节、产品版本或可验证的定价变化。

rss · Bloomberg Technology · 11月12日 22:54

**「事件背景」** 据彭博报道，英伟达董事会在黄仁勋被指涉及两段婚外情、其中一段与疑似为中国从事间谍活动的女性有关后将其免职；首席财务官 Colette Kress 出任临时 CEO，Harvey Jones 被任命为公司首任董事长。这一领导层变动构成当前关于英伟达 AI 芯片主导地位和定价权是否会被竞争对手削弱讨论的直接背景。

**「采购与兼容性影响」** AI 算力买家可借黄仁勋离任传闻，把 Broadcom、AMD、Google 等替代加速器纳入询价和兼容性评估，以争取对 Nvidia 高端定价的议价空间。但截至 2026 年，Nvidia 仍约占 AI 芯片市场 70%，AMD MI300X 约 10%，Google TPU、Amazon Trainium 等定制芯片合计约 5%，因此实际迁移仍受软件生态、互联与推理部署成本限制。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/read-the-memos-from-nvidia-chairman-and-interim-ceo-after-ouster">Nvidia Releases Leadership Memos Following CEO... - Bloomberg</a></li>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/jensen-huang-face-of-the-ai-boom-ousted-by-nvidia-board-as-ceo">Jensen Huang Removed as Nvidia CEO Following... - Bloomberg</a></li>
<li><a href="https://www.tomshardware.com/tech-industry/semiconductors/custom-ai-asics-examined-from-broadcom-to-mtia">The custom AI ASIC state of play (May 2026) — Broadcom deals ...</a></li>
<li><a href="https://www.companieshistory.com/ai-market-share-by-company/">AI Market Share By Company Statistics 2026</a></li>

</ul>
</details>

**标签**: `#Nvidia`, `#AI chips`, `#semiconductor competition`, `#compute pricing`, `#China A-share AI themes`

---

<a id="item-tech-news-11"></a>
### [UMAP 0.6 发布新初始化与优化器，提升大规模降维性能](https://www.reddit.com/r/MachineLearning/comments/1xudaah/umap_06_new_initialization_new_optimizers_and/) ⭐️ 7.0/10

UMAP 0.6 发布，引入递归初始化、新优化器和更快的最近邻搜索，面向需要大规模降维的机器学习用户。在 300 万篇 arXiv 论文上，该版本可在 5 分钟内完成运行，而 UMAP 0.5 尚未找到最近邻；固定种子下新优化器可利用全部核心复现，相比有种子 0.5 单线程 52 分钟快约 12 倍。新初始化比谱方法或 PCA 更接近最终布局，并让优化器在更少 epoch 内达到最终布局 3% 以内；新优化器通过高效 hard-negative mining 和更高 repulsion strength 支持，提升百万级数据集的邻域精度和细节。

reddit · r/MachineLearning · /u/lmcinnes · 11月12日 13:51

**「背景」** UMAP 是常用于高维数据可视化和降维的机器学习库，其流程通常依赖最近邻搜索、初始布局和迭代优化器。0.6 版本是在 UMAP 0.5 的基础上推出，重点针对大规模数据集下运行慢、细节不足和结果不够稳定等问题进行改进。

**「影响」** 对处理百万级数据集的用户，UMAP 0.6 的提速和更细结构使嵌入可视化与后续分析更可复现，但新初始化和优化器会改变输出，因此需要通过设置 compatibility\_layout=False 显式启用，并重新校准或重新生成既有可视化。

**标签**: `#machine-learning`, `#dimensionality-reduction`, `#open-source`, `#performance`, `#software-libraries`

---

<a id="item-tech-news-12"></a>
### [苹果详解 Secure Exclaves：硬件验证录音指示器](https://security.apple.com/blog/secure-exclaves/) ⭐️ 7.0/10

苹果 11 月 12 日发文详解 Secure Exclaves（安全隔离区）架构，称其可在独立安全环境中处理音视频，使主系统和 App 在环境感知模式下只获取必要识别结果，而不接触原始数据。该架构已用于 HomeView 的人脸与声音识别，并在 iPhone 18 Pro 上用于隐私指示器。在 iPhone 18 Pro 上，专用硬件会验证麦克风指示点的颜色、亮度和可见性，确认符合要求后才允许音频进入主系统；苹果还要求相关 Siri 音频会话期间持续显示指示点，且总显示时间至少三秒，以降低被遮挡或伪装的风险。

telegram · zaihuapd · 11月12日 09:13

**「架构背景」** Secure Exclaves 可理解为苹果将音视频处理放入隔离安全环境的硬件架构，使主系统和应用只获得必要结果，而非原始数据。此前报道显示，该机制已用于 HomeView 的摄像头与麦克风数据保护，并参与 iPhone 18 Pro 等设备的隐私指示器控制。

**「影响」** 对 iPhone 18 Pro 和 HomeView 用户而言，苹果把录音指示从单纯软件显示扩展到专用硬件校验，可能提高对隐私状态被隐藏或伪造的防护。对使用环境感知识别的 App 而言，苹果描述的设计意味着它们可能只能接收隔离区返回的识别结果，而非原始音视频数据。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://forums.macrumors.com/threads/apple-explains-how-homeview-keeps-camera-data-private.2494273/">Apple Explains How HomeView Keeps Camera Data Private</a></li>
<li><a href="https://www.wired.com/story/apples-homeview-tries-face-authentication-without-faceid/">Apple ’s HomeView Tries Face Authentication Without FaceID | WIRED</a></li>

</ul>
</details>

**标签**: `#Apple`, `#security architecture`, `#privacy`, `#AI inference`, `#hardware`

---

## 财经新闻

<a id="item-finance-news-1"></a>
### [礼来口服 GLP-1 减重药获中国批准](https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/) ⭐️ 8.0/10

中国药监局 11 月 12 日批准礼来口服 GLP-1 减重药奥氟格列隆钙片（商品名穆优达）为 1 类新药，用于肥胖或超重且伴至少一种体重相关合并症的成人；这是国内首个获批的口服 GLP-1 减重药（GLP-1 是一类模拟肠道激素、帮助控制体重和血糖的药物）。该药每日一次、不受饮食饮水限制；其 2 型糖尿病适应证仍在审评中，价格和上市时间未公布。

telegram · zaihuapd · 11月12日 10:09

**「市场背景」** 中国减重药市场此前主要由诺和诺德、辉瑞和信达生物的每周一次注射 GLP-1 药物主导，口服剂型尚未获批用于减重。

**「影响」** 对国内肥胖或超重治疗市场，礼来将以每日一次口服方案与诺和诺德、辉瑞及信达生物的每周一次注射产品竞争；由于价格和上市时间未公布，实际竞争影响尚不明确。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/">China approves Eli Lilly’s weight loss pill orforglipron</a></li>
<li><a href="https://pharmaphorum.com/news/lilly-beats-novo-china-oral-glp-1-obesity">Lilly beats Novo to China with an oral GLP-1 for obesity</a></li>

</ul>
</details>

**标签**: `#GLP-1减重药`, `#医药监管审批`, `#礼来`, `#信达生物`, `#A股医药主题`

---

<a id="item-finance-news-2"></a>
### [英伟达 CEO 黄仁勋辞职](https://news.google.com/rss/articles/CBMisAFBVV95cUxOMEFwN0FWdjB6blNtR0RZaTBWZXZDaWVwYkhXREttY2FaYVNNVC1qNEFHYm9Yd1pDODBDN2tvNzhnMTY4cmxWYTg1WVFidzFlNVFEdlZNb3IyZG1nS2FKcHAzUERhQW9EdG9oOER6YmwydXZOd0t1VHRub1BCdFdoR1V4dktlUVUydjZWeU53aVdKMGwtOGFtZmd2T3VhODF3eXhPazVtbV81b0hpUi1vcw?oc=5) ⭐️ 8.0/10

路透社报道，英伟达首席执行官黄仁勋辞职，并称这对由其参与推动的人工智能热潮构成重大打击；现有内容未提供原因或继任安排。

google\_news · Reuters · 11月12日 13:52

**「背景」** 英伟达董事会表示，黄仁勋已辞去 CEO，并由首席财务官科莱特·克雷斯出任临时 CEO。特朗普随后公开提议由苹果执行董事长蒂姆·库克接任。

**「影响」** Nvidia 投资者和 AI 芯片产业链面临不确定性，因为黄仁勋辞职后同意向国会作证，且分析师称其离职可能削弱美国在全球 AI 竞赛中的竞争力。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://digg.com/tech/f9rhq5tp">Trump’s one-man Nvidia CEO shortlist: Tim Cook · Digg</a></li>
<li><a href="https://www.bbc.com/news/live/c6zjry11v8w1t">Huang agrees to appear before Congress, US lawmakers... - BBC News</a></li>
<li><a href="https://www.bbc.com/news/articles/cmq5vd1wdgz6o">Scandal-hit Nvidia CEO Jensen Huang quits, plunging AI chipmaking...</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/nvidia-jensen-huang-ceo-live-updates.html">Nvidia CEO Jensen Huang resigns : Live updates</a></li>

</ul>
</details>

**标签**: `#Nvidia`, `#Jensen Huang`, `#CEO resignation`, `#AI supply chain`, `#semiconductor leadership`

---

<a id="item-finance-news-3"></a>
### [黄仁勋辞职或加剧中美科技紧张](https://www.cnbc.com/2026/11/13/jensen-huang-nvidia-us-china-relations.html) ⭐️ 7.0/10

据 CNBC 报道，英伟达 CEO 黄仁勋周四辞职，并将就在与一名被指为中国间谍人士的关系引发的国会审查中、于 11 月 26 日前作证。分析师称此事可能推动美国收紧半导体出口管制，并增加中国报复风险。

rss · CNBC Finance · 11月13日 02:56

**「背景」** 美国自 2022 年开始限制英伟达对华销售先进芯片，特朗普政府 2025 年放松了部分拜登时期限制；中国外交部称所谓“中国间谍”指控是抹黑。

**「影响」** 分析师称，若美国进一步收紧半导体出口管制，中国可能限制稀土或芯片材料供应，从而加剧 AI 供应链不确定性。

**标签**: `#US-China relations`, `#semiconductor export controls`, `#Nvidia`, `#AI supply chain`, `#domestic semiconductors`

---

<a id="item-finance-news-4"></a>
### [印度拟禁止私募股权机构控制多家非银行放贷机构](https://news.google.com/rss/articles/CBMizgFBVV95cUxPaUotYjFJTTF3amV0VWJmdDl3V00xWlVZdTd2VkFzek1GZ2hQbndleXV5XzMxOVdFRU03dmNWWDFXbHVtQ3daOEM3WFV1VHJoc0V0d3pYMEN5VU9vR1p5dmJwaDNBRWlVLWcxeEVSSHBrX2lSQVphdHJSdjM1b1Z6QlY0YjVmRlBtT2dWM1pocm1nclI3SXVISkpqakVJb1Bpb25LRTBEZTVNbl84WmtyRko1YWdkazJZcHFRbVBTejk0bjE3SF9JeG9KOTU5QQ?oc=5) ⭐️ 7.0/10

路透独家援引消息人士称，印度拟禁止私募股权机构控制多家非银行放贷机构（不吸收公众存款但提供贷款的金融机构）。

google\_news · Reuters · 11月12日 08:14

**「背景」** 在印度，NBFC 是不吸收公众存款但提供贷款的公司，其小微企业贷款增速快于银行；印度央行此前已因贷款定价过高等问题限制 4 家 NBFC 放贷，并调整银行向 NBFC 放贷的风险权重要求。

**「影响」** 据路透引述消息人士，若印度央行最终落实限制私募股权控股多家非银贷款机构的规定，相关股权架构和交易安排可能被迫调整，以缓解共同所有权带来的金融传染风险。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://theprint.in/india/indian-non-bank-lenders-to-tweak-funding-mix-after-rbi-relaxes-banks-lending-norms/2543049/">Indian non - bank lenders to tweak funding mix after RBI relaxes...</a></li>
<li><a href="https://indianexpress.com/article/business/banking-and-finance/excessive-pricing-rbi-bars-4-nbfcs-from-giving-loans-9625901/">‘Excessive pricing’: RBI bars 4 NBFCs from... - The Indian Express</a></li>
<li><a href="https://www.linkedin.com/posts/debarya-dey-03aa67256_non-bank-lenders-lap-up-opportunity-to-activity-7330798176506916864-4ef3">Non - bank finance companies lend more to MSMEs | LinkedIn</a></li>
<li><a href="https://www.reuters.com/legal/government/india-ban-private-equity-firms-controlling-multiple-non-bank-lenders-sources-say-2026-11-12/">India to ban private equity firms from controlling multiple ...</a></li>
<li><a href="https://www.etnownews.com/markets/rbi-new-rules-private-equity-firms-multiple-nbfcs-ownership-restrictions-article-156498245">RBI may bar private equity firms from controlling multiple ...</a></li>
<li><a href="https://tradersunion.com/news/regulators/show/4208705-india-curbs-private-equity-nbfcs/">India plans curbs on private equity control of multiple non ...</a></li>

</ul>
</details>

**标签**: `#India`, `#private equity`, `#non-bank lenders`, `#financial regulation`, `#Reuters`

---

<a id="item-finance-news-5"></a>
### [UForce 完成 7 亿美元融资，估值 60 亿美元](https://news.google.com/rss/articles/CBMi2wFBVV95cUxQZGJabUpkZzBWRWE3UG0xTTMtbGRSWnpwbVNjR09FZHMtR2JqSThHS1djUWtSMlZCdm9LR3ZubGZBTnVTQkYzaXYwMi11dHh1VXREdFl4UkV3b0hRZ2dSN1BDeTczSndZdHVscy11OVlPUVhHbk82TEhpbDBSVklQcmF2LWJrengxNllxTlZ1YmtFTko5WXduenp2enFVdnpCTmhhVzlOaUxIeWhJMUVpUGxLMjBfUllEdnVhaHBnc1FYRGRoVk95SGVpU21COXBoaThwdzlCYml1cGc?oc=5) ⭐️ 7.0/10

据路透社报道，乌克兰创立的无人机初创公司 UForce 完成 7 亿美元融资，估值为 60 亿美元。

google\_news · Reuters · 11月12日 10:44

**「背景」** UForce 是一家乌克兰创立的无人机企业；本轮融资由 Valor Equity Partners 与英国国家财富基金共同牵头，并有美国—乌克兰重建投资基金参与，反映投资者对经战场验证的自主武器系统关注度上升。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/business/aerospace-defense/ukraine-founded-drone-startup-uforce-secures-700-million-funding-round-6-billion-2026-11-12/">Ukraine-founded drone startup UForce secures $700 million ...</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/uforce-defense-tech-drones-warfare-ukraine.html">Ukrainian drone maker UFORCE hits $6 billion valuation - CNBC</a></li>
<li><a href="https://www.uforce.com/news/uforce-raises-700m-at-6-billion-valuation-from-leading-tech-and-sovereign-wealth-funds-to-scale-combat-proven-defence-systems-for-ukraine-and-allied-nations">UFORCE raises $700M at $6 billion valuation from Leading Tech ...</a></li>

</ul>
</details>

**标签**: `#private funding`, `#defense technology`, `#drones`, `#Ukraine`, `#valuation`

---

<a id="item-finance-news-6"></a>
### [印度 Clean Max 拟投 53 亿美元建清洁能源 AI 算力设施](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

路透社报道，印度 Clean Max 计划投资 53 亿美元建设清洁能源设施，为人工智能算力中心供电。

google\_news · Reuters · 11月12日 13:39

**「背景」** 清洁能源一般来自风能、太阳能等可再生能源；AI 算力中心需要大量稳定电力，因此这类投资常与数据中心供电和可再生能源项目绑定。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.nrdc.org/stories/renewable-energy-clean-facts">Renewable Energy Definition - Sources, Clean Alternatives</a></li>

</ul>
</details>

**标签**: `#AI computing infrastructure`, `#clean energy investment`, `#capital expenditure`, `#India markets`, `#Reuters`

---

<a id="item-finance-news-7"></a>
### [京东拟借 Ceconomy 交易拓展欧洲电子零售](https://news.google.com/rss/articles/CBMiygFBVV95cUxOWFBaanFxZDRLWkM3UWNHMHYwX181VlJINXBhMkFuZC01bzZScmgxUFdiZFV0V00tRlJiQk1LbFNfbE83TXFQUzBvZ1lqYmN4ZjBZRHpxQk5GUzc5bGhqM2tzdWdvR1RSVmd3eGQxLWR5TEZMcTRJVExDYkMtSUlDYWNMMkJ2WXlZa29EcmJ5QVo4STFsbTNvZTFDRUZGWGRWMjdLeUQySEhuLTFFYm1KTnJiLWotRDJYTUZ4Wl9GQ1dldjJkcldsZnN3?oc=5) ⭐️ 7.0/10

路透社报道，京东寻求通过一项与 Ceconomy 的交易成为欧洲线上电子产品零售的领导者。报道未披露交易条款、完成状态或财务影响。

google\_news · Reuters · 11月12日 16:41

**「背景」** 京东此前已获得欧盟对其以约 25 亿美元收购德国电子零售商 Ceconomy 的有条件批准，并目标在 11 月 12 日前完成交易。

**「影响」** 该约 25 亿美元交易完成后，京东获得 Ceconomy 渠道，并计划扩大在欧洲消费电子线上零售的存在，可能改变当地电子零售商竞争格局。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://www.reuters.com/legal/litigation/jdcom-wins-eu-approval-acquisition-ceconomy-2026-11-03/">JD.com wins EU approval for acquisition of Germany&#x27;s Ceconomy</a></li>
<li><a href="https://www.globalbankingandfinance.com/jd-com-wins-eu-approval-acquisition-ceconomy/">JD.com Secures EU Approval for $2.5B Acquisition of Ceconomy</a></li>
<li><a href="https://www.reuters.com/business/retail-consumer/jdcom-seeks-lead-europes-online-electronics-retail-with-ceconomy-deal-2026-11-12/">JD.com seeks to lead Europe&#x27;s online electronics retail with ...</a></li>
<li><a href="https://www.businessday.co.za/world/2026-11-12-jdcom-acquires-ceconomy-to-lead-europe-electronics-retail/">JD.com acquires Ceconomy to lead Europe electronics retail</a></li>

</ul>
</details>

**标签**: `#JD.com`, `#Ceconomy`, `#European electronics retail`, `#cross-border M&amp;A`, `#global technology`

---

<a id="item-finance-news-8"></a>
### [思科上调年度营收预测](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

思科因人工智能网络需求强劲上调其年度营收预测；路透社报道未披露具体上调金额或幅度。

google\_news · Reuters · 11月12日 23:18

**「背景」** 思科在公布 2027 财年首季业绩后上调全年收入指引，Reuters 称受 AI 网络需求推动；该季度业绩超预期，并被描述为逾 15 年来最强收入和盈利增长。

<details><summary>参考链接</summary>
<ul>
<li><a href="https://finance.yahoo.com/markets/stocks/articles/cisco-shares-climb-4-strong-214347073.html">Cisco shares climb 4% on strong earnings beat and raised outlook</a></li>

</ul>
</details>

**标签**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#AI infrastructure`, `#Reuters`

---