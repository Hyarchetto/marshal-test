# marshal-test — Python `marshal` 模块跨平台稳定性测试套件

[![测试矩阵](https://github.com/Hyarchetto/marshal-test/actions/workflows/test-matrix.yml/badge.svg)](https://github.com/Hyarchetto/marshal-test/actions/workflows/test-matrix.yml)

## 项目简介

本项目是**软件测试课程**期末实验，针对 Python 标准库的 `marshal` 模块设计黑盒与白盒测试套件，验证其序列化在不同**操作系统**和 **Python 版本**下的**稳定性与正确性**。

### 测试对象

`marshal` 模块负责 Python 内部对象的序列化/反序列化，主要用于读写 `.pyc` 字节码文件。其设计目标是**架构中立**（同一 Python 版本在不同 OS 上产生相同输出），但**不保证跨版本稳定**。

### 核心问题

> **相同的 Python 对象是否总是产生相同的 marshal 字节流？**

项目通过 3 个操作系统 × 5 个 Python 版本的全矩阵测试来回答这一问题。

## 测试矩阵

| 维度 | 覆盖范围 |
|------|----------|
| **操作系统** | Ubuntu (Linux), Windows, macOS |
| **Python 版本** | 3.9, 3.10, 3.11, 3.12, 3.13 |
| **组合数** | 3 × 5 = **15 个并行任务** |

每个组合在 GitHub Actions CI 中独立运行，结果自动汇总。

## 项目结构

```
marshal-test/
├── tests/
│   ├── test_marshal.py              # 主测试套件：静态用例 + 模糊测试 + 哈希基准比对
│   └── test_marshal_matrix.py       # 矩阵环境验证：环境信息 + marshal 基础功能
├── scripts/
│   ├── diagnose_random.py           # 随机数序列跨 OS 一致性诊断
│   └── diagnose_iter8.py            # set/dict hash 逐层拆解诊断
├── .github/
│   ├── workflows/test-matrix.yml    # CI 工作流：15 任务矩阵 + 汇总
│   └── merge_reports.py             # 多环境 JSON 报告合并工具
├── collect_baseline.py              # 在 Python 3.12 下重新采集基准哈希
├── pytest.ini                       # pytest 配置
├── .gitignore
└── README.md
```

## 测试策略

### 黑盒测试

| 技术 | 应用 |
|------|------|
| **等价类划分** | 按数据类型（None、int、float、str、bytes、tuple、list、dict、set、complex、frozenset、递归结构）划分等价类 |
| **边界值分析** | 空集合、极大集合、极小/极大整数、特殊浮点值（0.0, -0.0, inf, -inf, NaN） |
| **模糊测试 (Fuzzing)** | 随机生成 50 轮混合类型、嵌套结构数据，验证序列化一致性 |

### 白盒测试

| 技术 | 应用 |
|------|------|
| **跨版本哈希基准** | 预先在 Python 3.12 下固化 SHA-256 哈希，CI 中跨版本比对差异 |
| **set/dict 哈希诊断** | `PYTHONHASHSEED=1` 固定种子，逐层拆解 set/dict marshal 差异来源 |
| **random 序列验证** | 跨 OS 验证 `random.Random(42)` 输出序列一致性 |

## 使用方法

### 本地运行

```bash
# 确保 PYTHONHASHSEED 已固定
export PYTHONHASHSEED=1
pytest tests/ -v -s

# 直接运行查看 JSON 报告
python tests/test_marshal.py

# 采集基准哈希（Python 3.12 环境）
python collect_baseline.py > new_baselines.txt
```

### CI 运行

推送代码到 `master` 分支或创建 Pull Request 即可自动触发完整矩阵测试，测试报告以 Artifact 形式保存。

## 测试覆盖

- ✅ 基本数据类型（None、int、float、bool、str、bytes）
- ✅ 复合类型（tuple、list、dict、set、frozenset、complex）
- ✅ 递归结构（自引用 list、自引用 dict、深层嵌套）
- ✅ 特殊浮点值（0.0、-0.0、inf、-inf、NaN）
- ✅ 极大/极小边界值（大整数、空集合、长字符串）
- ✅ 模糊测试（50 轮随机生成混合结构）
- ✅ 跨平台/跨版本一致性验证

## License

本项目仅用于教学目的。
