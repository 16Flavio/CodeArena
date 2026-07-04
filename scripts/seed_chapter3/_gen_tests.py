"""Generate + verify all Chapter 3 reference solutions outputs.
Run: python scripts/seed_chapter3/_gen_tests.py
"""
import heapq, sys
from collections import deque

# ── L1 - insertion + merge ───────────────────────────────────────

def sol_merge_two(stdin):
    """Merge two sorted arrays into one sorted output."""
    lines = stdin.strip().split('\n')
    n, m = map(int, lines[0].split())
    a = list(map(int, lines[1].split())) if n else []
    b = list(map(int, lines[2].split())) if m else []
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] <= b[j]: out.append(a[i]); i += 1
        else:            out.append(b[j]); j += 1
    out.extend(a[i:]); out.extend(b[j:])
    return ' '.join(map(str, out)) + '\n'

def sol_inversions(stdin):
    """Count inversions via mergesort (stable)."""
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split())) if n else []
    def msort(arr):
        if len(arr) <= 1: return arr, 0
        mid = len(arr) // 2
        l, c1 = msort(arr[:mid]); r, c2 = msort(arr[mid:])
        merged = []; i = j = 0; c = c1 + c2
        while i < len(l) and j < len(r):
            if l[i] <= r[j]: merged.append(l[i]); i += 1
            else:            merged.append(r[j]); j += 1; c += len(l) - i
        merged.extend(l[i:]); merged.extend(r[j:])
        return merged, c
    _, count = msort(a)
    return str(count) + '\n'

def sol_kmerge(stdin):
    """Merge K sorted lists; output the global sorted sequence."""
    lines = stdin.strip().split('\n')
    k = int(lines[0])
    arrs = []
    idx = 1
    for _ in range(k):
        size = int(lines[idx]); idx += 1
        if size == 0:
            arrs.append([]); continue
        arrs.append(list(map(int, lines[idx].split()))); idx += 1
    h = []
    for li, arr in enumerate(arrs):
        if arr: heapq.heappush(h, (arr[0], li, 0))
    out = []
    while h:
        v, li, pi = heapq.heappop(h)
        out.append(v)
        if pi + 1 < len(arrs[li]):
            heapq.heappush(h, (arrs[li][pi+1], li, pi+1))
    return ' '.join(map(str, out)) + '\n' if out else '\n'

# ── L2 - quicksort + heapsort ────────────────────────────────────

def sol_partition(stdin):
    """Lomuto partition with pivot = last element. Output:
       line 1 = pivot final index (0-indexed)
       line 2 = the array after partition.
    """
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    pivot = a[-1]; i = 0
    for j in range(n - 1):
        if a[j] <= pivot:
            a[i], a[j] = a[j], a[i]; i += 1
    a[i], a[-1] = a[-1], a[i]
    return f"{i}\n" + ' '.join(map(str, a)) + '\n'

def sol_dutch(stdin):
    """In-place 3-way partition of values in {0,1,2}. Output the array."""
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    lo, mid, hi = 0, 0, n - 1
    while mid <= hi:
        if a[mid] == 0:
            a[lo], a[mid] = a[mid], a[lo]; lo += 1; mid += 1
        elif a[mid] == 2:
            a[mid], a[hi] = a[hi], a[mid]; hi -= 1
        else:
            mid += 1
    return ' '.join(map(str, a)) + '\n'

def sol_running_median(stdin):
    """Running median: print median after each prefix length 1..n.
    Output integer 2*median (so we stay in integers): if even count, two
    middle values v1<=v2 → output v1+v2 (i.e. 2*median); if odd count,
    output 2*middle.
    """
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    lo = []  # max-heap (negated)
    hi = []  # min-heap
    out = []
    for x in a:
        if not lo or x <= -lo[0]:
            heapq.heappush(lo, -x)
        else:
            heapq.heappush(hi, x)
        # Rebalance: |lo| - |hi| in {0, 1}.
        if len(lo) > len(hi) + 1:
            heapq.heappush(hi, -heapq.heappop(lo))
        elif len(hi) > len(lo):
            heapq.heappush(lo, -heapq.heappop(hi))
        if (len(lo) + len(hi)) % 2 == 1:
            out.append(-2 * lo[0])  # 2*median = 2*lo[0] (lo top is negated)
            # wait: lo is max-heap (negated). lo[0] is -max. so max = -lo[0].
            # If odd count, median = max of lo = -lo[0]. 2*median = -2*lo[0].
        else:
            out.append(-lo[0] + hi[0])  # 2*median = lo_top + hi_top = -lo[0] + hi[0]
    return ' '.join(map(str, out)) + '\n'

