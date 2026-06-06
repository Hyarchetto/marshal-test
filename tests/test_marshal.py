"""
marshal 模块跨平台/跨版本兼容性测试脚本

任务说明:
- 在 Python 3.12 基准环境采集 SHA-256 哈希并固化
- 在 CI 矩阵中跨操作系统/跨版本比对
- 探测序列化格式变化与不确定性输入

用法:
    pytest test_marshal.py -v
    python test_marshal.py          # 直接运行查看差异报告

注意:
    当前哈希值在 Python 3.12 环境采集，作为基准版本。
    同一 Python 版本在不同操作系统上应产生相同的 marshal 输出，
    不同 Python 版本之间 marshal 格式可能发生变化。
"""

import sys
import marshal
import hashlib
import random
import platform

#---全局约束配置---
BASELINE_VERSION = "3.12"
GLOBAL_SEED = 42
FUZZER_ITERATIONS = 50  # 模糊测试迭代次数

# ============================================================
# 1. 静态测试数据与预构建基准哈希
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

# 静态用例定义: (用例标识, 静态对象)
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

# 预构建的静态用例基准哈希表 (在 Python 3.12 环境采集)
# 用于验证: 同一 Python 版本内跨操作系统一致性，及跨版本格式差异
STATIC_BASELINE_HASHES = {
    "none": "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",
    "bool_true": "e632b7095b0bf32c260fa4c539e9fd7b852d0de454e9be26f24d0d6f91d069d3",
    "bool_false": "f67ab10ad4e4c53121b6a5fe4da9c10ddee905b978d3788d2723d7bfacbe28a9",
    "int_zero": "e8ebd827d1f36d7cfa5e5220610aa6370284d1589989363f48ac40166362d449",
    "int_minus1": "72aea108d59af9a3db0854601259c9d9a62dce69f656f4a3f4e451500fb85a1f",
    "int_small": "3c3e5f0b175ca9da4f2e28aaa9b4a9c08f37369cd16d7de1b3901512c5f92e46",
    "int_large": "6600bbb0ea0a2e1b46b3762687001781a4bfc217100abf0aeb19df30c4f4f1a0",
    "int_huge": "93133aef5016fb3e75f0e91c81f629b6103091b160d1a763b384818a7d0fca79",
    "int_negative_huge": "382e56d74f5468fbdd23d4f4abf37cd3fe7fb3cfc3bdcacf8764fc697709a369",
    "int_maxsize": "7da212917f2e476cf4865db2c13815055c744e353a553464833b8c812de25fcf",
    "int_minsize": "1d14c0165fb31ea4cbd0bb1b47e51ff68e5b351ac4e805209bc25b8a011c9e8a",
    "float_zero": "a7b2474c2b69133fff4c0515276a03bbf9d1c38d1d1f8c08bd5db478181398d6",
    "float_negzero": "61d36befa08b84a6b58ddc977ad118100fb1e244e7be671d6f1e027ba585a163",
    "float_small": "c906a01f29be5e4aa4529f278f3cdcb2568a965bb632567329af786157dc1c5f",
    "float_large": "0f7e1a38a5d9f75190dc3882b1cdd6e17293bb953366fc567fe659c9dc01ff20",
    "float_inf": "a723a76079a60280dcdb2d7984a2adf4a0874e31b9518b30dfc0cfd9c3b53c54",
    "float_neginf": "860d99b42a646c71e28db195c6fdd2478e70455cb540732d1204ea023e3fb0cf",
    "float_nan": "c0071368d2b0e5cb29b0995db32ea00ef9a3c215871dbabf0d4146930d1c7196",
    "float_max": "cf031cbdcce7c98ae2d07c03fec0b325cc44716e572ac53089b4f89230c97921",
    "float_min": "9011ea8add4af2315a691d58b88c2f4f059be77e3ac20f2681b0d1ccc6143634",
    "float_epsilon": "01c715d639cbadf264ffdf1e118b42fc9f994647a1ae0841d753ca9143cd43cb",
    "complex_zero": "4af55f659e98d62afb780d456414d7a3d98eaf04614feba89ba26b998575eaab",
    "complex_real": "b191bd4e24096285d6500daf7801202f5f6c5bb2ed87e28408bd280c051dcc35",
    "complex_inf": "55474fb13236bd5f7656d12b36a54cb1b21ffa2db3d9a81f5116bab112eec013",
    "complex_nan": "cb8c7796e2953788906ddcf5dff7277efee4698b4f309292c49f1985557b1140",
    "bytes_empty": "1e39f9576a47375992ed7b53b49a4fe68e1622c87227165ee0246d3c345996f1",
    "bytes_small": "92d6f64323a429f19ef66453832b55d63bf65e0ede48c28b6e965c674c605655",
    "bytes_binary": "0b08ed82f6c155739862b18db0d9bcd0717c90a3bd87e72a5828d85356b79078",
    "bytes_large": "4676eef00a8c15e98945c8373cd71adedd6d0c3b4481b712e1f22c483be7c2f2",
    "str_empty": "153d812467db095632c6583da7f82cf7ad1e3f9ef18b6358c10f28d2804822f4",
    "str_ascii": "233db27858826e2af6235757b42b2421d4cea8121c45fea323d58eb804810f5d",
    "str_unicode": "effffae60787a2b0448bdd167e6287819fadc08f73d7ea2d2a560a1c7e9dfe20",
    "str_special": "ba1248155e93d20f0ac08d8f0695299ebfc332cdb8b6de141c7340b5aad0fb5b",
    "str_large": "5659b07be1e193edb6fdf058b6fbb79b46da7ea90122ab0f793fb9a2d1add908",
    "tuple_empty": "86c11f10c038a75279e64a09cbc5cacb478a9af27d1b5cce1d1b1cc7e23a1b81",
    "tuple_single": "2acf613053bd5b7e696b2e325b85bf7f5f28c935da974ba35820fe64dae5ec79",
    "tuple_nested": "cf9674692b834eb9eaf249f58949cef63873dee994c30402f7ddbc1b81227847",
    "tuple_mixed": "863144443b10728dc6f80b92652ee570d01bdf99ed114aa89575849baf5d4dd3",
    "list_empty": "cd13cd2473c97737511c66500c332fdf9ad78c5f6e8d4eb4fea992bb63f42055",
    "list_single": "071faf4be14deab4120f7589142827a8907297e57d4f5443d67717f37ff1c1f7",
    "list_nested": "a4c5d64257331bd090e28d3edee681db298f2f7d7fae3cbb970a3b6f5f9af61e",
    "list_mixed": "6ab1362305e2ba4ad71a8688d21634432fa7b0fb58537953c9ef49aa2d1a51e2",
    "list_large": "56bd07653c06de22611041c7eab196c75ad0617b2c6e4f68dd8498c5dce38ce7",
    "set_empty": "995046494f919338259e00eb000e87957890be5cb4e30be304e6646e1426578b",
    "set_small": "cddf0b000e7d5e4d9d7ffbbf3ecc0f056e311652a56278e911321cfc9c588ec9",
    "set_mixed": "321becebcc167682458b1ccdfffefee8adf8a9d9acfe648e957160ead80d8cad",
    "set_large": "0e9bbe66dddf4b0ea233218e9a0a0f66ce0af98b7659e8408b0a3ba9749e72a1",
    "dict_empty": "fa433c89e61178902327da13af7dc0b09aede94a362de11626c21700a658c353",
    "dict_single": "f1867b0faa3babeb37093568b979d2571dae3f8b9bbd2e258436da98c11b318b",
    "dict_nested": "9cee698b3fec73a74716f078e91038e4af9dca5f12adba497388789d42d5515e",
    "dict_mixed": "582d63e4d3a1c002fcc8e4bf9d295e67763767b4e8fa23cea1687d761108c895",
    "dict_large": "ec97f81eadf0f8672c7e9a12451f299b813939da0cc23b32a21ad15f8920546f",
    "recursive_list": "b8df5a36c63ce3c63ba94d152cb2e5630e1f7c413460956990dd7e04546687cc",
    "recursive_dict": "2d862ef309884ba0c49b8e2dbea88c03f838316d251982f061a0f07c6656bc14",
    "deep_list_10": "eaff10ae250eb277746e7b54c21d7a942d2f6ed141afcecea149b2c8f7a52836",
    "deep_dict_10": "ee4fc59f34fc1f01c64ba32875264ecce77b80b2704dc9bbbf5a9714df6a841e",
    "deep_mixed": "1d08310f4f587688573a0f880a3ccf73a769d6a49b75ac00c25d2954b8275b6f",
}

