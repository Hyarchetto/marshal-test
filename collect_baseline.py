#!/usr/bin/env python3
"""
在 Python 3.12 环境运行此脚本，重新采集所有基准哈希值。
要求: PYTHONHASHSEED=1 环境变量已设置

用法:
    set PYTHONHASHSEED=1 && python collect_baseline.py > new_baselines.txt

然后将输出的哈希表复制到 tests/test_marshal.py 对应位置。
"""

import sys
import marshal
import hashlib
import random
import platform

# 确保 PYTHONHASHSEED 已固定
import os
if os.environ.get("PYTHONHASHSEED", "") != "1":
    print("警告: PYTHONHASHSEED 未设置为 1，set/dict 哈希将不可重现！")
    print("请设置环境变量 PYTHONHASHSEED=1 后重新运行\n", file=sys.stderr)

expected_version = "3.12"
current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
if current_version != expected_version:
    print(f"警告: 当前 Python 版本为 {current_version}，期望 {expected_version}")
    print("采集的哈希用于 Python 3.12 基准\n", file=sys.stderr)

# ============================================================
# 静态用例定义
# ============================================================

def _make_recursive_list():
    a = [1, 2, 3]
    a.append(a)
    return a

def _make_recursive_dict():
    d = {"a": 1}
    d["self"] = d
    return d

def _make_deep_list(depth):
    if depth == 0:
        return []
    return [_make_deep_list(depth - 1)]

def _make_deep_dict(depth):
    if depth == 0:
        return {}
    return {"next": _make_deep_dict(depth - 1)}

def _make_deep_mixed():
    return {
        "list": [1, {"tuple": (2, [3, {"dict": {"a": [4]}}])}],
        "nested": {
            "level1": {
                "level2": {
                    "level3": [1, 2, {"key": "value"}]
                }
            }
        }
    }

_STATIC_CASES_DEF = [
    ("none", None),
    ("bool_true", True),
    ("bool_false", False),
    ("int_zero", 0),
    ("int_minus1", -1),
    ("int_small", 42),
    ("int_large", 2**30),
    ("int_huge", 2**100),
    ("int_negative_huge", -(2**100)),
    ("int_maxsize", sys.maxsize),
    ("int_minsize", -sys.maxsize - 1),
    ("float_zero", 0.0),
    ("float_negzero", -0.0),
    ("float_small", 1e-308),
    ("float_large", 1e308),
    ("float_inf", float('inf')),
    ("float_neginf", float('-inf')),
    ("float_nan", float('nan')),
    ("float_max", sys.float_info.max),
    ("float_min", sys.float_info.min),
    ("float_epsilon", sys.float_info.epsilon),
    ("complex_zero", 0j),
    ("complex_real", 3+4j),
    ("complex_inf", complex(float('inf'), 0)),
    ("complex_nan", complex(float('nan'), 1)),
    ("bytes_empty", b""),
    ("bytes_small", b"hello"),
    ("bytes_binary", bytes(range(256))),
    ("bytes_large", b"x" * 10000),
    ("str_empty", ""),
    ("str_ascii", "hello world"),
    ("str_unicode", "你好世界 🌍 αβγ"),
    ("str_special", "\x00\x01\x02\x03\x7f"),
    ("str_large", "a" * 10000),
    ("tuple_empty", ()),
    ("tuple_single", (1,)),
    ("tuple_nested", (1, (2, (3,)))),
    ("tuple_mixed", (None, 42, 3.14, b"x", "y", (1, 2))),
    ("list_empty", []),
    ("list_single", [1]),
    ("list_nested", [1, [2, [3]]]),
    ("list_mixed", [None, 42, 3.14, b"x", "y", [1, 2]]),
    ("list_large", list(range(1000))),
    ("set_empty", set()),
    ("set_small", {1, 2, 3}),
    ("set_mixed", {None, 42, b"x", "y"}),
    ("set_large", set(range(100))),
    ("dict_empty", {}),
    ("dict_single", {"a": 1}),
    ("dict_nested", {"a": {"b": {"c": 3}}}),
    ("dict_mixed", {
        None: 1,
        42: "answer",
        3.14: b"pi",
        b"key": [1, 2, 3],
        "nested": {"x": 1, "y": 2},
    }),
    ("dict_large", {f"key_{i}": i for i in range(1000)}),
    ("recursive_list", _make_recursive_list()),
    ("recursive_dict", _make_recursive_dict()),
    ("deep_list_10", _make_deep_list(10)),
    ("deep_dict_10", _make_deep_dict(10)),
    ("deep_mixed", _make_deep_mixed()),
]


