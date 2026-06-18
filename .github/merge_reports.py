#!/usr/bin/env python3
"""
合并所有 matrix 环境的 JSON 报告为一份完整的汇总报告

功能:
  1. 收集所有 marshal 主报告 + 矩阵环境验证报告
  2. 按 Python 版本分组，对比跨操作系统一致性
  3. 证明「marshal 输出取决于 Python 版本，与操作系统无关」
  4. 输出一份汇总 JSON 和一份汇总 TXT
"""

import json
import os
import glob
from collections import defaultdict

REPORT_DIR = "all-reports"
OUTPUT_DIR = "combined-report"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ================================================================
    # 收集所有报告
    # ================================================================
    # 主 marshal 报告
    report_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "marshal_report_py*.json"),
        recursive=True,
    )
    # 矩阵验证报告
    matrix_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "marshal_matrix_report_py*.json"),
        recursive=True,
    )

    if not report_files:
        print("没有找到任何 marshal 报告文件")
        # 输出一份空报告方便 CI 继续
        _write_empty_report()
        return

    all_reports = _load_json_files(report_files, "marshal")
    all_matrix_reports = _load_json_files(matrix_files, "matrix")

    # ================================================================
    # 收集控制台日志 (.txt)
    # ================================================================
    txt_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "marshal_report_py*.txt"),
        recursive=True,
    )
    console_logs = {}
    merged_lines = []
    for txt_path in sorted(txt_files):
        env_tag = _extract_env_tag_from_path(txt_path)
        with open(txt_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
            console_logs[env_tag] = content
        merged_lines.append(f"{'='*70}")
        merged_lines.append(f"  环境: {env_tag}")
        merged_lines.append(f"{'='*70}")
        merged_lines.append(content.rstrip())
        merged_lines.append("")

    # ================================================================
    # 收集诊断日志 (diagnose_random + diagnose_iter8)
    # ================================================================
    diag_random_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "diagnose_random_*.txt"), recursive=True,
    )
    diag_iter8_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "diagnose_iter8_*.txt"), recursive=True,
    )
    diag_info = _collect_diagnostics(diag_random_files, diag_iter8_files)

    # ================================================================
    # 收集所有环境的哈希差异汇总文件并合并
    # ================================================================
    diff_files = glob.glob(
        os.path.join(REPORT_DIR, "**", "marshal_diff_py*.txt"), recursive=True,
    )
    if diff_files:
        combined_diff_lines = []
        diff_file_count = 0
        for diff_path in sorted(diff_files):
            env_tag = _extract_env_tag_from_path(diff_path)
            with open(diff_path, encoding="utf-8", errors="replace") as f:
                content = f.read().strip()
            combined_diff_lines.append(f"{'='*68}")
            combined_diff_lines.append(f"  环境: {env_tag}")
            combined_diff_lines.append(f"{'='*68}")
            combined_diff_lines.append(content)
            combined_diff_lines.append("")
            # 统计该环境的差异条目数
            diff_count = sum(1 for line in content.splitlines() if line.startswith("元素："))
            diff_file_count += diff_count

        combined_diff_path = os.path.join(OUTPUT_DIR, "combined_marshal_diff.txt")
        with open(combined_diff_path, "w", encoding="utf-8") as f:
            f.write("\n".join(combined_diff_lines))
        print(f"   合并哈希差异: {combined_diff_path} (共 {diff_file_count} 条差异，来自 {len(diff_files)} 个环境)")
    else:
        print("   无哈希差异文件需要合并")

    # 写入合并日志
    if merged_lines:
        merged_path = os.path.join(OUTPUT_DIR, "combined_console_logs.txt")
        with open(merged_path, "w", encoding="utf-8") as f:
            f.write("\n".join(merged_lines))
        print(f"   合并日志: {merged_path}")

    # ================================================================
    # 1. 环境元数据
    # ================================================================
    envs = []
    env_keys = []
    for r in all_reports:
        meta = r.get("metadata", {})
        py_ver = meta.get("current_version", "?")
        plat = meta.get("platform", "?")
        envs.append({
            "python_version": meta.get("python_version", "?"),
            "python_short": f"Python {py_ver}",
            "platform": plat,
            "machine": meta.get("machine", "?"),
            "timestamp": meta.get("timestamp", "?"),
            "current_version": py_ver,
            "baseline_version": meta.get("baseline_version", "?"),
            "marshal_version": meta.get("marshal_version", "?"),
        })
        env_keys.append(f"{plat} Py{py_ver}")

    # ================================================================
    # 2. 按类型分组统计
    # ================================================================
    overall = {}
    for i, r in enumerate(all_reports):
        key = env_keys[i]
        summary = _compute_summary(r)
        overall[key] = summary

    # ================================================================
    # 3. 静态用例跨环境对比
    # ================================================================
    static_comparison = _build_static_comparison(all_reports, env_keys)

    # ================================================================
    # 4. Fuzzer 跨环境对比
    # ================================================================
    fuzzer_comparison = _build_fuzzer_comparison(all_reports, env_keys)

    # ================================================================
    # 5. ★★★ 核心分析：按 Python 版本分组的跨 OS 一致性 ★★★
    # ================================================================
    os_consistency = _analyze_cross_os_consistency(all_reports, envs)

    # ================================================================
    # 6. 矩阵环境验证报告合集
    # ================================================================
    matrix_reports_summary = _collect_matrix_reports(all_matrix_reports)

    # ================================================================
    # 7. 最终结论
    # ================================================================
    conclusion = _generate_conclusion(os_consistency, static_comparison, fuzzer_comparison, summary)

    # ================================================================
    # 8. 拼装最终报告
    # ================================================================
    combined = {
        "combined_report": {
            "summary": {
                "total_environments": len(all_reports),
                "total_matrix_verification_reports": len(all_matrix_reports),
                "environments": envs,
                "overall": overall,
            },
            "static_cross_environment_comparison": static_comparison,
            "fuzzer_cross_environment_comparison": fuzzer_comparison,
            "cross_os_consistency_by_python_version": os_consistency,
            "matrix_verification_results": matrix_reports_summary,
            "diagnostic_summary": diag_info,
            "conclusion": conclusion,
            "console_logs": console_logs,
            "raw_environments": [
                {
                    "environment": env_keys[i],
                    "metadata": r.get("metadata", {}),
                    "static_results": r.get("static_results", []),
                    "fuzzer_results": r.get("fuzzer_results", []),
                }
                for i, r in enumerate(all_reports)
            ],
        },
    }

    # ---- 写汇总 JSON ----
    json_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    # ---- 写汇总 TXT（人类可读摘要）----
    txt_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.txt")
    _write_summary_txt(txt_path, combined, conclusion)

    print(f"\n{'='*60}")
    print(f"  ✅ 合并完成")
    print(f"  环境数: {len(all_reports)}")
    print(f"  汇总 JSON: {json_path}")
    print(f"  汇总 TXT : {txt_path}")
    static_total = static_comparison.get("total_cases", 0)
    fuzzer_total = fuzzer_comparison.get("total_iterations", 0)
    print(f"  静态用例: {static_total} 个 × {len(all_reports)} 环境")
    print(f"  模糊测试: {fuzzer_total} 轮 × {len(all_reports)} 环境")
    print(f"{'='*60}")


