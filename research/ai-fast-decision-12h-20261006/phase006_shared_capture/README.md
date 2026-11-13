# 当前source入口：job003失败，暂无三机制前向数据
截至2026-10-06 17:33UTC：job002已17:01:30网络丢失STOPPED，Owner复核真实session/PID终态、51172条gzip CRC/EOF/ordinal与首100prefix通过。此前“采集继续”回执来自过时snapshot，撤回当前live判断；旧运行snapshot另存，不作为现在状态。

phase007真实code/protocol冻结17:14:35.763208UTC晚于job002 EOS，故job002仅开发，不是该套前向。job003是父明确一次独立授权，保持同official endpoint/TLS/已有proxy，无auto reconnect，源/参数先冻结；实际PID35525/session55746于17:30:23启动尝试，17:30:28即TLS SSLEOFError停止，0消息/0订阅ACK/未建数据流，session exit0只是正常异常收尾，不是API成功。

CURRENT_CAPTURE.json指job003 FAILED_TLS_BEFORE_SUBSCRIPTION。错误原文EOF occurred in violation of protocol (_ssl.c:1129)，原因UNKNOWN；没有HTTP403/权限拒绝回执，不定性服务主动拒绝。LOCAL_BLOCKERS B007仅历史REST TLS EOF与MCP可读替代，不证明WS已修复；本机proxy配置仍127.0.0.1:7890启用，窄lsof未显示匹配listener不能当已证端口关闭，未改配置/TLS/身份/route或扫描凭据。任何下一WS须新证据与父预算，不盲循环。

旧job001逻辑cap变化后的短样本/oldjob002全部保留，不删除压缩原raw。job003最多45min计划未形成45min数据，不能用空采集报告策略0交易或模型失败。三机制冻结后可评价行情仍NONE，未来phase008只可准备来源切分/时序/簇/单位/资金费flags adapter；真正评价须以后获准的新成熟数据，不改规则或填造结果。

逻辑240MB/gzip≤230MB/stage240/global2GiB、OS共享域/boot、初100/CRC等规则没有放宽，0模型/费/key/install。phase007独立STATUS_CORRECTION已说明source更正，旧策略freeze不变；runID新来源绑定要在phase008显式记录，不能改旧freeze或默认旧job2。整体12h任务ACTIVE，局部source失败不等于目标完成。

