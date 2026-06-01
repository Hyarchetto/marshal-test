"""
验证测试矩阵环境的简易测试
打印运行环境信息和 marshal 基础功能
"""

import marshal
import io
import sys
import platform


def test_hello_world():
    """最小的验证测试——确认 pytest 能跑"""
    assert True


def test_environment_info():
    """打印当前运行环境的详细信息"""
    print(f"\n{'='*50}")
    print(f"Python 版本: {sys.version}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"架构: {struct.calcsize('P') * 8}-bit")
    print(f"机器: {platform.machine()}")
    print(f"节点名: {platform.node()}")
    print(f"{'='*50}\n")
    assert True


def test_marshal_basic():
    """测试 marshal 基本序列化/反序列化功能"""
    # 基本数据类型
    data = [
        None,
        True,
        False,
        42,
        -1,
        3.14159,
        "hello marshal",
        b"bytes",
        [1, 2, 3],
        {"a": 1},
    ]

    for obj in data:
        buf = io.BytesIO()
        marshal.dump(obj, buf)
        buf.seek(0)
        loaded = marshal.load(buf)
        assert type(loaded) is type(obj), f"类型不匹配: {type(obj)} -> {type(loaded)}"


def test_marshal_determinism():
    """验证 marshal 在相同环境下输出是否确定"""
    obj = {"answer": 42, "nested": [1, 2, 3], "flag": True}

    buf1 = io.BytesIO()
    marshal.dump(obj, buf1)
    h1 = hash(buf1.getvalue())

    buf2 = io.BytesIO()
    marshal.dump(obj, buf2)
    h2 = hash(buf2.getvalue())

    assert h1 == h2, "相同输入产生了不同的 marshal 输出！"


# 导入 struct（test_environment_info 中使用）
import struct


def test_marshal_platform_specific():
    """测试平台相关特性——输出平台标识"""
    import struct

    print(f"\n  --- 平台特定信息 ---")
    print(f"  字节序: {'大端' if sys.byteorder == 'big' else '小端'}")
    print(f"  指针大小: {struct.calcsize('P') * 8} 位")
    print(f"  浮点精度: {sys.float_info.dig} 位十进制数字")
    print(f"  最大递归深度: {sys.getrecursionlimit()}")
    print(f"  -------------------\n")
    assert True
