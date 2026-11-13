# macOS Python计时域复核

本轮父审实测Python3.9.6，monotonic实现为mach_absolute_time()；新进程monotonic_ns=10839208，而显式clock_gettime_ns(CLOCK_MONOTONIC)=5945227471000。这不是同一个起点，不能与阶段001另进程相对counter直接相减。

官方资料 https://docs.python.org/3/library/time.html 本轮实际读取：macOS monotonic在Python3.10变更为所有进程同一计时域。本机未升级，不能按新版保证假定旧运行时可跨进程比较。

已验范围：现有runtime/version/implementation和显式OS函数可用；同采集进程内时间差有效。阶段004后续真实parent-child夹逼检验已通过，两child分别6270458704000与6270477858000ns，均在parent前后区间内。只证明当前host/boot可比，不是跨host或重启保证。未来接入还需明确域ID及source-asof到quote的完整因果顺序；历史raw保持原样。原件见phase004_clock_transport/clock_proof.json及shared_clock.py，父已审。

不读密钥、不改系统时钟、不安装或升级Python；阶段001仍按原源和截止采集。此问题不构成Jev/Decisions模型速度失败，但会影响我们能否正确测量真实链路延迟。
