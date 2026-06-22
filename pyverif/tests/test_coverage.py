"""
test_coverage.py —— 功能覆盖率门限检查

对应学习思路："报告生成 - 覆盖率报告" + "覆盖率数据分析"

背景
----
UVM 里 apb_coverage.sv 用 covergroup 收集功能覆盖率，并在 report_phase
打印一行： "Functional coverage = 68.75%"。
真实流程里还会用 `make cov`(urg) 生成 HTML 覆盖率报告(urgReport/)。

本文件演示两件事：
    1) 从仿真日志里解析覆盖率数字，并断言达到"门限"（验证签核常用关卡）。
    2) 用 Python 复刻 covergroup 的 bin 计算，理解覆盖率是怎么算出来的。
"""

import pytest

from apb import ApbTransaction
from apb.log_parser import LogReport
from apb.model import NUM_REGS

# 签核门限：低于这个值就认为验证还不充分（这里设 60% 仅作教学示例）。
COVERAGE_GATE = 60.0


# --- 1) 从样例日志解析覆盖率并卡门限 -----------------------------------
@pytest.mark.cov
def test_coverage_meets_gate(sample_log):
    rep = LogReport.from_file(sample_log)
    assert rep.coverage is not None, "日志里没有找到覆盖率报告"
    assert rep.coverage >= COVERAGE_GATE, (
        f"功能覆盖率 {rep.coverage}% 低于门限 {COVERAGE_GATE}%"
    )


# --- 2) 用 Python 复刻 covergroup 的计算逻辑 --------------------------
# apb_coverage.sv 的 covergroup 有 4 个 coverpoint：
#   cp_dir  : write/read              -> 2 个 bin
#   cp_addr : addr[5:2] 0..15         -> 16 个 bin
#   cp_data : zero / ones / others    -> 3 个 bin
#   cx_dir_addr : cp_dir × cp_addr    -> 2*16 = 32 个 bin
def _compute_coverage(transactions):
    """给定一串事务，返回每个 coverpoint 命中的 bin 集合。"""
    dir_bins, addr_bins, data_bins, cross_bins = set(), set(), set(), set()
    for tr in transactions:
        dir_bins.add(tr.write)
        addr_bins.add(tr.reg_index)
        if tr.data == 0x0000_0000:
            data_bins.add("zero")
        elif tr.data == 0xFFFF_FFFF:
            data_bins.add("ones")
        else:
            data_bins.add("others")
        cross_bins.add((tr.write, tr.reg_index))
    return dir_bins, addr_bins, data_bins, cross_bins


@pytest.mark.cov
def test_case0_partial_coverage():
    """
    复刻 case0：只覆盖 addr[0:7]，数据用 zero + others。
    预期 cp_addr 只覆盖一半、cp_data 缺 ones —— 即未满覆盖。
    """
    traffic = []
    for i in range(8):
        data = 0 if i == 0 else (0xDEAD_0000 + i)
        traffic.append(ApbTransaction(write=True, addr=i << 2, data=data))
        traffic.append(ApbTransaction(write=False, addr=i << 2))

    dir_b, addr_b, data_b, cross_b = _compute_coverage(traffic)

    assert dir_b == {True, False}            # 读写都覆盖
    assert addr_b == set(range(8))           # 只覆盖低 8 个地址
    assert "ones" not in data_b              # case0 没有写全 1
    assert len(cross_b) == 16                # 8 地址 × 2 方向


@pytest.mark.cov
def test_case0_plus_case1_full_addr_coverage():
    """
    case0(addr 0..7) + case1(addr 8..15) 合并后应覆盖全部 16 个地址，
    且数据三种 bin(zero/ones/others) 齐全 —— 说明两个 case 互补。
    这正是 `make cov` 把多个 case 的覆盖率合并的意义。
    """
    traffic = []
    # case0
    for i in range(8):
        data = 0 if i == 0 else (0xDEAD_0000 + i)
        traffic.append(ApbTransaction(write=True, addr=i << 2, data=data))
        traffic.append(ApbTransaction(write=False, addr=i << 2))
    # case1
    for i in range(8, 16):
        data = 0xFFFF_FFFF if i == 15 else (0xBEEF_0000 + i)
        traffic.append(ApbTransaction(write=True, addr=i << 2, data=data))
        traffic.append(ApbTransaction(write=False, addr=i << 2))

    dir_b, addr_b, data_b, cross_b = _compute_coverage(traffic)

    assert addr_b == set(range(NUM_REGS))            # 16 个地址全覆盖
    assert data_b == {"zero", "ones", "others"}      # 数据 bin 齐全
    assert len(cross_b) == 32                         # cross 100%


# --- 3) 真实仿真覆盖率（需要 --run-sim）-------------------------------
@pytest.mark.cov
@pytest.mark.sim
def test_real_coverage(require_sim):
    """跑真实 case0 并检查日志里报告的覆盖率达标。"""
    require_sim.compile()
    res = require_sim.run_case("case0")
    assert res.report.coverage is not None
    assert res.report.coverage >= COVERAGE_GATE