# ====================================================================
# 辅助函数
# ====================================================================

def _load_json_files(file_list, label=""):
    """加载 JSON 文件列表"""
    result = []
    for path in sorted(file_list):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                result.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  警告: 无法加载 {label} 报告 {path}: {e}")
    return result


def _collect_diagnostics(diag_random_files, diag_iter8_files):
    """收集诊断脚本的输出，提取 hash(None) 跨平台对比"""
    result = {
        "hash_none_comparison": {},
        "hash_none_consistent": False,
        "diagnose_iter8": {},
    }

    # 从 diagnose_random 输出中提取 hash(None)
    for fpath in sorted(diag_random_files):
        tag = _extract_env_tag_from_diag_path(fpath)
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                content = f.read()
            # 提取 hash(None) 行
            for line in content.splitlines():
                if "hash(None)" in line:
                    result["hash_none_comparison"][tag] = line.strip()
                if "hash(None)" in line and "=" in line:
                    pass
        except OSError:
            pass

    # 从 diagnose_iter8 输出中提取分层 hash
    for fpath in sorted(diag_iter8_files):
        tag = _extract_env_tag_from_diag_path(fpath)
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                content = f.read()
            result["diagnose_iter8"][tag] = content[:2000]  # 保存前 2000 字符
        except OSError:
            pass

    # 判断 hash(None) 是否跨平台一致
    hash_vals = set(result["hash_none_comparison"].values())
    result["hash_none_consistent"] = len(hash_vals) <= 1

    return result


