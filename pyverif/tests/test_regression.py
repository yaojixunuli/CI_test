"""
test_regression.py —— 回归测试管理（批量跑仿真 + 汇总结果）

对应学习思路："回归测试管理：批量运行仿真、收集结果、生成报告"

回归(regression) = 把一组用例(case0/case1/...)成批跑一遍，确认改动没有
"回退"破坏已有功能。本文件分两类：

  A. 不依赖仿真器的"离线回归"：直接解析已有/样例日志来判定 case 通过与否。
     —— 这是练习"收集结果、汇总"的最佳入口，随时可跑。
  B. 依赖真实仿真器的"在线回归"：用 @pytest.mark.sim 标记，
     需要 `pytest --run-sim` 才会真正调用 make 跑 VCS。

注意 B 类用例默认会被 conftest.py 跳过（见 pytest_collection_modifyitems），
所以在没有仿真器的机器上，本文件依然能全绿。
"""

import pandas as pd
import pytest

from apb.log_parser import LogReport

# 回归用例清单：真实项目里通常从配置文件/目录扫描得到。
REGRESSION_CASES = ["case0", "case1"]


# =====================================================================
# A. 离线回归：基于日志判定（无需仿真器）
# =====================================================================
@pytest.mark.parametrize("case", REGRESSION_CASES)
def test_offline_regression_from_log(case, sample_log):
    """
    用样例日志代表每个 case 的运行结果，演示"解析日志 -> 判定通过"。
    真实项目里把 sample_log 换成 sim/<case>.log 即可。
    """
    rep = LogReport.from_file(sample_log)
    assert rep.passed, f"{case} 回归失败: {rep.summary()}"


def test_regression_summary_table(sample_log):
    """
    汇总多个 case 的结果成一张表（DataFrame），这是生成回归报告的核心步骤。
    真实场景：循环每个 case 的日志，收集 pass/fail/coverage/耗时。
    """
    rows = []
    for case in REGRESSION_CASES:
        rep = LogReport.from_file(sample_log)   # 示例：所有 case 复用同一日志
        s = rep.summary()
        s["case"] = case
        rows.append(s)

    df = pd.DataFrame(rows).set_index("case")

    # 回归门禁：所有 case 必须通过
    assert df["passed"].all(), f"存在失败 case:\n{df}"
    # 至少要有结果
    assert len(df) == len(REGRESSION_CASES)
    print("\n回归汇总:\n", df.to_string())


# =====================================================================
# B. 在线回归：真正调用仿真器（需 --run-sim）
# =====================================================================
@pytest.mark.sim
def test_compile_once(require_sim):
    """编译一次，作为后续在线回归的前置（simv 生成成功）。"""
    res = require_sim.compile()
    assert res.returncode == 0, f"编译失败，详见 {res.log_path}"


@pytest.mark.sim
@pytest.mark.parametrize("case", REGRESSION_CASES)
def test_online_regression(require_sim, case):
    """逐个跑真实 case，解析其日志并判定通过。"""
    res = require_sim.run_case(case)
    assert res.report.passed, (
        f"{case} 仿真未通过: {res.report.summary()}，日志: {res.log_path}"
    )
