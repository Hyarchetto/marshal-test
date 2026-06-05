#!/usr/bin/env python3
"""
合并所有 matrix 环境的 JSON 报告为一份汇总报告
"""

import json
import os
import glob

REPORT_DIR = "all-reports"
OUTPUT_DIR = "combined-report"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 收集所有 JSON 报告
    report_files = glob.glob(os.path.join(REPORT_DIR, "marshal_report_py*.json"))
    if not report_files:
        print("没有找到任何 marshal 报告文件")
        return

    all_reports = []
    for path in sorted(report_files):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            all_reports.append(data)

    # 提取环境元数据
    envs = []
    for r in all_reports:
        meta = r.get("metadata", {})
        envs.append({
            "python_version": meta.get("python_version", "?"),
            "platform": meta.get("platform", "?"),
            "current_version": meta.get("current_version", "?"),
            "baseline_version": meta.get("baseline_version", "?"),
        })

    # 汇总统计
    combined_summary = {
        "total_environments": len(all_reports),
        "environments": envs,
        "overall": {}
    }

    for r in all_reports:
        summary = r.get("summary", {})
        ver = r.get("metadata", {}).get("current_version", "?")
        plat = r.get("metadata", {}).get("platform", "?")
        key = f"{plat} Python {ver}"
        combined_summary["overall"][key] = summary

    # 生成跨环境比对表
    comparison_table = _build_comparison_table(all_reports)

    combined = {
        "combined_report": {
            "summary": combined_summary,
            "cross_environment_comparison": comparison_table,
        },
        "individual_reports": all_reports,
    }

    output_path = os.path.join(OUTPUT_DIR, "combined_marshal_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"✅ 合并完成: {len(all_reports)} 份报告 -> {output_path}")


def _build_comparison_table(all_reports):
    """构建用例在各环境间的哈希变化表"""
    from collections import OrderedDict

    # 收集所有用例名字
    case_names = set()
    for r in all_reports:
        for c in r.get("static_cases", []):
            case_names.add(c["name"])
    case_names = sorted(case_names)

    # 对每个用例列出各环境状态
    env_keys = []
    for r in all_reports:
        m = r.get("metadata", {})
        key = f"{m.get('platform', '?')} Py{m.get('current_version', '?')}"
        env_keys.append(key)

    rows = []
    for name in case_names:
        row = {"case": name, "type": "", "environments": {}}
        for r, key in zip(all_reports, env_keys):
            for c in r.get("static_cases", []):
                if c["name"] == name:
                    row["type"] = c.get("type", "")
                    row["environments"][key] = {
                        "status": c.get("status", "?"),
                        "hash": c.get("current_hash", "?")[:12],
                    }
                    break
        rows.append(row)

    return {
        "total_cases": len(rows),
        "environment_keys": env_keys,
        "details": rows,
    }


if __name__ == "__main__":
    main()
