"""
test_smoke.py —— 冒烟测试 / pytest 入门第一课

"冒烟测试"指最基础、最快的一组检查，相当于给电路上电看冒不冒烟。
本文件的真正目的是带新人认识 pytest 最核心的几个概念：

    A. 测试函数：以 test_ 开头，pytest 自动发现
    B. 断言：直接用 Python 的 assert，pytest 会美化失败信息
    C. fixture：用函数参数"注入"共享资源（这里是 model）
    D. 异常断言：pytest.raises 验证"应该报错"的场景
    E. 近似断言：pytest.approx 比较浮点数
    F. marker：给用例打标签，便于分类运行

运行方式：
    pytest tests/test_smoke.py -v
    pytest -m smoke            # 只跑打了 @pytest.mark.smoke 的用例
"""

import pytest

from apb import ApbSlaveModel, ApbTransaction, Direction, APB_CLOCK_NS


# --- A + B：最简单的测试函数 + 断言 -------------------------------------
@pytest.mark.smoke
def test_model_reset_value():
    """复位后所有寄存器应为 0。"""
    m = ApbSlaveModel()
    m.reset()
    # assert 后面可以跟一句说明，失败时会一起打印
    assert all(v == 0 for v in m.regs), "复位后存在非零寄存器"


# --- C：用 fixture 注入被测对象 -----------------------------------------
# 形参名 `model` 必须和 conftest.py 里的 @pytest.fixture 函数名一致，
# pytest 会自动调用那个 fixture 并把返回值传进来。
@pytest.mark.smoke
def test_single_write_read(model: ApbSlaveModel):
    """最基本的一写一读。"""
    model.write(0x04, 0xDEAD_BEEF)
    # assert model.read(0x04) == 0xDEAD_BEEF
    # 失败测试
    assert model.read(0x04) == 0xDEAD_BEED


# --- 验证数据按 32 位回绕（硬件位宽行为）-------------------------------
@pytest.mark.smoke
def test_data_truncated_to_32bit():
    tr = ApbTransaction(write=True, addr=0x00, data=0x1_2345_6789)
    assert tr.data == 0x2345_6789   # 高位被截掉


# --- D：用 pytest.raises 断言"应当抛异常" -------------------------------
@pytest.mark.smoke
def test_illegal_address_is_detected():
    """addr[1:0] != 0 不满足 DUT 约束，is_legal_addr() 应为 False。"""
    tr = ApbTransaction(write=True, addr=0x03, data=0)
    assert not tr.is_legal_addr()


def test_pytest_raises_demo():
    """演示 pytest.raises：访问越界下标应抛 IndexError。"""
    m = ApbSlaveModel()
    with pytest.raises(IndexError):
        _ = m.regs[999]


# --- E：用 pytest.approx 比较浮点 ---------------------------------------
@pytest.mark.smoke
def test_latency_is_approx():
    """一笔事务的延迟 = 3 周期 * 10ns = 30ns。浮点比较要用 approx。"""
    m = ApbSlaveModel()
    res = m.access(ApbTransaction(write=False, addr=0x00))
    assert res.latency_ns == pytest.approx(3 * APB_CLOCK_NS)


# --- F：方向枚举的可读性 -------------------------------------------------
def test_direction_enum():
    wr = ApbTransaction(write=True, addr=0)
    rd = ApbTransaction(write=False, addr=0)
    assert wr.direction is Direction.WRITE
    assert rd.direction is Direction.READ
