---
layout: default
title: "Horizon Summary: 2026-11-13 (EN)"
date: 2026-11-13
lang: en
---

> From 106 items, 17 important content pieces were selected

---

**Technology News**
1. [NVIDIA board removes CEO Jensen Huang amid China allegations](#item-tech-news-1) ⭐️ 8.0/10
2. [Rust 1.100.0 Stabilizes Never Type and Core Allocator API](#item-tech-news-2) ⭐️ 8.0/10
3. [PostgreSQL 22-Year-Old Type-Confusion Primitive Described as CVE-2026-6460 RCE](#item-tech-news-3) ⭐️ 8.0/10
4. [Malaysia Investigates Megaspeed Unit Over Possible AI Chip Re-Exports](#item-tech-news-4) ⭐️ 8.0/10
5. [Google Antigravity Adds Gemini 4 Hydrogen and Orchestrator Mode](#item-tech-news-5) ⭐️ 7.0/10
6. [Microsoft 365 outage disrupts email and chat for over nine hours](#item-tech-news-6) ⭐️ 7.0/10
7. [Apple Foundation Models Framework Highlights On-Device and Private Cloud Compute Access](#item-tech-news-7) ⭐️ 7.0/10
8. [Open-source effort runs 16B LLMs on sub-1GB devices](#item-tech-news-8) ⭐️ 7.0/10
9. [llm-gemini 0.37 release and Gemini 4 Hydrogen pricing](#item-tech-news-9) ⭐️ 7.0/10
10. [VulnCheck Finds Anthropic Glasswing AI Findings Mostly Unfixed and Duplicated](#item-tech-news-10) ⭐️ 7.0/10
11. [ISO Declines to Ratify C++26 Over Contracts Controversy](#item-tech-news-11) ⭐️ 7.0/10
12. [Nvidia Leadership Exit May Open AI Chip Competition](#item-tech-news-12) ⭐️ 7.0/10

**Financial News**
1. [Nvidia CEO Jensen Huang resigns](#item-finance-news-1) ⭐️ 9.0/10
2. [Nvidia CEO Resignation Raises U.S.-China Chip Control Risks](#item-finance-news-2) ⭐️ 8.0/10
3. [China Approves Eli Lilly&\#x27;s First Oral GLP-1 Weight-Loss Pill](#item-finance-news-3) ⭐️ 8.0/10
4. [Fed to skip rate vote at October 2027 meeting](#item-finance-news-4) ⭐️ 7.0/10
5. [Ukraine-founded drone startup UForce raises $700 million](#item-finance-news-5) ⭐️ 7.0/10

---

## Technology News

<a id="item-tech-news-1"></a>
### [NVIDIA board removes CEO Jensen Huang amid China allegations](https://apnews.com/article/nvidia-megaspeed-china-singapore-huang-5403f152a601cf82ce939f1d24fffa0f) ⭐️ 8.0/10

Reports linked from the Hacker News item say NVIDIA’s board removed CEO Jensen Huang after allegations of two affairs, including one with a woman suspected of spying for China. The item frames the change as tied to China export-control concerns, but the supplied source material mostly presents the allegations and removal as reported, not independently confirmed. Huang reportedly appeared broken and used phrases like “whatever” and “I don’t care” before surrendering his position.

hackernews · lldb · Nov 12, 13:52 · [Discussion](https://news.ycombinator.com/item?id=50467087)

**「Background」** Huang’s resignation followed public reports that he had extramarital affairs, including one involving a woman identified by U.S. intelligence as a suspected Chinese spy. Those revelations prompted calls in Congress for him to resign and were tied to broader scrutiny of Nvidia’s AI-chip business and export-control compliance.

**「Impact」** The reported removal introduces uncertainty for NVIDIA’s customers, investors, and partners because the company’s leadership stability is closely tied to AI compute supply and China export-control scrutiny.

**「Community discussion」** Commenters debated whether the reported ouster was primarily about personal conduct, national-security/export-control risk, or a broader strategic fight; one argued perception of leadership stability matters for the AI economy, while another said the alleged export-ban circumvention, not the affairs, was the real risk.

<details><summary>References</summary>
<ul>
<li><a href="https://www.cnbc.com/2026/11/11/nvidia-jensen-huang-congress-resign-ai-chips.html">Jensen Huang affair rocks D.C., brings calls from Congress to resign</a></li>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/13/nvidia-jensen-huang-to-testify-before-congress-live-latest-updates">Nvidia ’s Jensen Huang expected to testify before... | The Guardian</a></li>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live Updates</a></li>

</ul>
</details>

**Tags**: `#NVIDIA`, `#AI compute`, `#China export controls`, `#A-share catalysts`, `#leadership`

---

<a id="item-tech-news-2"></a>
### [Rust 1.100.0 Stabilizes Never Type and Core Allocator API](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 has been released for developers using the stable Rust toolchain. The supplied announcement lists stabilization of the never type and core parts of the Allocator API, along with Cargo reporting of unused dependencies. It does not provide performance, compatibility, or migration details beyond these release changes.

hackernews · mbStavola · Nov 12, 18:39 · [Discussion](https://news.ycombinator.com/item?id=50472038)

**「Background」** Rust releases are versioned updates to the stable compiler and standard library, with stabilization making previously experimental language or library features available without special configuration. Cargo is Rust’s package manager and build tool, so changes to Cargo affect dependency resolution, warnings, and project maintenance.

**「Impact」** For Rust developers, the release makes the never type and core Allocator API features available on stable Rust, while Cargo&\#x27;s unused-dependency reporting may surface stale dependencies during builds and require manifest cleanup.

**「Community discussion」** Commenters celebrated the release as unusually broad, pointing to features such as custom allocators, dependency cooldowns, cargo install lockfile behavior, and unused-dependency warnings. One user argued that the announcement omitted additional stabilized APIs such as bool::toggle and Box::map, while another asked whether compile times had improved and reported frequent cargo clean use.

**Tags**: `#Rust`, `#open source`, `#programming languages`, `#developer tooling`, `#software engineering`

---

<a id="item-tech-news-3"></a>
### [PostgreSQL 22-Year-Old Type-Confusion Primitive Described as CVE-2026-6460 RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 8.0/10

A security write-up describes how a 22-year-old PostgreSQL type-confusion primitive, referenced as CVE-2026-6460, was developed into a remote code execution exploit. The supplied item is the researcher&\#x27;s account, not a vendor advisory or confirmed patch release. Some commenters argue the issue may amount to privilege escalation from an authenticated database account, but the available source does not state the exact access prerequisites.

hackernews · ozirus · Nov 12, 18:22 · [Discussion](https://news.ycombinator.com/item?id=50471761)

**「Background」** The write-up centers on CVE-2026-6460, which PostgreSQL describes as a type-confusion issue after ALTER ... SET DATA TYPE that can let an object creator execute arbitrary code as the operating-system user running the database. The advisory was included in a broader PostgreSQL security release covering many CVEs, providing the patch context for the exploit research.

**「Impact」** If the remote code execution claim is correct, PostgreSQL deployments could face server compromise; however, the supplied material does not identify affected versions or exploit prerequisites.

**「Community Discussion」** Commenters debate the practical severity: several argue the exploit resembles privilege escalation from an authenticated database account, while others praise the detailed path to the zero-day.

<details><summary>References</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL : CVE - 2026 - 6460 : PostgreSQL type confusion after...</a></li>
<li><a href="https://www.phoronix.com/news/PostgreSQL-52-CVEs">PostgreSQL Sees New Releases For 52 Security... - Phoronix</a></li>

</ul>
</details>

**Tags**: `#PostgreSQL`, `#security research`, `#type confusion`, `#remote code execution`, `#database internals`

---

<a id="item-tech-news-4"></a>
### [Malaysia Investigates Megaspeed Unit Over Possible AI Chip Re-Exports](https://www.bloomberg.com/news/articles/2026-11-13/malaysia-checks-whether-chips-were-reexported-by-megaspeed-unit) ⭐️ 8.0/10

Malaysia is examining whether AI chips imported by a unit of Singapore-based Megaspeed International Pte were subsequently shipped overseas. The inquiry tightens scrutiny of Megaspeed amid a scandal that led to the resignation of Nvidia Corp.’s Jensen Huang. The provided report does not confirm that any chips were re-exported.

rss · Bloomberg Technology · Nov 13, 03:21

**「Background」** Jensen Huang resigned as Nvidia CEO after reports of two extramarital affairs, including one with an alleged Chinese spy. The scandal brought scrutiny to Megaspeed, a Singapore-based company reportedly incorporated in 2015 as Chinese video game developer 7Road International.

**「Export-control compliance risk」** The investigation creates concrete compliance risk for organizations sourcing AI chips through Megaspeed-linked Malaysian channels, because authorities are examining whether imported chips were re-exported and whether those routes allegedly bypassed export controls. Buyers should verify chip provenance, end-use, and re-export status before relying on such supply chains for AI deployments.

<details><summary>References</summary>
<ul>
<li><a href="https://www.theverge.com/ai-artificial-intelligence/1031689/jensen-huang-nvidia-ceo-resigns">Nvidia CEO Jensen Huang resigns amid spy, affair scandals</a></li>
<li><a href="https://www.zerohedge.com/political/i-dont-know-bessent-confronted-lutnick-over-why-nvidia-spy-scandal-firm-isnt-blacklisted">&quot;I Don&#x27;t Know&quot;: Bessent Confronted Lutnick Over Why Nvidia Spy...</a></li>
<li><a href="https://www.ainvest.com/news/geopolitical-risk-tech-supply-chains-megaspeed-case-global-implications-2510/">Geopolitical Risk in Tech Supply Chains: The Megaspeed Case and Its...</a></li>
<li><a href="https://www.linkedin.com/posts/rishabh-jaiswal-9b8aa1160_malaysia-to-tighten-semiconductor-regulations-activity-7309765907063418880-R0FS">Malaysia to tighten semiconductor regulations under... | LinkedIn</a></li>

</ul>
</details>

**Tags**: `#AI chips`, `#export controls`, `#supply chain`, `#Nvidia`, `#regulatory investigation`

---

<a id="item-tech-news-5"></a>
### [Google Antigravity Adds Gemini 4 Hydrogen and Orchestrator Mode](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) ⭐️ 7.0/10

Google reportedly introduced Gemini 4 Hydrogen and an Orchestrator mode in Google Antigravity, according to a Hacker News post linking to a Google Antigravity blog. Because the supplied item lacks source content, concrete details such as availability, benchmarks, pricing, compatibility, or shipped capabilities are not established. The announcement is relevant to developers working with AI agent workflows, model selection, and inference performance.

hackernews · jonbaer · Nov 12, 18:52 · [Discussion](https://news.ycombinator.com/item?id=50472260)

**「Background」** Google’s Gemini 4 family uses chemistry-themed model names, with Carbon and Argon described as large reasoning models and Hydrogen positioned as a faster, more cost-efficient option for agentic workflows. The Antigravity blog connects this model release to an Orchestrator mode intended to coordinate development tasks.

**「Impact」** For developers using Google Antigravity, the Orchestrator mode could reduce manual switching between models and effort settings if it reliably routes tasks, but its practical value depends on whether the model’s task-complexity judgments are accurate and how caching, billing, and latency behave in real agent workflows.

**「Community Discussion」** Commenters mocked the Hydrogen naming after earlier Carbon and Argon references and questioned the new model-name scheme, while others praised Orchestrator for avoiding constant manual model and effort switching. Several developers also claimed Google’s agents felt slower than alternatives such as Anthropic’s Opus or Flash-style models, and asked how multi-model pipelines handle caching and billing.

<details><summary>References</summary>
<ul>
<li><a href="https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/">Gemini 4 Hydrogen and Orchestrator | Google Antigravity Blog</a></li>
<li><a href="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/">Introducing Gemini 4 Hydrogen for Agentic Workflows</a></li>
<li><a href="https://thehype.news/gemini-4-hydrogen/">Gemini 4 Hydrogen : Benchmarks, Price and Availability</a></li>

</ul>
</details>

**Tags**: `#Gemini`, `#AI agents`, `#model releases`, `#inference performance`, `#developer tools`

---

<a id="item-tech-news-6"></a>
### [Microsoft 365 outage disrupts email and chat for over nine hours](https://status.cloud.microsoft/) ⭐️ 7.0/10

Microsoft 365 experienced a prolonged service degradation that left users unable to access email and chat services for more than nine hours, one of the company’s most severe disruptions in recent memory. Microsoft status updates said an alternative health check method had been validated on a subset of affected infrastructure, allowing some servers to return to service and prompting a broader rollout, while an automated recovery process was being prepared to detect and restart unresponsive servers. Community reports described Teams chat and meetings as partially usable while email remained down, and some users said Azure infrastructure appeared unaffected, pointing to a Microsoft 365-specific fault.

hackernews · dkpk · Nov 12, 18:20 · [Discussion](https://news.ycombinator.com/item?id=50471731)

**「Background」** Microsoft 365 is a cloud-based productivity suite that includes Outlook, Teams, and Exchange Online, so a service degradation can disrupt core business communications. During this incident, Microsoft had earlier reported restarting affected servers and said its status page was intermittently not loading. The company later said a portion of servers were returning to service.

**「Operational impact」** The outage directly disrupted Microsoft 365 email and collaboration, with Outlook and Exchange Online access failing for thousands while outage reports remained in the tens of thousands after the peak, so IT teams had to treat it as an extended enterprise incident and provide alternate communication paths rather than assuming a brief blip.

**「Community Discussion」** Users reported that email remained down for many hours while Teams chat and meetings continued to work, and some noted Azure infrastructure appeared unaffected. Other commenters argued the incident reflected wider Microsoft reliability concerns tied to AI and cloud investments, but those views were opinions, not confirmed causes.

<details><summary>References</summary>
<ul>
<li><a href="https://www.cnet.com/news-live/microsoft-outlook-outage-11-12-2026/">Is Microsoft Outlook Down? What We Know Now - CNET</a></li>
<li><a href="https://www.theguardian.com/technology/2026/nov/13/microsoft-outage-outlook-teams-word-excel-reports">Microsoft begins restoring services amid global outage ... | The Guardian</a></li>
<li><a href="https://www.youtube.com/watch?v=AHC76Eas5-s">Microsoft 365 OUTAGE : Outlook DOWN for Thousands! - YouTube</a></li>
<li><a href="https://www.usatoday.com/story/tech/2026/11/12/microsoft-down-outlook-365-outage-reports/92744582007/">Is Microsoft down? Live updates as users report Outlook, 365 issues</a></li>
<li><a href="https://mashable.com/tech/microsoft-outlook-outage-cause-revealed-nov-12-2026">Microsoft Outlook outage cause: What happened today | Mashable</a></li>

</ul>
</details>

**Tags**: `#Microsoft 365`, `#Cloud Reliability`, `#Enterprise Software`, `#Service Outage`, `#Hacker News`

---

<a id="item-tech-news-7"></a>
### [Apple Foundation Models Framework Highlights On-Device and Private Cloud Compute Access](https://developer.apple.com/foundation-models-framework/) ⭐️ 7.0/10

Apple’s Foundation Models framework documentation describes developer access to on-device AI and Private Cloud Compute \(PCC\) model execution. The supplied discussion notes that App Store Small Business Program developers with fewer than two million first-time downloads can use Apple Foundation Models on PCC with no cloud API cost, and can test PCC features via TestFlight or ad hoc distribution.

hackernews · kermatt · Nov 12, 21:13 · [Discussion](https://news.ycombinator.com/item?id=50474361)

**「Background」** The Foundation Models framework has existed since Apple Intelligence launched, originally as a Swift interface to an on-device Apple model that kept inference local. The current documentation builds on that baseline by describing Private Cloud Compute access and eligibility conditions for App Store Small Business Program developers.

**「Impact」** For eligible App Store developers, the PCC access path reduces the cost and infrastructure burden of adding AI features by avoiding separate cloud API billing, while requiring Small Business Program enrollment and first-time download limits to qualify.

**「Community discussion」** HN commenters emphasized practical developer angles: one quoted Apple’s eligibility terms for no-cost PCC access, another pointed to Apple’s CoreAI model repository for Swift-compatible open-weight models, and a user described usable terminal command suggestions on an 8GB M1.

<details><summary>References</summary>
<ul>
<li><a href="https://developer.apple.com/ios/whats-new/">What’s New - iOS - Apple Developer</a></li>
<li><a href="https://www.upendrasengar.com/blog/apples-foundation-models-framework-is">Apple &#x27;s Foundation Models Framework Is... - Upendra Sengar Blog</a></li>

</ul>
</details>

**Tags**: `#Apple AI`, `#on-device inference`, `#developer tools`, `#private cloud compute`, `#local LLMs`

---

<a id="item-tech-news-8"></a>
### [Open-source effort runs 16B LLMs on sub-1GB devices](https://github.com/hyperionaidev/smolmaxxing/) ⭐️ 7.0/10

GitHub project smolmaxxing is an open-source effort to make large language models run on small, old devices with very limited memory. Its author claims 16B models now run on an iPad Air 1st generation and a Xiaomi TV box, each with less than 1GB usable memory, at decent speeds for the hardware. The project says it is releasing kernels, results, and modified models on Hugging Face for reproduction.

hackernews · mrashad74 · Nov 12, 15:23 · [Discussion](https://news.ycombinator.com/item?id=50468888)

**「Background」** Large language models normally need substantial memory and compute to run, so edge devices and older hardware usually cannot host them directly. Projects like this rely on techniques such as smaller model variants, quantization, and optimized inference kernels to make LLMs practical on constrained devices.

**「Impact」** The documented results show 8B and 16B mixture-of-experts models running on devices with about 1 GB of RAM by loading only part of the model into memory and reading the rest from flash as needed, giving developers a concrete edge-inference path for old tablets and TV boxes. The compatibility caveat is that this depends on MoE models and flash-backed partial loading rather than general full-model inference.

**「Community discussion」** Comments include reports of LLMs running on older hardware, including a Dreamcast via Windows CE and experiments with Maxwell/Pascal GPUs, alongside claims that small local models have improved rapidly. One commenter argues that Opus and Fable can already perform this task as a one-shot prompt and that the main bottleneck is sourcing hardware and giving an agent SSH access, not the inference kernel itself.

<details><summary>References</summary>
<ul>
<li><a href="https://github.com/hyperionaidev/smolmaxxing/">GitHub - hyperionaidev/ smolmaxxing : maxxing the ability to run...</a></li>

</ul>
</details>

**Tags**: `#LLM inference`, `#edge AI`, `#open source`, `#hardware optimization`, `#small models`

---

<a id="item-tech-news-9"></a>
### [llm-gemini 0.37 release and Gemini 4 Hydrogen pricing](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

llm-gemini 0.37 is a new release from Simon Willison, published as Google launched Gemini 4 Hydrogen, the lowest-cost member of the Gemini 4 family. Hydrogen costs $1.50 input, $0.075 cached input, and $7.50 output per million tokens, while Carbon and Argon are $2.00/$0.10/$10.00 through Nov 30, 2026 and $4.00/$0.20/$20.00 from Dec 1, 2026. Willison notes the pricing is confusing because Carbon and Argon are identical in price, with Google saying Argon gives faster responses and lower token spend per turn; Hydrogen is also the new free-tier model and powers Google Search AI features.

rss · Simon Willison · Nov 12, 22:55

**「Background」** Google launched Gemini 4 Hydrogen as the lowest-cost model in the Gemini 4 family, alongside Carbon and Argon. The llm-gemini 0.37 release is tied to that model launch.

**「Impact」** For LLM users, the release and pricing make model selection date-sensitive: Willison says Hydrogen is currently only a 25% discount but will represent a 75% discount after the Dec 1 price doubling for Carbon and Argon. His small SVG pelican test shows Hydrogen producing plainer images at lower cost and time, so detailed output may still require the larger models, while cost-sensitive users also need to compare Hydrogen against Claude Haiku 5.5 and GPT-6 Luna, which he lists at $0.10/$0.50.

**Tags**: `#llm-gemini`, `#Gemini 4`, `#AI pricing`, `#inference cost`, `#model releases`

---

<a id="item-tech-news-10"></a>
### [VulnCheck Finds Anthropic Glasswing AI Findings Mostly Unfixed and Duplicated](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck analyst Patrick Garrity reported that, since Anthropic launched Project Glasswing on April 7, the company has reported 37,966 AI-found vulnerabilities but only 7,349 \(19.4%\) have been made public and 217 have been marked fixed. The analysis also counts 1,654 duplicates and 419 withdrawals, while Anthropic&\#x27;s ledger claims a 94.2% true-positive rate, up from 90.8% at launch. Garrity argues the numbers show low practical remediation and shifting triage burden onto open-source maintainers.

rss · LWN.net · Nov 12, 16:26

**「Background」** Anthropic&\#x27;s Project Glasswing is an AI vulnerability-discovery effort launched on April 7. VulnCheck&\#x27;s analysis examines the public triage ledger for its findings, where entries can be marked fixed, duplicate, withdrawn, or true positive.

**「Impact」** For open-source maintainers, the findings suggest that Glasswing may increase duplicate and withdrawn vulnerability reports rather than deliver completed fixes, so teams should treat AI-generated findings as triage candidates and verify public status, duplicates, and exploitability before allocating response effort.

**Tags**: `#AI security`, `#vulnerability triage`, `#Anthropic`, `#open source`, `#software engineering`

---

<a id="item-tech-news-11"></a>
### [ISO Declines to Ratify C++26 Over Contracts Controversy](https://lwn.net/Articles/1105400/) ⭐️ 7.0/10

On October 23, ISO declined to ratify the C++26 document presented by Working Group 21, the first time it has refused a WG21 submission. The decision was driven by controversy over the proposed contracts feature, which would add pre- and post-conditions to function signatures. The refusal leaves the future of C++26 uncertain for developers, compiler vendors, and standards users.

rss · LWN.net · Nov 12, 14:29

**「Background」** C++ standards are developed by ISO&\#x27;s Working Group 21, which integrates proposals into a draft and submits it for ratification; ISO has approved seven C++ revisions since 1998. The disputed C++26 feature, contracts, would add pre- and post-conditions to function signatures.

**「Impact」** C++ implementers and users now face an unclear path for the next standard revision, including whether contracts will remain, be revised, or be delayed before C++26 can be ratified.

**Tags**: `#C++`, `#ISO standards`, `#contracts`, `#software engineering`, `#programming languages`

---

<a id="item-tech-news-12"></a>
### [Nvidia Leadership Exit May Open AI Chip Competition](https://www.bloomberg.com/news/videos/2026-11-12/can-huang-s-exit-create-chip-competition-video) ⭐️ 7.0/10

Bloomberg reports that Jensen Huang’s departure from Nvidia is prompting analysts to consider whether rivals such as Broadcom, AMD, and Google could gain ground in the AI semiconductor market. The analysts say demand for AI computing remains strong, but Huang’s exit may encourage customers to seek alternatives and challenge Nvidia’s premium pricing. The item is an analyst discussion of potential market effects, not a confirmed shift in product capability or customer adoption.

rss · Bloomberg Technology · Nov 12, 22:54

**「Huang’s Departure」** Nvidia announced on November 12, 2026, that Jensen Huang resigned as president, chief executive officer, and board member effective immediately, ending a leadership tenure reported to span 33 years. The company did not specify the reason for the departure, while media reports linked it to personal relationship controversies and intelligence concerns.

**「Impact」** If customers respond to the leadership change by evaluating more suppliers, AI infrastructure buyers may gain leverage to negotiate pricing or diversify away from Nvidia-dominated compute stacks.

<details><summary>References</summary>
<ul>
<li><a href="https://nvidianews.nvidia.com/news/nvidia-announces-ceo-transition">NVIDIA Announces CEO Transition | NVIDIA Newsroom</a></li>
<li><a href="https://showgamer.com/en/news/9436-dzhensen-huang-ushel-iz-nvidia-kompaniya-naznachila-novogo-glavu">Jensen Huang Resigns as NVIDIA CEO After 33 Years, Kress Takes...</a></li>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live Updates</a></li>

</ul>
</details>

**Tags**: `#AI chips`, `#Nvidia`, `#semiconductor market`, `#compute infrastructure`, `#industry analysis`

---

## Financial News

<a id="item-finance-news-1"></a>
### [Nvidia CEO Jensen Huang resigns](https://news.google.com/rss/articles/CBMisAFBVV95cUxOMEFwN0FWdjB6blNtR0RZaTBWZXZDaWVwYkhXREttY2FaYVNNVC1qNEFHYm9Yd1pDODBDN2tvNzhnMTY4cmxWYTg1WVFidzFlNVFEdlZNb3IyZG1nS2FKcHAzUERhQW9EdG9oOER6YmwydXZOd0t1VHRub1BCdFdoR1V4dktlUVUydjZWeU53aVdKMGwtOGFtZmd2T3VhODF3eXhPazVtbV81b0hpUi1vcw?oc=5) ⭐️ 9.0/10

Reuters reports that Nvidia CEO Jensen Huang has resigned as president, CEO and director immediately; CFO Colette Kress has been named interim CEO while the board searches for a permanent successor.

google\_news · Reuters · Nov 12, 13:52

**「Background」** Jensen Huang had led Nvidia as its chief executive, and the company is central to the AI computing boom; according to reports, he resigned after alleged extramarital affairs, with chief financial officer Colette Kress serving as temporary CEO.

<details><summary>References</summary>
<ul>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live Updates</a></li>
<li><a href="https://edition.cnn.com/2026/11/12/tech/jensen-huang-nvidia-resigns">CFO Colette Kress to serve as interim leader after Nvidia CEO ...</a></li>
<li><a href="https://www.theguardian.com/technology/2026/nov/12/nvidia-ceo-jensen-huang-resigns">Jensen Huang resigns as Nvidia CEO after alleged... | The Guardian</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI supply chain`, `#Corporate leadership`, `#A-share themes`, `#Reuters`

---

<a id="item-finance-news-2"></a>
### [Nvidia CEO Resignation Raises U.S.-China Chip Control Risks](https://www.cnbc.com/2026/11/13/jensen-huang-nvidia-us-china-relations.html) ⭐️ 8.0/10

Nvidia CEO Jensen Huang resigned amid U.S. congressional scrutiny of reports that his alleged affair involved a woman said to have been recruited by Chinese intelligence. He agreed to testify before Congress by Nov. 26, and analysts said the episode could raise the risk of stricter semiconductor export controls.

rss · CNBC Finance · Nov 13, 02:56

**「Background」** U.S. limits on Nvidia&\#x27;s advanced chip sales to China began in 2022 and were partly eased in 2025 under a fragile trade truce. China denies the spy allegation, and it remains unclear whether sensitive information was shared.

**「Impact」** Analysts said the episode could tighten U.S. semiconductor export controls and accelerate China&\#x27;s push for domestic alternatives, affecting AI chip supply chains and Nvidia&\#x27;s China sales.

**Tags**: `#US-China relations`, `#Nvidia`, `#semiconductor export controls`, `#AI supply chain`, `#A-share semiconductors`

---

<a id="item-finance-news-3"></a>
### [China Approves Eli Lilly&\#x27;s First Oral GLP-1 Weight-Loss Pill](https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/) ⭐️ 8.0/10

Eli Lilly&\#x27;s oral GLP-1 weight-loss pill orforglipron was approved by China&\#x27;s drug regulator on Nov. 12, 2026, becoming the first oral GLP-1 weight-loss treatment approved in China for adults with obesity or overweight who have at least one weight-related condition.

telegram · zaihuapd · Nov 12, 10:09

**「Background」** Orforglipron is an oral, non-peptide, small-molecule GLP-1 receptor agonist developed by Eli Lilly and licensed from Chugai Pharmaceutical in 2018.

**「Impact」** The once-daily pill will compete with weekly injectable weight-loss drugs from Novo Nordisk, Pfizer and Innovent, though its price and launch timing were not disclosed.

<details><summary>References</summary>
<ul>
<li><a href="https://en.wikipedia.org/wiki/Orforglipron">Orforglipron - Wikipedia</a></li>

</ul>
</details>

**Tags**: `#GLP-1减重药`, `#中国药品监管`, `#肥胖症治疗`, `#医药产业链`, `#礼来`

---

<a id="item-finance-news-4"></a>
### [Fed to skip rate vote at October 2027 meeting](https://www.cnbc.com/2026/11/12/in-policy-switch-fed-says-its-october-2027-meeting-will-not-see-a-vote-on-interest-rates.html) ⭐️ 7.0/10

The Federal Reserve will not vote on interest rates at its Oct. 26-27, 2027 meeting, which the rate-setting FOMC will use to discuss broad monetary-policy strategy instead.

rss · CNBC Finance · Nov 12, 19:05

**「Context」** Chairman Kevin Warsh framed the move as part of a broader effort to reduce the Fed&\#x27;s market footprint and reshape policy communication, leaving seven voting meetings in 2027 and moving the final meeting from December to November.

**Tags**: `#Federal Reserve`, `#monetary policy`, `#market communication`, `#macro policy`, `#global markets`

---

<a id="item-finance-news-5"></a>
### [Ukraine-founded drone startup UForce raises $700 million](https://news.google.com/rss/articles/CBMi2wFBVV95cUxQZGJabUpkZzBWRWE3UG0xTTMtbGRSWnpwbVNjR09FZHMtR2JqSThHS1djUWtSMlZCdm9LR3ZubGZBTnVTQkYzaXYwMi11dHh1VXREdFl4UkV3b0hRZ2dSN1BDeTczSndZdHVscy11OVlPUVhHbk82TEhpbDBSVklQcmF2LWJrengxNllxTlZ1YmtFTko5WXduenp2enFVdnpCTmhhVzlOaUxIeWhJMUVpUGxLMjBfUllEdnVhaHBnc1FYRGRoVk95SGVpU21COXBoaThwdzlCYml1cGc?oc=5) ⭐️ 7.0/10

Reuters reports that Ukraine-founded drone startup UForce closed a $700 million funding round at a $6 billion valuation.

google\_news · Reuters · Nov 12, 10:44

**「Background」** The financing included £113m from the UK National Wealth Fund, its largest defense investment, for UForce, a Ukraine-founded maker of military drones for land, air and sea.

<details><summary>References</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/drone-startup-uforce-valued-at-6-billion-with-uk-wealth-fund-backing">Drone Startup Uforce Valued at $ 6 Billion With UK Wealth Fund ...</a></li>
<li><a href="https://www.theguardian.com/business/2026/nov/12/uk-drone-maker-ukraine-value-uforce">UK drone maker founded by Ukrainians hits £4.5bn value after...</a></li>

</ul>
</details>

**Tags**: `#drone technology`, `#defense startups`, `#venture funding`, `#Ukraine`, `#private valuations`

---