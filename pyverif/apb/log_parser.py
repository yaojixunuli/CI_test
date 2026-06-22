"""
log_parser.py —— 把 UVM 仿真日志解析成结构化数据（pandas DataFrame）

对应场景（来自学习思路 "数据分析 / 仿真日志解析"）：
    一次仿真会产生 sim.log / vcs.log，里面是成千上万行 UVM 报告。
    人工看日志又慢又容易漏，所以我们用正则把它解析成表格，
    再用 pandas 做统计、用 matplotlib 画图。

一条典型的 UVM 报告长这样：
    UVM_INFO apb_scoreboard.sv(44) @ 350: uvm_test_top.env.scoreboard \
        [apb_scoreboard] Compare SUCCESSFULLY addr=0x0 write=1 data=0xdeadbeef
拆开看：
    UVM_INFO            -> severity（严重级别）
    apb_scoreboard.sv   -> 文件名
    (44)                -> 行号
    @ 350               -> 仿真时间
    uvm_test_top...     -> reporter（哪个组件打印的）
    [apb_scoreboard]    -> id（消息分类标签）
    Compare ...         -> message（消息正文）

本模块提供两层 API：
    parse_log_text() / parse_log_file()  -> 返回原始报告表 (DataFrame)
    LogReport                            -> 在原始表之上做语义聚合（pass/fail/覆盖率...）
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# --- 核心正则：匹配一条 UVM 报告行 --------------------------------------
# 用 re.VERBOSE 写成多行带注释，便于新人逐段看懂。
# 下面这段用 r"""...""" 原始字符串：因为内容里有 \s \S \w 等反斜杠，
# 普通字符串会把它们当"转义序列"而报 SyntaxWarning，加 r 前缀即可避免。
r"""
(?P<severity> ... )：
这是一个命名捕获组，名字叫 severity。
匹配到的内容可以通过 match.group("severity") 直接取出。

\s 代表任意空白字符（空格或Tab），+ 代表匹配1次或多次。 
\s*：* 代表匹配0次或多次空格。
\S（大写的 S）代表非空白字符（即不是空格、不是Tab）

[\w./]：匹配字母、数字、下划线（\w）、点号（.）、斜杠（/）。

[^\]]：这是一个否定字符类。
^ 在方括号里表示“取反”。意思是：匹配除了右方括号 ] 之外的任何字符

