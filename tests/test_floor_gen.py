"""ギミック部屋つきのフロア生成と、ランダム歩行"""
import os, sys, random, collections
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
import pyxel
import main

random.seed(11)
g = main.Game()
g.new_game(1)  # 30F版
cnt = collections.Counter()
bad = []
for trial in range(300):
    g.floor = random.randint(2, 29)
    g.gen_floor()
    gims = [r for r in g.rooms.values() if r.kind == "gimmick"]
    cnt["floors"] += 1
    cnt[f"gimmick_rooms_{len(gims)}"] += 1
    for r in gims:
        cnt[r.gtype] += 1
        if r.chest is None or r.tiles[r.chest[1]][r.chest[0]] != ".":
            bad.append(("chest", r.gtype))
        if r.gtype == "guard":
            if not r.enemies or not all(e.guard and e.sleep and r.tiles[e.y][e.x] == "." for e in r.enemies):
                bad.append(("guard", g.floor))
        if r.gtype == "slide":
            if not r.arrows or not all(r.tiles[y][x] == "." for (x, y) in r.arrows):
                bad.append(("slide", g.floor))
        if r.gtype != "guard" and r.enemies:
            bad.append(("enemies_in_non_guard", r.gtype))
print(dict(cnt))
print("問題:", bad[:5], len(bad))
assert not bad

# ランダムに動くボットで、ギミック部屋の中を歩き回って例外が出ないか確かめる
steps = 0
for trial in range(120):
    g.floor = random.randint(2, 29)
    g.gen_floor()
    gims = [r for r in g.rooms.values() if r.kind == "gimmick"]
    if not gims:
        continue
    r = random.choice(gims)
    g.room = r
    g.state = "play"
    g.p.hp = 9999
    g.p.full = 100
    d = random.choice(list(main.DOORS))
    g.p.x, g.p.y = main.DOOR_IN[d][0]
    for _ in range(150):
        dx, dy = random.choice(main.DIRS8)
        g.state = "play"
        g.need_release = False
        try:
            g.try_move(dx, dy)
            g.end_turn()
        except Exception as ex:
            print("例外:", r.gtype, repr(ex))
            raise
        steps += 1
        if g.room is not r:
            g.room = r
            g.p.x, g.p.y = main.DOOR_IN[d][0]
        g.state = "play"
        g.pending_cards = 0
print("ランダム歩行ステップ数:", steps)
print("ALL_OK")
