#!/usr/bin/env python3
"""
合并所有 matrix 环境的 JSON 报告为一份完整的汇总报告
包含：环境元数据、按类型分组统计、静态用例跨环境对比、fuzzer 跨环境对比、原始数据全集
"""

import json
import os
import glob

REPORT_DIR = "all-reports"
OUTPUT_DIR = "combined-report"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 收集所有 JSON 报告（递归搜索子目录）
    report_files = glob.glob(os.path.join(REPORT_DIR, "**", "marshal_report_py*.json"), recursive=True)
    if not report_files:
        print("没有找到任何 marshal 报告文件")
        return

    all_reports = []
    for path in sorted(report_files):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            all_reports.append(data)

    # 收集所有控制台日志（.txt 文件）
    txt_files = glob.glob(os.path.join(REPORT_DIR, "**", "marshal_report_py*.txt"), recursive=True)
    console_logs = {}
    for txt_path in sorted(txt_files):
        basename = os.path.basename(txt_path).replace("marshal_report_py", "").replace(".txt", "")
        with open(txt_path, encoding="utf-8", errors="replace") as f:
            console_logs[basename] = f.read()

    # ================================================================
    # 1. 环境元数据 & 基本汇总
    # ================================================================
    envs = []
    env_keys = []
    for r in all_reports:
        meta = r.get("metadata", {})
        py_ver = meta.get("current_version", "?")
        plat = meta.get("platform", "?")
        envs.append({
            "python_version": meta.get("python_version", "?"),
            "platform": plat,
            "machine": meta.get("machine", "?"),
            "timestamp": meta.get("timestamp", "?"),
            "current_version": py_ver,
            "baseline_version": meta.get("baseline_version", "?"),
        })
        env_keys.append(f"{plat} Py{py_ver}")

    # 按类型统计（每个环境各自汇总）
    overall = {}
    for i, r in enumerate(all_reports):
        key = env_keys[i]
        summary = _compute_summary(r)
        overall[key] = summary

    combined_summary = {
        "total_environments": len(all_reports),
        "environments": envs,
        "overall": overall,
    }

    # ================================================================
    # 2. 静态用例跨环境对比
    # ================================================================
    static_comparison = _build_static_comparison(all_reports, env_keys)

    # ================================================================
    # 3. Fuzzer 跨环境对比
    # ================================================================
    fuzzer_comparison = _build_fuzzer_comparison(all_reports, env_keys)

    # ================================================================
    # 4. 原始数据全集（每份报告的完整内容）
    # ================================================================
    raw_data = []
    for i, r in enumerate(all_reports):
        raw_data.append({
            "environment": env_keys[i],
            "metadata": r.get("metadata", {}),
            "static_results": r.get("static_results", []),
            "fuzzer_results": r.get("fuzzer_results", []),
        })

    # ================================================================
    # 5. 组装最终报告
    # ================================================================
    combined = {
        "combined_report": {
            "summary": combined_summary,
            "static_cross_environment_comparison": static_comparison,
            "fuzzer_cross_environment_comparison": fuzzer_comparison,
            "console_logs": console_logs,
            "raw_environments": raw_data,
        },
    }

    output_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"✅ 合并完成: {len(all_reports)} 份报告 -> {output_path}")
    static_total = static_comparison.get("total_cases", 0)
    fuzzer_total = fuzzer_comparison.get("total_iterations", 0)
    print(f"   静态用例: {static_total} 个 × {len(all_reports)} 环境 = {static_total * len(all_reports)} 条")
    print(f"   模糊测试: {fuzzer_total} 轮 × {len(all_reports)} 环境 = {fuzzer_total * len(all_reports)} 条")
    print(f"   控制台日志: {len(console_logs)} 份")
    print(f"   原始数据: {len(raw_data)} 份完整报告（已包含在上述对比中）")


def _compute_summary(report):
    """统计单个报告的通过/失败/变化/不确定等数量"""
    static = report.get("static_results", [])
    fuzzer = report.get("fuzzer_results", [])

    def _count(items):
        counts = {"passed": 0, "failed": 0, "changed": 0, "unchanged": 0,
                  "uncertain": 0, "no_baseline": 0, "error": 0}
        for item in items:
            s = item.get("status", "")
            if s in ("uncertain_drift", "uncertain_stable"):
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
    # 收集所有用例名字
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

        # 标记是否全环境一致
        row["all_same"] = len(all_statuses) == 1

        rows.append(row)

    return {
        "total_cases": len(rows),
        "environment_keys": env_keys,
        "details": rows,
    }


def _build_fuzzer_comparison(all_reports, env_keys):
    """构建 fuzzer 用例在所有环境间的状态对比表"""
    # fuzzer 通过 iteration 索引对应
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
                row["environments"][key] = {"status": "missing", "type": "", "error": None}
                all_statuses.add("missing")

        row["all_same"] = len(all_statuses) == 1
        rows.append(row)

    return {
        "total_iterations": len(rows),
        "environment_keys": env_keys,
        "details": rows,
    }


if __name__ == "__main__":
    main()
