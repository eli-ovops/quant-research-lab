# job005 启动回执（非完整数据验收）

唯一新有限 public WS 已启动：PID42092，exec session31407，run `phase006-42092-1791311726`。实际开始18:35:26.173535 UTC，数据截止19:20:26.173535 UTC，close grace最多3秒另计。六订阅ACK、六频道真实data、初100行run/domain/ordinal/OS时序核对通过。TLS/hostname验证，既有request级proxy，无auth、无自动重连。

旧job004正常截止且终态gzip核验完成，旧PID均终止后才启动。逻辑JSONL硬上限240000000B，gzip实际动态上限213994033B（小于230000000B以保留阶段240MB及全局2GiB空间）；达到任一时间/容量界即关闭。本回执只证明启动层，运行中gzip未验CRC尾部，完整数据和策略结果仍null。运行源码不改、不重复启动。当前源入口见上一层CURRENT_CAPTURE.json；总12h目标ACTIVE，model/付费/key/私有/订单0。
