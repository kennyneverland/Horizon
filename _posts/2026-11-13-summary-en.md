---
layout: default
title: "Horizon Summary: 2026-11-13 (EN)"
date: 2026-11-13
lang: en
---

> From 128 items, 20 important content pieces were selected

---

**Technology News**
1. [Rust 1.100.0 Stabilizes Never Type, Allocators, Cargo Controls](#item-tech-news-1) ⭐️ 8.0/10
2. [PostgreSQL CVE-2026-6460 Type-Confusion to RCE Report](#item-tech-news-2) ⭐️ 8.0/10
3. [Google Reportedly Launches Gemini 4 Hydrogen for Coding and Agents](#item-tech-news-3) ⭐️ 8.0/10
4. [Apple Foundation Models framework: no cloud API cost for eligible developers](#item-tech-news-4) ⭐️ 7.0/10
5. [Open-source smolmaxxing claims 16B LLMs on sub-1GB devices](#item-tech-news-5) ⭐️ 7.0/10
6. [llm-gemini 0.37 Tracks Gemini 4 Hydrogen Pricing and Output Tradeoffs](#item-tech-news-6) ⭐️ 7.0/10
7. [VulnCheck: Glasswing findings mostly unfixed, burden maintainers](#item-tech-news-7) ⭐️ 7.0/10
8. [ISO declines to ratify C++26 over contracts feature](#item-tech-news-8) ⭐️ 7.0/10
9. [Malaysia Investigates Megaspeed Unit Over Possible AI Chip Reexports](#item-tech-news-9) ⭐️ 7.0/10
10. [Bloomberg Analysts Weigh Nvidia Leadership Change Impact](#item-tech-news-10) ⭐️ 7.0/10
11. [UMAP 0.6 adds recursive initialization and multi-core optimizers](#item-tech-news-11) ⭐️ 7.0/10
12. [Apple Details Secure Exclaves for Isolated Audio-Video Processing](#item-tech-news-12) ⭐️ 7.0/10

**Financial News**
1. [Eli Lilly’s oral weight-loss pill approved in China](#item-finance-news-1) ⭐️ 8.0/10
2. [Reuters: Nvidia CEO Jensen Huang Resigns](#item-finance-news-2) ⭐️ 8.0/10
3. [Nvidia CEO resignation raises U.S.-China chip-control risks](#item-finance-news-3) ⭐️ 7.0/10
4. [India plans ban on private equity control of multiple non-bank lenders](#item-finance-news-4) ⭐️ 7.0/10
5. [UForce raises $700 million at $6 billion valuation](#item-finance-news-5) ⭐️ 7.0/10
6. [Clean Max plans $5.3 billion clean energy investment for AI computing facility](#item-finance-news-6) ⭐️ 7.0/10
7. [JD.com seeks Europe electronics retail leadership via Ceconomy deal](#item-finance-news-7) ⭐️ 7.0/10
8. [Cisco raises annual revenue forecast on AI networking demand](#item-finance-news-8) ⭐️ 7.0/10

---

## Technology News

<a id="item-tech-news-1"></a>
### [Rust 1.100.0 Stabilizes Never Type, Allocators, Cargo Controls](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 ships stabilized language and tooling features including the never type and custom allocators, along with Cargo changes for dependency hygiene and supply-chain controls. Cargo can now warn about unused dependencies by default, and cargo install is described as using the lockfile already present in a crate tarball, making --locked a no-op. The release also introduces optional dependency cooldowns through minimum publish-age configuration, where the resolver ignores newly published versions unless they are already recorded in Cargo.lock.

hackernews · mbStavola · Nov 12, 18:39 · [Discussion](https://news.ycombinator.com/item?id=50472038)

**「Context for Rust 1.100」** Rust’s never type \`\!\` represents computations that diverge and never produce a value, while the allocator API governs custom memory allocation. The 1.100 release notes list these language features alongside Cargo changes such as unused-dependency reporting and minimum publish age.

**「Impact」** Stabilized never-type and custom allocator support makes these features available on stable Rust, while Cargo&\#x27;s default unused-dependency warnings and optional publish-age controls give maintainers practical ways to clean manifests and delay adoption of very new dependencies. The cargo install lockfile change may affect reproducibility expectations, so users should verify install behavior and dependency cooldown configuration.

**「Community Discussion」** Commenters praised the stabilized never type, custom allocators, dependency cooldowns, and Cargo unused-dependency warnings, and noted additional stabilized APIs such as bool::toggle\(\), Box::map\(\), and trimming helpers that were not highlighted in the announcement. One commenter argued that publish-age cooldowns are not a complete supply-chain fix because malicious code can remain dormant until later.

<details><summary>References</summary>
<ul>
<li><a href="https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/">Announcing Rust 1 . 100 . 0 | Rust Blog</a></li>
<li><a href="https://www.phoronix.com/news/Rust-1.100-Released">Rust 1 . 100 Released With The &quot; Never &quot; Type Finally Stable - Phoronix</a></li>
<li><a href="https://github.com/rust-lang/rust/issues/163811">Draft release notes for 1 . 100 . 0 · Issue #163811 · rust -lang/ rust · GitHub</a></li>

</ul>
</details>

**Tags**: `#Rust`, `#programming languages`, `#open source`, `#software engineering`, `#supply-chain security`

---

<a id="item-tech-news-2"></a>
### [PostgreSQL CVE-2026-6460 Type-Confusion to RCE Report](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 8.0/10

A security write-up reports CVE-2026-6460 as a PostgreSQL issue in which a 22-year-old type-confusion primitive was developed into remote code execution. The supplied source content is unavailable, so affected versions, patch availability, and the exact exploitation conditions are not independently confirmed. Commenters describe the primitive as involving PostgreSQL’s internal Datum values and their separate type identifiers, and note that the attack may require authenticated database access.

hackernews · ozirus · Nov 12, 18:22 · [Discussion](https://news.ycombinator.com/item?id=50471761)

**「Vulnerability context」** CVE-2026-6460 is a PostgreSQL type confusion vulnerability that can be triggered through DDL operations such as ALTER ... SET DATA TYPE, allowing an object creator to execute arbitrary code as the operating system user running the database. This establishes the baseline condition that the reported write-up discusses as a type-confusion primitive developed into remote code execution.

**「Impact」** PostgreSQL operators should treat the report as a security concern for environments where untrusted users can obtain database-account access, especially multi-tenant deployments, because authenticated access could be escalated to server code execution under the reported conditions. Until vendor guidance is available, restrict database-account privileges, audit access paths, and monitor for an official advisory or fixed versions.

**「Community Discussion」** The discussion debates whether this is classic RCE or primarily privilege escalation, with several commenters saying database-account access makes it more dangerous for multi-tenant systems than unauthenticated remote attackers. Other commenters value the write-up for showing the researcher’s path and PostgreSQL Datum/type-id internals.

<details><summary>References</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>

</ul>
</details>

**Tags**: `#postgresql`, `#security`, `#exploit-development`, `#database-internals`, `#open-source`

---

<a id="item-tech-news-3"></a>
### [Google Reportedly Launches Gemini 4 Hydrogen for Coding and Agents](https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/) ⭐️ 8.0/10

Google reportedly launched Gemini 4 Hydrogen, positioned for everyday programming and agentic workflows and reported available to developers, businesses, and general users. The model is priced at $1.50 per million input tokens and $7.50 per million output tokens. Google claims 2.5x speed over Gemini 3.8 Flash, with Terminal-Bench 4.1 rising from 18.2% to 57%, and says its default tier also exceeds Argon on the Artificial Analysis index. The item is a short Telegram summary of an official-looking Google blog post, so the release and benchmark details remain vendor-reported.

telegram · zaihuapd · Nov 13, 02:02

**「Background」** Google’s prior Gemini lineup included 3.8 Flash for faster everyday work and Argon as a higher-reasoning comparison point. Gemini 4 Hydrogen is presented as a new model for everyday coding and agentic workflows, with benchmark comparisons to those earlier models.

**「Impact」** For developers running coding agents, the reported $1.50/$7.50 per million token pricing and 2.5x speed claim over Gemini 3.8 Flash make Gemini 4 Hydrogen a potential lower-latency option for everyday programming and terminal-style agent tasks, subject to independent verification.

**「Community Discussion」** Commenters focused on the element-themed naming and practical agent use: some welcomed a faster Flash-class option after finding Argon and Carbon slow, while others compared the release to Anthropic’s advisor mode or GitHub’s multi-model pipeline and said they would still assign models to subagents manually because models can overestimate their own capabilities.

<details><summary>References</summary>
<ul>
<li><a href="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/">Introducing Gemini 4 Hydrogen for Agentic Workflows</a></li>
<li><a href="https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity">Gemini 4 Hydrogen and Orchestrator | Google Antigravity Blog</a></li>

</ul>
</details>

**Tags**: `#AI models`, `#Google Gemini`, `#inference pricing`, `#agentic workflows`, `#benchmarking`

---

<a id="item-tech-news-4"></a>
### [Apple Foundation Models framework: no cloud API cost for eligible developers](https://developer.apple.com/foundation-models-framework/) ⭐️ 7.0/10

Apple&\#x27;s Foundation Models framework page describes developer access to Apple Foundation Models through Private Cloud Compute, and the supplied discussion reports that eligible App Store developers can use that access with no cloud API cost. The reported eligibility conditions are enrollment in the App Store Small Business Program and fewer than two million first-time App Store downloads, with testing available via TestFlight or ad hoc distribution. Separate community comments point to Apple CoreAI open-weight model adaptations for Swift and local AI use on M1 Macs.

hackernews · kermatt · Nov 12, 21:13 · [Discussion](https://news.ycombinator.com/item?id=50474361)

**「Background」** Apple’s Foundation Models framework gives app developers access to large language models, including on-device models and server-side models run through Private Cloud Compute. Private Cloud Compute is Apple’s privacy-focused cloud execution environment, and eligible App Store Small Business Program developers with fewer than two million first-time downloads can use it for Foundation Models without cloud API cost.

**「Impact」** For eligible small App Store developers, the reported no-cloud-API-cost path through Private Cloud Compute lowers a direct inference-cost barrier for adding Apple Foundation Models, while TestFlight or ad hoc testing provides a way to validate that path before distribution. Developers comparing other vendors&\#x27; APIs or local models should still check availability, privacy, Swift/CoreAI integration, and device requirements.

**「Community discussion」** Commenters treated the eligibility rules and no cloud API cost as the main practical takeaway, while one argued that Apple&\#x27;s CoreAI open-weight Swift models are underappreciated. Others shared hands-on local AI use on an M1 8GB machine and noted that Claude already supports App Attest for iOS apps.

<details><summary>References</summary>
<ul>
<li><a href="https://developer.apple.com/private-cloud-compute/">Private Cloud Compute - Apple Developer</a></li>
<li><a href="https://developer.apple.com/documentation/foundationmodels">Foundation Models | Apple Developer Documentation</a></li>
<li><a href="https://techcrunch.com/2026/06/08/apple-bets-cheaper-ai-will-woo-small-developers/">Apple bets cheaper AI will woo small developers - TechCrunch</a></li>

</ul>
</details>

**Tags**: `#Apple AI`, `#Foundation Models`, `#Private Cloud Compute`, `#Developer Tools`, `#Local AI`

---

<a id="item-tech-news-5"></a>
### [Open-source smolmaxxing claims 16B LLMs on sub-1GB devices](https://github.com/hyperionaidev/smolmaxxing/) ⭐️ 7.0/10

An open-source Hacker News project, smolmaxxing, claims to run 16B LLMs on old or small devices with under 1GB of usable memory, including an iPad Air 1st gen and a Xiaomi TV box. The author says the effort includes custom kernels, reproducible results, and modified models published on Hugging Face. The supplied material does not include independent benchmarks, so the performance and memory claims remain author-reported.

hackernews · mrashad74 · Nov 12, 15:23 · [Discussion](https://news.ycombinator.com/item?id=50468888)

**「Background」** The project builds on local LLM inference techniques that make large weights fit in tiny RAM by using modified models, custom kernels, smarter memory use, and weight streaming. Its current targets are constrained devices such as a Xiaomi TV Box with about 1 GB usable RAM and a 2013 iPad Air with about 700 MB usable RAM.

**「Impact」** For developers evaluating edge AI, the published kernels and models provide a concrete starting point for testing sub-1GB inference, but adoption should first verify speed, memory use, and hardware compatibility on the target device because the claims are not independently measured in the source.

**「Community discussion」** Commenters split between enthusiasm and skepticism: mrashad74 reported 16B models running on iPad Air 1st gen and Xiaomi TV box, while Farmadupe2 argued that modern agents could already perform such ports because inference is mostly multiplication.

<details><summary>References</summary>
<ul>
<li><a href="https://github.com/hyperionaidev/smolmaxxing">GitHub - hyperionaidev/smolmaxxing: maxxing the ability to ...</a></li>
<li><a href="https://ai-tldr.dev/tools/smolmaxxing/">smolmaxxing GitHub: LLMs on a TV box and an old iPad | AI/TLDR</a></li>

</ul>
</details>

**Tags**: `#edge-AI`, `#LLM-inference`, `#open-source`, `#quantization`, `#hardware-efficiency`

---

<a id="item-tech-news-6"></a>
### [llm-gemini 0.37 Tracks Gemini 4 Hydrogen Pricing and Output Tradeoffs](https://simonwillison.net/2026/Nov/12/llm-gemini/) ⭐️ 7.0/10

Simon Willison&\#x27;s llm-gemini 0.37 release follows Google&\#x27;s launch of Gemini 4 Hydrogen, the lowest-cost member of the Gemini 4 family. It records Hydrogen at $1.50 per million input tokens, $0.075 per million cached input tokens, and $7.50 per million output tokens, while Carbon and Argon are $2.00/$0.10/$10.00 through Nov 30, 2026 and $4.00/$0.20/$20.00 from Dec 1. Google says Hydrogen is the new free-tier model and will power AI features in Google Search; Willison&\#x27;s pelican comparison found its outputs much simpler than Carbon and Argon despite only a 25% discount before the December price change.

rss · Simon Willison · Nov 12, 22:55

**「Background」** llm-gemini 0.37 is a release of Simon Willison’s Gemini support for LLM workflows. It arrives as Google introduces Gemini 4 Hydrogen as the low-cost model in the Gemini 4 family, alongside Carbon and Argon.

**「Impact」** The release gives llm users a concrete pricing and output-quality comparison for Gemini 4 models before Google&\#x27;s December 1 price increase. Teams considering Hydrogen as a cheaper execution model should test whether its simpler outputs are acceptable, because it remains about 15x more expensive than Claude Haiku 5.5 and GPT-6 Luna at $0.10/$0.50 per the source.

**Tags**: `#Gemini`, `#AI pricing`, `#LLM tooling`, `#inference cost`, `#Google`

---

<a id="item-tech-news-7"></a>
### [VulnCheck: Glasswing findings mostly unfixed, burden maintainers](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck analyst Patrick Garrity reports that, since Anthropic launched Project Glasswing on April 7, the project has produced 37,966 reported vulnerability findings, but only 7,349 have been made public and just 217 have been marked fixed. The analysis also says 1,654 findings have been marked duplicates and 419 withdrawn, while the project ledger claims a 94.2% true-positive rate, up from 90.8% at launch. Garrity argues that the evidence does not match the launch narrative because fixes have stalled, duplicates and withdrawals have accumulated, and triage burden has shifted onto open-source maintainers.

rss · LWN.net · Nov 12, 16:26

**「Project Glasswing context」** Project Glasswing is Anthropic&\#x27;s AI-assisted vulnerability-discovery program, launched on April 7 and reported to have produced tens of thousands of findings. VulnCheck&\#x27;s November update examines the public disposition of those findings, including fixes, duplicates, withdrawals, and the claimed true-positive rate.

**「Impact」** For open-source maintainers, the reported pattern means more work sorting large volumes of AI-generated vulnerability findings, many of which may be duplicate or withdrawn, while only a small fraction result in confirmed fixes.

**Tags**: `#AI security`, `#vulnerability management`, `#Anthropic Project Glasswing`, `#open-source maintainers`, `#software supply chain`

---

<a id="item-tech-news-8"></a>
### [ISO declines to ratify C++26 over contracts feature](https://lwn.net/Articles/1105400/) ⭐️ 7.0/10

On October 23, ISO declined to ratify the C++26 standard document submitted by Working Group 21, marking the first time it has rejected a WG21 standard document. The decision was driven by controversy around a proposed contracts feature that would add pre- and post-conditions to function signatures. The rejection leaves the future of C++26 uncertain for C++ developers and standards users.

rss · LWN.net · Nov 12, 14:29

**「Background」** C++ revisions are developed by ISO Working Group 21 and then submitted to national standards bodies for a Draft International Standard ballot, which requires a two-thirds majority to approve. Horizon&\#x27;s Nov 4 digest reported that the C++26 DIS ballot failed on October 23, 2026, with comments identifying the proposed contracts feature as the main obstacle.

**「Standardization Delay」** ISO’s refusal to ratify the C++26 document leaves the standard’s release timeline and the proposed contracts feature unresolved, so compiler vendors and library authors cannot treat pre- and post-condition syntax as a confirmed part of C++26. Projects should treat contracts as provisional and watch WG21 and ISO for a revised proposal or alternative path.

<details><summary>References</summary>
<ul>
<li><a href="https://sitem.co/public/summary/6215/c-26-dis-ballot-rejected-due-to-contracts-controversy">C++26 DIS Ballot Rejected Due to Contracts Controversy</a></li>
<li><a href="https://news.lavx.hu/article/c-26-dis-fails-in-historic-vote-contracts-dispute-stalls-standardization">C++26 DIS fails in historic vote, contracts dispute stalls ...</a></li>
<li><a href="https://open-std.org/jtc1/sc22/wg21/">ISO/IEC JTC1/SC22/ WG 21 - The C++ Standards Committee - ISOCPP</a></li>

</ul>
</details>

**Tags**: `#C++26`, `#ISO standardization`, `#contracts`, `#programming languages`, `#software engineering`

---

<a id="item-tech-news-9"></a>
### [Malaysia Investigates Megaspeed Unit Over Possible AI Chip Reexports](https://www.bloomberg.com/news/articles/2026-11-13/malaysia-checks-whether-chips-were-reexported-by-megaspeed-unit) ⭐️ 7.0/10

Malaysian authorities are examining whether a unit of Singapore-based Megaspeed International Pte reexported AI chips after importing them into Malaysia, Bloomberg reported. The scrutiny tightens around Megaspeed, which is described as central to a scandal that led to Nvidia CEO Jensen Huang’s resignation. The report does not specify the chip models, quantities, destination countries, or whether any violation has been found.

rss · Bloomberg Technology · Nov 13, 03:21

**「Background」** Megaspeed International Pte is a Singapore-based company whose unit imported AI chips into Malaysia. The investigation asks whether those chips were later reexported, a supply-chain compliance issue linked to the scandal that led to Nvidia CEO Jensen Huang&\#x27;s resignation.

**「Impact」** Companies using or supplying AI hardware through Megaspeed may face increased export-control and compliance questions, especially if reexport activity is confirmed or investigated.

**Tags**: `#AI chips`, `#export controls`, `#Nvidia`, `#supply chain`, `#regulatory investigation`

---

<a id="item-tech-news-10"></a>
### [Bloomberg Analysts Weigh Nvidia Leadership Change Impact](https://www.bloomberg.com/news/videos/2026-11-12/can-huang-s-exit-create-chip-competition-video) ⭐️ 7.0/10

Bloomberg Intelligence analysts say Jensen Huang&\#x27;s departure from Nvidia could create openings for rival AI chip vendors such as Broadcom, AMD, and Google. They note that demand for AI computing remains strong, but customers may use the leadership change to seek alternatives and push back on Nvidia&\#x27;s premium pricing. The discussion centers on whether this could pressure Nvidia&\#x27;s dominance in the AI semiconductor market.

rss · Bloomberg Technology · Nov 12, 22:54

**「Background」** Bloomberg reported on November 12, 2026, that Nvidia’s board removed Jensen Huang as CEO after reports of two affairs, including one with a woman suspected of spying for China. Nvidia named CFO Colette Kress as interim CEO while seeking a successor.

**「Impact」** The reported leadership change gives AI compute customers a concrete reason to diversify suppliers, because Broadcom, AMD, and Google are named as potential alternatives and Nvidia’s premium pricing could face pressure. Market context supports this concern: Nvidia still held about 70% AI chip share in May 2026, while AMD’s MI300X had reached roughly 10% by 2026, so buyers can increasingly compare options without assuming a single vendor is unavoidable.

<details><summary>References</summary>
<ul>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/read-the-memos-from-nvidia-chairman-and-interim-ceo-after-ouster">Nvidia Releases Leadership Memos Following CEO... - Bloomberg</a></li>
<li><a href="https://www.bloomberg.com/news/articles/2026-11-12/jensen-huang-face-of-the-ai-boom-ousted-by-nvidia-board-as-ceo">Jensen Huang Removed as Nvidia CEO Following... - Bloomberg</a></li>
<li><a href="https://www.tomshardware.com/tech-industry/semiconductors/custom-ai-asics-examined-from-broadcom-to-mtia">The custom AI ASIC state of play (May 2026) — Broadcom deals ...</a></li>
<li><a href="https://www.companieshistory.com/ai-market-share-by-company/">AI Market Share By Company Statistics 2026</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI chips`, `#semiconductor competition`, `#compute pricing`, `#China A-share AI themes`

---

<a id="item-tech-news-11"></a>
### [UMAP 0.6 adds recursive initialization and multi-core optimizers](https://www.reddit.com/r/MachineLearning/comments/1xudaah/umap_06_new_initialization_new_optimizers_and/) ⭐️ 7.0/10

UMAP 0.6 introduces a recursive initialization scheme, new optimizers, and faster nearest-neighbor search for users running large-scale dimensionality reduction. The release notes report that neighbor search is about 4x faster through PyNNDescent, that seeded runs can use every core, and that a seeded UMAP 0.5 run took 52 minutes on 3 million arXiv papers while UMAP 0.6 finished in under 5 minutes. The new initialization and hard-negative mining are said to improve million-scale quality, yielding finer cluster structure and better kNN recall, but they are currently opt-in with compatibility\_layout=False and are planned to become default in future versions.

reddit · r/MachineLearning · /u/lmcinnes · Nov 12, 13:51

**「Context」** UMAP is an open-source dimensionality-reduction library commonly used to visualize high-dimensional data in low-dimensional layouts. Earlier UMAP 0.5 workflows relied on approximate nearest-neighbor search and stochastic optimization, with initialization often based on spectral or PCA layouts and seeded runs limited to single-threaded execution.

**「Impact」** Users processing large datasets can expect substantially faster and reproducible multi-core UMAP runs, but should enable compatibility\_layout=False and validate embedding changes before adoption because the new initialization and optimizer behavior alters output.

**Tags**: `#machine-learning`, `#dimensionality-reduction`, `#open-source`, `#performance`, `#software-libraries`

---

<a id="item-tech-news-12"></a>
### [Apple Details Secure Exclaves for Isolated Audio-Video Processing](https://security.apple.com/blog/secure-exclaves/) ⭐️ 7.0/10

Apple published a security blog on November 12 describing Secure Exclaves, a hardware-backed architecture that processes audio and video in isolated secure environments. The design lets the main system and apps receive only necessary recognition results in context-aware mode, rather than raw sensor data. On iPhone 18 Pro, Apple says dedicated hardware verifies the microphone indicator’s color, brightness, and visibility before audio can enter the main system, and requires the indicator to remain visible during relevant Siri audio sessions for at least three seconds. The blog states that the architecture is used for HomeView face and voice recognition and iPhone 18 Pro privacy indicators.

telegram · zaihuapd · Nov 12, 09:13

**「Background」** HomeView is an Apple smart display with built-in privacy features, and Apple had already described using Secure Exclaves to protect camera and microphone data on it. Apple has also tied Secure Exclaves to newer S11 and A20 Pro chips, including using the isolated environment to govern privacy indicators.

**「Impact」** For iPhone 18 Pro users, the change makes microphone privacy indicators harder to spoof or hide by tying audio access to hardware-verified indicator state, reducing a class of covert recording risks.

<details><summary>References</summary>
<ul>
<li><a href="https://forums.macrumors.com/threads/apple-explains-how-homeview-keeps-camera-data-private.2494273/">Apple Explains How HomeView Keeps Camera Data Private</a></li>
<li><a href="https://www.wired.com/story/apples-homeview-tries-face-authentication-without-faceid/">Apple ’s HomeView Tries Face Authentication Without FaceID | WIRED</a></li>
<li><a href="https://www.apple.com/apple-homeview/">Apple HomeView - Apple</a></li>

</ul>
</details>

**Tags**: `#Apple`, `#security architecture`, `#privacy`, `#AI inference`, `#hardware`

---

## Financial News

<a id="item-finance-news-1"></a>
### [Eli Lilly’s oral weight-loss pill approved in China](https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/) ⭐️ 8.0/10

China’s drug regulator approved Eli Lilly’s orforglipron calcium tablets on Nov. 12, 2026, as the country’s first oral GLP-1 weight-loss drug for adults with obesity or overweight plus at least one weight-related condition. The once-daily pill will compete with weekly injectables from Novo Nordisk, Pfizer and Innovent; price and launch timing were not announced.

telegram · zaihuapd · Nov 12, 10:09

**「Background」** GLP-1 weight-loss drugs are a class of medicines for obesity or overweight, and China’s approved options have included weekly injectables from Novo Nordisk, Pfizer and Innovent. This clearance makes orforglipron the first oral GLP-1 weight-loss medicine approved in China, adding a once-daily pill alternative to injections.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/healthcare-pharmaceuticals/china-approves-eli-lillys-weight-loss-pill-orforglipron-2026-11-12/">China approves Eli Lilly’s weight loss pill orforglipron</a></li>
<li><a href="https://pharmaphorum.com/news/lilly-beats-novo-china-oral-glp-1-obesity">Lilly beats Novo to China with an oral GLP-1 for obesity</a></li>
<li><a href="https://seekingalpha.com/news/4671225-china-approves-eli-lillys-glp-1-weight-loss-pill-giving-it-lead-over-novo---report">China approves Eli Lilly&#x27;s GLP-1 weight-loss pill, giving it ...</a></li>

</ul>
</details>

**Tags**: `#GLP-1减重药`, `#医药监管审批`, `#礼来`, `#信达生物`, `#A股医药主题`

---

<a id="item-finance-news-2"></a>
### [Reuters: Nvidia CEO Jensen Huang Resigns](https://news.google.com/rss/articles/CBMisAFBVV95cUxOMEFwN0FWdjB6blNtR0RZaTBWZXZDaWVwYkhXREttY2FaYVNNVC1qNEFHYm9Yd1pDODBDN2tvNzhnMTY4cmxWYTg1WVFidzFlNVFEdlZNb3IyZG1nS2FKcHAzUERhQW9EdG9oOER6YmwydXZOd0t1VHRub1BCdFdoR1V4dktlUVUydjZWeU53aVdKMGwtOGFtZmd2T3VhODF3eXhPazVtbV81b0hpUi1vcw?oc=5) ⭐️ 8.0/10

Reuters reports that Nvidia CEO Jensen Huang has resigned, marking a leadership change at the company central to AI chip supply.

google\_news · Reuters · Nov 12, 13:52

**「Background」** Nvidia’s board named chief financial officer Colette Kress as interim CEO, while reports say Huang has agreed to appear before Congress and President Trump proposed Apple’s Tim Cook as a possible successor.

**「Impact」** The resignation puts Nvidia’s AI-chip leadership and supply chain under closer scrutiny, as Huang agreed to testify before Congress and a semiconductor analyst warned his ouster could weaken the U.S. position in the global AI race.

<details><summary>References</summary>
<ul>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/12/nvidia-ceo-jensen-huang-affairs-share-price-plunges-live-latest?page=with:block-6af53b548f08bed8cbc53c06">Nvidia turmoil continues as Jensen Huang resigns ... | The Guardian</a></li>
<li><a href="https://digg.com/tech/f9rhq5tp">Trump’s one-man Nvidia CEO shortlist: Tim Cook · Digg</a></li>
<li><a href="https://www.bbc.com/news/live/c6zjry11v8w1t">Huang agrees to appear before Congress, US lawmakers... - BBC News</a></li>
<li><a href="https://www.euronews.com/2026/11/12/nvidia-without-huang-a-significant-loss-and-puts-the-ai-boom-under-a-microscope-say-econom">Nvidia without Huang &#x27;a significant loss&#x27; and puts the AI ... | Euronew...</a></li>
<li><a href="https://www.cnbc.com/2026/11/12/nvidia-jensen-huang-ceo-live-updates.html">Nvidia CEO Jensen Huang resigns : Live updates</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#Jensen Huang`, `#CEO resignation`, `#AI supply chain`, `#semiconductor leadership`

---

<a id="item-finance-news-3"></a>
### [Nvidia CEO resignation raises U.S.-China chip-control risks](https://www.cnbc.com/2026/11/13/jensen-huang-nvidia-us-china-relations.html) ⭐️ 7.0/10

Nvidia CEO Jensen Huang resigned amid U.S. congressional scrutiny of unverified reports that China&\#x27;s Ministry of State Security recruited a businesswoman with whom he had an affair to gather information, and he agreed to testify to Congress by Nov. 26. Analysts expect the episode could push Congress to tighten rules limiting sales of advanced chips to China by year-end.

rss · CNBC Finance · Nov 13, 02:56

**「Background」** U.S. rules limiting sales of advanced Nvidia chips to China began in 2022, but the Trump administration eased many Biden-era restrictions in 2025.

**Tags**: `#US-China relations`, `#semiconductor export controls`, `#Nvidia`, `#AI supply chain`, `#domestic semiconductors`

---

<a id="item-finance-news-4"></a>
### [India plans ban on private equity control of multiple non-bank lenders](https://news.google.com/rss/articles/CBMizgFBVV95cUxPaUotYjFJTTF3amV0VWJmdDl3V00xWlVZdTd2VkFzek1GZ2hQbndleXV5XzMxOVdFRU03dmNWWDFXbHVtQ3daOEM3WFV1VHJoc0V0d3pYMEN5VU9vR1p5dmJwaDNBRWlVLWcxeEVSSHBrX2lSQVphdHJSdjM1b1Z6QlY0YjVmRlBtT2dWM1pocm1nclI3SXVISkpqakVJb1Bpb25LRTBEZTVNbl84WmtyRko1YWdkazJZcHFRbVBTejk0bjE3SF9JeG9KOTU5QQ?oc=5) ⭐️ 7.0/10

Reuters, citing sources, reports that India plans to bar private equity firms from controlling multiple non-bank lenders, a proposed rule that would limit private capital&\#x27;s ownership of lending companies outside banks.

google\_news · Reuters · Nov 12, 08:14

**「Background」** Non-bank lenders are firms that issue loans but do not take deposits like banks, and India’s Reserve Bank of India has adjusted funding rules for them and barred some lenders for excessive pricing.

**「Impact」** The proposed RBI curbs reported by Reuters would directly affect private-equity firms and non-bank lenders by restricting controlling stakes in multiple lenders, aiming to reduce financial contagion risk from common ownership.

<details><summary>References</summary>
<ul>
<li><a href="https://theprint.in/india/indian-non-bank-lenders-to-tweak-funding-mix-after-rbi-relaxes-banks-lending-norms/2543049/">Indian non - bank lenders to tweak funding mix after RBI relaxes...</a></li>
<li><a href="https://indianexpress.com/article/business/banking-and-finance/excessive-pricing-rbi-bars-4-nbfcs-from-giving-loans-9625901/">‘Excessive pricing’: RBI bars 4 NBFCs from... - The Indian Express</a></li>
<li><a href="https://www.reuters.com/legal/government/india-ban-private-equity-firms-controlling-multiple-non-bank-lenders-sources-say-2026-11-12/">India to ban private equity firms from controlling multiple ...</a></li>
<li><a href="https://www.etnownews.com/markets/rbi-new-rules-private-equity-firms-multiple-nbfcs-ownership-restrictions-article-156498245">RBI may bar private equity firms from controlling multiple ...</a></li>

</ul>
</details>

**Tags**: `#India`, `#private equity`, `#non-bank lenders`, `#financial regulation`, `#Reuters`

---

<a id="item-finance-news-5"></a>
### [UForce raises $700 million at $6 billion valuation](https://news.google.com/rss/articles/CBMi2wFBVV95cUxQZGJabUpkZzBWRWE3UG0xTTMtbGRSWnpwbVNjR09FZHMtR2JqSThHS1djUWtSMlZCdm9LR3ZubGZBTnVTQkYzaXYwMi11dHh1VXREdFl4UkV3b0hRZ2dSN1BDeTczSndZdHVscy11OVlPUVhHbk82TEhpbDBSVklQcmF2LWJrengxNllxTlZ1YmtFTko5WXduenp2enFVdnpCTmhhVzlOaUxIeWhJMUVpUGxLMjBfUllEdnVhaHBnc1FYRGRoVk95SGVpU21COXBoaThwdzlCYml1cGc?oc=5) ⭐️ 7.0/10

Reuters reported that Ukraine-founded drone startup UForce secured a $700 million funding round at a $6 billion valuation.

google\_news · Reuters · Nov 12, 10:44

**「Background」** UForce is a Ukrainian-founded drone maker that says the funding will help expand production of autonomous sea, land and air systems for Ukraine. The company said the round was co-led by Valor Equity Partners and the UK National Wealth Fund, with participation from the U.S.-Ukraine Reconstruction Investment Fund.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/aerospace-defense/ukraine-founded-drone-startup-uforce-secures-700-million-funding-round-6-billion-2026-11-12/">Ukraine-founded drone startup UForce secures $700 million ...</a></li>
<li><a href="https://www.uforce.com/news/uforce-raises-700m-at-6-billion-valuation-from-leading-tech-and-sovereign-wealth-funds-to-scale-combat-proven-defence-systems-for-ukraine-and-allied-nations">UFORCE raises $700M at $6 billion valuation from Leading Tech ...</a></li>

</ul>
</details>

**Tags**: `#private funding`, `#defense technology`, `#drones`, `#Ukraine`, `#valuation`

---

<a id="item-finance-news-6"></a>
### [Clean Max plans $5.3 billion clean energy investment for AI computing facility](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

Reuters reported that India&\#x27;s Clean Max plans a $5.3 billion clean energy investment to power an AI computing facility. The headline describes a planned investment, not completed spending, and gives no timeline or project details.

google\_news · Reuters · Nov 12, 13:39

**「Background」** AI computing facilities need large amounts of electricity, and clean energy typically refers to renewable sources such as wind and solar.

<details><summary>References</summary>
<ul>
<li><a href="https://www.nrdc.org/stories/renewable-energy-clean-facts">Renewable Energy Definition - Sources, Clean Alternatives</a></li>

</ul>
</details>

**Tags**: `#AI computing infrastructure`, `#clean energy investment`, `#capital expenditure`, `#India markets`, `#Reuters`

---

<a id="item-finance-news-7"></a>
### [JD.com seeks Europe electronics retail leadership via Ceconomy deal](https://news.google.com/rss/articles/CBMiygFBVV95cUxOWFBaanFxZDRLWkM3UWNHMHYwX181VlJINXBhMkFuZC01bzZScmgxUFdiZFV0V00tRlJiQk1LbFNfbE83TXFQUzBvZ1lqYmN4ZjBZRHpxQk5GUzc5bGhqM2tzdWdvR1RSVmd3eGQxLWR5TEZMcTRJVExDYkMtSUlDYWNMMkJ2WXlZa29EcmJ5QVo4STFsbTNvZTFDRUZGWGRWMjdLeUQySEhuLTFFYm1KTnJiLWotRDJYTUZ4Wl9GQ1dldjJkcldsZnN3?oc=5) ⭐️ 7.0/10

Reuters reports that JD.com is seeking to lead Europe’s online electronics retail through a deal with Ceconomy, but the supplied article does not provide deal terms, completion status, or financial impact.

google\_news · Reuters · Nov 12, 16:41

**「Deal context」** Reuters reported that JD.com will use the acquisition of German electronics retailer Ceconomy to become the leading online retail platform for electronics in Europe, after securing conditional EU approval for the $2.5 billion deal and targeting a November 12 close.

**「Impact」** European online electronics retailers are affected by JD.com&\#x27;s reported €2.2bn acquisition of Ceconomy, which an executive said is intended to make it the region&\#x27;s leading online electronics platform.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/jdcom-seeks-lead-europes-online-electronics-retail-with-ceconomy-deal-2026-11-12/">JD.com seeks to lead Europe&#x27;s online electronics retail with ...</a></li>
<li><a href="https://www.reuters.com/legal/litigation/jdcom-wins-eu-approval-acquisition-ceconomy-2026-11-03/">JD.com wins EU approval for acquisition of Germany&#x27;s Ceconomy</a></li>
<li><a href="https://www.globalbankingandfinance.com/jd-com-wins-eu-approval-acquisition-ceconomy/">JD.com Secures EU Approval for $2.5B Acquisition of Ceconomy</a></li>
<li><a href="https://www.ft.com/content/9f71bc39-fef2-4af1-a2e4-b2ff17aa5641?syn-25a6b1a6=1">Chinese retail giant JD.com cleared to buy Germany’s Ceconomy</a></li>
<li><a href="https://www.reuters.com/business/retail-consumer/jdcom-seeks-lead-europes-online-electronics-retail-with-ceconomy-deal-2026-11-12/">JD.com seeks to lead Europe&#x27;s online electronics retail with ...</a></li>

</ul>
</details>

**Tags**: `#JD.com`, `#Ceconomy`, `#European electronics retail`, `#cross-border M&amp;A`, `#global technology`

---

<a id="item-finance-news-8"></a>
### [Cisco raises annual revenue forecast on AI networking demand](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

Cisco raised its annual revenue forecast because demand for AI networking is strong, according to Reuters. The report did not provide the new forecast figure or its size.

google\_news · Reuters · Nov 12, 23:18

**「Background」** Cisco&\#x27;s raised annual revenue forecast follows first-quarter fiscal 2027 results that beat analyst expectations and lifted its full-year outlook, with Reuters reporting that demand for AI networking was a key driver.

<details><summary>References</summary>
<ul>
<li><a href="https://finance.yahoo.com/markets/stocks/articles/cisco-shares-climb-4-strong-214347073.html">Cisco shares climb 4% on strong earnings beat and raised outlook</a></li>

</ul>
</details>

**Tags**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#AI infrastructure`, `#Reuters`

---