re.VERBOSE：允许我们在规则里换行、缩进、写注释。
"""
_UVM_LINE = re.compile(
    r"""
    ^(?P<severity>UVM_INFO|UVM_WARNING|UVM_ERROR|UVM_FATAL)\s+   # 严重级别
    (?P<file>[\w./]+)\((?P<line>\d+)\)\s+                        # 文件名(行号)
    @\s*(?P<time>\d+):\s*                                        # @ 仿真时间
    (?P<reporter>\S+)\s+                                         # 报告组件路径
    \[(?P<id>[^\]]+)\]\s*                                        # [消息ID]
    (?P<message>.*)$                                             # 消息正文
    """,
    re.VERBOSE,
)

# 从 scoreboard 的成功消息里再抠出 addr/write/data。
#   "Compare SUCCESSFULLY addr=0x0 write=1 data=0xdeadbeef"
_CMP_FIELDS = re.compile(
    r"addr=0x(?P<addr>[0-9a-fA-F]+)\s+write=(?P<write>[01])\s+data=0x(?P<data>[0-9a-fA-F]+)"
)

# 覆盖率消息： "Functional coverage = 87.50%"
_COV_LINE = re.compile(r"Functional coverage\s*=\s*(?P<cov>[\d.]+)%")


def parse_log_text(text: str) -> pd.DataFrame:
    """
    解析一段日志文本，返回所有 UVM 报告组成的 DataFrame。

    列： severity, file, line, time, reporter, id, message
    无法匹配的行（如 $display 的纯文本）会被忽略——这正是正则解析的取舍：
    只关心结构化的报告。

    m.groupdict()：把在正则里写的所有 (?P<name>...) 命名分组，一次性转换成一个 Python 字典。
    """
    rows = []
    for raw in text.splitlines():
        m = _UVM_LINE.match(raw.strip())
        if not m:
            continue
        d = m.groupdict()
        d["line"] = int(d["line"])
        d["time"] = int(d["time"])
        rows.append(d)

    cols = ["severity", "file", "line", "time", "reporter", "id", "message"]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(rows, columns=cols)


def parse_log_file(path: str | Path) -> pd.DataFrame:
    """从文件读取并解析（UTF-8，遇到非法字节就替换，避免崩溃）。"""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_log_text(text)


@dataclass
class LogReport:
    """
    对解析结果做语义聚合，得到一张"体检报告"。

    用法：
        rep = LogReport.from_file("sim.log")
        assert rep.passed
        print(rep.summary())

    @property 让你可以像访问属性一样调用方法，核心价值是“实时计算、自动更新、代码简洁”。

    @dataclass 是 Python 的一个装饰器，它通过“自动生成代码”的方式，
    帮你省掉写 __init__、__repr__、__eq__ 等“机械重复”的样板代码，
    让你只需要专注于定义“这个类里存了哪些数据（字段）”。

    """


    df: pd.DataFrame                 # 原始报告表
    compares: pd.DataFrame           # scoreboard 比较明细（addr/write/data/result）
    coverage: float | None           # 功能覆盖率 %（解析不到则 None）
    test_passed: bool | None         # 是否出现 "TEST CASE PASSED"（$display 文本）

    # ---- 计数（property，按需计算，避免存陈旧值）-----------------------
    @property
    def n_info(self) -> int:
        return int((self.df["severity"] == "UVM_INFO").sum())

    @property
    def n_warning(self) -> int:
        return int((self.df["severity"] == "UVM_WARNING").sum())

    @property
    def n_error(self) -> int:
        return int((self.df["severity"] == "UVM_ERROR").sum())

    @property
    def n_fatal(self) -> int:
        return int((self.df["severity"] == "UVM_FATAL").sum())

    @property
    def n_compare_pass(self) -> int:
        if self.compares.empty:
            return 0
        return int((self.compares["result"] == "PASS").sum())

    @property
    def n_compare_fail(self) -> int:
        if self.compares.empty:
            return 0
        return int((self.compares["result"] == "FAIL").sum())

    @property
    def passed(self) -> bool:
        """
        综合判定用例是否通过：
        - 没有 ERROR / FATAL
        - 没有比较失败
        - 若日志里有 TEST CASE PASSED/FAILED 文本，以它为准
        """
        if self.test_passed is False:
            return False
        return self.n_error == 0 and self.n_fatal == 0 and self.n_compare_fail == 0

    def summary(self) -> dict:
        """返回一个适合塞进报告/断言的小字典。"""
        return {
            "info": self.n_info,
            "warning": self.n_warning,
            "error": self.n_error,
            "fatal": self.n_fatal,
            "compare_pass": self.n_compare_pass,
            "compare_fail": self.n_compare_fail,
            "coverage": self.coverage,
            "passed": self.passed,
        }

    # ---- 构造入口 -------------------------------------------------------
    '''
        @classmethod 是一个装饰器，它告诉 Python：“这个方法不属于某个具体的对象（实例），而是属于这个类本身。”
        cls 是 “class” 的缩写（约定俗成的名字），它代表这个类本身
        "LogReport"是 Python 的“前向引用（Forward Reference）”语法，核心原因是：在解析 from_file 方法定义的那一瞬间，LogReport 这个类还没有完全构建好。
    '''
    @classmethod
    def from_text(cls, text: str) -> "LogReport":
        df = parse_log_text(text)
        compares = _extract_compares(df)
        coverage = _extract_coverage(df)
        test_passed = _extract_test_verdict(text)
        return cls(df=df, compares=compares, coverage=coverage, test_passed=test_passed)

    @classmethod
    def from_file(cls, path: str | Path) -> "LogReport":
        return cls.from_text(Path(path).read_text(encoding="utf-8", errors="replace"))


# --- 下面是给 LogReport 用的内部小函数 ----------------------------------
def _extract_compares(df: pd.DataFrame) -> pd.DataFrame:
    """从 scoreboard 的消息里抽取每一笔比较结果。
        df.iterrows()是Pandas 提供的一个方法，用于逐行遍历表格。它返回一个迭代器，每次迭代会生成一个 (索引, 行数据) 的元组（Tuple）。
        _ 是一个约定俗成的“弃子”变量名
    """
    rows = []
    for _, r in df.iterrows():
        msg = r["message"]
        if "Compare SUCCESSFULLY" in msg or "Compare FAILED" in msg:
            result = "PASS" if "SUCCESSFULLY" in msg else "FAIL"
            fields = _CMP_FIELDS.search(msg)
            rows.append({
                "time": r["time"],
                "result": result,
                "addr": int(fields["addr"], 16) if fields else None,
                "write": int(fields["write"]) if fields else None,
                "data": int(fields["data"], 16) if fields else None,
            })
    cols = ["time", "result", "addr", "write", "data"]
    return pd.DataFrame(rows, columns=cols)


def _extract_coverage(df: pd.DataFrame) -> float | None:
    """取最后一条覆盖率报告（report_phase 里打印的那条）。"""
    cov = None
    for msg in df["message"]:
        m = _COV_LINE.search(msg)
        if m:
            cov = float(m["cov"])
    return cov


def _extract_test_verdict(text: str) -> bool | None:
    """apb_base_test 用 $display 打印 PASSED/FAILED（不是 UVM 报告）。"""
    if "TEST CASE FAILED" in text:
        return False
    if "TEST CASE PASSED" in text:
        return True
    return None
