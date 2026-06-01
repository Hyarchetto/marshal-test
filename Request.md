Testing real-world software
到期： 2026年 6月11日 23:59
允许尝试任意次数
可供使用的起始日期 2026年 5月28日 0:00可供使用的起始日期 2026年 5月28日 0:00
Introduction
The marshal module implements serialization and deserialization of Python’s internal object types. It is primarily used to read and write the “pseudo-compiled” bytecode of Python modules (.pyc files). “Marshalling” converts a supported Python object into a binary byte stream, and “unmarshalling” performs the reverse operation.

The marshal format is designed to be architecture‑independent (the same data should be produced on different operating systems for the same Python version), but it is deliberately not stable across Python versions – the format may (and does) change between major releases. Even within a single version, subtle differences in floating‑point handling, recursive data structures, and internal implementation details could potentially cause non‑deterministic output.

I would like to understand how stable and correct the module is: Does the same input always create the same (serialized) output?
We define the same input and output as hash‑identical (logical equivalence is insufficient). This means an input must create the same marshal byte stream under all circumstances.marshal
Possible options to investigate include:

Different operating systems (e.g., Windows, Linux, macOS)

Different Python versions (the marshal format may vary)

Floating point accuracy and special values (, NaNInf)

Recursive and cyclic data structures (e.g., lists that contain themselves)

Empty and extremely large collections

Please keep your mind open to other options.
Your task
Develop a test suite for the stability and correctness of the module.
You should use the black-box testing techniques you learned in the lectures (equivalence partitioning, boundary value analysis, fuzzing, etc.).
Since the source code is available (Python/marshal.c and Lib/marshal.py), you may also apply white‑box testing approaches discussed in the lectures (e.g., all‑definitions, all‑uses coverage).marshalmarshal

Final report
You must submit a final report. Your final report discusses:

    Your test suite, including the testing strategies you applied.
    Why you decided to use (or not use) a specific testing technique (e.g., boundary value analysis).
    The completeness of your test suite through a traceability matrix.
    The findings of your test suite (observed stability issues, non‑determinism, bugs, etc.).
    The limitations and shortcomings of your test suite.
Your final report must not exceed 8 pages.
Your code must comply with the PEP 8 coding style guidelines and be available on a public repository such as GitHub or GitLab.

Please provide a link to your repository in your report.