def _compute_hash(obj):
    return hashlib.sha256(marshal.dumps(obj)).hexdigest()


def generate_fuzz_data(max_depth=8, current_depth=0, for_set=False, for_dict_key=False):
    """同 test_marshal.py 中的生成器"""
    if for_set or for_dict_key:
        if current_depth >= max_depth:
            return random.choice([
                lambda: None,
                lambda: random.randint(-2**30, 2**30),
                lambda: random.uniform(-1e10, 1e10),
                lambda: random.random() * 1j + random.random(),
                lambda: bytes([random.randint(0, 255) for _ in range(random.randint(0, 20))]),
                lambda: ''.join(chr(random.randint(32, 126)) for _ in range(random.randint(0, 20))),
            ])()

        choices = [
            lambda: None,
            lambda: random.randint(-2**62, 2**62),
            lambda: random.choice([
                float('inf'), float('-inf'), float('nan'),
                sys.float_info.max, sys.float_info.min,
                random.uniform(-1e308, 1e308),
                0.0, -0.0,
            ]),
            lambda: complex(
                random.choice([0, 1, -1, random.random(), float('inf'), float('nan')]),
                random.choice([0, 1, -1, random.random(), float('inf'), float('nan')])
            ),
            lambda: b'' if random.random() < 0.3 else bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]),
            lambda: '' if random.random() < 0.3 else ''.join(
                chr(random.randint(1, 0x10FFFF)) for _ in range(random.randint(1, 50))
            ),
            lambda: tuple(generate_fuzz_data(max_depth, current_depth + 1, for_set=True) for _ in range(random.randint(0, 5))),
        ]
        return random.choice(choices)()

    if current_depth >= max_depth:
        return random.choice([
            lambda: None,
            lambda: random.randint(-2**30, 2**30),
            lambda: random.uniform(-1e10, 1e10),
            lambda: random.random() * 1j + random.random(),
            lambda: bytes([random.randint(0, 255) for _ in range(random.randint(0, 20))]),
            lambda: ''.join(chr(random.randint(32, 126)) for _ in range(random.randint(0, 20))),
        ])()

    choices = [
        lambda: None,
        lambda: random.randint(-2**62, 2**62),
        lambda: random.choice([
            float('inf'), float('-inf'), float('nan'),
            sys.float_info.max, sys.float_info.min,
            random.uniform(-1e308, 1e308),
            0.0, -0.0,
        ]),
        lambda: complex(
            random.choice([0, 1, -1, random.random(), float('inf'), float('nan')]),
            random.choice([0, 1, -1, random.random(), float('inf'), float('nan')])
        ),
        lambda: b'' if random.random() < 0.3 else bytes([random.randint(0, 255) for _ in range(random.randint(1, 100))]),
        lambda: '' if random.random() < 0.3 else ''.join(
            chr(random.randint(1, 0x10FFFF)) for _ in range(random.randint(1, 50))
        ),
        lambda: tuple(generate_fuzz_data(max_depth, current_depth + 1) for _ in range(random.randint(0, 5))),
        lambda: [generate_fuzz_data(max_depth, current_depth + 1) for _ in range(random.randint(0, 5))],
        lambda: {generate_fuzz_data(max_depth, current_depth + 1, for_set=True) for _ in range(random.randint(0, 5))},
        lambda: {
            generate_fuzz_data(max_depth, current_depth + 1, for_dict_key=True): generate_fuzz_data(max_depth, current_depth + 1)
            for _ in range(random.randint(0, 5))
        },
    ]
    return random.choice(choices)()


# ============================================================
# 采集逻辑
# ============================================================

print(f"# Python {current_version} 基线哈希表")
print(f"# 平台: {platform.system()} {platform.machine()}")
print(f"# PYTHONHASHSEED={os.environ.get('PYTHONHASHSEED', '未设置')}")
print(f"# marshal.version = {marshal.version}")
print()

# --- 静态用例 ---
print("STATIC_BASELINE_HASHES = {")
for name, obj in _STATIC_CASES_DEF:
    h = _compute_hash(obj)
    print(f'    "{name}": "{h}",')
print("}")

# --- Fuzzer ---
GLOBAL_SEED = 42
FUZZER_ITERATIONS = 50
random.seed(GLOBAL_SEED)
print()
print("FUZZER_BASELINE_HASHES = [")
for i in range(FUZZER_ITERATIONS):
    fuzz_obj = generate_fuzz_data(max_depth=6)
    h = _compute_hash(fuzz_obj)
    print(f'    "{h}",  # iter {i}')
print("]")
