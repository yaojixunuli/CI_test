"""
transaction.py —— 一笔 APB 事务的数据结构

对应 SystemVerilog 源码： uvm/apb_transaction.sv

    class apb_transaction extends uvm_sequence_item;
       rand bit       write;        // 1=写, 0=读
       rand bit[31:0] addr;         // 地址
       rand bit[31:0] data;         // 数据
       constraint addr_range { addr[31:6] == 0; addr[1:0] == 0; }
    endclass

我们用 Python 的 dataclass 来表达同样的东西。dataclass 会自动帮我们
生成 __init__ / __repr__ / __eq__，非常适合做这种"纯数据"对象。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Direction(IntEnum):
    """读写方向。用 IntEnum 是为了既能当数字（0/1）又有可读的名字。"""
    READ = 0
    WRITE = 1


# DUT（apb_slave）的地址约束：addr[31:6]==0 且 addr[1:0]==0
# 也就是说合法地址是 0x00, 0x04, 0x08, ... 0x3C 共 16 个。
ADDR_MASK_HIGH = 0xFFFFFFC0   # bit[31:6] 必须为 0
ADDR_MASK_LOW = 0x00000003    # bit[1:0]  必须为 0
DATA_WIDTH = 32
DATA_MASK = (1 << DATA_WIDTH) - 1   # 0xFFFF_FFFF


@dataclass
class ApbTransaction:
    """
    一笔 APB 读/写事务。

    字段：
        write : True=写, False=读        （对应 SV 的 bit write）
        addr  : 32 位地址               （对应 SV 的 bit[31:0] addr）
        data  : 32 位数据               （写时为写入值；读时为期望/读回值）

    例子：
        >>> wr = ApbTransaction(write=True, addr=0x04, data=0x1234_5678)
        >>> rd = ApbTransaction(write=False, addr=0x04)
    """

    write: bool
    addr: int
    data: int = 0

    # frozen=False（默认），允许我们在读事务回来后回填 data。
    # 下面这个字段不是 APB 信号，只是给报告用的可选备注。
    note: str = field(default="", compare=False)

    @property
    def direction(self) -> Direction:
        return Direction.WRITE if self.write else Direction.READ

    @property
    def reg_index(self) -> int:
        """
        DUT 用 paddr[5:2] 作为 16 个寄存器的下标。
        即 addr=0x00->0, 0x04->1, 0x08->2 ... 0x3C->15。
        """
        return (self.addr >> 2) & 0xF

    def is_legal_addr(self) -> bool:
        """是否满足 apb_transaction 里的 addr_range 约束。"""
        return (self.addr & ADDR_MASK_HIGH) == 0 and (self.addr & ADDR_MASK_LOW) == 0

    def __post_init__(self) -> None:
        # 把 data 截断到 32 位，模拟硬件位宽自动回绕的行为，
        # 这样测试里写 0x1_0000_0000 不会"溢出"成 Python 大整数。
        self.data &= DATA_MASK

    def __repr__(self) -> str:  # 让打印更像波形/日志
        kind = "WR" if self.write else "RD"
        return f"<{kind} addr=0x{self.addr:08x} data=0x{self.data:08x}>"