def _extract_env_tag_from_diag_path(fpath):
    """从 diagnose 文件名提取环境标签"""
    basename = os.path.basename(fpath)
    # 格式: diagnose_random_ubuntu-latest-py3.10.txt
    # 或     diagnose_iter8_windows-latest-py3.9.txt
    parts = basename.replace("diagnose_random_", "").replace("diagnose_iter8_", "").replace(".txt", "").split("-py")
    if len(parts) == 2:
        os_part = parts[0].replace("-latest", "").replace("-", " ").title()
        py_part = f"Py{parts[1]}"
        return f"{os_part} {py_part}"
    return basename


def _extract_env_tag_from_path(txt_path):
    """从路径推断环境标识"""
    parent_dir = os.path.basename(os.path.dirname(txt_path))
    if parent_dir.startswith("report-"):
        # report-ubuntu-latest-py3.12 → Ubuntu Py3.12
        tag = parent_dir.replace("report-", "")
        # 去掉 -latest 后缀
        tag = tag.replace("-latest", "")
        # 分隔 os 和 python 部分
        parts = tag.split("-py")
        if len(parts) == 2:
            os_part = parts[0].replace("-", " ").title()
            py_part = f"Py{parts[1]}"
            return f"{os_part} {py_part}"
        return tag.replace("-", " ").title()
    else:
        return os.path.basename(txt_path).replace("marshal_report_py", "").replace(".txt", "")


def _compute_summary(report):
    """统计单个报告的通过/失败/变化/不确定等数量"""
    static = report.get("static_results", [])
    fuzzer = report.get("fuzzer_results", [])

    def _count(items):
        counts = {
            "passed": 0, "failed": 0, "changed": 0, "unchanged": 0,
            "uncertain": 0, "no_baseline": 0, "error": 0,
        }
        for item in items:
            s = item.get("status", "")
            if s in ("uncertain_drift", "uncertain_stable", "uncertain_skip"):
                counts["uncertain"] += 1
            elif s in counts:
                counts[s] += 1
            else:
                counts["error"] += 1
        return counts

    static_counts = _count(static)
    fuzzer_counts = _count(fuzzer)

    return {
        "total_static": len(static),
        "total_fuzzer": len(fuzzer),
        "static": static_counts,
        "fuzzer": fuzzer_counts,
    }


def _build_static_comparison(all_reports, env_keys):
    """构建静态用例在所有环境间的状态对比表"""
    case_names = set()
    for r in all_reports:
        for c in r.get("static_results", []):
            case_names.add(c["name"])
    case_names = sorted(case_names)

    rows = []
    for name in case_names:
        row = {"case": name, "category": "", "type": "", "environments": {}}
        all_statuses = set()
        for r, key in zip(all_reports, env_keys):
            found = [c for c in r.get("static_results", []) if c["name"] == name]
            if found:
                c = found[0]
                row["category"] = c.get("category", "")
                row["type"] = c.get("type", "")
                status = c.get("status", "?")
                row["environments"][key] = {
                    "status": status,
                    "error": c.get("error"),
                }
                all_statuses.add(status)
            else:
                row["environments"][key] = {"status": "missing", "error": None}
                all_statuses.add("missing")
        row["all_same"] = len(all_statuses) == 1
        rows.append(row)

    return {
        "total_cases": len(rows),
        "environment_keys": env_keys,
        "details": rows,
    }