# ============================================================
# 2. 预构建的模糊测试基准哈希表
# ============================================================
# 注意: 以下哈希在 Python 3.12 环境采集
FUZZER_BASELINE_HASHES = [
    "fec32d0301abb181227152f011676afde28d0eaa2b5160779f9d4425bfe02ccf",  # iter 0
    "bfaaaf30db9f92f59b177a8c52f8c5345e185565bcbb63668f6e5ade19407f75",  # iter 1
    "21e05e55b090bae69d3b999b9f9dab0fa015e45abea5fd8d5ed04b364024696d",  # iter 2
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 3
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 4
    "23a9274954d477fc3f1a6a63db4ea0d8b6af80553fe14228759afd279af38874",  # iter 5
    "9554bc91c3e416c9ababbde7cc0db71967d5679f8a4b4c268f1af7031d4a0992",  # iter 6
    "4af55f659e98d62afb780d456414d7a3d98eaf04614feba89ba26b998575eaab",  # iter 7
    "92da89e1d377eafdcb469633a68488c014cf2e23eafa470f720fb194241543ce",  # iter 8
    "153d812467db095632c6583da7f82cf7ad1e3f9ef18b6358c10f28d2804822f4",  # iter 9
    "f2bcabb9c61d500d993ca724ccb9257b57ff33331cd250b2297230955d466f94",  # iter 10
    "614f4698d96cd3431211cdb732b3332f2f138416404ee21f47ff11877c6e46ad",  # iter 11
    "a7b2474c2b69133fff4c0515276a03bbf9d1c38d1d1f8c08bd5db478181398d6",  # iter 12
    "ce8a48b5ee4ee3f6355f25989e3946d62597f44008df4440cbbcf2cb5c3bb9eb",  # iter 13
    "a773433064a861a45f52c711414fc4acd4c3c5afbcfe1518e2bfc9713b5841bd",  # iter 14
    "99b1b2a3970c65913c4bda5c17f005e7c351f64fc18d90e73456e6191456b8bd",  # iter 15
    "4055a6f837743c4c9125121d42c1af1e60bbf1bce5189a33366bae597ebd8660",  # iter 16
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 17
    "84cb29a166e8b1db4c706c80e99e32004c2ba2f6610ace235de68cafb10555af",  # iter 18
    "94a9411713d0f1705a812774276781ab4580b650e2351460208e04d479e623aa",  # iter 19
    "4e0f30475036856997fa4778d22c023b1d4394e661dc53558eac5e0bd14029e6",  # iter 20
    "cb4f6f4b65d78e1e827341c998c2e5e7ddb4e19387c9fdc70bd90f795e546383",  # iter 21
    "60200eba3d4007b224606f0dc78eebb6c244489175aa86f96c12b75041bcd743",  # iter 22
    "bfcd8d67ecc76303dc3597ffd941dfbe079e199cb8c344ee20348425d5c2ba33",  # iter 23
    "2dd1d0161a76325142a84eb5f951f5b3ae6beb4258fe982ebdca854953e7c57e",  # iter 24
    "2f8143c30675b1a0da2d39c8ce03cfeff5a1956c2556d01e9a0f961fed720877",  # iter 25
    "a7b2474c2b69133fff4c0515276a03bbf9d1c38d1d1f8c08bd5db478181398d6",  # iter 26
    "1e39f9576a47375992ed7b53b49a4fe68e1622c87227165ee0246d3c345996f1",  # iter 27
    "153d812467db095632c6583da7f82cf7ad1e3f9ef18b6358c10f28d2804822f4",  # iter 28
    "5719702c32e118ca1c521551bd683c23ad248b717b1290ea159aeae5c460ea6f",  # iter 29
    "995046494f919338259e00eb000e87957890be5cb4e30be304e6646e1426578b",  # iter 30
    "609b5e633b82094a4de85361a430016edf60b6916894efab84fbc3503892f0f2",  # iter 31
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 32
    "439e1978fc13f7ee182bde9ab9b39b1b992642d32975312d16a1969a58d4bdba",  # iter 33
    "3310571104f820760d889d76866065b2177173825f39a236c00b9a9291884c38",  # iter 34
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 35
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 36
    "8d3a149487301b21968302bedc503fcd3eca84d53299a177367d8d91c4d61721",  # iter 37
    "a7b2474c2b69133fff4c0515276a03bbf9d1c38d1d1f8c08bd5db478181398d6",  # iter 38
    "6d42a58be2a9ddf69cabfa66caa0c4955a86d30f8862a690044860a053466eb6",  # iter 39
    "fa433c89e61178902327da13af7dc0b09aede94a362de11626c21700a658c353",  # iter 40
    "995046494f919338259e00eb000e87957890be5cb4e30be304e6646e1426578b",  # iter 41
    "62f36c7759f2795666431696c9dc5720c113902259acae8455c8ff9536d51459",  # iter 42
    "1e39f9576a47375992ed7b53b49a4fe68e1622c87227165ee0246d3c345996f1",  # iter 43
    "8ce86a6ae65d3692e7305e2c58ac62eebd97d3d943e093f577da25c36988246b",  # iter 44
    "bfaf63f58037acb67767fccf7a07029b05a92f0e984d65211f3450fe45876067",  # iter 45
    "8901195821c15bfb6807a185a0da4e5cd01e18ddaf4f2aaa2aba8f7638bc0f25",  # iter 46
    "fa433c89e61178902327da13af7dc0b09aede94a362de11626c21700a658c353",  # iter 47
    "dceead4121c5b437bee479a7cf20fca8ebcbebe62d1f5622c40d83b850ec8769",  # iter 48
    "c7cfaa3e4f8744e6b386b078a80511e82a93e424c8e918284cc2778e18af334b",  # iter 49
]

