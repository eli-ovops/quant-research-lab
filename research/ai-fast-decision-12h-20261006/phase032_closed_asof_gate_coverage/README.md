# Phase032 current v3: fresh-dependent asof coverage

SEALED; only past received proxies, no future quotes/income/model calls. 8248 fixed anchored1Hz post026-cut samples, no original state_valid filtering; 123491 raw rows scanned. Actual code/protocol/rule hashes verified in driver before computation; logical raw SHA and telemetry SHA verified. Source025 already used, developmental diagnostic, not OOS.

|Asset|All samples|Fresh cost-margin available/pass|Median abs10 bps|Median necessary+5 bps|Best past margin bps|Depth ratio available/pass|
|---|---:|---:|---:|---:|---:|---:|
|BTC-USDT-SWAP|960|858/0|0.0117|15.0167|-11.0324|900/153|
|ETH-USDT-SWAP|960|911/0|0.0000|15.0421|-12.6321|929/81|
|SOL-USDT-SWAP|960|911/0|0.8248|15.8313|-11.7015|925/0|
|DOGE-USDT-SWAP|960|900/0|0.0000|16.0772|-10.7236|905/9|
|XRP-USDT-SWAP|960|877/0|0.0000|15.6729|-10.9999|890/0|
|SUI-USDT-SWAP|959|867/0|0.8485|15.8544|-6.5260|802/19|
|PEPE-USDT-SWAP|926|645/0|0.0000|17.3553|-7.9590|446/0|
|WIF-USDT-SWAP|820|409/0|0.0000|19.1024|-9.1879|393/0|
|BONK-USDT-SWAP|743|272/0|0.0000|21.4923|-8.4563|158/0|

6650 samples have valid fresh current/reference and both-side capacity cost-margin inputs; none meets abs10>=necessary+5bps. Remaining1598 cost-margin inputs are unknown, not failed income. Both original sequential branch funnels are zero, not zero-profit strategies.

Main impulse10 requires current and ref10 fresh; current necessary cost requires current fresh and full entry/reverse depth; past margin requires both. Reference depth ratio requires fresh10s ref and nonzero known direction/volume. Missing/stale metrics are null. Single-gate pass denominators are their own available inputs, separate from sequential all-gate survival. Zero received quantity remains an observed zero, never invented zero imbalance/ratio or evidence of broken source.

Original candidate-order funnel is in original_rule_funnel.json (capacity before flow gates). results.json also retains a declared explanatory gate order; both use identical gates and no cooldown. First rejection does not prove other gates passed. Numeric ratio/volume proxies do not prove future edge or true market completeness. No strategy event emission, future exit, fee PnL, parameter selection or provider invocation.

Independent finite audit: 27 fixed first/middle/last perasset asof cases, distinct raw dedup/window scan and Fraction sizing/cost arithmetic; only fresh-available principal inputs compared. All perasset available/missing counts and 8248 total reconcile. Same Owner, different arithmetic implementation; not third-party/full strategy replay.

v2 stale-known main distributions, code/freeze/results/audit/manifest preserved in v2_stale_known_snapshot. PMO identified fresh-availability error after v2 computation; v3 is a correctness repair, separately frozen before recomputation, no rule/threshold changes. Initial pre-results path and compressed-vs-logical hash failures are preserved. Source and original026 rule bytes unchanged.

Current job010 producer unchanged; live source income not read. Actual provider/model/API/fees/market completeness UNKNOWN, model calls0. Global 12-hour goal ACTIVE; route/model/effort UNKNOWN.