def _build_fuzzer_comparison(all_reports, env_keys):
    """构建 fuzzer 用例在所有环境间的状态对比表"""
    max_iter = 0
    for r in all_reports:
        fuzz = r.get("fuzzer_results", [])
        if fuzz:
            max_iter = max(max_iter, max(f.get("iteration", 0) for f in fuzz) + 1)

    rows = []
    for i in range(max_iter):
        row = {"iteration": i, "environments": {}}
        all_statuses = set()
        for r, key in zip(all_reports, env_keys):
            found = [f for f in r.get("fuzzer_results", []) if f.get("iteration") == i]
            if found:
                f = found[0]
                status = f.get("status", "?")
                row["environments"][key] = {
                    "status": status,
                    "type": f.get("type", ""),
                    "error": f.get("error"),
                }
                all_statuses.add(status)
            else:
                row["environments"][key] = {
                    "status": "missing", "type": "", "error": None,
                }
                all_statuses.add("missing")
        row["all_same"] = len(all_statuses) == 1
        rows.append(row)

    return {
        "total_iterations": len(rows),
        "environment_keys": env_keys,
        "details": rows,
    }


def _analyze_cross_os_consistency(all_reports, envs):
    """
    按 Python 版本分组分析跨操作系统一致性。
    这是验证「marshal 与 OS 无关」的核心分析。
    """
    # 按 Python 短版本分组
    groups = defaultdict(list)  # py_version → [(platform, report)]
    for i, r in enumerate(all_reports):
        meta = r.get("metadata", {})
        py_ver = meta.get("current_version", "?")
        plat = meta.get("platform", "?")
        groups[py_ver].append((plat, r))

    result = {
        "analysis": "按 Python 版本分组，比较同一版本在不同操作系统上的结果是否一致",
        "python_groups": {},
        "overall_consistent": True,
        "summary": "",
    }

    for py_ver in sorted(groups.keys()):
        entries = groups[py_ver]
        platforms = [e[0] for e in entries]
        reports = [e[1] for e in entries]

        # 比较静态结果是否完全一致
        static_consistent = True
        static_diff_details = []

        if len(reports) > 1:
            ref_static = reports[0].get("static_results", [])
            ref_names = {c["name"] for c in ref_static}

            for idx in range(1, len(reports)):
                cur_static = reports[idx].get("static_results", [])
                cur_map = {c["name"]: c for c in cur_static}

                for ref_c in ref_static:
                    name = ref_c["name"]
                    if name in cur_map:
                        cur_c = cur_map[name]
                        if ref_c.get("status") != cur_c.get("status"):
                            static_consistent = False
                            static_diff_details.append(
                                f"{name}: {platforms[0]}={ref_c.get('status')} vs "
                                f"{platforms[idx]}={cur_c.get('status')}"
                            )
                    else:
                        static_consistent = False
                        static_diff_details.append(f"{name}: missing in {platforms[idx]}")

        # 比较 fuzzer 结果
        fuzzer_consistent = True
        fuzzer_diff_details = []

        if len(reports) > 1:
            ref_fuzzer = reports[0].get("fuzzer_results", [])
            ref_by_iter = {f["iteration"]: f for f in ref_fuzzer}

            for idx in range(1, len(reports)):
                cur_fuzzer = reports[idx].get("fuzzer_results", [])
                cur_by_iter = {f["iteration"]: f for f in cur_fuzzer}

                for iter_num, ref_f in ref_by_iter.items():
                    if iter_num in cur_by_iter:
                        cur_f = cur_by_iter[iter_num]
                        if ref_f.get("status") != cur_f.get("status"):
                            fuzzer_consistent = False
                            fuzzer_diff_details.append(
                                f"iter {iter_num}: {platforms[0]}={ref_f.get('status')} vs "
                                f"{platforms[idx]}={cur_f.get('status')}"
                            )
                    else:
                        fuzzer_consistent = False
                        fuzzer_diff_details.append(
                            f"iter {iter_num}: missing in {platforms[idx]}"
                        )

        consistent = static_consistent and fuzzer_consistent
        if not consistent:
            result["overall_consistent"] = False

        py_group = {
            "python_version": py_ver,
            "platforms": platforms,
            "platform_count": len(platforms),
            "static_consistent": static_consistent,
            "fuzzer_consistent": fuzzer_consistent,
            "overall_consistent": consistent,
            "differences": {
                "static": static_diff_details,
                "fuzzer": fuzzer_diff_details,
            },
        }
        result["python_groups"][py_ver] = py_group

    # 生成摘要
    total_groups = len(groups)
    consistent_groups = sum(
        1 for g in result["python_groups"].values() if g["overall_consistent"]
    )
    result["summary"] = (
        f"共 {total_groups} 个 Python 版本组，"
        f"{consistent_groups}/{total_groups} 组在所有操作系统上结果完全一致。"
        if result["overall_consistent"]
        else f"发现不一致: {total_groups - consistent_groups}/{total_groups} 个版本组存在跨 OS 差异。"
    )

    return result