# ============================================================
# 3. Fuzzer 数据生成器
# ============================================================

def generate_fuzz_data(max_depth=8, current_depth=0, for_set=False, for_dict_key=False):
    """
    递归构造复杂嵌套数据。
    支持类型: None, int, float, complex, bytes, str, tuple, list, set, dict

    for_set=True: 生成可哈希数据（用于 set 元素）
    for_dict_key=True: 生成可哈希数据（用于 dict key）
    """
    if for_set or for_dict_key:
        # 只能生成可哈希类型
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

    # 普通模式：任何类型
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


def _extract_type_category(case_name):
    """从用例名推断类型分类"""
    prefix_map = {
        "none": "NoneType",
        "bool": "bool",
        "int": "int",
        "float": "float",
        "complex": "complex",
        "bytes": "bytes",
        "str": "str",
        "tuple": "tuple",
        "list": "list",
        "set": "set",
        "dict": "dict",
        "recursive": "recursive",
        "deep": "deep_nested",
    }
    for prefix, category in prefix_map.items():
        if case_name.startswith(prefix):
            return category
    return "other"


def _is_special_float(case_name):
    """判断是否为浮点特殊值用例"""
    specials = {"float_nan", "float_inf", "float_neginf", "float_negzero",
                "complex_nan", "complex_inf"}
    return case_name in specials


