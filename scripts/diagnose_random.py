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
for i in range(5):
    obj = generate_fuzz_data(max_depth=6)
    h = _compute_hash(obj)
    t = type(obj).__name__
    print(f"  iter {i}: type={t:>8s}  marshal_hash={h}")
    if hasattr(obj, '__len__'):
        print(f"           len={len(obj)}")
