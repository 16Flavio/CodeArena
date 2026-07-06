"""Validate the 12 reference solutions of Chapter 1 against the seed test cases."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from seed_chapter1 import LESSONS  # noqa: E402

REF = {
    "EX_RAM_STD": """import sys
def main():
    n = int(sys.stdin.readline())
    print(n*(n-1)//2)
main()
""",
    "EX_RAM_TWIST": """import sys
def main():
    a, b, c, k = map(int, sys.stdin.read().split())
    def h(n): return (k-a)*n*n - b*n - c
    last_bad = 0
    for n in range(1, 5000):
        if h(n) < 0: last_bad = n
    print(max(1, last_bad + 1))
main()
""",
    "EX_RAM_HARD": """import sys
def main():
    a, b = map(int, sys.stdin.read().split())
    n = 2
    while True:
        if a*n >= b*(n.bit_length()-1):
            print(n); break
        n += 1
main()
""",
    "EX_LOOP_STD": """import sys
def main():
    n = int(sys.stdin.readline())
    print(n*(n+1)//2)
main()
""",
    "EX_LOOP_TWIST": """import sys
def main():
    n = int(sys.stdin.readline())
    print(n.bit_length())
main()
""",
    "EX_LOOP_HARD": """import sys
MOD = 10**9 + 7
def main():
    r, n = map(int, sys.stdin.read().split())
    if r % MOD == 1:
        print(n % MOD)
    else:
        print((pow(r, n, MOD) - 1) * pow(r - 1, MOD - 2, MOD) % MOD)
main()
""",
    "EX_REC_STD": """import sys
def main():
    n = int(sys.stdin.readline())
    print(n.bit_length())
main()
""",
    "EX_REC_TWIST": """import sys
def main():
    a, b, d = map(int, sys.stdin.read().split())
    t = b**d
    print(1 if a > t else (2 if a == t else 3))
main()
""",
    "EX_REC_HARD": """import sys
from functools import lru_cache
sys.setrecursionlimit(10000)
MOD = 10**9 + 7
def main():
    a, b, n = map(int, sys.stdin.read().split())
    @lru_cache(maxsize=None)
    def T(m):
        if m < b:
            return m % MOD
        return (a * T((m + b - 1) // b) + m) % MOD
    print(T(n))
main()
""",
    "EX_AMO_STD": """import sys
def main():
    n = int(sys.stdin.readline())
    total = 0
    cap = 1
    while cap <= n - 1:
        total += cap
        cap *= 2
    print(total)
main()
""",
    "EX_AMO_TWIST": """import sys
def main():
    data = sys.stdin.read().splitlines()
    q = int(data[0])
    stack = []
    for i in range(1, q + 1):
        parts = data[i].split()
        if parts[0] == 'P':
            stack.append(parts[1])
        elif parts[0] == 'O':
            if stack: stack.pop()
        else:
            k = int(parts[1])
            del stack[max(0, len(stack) - k):]
    print(' '.join(stack) if stack else 'EMPTY')
main()
""",
    "EX_AMO_HARD": """import sys
def main():
    k = int(sys.stdin.readline())
    print(2*k - bin(k).count('1'))
main()
""",
}


def normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())


def main():
    ok_total = fail_total = 0
    for lesson in LESSONS:
        for ex in lesson["exercises"]:
            key = ex["key"]
            sol = REF[key]
            cases = ex["test_cases"]
            failed = []
            for i, case in enumerate(cases):
                proc = subprocess.run(
                    [sys.executable, "-c", sol],
                    input=case["input"].encode(),
                    capture_output=True,
                    timeout=15,
                )
                actual = proc.stdout.decode()
                if normalize(actual) != normalize(case["expected"]):
                    failed.append((
                        i,
                        case["input"][:40],
                        case["expected"][:40],
                        actual[:40],
                    ))
            if failed:
                print(f"  FAIL {key}: {len(failed)}/{len(cases)} failed")
                for f in failed[:3]:
                    print(f"    case {f[0]}: in={f[1]!r} exp={f[2]!r} got={f[3]!r}")
                fail_total += 1
            else:
                print(f"  OK   {key}: {len(cases)}/{len(cases)} pass")
                ok_total += 1

    print()
    print(f"TOTAL: {ok_total} ok, {fail_total} failing")
    return 1 if fail_total else 0


if __name__ == "__main__":
    raise SystemExit(main())
