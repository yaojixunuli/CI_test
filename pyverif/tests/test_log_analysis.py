"""
test_log_analysis.py —— 仿真日志解析与数据分析

对应学习思路："数据分析：仿真日志解析、覆盖率数据分析、趋势可视化"
                + "pandas 数据处理"

这里我们把 UVM 日志喂给 log_parser，得到 DataFrame，再用 pandas 做各种
统计和检查。重点不在硬件，而在于"如何把一堆文本变成可断言的数据"。
"""

import pandas as pd
import pytest

from apb.log_parser import LogReport, parse_log_file


# --- 1) 基本解析：能从样例日志解析出报告行 ----------------------------
@pytest.mark.analysis
def test_parse_returns_dataframe(sample_log):
    df = parse_log_file(sample_log)
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    # 解析出来的列必须齐全
    assert set(df.columns) == {"severity", "file", "line", "time", "reporter", "id", "message"}


# --- 2) 按严重级别统计（pandas value_counts）-------------------------
@pytest.mark.analysis
def test_severity_counts(sample_log):
    rep = LogReport.from_file(sample_log)
    # 样例日志里：0 个 error / 0 个 fatal，应判为通过
    assert rep.n_error == 0
    assert rep.n_fatal == 0
    assert rep.passed is True


# --- 3) scoreboard 比较明细抽取 ---------------------------------------
@pytest.mark.analysis
def test_compare_extraction(sample_log):
    rep = LogReport.from_file(sample_log)
    # 样例日志有 16 笔比较，全部 PASS
    assert rep.n_compare_pass == 16
    assert rep.n_compare_fail == 0

    # compares 是个 DataFrame，可以继续分析
    cmp_df = rep.compares
    assert len(cmp_df) == 16
    # 一半是写、一半是读
    assert (cmp_df["write"] == 1).sum() == 8
    assert (cmp_df["write"] == 0).sum() == 8


# --- 4) 用 pandas 做"每个地址访问了几次"的分组统计 ------------------
@pytest.mark.analysis
def test_access_count_per_address(sample_log):
    rep = LogReport.from_file(sample_log)
    counts = rep.compares.groupby("addr").size()
    # case0 每个地址都"先写后读"，所以每个地址恰好出现 2 次
    assert (counts == 2).all(), f"存在访问次数异常的地址:\n{counts}"


# --- 5) 时间顺序检查：比较事件的时间应单调递增 -----------------------
@pytest.mark.analysis
def test_compare_time_monotonic(sample_log):
    rep = LogReport.from_file(sample_log)
    times = rep.compares["time"].tolist()
    assert times == sorted(times), "比较事件时间戳非单调递增，日志可能错乱"


# --- 6) 演示对"失败日志"的解析（构造一段带 ERROR 的文本）------------
@pytest.mark.analysis
def test_parse_failing_log():
    failing = (
        "UVM_INFO apb_scoreboard.sv(44) @ 75: uvm_test_top.env.scoreboard "
        "[apb_scoreboard] Compare SUCCESSFULLY addr=0x0 write=1 data=0x0\n"
        "UVM_ERROR apb_scoreboard.sv(48) @ 115: uvm_test_top.env.scoreboard "
        "[apb_scoreboard] Compare FAILED\n"
        "UVM_INFO apb_scoreboard.sv(49) @ 115: uvm_test_top.env.scoreboard "
        "[apb_scoreboard]   expect: addr=0x4 write=0 data=0xdead0001\n"
        "UVM_INFO apb_scoreboard.sv(51) @ 115: uvm_test_top.env.scoreboard "
        "[apb_scoreboard]   actual: addr=0x4 write=0 data=0x00000000\n"
        "TEST CASE FAILED\n"
    )
    rep = LogReport.from_text(failing)
    assert rep.n_error == 1
    assert rep.n_compare_fail == 1
    assert rep.passed is False


# --- 7) summary() 字典：方便塞进报告或做断言 -------------------------
@pytest.mark.analysis
def test_summary_dict(sample_log):
    rep = LogReport.from_file(sample_log)
    s = rep.summary()
    assert s["passed"] is True
    assert s["compare_pass"] == 16
    assert s["coverage"] == pytest.approx(68.75)