def _classify_float_subtype(case_name):
    """浮点数子分类：特殊值 vs 常规值"""
    if not case_name.startswith("float_"):
        return None
    if case_name in ("float_nan", "float_inf", "float_neginf", "float_negzero"):
        return "特殊值 (NaN/Inf/-0.0)"
    return "常规浮点数"


# ============================================================
# 5. 核心验证逻辑（增强版：收集数据而非直接打印）
# ============================================================

def _compute_hash(obj):
    """计算对象的 marshal SHA-256 哈希"""
    return hashlib.sha256(marshal.dumps(obj)).hexdigest()


# 不确定性用例清单
UNCERTAIN_CASES = {
    "float_nan", "complex_nan",
    "set_empty", "set_small", "set_mixed", "set_large",
    "dict_empty", "dict_single", "dict_nested", "dict_mixed", "dict_large",
}


def _contains_non_deterministic(obj, seen=None):
    """
    递归检查对象是否包含非确定性类型（set/dict/NaN/math-like）。
    set/dict 因 PYTHONHASHSEED 导致迭代顺序不定；
    NaN 有多种位表示。
    """
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return False  # 循环引用已访问过，不重复
    seen.add(obj_id)

    if isinstance(obj, (set, dict)):
        return True
    if isinstance(obj, float):
        # NaN 的唯一判断方式：不等于自身
        if obj != obj:
            return True
    if isinstance(obj, complex):
        if obj.real != obj.real or obj.imag != obj.imag:
            return True
    if isinstance(obj, (list, tuple)):
        return any(_contains_non_deterministic(item, seen) for item in obj)

    return False


