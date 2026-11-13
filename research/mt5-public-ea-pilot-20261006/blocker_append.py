# -*- coding: utf-8 -*-
from pathlib import Path
p=Path('/Users/USER/.codex/LOCAL_BLOCKERS.md')
heading='## 2026-10-06 MT5公开EA源码与Dukascopy历史数据探针'
if heading not in p.read_text():
 with p.open('a') as f:f.write('\n'+heading+'\n\n- 范围：本轮 /Volumes/EXTERNAL/量化/research/mt5-public-ea-pilot-20261006。MQL5候选1/2附件web.click仅Internal Error；urllib三个MQL5页TLS handshake timeout。页面有下载链接不等取得源码。\n- Jina候选1返回401，未重试、找凭据或绕过。官方文章17239的inline代码可由web读取，只支持部分静态审阅，不证明附件完整可复现。\n- Dukascopy官方当前data-export可读，S3 requester-pays要求AWS凭据与费用，不在本轮授权内；未调用S3。公开legacy EURUSD/2026/08/21/07h_ticks.bi5探针urllib TLS handshake timeout，无报价记录，不推断全站或该日期永久无数据。\n- IAB本轮unavailable，Chrome新建研究页navigate10秒timeout，仍about:blank。未触用户标签，未改网络/认证。没有受支持且本轮已验证的数据替代入口，停止重试，不以修工具为业务必经步骤。\n- 下一步补候选1原mq5和固定期间真实双边数据/明确broker规格后回放，可用受支持官方历史文件或MT5 Tester的broker数据；不要求安装或账户操作。PnL=null。\n- 原错：requests.jsonl、rawsource/tool_failures.json、official_web_receipt.json、asian_code_receipt.json（均在本任务目录）。仅适用本次，禁止旧失败替代当前验证。\n')
print('scoped LOCAL_BLOCKERS entry retained')
