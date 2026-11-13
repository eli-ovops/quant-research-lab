# Phase032 — closed asof gate coverage

Complete past-proxy-only diagnostic; no future prices, income or API/model calls. Total goal ACTIVE.

025 closed raw hash and telemetry hash verified. All 8248 fixed anchored 1Hz sourceordinal samples after actual026 OS cut29136966188000 were included, irrespective of original state_valid. Earlier raw is causal warmup. All123491 rows scanned, no source copy/alteration. This is used historical development data, not OOS.

|Asset|Samples|Cost available/pass|Median abs10 move bps|Median necessary+5 bps|Best past cost margin bps|Dominant depth available/pass|
|---|---:|---:|---:|---:|---:|---:|
|BTC-USDT-SWAP|960|959/0|0.0351|15.0167|-11.0324|960/166|
|ETH-USDT-SWAP|960|960/0|0.0000|15.0421|-12.6321|960/89|
|SOL-USDT-SWAP|960|960/0|0.8248|15.8313|-10.8751|958/0|
|DOGE-USDT-SWAP|960|960/0|1.0698|16.0772|-10.7227|955/10|
|XRP-USDT-SWAP|960|960/0|0.0000|15.6729|-10.9999|960/0|
|SUI-USDT-SWAP|959|959/0|0.8485|15.8544|-6.5260|874/20|
|PEPE-USDT-SWAP|926|926/0|0.0000|17.3553|-7.9590|634/0|
|WIF-USDT-SWAP|820|820/0|0.0000|19.1024|-9.1879|743/0|
|BONK-USDT-SWAP|743|743/0|0.0000|21.4923|-8.2558|436/0|

No sampled asset passes past cost-room gate; all qualified branch funnels are zero. Other independent gates can pass (including received volume vs reference depth in some assets); first-reject counts do not imply later gates passed. No fresh quote/fee outcome path is evaluated here.

`results.json` contains per-field available/missing, median/p95/min/max, independent gate available/pass denominators and a declared explanatory funnel. `original_rule_funnel.json` separately follows original candidate order (capacity before pressure_choice flow gates); this presentation clarification does not change any rule or numeric field. Cooldown is not applied because independent asof coverage is not emitted-strategy event frequency.

Missing references/undefined imbalance or ratio remain null; zero received volume is an observed quantity, not invented ratio zero or proof of damaged source. Numeric proxies from a stale book/reference can be described, but freshness gates are separate and qualification requires them. Received-flow/source completeness and provider compatibility remain UNKNOWN; no model adapter invocation. Past_cost_margin is not expected future return.

Finite independent rational audit recomputed first/middle/last asof per asset (27 cases), 10s/1s quantities, observed impulse and both-side capacity/cost formulas; all pass. All group available+missing counts and total8248 reconcile. Same Owner, different arithmetic implementation, not third-party/full independent strategy replay.

Initial prefreeze path resolution failure and pre-results compressed-versus-logical hash assertion are preserved. v1 code/freeze and failure logs remain; corrected logical SHA verification and v2 freeze preceded all computed diagnostics. Original026 rule bytes unchanged. Actual route/model/effort UNKNOWN. Current job010 producer untouched and no live results read.
