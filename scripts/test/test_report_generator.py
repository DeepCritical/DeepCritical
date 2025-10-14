#!/usr/bin/env python3
"""
Test report generator for DeepCritical.

This script generates comprehensive test reports from pytest results
and benchmarking data.
"""

import argparse
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_junit_xml(xml_file: Path) -> dict[str, Any]:
    """Parse JUnit XML test results."""
    tree = ET.parse(xml_file)
    root = tree.getroot()

    testsuites = []
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_time = 0.0

    for testsuite in root.findall("testsuite"):
        suite_name = testsuite.get("name", "unknown")
        suite_tests = int(testsuite.get("tests", 0))
        suite_failures = int(testsuite.get("failures", 0))
        suite_errors = int(testsuite.get("errors", 0))
        suite_time = float(testsuite.get("time", 0))

        total_tests += suite_tests
        total_failures += suite_failures
        total_errors += suite_errors
        total_time += suite_time

        testsuites.append(
            {
                "name": suite_name,
                "tests": suite_tests,
                "failures": suite_failures,
                "errors": suite_errors,
                "time": suite_time,
            }
        )

    return {
        "testsuites": testsuites,
        "total_tests": total_tests,
        "total_failures": total_failures,
        "total_errors": total_errors,
        "total_time": total_time,
        "success_rate": (
            ((total_tests - total_failures - total_errors) / total_tests * 100)
            if total_tests > 0
            else 0
        ),
    }


def parse_benchmark_json(json_file: Path) -> dict[str, Any]:
    """Parse benchmark JSON results."""
    if not json_file.exists():
        return {"benchmarks": [], "summary": {}}

    with json_file.open() as f:
        data = json.load(f)

    benchmarks = [
        {
            "name": benchmark.get("name", "unknown"),
            "fullname": benchmark.get("fullname", ""),
            "stats": benchmark.get("stats", {}),
            "group": benchmark.get("group", "default"),
        }
        for benchmark in data.get("benchmarks", [])
    ]

    return {
        "benchmarks": benchmarks,
        "summary": {
            "total_benchmarks": len(benchmarks),
            "machine_info": data.get("machine_info", {}),
            "datetime": data.get("datetime", ""),
        },
    }


def generate_html_report(
    junit_data: dict[str, Any], benchmark_data: dict[str, Any], output_file: Path
):
    """Generate HTML test report."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>DeepCritical Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .metric {{ text-align: center; padding: 10px; background: #e8f4f8; border-radius: 5px; }}
        .testsuites {{ margin: 20px 0; }}
        .testsuite {{ margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 5px; }}
        .benchmarks {{ margin: 20px 0; }}
        .benchmark {{ margin: 10px 0; padding: 10px; background: #fff; border: 1px solid #ddd; border-radius: 5px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .error {{ color: orange; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DeepCritical Test Report</h1>
        <p>Generated on: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>

    <div class="summary">
        <div class="metric">
            <h3>Total Tests</h3>
            <div style="font-size: 2em;">{junit_data["total_tests"]}</div>
        </div>
        <div class="metric">
            <h3>Success Rate</h3>
            <div style="font-size: 2em;">{junit_data["success_rate"]:.1f}%</div>
        </div>
        <div class="metric">
            <h3>Total Time</h3>
            <div style="font-size: 2em;">{junit_data["total_time"]:.2f}s</div>
        </div>
        <div class="metric">
            <h3>Benchmarks</h3>
            <div style="font-size: 2em;">{
        benchmark_data["summary"].get("total_benchmarks", 0)
    }</div>
        </div>
    </div>

    <div class="testsuites">
        <h2>Test Suites</h2>
        {
        "".join(
            f'''
        <div class="testsuite">
            <h3>{suite["name"]}</h3>
            <p>Tests: {suite["tests"]}, Failures: {suite["failures"]}, Errors: {suite["errors"]}, Time: {suite["time"]:.2f}s</p>
        </div>
        '''
            for suite in junit_data["testsuites"]
        )
    }
    </div>

    <div class="benchmarks">
        <h2>Performance Benchmarks</h2>
        {
        "".join(
            f'''
        <div class="benchmark">
            <h4>{bench["name"]}</h4>
            <p>Group: {bench["group"]}</p>
            <p>Mean: {bench["stats"].get("mean", "N/A")}, StdDev: {bench["stats"].get("stddev", "N/A")}</p>
        </div>
        '''
            for bench in benchmark_data["benchmarks"][:10]
        )
    }  <!-- Show first 10 benchmarks -->
    </div>
</body>
</html>
"""

    with output_file.open("w") as f:
        f.write(html)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test reports for DeepCritical"
    )
    parser.add_argument(
        "--junit-xml",
        type=Path,
        default=Path("test-results.xml"),
        help="JUnit XML test results file",
    )
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        default=Path("benchmark.json"),
        help="Benchmark JSON results file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_report.html"),
        help="Output HTML report file",
    )

    args = parser.parse_args()

    # Parse test results
    junit_data = parse_junit_xml(args.junit_xml)
    benchmark_data = parse_benchmark_json(args.benchmark_json)

    # Generate HTML report
    generate_html_report(junit_data, benchmark_data, args.output)


if __name__ == "__main__":
    main()
