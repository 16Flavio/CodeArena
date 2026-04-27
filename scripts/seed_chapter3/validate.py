"""Validate the 12 reference solutions of Chapter 3 against DB test cases."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REF = {
    "EX_SO_MERGE2": """import sys
def main():
    data = sys.stdin.read().split()
    n, m = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    b = list(map(int, data[2+n:2+n+m]))
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] <= b[j]: out.append(a[i]); i += 1
        else:            out.append(b[j]); j += 1
    out.extend(a[i:]); out.extend(b[j:])
    print(' '.join(map(str, out)))
main()
""",
    "EX_SO_INVERSIONS": """import sys
sys.setrecursionlimit(200000)
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    def msort(arr):
        if len(arr) <= 1: return arr, 0
        m = len(arr) // 2
        L, c1 = msort(arr[:m]); R, c2 = msort(arr[m:])
        merged = []; i = j = 0; c = c1 + c2
        while i < len(L) and j < len(R):
            if L[i] <= R[j]: merged.append(L[i]); i += 1
            else:            merged.append(R[j]); j += 1; c += len(L) - i
        merged.extend(L[i:]); merged.extend(R[j:])
        return merged, c
    _, count = msort(a)
    print(count)
main()
""",
    "EX_SO_KMERGE": """import sys, heapq
def main():
    data = sys.stdin.read().splitlines()
    k = int(data[0])
    arrs = []
    idx = 1
    for _ in range(k):
        size = int(data[idx]); idx += 1
        if size == 0:
            arrs.append([]); continue
        arrs.append(list(map(int, data[idx].split()))); idx += 1
    h = []
    for li, arr in enumerate(arrs):
        if arr: heapq.heappush(h, (arr[0], li, 0))
    out = []
    while h:
        v, li, pi = heapq.heappop(h)
        out.append(v)
        if pi + 1 < len(arrs[li]):
            heapq.heappush(h, (arrs[li][pi+1], li, pi+1))
    print(' '.join(map(str, out)))
main()
""",
    "EX_SO_PARTITION": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    pivot = a[-1]; i = 0
    for j in range(n - 1):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]; i += 1
    a[i], a[-1] = a[-1], a[i]
    print(i)
    print(' '.join(map(str, a)))
main()
""",
    "EX_SO_DUTCH": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    lo, mid, hi = 0, 0, n - 1
    while mid <= hi:
        if a[mid] == 0:
            a[lo], a[mid] = a[mid], a[lo]; lo += 1; mid += 1
        elif a[mid] == 2:
            a[mid], a[hi] = a[hi], a[mid]; hi -= 1
        else:
            mid += 1
    print(' '.join(map(str, a)))
main()
""",
    "EX_SO_RUNMEDIAN": """import sys, heapq
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    lo, hi = [], []  # lo max-heap (negated), hi min-heap
    out = []
    for x in a:
        if not lo or x <= -lo[0]:
            heapq.heappush(lo, -x)
        else:
            heapq.heappush(hi, x)
        if len(lo) > len(hi) + 1:
            heapq.heappush(hi, -heapq.heappop(lo))
        elif len(hi) > len(lo):
            heapq.heappush(lo, -heapq.heappop(hi))
        if (len(lo) + len(hi)) % 2 == 1:
            out.append(-2 * lo[0])
        else:
            out.append(-lo[0] + hi[0])
    print(' '.join(map(str, out)))
main()
""",
    "EX_SO_COUNTING": """import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    cnt = [0] * (k + 1)
    for x in a: cnt[x] += 1
    out = []
    for v, c in enumerate(cnt):
        out.extend([v] * c)
    print(' '.join(map(str, out)))
main()
""",
    "EX_SO_RADIX": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    if not a:
        print(''); return
    mx = max(a); exp = 1
    while mx // exp > 0:
        cnt = [0] * 10
        for x in a: cnt[(x // exp) % 10] += 1
        for i in range(1, 10): cnt[i] += cnt[i-1]
        out = [0] * n
        for x in reversed(a):
            d = (x // exp) % 10
            cnt[d] -= 1
            out[cnt[d]] = x
        a = out; exp *= 10
    print(' '.join(map(str, a)))
main()
""",
    "EX_SO_RADIX_STR": """import sys
def main():
    data = sys.stdin.read().split()
    n, d = int(data[0]), int(data[1])
    a = data[2:2+n]
    for pos in range(d - 1, -1, -1):
        buckets = [[] for _ in range(26)]
        for s in a:
            buckets[ord(s[pos]) - ord('a')].append(s)
        a = [s for b in buckets for s in b]
    print(' '.join(a))
main()
""",
    "EX_SO_SELECT": """import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    a.sort()
    print(a[k - 1])
main()
""",
    "EX_SO_MINMAX": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    print(min(a), max(a))
main()
""",
    "EX_SO_TOPK": """import sys
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    a.sort()
    print(' '.join(map(str, a[:k])))
main()
""",
}

KEY_BY_LESSON_ORDER = [
    ("EX_SO_MERGE2", "EX_SO_INVERSIONS", "EX_SO_KMERGE"),
    ("EX_SO_PARTITION", "EX_SO_DUTCH", "EX_SO_RUNMEDIAN"),
    ("EX_SO_COUNTING", "EX_SO_RADIX", "EX_SO_RADIX_STR"),
    ("EX_SO_SELECT", "EX_SO_MINMAX", "EX_SO_TOPK"),
]


def normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())


def main():
    db_path = Path(__file__).resolve().parent.parent.parent / "contest.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT le.id, l.order_idx, le.test_cases
           FROM lesson_exercises le JOIN lessons l ON l.id = le.lesson_id
           WHERE l.section_id = (SELECT id FROM learning_sections WHERE slug='tris')
           ORDER BY l.order_idx, le.id"""
    )
    rows = c.fetchall()

    by_lesson: dict[int, list] = {}
    for ex_id, l_order, tests_json in rows:
        by_lesson.setdefault(l_order, []).append((ex_id, tests_json))

    ok_total = fail_total = 0
    for lesson_order in sorted(by_lesson):
        keys = KEY_BY_LESSON_ORDER[lesson_order]
        for (ex_id, tests_json), key in zip(by_lesson[lesson_order], keys):
            sol = REF[key]
            cases = json.loads(tests_json)
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
                    failed.append((i, case["input"][:40], case["expected"][:40], actual[:40]))
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