def _collect_matrix_reports(all_matrix_reports):
    """收集所有矩阵环境验证报告"""
    if not all_matrix_reports:
        return {"total": 0, "reports": []}

    collected = []
    for r in all_matrix_reports:
        meta = r.get("metadata", {})
        summary = r.get("summary", {})
        collected.append({
            "environment": {
                "python_version": meta.get("python_version_short", "?"),
                "platform": meta.get("platform", "?"),
                "machine": meta.get("machine", "?"),
                "architecture": meta.get("architecture", "?"),
            },
            "test_summary": summary,
            "test_results": r.get("test_results", []),
        })

    return {"total": len(collected), "reports": collected}


def _generate_conclusion(os_consistency, static_comparison, fuzzer_comparison, summary):
    """生成最终结论"""
    consistent = os_consistency.get("overall_consistent", False)
    static_cases = static_comparison.get("total_cases", 0)
    fuzzer_iters = fuzzer_comparison.get("total_iterations", 0)

    conclusion_parts = []

    if consistent:
        conclusion_parts.append(
            "结论: marshal 序列化输出与操作系统无关，仅与 Python 版本有关。"
        )
        conclusion_parts.append(
            f"在全部 {len(os_consistency.get('python_groups', {}))} 个 Python 版本组中，"
            "每个版本在 Windows/Linux/macOS 上的输出完全一致。"
        )
    else:
        conclusion_parts.append(
            "结论: 部分 Python 版本在不同操作系统上存在 marshal 输出差异。"
        )

    # 跨版本分析：收集各版本的 marshal.version
    version_info = {}
    for env in summary.get("environments", []):
        py_ver = env.get("current_version", "?")
        mv = env.get("marshal_version", "?")
        if py_ver not in version_info:
            version_info[py_ver] = mv

    conclusion_parts.append("")
    conclusion_parts.append("--- 版本依赖性分析 ---")
    for py_ver in sorted(version_info.keys(), key=lambda v: float(v)):
        mv = version_info[py_ver]
        conclusion_parts.append(f"  Python {py_ver:<5} → marshal.version = {mv}")

    mv_set = set(version_info.values())
    if len(mv_set) > 1:
        conclusion_parts.append(
            f"  → marshal.version 存在差异 ({', '.join(sorted(mv_set, key=str))})，证明格式随版本变化。"
        )
    else:
        conclusion_parts.append(
            "  → 本轮测试中各版本的 marshal.version 相同，基础类型编码未变。"
        )

    # 跨版本分析
    conclusion_parts.append("")
    conclusion_parts.append(
        f"跨版本分析: {static_cases} 个静态用例 + {fuzzer_iters} 轮模糊测试"
    )

    return {
        "summary": " ".join(conclusion_parts),
        "details": conclusion_parts,
        "marshal_depends_on_python_version_not_os": consistent,
        "total_static_cases": static_cases,
        "total_fuzzer_iterations": fuzzer_iters,
    }


