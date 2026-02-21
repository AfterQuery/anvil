import json
import re

def parse_pytest(output: str):
    passed = len(re.findall(r"passed", output))
    failed = len(re.findall(r"failed", output))
    return json.dumps({"passed": passed, "failed": failed})

if __name__ == '__main__':
    import sys
    print(parse_pytest(sys.stdin.read()))
