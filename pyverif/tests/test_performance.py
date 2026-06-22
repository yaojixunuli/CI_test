"""
test_performance.py —— 性能测试（延迟 / 带宽 / 压力）

对应学习思路："性能测试：测量读写延迟、带宽测试、压力测试"

这里演示如何用 pandas 做统计、如何写"性能门限"断言。
注意：这里的"性能"是基于 APB 时序模型推算的（每笔事务 3 周期 @100MHz），
对接真实仿真时，把数据来源换成从波形/日志里测得的实际周期即可，
统计与断言部分完全复用。
"""

import pandas as pd
import pytest

from apb import ApbSlaveModel, ApbTransaction, APB_CLOCK_NS
from apb.model import NUM_REGS, CYCLES_PER_XFER

ALL_ADDRS = [i << 2 for i in range(NUM_REGS)]


def _run_traffic(model: ApbSlaveModel, transactions) -> pd.DataFrame:
    """跑一批事务，把每笔的延迟收集成 DataFrame（性能分析的标准做法）。"""
    records = []
    for tr in transactions:
        res = model.access(tr)
        records.append({
            "addr": tr.addr,
            "write": tr.write,
            "cycles": res.cycles,
            "latency_ns": res.latency_ns,
        })
    return pd.DataFrame(records)


# --- 1) 单笔延迟：每笔事务延迟应等于固定的 3 周期 ----------------------
@pytest.mark.perf
def test_single_transfer_latency(model: ApbSlaveModel):
    res = model.access(ApbTransaction(write=True, addr=0x00, data=0x1))
    assert res.cycles == CYCLES_PER_XFER
    assert res.latency_ns == pytest.approx(CYCLES_PER_XFER * APB_CLOCK_NS)


# --- 2) 延迟分布统计：用 pandas 算 mean/min/max/p99 --------------------
@pytest.mark.perf
def test_latency_distribution(model: ApbSlaveModel):
    # 构造混合读写流量
    traffic = []
    for addr in ALL_ADDRS:
        traffic.append(ApbTransaction(write=True, addr=addr, data=addr))
        traffic.append(ApbTransaction(write=False, addr=addr))

    df = _run_traffic(model, traffic)

    stats = df["latency_ns"].describe()           # pandas 一行出统计
    p99 = df["latency_ns"].quantile(0.99)

    # 性能门限断言：平均延迟和 p99 都不应超过预期上限
    assert stats["mean"] <= 30.0, f"平均延迟过高: {stats['mean']}ns"
    assert p99 <= 30.0, f"p99 延迟过高: {p99}ns"
    # 把统计打印出来，-s 运行时可见，也会进 HTML 报告的 captured log
    print("\n延迟统计(ns):\n", stats.to_string())


# --- 3) 带宽：吞吐 = 传输字节数 / 总时间 -------------------------------
@pytest.mark.perf
def test_write_bandwidth(model: ApbSlaveModel):
    """连续写 N 笔，计算等效带宽 (MB/s)，并断言不低于门限。"""
    n = 1000
    bytes_per_xfer = 4   # 每笔 32 位 = 4 字节
    traffic = [ApbTransaction(write=True, addr=ALL_ADDRS[i % NUM_REGS], data=i)
               for i in range(n)]

    df = _run_traffic(model, traffic)
    total_time_ns = df["latency_ns"].sum()
    total_bytes = n * bytes_per_xfer

    # MB/s = 字节 / 时间(ns) * 1e9 / 1e6 = 字节 / 时间(ns) * 1000
    bandwidth_mbps = total_bytes / total_time_ns * 1000

    # 理论上限：4 字节 / 30ns ≈ 133 MB/s。设一个稍宽松的门限。
    assert bandwidth_mbps >= 100.0, f"写带宽过低: {bandwidth_mbps:.1f} MB/s"
    print(f"\n写带宽 = {bandwidth_mbps:.1f} MB/s ({n} 笔事务)")


# --- 4) 读 vs 写 延迟对比：分组聚合 ------------------------------------
@pytest.mark.perf
def test_read_vs_write_latency(model: ApbSlaveModel):
    traffic = []
    for addr in ALL_ADDRS:
        traffic.append(ApbTransaction(write=True, addr=addr, data=addr))
        traffic.append(ApbTransaction(write=False, addr=addr))
    df = _run_traffic(model, traffic)

    # groupby：按 write 字段分组求平均延迟（pandas 分组聚合的典型用法）
    by_dir = df.groupby("write")["latency_ns"].mean()
    # 本模型读写延迟相同；真实 DUT 若读慢写快，这里就能抓出来
    assert by_dir[True] == pytest.approx(by_dir[False])


# --- 5) 压力测试：大批量事务下系统应稳定、统计可控 --------------------
@pytest.mark.perf
@pytest.mark.parametrize("n_xfers", [100, 1000, 5000])
def test_stress(model: ApbSlaveModel, n_xfers):
    """
    压力测试：逐渐加大事务数量，验证：
      - 功能仍正确（写进去能读出来）
      - 总耗时随事务数线性增长（无异常抖动）
    """
    traffic = [ApbTransaction(write=True, addr=ALL_ADDRS[i % NUM_REGS], data=i & 0xFFFF_FFFF)
               for i in range(n_xfers)]
    df = _run_traffic(model, traffic)

    # 总周期应等于 事务数 * 每笔周期（线性、可预测）
    assert df["cycles"].sum() == n_xfers * CYCLES_PER_XFER
    # 抽查最后一次写的功能正确性
    last_addr = ALL_ADDRS[(n_xfers - 1) % NUM_REGS]
    assert model.read(last_addr) == ((n_xfers - 1) & 0xFFFF_FFFF)
