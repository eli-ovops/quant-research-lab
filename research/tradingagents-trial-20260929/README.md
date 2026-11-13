# TradingAgents 适配试用

本机已核：TradingAgents 0.5.2，全局 CLI 与 backtest --help 成功。安装位于 /Volumes/EXTERNAL/.codex-global-tools/uv-tools/tradingagents；未修改安装文件或读取密钥。

已执行：try_indicators.py 使用安装包实际 get_stockstats_indicator 函数，通过进程内只读数据适配器接入公开 OKX ETH-USDT-SWAP 的99根已确认日线。保留交易所日界，未将日线伪称15分钟数据。脚本禁网络，未调用模型、未下单。数据、SHA256、指标输出见 public-candles.json / component-result.json；不使用200周期指标，样本不足。

适合用途：独立分析候选方向，比较多空理由；指标模块可读取现有公开合约K线。完整LLM分析尚未运行，模型服务配置状态UNKNOWN，已向用户询问服务名称/是否已配置，不索取密钥内容。

重大适配限制：安装包backtest.py明确仅评估判断质量，不是组合模拟器；没有据此生成的成交价/数量/现金账本。不能用其评分替代合约含费收益或强平模型。其技术指标接口按日期工作，不可直接塞入同一天多根15分钟K线并声称保留了完整时间语义。

未将本轮试用结果混入已冻结24小时纸面实验；HyperFrames面向视频展示，本任务无需调用；未下载/安装Fincept。本目录三个数据/代码产物和本说明保留供复核。

官方项目：https://github.com/TauricResearch/TradingAgents 。模型接口设置参考官方仓库README与.env.example；安装成功不等于已配置LLM或已证明收益。
