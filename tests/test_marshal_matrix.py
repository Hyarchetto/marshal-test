"""
验证测试矩阵环境的简易测试
打印运行环境信息和 marshal 基础功能

用法:
    pytest test_marshal_matrix.py -v
    python test_marshal_matrix.py            # 直接运行输出 JSON 报告
"""

import marshal
import io
import sys
import platform
import struct
import json
from datetime import datetime


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


def test_marshal_platform_specific():
    """测试平台相关特性——输出平台标识"""

    print(f"\n  --- 平台特定信息 ---")
    print(f"  字节序: {'大端' if sys.byteorder == 'big' else '小端'}")
    print(f"  指针大小: {struct.calcsize('P') * 8} 位")
    print(f"  浮点精度: {sys.float_info.dig} 位十进制数字")
    print(f"  最大递归深度: {sys.getrecursionlimit()}")
    print(f"  -------------------\n")
    assert True


# ============================================================
# 结构化报告输出（直接运行时）
# ============================================================

def run_matrix_report():
    """
    直接运行时生成结构化 JSON 报告。
    执行所有矩阵验证测试并输出环境信息 + 测试结果。
    """
    print(f"\n{'='*68}")
    print(f"  marshal 矩阵环境验证报告")
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}  |  {platform.system()}")
    print(f"{'='*68}\n")

    # 环境信息
    env_info = {
        "python_version": sys.version,
        "python_version_short": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "platform_release": platform.release(),
        "machine": platform.machine(),
        "node": platform.node(),
        "architecture": f"{struct.calcsize('P') * 8}-bit",
        "byteorder": sys.byteorder,
        "pointer_size": struct.calcsize('P') * 8,
        "float_digits": sys.float_info.dig,
        "recursion_limit": sys.getrecursionlimit(),
        "timestamp": datetime.now().isoformat(),
    }

    print(f"  Python 版本 : {env_info['python_version_short']}")
    print(f"  操作系统    : {env_info['platform']} {env_info['platform_release']}")
    print(f"  架构        : {env_info['architecture']}, {env_info['byteorder']} 字节序")
    print(f"  机器        : {env_info['machine']}")
    print(f"  节点名      : {env_info['node']}")
    print()

    # ---- 运行测试 ----
    test_results = []

    # 测试 1: hello_world
    try:
        assert True
        test_results.append({
            "test": "test_hello_world",
            "status": "passed",
            "description": "基本 pytest 环境验证",
            "error": None,
        })
        print("  ✓ test_hello_world")
    except Exception as e:
        test_results.append({
            "test": "test_hello_world",
            "status": "failed",
            "description": "基本 pytest 环境验证",
            "error": str(e),
        })
        print("  ✗ test_hello_world")

    # 测试 2: marshal basic 序列化/反序列化
    basic_data = [
        None, True, False, 42, -1, 3.14159,
        "hello marshal", b"bytes", [1, 2, 3], {"a": 1},
    ]
    basic_errors = []
    for obj in basic_data:
        try:
            buf = io.BytesIO()
            marshal.dump(obj, buf)
            buf.seek(0)
            loaded = marshal.load(buf)
            assert type(loaded) is type(obj), f"类型不匹配: {type(obj)} -> {type(loaded)}"
        except Exception as e:
            basic_errors.append(f"{obj!r}: {e}")

    if not basic_errors:
        test_results.append({
            "test": "test_marshal_basic",
            "status": "passed",
            "description": "基本类型序列化/反序列化 (10 种类型)",
            "error": None,
            "details": {"types_tested": len(basic_data)},
        })
        print(f"  ✓ test_marshal_basic  (10 种类型全部通过)")
    else:
        test_results.append({
            "test": "test_marshal_basic",
            "status": "failed",
            "description": "基本类型序列化/反序列化",
            "error": "; ".join(basic_errors),
            "details": {"types_tested": len(basic_data), "errors": basic_errors},
        })
        print(f"  ✗ test_marshal_basic  ({len(basic_errors)} 个错误)")

    # 测试 3: marshal determinism
    obj = {"answer": 42, "nested": [1, 2, 3], "flag": True}
    try:
        buf1 = io.BytesIO()
        marshal.dump(obj, buf1)
        h1 = hash(buf1.getvalue())

        buf2 = io.BytesIO()
        marshal.dump(obj, buf2)
        h2 = hash(buf2.getvalue())

        if h1 == h2:
            test_results.append({
                "test": "test_marshal_determinism",
                "status": "passed",
                "description": "相同输入产生相同 marshal 输出",
                "error": None,
            })
            print("  ✓ test_marshal_determinism")
        else:
            raise AssertionError("相同输入产生了不同的 marshal 输出")
    except Exception as e:
        test_results.append({
            "test": "test_marshal_determinism",
            "status": "failed",
            "description": "相同输入产生相同 marshal 输出",
            "error": str(e),
        })
        print("  ✗ test_marshal_determinism")

    # ---- 汇总 ----
    total = len(test_results)
    passed = sum(1 for t in test_results if t["status"] == "passed")
    failed = total - passed

    print(f"\n  ─── 矩阵环境验证汇总 ───")
    print(f"  总计: {total}  |  通过: {passed}  |  失败: {failed}")

    report = {
        "metadata": env_info,
        "test_results": test_results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
        },
    }

    # 也保存为 JSON 文件
    py_ver_compact = f"{sys.version_info.major}{sys.version_info.minor}"
    report_file = f"marshal_matrix_report_py{py_ver_compact}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"  矩阵报告已保存: {report_file}")
    print(f"{'='*68}\n")

    return report


if __name__ == "__main__":
    run_matrix_report()