# ── L3 - counting + radix ────────────────────────────────────────

def sol_counting(stdin):
    """Counting sort. Inputs in [0, k]."""
    lines = stdin.strip().split('\n')
    n, k = map(int, lines[0].split())
    a = list(map(int, lines[1].split())) if n else []
    cnt = [0] * (k + 1)
    for x in a: cnt[x] += 1
    out = []
    for v, c in enumerate(cnt):
        out.extend([v] * c)
    return ' '.join(map(str, out)) + '\n'

def sol_radix(stdin):
    """LSD radix sort on non-negative integers."""
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split())) if n else []
    if not a:
        return '\n'
    mx = max(a); exp = 1
    while mx // exp > 0:
        # one stable counting-sort pass on digit "exp"
        cnt = [0] * 10
        for x in a: cnt[(x // exp) % 10] += 1
        for i in range(1, 10): cnt[i] += cnt[i-1]
        out = [0] * n
        for x in reversed(a):
            d = (x // exp) % 10
            cnt[d] -= 1
            out[cnt[d]] = x
        a = out
        exp *= 10
    return ' '.join(map(str, a)) + '\n'

def sol_radix_strings(stdin):
    """Stable radix sort on fixed-length lowercase strings (LSD)."""
    lines = stdin.strip().split('\n')
    n, d = map(int, lines[0].split())
    if n == 0: return '\n'
    a = lines[1].split()
    # LSD radix on chars
    for pos in range(d - 1, -1, -1):
        buckets = [[] for _ in range(26)]
        for s in a:
            buckets[ord(s[pos]) - ord('a')].append(s)
        a = [s for b in buckets for s in b]
    return ' '.join(a) + '\n'

# ── L4 - selection ───────────────────────────────────────────────

def sol_quickselect(stdin):
    """k-th smallest (1-indexed)."""
    import random
    random.seed(42)
    lines = stdin.strip().split('\n')
    n, k = map(int, lines[0].split())
    a = list(map(int, lines[1].split()))
    a.sort()
    return str(a[k - 1]) + '\n'

def sol_minmax(stdin):
    """Print min and max."""
    lines = stdin.strip().split('\n')
    n = int(lines[0])
    a = list(map(int, lines[1].split()))
    return f"{min(a)} {max(a)}\n"

def sol_topk_sorted(stdin):
    """Top k smallest, in ascending order."""
    lines = stdin.strip().split('\n')
    n, k = map(int, lines[0].split())
    a = list(map(int, lines[1].split()))
    a.sort()
    return ' '.join(map(str, a[:k])) + '\n'


# ── Generation ───────────────────────────────────────────────────

CASES = [
    ('EX_SO_MERGE2',  sol_merge_two,  [
        ("3 3\n1 3 5\n2 4 6\n", True),
        ("4 0\n1 2 3 4\n\n", True),
        ("0 4\n\n5 6 7 8\n", False),
        ("5 5\n1 1 2 3 4\n0 1 5 6 9\n", False),
        ("1 1\n10\n5\n", False),
        ("3 3\n-3 0 7\n-5 4 9\n", False),
    ]),
    ('EX_SO_INVERSIONS', sol_inversions, [
        ("5\n2 4 1 3 5\n", True),  # 3 inversions
        ("4\n4 3 2 1\n", True),   # 6
        ("1\n42\n", False),        # 0
        ("5\n1 2 3 4 5\n", False), # 0
        ("6\n6 5 4 3 2 1\n", False),  # 15
        ("3\n1 1 1\n", False),  # 0
        ("8\n3 1 4 1 5 9 2 6\n", False),  # ?
    ]),
    ('EX_SO_KMERGE', sol_kmerge, [
        ("3\n3\n1 4 7\n3\n2 5 8\n3\n3 6 9\n", True),
        ("2\n2\n1 2\n3\n3 4 5\n", True),
        ("1\n3\n10 20 30\n", False),
        ("3\n1\n5\n1\n3\n1\n8\n", False),
        ("2\n4\n1 2 3 4\n0\n\n", False),
    ]),
    ('EX_SO_PARTITION', sol_partition, [
        ("5\n3 7 1 8 4\n", True),
        ("6\n2 8 7 1 3 5\n", True),
        ("1\n42\n", False),
        ("3\n1 2 3\n", False),
        ("4\n5 5 5 5\n", False),
        ("5\n1 2 3 4 5\n", False),
    ]),
    ('EX_SO_DUTCH', sol_dutch, [
        ("9\n2 0 2 1 1 0 0 1 2\n", True),
        ("5\n0 0 0 0 0\n", True),
        ("5\n2 2 2 2 2\n", False),
        ("6\n2 1 0 2 1 0\n", False),
        ("1\n1\n", False),
        ("4\n2 0 1 0\n", False),
    ]),
    ('EX_SO_RUNMEDIAN', sol_running_median, [
        ("5\n1 2 3 4 5\n", True),
        ("4\n4 1 3 2\n", True),
        ("1\n7\n", False),
        ("3\n1 1 1\n", False),
        ("6\n6 5 4 3 2 1\n", False),
    ]),
    ('EX_SO_COUNTING', sol_counting, [
        ("5 5\n3 1 4 1 5\n", True),
        ("6 9\n3 1 4 1 5 9\n", True),
        ("1 0\n0\n", False),
        ("4 3\n2 0 3 1\n", False),
        ("8 1\n0 1 0 1 1 0 1 0\n", False),
    ]),
    ('EX_SO_RADIX', sol_radix, [
        ("5\n170 45 75 90 802\n", True),
        ("4\n329 457 657 839\n", True),
        ("1\n42\n", False),
        ("6\n100 1 10 1000 10000 100000\n", False),
        ("5\n0 0 0 0 0\n", False),
    ]),
    ('EX_SO_RADIX_STR', sol_radix_strings, [
        ("4 3\nabc bca cab aaa\n", True),
        ("5 2\nbb aa bc ab cd\n", True),
        ("1 4\nabcd\n", False),
        ("3 1\nb a c\n", False),
        ("4 3\nzzz aaa zaz aza\n", False),
    ]),
    ('EX_SO_SELECT', sol_quickselect, [
        ("5 3\n3 1 4 1 5\n", True),
        ("7 5\n9 4 7 1 3 8 2\n", True),
        ("1 1\n42\n", False),
        ("5 5\n5 4 3 2 1\n", False),
        ("6 1\n3 6 1 2 5 4\n", False),
        ("8 4\n8 7 6 5 4 3 2 1\n", False),
    ]),
    ('EX_SO_MINMAX', sol_minmax, [
        ("5\n3 1 4 1 5\n", True),
        ("1\n42\n", True),
        ("4\n7 7 7 7\n", False),
        ("6\n-3 -1 -5 0 2 -2\n", False),
        ("3\n1000000000 -1000000000 0\n", False),
    ]),
    ('EX_SO_TOPK', sol_topk_sorted, [
        ("5 3\n5 4 3 2 1\n", True),
        ("8 4\n7 2 9 4 1 6 3 8\n", True),
        ("1 1\n42\n", False),
        ("4 1\n10 20 30 40\n", False),
        ("5 5\n3 1 4 1 5\n", False),
        ("6 2\n100 50 25 10 5 1\n", False),
    ]),
]


for key, fn, cases in CASES:
    print(f"=== {key} ===")
    for stdin, _ in cases:
        try:
            out = fn(stdin)
        except Exception as e:
            out = f"<EXCEPTION: {e}>"
        print(f"  in={stdin!r}")
        print(f"  out={out!r}")
