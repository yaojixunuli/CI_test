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
    assert model.read(0x04) == 0xDEAD_BEEF


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


# =====================================================================
# G：跳过 / 预期失败 练习区
#   跑 `pytest tests/test_smoke.py -v -rsxX` 可看到 skipped / xfail 明细：
#       -rs : 列出 skipped 的原因
#       -rx : 列出 xfailed 的原因
#       -rX : 列出 xpassed（预期失败却通过了）的用例
# =====================================================================
import sys


# G-1：无条件跳过。报告显示 SKIPPED，永远不执行函数体。
@pytest.mark.smoke
@pytest.mark.skip(reason="演示用：该功能尚未实现，先跳过")
def test_skip_demo():
    assert False        # 不会被执行，所以不会失败


# G-2：条件跳过。条件为真才跳；这里在 Windows 上跳过。
@pytest.mark.smoke
@pytest.mark.skipif(sys.platform == "win32", reason="演示用：仅在非 Windows 运行")
def test_skipif_demo():
    assert True


# G-3：运行中跳过。前提条件要在函数内部才知道时用。
@pytest.mark.smoke
def test_runtime_skip_demo(model: ApbSlaveModel):
    if len(model.regs) != 32:                 # 本模型是 16 个寄存器，条件成立
        pytest.skip("演示用：寄存器数不是 32，跳过该用例")
    assert False        # 跳过后不会执行到这里


# G-4：预期失败(xfail)。用例"会跑"，失败算符合预期 → 报告显示 x（不是 F）。
#      适合标注"已知 bug、待修复"的用例：既保留用例、又不让 CI 变红。
@pytest.mark.smoke
@pytest.mark.xfail(reason="演示用：已知该断言会失败（模拟未修复的 bug）")
def test_xfail_demo(model: ApbSlaveModel):
    model.write(0x04, 0xDEAD_BEEF)
    assert model.read(0x04) == 0xDEAD_BEED    # 故意写错，预期失败


# G-5：xfail + strict。strict=True 时，万一"意外通过"会判 FAIL，
#      提醒你"bug 可能已修复，该把 xfail 去掉了"。
@pytest.mark.smoke
@pytest.mark.xfail(reason="演示用：strict 模式", strict=True)
def test_xfail_strict_demo(model: ApbSlaveModel):
    model.write(0x08, 0x1234)
    assert model.read(0x08) == 0xBAD          # 故意写错，确保确实失败
