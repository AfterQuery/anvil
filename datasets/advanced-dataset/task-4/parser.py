import json
import sys

def parse():
    text = sys.stdin.read()
    passed = text.count("PASSED")
    failed = text.count("FAILED")
    print(json.dumps({"raw": text, "passed": passed, "failed": failed}))

if __name__ == "__main__":
    parse()
