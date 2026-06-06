#!/usr/bin/env python3
"""
诊断 iter 8 的逐层 marshal hash，帮助定位跨平台差异来源。
在 macOS 和 Windows 上分别运行，对比每层输出。
"""
import sys, os, random, hashlib, marshal
sys.path.insert(0, 'tests')
from test_marshal import generate_fuzz_data

random.seed(42)

# 跳到 iter 6
for _ in range(6):
    generate_fuzz_data(max_depth=6)
obj6 = generate_fuzz_data(max_depth=6)   # iter 6: set
obj7 = generate_fuzz_data(max_depth=6)   # iter 7: complex
obj8 = generate_fuzz_data(max_depth=6)   # iter 8: tuple

def mhash(obj):
    return hashlib.sha256(marshal.dumps(obj)).hexdigest()

# █ ==================== 环境信息 ====================
print('=' * 60)
print('环境信息')
print('=' * 60)
print(f'Python: {sys.version}')
print(f'PYTHONHASHSEED: {os.environ.get("PYTHONHASHSEED", "NOT SET")}')
print(f'Platform: {sys.platform}')
print(f'hash(None) = {hash(None)}')
print(f'hash(None) & 7 = {hash(None) & 7}')
print()

# █ ==================== iter 6 (全 set) ====================
print('=' * 60)
print('iter 6 — set (对照: 已知两边一致)')
print('=' * 60)
print(f'marshal hash = {mhash(obj6)}')
print(f'元素: {list(obj6)}')
for e in obj6:
    print(f'  {type(e).__name__:8s} hash={hash(e):20d} hash&7={hash(e)&7} val={repr(e)[:60]}')
print()

# █ ==================== iter 8 拆解 ====================
print('=' * 60)
print('iter 8 — 逐层 marshal hash')
print('=' * 60)
print(f'整体 tuple: {mhash(obj8)}')

t0 = obj8[0]   # list
t1 = obj8[1]   # int

print(f'  tuple[0] = list(len={len(t0)}):    {mhash(t0)}')
for i, e in enumerate(t0):
    h = mhash(e)
    t = type(e).__name__
    mark = '  ← 重点关注' if isinstance(e, (set, dict)) else ''
    print(f'    list[{i}] {t:8s}: {h}{mark}')

print(f'  tuple[1] = int:                  {mhash(t1)}')
print()

# █ ==================== 重点: 嵌套 set ====================
for i, e in enumerate(t0):
    if isinstance(e, set):
        print(f'▼ list[{i}] = set(len={len(e)}) 逐元素:')
        print(f'  marshal hash = {mhash(e)}')
        print(f'  iteration order = {list(e)}')
        for el in e:
            print(f'    {type(el).__name__:8s} hash={hash(el):20d} hash&7={hash(el)&7} val={repr(el)[:50]}')
        print()

# █ ==================== 重点: 嵌套 dict ====================
for i, e in enumerate(t0):
    if isinstance(e, dict):
        print(f'▼ list[{i}] = dict(len={len(e)}) 逐元素:')
        print(f'  marshal hash = {mhash(e)}')
        for k, v in e.items():
            print(f'    key {type(k).__name__:8s} hash={hash(k):20d} hash&7={hash(k)&7} val={repr(k)[:30]}')
            print(f'    val {type(v).__name__:8s}                                       val={repr(v)[:30]}')
        print()

# █ ==================== 全部子元素各自序列化 ====================
print('=' * 60)
print('全部子元素独立 marshal hash')
print('=' * 60)
# 递归遍历所有元素
def walk(obj, path='root', depth=0):
    if depth > 4:
        return
    prefix = '  ' * depth
    if isinstance(obj, (list, tuple)):
        print(f'{prefix}{path} ({type(obj).__name__}) -> {mhash(obj)}')
        for i, e in enumerate(obj):
            walk(e, f'{path}[{i}]', depth + 1)
    elif isinstance(obj, set):
        print(f'{prefix}{path} (set) -> {mhash(obj)}')
        for i, e in enumerate(obj):
            walk(e, f'{path}.elem[{i}]', depth + 1)
    elif isinstance(obj, dict):
        print(f'{prefix}{path} (dict) -> {mhash(obj)}')
        for k, v in obj.items():
            walk(k, f'{path}.key({repr(k)[:20]})', depth + 1)
            walk(v, f'{path}.val[{repr(k)[:20]}]', depth + 1)
    else:
        print(f'{prefix}{path} ({type(obj).__name__}) -> {mhash(obj)}')

walk(obj8)
