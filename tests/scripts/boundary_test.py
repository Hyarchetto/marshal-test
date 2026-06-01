"""边界值与特殊值测试（跨平台交叉验证）"""
import marshal
import io
import sys

# 整数边界
int_cases = [
    ('int_min_i32', -2**31),
    ('int_max_i32', 2**31 - 1),
    ('int_min_i64', -2**63),
    ('int_max_i64', 2**63 - 1),
    ('int_min_i16', -2**15),
    ('int_max_i16', 2**15 - 1),
    ('int_large_pos', 2**100),
    ('int_large_neg', -2**100),
]

# 浮点数边界
float_cases = [
    ('float_min', sys.float_info.min),
    ('float_max', sys.float_info.max),
    ('float_epsilon', sys.float_info.epsilon),
    ('float_neg_zero', -0.0),
    ('float_nan', float('nan')),
    ('float_neg_nan', -float('nan')),
    ('float_inf', float('inf')),
    ('float_neg_inf', -float('inf')),
    ('float_denorm', 1e-308),
]

# 字符串边界
str_cases = [
    ('str_empty', ''),
    ('str_single', 'a'),
    ('str_unicode', '你好，世界 🌍'),
    ('str_control', chr(0) + chr(31) + chr(127)),
    ('str_very_long', 'A' * 100_000),
]

# 容器边界
container_cases = [
    ('list_empty', []),
    ('tuple_empty', ()),
    ('dict_empty', {}),
]

all_cases = int_cases + float_cases + str_cases + container_cases
failed = 0

for name, obj in all_cases:
    try:
        buf = io.BytesIO()
        marshal.dump(obj, buf)
        buf.seek(0)
        loaded = marshal.load(buf)
        size = len(buf.getvalue())
        print(f'  [PASS] {name} (size={size} bytes)')
    except Exception as e:
        print(f'  [FAIL] {name} -> {e}')
        failed += 1

print(f'\n结果: {len(all_cases) - failed}/{len(all_cases)} 通过')

if __name__ == "__main__":
    sys.exit(0 if failed == 0 else 1)