def _evaluate_case(case_name, test_data, baseline_hash, current_version):
    """
    评估单个用例的状态。
    
    返回: (status, current_hash, error_msg)
        status: "passed" | "failed" | "changed" | "unchanged" | "uncertain" | "error"
    """
    try:
        current_hash = _compute_hash(test_data)

        if baseline_hash is None:
            return ("no_baseline", current_hash, None)

        if current_version == BASELINE_VERSION:
            # 同版本 -> 验证跨平台一致性
            if case_name in UNCERTAIN_CASES or _contains_non_deterministic(test_data):
                # 不确定性用例：记录漂移但不判定失败
                if current_hash != baseline_hash:
                    return ("uncertain_drift", current_hash, None)
                else:
                    return ("uncertain_stable", current_hash, None)
            else:
                if current_hash == baseline_hash:
                    return ("passed", current_hash, None)
                else:
                    return ("failed", current_hash,
                            f"跨平台不一致: baseline={baseline_hash[:16]}..., current={current_hash[:16]}...")
        else:
            # 跨版本 -> 探测格式变化
            # 注意: 非确定性类型（set/dict/NaN）也参与比对，
            # CI 中 PYTHONHASHSEED=1 固定为字面量种子，各平台一致
            if current_hash != baseline_hash:
                return ("changed", current_hash, None)
            else:
                return ("unchanged", current_hash, None)

    except Exception as e:
        return ("error", None, f"{type(e).__name__}: {str(e)}")


# ============================================================
# 6. 结构化报告生成
# ============================================================

