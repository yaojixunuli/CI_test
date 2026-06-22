"""
test_registers.py —— 寄存器读写测试（重点演示"参数化"）

对应学习思路："寄存器测试：读取寄存器值、比对预期、记录异常"

本文件的主角是 @pytest.mark.parametrize ——pytest 最强大的特性之一：
    用一份测试逻辑，自动展开成很多个独立用例（每个参数一个用例，
    失败互不影响、各自计入统计）。这正是验证里"数据驱动测试"的思路，
    和 SV 里 `for` 循环 + 约束随机异曲同工，但可读性和报告更好。

运行：
    pytest tests/test_registers.py -v      # -v 可看到每个参数展开的用例名
"""

import pytest

from apb import ApbSlaveModel, ApbTransaction
from apb.model import NUM_REGS

# DUT 合法地址：0x00, 0x04, ... 0x3C（16 个），见 apb_transaction 约束。
ALL_ADDRS = [i << 2 for i in range(NUM_REGS)]

# 典型测试数据：边界值 + 几个"花样"值。对应覆盖率里的 zero/ones/others。
PATTERNS = {
    "zero": 0x0000_0000,
    "ones": 0xFFFF_FFFF,
    "walking_1": 0x0000_0001,
    "walking_0": 0xFFFF_FFFE,
    "aa55": 0xAAAA_5555,
    "deadbeef": 0xDEAD_BEEF,
}


# --- 1) 对单个地址参数化：遍历全部 16 个寄存器 -------------------------
@pytest.mark.reg
@pytest.mark.parametrize("addr", ALL_ADDRS)
def test_write_then_read_each_reg(model: ApbSlaveModel, addr):
    """每个寄存器都做一次"写入 0xA5A5_0000+idx 再读回"。"""
    expected = 0xA5A5_0000 + (addr >> 2)
    model.write(addr, expected)
    actual = model.read(addr)
    assert actual == expected, f"reg@0x{addr:02x} 期望 0x{expected:08x} 实得 0x{actual:08x}"


# --- 2) 对数据 pattern 参数化（用 ids 让报告更易读）-------------------
@pytest.mark.reg
'''
遍历字典 PATTERNS 中的每一项，把字典的值（values()）作为测试数据传给参数 value，
同时把字典的键（keys()）作为这个测试用例的显示名称（ID）。
'''
@pytest.mark.parametrize("value", PATTERNS.values(), ids=PATTERNS.keys())
def test_data_patterns(model: ApbSlaveModel, value):
    """固定地址，写入各种典型数据再读回。"""
    model.write(0x10, value)
    assert model.read(0x10) == value


# --- 3) 二维参数化：地址 × 数据 的笛卡尔积（共 16×6=96 个用例）-------
# 叠加多个 @parametrize 会自动求笛卡尔积——一行代码生成上百个用例。
@pytest.mark.reg
@pytest.mark.parametrize("value", PATTERNS.values(), ids=PATTERNS.keys())
@pytest.mark.parametrize("addr", ALL_ADDRS)
def test_addr_data_cross(model: ApbSlaveModel, addr, value):
    model.write(addr, value)
    assert model.read(addr) == value


# --- 4) 寄存器之间互不串扰（aliasing 检查）-----------------------------
@pytest.mark.reg
def test_no_aliasing(model: ApbSlaveModel):
    """给每个寄存器写入唯一值，最后一次性读回，确认没有相互覆盖。"""
    for addr in ALL_ADDRS:
        model.write(addr, 0x1000 + (addr >> 2))
    for addr in ALL_ADDRS:
        assert model.read(addr) == 0x1000 + (addr >> 2)


# --- 5) 复位行为：写入后复位应全部清零 ---------------------------------
@pytest.mark.reg
def test_reset_clears_all(model: ApbSlaveModel):
    for addr in ALL_ADDRS:
        model.write(addr, 0xFFFF_FFFF)
    model.reset()
    for addr in ALL_ADDRS:
        assert model.read(addr) == 0


# --- 6) "记录异常"：用类组织一组相关用例 ------------------------------
# 对应学习思路里的"类组织"。同一个类里的方法共享 marker，逻辑上聚合。
@pytest.mark.reg
class TestRegisterCornerCases:
    """寄存器的边角场景集合。"""

    def test_overwrite(self, model: ApbSlaveModel):
        """同地址连续写，后写覆盖前写。"""
        model.write(0x08, 0x1111_1111)
        model.write(0x08, 0x2222_2222)
        assert model.read(0x08) == 0x2222_2222

    def test_read_does_not_modify(self, model: ApbSlaveModel):
        """读操作不应改变寄存器内容（连读两次结果一致）。"""
        model.write(0x0C, 0x5A5A_5A5A)
        first = model.read(0x0C)
        second = model.read(0x0C)
        assert first == second == 0x5A5A_5A5A

    def test_full_register_sweep_via_transaction(self, model: ApbSlaveModel):
        """用 ApbTransaction + access() 接口跑一遍全寄存器，模拟 scoreboard 比较。"""
        mismatches = []
        for addr in ALL_ADDRS:
            wr = ApbTransaction(write=True, addr=addr, data=0xC0DE_0000 + (addr >> 2))
            model.access(wr)
            rd = model.access(ApbTransaction(write=False, addr=addr))
            if rd.rdata != wr.data:
                mismatches.append((addr, wr.data, rd.rdata))
        # 一次性断言所有不匹配项，报告里能看到完整清单（比逐个 assert 更友好）
        assert not mismatches, f"发现 {len(mismatches)} 处不匹配: {mismatches}"
