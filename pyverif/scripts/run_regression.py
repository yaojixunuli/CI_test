#!/usr/bin/env python3
"""
run_regression.py —— 一键回归脚本（批量仿真 -> 收集结果 -> 生成报告）

对应学习思路终极实践：
    "编写 Python 脚本自动运行 VCS 仿真、解析 log、生成 HTML 报告"

这个脚本把前面所有零件串起来，是给"真实工程"用的命令行工具：

    python scripts/run_regression.py                # 离线模式：解析已有日志
    python scripts/run_regression.py --run-sim      # 在线模式：真的调 make 跑 VCS

输出：
    reports/regression.html   —— 人看的 HTML 报告
    reports/regression.csv    —— 机器读的结果表（可喂给 analyze_trend.py 画趋势）

设计上它不依赖 pytest，纯脚本即可运行，方便接入 CI / 定时任务。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 让脚本无论从哪运行，都能 import 到 apb 包（把 pyverif/ 加进 sys.path）
PYVERIF_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PYVERIF_DIR))

import pandas as pd  # noqa: E402

from apb.log_parser import LogReport  # noqa: E402
from apb.simulator import Simulator  # noqa: E402

CASES = ["case0", "case1"]
REPORT_DIR = PYVERIF_DIR / "reports"
SAMPLE_LOG = PYVERIF_DIR / "data" / "sample_sim.log"


def collect_results(run_sim: bool) -> pd.DataFrame:
    """跑（或解析）每个 case，返回结果汇总表。"""
    rows = []
    sim = Simulator()

    if run_sim:
        if not sim.is_available():
            print("[警告] 未检测到仿真器，回退到离线模式（解析样例日志）。")
            run_sim = False
        else:
            print("[信息] 在线模式：编译中 (make com) ...")
            sim.compile()

    for case in CASES:
        if run_sim:
            print(f"[信息] 运行 {case} (make {case}) ...")
            res = sim.run_case(case)
            rep = res.report
            wall = res.wall_time_s
        else:
            rep = LogReport.from_file(SAMPLE_LOG)
            wall = 0.0

        s = rep.summary()
        s["case"] = case
        s["wall_time_s"] = round(wall, 2)
        rows.append(s)
        verdict = "PASS" if s["passed"] else "FAIL"
        print(f"    -> {case}: {verdict}  覆盖率={s['coverage']}%  "
              f"比较 {s['compare_pass']}/{s['compare_pass'] + s['compare_fail']}")

    cols = ["case", "passed", "error", "fatal", "compare_pass",
            "compare_fail", "coverage", "wall_time_s"]
    return pd.DataFrame(rows)[cols].set_index("case")


def write_html(df: pd.DataFrame, path: Path) -> None:
    """把结果表渲染成一个简单自包含的 HTML 报告。"""
    n_pass = int(df["passed"].sum())
    n_total = len(df)
    overall = "PASS" if n_pass == n_total else "FAIL"
    color = "#2e7d32" if overall == "PASS" else "#c62828"

    html = f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>APB 回归报告</title>
<style>
  body {{ font-family: Consolas, "Microsoft YaHei", monospace; margin: 2rem; }}
  h1 {{ margin-bottom: .2rem; }}
  .verdict {{ color: {color}; font-weight: bold; font-size: 1.4rem; }}
  table {{ border-collapse: collapse; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: center; }}
  th {{ background: #f0f0f0; }}
</style>
</head>
<body>
  <h1>APB 回归测试报告</h1>
  <p>总体结论：<span class="verdict">{overall}</span>
     （通过 {n_pass}/{n_total}）</p>
  {df.reset_index().to_html(index=False, border=0)}
  <p style="color:#888;margin-top:2rem">由 pyverif/scripts/run_regression.py 生成</p>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="APB 一键回归")
    parser.add_argument("--run-sim", action="store_true",
                        help="调用真实仿真器(make/VCS)；默认离线解析样例日志")
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = collect_results(run_sim=args.run_sim)

    csv_path = REPORT_DIR / "regression.csv"
    html_path = REPORT_DIR / "regression.html"
    df.to_csv(csv_path)
    write_html(df, html_path)

    print(f"\n[完成] CSV : {csv_path}")
    print(f"[完成] HTML: {html_path}")

    # 退出码：全通过返回 0，否则返回 1（方便 CI 判断）
    return 0 if bool(df["passed"].all()) else 1

'''
如果你的脚本最后一行只是 main()，那么在 CI（持续集成）服务器或 Makefile 眼里，无论你的画图是否报错，它都会认为“Python 解释器正常退出了，任务完成”。

但加了 raise SystemExit(main()) 后：

如果 main() 返回 1（比如 CSV 文件没找到，画图失败），raise SystemExit(1) 会把 1 这个代码传给操作系统。

你的 CI 流水线（比如 Jenkins）如果检测到退出码不是 0，就会自动判定本次构建失败，并停止后续的打包发布流程。
'''
if __name__ == "__main__":
    raise SystemExit(main())
