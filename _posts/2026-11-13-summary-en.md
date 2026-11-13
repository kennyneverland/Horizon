---
layout: default
title: "Horizon Summary: 2026-11-13 (EN)"
date: 2026-11-13
lang: en
---

> From 121 items, 21 important content pieces were selected

---

**Technology News**
1. [NVIDIA CEO Jensen Huang Resigns Amid China and Export-Control Scrutiny](#item-tech-news-1) ⭐️ 8.0/10
2. [Rust 1.100 Stabilizes Never Type, Allocator, and Cargo Dependency Controls](#item-tech-news-2) ⭐️ 8.0/10
3. [Google Releases Gemini 4 Hydrogen for Faster Agent Workflows](#item-tech-news-3) ⭐️ 8.0/10
4. [Apple Foundation Models framework: on-device and PCC developer access](#item-tech-news-4) ⭐️ 8.0/10
5. [Anthropic IPO Reportedly Six Times Oversubscribed](#item-tech-news-5) ⭐️ 8.0/10
6. [Edge0-145B Claims Local Frontier AI at 29GB Peak Memory](#item-tech-news-6) ⭐️ 7.0/10
7. [PostgreSQL CVE-2026-6460 type-confusion primitive reportedly escalated to RCE](#item-tech-news-7) ⭐️ 7.0/10
8. [llm-gemini 0.37 and Gemini 4 Hydrogen Pricing](#item-tech-news-8) ⭐️ 7.0/10
9. [OpenAI Codex Security CLI and TypeScript SDK Released](#item-tech-news-9) ⭐️ 7.0/10
10. [Meta Open-Sources Beta Astryx Design System for React 19 and Agents](#item-tech-news-10) ⭐️ 7.0/10
11. [VulnCheck Finds Glasswing Duplicates and Withdrawals Overwhelm Maintainers](#item-tech-news-11) ⭐️ 7.0/10

**Financial News**
1. [China approves first oral GLP-1 obesity drug](#item-finance-news-1) ⭐️ 8.0/10
2. [Fed to skip October 2027 rate vote and discuss strategy](#item-finance-news-2) ⭐️ 7.0/10
3. [AI stocks trim losses after Nvidia CEO exit](#item-finance-news-3) ⭐️ 7.0/10
4. [Lawsuit seeks halt to frontier AI development](#item-finance-news-4) ⭐️ 7.0/10
5. [Clean Max Plans $5.3 Billion India AI Energy Project](#item-finance-news-5) ⭐️ 7.0/10
6. [SpaceX plans $74 billion AI campus investment](#item-finance-news-6) ⭐️ 7.0/10
7. [Cisco raises annual revenue forecast on AI networking demand](#item-finance-news-7) ⭐️ 7.0/10
8. [Applied Materials Sees Quarterly Revenue Above Estimates on AI Chip Demand](#item-finance-news-8) ⭐️ 7.0/10
9. [US opens fiscal 2027 with record $404 billion October deficit](#item-finance-news-9) ⭐️ 7.0/10
10. [US existing home sales fall to more than 16-year low](#item-finance-news-10) ⭐️ 7.0/10

---

## Technology News

<a id="item-tech-news-1"></a>
### [NVIDIA CEO Jensen Huang Resigns Amid China and Export-Control Scrutiny](https://apnews.com/article/nvidia-megaspeed-china-singapore-huang-5403f152a601cf82ce939f1d24fffa0f) ⭐️ 8.0/10

AP News reports that NVIDIA CEO Jensen Huang has resigned, with linked coverage pointing to an NVIDIA CEO-transition announcement and major media reports. The item frames the leadership change around NVIDIA’s China exposure and export-control scrutiny, but the available excerpt does not establish the precise reason, successor, or any legal finding. The event should be treated as breaking reported news rather than a settled account of wrongdoing or a completed transition plan.

hackernews · lldb · Nov 12, 13:52 · [Discussion](https://news.ycombinator.com/item?id=50467087)

**「Background」** Reuters reported that Jensen Huang stepped down after revelations of extramarital affairs, including one involving a suspected Chinese spy, plunged the company into crisis. The New York Times said the affair was reported in October 2026 and that Nvidia’s board announced an investigation in November after Huang admitted it.

**「Impact」** For NVIDIA’s enterprise, cloud, and AI-hardware customers, the resignation introduces governance uncertainty around the company’s China-related supply chain and export-control posture, making official statements on succession, compliance, and customer commitments important before relying on long-term roadmap decisions.

**「Community discussion」** Commenters split between treating the resignation as a PR or governance issue tied to unverified personal and China-tie allegations and arguing that the central concern is alleged export-control evasion; another speculative thread connects it to NVIDIA’s ambitions in open frontier models and conflicts with national-security hawks. These views are community interpretations, not established facts from the source.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/nvidia-ceo-jensen-huang-step-down-big-blow-ai-boom-2026-11-12/">Nvidia CEO Jensen Huang resigns in blow to AI boom he helped ...</a></li>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live ...</a></li>

</ul>
</details>

**Tags**: `#NVIDIA`, `#AI chips`, `#China AI industry`, `#export controls`, `#A-share catalysts`

---

<a id="item-tech-news-2"></a>
### [Rust 1.100 Stabilizes Never Type, Allocator, and Cargo Dependency Controls](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 was released on November 12, 2026, stabilizing the never type and core parts of the Allocator API. The release also changes Cargo workflows, including reporting unused dependencies; community comments describe minimum publish age settings that make the resolver ignore versions newer than a configured age unless already recorded in Cargo.lock, and cargo install using the existing lockfile by default.

hackernews · mbStavola · Nov 12, 18:39 · [Discussion](https://news.ycombinator.com/item?id=50472038)

**「Background」** Rust 1.100 stabilizes the never type and core parts of the \`Allocator\` API, features that had previously been unstable. It also changes Cargo, Rust’s package manager and build tool, which is why dependency-reporting and lockfile updates matter to Rust projects.

**「Impact」** Developers using Cargo may need to review new unused-dependency warnings and decide whether to remove stale dependencies or configure cargo::unused\_dependencies. The reported dependency cooldown and install-lockfile defaults give projects a concrete way to reduce accidental adoption of very recently published packages and make cargo install more reproducible.

**「Community discussion」** Commenters highlighted the never type, custom allocator support, dependency cooldowns, and cargo install lockfile behavior as the release’s most useful changes, while one user asked whether compile speed had improved and complained about cargo clean removing large temp files.

**Tags**: `#Rust`, `#programming languages`, `#open source`, `#developer tooling`, `#Cargo`

---

<a id="item-tech-news-3"></a>
### [Google Releases Gemini 4 Hydrogen for Faster Agent Workflows](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) ⭐️ 8.0/10

Google has released Gemini 4 Hydrogen, a model aimed at everyday coding and agent workflows, and says it is available to developers, enterprises, and general users. Google reports that it is 2.5x faster than Gemini 3.8 Flash, improves Terminal-Bench 4.1 from 18.2% to 57%, and is priced at $1.50 per million input tokens and $7.50 per million output tokens. The announcement also references an Orchestrator, but the supplied source does not provide concrete details about its availability or behavior.

hackernews · jonbaer · Nov 12, 18:52 · [Discussion](https://news.ycombinator.com/item?id=50472260)

**「Background」** Gemini 4 Hydrogen is introduced as a new entry in Google’s Gemini model family, and the announcement compares it directly to Gemini 3.8 Flash and Argon. That places it in the context of Google’s existing speed- and cost-oriented developer models rather than as a standalone new product line.

**「Impact」** For developers using Google’s coding and agent workflows, Gemini 4 Hydrogen’s disclosed $1.50 per million input tokens and $7.50 per million output tokens pricing, along with claimed speed and Terminal-Bench gains, make it a practical candidate for latency-sensitive automation. However, teams should verify current and post-January pricing and cache-billing terms before standardizing on it, because community reports mention a future price increase across Google models.

**「Community Discussion」** HN commenters focused on the naming scheme and practical concerns, with some joking about “Gemini Hydrogen” after “Carbon” and others asking how multi-model agent pipelines can work with caching. One commenter also pointed to a reported 2x price increase for Google models starting Jan 1, while another questioned whether the new models justify resubscribing to Antigravity to use remaining credits.

**Tags**: `#AI models`, `#Google Gemini`, `#AI agents`, `#inference cost`, `#developer tools`

---

<a id="item-tech-news-4"></a>
### [Apple Foundation Models framework: on-device and PCC developer access](https://developer.apple.com/foundation-models-framework/) ⭐️ 8.0/10

The item directs developers to Apple&\#x27;s Foundation Models framework, which comments describe as supporting on-device inference and Private Cloud Compute access. A comment quoting Apple&\#x27;s site says developers enrolled in the App Store Small Business Program with fewer than two million first-time App Store downloads can use Apple Foundation Models on PCC with no cloud API cost where Apple Intelligence is available, and can test PCC features via TestFlight or ad hoc distribution. One commenter refers to a 3B on-device model but notes no comparative benchmarks have been seen.

hackernews · kermatt · Nov 12, 21:13 · [Discussion](https://news.ycombinator.com/item?id=50474361)

**「Background」** Apple’s Foundation Models framework is a native Swift API that exposes the on-device model behind Apple Intelligence and lets apps use other language models that conform to the framework. It is paired with Apple’s Private Cloud Compute path for server-side Apple Foundation Models, which eligible App Store Small Business Program developers can access without cloud API costs.

**「Impact」** For eligible small App Store developers, the framework creates a concrete cost and integration decision point: they can evaluate Apple&\#x27;s Foundation Models without cloud API charges, but only if they meet the program and download thresholds and have Apple Intelligence availability.

**「Community discussion」** The discussion centered on the missing benchmark comparison between Apple&\#x27;s on-device model and similarly sized open models such as Gemma 4 E4B and Qwen 3.5 4B. Other comments pointed to practical local use, such as terminal command correction on an M1 8 GB Mac, and to adjacent Apple CoreAI/Swift tooling.

<details><summary>References</summary>
<ul>
<li><a href="https://developer.apple.com/private-cloud-compute/">Private Cloud Compute - Apple Developer</a></li>
<li><a href="https://developer.apple.com/wwdc26/guides/apple-intelligence/">WWDC26 Apple Intelligence guide - Apple Developer</a></li>
<li><a href="https://techcrunch.com/2026/06/08/apple-bets-cheaper-ai-will-woo-small-developers/">Apple bets cheaper AI will woo small developers - TechCrunch</a></li>

</ul>
</details>

**Tags**: `#Apple AI`, `#Foundation Models`, `#on-device inference`, `#Private Cloud Compute`, `#developer framework`

---

<a id="item-tech-news-5"></a>
### [Anthropic IPO Reportedly Six Times Oversubscribed](https://www.bloomberg.com/news/videos/2026-11-13/anthropic-ipo-said-to-be-six-times-oversubscribed-video) ⭐️ 8.0/10

Bloomberg reports that Anthropic&\#x27;s IPO has drawn about six times the orders for available shares, according to people familiar with the matter. The Claude AI company and its co-founders are seeking to raise as much as $64.4 billion in the IPO and $26 billion in a private placement, filings show. If completed, the combined offering would exceed SpaceX&\#x27;s IPO and become the largest listing ever.

rss · Bloomberg Technology · Nov 13, 06:54

**「Background」** An initial public offering is a company&\#x27;s first sale of shares to public investors, and oversubscription means demand for those shares exceeds the number being offered. The Bloomberg report frames Anthropic&\#x27;s planned listing against SpaceX&\#x27;s IPO, using the prior record as a benchmark for how large the new offering could become.

**Tags**: `#AI IPO`, `#Anthropic`, `#AI commercialization`, `#capital markets`, `#Claude`

---

<a id="item-tech-news-6"></a>
### [Edge0-145B Claims Local Frontier AI at 29GB Peak Memory](https://edge0.ai/blog/introducing-edge0-145b-frontier-ai-capabilities-on-your-own-computer) ⭐️ 7.0/10

Edge0-145B is presented as a 145B-parameter AI model capable of running locally with about 29GB of peak memory, using a shared-expert design in which each group of 64 experts shares two large matrices while retaining small per-expert parameters. The announcement also highlights practical tool-use demonstrations, including Blender. Because the claim comes from a vendor blog and no source content is available, the model’s novelty, measured performance, and provenance remain unverified.

hackernews · sroussey · Nov 12, 23:06 · [Discussion](https://news.ycombinator.com/item?id=50475713)

**「Background」** The item presents Edge0-145B as a 145B-parameter AI model claimed to run locally with unusually low peak memory by sharing expert weight matrices. This is relevant because large mixture-of-experts models normally store and move many expert parameters, which can make local inference memory-intensive.

**「Impact」** If the vendor’s 29GB peak-memory figure is accurate, local inference of a 145B-class model could become practical on high-end consumer laptops; however, users and developers should wait for weights, benchmarks, licensing, and provenance details before treating it as a production-ready frontier model.

**「Community discussion」** Commenters split between enthusiasm for the reported 29GB peak-memory shared-expert design and Blender tool-use demos, and skepticism that the model may be a quantized or rebranded variant of an existing system such as Qwen 3.8 Flash Next on Strata. Some also doubted whether agent-made designs are practical without substantial human cleanup.

**Tags**: `#AI models`, `#local inference`, `#MoE`, `#tool use`, `#inference efficiency`

---

<a id="item-tech-news-7"></a>
### [PostgreSQL CVE-2026-6460 type-confusion primitive reportedly escalated to RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 7.0/10

A blog post discussed on Hacker News reports that a PostgreSQL type-confusion primitive, described as 22 years old and reported as CVE-2026-6460, was turned into remote code execution. The write-up reportedly involves creating a prepared statement on a table, changing the table, and executing the prepared statement when it should have been invalidated. Commenters dispute the severity, with several arguing the behavior is closer to authenticated privilege escalation than unauthenticated RCE.

hackernews · ozirus · Nov 12, 18:22 · [Discussion](https://news.ycombinator.com/item?id=50471761)

**「Background」** The post discusses CVE-2026-6460, a PostgreSQL type-confusion issue in which inadequate tracking of typed values during data-definition commands such as ALTER ... SET DATA TYPE can let an object creator execute arbitrary code as the database’s operating-system user. Type confusion occurs when software treats a value as one data type while its actual runtime representation is another, potentially corrupting memory or bypassing checks. The advisory also notes other DDL attack routes, such as ALTER TABLE ... ADD COLUMN followed by ROLLBACK and another ADD COLUMN.

**「Impact」** For PostgreSQL operators, the practical consequence is that database users who can create or run prepared statements and change the table involved may cross a security boundary, especially in shared or multi-tenant deployments where an account is not fully trusted.

**「Community discussion」** The most useful disagreement is whether the finding is true RCE or privilege escalation: logophobia and jmuguy say it likely requires database access and mainly threatens multi-tenant databases, while ahartmetz describes the technical path as a stale prepared statement after a table change.

<details><summary>References</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>
<li><a href="https://access.redhat.com/security/cve/cve-2026-6460">CVE-2026-6460 - Red Hat Customer Portal</a></li>

</ul>
</details>

**Tags**: `#PostgreSQL`, `#Security`, `#Database Internals`, `#Exploit Research`, `#Open Source`

---

<a id="item-tech-news-8"></a>
### [llm-gemini 0.37 and Gemini 4 Hydrogen Pricing](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

Simon Willison released llm-gemini 0.37 as Google launched Gemini 4 Hydrogen, the lowest-cost model in the Gemini 4 family. Hydrogen is priced at $1.50 per million input tokens, $0.075 for cached input, and $7.50 for output, while Gemini 4 Carbon and Argon are both $2.00/$0.10/$10.00 through November 30, 2026 and double to $4.00/$0.20/$20.00 on December 1. Google describes Argon as faster and lower token spend than Carbon at the same price, and positions Hydrogen as the new free-tier model powering AI features in Google Search. In Willison&\#x27;s generated pelican comparison, Hydrogen produced visibly simpler outputs at lower reported cost and latency than Carbon and Argon across thinking levels.

rss · Simon Willison · Nov 12, 22:55

**「Background」** The item reports llm-gemini 0.37 alongside Google&\#x27;s launch of Gemini 4 Hydrogen, the lowest-cost member of the Gemini 4 family. Hydrogen is presented relative to its larger siblings, Gemini 4 Carbon and Gemini 4 Argon, whose pricing and capabilities make the new model&\#x27;s positioning harder to interpret.

**「Cost and model-selection impact」** With llm-gemini 0.37 and Google’s Gemini 4 Hydrogen launch, developers should reprice Gemini 4 workloads before Dec 1, 2026, when Carbon and Argon are scheduled to double from $2/$10 to $4/$20 per million input/output tokens. Hydrogen remains $1.50/$7.50 and is Google’s new free-tier model powering AI features in Google Search, but Simon Willison’s comparison suggests teams should test whether its lower-quality output is acceptable for routine coding and testing tasks.

**Tags**: `#Gemini`, `#LLM tooling`, `#AI pricing`, `#Inference cost`, `#Model release`

---

<a id="item-tech-news-9"></a>
### [OpenAI Codex Security CLI and TypeScript SDK Released](https://github.com/openai/codex-security) ⭐️ 7.0/10

OpenAI has published Codex Security as a CLI and TypeScript SDK for finding, validating, and fixing code vulnerabilities. The @openai/codex-security package supports repository, path, and Git diff scans, deep scans, patch generation, fix verification, and exports to SARIF, JSON, and CSV. It requires Node.js 22.13.0+ within 22.x, or Node.js 24.x or 26.x, and Python 3.10+; Python 3.10 also requires tomli. Some cybersecurity requests and protected findings are gated by Trusted Access for Cyber, while Codex Security Cloud integration is optional and account-dependent.

rss · GitHub Trending - Daily · Nov 13, 09:14

**「Background」** Codex Security extends OpenAI&\#x27;s Codex coding-agent workflows with a dedicated security plugin, CLI, and TypeScript SDK for repository scanning, finding validation, and patch generation. The package is distributed as @openai/codex-security and can run locally, in terminals, or in CI.

**「Impact」** Development and security teams can integrate Codex Security scans, validation, patch generation, and SARIF/JSON/CSV exports into CI or TypeScript automation, but adoption requires Node.js 22.13+ or 24/26, Python 3.10+, an OpenAI/Codex API key or login, and Trusted Access for some cyber requests.

**Tags**: `#openai`, `#ai-coding-tools`, `#developer-security`, `#typescript`, `#github-trending`

---

<a id="item-tech-news-10"></a>
### [Meta Open-Sources Beta Astryx Design System for React 19 and Agents](https://github.com/meta/astryx) ⭐️ 7.0/10

Meta has open-sourced Astryx, a beta design system for React 19+ built with StyleX and distributed as @astryxdesign/core with a CLI, themes, templates, and dark mode. Meta says Astryx grew from internal use and ships 150+ accessible components, with styling overrides possible through className using Tailwind, CSS modules, or plain CSS. The source also notes that experimental lab components are not published to npm, while chart-related packages are currently available only under a canary dist-tag.

rss · GitHub Trending - Daily · Nov 13, 09:14

**「Background」** Astryx is a design system, meaning it packages reusable UI components, theming, and styling conventions so teams can build web interfaces consistently. It is built on React 19 and StyleX, so adopting it requires a React-based frontend stack and uses StyleX for the underlying styling approach.

**「Impact」** Frontend teams already on React 19 can evaluate Astryx as a typed component system without adopting a required build plugin or being locked into StyleX, but its beta status and incomplete stable chart packages mean teams should test it before production use and watch for API changes.

**Tags**: `#open-source`, `#AI agents`, `#design systems`, `#React`, `#Meta`

---

<a id="item-tech-news-11"></a>
### [VulnCheck Finds Glasswing Duplicates and Withdrawals Overwhelm Maintainers](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

A VulnCheck analysis of Anthropic&\#x27;s Project Glasswing, launched April 7, says its 37,966 reported AI-found vulnerabilities have produced only 7,349 public findings and 217 marked fixed. It counts 1,654 duplicates and 419 withdrawals, and questions Glasswing&\#x27;s claimed 94.2% true-positive rate because withdrawn or duplicate findings exceed confirmed fixes. The analysis argues the project has shifted triage burden onto open-source maintainers rather than delivering confirmed fixes.

rss · LWN.net · Nov 12, 16:26

**「Background」** VulnCheck&\#x27;s analysis examines Anthropic&\#x27;s Project Glasswing, an AI-driven vulnerability-discovery program launched on April 7, by comparing reported findings against public, fixed, duplicate, and withdrawn statuses.

**「Impact」** For open-source maintainers and security teams, the reported duplicate and withdrawal backlog means Glasswing findings may require independent validation before CVE triage, and the low confirmed-fix rate reduces immediate remediation value despite the large volume of reports.

**Tags**: `#AI-security`, `#vulnerability-discovery`, `#open-source-maintainers`, `#Anthropic-Glasswing`, `#security-triage`

---

## Financial News

<a id="item-finance-news-1"></a>
### [China approves first oral GLP-1 obesity drug](https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/) ⭐️ 8.0/10

China approved Eli Lilly’s orforglipron, an oral GLP-1 weight-loss drug, on Nov. 12, 2026, making it the first oral GLP-1 obesity treatment approved in China for adults with obesity or overweight and at least one weight-related condition.

telegram · zaihuapd · Nov 12, 10:09

**「Background」** China is the world&\#x27;s second-largest market for obesity drugs, and GLP-1 treatments have mainly been weekly injections, making an oral GLP-1—a class of appetite-reducing drugs—a new, daily option for weight management.

**「Impact」** The approval introduces a once-daily oral option that will compete with once-weekly injectables from Novo Nordisk, Pfizer and Innovent in China’s obesity-drug market, though price and launch timing were not announced.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/">Eli Lilly becomes first drugmaker to have a GLP-1 weight-loss ...</a></li>
<li><a href="https://www.globaltimes.cn/page/202611/1374192.shtml">China approves first oral GLP-1 weight-loss drug - Global Times</a></li>

</ul>
</details>

**Tags**: `#China healthcare regulation`, `#GLP-1 obesity drugs`, `#Eli Lilly`, `#China biotech competition`, `#pharmaceutical market`

---

<a id="item-finance-news-2"></a>
### [Fed to skip October 2027 rate vote and discuss strategy](https://www.cnbc.com/2026/11/12/in-policy-switch-fed-says-its-october-2027-meeting-will-not-see-a-vote-on-interest-rates.html) ⭐️ 7.0/10

The Federal Reserve’s rate-setting committee will not vote on interest rates at its Oct. 26-27, 2027 meeting, using that session instead for broad monetary-policy strategy discussion. The change leaves seven voting meetings in 2027 and moves the final meeting to November from December.

rss · CNBC Finance · Nov 12, 19:05

**「Background」** The Fed usually holds eight meetings a year at which policymakers vote on rates, but Chair Kevin Warsh has been streamlining communication by shortening statements and adding strategy-only sessions. His revised schedule will keep seven voting meetings in 2027, make October a nonvoting strategy session, and expand nonvoting meetings to two in 2028.

**「Impact」** For markets, it removes one regular rate decision and post-meeting statement in October 2027, shifting the year-end policy signal to November.

<details><summary>References</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-06/fed-s-new-fomc-schedule-turns-back-the-clock-for-strategy-sessions">Fed’s New FOMC Schedule Turns Back the Clock for ‘Strategy ...</a></li>
<li><a href="https://economictimes.indiatimes.com/markets/us-stocks/news/us-fed-sets-new-meeting-schedule-for-2027-as-foretold-by-chairman-kevin-warsh/articleshow/135781878.cms">US Fed sets new meeting schedule for 2027, as foretold by ...</a></li>

</ul>
</details>

**Tags**: `#Federal Reserve`, `#monetary policy`, `#FOMC schedule`, `#market communication`, `#Kevin Warsh`

---

<a id="item-finance-news-3"></a>
### [AI stocks trim losses after Nvidia CEO exit](https://news.google.com/rss/articles/CBMiuwFBVV95cUxOTDc4NU9Ycko1b01GTVdRT1lMVzJWaEhrLS1OSU92el9GTTRMSEhyTW5VbThOZEhoVGNCbHNBU19EZS1UUlNiTW0wVU41RUdBVkJpQlNRazBvaHJFQ2VnT2FJU183NE9ub1RKQU5wMFp6N1luX3lrMFZubFVIaHJ0TWhZRVkyUzhJVjBsaDRlMEpKNUFLeWtITVhLRVhqOERFMzh0azNJeVlqVzI0ZUowcnV4Z3VYMUdXcFY0?oc=5) ⭐️ 7.0/10

Reuters reported that AI stocks trimmed losses as investors assessed the fallout from Nvidia&\#x27;s CEO exit, but the item gave no figures, policy change, or details of the departure.

google\_news · Reuters · Nov 12, 20:57

**「Background」** Nvidia CEO Jensen Huang&\#x27;s departure rattled the AI trade, pushing AI-linked stocks and broader indexes lower before investors pared some of the losses.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/global-ai-stocks-sink-nvidia-crisis-deepens-sector-selloff-2026-11-12/">AI stocks pare losses as investors assess fallout of Nvidia ...</a></li>
<li><a href="https://www.kitco.com/news/off-the-wire/2026-11-12/sp-500-nasdaq-fall-nvidia-ceos-exit-rattles-ai-stocks">S&amp;P 500, Nasdaq fall as Nvidia CEO&#x27;s exit rattles AI stocks</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI stocks`, `#CEO exit`, `#market reaction`, `#AI supply chain`

---

<a id="item-finance-news-4"></a>
### [Lawsuit seeks halt to frontier AI development](https://news.google.com/rss/articles/CBMivwFBVV95cUxPWTR4ak5BdnRmV3hzYTZOcVhBYklWU01YRmtLak03b2hmeC1PMTd5blRQWUkxR2Q1ZXZWRC0xNkNxVDVoN2VOdTVlX1hFMXgwS1Y5TW1fUGt4NThQaEhRVFdna1YxUDhLTnBYUFJ6WTlFajlLM1BZTTRwNk5sWFMydkZtMlJNUnU4MWlDcUN6QmNtVHdUT1pLNXd6QXc4QVk0WmMtM1JxWU5XVC1PUGRIMVJNY2wzN1Z1d2N6WWJkbw?oc=5) ⭐️ 7.0/10

Reuters reports that OpenAI, Google, and Anthropic are facing a lawsuit seeking to halt frontier AI development. The article does not disclose the filing details, court, legal basis, or likelihood of success.

google\_news · Reuters · Nov 12, 20:35

**「Background」** Frontier AI is the label used for the most advanced large AI systems, so the lawsuit asks a court to halt work on those systems.

**Tags**: `#AI regulation`, `#frontier AI litigation`, `#AI industry economics`, `#OpenAI`, `#Anthropic`

---

<a id="item-finance-news-5"></a>
### [Clean Max Plans $5.3 Billion India AI Energy Project](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

India&\#x27;s Clean Max has announced a planned $5.3 billion clean-energy investment to power an AI computing facility, according to Reuters.

google\_news · Reuters · Nov 12, 13:39

**「Background」** AI computing facilities need large, reliable power supplies, so Clean Max&\#x27;s plan links new clean-energy capacity to electricity demand from data-center operations.

**Tags**: `#AI infrastructure`, `#clean energy`, `#capital expenditure`, `#India`, `#data centers`

---

<a id="item-finance-news-6"></a>
### [SpaceX plans $74 billion AI campus investment](https://news.google.com/rss/articles/CBMixAFBVV95cUxQdlQwLUxxTENmenRpSFFXVlNUeVkzeURtNWxCZ1RuVEQwdENKV0g3MndreVZsZFYwVGtpT3Q3SDJZU0pHTGI1WFFYWERreFJmbzVjaUtOR2NjUURRMTVHNVlKdGE0VkdRVzRvekpIcHdmRGdOV2kwRXVmbWl1blRIV1VKSjQ4c19FSVFTUWZNM2ptQ0ZaMW96a2UyTFphWjNsSnc3ZmJZdWhHNWpiS19hTDhYSk9vNkpkeng1N3prZ1Y3b1lI?oc=5) ⭐️ 7.0/10

Reuters reports that SpaceX plans more than $74 billion of investment in AI campuses in Texas and Arizona.

google\_news · Reuters · Nov 12, 20:23

**「Background」** SpaceX said it plans to invest more than $74 billion in two AI supercomputing campuses, one at its Starbase site in Texas and one in Cochise County, Arizona.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/media-telecom/spacex-invest-over-74-billion-supercompute-facilities-texas-arizona-2026-11-12/">SpaceX plans over $74 billion investment in Texas, Arizona AI ...</a></li>
<li><a href="https://finance.yahoo.com/technology/ai/articles/spacex-commits-74b-ai-campuses-175531621.html?fr=sycsrp_catchall">SpaceX Commits $74B To New AI Campuses While Musk Eyes Hiring ...</a></li>
<li><a href="https://finance.yahoo.com/technology/ai/articles/spacex-build-74b-ai-supercomputing-222425804.html?fr=sycsrp_catchall">SpaceX to build $74B AI supercomputing facilities in Texas ...</a></li>

</ul>
</details>

**Tags**: `#SpaceX`, `#AI infrastructure`, `#capital expenditure`, `#data centers`, `#Reuters`

---

<a id="item-finance-news-7"></a>
### [Cisco raises annual revenue forecast on AI networking demand](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

Cisco raised its annual revenue forecast, citing strong demand for AI networking products, according to Reuters. The report did not provide the new revenue figure or the prior forecast.

google\_news · Reuters · Nov 12, 23:18

**「Background」** Cisco&\#x27;s latest guidance lift follows a first-quarter result that beat Wall Street estimates and builds on an earlier fiscal 2027 revenue forecast that already relied on strong demand for its AI networking gear.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/media-telecom/cisco-raises-annual-revenue-forecast-strong-ai-networking-demand-2026-11-12/">Cisco lifts annual revenue forecast on strong AI networking ...</a></li>
<li><a href="https://www.reuters.com/technology/cisco-forecasts-upbeat-annual-revenue-2026-08-12/">Cisco forecasts annual revenue above estimates on sustained ...</a></li>

</ul>
</details>

**Tags**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#technology earnings`, `#Reuters`

---

<a id="item-finance-news-8"></a>
### [Applied Materials Sees Quarterly Revenue Above Estimates on AI Chip Demand](https://news.google.com/rss/articles/CBMivgFBVV95cUxNeVJYSC1hal9odmptblkwc25YV0pZQXBaaTd0SGFyMW5tT1ZtNzZaTlN0OGFnY2I0dnI3ZmZRaXpwUThvZW5kay1tMElieklOVVZLTDFBTmtQbkpiSWpUZzlLNnZPRmlJSkxoWVZhZGlveTdzNjVsN0ZtZUVMMnk2REQtYmRHRzQwMDhNMVBYQXVQbjBpcHNNYnFWWldTbUItYV9pT1hMYkwwZi1jS0pvZXp4eHJhbHE4OEp6RW13?oc=5) ⭐️ 7.0/10

Applied Materials forecast quarterly revenue above estimates, Reuters reported, citing strong demand for AI chips.

google\_news · Reuters · Nov 12, 23:44

**「Background」** Applied Materials makes equipment used to manufacture semiconductors, so its revenue guidance reflects chipmakers&\#x27; spending plans; prior company forecasts had flagged weaker China spending from U.S. export controls while AI demand supported overall growth.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/applied-materials-forecasts-quarterly-revenue-above-estimates-strong-ai-chip-2026-11-12/">Applied Materials forecasts quarterly revenue above estimates ...</a></li>
<li><a href="https://www.reuters.com/business/applied-materials-forecasts-strong-quarterly-revenue-ai-chip-demand-2025-11-13/">Applied Materials sees weaker China spending in 2026 on ...</a></li>

</ul>
</details>

**Tags**: `#Applied Materials`, `#AI chips`, `#semiconductor equipment`, `#earnings guidance`, `#Reuters`

---

<a id="item-finance-news-9"></a>
### [US opens fiscal 2027 with record $404 billion October deficit](https://news.google.com/rss/articles/CBMiugFBVV95cUxPSDdFRmlLcWNxcWNRVHRGN05hM2dMcmpEeW1IY1gyVkM0R2NPQVpfWU1ObHZMX08xZHFFYXhGbllpTW9abFR2SGxoNUprSFdxYTR1OXF1N3d2RGRNNGRzelRRdzhSOF8tMmM2U2I3clNQR0trbDZrLWN4QlVyNXlKOTJsdXp2NU5aWUxHR3AyQndrNFc5dFhBQS1MWHdZZHQ5c0thakE1b1Y1OTdhcFNHb1U1cmlZbjNyQWc?oc=5) ⭐️ 7.0/10

Reuters reports that the US recorded a $404 billion federal budget deficit in October, the first month of fiscal 2027, a figure described as a record for the month.

google\_news · Reuters · Nov 12, 20:18

**「Background」** The US fiscal year begins in October, and the Treasury’s Monthly Treasury Statement records the government’s monthly borrowing; Reuters said October’s $404 billion deficit was 42% higher than the same month a year earlier.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/us-starts-2027-fiscal-year-with-record-october-budget-deficit-404-billion-2026-11-12/">US starts 2027 fiscal year with record October budget deficit ...</a></li>
<li><a href="https://www.crfb.org/press-releases/treasury-confirms-404-billion-deficit-first-month-fiscal-year-2027">Treasury Confirms $404 Billion Deficit for First Month of ...</a></li>

</ul>
</details>

**Tags**: `#US fiscal policy`, `#budget deficit`, `#macroeconomic data`, `#global markets`, `#Reuters`

---

<a id="item-finance-news-10"></a>
### [US existing home sales fall to more than 16-year low](https://news.google.com/rss/articles/CBMipgFBVV95cUxQTG4zNkNsSG5RNkJsdlhCZ0prLXlLTTRDZFdmLWEta3QwVGd3YXN3dnZpd0h2R3duS1N5WEx4eE85THlmT0VYZ0tlQ0ZJUlB4bHJPNnpfQnZTM0dqM1Y4eEJYNlJPX0xhNWxxYXMxMW1ncjZOclhSMmpINlVBOTJtYVc5bXJGRVhjU1lEb2ZZWkFOaXRXZDl0b3dETFFLVlA3ZUVLalpn?oc=5) ⭐️ 7.0/10

Reuters reported that US existing home sales fell in October to their lowest level in more than 16 years.

google\_news · Reuters · Nov 12, 15:03

**「Background」** The National Association of Realtors measures existing-home sales as a seasonally adjusted annual rate, and October&\#x27;s 3.75 million pace was the lowest since August 2010 because higher mortgage rates and still-elevated prices pushed buyers away.

**「Impact」** Record-high mortgage rates and rising inflation are keeping buyers out of the market, directly weighing on household home-purchasing activity.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/us-existing-home-sales-slump-more-than-16-year-low-october-2026-11-12/">Reuters | US existing home sales slump to more than 16-year ...</a></li>
<li><a href="https://www.nar.realtor/newsroom/existing-home-sales-decreased-5-5-percent-october-nar-report">Existing-Home Sales Decreased 5.5% in October, According to ...</a></li>
<li><a href="https://www.realtor.com/news/trends/existing-home-sales-data-nar-october-2026/">Home Sales Plunge to 16-Year Low as High Mortgage Rates ...</a></li>
<li><a href="https://www.theguardian.com/business/2026/nov/12/home-sales-october-low">Home sales hit 16-year low in October amid record-high ...</a></li>

</ul>
</details>

**Tags**: `#US housing`, `#existing home sales`, `#macroeconomic data`, `#interest rates`, `#consumer economy`

---