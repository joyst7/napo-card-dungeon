"""一方通行の床パズルの配置を探す。ゲーム本体と同じ規則で、解けるか・詰まらないかを全探索で確かめる。"""
import random, sys, json
from collections import deque

RW, RH = 20, 13
DOORS = {"L": (0, 6), "R": (RW - 1, 6), "U": (10, 0), "D": (10, RH - 1)}
DOOR_IN = {"L": [(1, 6), (2, 6)], "R": [(RW - 2, 6), (RW - 3, 6)],
           "U": [(10, 1), (10, 2)], "D": [(10, RH - 2), (10, RH - 3)]}
ENTR = {d: DOOR_IN[d][0] for d in DOORS}
CHEST = (10, 6)
DIRS8 = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
ORTH = [(0, -1), (1, 0), (0, 1), (-1, 0)]
DOORTILES = set(DOORS.values())
SLIDE_LIMIT = 16


def is_wall(P, x, y):
    return not (0 <= x < RW and 0 <= y < RH) or x in (0, RW - 1) or y in (0, RH - 1) or (x, y) in P


def passable(P, x, y):
    return (not is_wall(P, x, y)) and (x, y) != CHEST


def slide(P, A, x, y):
    n = 0
    while (x, y) in A and n < SLIDE_LIMIT:
        dx, dy = A[(x, y)]
        nx, ny = x + dx, y + dy
        if not passable(P, nx, ny):
            break
        x, y = nx, ny
        n += 1
    return x, y


def moves(P, A, s):
    x, y = s
    for dx, dy in DIRS8:
        nx, ny = x + dx, y + dy
        if not passable(P, nx, ny):
            continue
        if dx and dy and (is_wall(P, x + dx, y) or is_wall(P, x, y + dy)):
            continue
        fx, fy = slide(P, A, nx, ny)
        yield (fx, fy), ((fx, fy) != (nx, ny))


def goal_set(P):
    g = set()
    for dx, dy in DIRS8:
        x, y = CHEST[0] + dx, CHEST[1] + dy
        if not passable(P, x, y):
            continue
        if dx and dy and (is_wall(P, CHEST[0] + dx, CHEST[1]) or is_wall(P, CHEST[0], CHEST[1] + dy)):
            continue
        g.add((x, y))
    return g


def bfs(P, A, s0):
    dist = {s0: 0}
    par = {s0: (None, False)}
    q = deque([s0])
    while q:
        s = q.popleft()
        for t, sl in moves(P, A, s):
            if t not in dist:
                dist[t] = dist[s] + 1
                par[t] = (s, sl)
                q.append(t)
    return dist, par


def evaluate(P, A):
    G = goal_set(P)
    if not G:
        return -1, None
    # グラフを1回だけ作る
    states = [(x, y) for x in range(1, RW - 1) for y in range(1, RH - 1) if passable(P, x, y)]
    succ = {s: [] for s in states}
    pred = {s: [] for s in states}
    for s in states:
        for t, sl in moves(P, A, s):
            succ[s].append((t, sl))
            pred[t].append(s)
    best = 99
    slides_in_best = 99
    detour = 99
    plain = {s: [] for s in states}
    for s in states:
        for t, sl in moves(P, {}, s):
            plain[s].append(t)
    for d, s0 in ENTR.items():
        if s0 in P or s0 in A:
            return -1, None
        dist = {s0: 0}
        par = {s0: (None, False)}
        q = deque([s0])
        while q:
            s = q.popleft()
            for t, sl in succ[s]:
                if t not in dist:
                    dist[t] = dist[s] + 1
                    par[t] = (s, sl)
                    q.append(t)
        gs = [(dist[g], g) for g in G if g in dist]
        if not gs:
            return -1, None
        dg, g = min(gs)
        n = 0
        cur = g
        while par[cur][0] is not None:
            n += par[cur][1]
            cur = par[cur][0]
        # 矢印がただの床だった場合の最短手数
        pd = {s0: 0}
        q = deque([s0])
        while q:
            s = q.popleft()
            for t in plain[s]:
                if t not in pd:
                    pd[t] = pd[s] + 1
                    q.append(t)
        pdg = min(pd[g2] for g2 in G if g2 in pd)
        detour = min(detour, dg - pdg)
        best = min(best, dg)
        slides_in_best = min(slides_in_best, n)
        # 詰み防止：到達できる場所すべてから、この入口へ戻れること
        back = {s0}
        q = deque([s0])
        while q:
            s = q.popleft()
            for t in pred[s]:
                if t not in back:
                    back.add(t)
                    q.append(t)
        if not set(dist) <= back:
            return -1, None
    return best * 10 + max(0, detour) * 12, (best, detour)


def rand_layout(rng):
    free = [(x, y) for x in range(1, RW - 1) for y in range(1, RH - 1)
            if (x, y) != CHEST and (x, y) not in ENTR.values()
            and (x, y) not in sum(DOOR_IN.values(), [])]
    P = set(rng.sample(free, rng.randint(6, 12)))
    rest = [t for t in free if t not in P]
    A = {t: rng.choice(ORTH) for t in rng.sample(rest, rng.randint(6, 12))}
    return P, A, free


def mutate(P, A, free, rng):
    P, A = set(P), dict(A)
    t = rng.choice(free)
    r = rng.random()
    if r < 0.35:
        if t in P:
            P.discard(t)
        elif t not in A and len(P) < 18:
            P.add(t)
    elif r < 0.7:
        if t in A:
            del A[t]
        elif t not in P and len(A) < 16:
            A[t] = rng.choice(ORTH)
    else:
        if t in A:
            A[t] = rng.choice(ORTH)
    return P, A


def search(seed, iters=8000):
    rng = random.Random(seed)
    P, A, free = rand_layout(rng)
    sc, info = evaluate(P, A)
    tries = 0
    while sc < 0 and tries < 300:
        P, A, free = rand_layout(rng)
        sc, info = evaluate(P, A)
        tries += 1
    if sc < 0:
        return None
    for _ in range(iters):
        P2, A2 = mutate(P, A, free, rng)
        s2, i2 = evaluate(P2, A2)
        if s2 >= sc:
            P, A, sc, info = P2, A2, s2, i2
    return sc, info, sorted(P), sorted(A.items())


if __name__ == "__main__":
    seeds = range(int(sys.argv[1]), int(sys.argv[2]))
    out = []
    for sd in seeds:
        r = search(sd)
        if r:
            print(sd, r[0], r[1], flush=True)
            out.append(dict(seed=sd, score=r[0], info=r[1], P=r[2], A=[[list(k), list(v)] for k, v in r[3]]))
    json.dump(out, open(sys.argv[3], "w"))
