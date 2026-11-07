"""実際のゲームのコードで、矢印の床・番人の部屋を動かして確かめる。"""
import os, sys, random
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyxel
import main
import slide_search as S
from verify_shot import shot

random.seed(7)
g = main.Game()
g.new_game(0)
g.state = "play"
g.need_release = False

# ---------- 1) 矢印の床：4つの入口から、実際のtry_moveで宝箱のそばへ着けるか ----------
P, A = main.SLIDE_LAYOUTS[0]
Pset = {tuple(p) for p in P}
Aset = {tuple(k): tuple(v) for k, v in A}
ok_all = True
seen_flip = set()
for d, start in list(S.ENTR.items()) * 6:
    r = main.Room(5, 5)
    r.doors = {k: main.DOORS[k] for k in main.DOORS}
    r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
    r.kind = "gimmick"
    g.floor = 3
    g.setup_slide(r)
    g.rooms[(5, 5)] = r
    g.room = r
    # 実際に作られた部屋から、柱と矢印を読み取って検証する（上下反転も含めて確かめる）
    Pset = {(x, y) for y in range(1, main.RH - 1) for x in range(1, main.RW - 1) if r.tiles[y][x] == "#"}
    Aset = dict(r.arrows)
    seen_flip.add(Aset.get((2, 1)) is not None)
    g.p.x, g.p.y = start
    g.p.rx, g.p.ry = start[0] * main.TS, start[1] * main.TS
    # モデルで最短の動きを求める
    dist, par = S.bfs(Pset, Aset, start)
    G = S.goal_set(Pset)
    goal = min((dist[x], x) for x in G if x in dist)[1]
    seq = []
    cur = goal
    while par[cur][0] is not None:
        seq.append(cur)
        cur = par[cur][0]
    seq.reverse()
    pos = start
    for tgt in seq:
        # この目標へ行ける向きを探して、実際に動かす
        done = False
        for dx, dy in main.DIRS8:
            for (t, sl) in S.moves(Pset, Aset, pos):
                pass
            nx, ny = pos[0] + dx, pos[1] + dy
            if not S.passable(Pset, nx, ny):
                continue
            if dx and dy and (S.is_wall(Pset, pos[0] + dx, pos[1]) or S.is_wall(Pset, pos[0], pos[1] + dy)):
                continue
            if S.slide(Pset, Aset, nx, ny) != tgt:
                continue
            g.p.x, g.p.y = pos
            moved = g.try_move(dx, dy)
            assert moved, (d, pos, (dx, dy))
            assert (g.p.x, g.p.y) == tgt, (d, pos, (dx, dy), (g.p.x, g.p.y), tgt)
            pos = tgt
            done = True
            break
        assert done, (d, pos, tgt)
    # 宝箱を開けられるか（向きを変えてZ相当）
    cx, cy = main.CHEST if hasattr(main, "CHEST") else (10, 6)
    adj = max(abs(g.p.x - 10), abs(g.p.y - 6)) == 1
    print(f"入口{d}: {len(seq)}手で宝箱のとなりに到着:", adj)
    ok_all = ok_all and adj
    if d == "L":
        g.state = "play"
        g.draw()
        shot("slide_room")
assert ok_all
print("SLIDE_OK  反転あり/なし両方を確認:", sorted(seen_flip))

# ---------- 2) 番人の部屋 ----------
for fl in (3, 12, 25):
    r = main.Room(6, 6)
    r.doors = {k: main.DOORS[k] for k in main.DOORS}
    r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
    r.kind = "gimmick"
    g.floor = fl
    r.gtype = "guard"
    g.setup_guard(r)
    print(f"{fl}F 番人の数:", len(r.enemies), "全員眠っている:", all(e.sleep and e.guard for e in r.enemies),
          "場所:", [(e.x, e.y) for e in r.enemies])
    assert all(r.tiles[e.y][e.x] == "." for e in r.enemies)
g.floor = 3
r = main.Room(6, 6)
r.doors = {k: main.DOORS[k] for k in main.DOORS}
r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
r.kind = "gimmick"
g.setup_guard(r)
g.rooms[(6, 6)] = r
g.room = r
# 離れていれば起きない／となりだと起きる／1体起きると全員起きる
HOME = [(e.x, e.y) for e in r.enemies]


def reset_guards():
    for e, (x, y) in zip(r.enemies, HOME):
        e.x, e.y, e.sleep = x, y, True
        e.rx, e.ry = x * main.TS, y * main.TS
    g.p.hp = 40


g.p.x, g.p.y = 10, 2
woke = 0
for _ in range(200):
    reset_guards()
    g.enemies_act()
    woke += any(not e.sleep for e in r.enemies)
print("離れている(距離>=3)とき、200ターンで起きた回数:", woke)
assert woke == 0
g.p.x, g.p.y = 10, 5  # (9,5)の番人のとなり
cnt = 0
N = 2000
for _ in range(N):
    reset_guards()
    g.enemies_act()
    if any(not e.sleep for e in r.enemies):
        cnt += 1
        assert all(not e.sleep for e in r.enemies), "全員起きるはず"
print(f"となり合ったとき、1ターンで起きる割合: {cnt / N:.2f}  (期待値0.40)")
assert 0.33 < cnt / N < 0.47
g.p.x, g.p.y = 11, 5  # (11,5)は番人の位置ではない。2体のとき、安全なマスのはず
reset_guards()
near = [e for e in r.enemies if max(abs(e.x - 11), abs(e.y - 5)) <= 1]
print("2体のとき、(11,5)のとなりにいる番人:", len(near))
g.state = "play"
g.p.x, g.p.y = 10, 8
g.draw()
shot("guard_room")

# ---------- 3) 解説ページ（全カード） ----------
g.state = "info"
g.info_cache = None
pages = g.info_pages()
print("解説ページ数:", len(pages))
for i in range(len(pages)):
    g.info_page = i
    g.draw()
    shot(f"info3_{i + 1}")
print("ALL_OK")
