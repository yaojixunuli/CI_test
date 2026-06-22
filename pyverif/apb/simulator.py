"""
simulator.py —— 封装"调用真实仿真器跑一个 case"的流程

对应学习思路："编写 Python 脚本自动运行 VCS 仿真、解析 log、生成报告"

设计要点
--------
1. 用 subprocess 调 makefile 的目标（com / case0 / case1 / cov）。
2. 自动把每个 case 的 stdout 存成日志文件，方便 log_parser 解析。
3. 仿真器可能没装（比如在纯学习的机器上），所以提供 is_available()，
   测试用例可以据此 skip，而不是直接报错。

注意：本项目的 sim/makefile 用的是 VCS。如果你用的是其它仿真器
（如 Vivado xsim、Questa），把下面的命令改掉即可，测试逻辑不用动——
这正是"把工具调用封装在一处"的好处。
"""

from __future__ import annotations

'''
shutil 是 Python 的高级文件操作工具箱，它的名字来源于 Shell Utility（Shell 工具）的缩写。
应用场景为需要“复制、移动、删除、打包”硬盘上的文件和文件夹时
'''
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .log_parser import LogReport

# 仿真目录（sim/）相对本文件的位置： pyverif/apb/ -> ../../sim
SIM_DIR = (Path(__file__).resolve().parent.parent.parent / "sim").resolve()


@dataclass
class SimResult:
    """一次仿真运行的结果。"""
    case: str
    returncode: int
    log_path: Path
    wall_time_s: float        # 真实墙上时间（不是仿真时间）
    report: LogReport         # 解析后的日志报告


class Simulator:
    """
    仿真器封装。

    用法：
        sim = Simulator()
        if sim.is_available():
            sim.compile()
            res = sim.run_case("case0")
            assert res.report.passed
    """

    def __init__(self, sim_dir: Path | None = None, make: str = "make") -> None:
        self.sim_dir = Path(sim_dir) if sim_dir else SIM_DIR
        self.make = make

    # ---- 环境探测 -------------------------------------------------------
    def is_available(self) -> bool:
        """
        判断当前机器能否真正跑仿真：需要有 make，且有 vcs 或 simv。
        测试里用它来决定 skip：
            if not sim.is_available(): pytest.skip("无仿真器")
        """
        if shutil.which(self.make) is None:
            return False
        has_vcs = shutil.which("vcs") is not None
        has_simv = (self.sim_dir / "simv").exists()
        return has_vcs or has_simv

    # ---- 编译 -----------------------------------------------------------
    def compile(self, timeout: int = 600) -> SimResult:
        """执行 `make com`（编译 + elaborate，生成 simv）。"""
        return self._run_make("com", log_name="vcs", timeout=timeout)

    # ---- 跑一个 case ----------------------------------------------------
    def run_case(self, case: str, timeout: int = 600) -> SimResult:
        """
        执行 `make <case>`，例如 case0 / case1。
        makefile 里这些目标会运行 simv 并带上对应的 +UVM_TESTNAME。
        """
        return self._run_make(case, log_name=case, timeout=timeout)

    # ---- 合并覆盖率并出 HTML 报告 ---------------------------------------
    def merge_coverage(self, timeout: int = 300) -> SimResult:
        """执行 `make cov`，用 urg 生成 urgReport/dashboard.html。"""
        return self._run_make("cov", log_name="urg", timeout=timeout)

    # ---- 内部：真正调用 make -------------------------------------------
    def _run_make(self, target: str, log_name: str, timeout: int) -> SimResult:
        log_path = self.sim_dir / f"{log_name}.pylog"
        start = time.monotonic()
        proc = subprocess.run(
            [self.make, target],
            cwd=str(self.sim_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        wall = time.monotonic() - start

        # 把 stdout+stderr 落盘，供 log_parser 复用（也便于人工排查）
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        log_path.write_text(combined, encoding="utf-8", errors="replace")

        return SimResult(
            case=target,
            returncode=proc.returncode,
            log_path=log_path,
            wall_time_s=wall,
            report=LogReport.from_text(combined),
        )