def _write_summary_txt(txt_path, combined, conclusion):
    """写入人类可读的汇总 TXT"""
    combined_report = combined.get("combined_report", {})
    summary = combined_report.get("summary", {})
    os_consistency = combined_report.get("cross_os_consistency_by_python_version", {})
    conclusion_data = conclusion

    lines = []
    lines.append("=" * 68)
    lines.append("  marshal 序列化稳定性测试 — 汇总报告")
    lines.append("=" * 68)
    lines.append("")

    # 环境列表
    lines.append("▌ 测试环境")
    lines.append(f"{'─'*68}")
    for env in summary.get("environments", []):
        py_short = env.get("python_short", "?")
        plat = env.get("platform", "?")
        mach = env.get("machine", "?")
        mv = env.get("marshal_version", "?")
        lines.append(f"  {py_short:<12} | {plat:<14} | {mach:<8} | marshal v{mv}")
    lines.append("")

    # 按组统计
    lines.append("▌ 各环境测试统计")
    lines.append(f"{'─'*68}")
    overall_data = summary.get("overall", {})
    for env_key in sorted(overall_data.keys()):
        data = overall_data[env_key]
        static = data.get("static", {})
        fuzzer = data.get("fuzzer", {})
        lines.append(f"  {env_key}")
        lines.append(f"      静态: 总计={data['total_static']}, "
                     f"通过={static.get('passed',0)}, "
                     f"失败={static.get('failed',0)}, "
                     f"兼容={static.get('unchanged',0)}, "
                     f"变化={static.get('changed',0)}, "
                     f"不确定={static.get('uncertain',0)}")
        lines.append(f"      Fuzzer: 总计={data['total_fuzzer']}, "
                     f"通过={fuzzer.get('passed',0)}, "
                     f"兼容={fuzzer.get('unchanged',0)}, "
                     f"变化={fuzzer.get('changed',0)}, "
                     f"不确定={fuzzer.get('uncertain',0)}")
    lines.append("")

    # ★★★ 核心分析：跨 OS 一致性 ★★★
    lines.append("▌ ★★★ 核心分析：marshal 是否与操作系统无关？")
    lines.append(f"{'─'*68}")
    lines.append(f"  分析方式: 按 Python 版本分组，对比不同 OS 的测试结果")
    lines.append("")

    for py_ver, group in sorted(os_consistency.get("python_groups", {}).items()):
        platforms = group.get("platforms", [])
        consistent = group.get("overall_consistent", False)
        status_str = "✓ 完全一致" if consistent else "✗ 存在差异"

        lines.append(f"  Python {py_ver}  — {status_str}")
        lines.append(f"    操作系统: {', '.join(platforms)}")
        lines.append(f"    静态结果一致: {'是' if group.get('static_consistent') else '否'}")
        lines.append(f"    模糊测试一致: {'是' if group.get('fuzzer_consistent') else '否'}")

        diffs = group.get("differences", {})
        if diffs.get("static"):
            for d in diffs["static"][:5]:
                lines.append(f"      静态差异: {d}")
        if diffs.get("fuzzer"):
            for d in diffs["fuzzer"][:5]:
                lines.append(f"      Fuzzer差异: {d}")
        lines.append("")

    overall_consistent = os_consistency.get("overall_consistent", False)
    lines.append(
        f"  总体判定: {'✓ 全部一致 — marshal 序列化与操作系统无关' if overall_consistent else '✗ 存在差异'}"
    )
    lines.append("")

    # 诊断摘要：hash(None) 跨平台对比
    diag_info = combined_report.get("diagnostic_summary", {})
    hc = diag_info.get("hash_none_comparison", {})
    if hc:
        lines.append("▌ 诊断：hash(None) 跨平台对比（基于 random.seed）")
        lines.append(f"{'─'*68}")
        for tag, val in sorted(hc.items()):
            lines.append(f"  {tag:<20s} → {val}")
        consistent = diag_info.get("hash_none_consistent", False)
        lines.append(f"  结论: hash(None) 跨平台{'一致' if consistent else '不一致（不同进程地址不同）'}")
        lines.append("")

    # 结论
    lines.append("▌ 最终结论")
    lines.append(f"{'─'*68}")
    for part in conclusion_data.get("details", []):
        lines.append(f"  {part}")
    lines.append("")
    lines.append(f"  详细数据请见 combined_marshal_report.json")
    lines.append("=" * 68)
    lines.append(f"  生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 68)
    lines.append("")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"   汇总 TXT: {txt_path}")


def _write_empty_report():
    """当没有报告时输出空报告占位"""
    empty = {"combined_report": {"error": "没有找到任何 marshal 报告文件"}}
    json_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(empty, f, indent=2)
    txt_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("没有找到任何 marshal 报告文件\n")


if __name__ == "__main__":
    main()
