#!/usr/bin/env python3
"""
诊断：验证 random.seed(42) 在不同 Python 版本/OS 上是否产生相同序列。
用于 CI 中排查 fuzzer 跨 OS 不一致的根因。
"""
import random
import sys

print(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
print(f"sys.version: {sys.version.strip()}")
print()

random.seed(42)
print("random.seed(42) 前 5 个 random.random():")
for i in range(5):
    print(f"  #{i}: {random.random()}")

random.seed(42)
print("\nrandom.seed(42) 前 5 个 random.randint(0, 100):")
for i in range(5):
    print(f"  #{i}: {random.randint(0, 100)}")

random.seed(42)
print("\nrandom.seed(42) 前 5 个 random.choice 的类型:")
choices = ["int", "float", "str", "bytes", "None", "list", "tuple"]
for i in range(5):
    print(f"  #{i}: {random.choice(choices)}")

# 验证 PYTHONHASHSEED 是否真的生效
print("\n=== PYTHONHASHSEED 验证 ===")
import os
print(f"PYTHONHASHSEED env = {os.environ.get('PYTHONHASHSEED', 'NOT SET')}")

# 测试字符串/bytes 的 hash 是否跨平台一致
test_strings = ["hello", "world", "x", "", "你好"]
for s in test_strings:
    print(f"  hash({s!r}) = {hash(s)}")

test_bytes = [b"hello", b"x", b""]
for b in test_bytes:
    print(f"  hash({b!r}) = {hash(b)}")

# 测试 set 迭代顺序
s = {None, 42, b"x", "y"}
print(f"\n  set_mixed 迭代顺序: {list(s)}")
# marshal 该 set 并打印哈希
import marshal, hashlib
h = hashlib.sha256(marshal.dumps(s)).hexdigest()
print(f"  set_mixed marshal hash: {h}")

# 测试 dict 迭代顺序
d = {None: 1, 42: "answer", 3.14: b"pi"}
print(f"  dict_mixed 迭代顺序 keys: {list(d.keys())}")
h2 = hashlib.sha256(marshal.dumps(d)).hexdigest()
print(f"  dict_mixed marshal hash: {h2}")

# 直接跑 fuzzer 前 5 次迭代，看生成的对象和 marshal 哈希
print()
print("=== Fuzzer 前 5 次迭代 ===")
import sys as _sys
_sys.path.insert(0, "tests")
from test_marshal import generate_fuzz_data, _compute_hash

random.seed(42)
for i in range(10):
    obj = generate_fuzz_data(max_depth=6)
    h = _compute_hash(obj)
    t = type(obj).__name__
    non_det = " <-" if type(obj).__name__ in ('set','dict') or (type(obj).__name__ == 'float' and obj != obj) else ""
    print(f"  iter {i:2d}: type={t:>8s}  marshal_hash={h}{non_det}")
    if hasattr(obj, '__len__') and not isinstance(obj, (str, bytes)):
        print(f"           len={len(obj)}")
    elif isinstance(obj, (str, bytes)):
        el = repr(obj)[:60] if len(obj) > 5 else repr(obj)
        print(f"           val={el}")

# 验证 NaN 和特殊浮点数的跨平台编码
print()
print("=== 特殊浮点数跨平台编码验证 ===")
special_floats = [float('nan'), float('inf'), float('-inf'), -0.0, 0.0]
for f in special_floats:
    h = _compute_hash(f)
    print(f"  marshal({f!r:>8s}): {h}")

# 验证 complex(NaN)
nan = float('nan')
special_complexes = [complex(nan, 0), complex(0, nan), complex(nan, nan)]
for c in special_complexes:
    h = _compute_hash(c)
    print(f"  marshal({c!r}): {h}")

# 验证含 NaN 的 list/tuple 编码
print()
print("=== 含 NaN 的容器编码验证 ===")
nan_container = [1.0, float('nan'), 2.0]
h = _compute_hash(nan_container)
print(f"  list [1.0, nan, 2.0]: {h}")

nan_tuple = (1.0, float('nan'), 2.0)
h = _compute_hash(nan_tuple)
print(f"  tuple (1.0, nan, 2.0): {h}")
