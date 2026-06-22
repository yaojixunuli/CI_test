"""
model.py —— APB Slave 的"黄金参考模型"（纯 Python）

对应 SystemVerilog 源码：
    rtl/apb_slave.sv     真正的 DUT（16 个 32 位寄存器）
    uvm/apb_model.sv     UVM 里的参考模型（mirror[16]）

什么是"参考模型 / 黄金模型"？
    它是 DUT 行为的一份独立、可信实现。验证时让激励同时喂给 DUT 和模型，
    再用 scoreboard 比较两者输出是否一致。这里我们直接用这个模型来做
    寄存器/性能测试，省去仿真器。

DUT 行为（来自 apb_slave.sv）：
    - 16 个寄存器，地址用 paddr[5:2] 索引；
    - 写：psel && penable && pwrite 时 mem[idx] <= pwdata；
    - 读：psel && !pwrite 时 prdata = mem[idx]（组合逻辑）；
    - 复位（prst_n=0）：所有寄存器清零；
    - pready 恒为 1，pslverr 恒为 0（即从不插入等待、从不报错）。
"""

from __future__ import annotations

from dataclasses import dataclass

from .transaction import ApbTransaction, DATA_MASK

# --- 一些与硬件对应的常量 ------------------------------------------------
NUM_REGS = 16            # apb_slave 里 reg[31:0] mem[15:0]
APB_CLOCK_NS = 10.0      # top_tb.sv: `forever #5 pclk=~pclk` -> 周期 10ns (100MHz)

# 一笔 APB 传输占用的时钟周期数。
# 看 apb_driver.sv 的 drive_one_pkt：
#   SETUP  : 拉高 psel，等 1 个时钟沿
#   ACCESS : 拉高 penable，等 1 个时钟沿；pready=1 所以不再等待
#   结束   : 拉低 psel/penable，等 1 个时钟沿
# 因此每笔事务约占 3 个时钟（这是一个便于教学的近似值）。
CYCLES_PER_XFER = 3


@dataclass
class TransferResult:
    """一次 access() 的结果，既有功能数据也有时序信息（给性能测试用）。"""
    transaction: ApbTransaction
    rdata: int            # 读回的数据（写事务时等于写入值）
    cycles: int           # 本次传输占用的时钟周期
    latency_ns: float     # 折算成纳秒的延迟


class ApbSlaveModel:
    """
    APB Slave 的纯 Python 模型。

    典型用法：
        m = ApbSlaveModel()
        m.write(0x04, 0xDEAD_BEEF)
        assert m.read(0x04) == 0xDEAD_BEEF

    或者用统一的 access() 接口（同时拿到时序信息）：
        res = m.access(ApbTransaction(write=True, addr=0x04, data=0x1))
    """

    def __init__(self) -> None:
        self.regs = [0] * NUM_REGS     # 16 个 32 位寄存器，复位值全 0
        self.xfer_count = 0            # 累计事务数（性能/统计用）
        self.cycle_count = 0           # 累计时钟周期

    # ---- 复位 -----------------------------------------------------------
    def reset(self) -> None:
        """对应 prst_n=0：所有寄存器清零。"""
        self.regs = [0] * NUM_REGS

    # ---- 底层读写 -------------------------------------------------------
    def write(self, addr: int, data: int) -> None:
        """写一个寄存器（不返回时序信息的便捷接口）。"""
        idx = (addr >> 2) & 0xF
        self.regs[idx] = data & DATA_MASK
        self._tick()

    def read(self, addr: int) -> int:
        """读一个寄存器，返回 32 位数据。"""
        idx = (addr >> 2) & 0xF
        self._tick()
        return self.regs[idx]

    # ---- 统一事务接口（功能 + 时序）------------------------------------
    def access(self, tr: ApbTransaction) -> TransferResult:
        """
        执行一笔事务，返回 TransferResult。
        这是给 scoreboard 风格比较、以及性能测试用的主接口。
        """
        if tr.write:
            self.write(tr.addr, tr.data)
            rdata = tr.data & DATA_MASK
        else:
            rdata = self.read(tr.addr)
        return TransferResult(
            transaction=tr,
            rdata=rdata,
            cycles=CYCLES_PER_XFER,
            latency_ns=CYCLES_PER_XFER * APB_CLOCK_NS,
        )

    # ---- 内部计数 -------------------------------------------------------
    def _tick(self) -> None:
        self.xfer_count += 1
        self.cycle_count += CYCLES_PER_XFER

    @property
    def elapsed_ns(self) -> float:
        """从复位以来累计的仿真时间（ns）。"""
        return self.cycle_count * APB_CLOCK_NS
