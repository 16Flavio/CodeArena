"""Validate the 12 reference solutions of Chapter 2 against the DB test cases."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REF = {
    "EX_DS_QUEUE": """import sys
def main():
    data = sys.stdin.read().splitlines()
    q = int(data[0])
    in_, out_ = [], []
    res = []
    for i in range(1, q + 1):
        p = data[i].split()
        if p[0] == 'P':
            in_.append(p[1])
        else:
            if not out_:
                while in_: out_.append(in_.pop())
            res.append(out_.pop() if out_ else 'EMPTY')
    sys.stdout.write('\\n'.join(res) + ('\\n' if res else ''))
main()
""",
    "EX_DS_SLIDING": """import sys
from collections import deque
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    dq = deque(); res = []
    for i, x in enumerate(a):
        while dq and dq[0] <= i - k: dq.popleft()
        while dq and a[dq[-1]] <= x: dq.pop()
        dq.append(i)
        if i >= k - 1: res.append(a[dq[0]])
    print(' '.join(map(str, res)))
main()
""",
    "EX_DS_JOSEPHUS": """import sys
def main():
    n, k = map(int, sys.stdin.read().split())
    j = 0
    for m in range(2, n+1):
        j = (j + k) % m
    print(j + 1)
main()
""",
    "EX_HT_DISTINCT": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    vals = list(map(int, data[1:1+n]))
    print(len(set(vals)))
main()
""",
    "EX_HT_TWOSUM": """import sys
def main():
    data = sys.stdin.read().split()
    n, t = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    seen = {}
    for j, x in enumerate(a):
        c = t - x
        if c in seen:
            print(str(seen[c]+1) + ' ' + str(j+1)); return
        if x not in seen: seen[x] = j
    print('NONE')
main()
""",
    "EX_HT_ZEROSUM": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    last = {0: -1}
    s = 0; best = float('inf')
    for j, x in enumerate(a):
        s += x
        if s in last:
            best = min(best, j - last[s])
        last[s] = j
    print(best if best != float('inf') else -1)
main()
""",
    "EX_BST_INORDER": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    vals = list(map(int, data[1:1+n]))
    class N:
        __slots__=('k','l','r')
        def __init__(s,k): s.k=k; s.l=None; s.r=None
    root=None
    for v in vals:
        if root is None: root=N(v); continue
        cur=root
        while True:
            if v < cur.k:
                if cur.l is None: cur.l=N(v); break
                cur=cur.l
            elif v > cur.k:
                if cur.r is None: cur.r=N(v); break
                cur=cur.r
            else: break
    res=[]; stack=[]; cur=root
    while cur or stack:
        while cur: stack.append(cur); cur=cur.l
        cur=stack.pop(); res.append(cur.k); cur=cur.r
    print(' '.join(map(str,res)))
main()
""",
    "EX_BST_PREORDER": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    stack = []; lower = float('-inf')
    for x in a:
        if x <= lower: print('NO'); return
        while stack and stack[-1] < x: lower = stack.pop()
        stack.append(x)
    print('YES')
main()
""",
    "EX_BST_HEIGHT": """import sys
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    class N:
        __slots__=('k','l','r')
        def __init__(s,k): s.k=k; s.l=None; s.r=None
    root=None
    for v in a:
        if root is None: root=N(v); continue
        cur=root
        while True:
            if v < cur.k:
                if cur.l is None: cur.l=N(v); break
                cur=cur.l
            elif v > cur.k:
                if cur.r is None: cur.r=N(v); break
                cur=cur.r
            else: break
    if not root: print(0); return
    stack = [(root, 1)]; best = 0
    while stack:
        node, d = stack.pop()
        if d > best: best = d
        if node.l: stack.append((node.l, d+1))
        if node.r: stack.append((node.r, d+1))
    print(best)
main()
""",
    "EX_HP_HEAPSORT": """import sys, heapq
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    heapq.heapify(a)
    out = [heapq.heappop(a) for _ in range(n)]
    print(' '.join(map(str, out)))
main()
""",
    "EX_HP_KSMALL": """import sys, heapq
def main():
    data = sys.stdin.read().split()
    n, k = int(data[0]), int(data[1])
    a = list(map(int, data[2:2+n]))
    heap = []
    for x in a:
        if len(heap) < k:
            heapq.heappush(heap, -x)
        elif -heap[0] > x:
            heapq.heapreplace(heap, -x)
    out = sorted(-x for x in heap)
    print(' '.join(map(str, out)))
main()
""",
    "EX_HP_MERGE": """import sys, heapq
def main():
    data = sys.stdin.read().split()
    n = int(data[0])
    a = list(map(int, data[1:1+n]))
    if n <= 1: print(0); return
    heapq.heapify(a)
    cost = 0
    while len(a) > 1:
        x = heapq.heappop(a); y = heapq.heappop(a)
        cost += x + y
        heapq.heappush(a, x + y)
    print(cost)
main()
""",
}

# Map title_fr -> key. We use code keys instead of text titles to avoid
# encoding issues with accents and apostrophes.
KEY_BY_ID_OFFSET = [
    ("EX_DS_QUEUE", "EX_DS_SLIDING", "EX_DS_JOSEPHUS"),
    ("EX_HT_DISTINCT", "EX_HT_TWOSUM", "EX_HT_ZEROSUM"),
    ("EX_BST_INORDER", "EX_BST_PREORDER", "EX_BST_HEIGHT"),
    ("EX_HP_HEAPSORT", "EX_HP_KSMALL", "EX_HP_MERGE"),
]


def normalize(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())


def main():
    db_path = Path(__file__).resolve().parent.parent.parent / "contest.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """SELECT le.id, l.slug, l.order_idx, le.test_cases
           FROM lesson_exercises le JOIN lessons l ON l.id = le.lesson_id
           WHERE l.section_id = (SELECT id FROM learning_sections
                                 WHERE slug='structures-de-donnees')
           ORDER BY l.order_idx, le.id"""
    )
    rows = c.fetchall()

    # Group by lesson order_idx
    by_lesson: dict[int, list] = {}
    for ex_id, lslug, l_order, tests_json in rows:
        by_lesson.setdefault(l_order, []).append((ex_id, lslug, tests_json))

    ok_total = fail_total = 0
    for lesson_order in sorted(by_lesson):
        keys = KEY_BY_ID_OFFSET[lesson_order]
        for (ex_id, lslug, tests_json), key in zip(by_lesson[lesson_order], keys):
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
