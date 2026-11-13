---
layout: default
title: "Horizon Summary: 2026-11-13 (EN)"
date: 2026-11-13
lang: en
---

> From 128 items, 19 important content pieces were selected

---

**Technology News**
1. [Nvidia Board Reportedly Removes CEO Jensen Huang](#item-tech-news-1) ⭐️ 8.0/10
2. [Rust 1.100 Stabilizes Never Type and Core Allocator APIs](#item-tech-news-2) ⭐️ 8.0/10
3. [Apple Foundation Models Framework Details Private Cloud and CoreAI Access](#item-tech-news-3) ⭐️ 7.0/10
4. [Google Antigravity Adds Gemini 4 Hydrogen and Orchestrator](#item-tech-news-4) ⭐️ 7.0/10
5. [Smolmaxxing Claims 16B LLMs Run on Under-1GB Legacy Devices](#item-tech-news-5) ⭐️ 7.0/10
6. [PostgreSQL CVE-2026-6460 type-confusion claimed to enable RCE](#item-tech-news-6) ⭐️ 7.0/10
7. [VulnCheck: Anthropic Glasswing findings overwhelm maintainers](#item-tech-news-7) ⭐️ 7.0/10
8. [ISO Declines to Ratify C++26 Over Contract Controversy](#item-tech-news-8) ⭐️ 7.0/10
9. [UMAP 0.6 Adds Recursive Initialization and Faster Optimizers](#item-tech-news-9) ⭐️ 7.0/10
10. [Apple Details Secure Exclaves to Prevent Mic Indicator Spoofing](#item-tech-news-10) ⭐️ 7.0/10
11. [Research Claims Blackwell Fingerprints in Six Chinese AI Models](#item-tech-news-11) ⭐️ 7.0/10

**Financial News**
1. [AI stocks pare losses after Nvidia CEO exit report](#item-finance-news-1) ⭐️ 8.0/10
2. [Study: Large firms plan more open-weight AI use](#item-finance-news-2) ⭐️ 7.0/10
3. [Ukraine-founded drone startup UForce raises $700 million](#item-finance-news-3) ⭐️ 7.0/10
4. [Nvidia CEO Jensen Huang Resigns](#item-finance-news-4) ⭐️ 7.0/10
5. [Clean Max plans $5.3 billion India clean energy project for AI computing](#item-finance-news-5) ⭐️ 7.0/10
6. [SpaceX plans $74 billion AI campuses](#item-finance-news-6) ⭐️ 7.0/10
7. [JD.com Reported to Pursue Ceconomy Deal in Europe](#item-finance-news-7) ⭐️ 7.0/10
8. [Cisco Raises Annual Revenue Forecast on AI Networking Demand](#item-finance-news-8) ⭐️ 7.0/10

---

## Technology News

<a id="item-tech-news-1"></a>
### [Nvidia Board Reportedly Removes CEO Jensen Huang](https://apnews.com/article/nvidia-megaspeed-china-singapore-huang-5403f152a601cf82ce939f1d24fffa0f) ⭐️ 8.0/10

Reuters and The New York Times reported that Nvidia’s board removed founder and CEO Jensen Huang after allegations of two affairs, including one with a woman suspected of spying for China and another with an employee. The change ends Huang’s tenure as Nvidia’s only CEO and puts the company’s AI-hardware strategy, board succession, and China export-control posture under immediate scrutiny. Commentary from SemiAnalysis and Hacker News users argues the removal may also be tied to claims that restricted Nvidia GPUs reached China and to pressure from national-security actors, but the supplied reporting does not independently confirm those causal claims.

hackernews · lldb · Nov 12, 13:52 · [Discussion](https://news.ycombinator.com/item?id=50467087)

**「Background」** Huang founded Nvidia and had become one of the most visible leaders of the AI hardware industry, so his departure immediately reverberated through the sector. The reported affair involving a woman identified by U.S. intelligence as a Chinese spy also drew congressional attention to Nvidia’s AI chips and China-related security concerns.

**「Leadership transition under scrutiny」** Nvidia is operating under an interim CEO after the reported resignation, while U.S. lawmakers and international media scrutinize China-related allegations, creating governance and compliance uncertainty for employees, investors, and partners.

**「Community discussion」** Commenters split on whether the affair allegations were the cause or a surface issue: some said the China-linked claims made Huang a governance and perception risk, while others argued the real concern was possible export-control evasion and national-security pressure. A few speculated that the timing reflected a broader AI-policy fight or a PR campaign, but those views were not established by the supplied reporting.

<details><summary>References</summary>
<ul>
<li><a href="https://www.nytimes.com/live/2026/11/12/business/nvidia-jensen-huang-resigns">Jensen Huang Resigns as Nvidia CEO After Affairs: Live Updates</a></li>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/13/nvidia-jensen-huang-to-testify-before-congress-live-latest-updates">Nvidia ’s Jensen Huang expected to testify before... | The Guardian</a></li>
<li><a href="https://www.cnbc.com/2026/11/11/nvidia-jensen-huang-congress-resign-ai-chips.html">Jensen Huang affair rocks D.C., brings calls from Congress to resign</a></li>
<li><a href="https://www.cnbc.com/2026/11/11/nvidia-jensen-huang-congress-resign-ai-chips.html">Jensen Huang affair rocks D.C., brings calls from Congress to resign</a></li>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/12/nvidia-ceo-jensen-huang-affairs-share-price-plunges-live-latest?page=with:block-6af53b548f08bed8cbc53c06">Nvidia turmoil continues as Jensen Huang resigns ... | The Guardian</a></li>
<li><a href="https://www.bbc.com/news/live/c6zjry11v8w1t">Huang agrees to appear before Congress, US lawmakers... - BBC News</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI hardware`, `#China export controls`, `#market catalysts`, `#technology leadership`

---

<a id="item-tech-news-2"></a>
### [Rust 1.100 Stabilizes Never Type and Core Allocator APIs](https://blog.rust-lang.org/2026/11/12/Rust-1.100.0/) ⭐️ 8.0/10

Rust 1.100.0 has been released for language users and Cargo developers. The release stabilizes the never type and core parts of the Allocator API, and Cargo now reports unused dependencies. The announcement also notes additional changes beyond these highlights.

hackernews · mbStavola · Nov 12, 18:39 · [Discussion](https://news.ycombinator.com/item?id=50472038)

**「Background」** Rust 1.100 is a versioned language release, where previously unstable features can become stabilized and Cargo tooling behavior can change. Cargo is Rust’s package manager, so its resolver, lockfile handling, and dependency reporting directly affect how projects declare, install, and update crates.

**「Impact」** Rust developers can now use the never type and core allocator APIs on stable Rust, while Cargo&\#x27;s unused-dependency reporting gives maintainers a direct way to identify dependencies listed in Cargo.toml that may no longer be needed.

**「Community discussion」** Commenters highlighted the never type, custom allocators, unused-dependency warnings, and reported publish-age controls and cargo-install lockfile changes. One commenter argued that publish-age controls are not a complete supply-chain fix because malicious crates could use time-based behavior.

**Tags**: `#rust`, `#open-source`, `#programming-languages`, `#supply-chain-security`, `#developer-tools`

---

<a id="item-tech-news-3"></a>
### [Apple Foundation Models Framework Details Private Cloud and CoreAI Access](https://developer.apple.com/foundation-models-framework/) ⭐️ 7.0/10

Apple&\#x27;s Foundation Models framework page and related developer resources describe tools for building AI applications with Apple Foundation Models, Private Cloud Compute, and CoreAI model repositories. A developer comment states that App Store Small Business Program participants with fewer than two million first-time App Store downloads can use Apple Foundation Models on Private Cloud Compute with no cloud API cost where Apple Intelligence is available, and can test those features through TestFlight or ad hoc distribution. The comments also point to Apple&\#x27;s CoreAI GitHub repository as adapting open-weight models to run natively with Swift, though the supplied source provides no independent performance or cost measurements.

hackernews · kermatt · Nov 12, 21:13 · [Discussion](https://news.ycombinator.com/item?id=50474361)

**「Background」** Apple&\#x27;s Foundation Models framework is a native Swift API for integrating large language models into apps, including Apple Foundation Models running on-device or in Private Cloud Compute. It builds on Apple&\#x27;s Core AI stack, which allows AI models to run on Apple silicon. The framework also connects to Apple&\#x27;s third-generation Foundation Models, introduced for experiences such as a new Siri and intelligent app features.

**「Impact」** Developers enrolled in the App Store Small Business Program with fewer than two million first-time downloads can use Apple Foundation Models on Private Cloud Compute at no cloud API cost, while the framework also exposes on-device models and other providers through one interface. This reduces inference cost and integration overhead for adding AI features to iOS apps, especially for smaller teams that would otherwise need separate cloud inference arrangements.

**「Community Discussion」** Commenters emphasize the practical value of low-cost Private Cloud Compute access for eligible small developers and the undernoticed CoreAI Swift model repository. Others share hands-on experiences, including using local AI on an 8GB M1 Mac for terminal command assistance, while noting that existing paths such as Firebase or Claude App Attest already let iOS apps call LLMs.

<details><summary>References</summary>
<ul>
<li><a href="https://developer.apple.com/documentation/coreai">Core AI | Apple Developer Documentation</a></li>
<li><a href="https://developer.apple.com/foundation-models-framework/">Foundation Models framework - Apple Developer</a></li>
<li><a href="https://gigazine.net/gsc_news/en/20260610-apple-foundation-models/">What&#x27;s so amazing about the new AI , &#x27; Apple Foundation Models &#x27;?</a></li>
<li><a href="https://developer.apple.com/apple-intelligence/">Apple Intelligence - Apple Developer</a></li>
<li><a href="https://www.thoughtworks.com/insights/blog/generative-ai/local-inference-boundary-reflections-apple-afm3-token-economics">The local inference boundary: Reflections on Apple ’s AFM 3 and token...</a></li>
<li><a href="https://corecodify.com/blog/ai-features-in-mobile-apps-2026">AI features users now expect in mobile apps | CoreCodify</a></li>

</ul>
</details>

**Tags**: `#Apple developer tools`, `#on-device AI`, `#inference cost`, `#open-source models`, `#AI applications`

---

<a id="item-tech-news-4"></a>
### [Google Antigravity Adds Gemini 4 Hydrogen and Orchestrator](https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/) ⭐️ 7.0/10

A Google Antigravity blog item announces Gemini 4 Hydrogen and an Orchestrator mode for its coding-agent workflows, positioning the change as a model-selection and agent-orchestration update for developers. The available evidence does not specify rollout, pricing, benchmarks, or compatibility, so the release details remain vendor-described rather than independently measured.

hackernews · jonbaer · Nov 12, 18:52 · [Discussion](https://news.ycombinator.com/item?id=50472260)

**「Background」** Google Antigravity has introduced Gemini 4 Hydrogen, a model Google describes as fast and cost-efficient for agentic workflows. It also added an Orchestrator mode that pairs Hydrogen with stronger Gemini 4 models such as Carbon for longer tasks.

**「Developer impact」** For developers using Antigravity, Gemini 4 Hydrogen’s flat $1.50 per million input tokens and $7.50 per million output tokens across its 1M-token context window makes multi-agent coding workloads more cost-predictable, while launch coverage reports a 57% coding benchmark score and speed claims tied to Flash. Because the independent benchmark ranking is estimated from limited rows, teams should still measure end-to-end latency and total spend on their own repositories before making Hydrogen the default coding-agent model.

**「Community discussion」** Commenters welcomed the Orchestrator mode for removing manual model and effort switching, while others criticized the new naming and asked how multi-agent calls preserve caching and billing. Several practitioners said they still prefer choosing models per subagent because models can be overoptimistic about their own capabilities.

<details><summary>References</summary>
<ul>
<li><a href="https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity">Gemini 4 Hydrogen and Orchestrator | Google Antigravity Blog</a></li>
<li><a href="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/">Introducing Gemini 4 Hydrogen for Agentic Workflows</a></li>
<li><a href="https://benchlm.ai/models/gemini-4-hydrogen">Gemini 4 Hydrogen Benchmarks &amp; Pricing (November 2026)</a></li>
<li><a href="https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/">Introducing Gemini 4 Hydrogen for Agentic Workflows</a></li>
<li><a href="https://interestingengineering.com/ai-robotics/google-gemini-4-hydrogen-coding-benchmark">Google launches Gemini 4 Hydrogen for faster coding and agentic...</a></li>

</ul>
</details>

**Tags**: `#AI coding agents`, `#model orchestration`, `#inference cost`, `#Google Gemini`

---

<a id="item-tech-news-5"></a>
### [Smolmaxxing Claims 16B LLMs Run on Under-1GB Legacy Devices](https://github.com/hyperionaidev/smolmaxxing/) ⭐️ 7.0/10

The GitHub project smolmaxxing claims to make 16B-parameter LLMs run on old, memory-constrained devices, including an iPad Air 1st generation and a Xiaomi TV box with less than 1GB usable memory. The author says the effort is open sourced, with custom kernels, reproducible results, and modified models published on Hugging Face. The supplied evidence is a project report, not an independent benchmark, so speed, memory use, and compatibility remain unverified.

hackernews · mrashad74 · Nov 12, 15:23 · [Discussion](https://news.ycombinator.com/item?id=50468888)

**「Background」** Mixture-of-experts models activate only a subset of parameters for each token, which can reduce memory and compute relative to dense models of the same total size. The project applies that idea to very constrained hardware by keeping only part of an 8B or 16B model in about 1GB of RAM and reading the rest from flash storage as needed.

**「Impact」** Edge developers can inspect and reproduce the claimed kernels and modified 16B models, but they should treat the under-1GB memory and speed claims as unvalidated until benchmarks and quality metrics are available.

**「Community discussion」** HN commenters were mostly fascinated by the optimization trend, with one arguing that modern agents might already handle such porting tasks and another asking whether the small models are useful for practical work. Others shared related experiments, such as running an LLM on Dreamcast hardware, but no comment supplied independent measurements.

<details><summary>References</summary>
<ul>
<li><a href="https://github.com/hyperionaidev/smolmaxxing/">GitHub - hyperionaidev / smolmaxxing : maxxing the ability to run...</a></li>

</ul>
</details>

**Tags**: `#LLM inference`, `#Edge AI`, `#Open source`, `#Model optimization`, `#Compute cost`

---

<a id="item-tech-news-6"></a>
### [PostgreSQL CVE-2026-6460 type-confusion claimed to enable RCE](https://mehmetince.net/part-3-6-how-i-ended-up-turning-a-22-year-old-postgresql-type-confusion-primitive-into-rce-cve-2026-6460/) ⭐️ 7.0/10

A technical write-up linked from Hacker News claims that a 22-year-old PostgreSQL type-confusion primitive, identified in the URL as CVE-2026-6460, can be escalated into remote code execution. Because the source content is unavailable, the exact affected versions, patch status, and attack prerequisites cannot be confirmed. The claim is therefore best treated as a researcher-reported exploit chain pending independent verification.

hackernews · ozirus · Nov 12, 18:22 · [Discussion](https://news.ycombinator.com/item?id=50471761)

**「Background」** PostgreSQL’s CVE-2026-6460 advisory describes a type-confusion issue that can be triggered when DDL commands such as ALTER ... SET DATA TYPE change how stored values are interpreted. The advisory says the flaw can let an object creator execute arbitrary code as the operating-system user running the database, with other DDL paths also cited.

**「Impact」** PostgreSQL CVE-2026-6460 lets an authenticated user who can create or alter database objects execute arbitrary code as the operating-system user running the database through DDL commands such as ALTER ... SET DATA TYPE, making multi-tenant and hosted database deployments a concrete privilege-escalation risk. Affected versions are PostgreSQL before 18.7, 17.12, 16.16, 15.20, and 14.25, so operators should patch or upgrade and restrict object-definition privileges where possible.

**「Community discussion」** Commenters debated whether the result is true remote code execution or primarily privilege escalation, with several arguing that it likely requires authenticated database access and is most relevant to multi-tenant environments. Another commenter focused on PostgreSQL’s internal Datum representation as a risky code pattern, while others praised the write-up’s detail.

<details><summary>References</summary>
<ul>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>
<li><a href="https://www.postgresql.org/support/security/CVE-2026-6460/">PostgreSQL: CVE-2026-6460: PostgreSQL type confusion after ...</a></li>
<li><a href="https://access.redhat.com/security/cve/cve-2026-6460">CVE-2026-6460 - Red Hat Customer Portal</a></li>
<li><a href="https://app.opencve.io/cve/CVE-2026-6460">CVE-2026-6460 - Vulnerability Details - OpenCVE</a></li>

</ul>
</details>

**Tags**: `#postgresql`, `#security-exploits`, `#database-internals`, `#rce`, `#open-source`

---

<a id="item-tech-news-7"></a>
### [VulnCheck: Anthropic Glasswing findings overwhelm maintainers](https://lwn.net/Articles/1107173/) ⭐️ 7.0/10

VulnCheck&\#x27;s Patrick Garrity analyzed Anthropic&\#x27;s Project Glasswing since its April 7 launch and reported 37,966 findings, of which 7,349 \(19.4%\) are public and only 217 are fixed. He also counted 1,654 duplicates \(4.4%\) and 419 withdrawals, more than seven times as many duplicates as fixes, while the project&\#x27;s ledger claims a 94.2% true-positive rate, up from 90.8% at launch. Garrity argues that the reported data does not match the launch narrative and that the triage burden is shifting to the open-source maintainers Glasswing promised to help.

rss · LWN.net · Nov 12, 16:26

**「Background」** Project Glasswing is Anthropic&\#x27;s AI vulnerability-discovery project, launched on April 7. VulnCheck&\#x27;s November update evaluates the project&\#x27;s reported findings against triage outcomes, including public disclosures, fixes, duplicate reports, and withdrawals.

**「Impact」** For open-source maintainers and security triage teams, the reported pattern means large AI-generated finding volumes may increase manual deduplication, withdrawal review, and fix-validation work rather than reduce it, so Glasswing output should be treated as a triage queue rather than as confirmed, prioritized vulnerabilities.

**Tags**: `#AI security`, `#vulnerability discovery`, `#open source maintenance`, `#security triage`, `#Anthropic`

---

<a id="item-tech-news-8"></a>
### [ISO Declines to Ratify C++26 Over Contract Controversy](https://lwn.net/Articles/1105400/) ⭐️ 7.0/10

ISO declined to ratify the C++26 document submitted by Working Group 21 on October 23, the first such rejection in the standard&\#x27;s history. The decision leaves C++26&\#x27;s future uncertain and is tied to controversy over the proposed contracts feature, which would add pre- and post-conditions to function signatures. The source does not indicate whether WG21 will revise the document or seek a new vote.

rss · LWN.net · Nov 12, 14:29

**「Background」** C++ standards are produced by ISO Working Group 21, which integrates language proposals into a document for ratification by national bodies. The disputed C++26 feature, contracts, would add pre- and post-conditions to function declarations and was added after years of debate.

**「C++26 adoption uncertainty」** Because C++26&\#x27;s ISO DIS ballot missed both required vote thresholds and contracts are the probable cause, the standard&\#x27;s publication schedule is in limbo until WG21&\#x27;s next meeting in Brazil. Compiler vendors, library authors, and projects planning around C++26 contracts therefore cannot treat the feature as stable or schedule their implementations around a confirmed C++26 release.

<details><summary>References</summary>
<ul>
<li><a href="https://news.lavx.hu/article/c-26-fails-national-body-ballot-over-contracts-dispute">C++26 fails national body ballot over Contracts dispute ...</a></li>
<li><a href="https://news.lavx.hu/article/c-26-fails-iso-draft-ballot-over-contracts-fight">C++26 Fails ISO Draft Ballot Over Contracts Fight | LavX News</a></li>

</ul>
</details>

**Tags**: `#C++ standards`, `#C++26`, `#ISO`, `#language design`, `#software engineering`

---

<a id="item-tech-news-9"></a>
### [UMAP 0.6 Adds Recursive Initialization and Faster Optimizers](https://www.reddit.com/r/MachineLearning/comments/1xudaah/umap_06_new_initialization_new_optimizers_and/) ⭐️ 7.0/10

UMAP 0.6, announced by maintainer lmcinnes, adds a recursive UMAP-based initialization, new optimizers with hard-negative mining, and faster nearest-neighbor search. The release is available via pip install -U umap-learn and conda-forge, and the maintainer reports that a 3 million arXiv paper run finishes in under 5 minutes, with neighbor search about 4x faster and a seeded UMAP 0.5 comparison taking 52 minutes single-threaded. The new initialization and optimizers are currently opt-in through compatibility\_layout=False because they change output.

reddit · r/MachineLearning · /u/lmcinnes · Nov 12, 13:51

**「Background」** UMAP is a dimensionality reduction library that relies on nearest-neighbor graph construction. PyNNDescent is the related nearest-neighbor search package used for that step, and it also has a 0.6.0 release.

**「Impact」** Users working with million-scale embeddings can enable compatibility\_layout=False to test faster runs and finer cluster detail, but should expect layout changes and pin or revalidate downstream visualizations before the new defaults arrive.

<details><summary>References</summary>
<ul>
<li><a href="https://github.com/lmcinnes/umap">GitHub - lmcinnes / umap : Uniform Manifold Approximation and...</a></li>
<li><a href="https://newreleases.io/project/github/lmcinnes/pynndescent/release/release-0.6.0">lmcinnes / pynndescent release - 0 . 6 .0 on GitHub</a></li>

</ul>
</details>

**Tags**: `#UMAP`, `#dimensionality reduction`, `#open-source ML library`, `#large-scale performance`, `#software release`

---

<a id="item-tech-news-10"></a>
### [Apple Details Secure Exclaves to Prevent Mic Indicator Spoofing](https://security.apple.com/blog/secure-exclaves/) ⭐️ 7.0/10

Apple described a new Secure Exclaves architecture that isolates audio and video processing in a separate secure environment, so the main system and apps in environment-aware mode receive only the necessary recognition results instead of raw data. Apple said the architecture is already used in HomeView face and voice recognition and in the iPhone 18 Pro privacy indicator. On iPhone 18 Pro, dedicated hardware is described as checking the microphone indicator’s color, brightness, and visibility before audio can reach the main system, and Siri audio sessions must keep the indicator visible for at least three seconds in total to prevent it from being hidden or spoofed.

telegram · zaihuapd · Nov 12, 09:13

**「Background」** Apple’s privacy indicators for microphones and cameras have traditionally relied on software-enforced rules and visible system UI, which could in principle be obscured, delayed, or spoofed by compromised software. Secure Exclaves is a hardware-isolated processing environment that lets sensitive audio and video data be analyzed without exposing the raw streams to the main operating system or apps.

**「Impact」** For iPhone 18 Pro users, the microphone privacy indicator becomes harder to hide or fake because the system is described as requiring hardware verification before audio enters the main OS. For apps and developers, Apple’s environment-aware model means some audio/video features may depend on the isolated recognition path rather than direct access to raw microphone or camera data.

**Tags**: `#Apple`, `#security architecture`, `#privacy`, `#hardware`, `#audio-video`

---

<a id="item-tech-news-11"></a>
### [Research Claims Blackwell Fingerprints in Six Chinese AI Models](https://unemploymentlabs.com/checkpoint-forensics) ⭐️ 7.0/10

Unemployment Labs claims that public model-weight analysis of six Chinese AI models from DeepSeek, Moonshot AI, MiniMax, and Ant Group shows initialization patterns consistent with NVIDIA Blackwell hardware. The analysis says DeepSeek-V4-Flash matched on B300 systems and Kimi K3 matched closely on GB200, and estimates that five models&\#x27; final training runs may have used about 12,000 Blackwell GPUs. The finding remains a single-source research claim, not an independently confirmed hardware audit.

telegram · zaihuapd · Nov 13, 02:42

**「Background」** The claim rests on model-weight forensics: because NVIDIA Blackwell-class GPUs have a distinctive compute layout, researchers can inspect public checkpoints for initialization patterns that resemble that hardware. Unemployment Labs says six models from four Chinese labs show such Blackwell-class fingerprints.

**「Impact」** If validated, the method would give researchers, auditors, and export-control teams a way to infer training hardware from public weights, but the claim that Blackwell chips participated in training and the 12,000-GPU estimate remain unconfirmed.

<details><summary>References</summary>
<ul>
<li><a href="https://unemploymentlabs.com/checkpoint-forensics">Top Chinese Frontier AI Models Carry the Fingerprint of...</a></li>

</ul>
</details>

**Tags**: `#China AI`, `#NVIDIA Blackwell`, `#model weights`, `#AI training compute`, `#GPU supply`

---

## Financial News

<a id="item-finance-news-1"></a>
### [AI stocks pare losses after Nvidia CEO exit report](https://news.google.com/rss/articles/CBMiuwFBVV95cUxOTDc4NU9Ycko1b01GTVdRT1lMVzJWaEhrLS1OSU92el9GTTRMSEhyTW5VbThOZEhoVGNCbHNBU19EZS1UUlNiTW0wVU41RUdBVkJpQlNRazBvaHJFQ2VnT2FJU183NE9ub1RKQU5wMFp6N1luX3lrMFZubFVIaHJ0TWhZRVkyUzhJVjBsaDRlMEpKNUFLeWtITVhLRVhqOERFMzh0azNJeVlqVzI0ZUowcnV4Z3VYMUdXcFY0?oc=5) ⭐️ 8.0/10

Reuters reported that AI stocks pared losses as investors assessed fallout from Nvidia CEO&\#x27;s exit, but the item provided no figures or further confirmation.

google\_news · Reuters · Nov 12, 20:57

**「Background」** AI-linked stocks had fallen after investors weighed concerns about leadership transition and sector stability following the departure of Nvidia CEO Jensen Huang.

**「Impact」** Nvidia&\#x27;s leadership exit is prompting investors and AI supply-chain businesses to reassess confidence in a key chip supplier, with some Chinese AI firms reportedly racing to secure GPU shipments.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/global-ai-stocks-sink-nvidia-crisis-deepens-sector-selloff-2026-11-12/">AI stocks pare losses as investors assess fallout of Nvidia ...</a></li>
<li><a href="https://www.globalbankingandfinance.com/global-ai-stocks-sink-nvidia-crisis-deepens-sector-selloff/">Nvidia CEO Exit Sends AI Stocks Lower Amid Market Uncertainty</a></li>
<li><a href="https://wccftech.com/jensen-huang-resigns-nvidia-ceo-colette-kress-interim/">Jensen Huang Steps Down As NVIDIA CEO , As Company Thanks Him...</a></li>
<li><a href="https://www.theguardian.com/technology/live/2026/nov/12/nvidia-ceo-jensen-huang-affairs-share-price-plunges-live-latest?page=with:block-6af53b548f08bed8cbc53c06">Nvidia turmoil continues as Jensen Huang resigns ... | The Guardian</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI stocks`, `#leadership change`, `#market reaction`, `#semiconductors`

---

<a id="item-finance-news-2"></a>
### [Study: Large firms plan more open-weight AI use](https://news.google.com/rss/articles/CBMitAFBVV95cUxOYWVBOHhodjNxVmZ6Q05XeEJBOFlHNUFzTjRyMVBUMEtoOEgwRWJKT0dqWlU0RGo2ZmZFNm5nZ0ZYSXJydEZfbTJyUmxCQmc1OEhvMmlBc1N0aUJNZXFjb2FFM2Y3N0ZoQzN2bEZKcEU4N3pUeWxiYWhwT1kzUHdLTkwzSUJyZXhpSUxQck1RUzUzQ1JNa2EzV0hURFl6V3VsRDR5eUl1SzBVczN1WV9BTkU3cno?oc=5) ⭐️ 7.0/10

Reuters reports a study finding that most large firms plan to use more open-weight AI models—software whose learned parameters can be freely used or modified—to control spending.

google\_news · Reuters · Nov 12, 09:04

**「Background」** Open-weight AI models are AI systems whose trained parameters are released for broader use, allowing firms to run or adapt them on their own infrastructure and potentially reduce spending on paid proprietary services.

**Tags**: `#AI adoption`, `#enterprise AI costs`, `#open-weight models`, `#Reuters`, `#market research`

---

<a id="item-finance-news-3"></a>
### [Ukraine-founded drone startup UForce raises $700 million](https://news.google.com/rss/articles/CBMi2wFBVV95cUxQZGJabUpkZzBWRWE3UG0xTTMtbGRSWnpwbVNjR09FZHMtR2JqSThHS1djUWtSMlZCdm9LR3ZubGZBTnVTQkYzaXYwMi11dHh1VXREdFl4UkV3b0hRZ2dSN1BDeTczSndZdHVscy11OVlPUVhHbk82TEhpbDBSVklQcmF2LWJrengxNllxTlZ1YmtFTko5WXduenp2enFVdnpCTmhhVzlOaUxIeWhJMUVpUGxLMjBfUllEdnVhaHBnc1FYRGRoVk95SGVpU21COXBoaThwdzlCYml1cGc?oc=5) ⭐️ 7.0/10

Reuters reported that Ukraine-founded drone startup UForce secured a $700 million funding round at a $6 billion valuation.

google\_news · Reuters · Nov 12, 10:44

**「Background」** UForce is a Ukraine-founded military drone maker, described as a UK drone company, that builds unmanned systems for land, air and sea. Its chief executive said bookings more than doubled over the past year, and the UK national wealth fund invested £113m, making it one of the UK&\#x27;s fastest-growing unicorns, or startups valued above $1bn.

**「Impact」** The funding includes £113m from the UK’s national wealth fund, helping UForce become one of the UK’s fastest-growing unicorns as a maker of military drones for land, air and sea.

<details><summary>References</summary>
<ul>
<li><a href="https://www.cnbc.com/2026/11/12/uforce-defense-tech-drones-warfare-ukraine.html">Ukrainian drone maker UFORCE hits $ 6 billion valuation</a></li>
<li><a href="https://www.theguardian.com/business/2026/nov/12/uk-drone-maker-ukraine-value-uforce">UK drone maker founded by Ukrainians hits £4.5bn value after raising...</a></li>
<li><a href="https://www.theguardian.com/business/2026/nov/12/uk-drone-maker-ukraine-value-uforce">UK drone maker founded by Ukrainians hits £4.5bn value after raising...</a></li>

</ul>
</details>

**Tags**: `#drone startup`, `#defense technology`, `#private funding`, `#valuation`, `#Ukraine`

---

<a id="item-finance-news-4"></a>
### [Nvidia CEO Jensen Huang Resigns](https://news.google.com/rss/articles/CBMisAFBVV95cUxOMEFwN0FWdjB6blNtR0RZaTBWZXZDaWVwYkhXREttY2FaYVNNVC1qNEFHYm9Yd1pDODBDN2tvNzhnMTY4cmxWYTg1WVFidzFlNVFEdlZNb3IyZG1nS2FKcHAzUERhQW9EdG9oOER6YmwydXZOd0t1VHRub1BCdFdoR1V4dktlUVUydjZWeU53aVdKMGwtOGFtZmd2T3VhODF3eXhPazVtbV81b0hpUi1vcw?oc=5) ⭐️ 7.0/10

Reuters reported that Nvidia CEO Jensen Huang resigned; the headline called it a blow to the AI boom he helped foster, but the supplied item gave no further details.

google\_news · Reuters · Nov 12, 13:52

**「Background」** Huang’s resignation followed reports of his extramarital affairs, including one involving a suspected Chinese spy, and a US Senate Banking Committee Republican’s call for him to step down.

**「Market impact」** Nvidia shares fell 10% in pre-market trading, pressuring AI-linked US tech stocks as investors grappled with leadership uncertainty just before Anthropic&\#x27;s planned public offering.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/retail-consumer/nvidia-ceo-jensen-huang-step-down-big-blow-ai-boom-2026-11-12/">Nvidia CEO Jensen Huang resigns in blow to AI boom he helped ...</a></li>
<li><a href="https://www.reuters.com/world/china/senior-republican-us-senate-banking-panel-calls-nvidia-ceo-huang-resign-2026-11-11/">Senior Republican on US Senate banking panel calls on Nvidia ...</a></li>
<li><a href="https://apnews.com/article/nvidia-jensen-huang-resigns-ceo-affairs-314714d463cf578cbb0dbd49de903107">What we know after Jensen Huang resigns as Nvidia&#x27;s CEO</a></li>
<li><a href="https://www.ft.com/content/b4a0f3d9-f075-47ea-9a85-77cdade9a06f?syn-25a6b1a6=1">Nvidia live: Jensen Huang resigns as chief executive after affair...</a></li>

</ul>
</details>

**Tags**: `#Nvidia`, `#AI supply chain`, `#leadership change`, `#semiconductors`, `#market risk`

---

<a id="item-finance-news-5"></a>
### [Clean Max plans $5.3 billion India clean energy project for AI computing](https://news.google.com/rss/articles/CBMixwFBVV95cUxPbUd5azlyc2VuWEFpbXhjNFBHM0I1SGRVRld4QVJHdUpxcHNaYlppRXFpRGZZdHlMWVR2TVAtbTd5bnV6WV9DNHliaWlteTM2S0xaYjBJT3BCODhrck9uNWVnVXJEcEZWZWNvbXZfUDkyNzB1a1IxYzduM2tIRFlIa0lod1FXbUNzTUozbHdSdjhnV3NqdURJYzk1WGd4TURSM0F6SmlTM2VyajNJWlphQ3VYdzctckxJX1p1aWIzUmp2S2hwRVQw?oc=5) ⭐️ 7.0/10

Reuters reports that India&\#x27;s Clean Max plans a $5.3 billion clean energy investment to power an AI computing facility.

google\_news · Reuters · Nov 12, 13:39

**「Background」** Clean Max&\#x27;s plan is described as a proposed $5.3 billion clean-energy investment to power an AI computing facility, which needs large, reliable electricity; clean energy generally refers to sources such as wind and solar.

**「Impact」** The planned wind-solar-and-storage complex would expand clean-energy infrastructure in Andhra Pradesh while supplying power for AI computing, reinforcing CleanMax’s role as a commercial and industrial renewable energy provider.

<details><summary>References</summary>
<ul>
<li><a href="https://www.nrdc.org/stories/renewable-energy-clean-facts">Renewable Energy Definition - Sources, Clean Alternatives</a></li>
<li><a href="https://www.reuters.com/business/energy/indias-clean-max-plans-53-billion-clean-energy-investment-power-ai-computing-2026-11-12/">India&#x27;s Clean Max plans $5.3 billion clean energy investment ...</a></li>
<li><a href="https://economictimes.indiatimes.com/industry/energy/power/cleanmax-to-invest-rs-50000-crore-in-ai-compute-renewable-energy-projects-in-andhra-pradesh/articleshow/135788341.cms">CleanMax to invest Rs 50,000 crore in AI compute, renewable ...</a></li>

</ul>
</details>

**Tags**: `#AI infrastructure`, `#clean energy`, `#capital expenditure`, `#data centers`, `#India`

---

<a id="item-finance-news-6"></a>
### [SpaceX plans $74 billion AI campuses](https://news.google.com/rss/articles/CBMixAFBVV95cUxQdlQwLUxxTENmenRpSFFXVlNUeVkzeURtNWxCZ1RuVEQwdENKV0g3MndreVZsZFYwVGtpT3Q3SDJZU0pHTGI1WFFYWERreFJmbzVjaUtOR2NjUURRMTVHNVlKdGE0VkdRVzRvekpIcHdmRGdOV2kwRXVmbWl1blRIV1VKSjQ4c19FSVFTUWZNM2ptQ0ZaMW96a2UyTFphWjNsSnc3ZmJZdWhHNWpiS19hTDhYSk9vNkpkeng1N3prZ1Y3b1lI?oc=5) ⭐️ 7.0/10

Reuters reported that SpaceX plans more than $74 billion of investment in AI campuses in Texas and Arizona.

google\_news · Reuters · Nov 12, 20:23

**「Context」** SpaceX, a rocket and satellite company, is planning large AI data-center campuses, with Reuters saying the effort spans two sites: its Starbase rocket facility in Texas and Cochise County, Arizona.

<details><summary>References</summary>
<ul>
<li><a href="https://www.reuters.com/business/media-telecom/spacex-invest-over-74-billion-supercompute-facilities-texas-arizona-2026-11-12/">SpaceX plans over $74 billion investment in Texas, Arizona AI ...</a></li>

</ul>
</details>

**Tags**: `#AI infrastructure`, `#capital expenditure`, `#SpaceX`, `#data centers`, `#global tech`

---

<a id="item-finance-news-7"></a>
### [JD.com Reported to Pursue Ceconomy Deal in Europe](https://news.google.com/rss/articles/CBMiygFBVV95cUxOWFBaanFxZDRLWkM3UWNHMHYwX181VlJINXBhMkFuZC01bzZScmgxUFdiZFV0V00tRlJiQk1LbFNfbE83TXFQUzBvZ1lqYmN4ZjBZRHpxQk5GUzc5bGhqM2tzdWdvR1RSVmd3eGQxLWR5TEZMcTRJVExDYkMtSUlDYWNMMkJ2WXlZa29EcmJ5QVo4STFsbTNvZTFDRUZGWGRWMjdLeUQySEhuLTFFYm1KTnJiLWotRDJYTUZ4Wl9GQ1dldjJkcldsZnN3?oc=5) ⭐️ 7.0/10

JD.com is reported to be seeking a deal with Ceconomy to strengthen its position in Europe&\#x27;s online electronics retail market, according to Reuters.

google\_news · Reuters · Nov 12, 16:41

**「Background」** Ceconomy is a German-listed electronics retailer, and Reuters reported that EU regulators opened a full-scale investigation into JD.com’s reported $2.5 billion bid over possible Chinese subsidies.

<details><summary>References</summary>
<ul>
<li><a href="https://ecmsource.com/jd-com-ceconomy-eu-foreign-subsidies-investigation-may-2026/">EU Opens FSR Probe Into JD . com &#x27;s $2.5B Ceconomy Bid - Equity...</a></li>
<li><a href="https://finance.yahoo.com/economy/policy/articles/jd-coms-ceconomy-deal-faces-095226384.html">JD . com &#x27;s Ceconomy deal involves Chinese subsidies, EU regulators...</a></li>

</ul>
</details>

**Tags**: `#JD.com`, `#Ceconomy`, `#cross-border acquisition`, `#e-commerce`, `#electronics retail`

---

<a id="item-finance-news-8"></a>
### [Cisco Raises Annual Revenue Forecast on AI Networking Demand](https://news.google.com/rss/articles/CBMiwAFBVV95cUxPcDgteG5IeXZjU1k1UDdhbFkyZlVCaHI1d0pPdGp2elFReVRRclN6dWhTM2NuSUk3cGdUSnRRU2c4aWpCcS14blFsN3hLTTNCSktQbXpTUVgxRjVJV1R1YldHdEVYMXJvVHg3TzJiOXhEM0owM08ySlI1bmNkMG5GQXhnQl9iVExNWlN1Z0ZweFk3YldGWDltNFpnekdDZWpVcTJ3QTFlUUxNWXlLX0NjLUhvTjRtNzlrYnlXdXJiTmc?oc=5) ⭐️ 7.0/10

Reuters reports that Cisco increased its annual revenue forecast because of strong demand for AI networking. The supplied headline does not state the new forecast, prior baseline, or specific period.

google\_news · Reuters · Nov 12, 23:18

**「Background」** Cisco&\#x27;s raised full-year revenue forecast follows a first-quarter fiscal 2027 report that beat analyst expectations and marked its strongest revenue and earnings growth in more than 15 years.

<details><summary>References</summary>
<ul>
<li><a href="https://finance.yahoo.com/markets/stocks/articles/cisco-shares-climb-4-strong-214347073.html">Cisco shares climb 4% on strong earnings beat and raised outlook</a></li>

</ul>
</details>

**Tags**: `#Cisco`, `#AI networking`, `#revenue guidance`, `#Reuters`, `#technology`

---