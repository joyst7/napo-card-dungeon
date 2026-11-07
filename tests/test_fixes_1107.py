"""修正値の表記・装備の比較・戻ったときの敵・盗む敵の逃走・ななつぼし"""
import os, sys, random
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyxel, main
from verify_shot import shot
random.seed(21)
g = main.Game(); g.new_game(1); g.state = "play"; g.need_release = False

# ---- 修正値の書き方 ----
it = main.make_item("普通の剣"); it.update(base=5, plus=0)
assert main.item_label(it) == "普通の剣", main.item_label(it)
it["plus"] = 2
assert main.item_label(it) == "普通の剣+2"
assert "攻撃力 7（基礎5 修正+2）" in main.item_desc(it), main.item_desc(it)
print("名前の横は修正値だけ OK:", main.item_label(it))

# ---- 強化・弱体の表示 ----
g.p.inv = []
cur = main.make_item("弱い剣"); cur.update(base=2, plus=0, eq=True)
up = main.make_item("強い剣"); up.update(base=8, plus=1)
dn = main.make_item("弱い剣"); dn.update(base=1, plus=0)
same = main.make_item("弱い剣"); same.update(base=2, plus=0)
g.p.inv += [cur, up, dn, same]
for o, want in ((up, "▲強化 +7"), (dn, "▼弱体 -1"), (same, "＝変わらない")):
    t, c = g.gear_diff(o)
    print(" ", main.item_label(o), "→", t)
    assert want in t
assert g.gear_diff(cur) is None
sh = main.make_item("弱い盾"); sh.update(base=3, plus=0)
t, c = g.gear_diff(sh)
assert "防御力 0→3" in t and "強化" in t, t   # 盾をそうびしていない
g.state = "inv"; g.inv_sel = 1
g.draw(); shot("inv_diff_up")
g.inv_sel = 2; g.draw(); shot("inv_diff_down")
g.state = "play"

# ---- 戻ったとき、追ってきた敵がすぐ出てくる ----
g.floor = 5
g.gen_floor(); g.state = "play"
g.p.hp = 99999
ok = 0; tried = 0
for gx in range(8):
    for gy in range(8):
        r = g.rooms.get((gx, gy))
        if not r or r.kind != "normal" or r.boss_room or r.locked:
            continue
        for d in r.doors:
            n = g.rooms.get((gx + main.DIR_VEC[d][0], gy + main.DIR_VEC[d][1]))
            if not n or n.kind not in ("normal",) or n.locked or n.boss_room:
                continue
            g.room = r
            r.enemies.clear(); n.enemies.clear(); r.pending.clear(); n.pending.clear()
            door = main.DOORS[d]
            # ドアの近くに、起きている敵を3歩はなして置く
            ex, ey = door[0] - main.DIR_VEC[d][0] * 4, door[1] - main.DIR_VEC[d][1] * 4
            if not g.passable(r, ex, ey):
                continue
            e = main.Enemy("マムル", ex, ey, 3)
            r.enemies.append(e)
            g.p.x, g.p.y = door
            before = len(r.enemies) + len(r.pending) + len(n.enemies) + len(n.pending)
            g.change_room(d)           # 出る
            g.state = "play"
            assert e not in r.enemies and any(pd[1] is e for pd in n.pending), "出ていくときは待機になる"
            g.change_room(main.OPP[d]) # すぐ戻る
            g.state = "play"
            tried += 1
            if e in r.enemies:
                ok += 1
            r.enemies = [x for x in r.enemies if x is not e]
            break
print(f"すぐ戻ったとき、敵がその場にいた: {ok}/{tried}")
assert tried >= 5 and ok == tried

# ---- 盗んだ敵は、部屋を出ていく ----
def find_room():
    for (gx, gy), r in g.rooms.items():
        if r.kind == "normal" and not r.boss_room and not r.locked:
            ex = [d for d in r.doors if g.rooms.get((gx + main.DIR_VEC[d][0], gy + main.DIR_VEC[d][1]))]
            if ex:
                return r, ex
    return None, None
escaped = 0; stuck = 0; N = 40
for t in range(N):
    g.floor = random.randint(3, 20)
    g.gen_floor(); g.state = "play"
    g.p.hp = 99999
    cands = []
    for (gx, gy), r in g.rooms.items():
        if r.kind == "normal" and not r.boss_room and not r.locked:
            ex = [d for d in r.doors if g.rooms.get((gx + main.DIR_VEC[d][0], gy + main.DIR_VEC[d][1]))]
            if ex:
                cands.append(r)
    if not cands:
        continue
    r = random.choice(cands)
    g.room = r
    r.enemies.clear(); r.pending.clear()
    pos = g.free_tile(r)
    p0 = g.free_tile(r)
    if not pos or not p0:
        continue
    g.p.x, g.p.y = p0
    th = main.Enemy("ぬすっと", pos[0], pos[1], 3)
    th.loot = 50
    r.enemies.append(th)
    gone = False
    for turn in range(80):
        g.enemies_act()
        g.p.hp = 99999
        if th not in r.enemies:
            gone = True
            break
    if gone:
        neighbor = [rr for rr in g.rooms.values() if th in rr.enemies]
        assert neighbor, "出ていったのに、どの部屋にもいない"
        escaped += 1
    else:
        stuck += 1
        print("  逃げられなかった: 位置", (th.x, th.y), "プレイヤー", (g.p.x, g.p.y), "ドア", list(r.doors))
print(f"盗んだ敵が部屋を出た: {escaped}/{N}（出られなかった {stuck}）")
assert escaped >= N * 0.9

# ---- ななつぼしは通常攻撃が効かない ----
g.floor = 5; g.gen_floor(); g.state = "play"
r = g.room
r.enemies.clear()
st_ = main.Enemy("ななつぼし", g.p.x + 1, g.p.y, 5)
r.enemies.append(st_)
g.p.fx, g.p.fy = 1, 0
hp0 = st_.hp
for _ in range(10):
    g.player_attack()
assert st_.hp == hp0
print("ななつぼし: 通常攻撃は効かない OK")

# ---- 画面（タイトル・階バナー） ----
g.state = "title"; g.title_sel = 0; g.frame = 0
g.draw(); shot("title_bright0")
g.title_sel = 1; g.frame = 30
g.draw(); shot("title_bright1")
g.new_game(1)
g.state = "play"
g.banner = 60
g.draw(); shot("banner")
print("ALL_OK")
