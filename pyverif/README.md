# pyverif —— APB 验证的 Python / pytest 实践框架

> 面向新人的教学型框架：用 **pytest** 把"回归管理、寄存器测试、性能测试、
> 数据分析、报告生成"这一整套验证自动化流程跑通一遍。配套本项目的
> UVM APB testbench（`rtl/` + `uvm/` + `sim/`）。

---

## 0. 这个框架解决什么问题？

数字验证里，SystemVerilog/UVM 负责"在仿真器里造激励、比对、收覆盖率"，
而 **Python 负责把这些仿真"管起来"**：批量运行、解析日志、统计数据、
出报告、画趋势。本框架就是后者的一个最小但完整的样板。

学习思路 → 本框架对应实现：

| 学习思路 | 在本框架里的位置 |
|---|---|
| pytest 基础：fixture / 参数化 / 断言 | [tests/test_smoke.py](tests/test_smoke.py)、[tests/test_registers.py](tests/test_registers.py) |
| 用例组织：`test_` 前缀 / 类 / `conftest.py` | [conftest.py](conftest.py)、各 `tests/test_*.py` |
| 报告生成：HTML / JUnit XML / 覆盖率 | 见下文 [§4 生成报告](#4-生成报告) |
| 回归测试管理：批量跑、收结果、出报告 | [tests/test_regression.py](tests/test_regression.py)、[scripts/run_regression.py](scripts/run_regression.py) |
| 寄存器测试：读值、比对、记录异常 | [tests/test_registers.py](tests/test_registers.py) |
| 性能测试：延迟 / 带宽 / 压力 | [tests/test_performance.py](tests/test_performance.py) |
| 数据分析：日志解析 / 覆盖率分析 / 趋势可视化 | [apb/log_parser.py](apb/log_parser.py)、[tests/test_log_analysis.py](tests/test_log_analysis.py)、[scripts/analyze_trend.py](scripts/analyze_trend.py) |
| 实践项目：脚本跑 VCS、解析 log、出 HTML | [scripts/run_regression.py](scripts/run_regression.py) |

### 关键设计：为什么不用装仿真器也能学？

本框架用纯 Python 写了一个 **APB 黄金参考模型**（[apb/model.py](apb/model.py)，
对应 `rtl/apb_slave.sv`）。这样：

- 学 pytest 时，所有寄存器/性能/分析用例**秒级跑完，零外部依赖**；
- 需要真实仿真时，把数据来源从"Python 模型"换成"仿真器日志"即可，
  测试逻辑几乎不用改（见 [apb/simulator.py](apb/simulator.py) 和带
  `@pytest.mark.sim` 的用例）。

---

## 1. 目录结构

```
pyverif/
├── README.md                  # 本文档
├── requirements.txt           # Python 依赖
├── pytest.ini                 # pytest 配置（发现规则 / marker / 默认参数）
├── conftest.py                # 共享 fixture（被 pytest 自动加载）
│
├── apb/                       # 验证工具库（被测对象的 Python 抽象）
│   ├── __init__.py
│   ├── transaction.py         # APB 事务数据结构   <- uvm/apb_transaction.sv
│   ├── model.py               # APB 从机黄金模型   <- rtl/apb_slave.sv
│   ├── simulator.py           # 封装 make/VCS 调用 <- sim/makefile
│   └── log_parser.py          # UVM 日志 -> DataFrame
│
├── tests/                     # 所有 pytest 用例
│   ├── test_smoke.py          # 入门：断言 / fixture / raises / approx
│   ├── test_registers.py      # 寄存器读写 + 参数化（重点）
│   ├── test_performance.py    # 延迟 / 带宽 / 压力（pandas 统计）
│   ├── test_coverage.py       # 覆盖率门限 + covergroup 复刻
│   ├── test_log_analysis.py   # 日志解析与数据分析
│   └── test_regression.py     # 回归：离线(日志) + 在线(--run-sim)
│
├── scripts/                   # 可独立运行的命令行脚本
│   ├── run_regression.py      # 一键回归 -> HTML + CSV 报告
│   └── analyze_trend.py       # 覆盖率/失败趋势 -> PNG（matplotlib）
│
├── data/                      # 示例数据（无需仿真器即可练习）
│   ├── sample_sim.log         # 一份样例 UVM 日志
│   └── regression_history.csv # 历史回归数据（趋势图用）
│
└── reports/                   # 运行后自动生成的报告（HTML/CSV/PNG）
```

---

## 2. 安装

> 前提：安装 **Python 3.9+**。Windows 上若 `python` 弹出应用商店，
> 说明装的是占位符，请到 [python.org](https://www.python.org/downloads/)
> 安装真正的 Python，并勾选 *Add Python to PATH*。

```bash
cd pyverif

# （推荐）创建虚拟环境，隔离依赖
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

验证安装：

```bash
pytest --version
```

---

## 3. 运行测试

在 `pyverif/` 目录下执行：

```bash
# 跑全部用例（不含真实仿真，约 1 秒）
pytest

# 看详细用例名（参数化展开的每个用例都会列出）
pytest -v

# 只跑某一类（用 marker 过滤）
pytest -m smoke          # 冒烟
pytest -m reg            # 寄存器
pytest -m perf           # 性能
pytest -m cov            # 覆盖率
pytest -m analysis       # 数据分析

# 跑单个文件 / 单个用例
pytest tests/test_registers.py
pytest tests/test_registers.py::test_no_aliasing
pytest -k "bandwidth"    # 按名字关键字筛选

# 看 print 输出（性能统计等）
pytest -s -m perf
```

### 跑真实仿真（可选，需要 VCS / simv）

带 `@pytest.mark.sim` 的用例默认被跳过。要真正调用仿真器：

```bash
pytest --run-sim -m sim
```

它会通过 [apb/simulator.py](apb/simulator.py) 调用 `sim/makefile` 的
`make com` / `make case0` / `make case1`，再解析日志判定通过与否。
若机器上没有仿真器，这些用例会自动 `skip` 而不是报错。

---

## 4. 生成报告

### 4.1 HTML 报告（pytest-html）

```bash
pytest --html=reports/pytest_report.html --self-contained-html
```

打开 `reports/pytest_report.html` 即可看到每个用例的结果、耗时、日志。

### 4.2 JUnit XML（给 CI / Jenkins 用）

```bash
pytest --junitxml=reports/junit.xml
```

### 4.3 Python 代码覆盖率（pytest-cov）

> 注意：这是 **Python 脚本** 的代码覆盖率，**不是芯片功能覆盖率**。
> 芯片功能覆盖率由 UVM covergroup + `make cov`(urg) 产生。

```bash
pytest --cov=apb --cov-report=html:reports/pycov
```

### 4.4 一键回归报告（自定义脚本）

```bash
# 离线模式：解析样例日志，生成 reports/regression.html + .csv
python scripts/run_regression.py

# 在线模式：真正调用 VCS（需要仿真器）
python scripts/run_regression.py --run-sim
```

### 4.5 趋势可视化

```bash
python scripts/analyze_trend.py
# 生成 reports/trend_coverage.png 和 reports/trend_failures.png
```

---

## 5. 新人学习路线（建议顺序）

1. **[tests/test_smoke.py](tests/test_smoke.py)** —— 先搞懂 pytest 怎么写：
   测试函数、`assert`、fixture 注入、`pytest.raises`、`pytest.approx`。
2. **[conftest.py](conftest.py)** —— 理解 fixture 的作用域(scope)、
   `yield` 式 setup/teardown、自定义命令行选项 `--run-sim`。
3. **[tests/test_registers.py](tests/test_registers.py)** —— 掌握
   `@pytest.mark.parametrize`（一份逻辑展开成上百个用例），这是数据驱动
   测试的核心。
4. **[apb/log_parser.py](apb/log_parser.py) + [tests/test_log_analysis.py](tests/test_log_analysis.py)**
   —— 学会用正则 + pandas 把日志变成可分析、可断言的表格。
5. **[tests/test_performance.py](tests/test_performance.py)** —— 用 pandas
   做延迟分布、带宽、压力统计，并写"性能门限"断言。
6. **[tests/test_coverage.py](tests/test_coverage.py)** —— 理解功能覆盖率
   是怎么从 bin 算出来的，以及覆盖率门禁。
7. **[scripts/](scripts/)** —— 把上面所有东西串成可接入 CI 的命令行工具。

---

## 6. 与 UVM 源码的对应关系（速查）

| Python | SystemVerilog | 说明 |
|---|---|---|
| `apb/transaction.py` | `uvm/apb_transaction.sv` | 事务：write/addr/data + 地址约束 |
| `apb/model.py` | `rtl/apb_slave.sv`、`uvm/apb_model.sv` | 16×32bit 寄存器、读写、复位行为 |
| `apb/log_parser.py` | `uvm/apb_scoreboard.sv`、`apb_coverage.sv` | 解析比较结果与覆盖率消息 |
| `apb/simulator.py` | `sim/makefile` | 封装 `make com/case0/case1/cov` |
| `test_coverage.py` 里的 `_compute_coverage` | `uvm/apb_coverage.sv` 的 covergroup | 复刻 cp_dir / cp_addr / cp_data / cross |
| `test_registers.py` | `uvm/apb_sequence_case0/1.sv` | 把 SV 的 for 循环激励换成参数化用例 |

---

## 7. 常见问题

- **`ModuleNotFoundError: No module named 'apb'`**
  请在 `pyverif/` 目录下运行 `pytest`（这里有 `conftest.py`，pytest 会把
  本目录加入 import 路径）。脚本则已自行处理路径。

- **`pytest` 找不到用例**
  确认文件名是 `test_*.py`、函数名是 `test_*`，且在 `tests/` 目录下。

- **想加新的 case / 新寄存器测试**
  在 `tests/` 下新建 `test_xxx.py`，按现有风格写即可，pytest 会自动发现。
  需要新的共享资源就往 `conftest.py` 加 fixture。
