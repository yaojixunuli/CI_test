"""
conftest.py —— pytest 的"共享配置中心"

这是 pytest 框架里非常重要的一个特殊文件：
    - 文件名必须叫 conftest.py，pytest 会"自动"加载它，无需 import；
    - 它定义的 fixture（测试夹具）对同目录及子目录下所有 test_*.py 可见；
    - 适合放：路径、被测对象、数据库连接、仿真器句柄等"多个用例共享的东西"。

本文件演示了 pytest 几大核心机制：
    1) @pytest.fixture          —— 提供并管理测试资源（含 setup/teardown）
    2) fixture 的 scope         —— function / module / session 控制创建频率
    3) 命令行选项 + fixture     —— pytest_addoption 自定义 `--run-sim` 开关
    4) pytest_configure         —— 程序化注册 marker
    5) 钩子函数(hook)            —— 把额外信息写进 HTML 报告
"""

from __future__ import annotations

from pathlib import Path

import pytest

from apb import ApbSlaveModel
from apb.simulator import Simulator

# 项目里几个常用目录，集中算一次，供各 fixture 复用。
PYVERIF_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PYVERIF_DIR.parent
DATA_DIR = PYVERIF_DIR / "data"
REPORT_DIR = PYVERIF_DIR / "reports"


# =====================================================================
# 1) 自定义命令行选项
#    让使用者可以 `pytest --run-sim` 来开启真实仿真用例。
#    默认不开，保证"零依赖"也能跑通绝大多数用例。
# =====================================================================
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-sim",
        action="store_true",
        default=False,
        help="运行需要真实仿真器(VCS/xsim)的用例（默认跳过）",
    )


# =====================================================================
# 2) 程序化注册/处理 marker，并实现 --run-sim 的跳过逻辑
#    标了 @pytest.mark.sim 的用例，在没加 --run-sim 时自动 skip。
# =====================================================================
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-sim"):
        return  # 用户显式要求跑仿真，不跳过
    skip_sim = pytest.mark.skip(reason="需要 --run-sim 才运行（依赖真实仿真器）")
    for item in items:
        if "sim" in item.keywords:
            item.add_marker(skip_sim)


# =====================================================================
# 3) Fixture：被测对象——APB 黄金模型
#    scope="function"（默认）：每个测试函数都拿到一个全新、干净的模型，
#    保证用例之间互不影响（测试隔离性，非常重要）。
# =====================================================================
@pytest.fixture
def model() -> ApbSlaveModel:
    """提供一个复位后的 APB 从机模型。"""
    m = ApbSlaveModel()
    m.reset()
    return m
    # 这里没有 teardown：Python 对象用完会被垃圾回收，无需手动清理。


# =====================================================================
# 4) Fixture：演示 yield 写法（带 setup + teardown）
#    yield 之前是 setup，yield 之后是 teardown（即使用例失败也会执行）。
# =====================================================================
@pytest.fixture
def report_dir() -> Path:
    """提供（并确保存在）报告输出目录。"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    yield REPORT_DIR
    # teardown 位置：这里我们故意不删报告，留给用户查看。
    # 真实项目里可能在这里关闭文件、断开连接、清理临时目录等。


# =====================================================================
# 5) Fixture：仿真器句柄
#    scope="session"：整个 pytest 进程只创建一次（仿真器编译很贵，
#    不该每个用例都重来）。
# =====================================================================
@pytest.fixture(scope="session")
def simulator() -> Simulator:
    return Simulator()


@pytest.fixture(scope="session")
def require_sim(simulator: Simulator, request: pytest.FixtureRequest) -> Simulator:
    """
    依赖真实仿真器的用例可以 `def test_x(require_sim):` 直接拿到 simulator，
    若机器上没有仿真器则自动 skip（fixture 里也能 skip，很常用）。
    """
    if not request.config.getoption("--run-sim"):
        pytest.skip("未加 --run-sim")
    if not simulator.is_available():
        pytest.skip("当前机器未检测到可用的仿真器(make + vcs/simv)")
    return simulator


# =====================================================================
# 6) Fixture：常用目录
# =====================================================================
@pytest.fixture(scope="session")
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture(scope="session")
def sample_log(data_dir: Path) -> Path:
    """示例 UVM 日志（无需仿真器即可练习"日志解析/数据分析"）。"""
    return data_dir / "sample_sim.log"


# =====================================================================
# 7) Hook：往 pytest-html 报告里加一列"环境信息"
#    optionalhook=True 是关键：这个 hook 由 pytest-html 插件定义，
#    没装该插件时 pytest 不认识这个名字。加了 optionalhook 标记，
#    pytest 就会"没装就忽略"，而不是抛 unknown hook 的校验错误。
# =====================================================================
@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(report) -> None:    # noqa: ANN001 (pytest-html 提供)
    report.title = "APB pyverif 测试报告"
