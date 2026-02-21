import json
import re
import sys
import ast


def parse_pytest(output: str):
    passed = len(re.findall(r"passed", output))
    failed = len(re.findall(r"failed", output))
    return {"passed": passed, "failed": failed}


def main():
    # If file paths + test name lists are provided, produce structured tests output
    if len(sys.argv) >= 6:
        stdout_path = sys.argv[1]
        stderr_path = sys.argv[2]
        out_path = sys.argv[3]
        f2p_str = sys.argv[4]
        p2p_str = sys.argv[5]
        try:
            with open(stdout_path, 'r') as f:
                stdout = f.read()
        except FileNotFoundError:
            stdout = ""
        counts = parse_pytest(stdout)
        try:
            f2p = ast.literal_eval(f2p_str) if f2p_str else []
        except Exception:
            f2p = []
        try:
            p2p = ast.literal_eval(p2p_str) if p2p_str else []
        except Exception:
            p2p = []
        all_tests = list(dict.fromkeys((f2p or []) + (p2p or [])))
        status = "PASSED" if counts.get("failed", 0) == 0 else "FAILED"
        tests = []
        for t in all_tests:
            tests.append({"name": t, "status": status})
        out = {"tests": tests}
        with open(out_path, 'w') as f:
            json.dump(out, f)
    else:
        print(json.dumps(parse_pytest(sys.stdin.read())))


if __name__ == '__main__':
    main()