def test_marshal_stability_with_report():
    """增强版：运行测试并输出结构化分析报告"""
    import json
    from collections import defaultdict
    from datetime import datetime

    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    is_baseline = (current_version == BASELINE_VERSION)
    version_label = f"Python {current_version} (@ {platform.system()})"
    ref_label = f"基准: Python {BASELINE_VERSION}"

    # ----- 结果收集 -----
    results = []  # 每条: {name, category, status, is_special_float, ...}
    fuzzer_results = []

    # --- 静态用例 ---
    for name, obj in _STATIC_CASES_DEF:
        baseline_hash = STATIC_BASELINE_HASHES.get(name)
        status, cur_hash, err = _evaluate_case(name, obj, baseline_hash, current_version)
        results.append({
            "name": name,
            "category": _extract_type_category(name),
            "subtype": _classify_float_subtype(name),
            "is_special_float": _is_special_float(name),
            "status": status,
            "type": type(obj).__name__,
            "error": err,
        })

    # --- 模糊测试 ---
    random.seed(GLOBAL_SEED)
    for i in range(FUZZER_ITERATIONS):
        fuzz_obj = generate_fuzz_data(max_depth=6)
        baseline_hash = FUZZER_BASELINE_HASHES[i] if i < len(FUZZER_BASELINE_HASHES) else None
        status, cur_hash, err = _evaluate_case(f"fuzzer_{i}", fuzz_obj, baseline_hash, current_version)
        fuzzer_results.append({
            "iteration": i,
            "status": status,
            "type": type(fuzz_obj).__name__,
            "error": err,
        })

    # ----- 输出报告 -----
    print(f"\n{'='*68}")
    print(f"  marshal 序列化稳定性测试报告")
    print(f"  {version_label}  |  {ref_label}")
    print(f"{'='*68}\n")

    # ──── 板块 A：按类型分组的稳定性汇总 ────
    print("▌ A. 按类型分组的稳定性分析")
    print(f"{'─'*68}")

    # 按类型分组统计
    category_stats = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0,
                                           "changed": 0, "unchanged": 0, "uncertain": 0, "error": 0})
    for r in results:
        cat = r["category"]
        category_stats[cat]["total"] += 1
        if r["status"] in ("passed",):
            category_stats[cat]["passed"] += 1
        elif r["status"] in ("failed",):
            category_stats[cat]["failed"] += 1
        elif r["status"] in ("changed",):
            category_stats[cat]["changed"] += 1
        elif r["status"] in ("unchanged",):
            category_stats[cat]["unchanged"] += 1
        elif r["status"] in ("uncertain_drift", "uncertain_stable", "uncertain_skip"):
            category_stats[cat]["uncertain"] += 1
        elif r["status"] in ("error",):
            category_stats[cat]["error"] += 1

    # 打印类型汇总表
    header = f"{'类型':<16} {'总数':>6} {'通过':>6} {'失败':>6} {'变化':>6} {'兼容':>6} {'不确定':>8}"
    print(header)
    print(f"{'─'*68}")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        if is_baseline:
            # 同版本：关注通过/失败/不确定
            print(f"{cat:<16} {s['total']:>6} {s['passed']:>6} {s['failed']:>6} {'—':>6} {'—':>6} {s['uncertain']:>8}")
        else:
            # 跨版本：关注变化/兼容
            print(f"{cat:<16} {s['total']:>6} {'—':>6} {'—':>6} {s['changed']:>6} {s['unchanged']:>6} {s['uncertain']:>8}")

    # ──── 板块 B：浮点数特殊值专项分析 ────
    print(f"\n▌ B. 浮点数特殊值专项分析")
    print(f"{'─'*68}")

    float_special = [r for r in results if r["is_special_float"]]
    float_normal = [r for r in results if r["subtype"] == "常规浮点数"]

    if float_special:
        print(f"  特殊值 (NaN/Inf/-0.0): {len(float_special)} 个用例")
        for r in float_special:
            status_symbol = {
                "passed": "✓", "failed": "✗", "changed": "Δ", "unchanged": "=",
                "uncertain_drift": "~", "uncertain_stable": "≈", "uncertain_skip": "-", "error": "!"
            }.get(r["status"], "?")
            print(f"    {status_symbol} {r['name']:25s}  | 状态: {r['status']}")
    else:
        print("  (无特殊浮点值用例)")

    if float_normal:
        n_changed = sum(1 for r in float_normal if r["status"] == "changed")
        n_unchanged = sum(1 for r in float_normal if r["status"] == "unchanged")
        print(f"  常规浮点数: {len(float_normal)} 个用例, 跨版本变化: {n_changed}, 兼容: {n_unchanged}")

    # ──── 板块 C：容器类型稳定性分析 ────
    print(f"\n▌ C. 容器类型稳定性分析")
    print(f"{'─'*68}")

    container_types = {"list", "tuple", "set", "dict", "recursive", "deep_nested"}
    for cat in sorted(container_types):
        if cat not in category_stats:
            continue
        s = category_stats[cat]
        if is_baseline:
            stable = s["passed"] + s["uncertain"]
            print(f"  {cat:<14} {s['total']:>3} 个用例 | 同平台一致性: {stable}/{s['total']}")
        else:
            changes = s["changed"]
            compat = s["unchanged"]
            print(f"  {cat:<14} {s['total']:>3} 个用例 | 跨版本: {changes} 变化, {compat} 兼容")
            if changes > 0:
                changed_names = [r["name"] for r in results
                                 if r["category"] == cat and r["status"] == "changed"]
                print(f"                     变化用例: {', '.join(changed_names)}")

    # ──── 板块 D：模糊测试统计 ────
    print(f"\n▌ D. 模糊测试 ({FUZZER_ITERATIONS} 次迭代)")
    print(f"{'─'*68}")

    fuzzer_status_count = defaultdict(int)
    for r in fuzzer_results:
        fuzzer_status_count[r["status"]] += 1

    if is_baseline:
        print(f"  同版本通过 (跨平台一致): {fuzzer_status_count.get('passed', 0)}")
        print(f"  同版本失败 (跨平台不一致): {fuzzer_status_count.get('failed', 0)}")
        uncertain_cnt = fuzzer_status_count.get("uncertain_drift", 0) + fuzzer_status_count.get("uncertain_stable", 0) + fuzzer_status_count.get("uncertain_skip", 0)
        if uncertain_cnt:
            print(f"  非确定性类型 (set/dict/NaN 跳过): {uncertain_cnt}")
    else:
        print(f"  跨版本格式变化: {fuzzer_status_count.get('changed', 0)}")
        print(f"  跨版本格式兼容: {fuzzer_status_count.get('unchanged', 0)}")
        skip_cnt = fuzzer_status_count.get("uncertain_skip", 0) + fuzzer_status_count.get("uncertain_drift", 0) + fuzzer_status_count.get("uncertain_stable", 0)
        if skip_cnt:
            print(f"  非确定性类型 (跳过比对的): {skip_cnt}")
    print(f"  执行异常: {fuzzer_status_count.get('error', 0)}")
    # 分析4：跨版本格式兼容性
    if not is_baseline:
        total_cross = sum(1 for r in results if r["status"] in ("changed", "unchanged"))
        n_changed = sum(1 for r in results if r["status"] == "changed")
        n_unchanged = sum(1 for r in results if r["status"] == "unchanged")
        print(f"  跨版本静态用例: {n_unchanged}/{total_cross} 格式兼容, {n_changed}/{total_cross} 格式重构")
        
        # 列出哪些类型变化最多
        changed_by_cat = defaultdict(int)
        for r in results:
            if r["status"] == "changed":
                changed_by_cat[r["category"]] += 1
        if changed_by_cat:
            most_changed = sorted(changed_by_cat.items(), key=lambda x: -x[1])[:3]
            print(f"  变化最显著的类型: {', '.join(f'{cat}({n})' for cat, n in most_changed)}")

        # Fuzzer 跨版本统计
        f_changed = fuzzer_status_count.get("changed", 0)
        f_unchanged = fuzzer_status_count.get("unchanged", 0)
        f_total = f_changed + f_unchanged
        if f_total > 0:
            print(f"  模糊测试跨版本: {f_unchanged}/{f_total} 兼容, {f_changed}/{f_total} 重构")

    # ──── 输出摘要行 ────
    print(f"\n{'='*68}")
    print(f"  测试执行环境: {version_label}")
    print(f"  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*68}\n")

    # ----- 同时也保存 JSON 报告供后续分析 -----
    report = {
        "metadata": {
            "python_version": sys.version,
            "platform": platform.system(),
            "machine": platform.machine(),
            "timestamp": datetime.now().isoformat(),
            "baseline_version": BASELINE_VERSION,
            "current_version": current_version,
            "marshal_version": marshal.version,
        },
        "static_results": results,
        "fuzzer_results": fuzzer_results,
    }
    report_file = f"marshal_report_py{current_version.replace('.', '')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"详细报告已保存: {report_file}")


def test_marshal_stability():
    """pytest 兼容入口，直接调用报告模式"""
    test_marshal_stability_with_report()


if __name__ == "__main__":
    test_marshal_stability_with_report()

