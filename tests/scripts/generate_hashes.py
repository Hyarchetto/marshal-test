"""生成 marshal 序列化基准哈希，用于跨平台一致性验证"""
import marshal
import hashlib
import io
import sys

test_cases = {
    'none': None,
    'true': True,
    'false': False,
    'int_zero': 0,
    'int_pos': 42,
    'int_neg': -42,
    'int_large': 2**63 - 1,
    'float_zero': 0.0,
    'float_pi': 3.141592653589793,
    'float_nan': float('nan'),
    'float_inf': float('inf'),
    'str_empty': '',
    'str_hello': 'Hello, marshal!',
    'list_empty': [],
    'list_nested': [1, [2, [3]]],
    'tuple_mixed': (1, 'a', 3.14, None),
    'dict_simple': {'key': 'value', 'num': 42},
    'bytes_data': b'\x00\x01\x02\xff',
    'complex_num': 1+2j,
}

py_ver = f"py{sys.version_info.major}.{sys.version_info.minor}"
filename = f"marshal_hashes_{py_ver}.csv"

with open(filename, 'w') as f:
    for name, obj in test_cases.items():
        buf = io.BytesIO()
        marshal.dump(obj, buf)
        h = hashlib.sha256(buf.getvalue()).hexdigest()
        f.write(f'{name},{h}\n')

print(f"已生成 {filename}，共 {len(test_cases)} 条哈希记录")


if __name__ == "__main__":
    pass  # 允许作为脚本直接运行
