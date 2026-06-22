"""
apb —— APB 验证用的 Python 工具库
=================================================================

这个包把 SystemVerilog/UVM testbench 里的几个关键概念，用纯 Python
重新实现了一遍，目的是让"新人"在 **不依赖任何商业仿真器** 的情况下，
也能完整地练习 pytest 的全部功能。

模块对照表（Python  <->  UVM 源码）：

    transaction.py   <->  uvm/apb_transaction.sv     一笔 APB 事务的数据结构
    model.py         <->  rtl/apb_slave.sv +          16 个寄存器的"黄金参考模型"
                          uvm/apb_model.sv
    simulator.py     <->  sim/makefile                封装 `make com/case0/...`
    log_parser.py    <->  (解析 sim.log / vcs.log)    把 UVM 日志变成 DataFrame

为什么要做 Python 黄金模型？
    - 学 pytest 时，重点是 fixture / 参数化 / 断言 / 报告，而不是装 VCS。
    - 有了纯 Python 模型，寄存器测试、性能测试可以"秒级"跑完，便于练习。
    - 同一套测试逻辑，将来对接真实仿真器时几乎不用改（见 simulator.py）。
"""

from .transaction import ApbTransaction, Direction
from .model import ApbSlaveModel, APB_CLOCK_NS, NUM_REGS

__all__ = [
    "ApbTransaction",
    "Direction",
    "ApbSlaveModel",
    "APB_CLOCK_NS",
    "NUM_REGS",
]
