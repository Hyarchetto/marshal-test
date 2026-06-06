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
