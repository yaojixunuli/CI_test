#!/usr/bin/env python3
"""
analyze_trend.py —— 覆盖率/通过率趋势可视化（matplotlib + pandas）

对应学习思路："趋势可视化" + "matplotlib 可视化" + "覆盖率数据分析"

它读取历史回归数据 (data/regression_history.csv)，画出：
    1) 各 case 的功能覆盖率随时间变化（折线图）
    2) 每次回归的比较失败数（柱状图）
并保存成图片到 reports/ 目录。

运行：
    python scripts/analyze_trend.py
    python scripts/analyze_trend.py --csv path/to/your.csv

这演示了验证里非常实用的一环：把每天/每次回归的数据沉淀下来，
用图表看清"覆盖率是否在涨、失败是否收敛"，支撑项目进度判断。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# matplotlib 在无图形界面的环境(CI/服务器)也要能出图，用 Agg 后端。
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PYVERIF_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PYVERIF_DIR / "data" / "regression_history.csv"
REPORT_DIR = PYVERIF_DIR / "reports"


def load_history(csv_path: Path) -> pd.DataFrame:
    """读 CSV 并把 date 解析成日期类型，按时间排序。
    parse_dates=["date"] 这个参数的作用非常直接：它告诉 Pandas，在读取 CSV 文件时，
    不要将 "date" 这一列当作普通的字符串或数字，而是要“强行”解析成 Python 的日期时间类型（datetime）。
    """
    df = pd.read_csv(csv_path, parse_dates=["date"])
    return df.sort_values("date")


def plot_coverage_trend(df: pd.DataFrame, out_path: Path) -> None:
    """折线图：每个 case 的覆盖率随时间变化。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))

    # pivot：行=日期, 列=case, 值=coverage —— pandas 透视表的经典用法
    pivot = df.pivot_table(index="date", columns="case", values="coverage")
    for case in pivot.columns:
        ax.plot(pivot.index, pivot[case], marker="o", label=case)

    ax.axhline(60, color="red", linestyle="--", linewidth=1, label="门限 60%")
    ax.set_title("功能覆盖率趋势")
    ax.set_xlabel("日期")
    ax.set_ylabel("覆盖率 (%)")
    ax.set_ylim(0, 105)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def plot_failures(df: pd.DataFrame, out_path: Path) -> None:
    """柱状图：每次回归的总比较失败数。"""
    fig, ax = plt.subplots(figsize=(8, 4.5))

    by_date = df.groupby("date")["compare_fail"].sum()
    ax.bar([d.strftime("%m-%d") for d in by_date.index], by_date.values,
           color=["#c62828" if v > 0 else "#2e7d32" for v in by_date.values])
    ax.set_title("每次回归的比较失败数")
    ax.set_xlabel("日期")
    ax.set_ylabel("失败次数")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def main() -> int:

    '''
    argparse.ArgumentParser()：创建一个新的“参数解析器”对象（取名 parser）。
    description：给它设置一段描述。当用户输入 python your_script.py --help 时，这段文字就会显示出来，告诉别人这个脚本是干嘛的（“回归趋势可视化”）。
    '''
    parser = argparse.ArgumentParser(description="回归趋势可视化")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV,
                        help=f"历史数据 CSV（默认 {DEFAULT_CSV}）")
    '''它会去读取你在终端敲入的命令（比如 python plot.py --csv mydata.csv），解析出参数，并将其封装成一个简单的对象（args）。'''
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_history(args.csv)

    cov_png = REPORT_DIR / "trend_coverage.png"
    fail_png = REPORT_DIR / "trend_failures.png"
    plot_coverage_trend(df, cov_png)
    plot_failures(df, fail_png)

    # 顺带在终端打印一份文字小结（pandas 聚合）
    latest = df[df["date"] == df["date"].max()]
    print("最新一次回归：")
    print(latest[["case", "coverage", "compare_fail", "passed"]].to_string(index=False))
    print(f"\n[完成] 覆盖率趋势图: {cov_png}")
    print(f"[完成] 失败数柱状图: {fail_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
