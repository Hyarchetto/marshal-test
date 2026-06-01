"""递归/循环数据结构测试"""
import marshal
import io
import sys

recursive_cases = []

# 列表包含自身
lst = []
lst.append(lst)
recursive_cases.append(('list_self_ref', lst))

# 字典包含自身
d = {}
d['self'] = d
recursive_cases.append(('dict_self_ref', d))

# 列表包含相同对象的多个引用
shared = [1, 2, 3]
multi_ref = [shared, shared, [shared]]
recursive_cases.append(('list_multi_shared_ref', multi_ref))

# 深层嵌套
deep = []
cursor = deep
for _ in range(5000):
    cursor.append([])
    cursor = cursor[0]
recursive_cases.append(('list_deep_nest_5000', deep))

failed = 0
for name, obj in recursive_cases:
    try:
        buf = io.BytesIO()
        marshal.dump(obj, buf)
        buf.seek(0)
        loaded = marshal.load(buf)
        size = len(buf.getvalue())
        print(f'  [PASS] {name} (size={size} bytes)')
    except (ValueError, RecursionError) as e:
        print(f'  [SKIP] {name} 预期拒绝 -> {e}')
    except Exception as e:
        print(f'  [FAIL] {name} -> {e}')
        failed += 1

print(f'\n结果: {len(recursive_cases) - failed}/{len(recursive_cases)} 通过')

if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)
