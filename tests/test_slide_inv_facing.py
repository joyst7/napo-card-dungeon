"""矢印の床の全配置・2列の持ち物欄・攻撃してきた敵を向く"""
import os, sys, random
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyxel
import main
import slide_search as S
from verify_shot import shot

random.seed(5)
g = main.Game()
g.new_game(0)
g.state = "play"
g.need_release = False

# ---------- 1) 全配置 × 上下反転 × 4入口 を、実際のtry_moveで解く ----------
orig_random = main.random.random
total = 0
for li, lay in enumerate(list(main.SLIDE_LAYOUTS)):
    for flip in (0.0, 0.99):
        main.SLIDE_LAYOUTS = [lay]
        for d, start in S.ENTR.items():
            r = main.Room(5, 5)
            r.doors = {k: main.DOORS[k] for k in main.DOORS}
            r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
            r.kind = "gimmick"
            g.floor = 3
            main.random.random = lambda v=flip: v
            try:
                g.setup_slide(r)
            finally:
                main.random.random = orig_random
            g.rooms[(5, 5)] = r
            g.room = r
            Pset = {(x, y) for y in range(1, main.RH - 1) for x in range(1, main.RW - 1) if r.tiles[y][x] == "#"}
            Aset = dict(r.arrows)
            sc, info = S.evaluate(Pset, Aset)
            assert sc >= 0, ("全探索で不合格", li, flip)
            dist, par = S.bfs(Pset, Aset, start)
            G = S.goal_set(Pset)
            goal = min((dist[x], x) for x in G if x in dist)[1]
            seq, cur = [], goal
            while par[cur][0] is not None:
                seq.append(cur)
                cur = par[cur][0]
            seq.reverse()
            pos = start
            g.p.x, g.p.y = start
            for tgt in seq:
                done = False
                for dx, dy in main.DIRS8:
                    nx, ny = pos[0] + dx, pos[1] + dy
                    if not S.passable(Pset, nx, ny):
                        continue
                    if dx and dy and (S.is_wall(Pset, pos[0] + dx, pos[1]) or S.is_wall(Pset, pos[0], pos[1] + dy)):
                        continue
                    if S.slide(Pset, Aset, nx, ny) != tgt:
                        continue
                    g.p.x, g.p.y = pos
                    assert g.try_move(dx, dy)
                    assert (g.p.x, g.p.y) == tgt
                    pos = tgt
                    done = True
                    break
                assert done
            assert max(abs(g.p.x - 10), abs(g.p.y - 6)) == 1
            total += 1
    print(f"配置{li + 1}: 上下反転あり/なし×4入口 すべて到達 (全探索の評価 {info})")
print("SLIDE_OK", total, "通り")

# ---------- 2) 持ち物20個：2列表示 ----------
names = [n for n in main.ITEMS if main.ITEMS[n]["k"] != "gold"]
longest = sorted(names, key=len, reverse=True)
g.p.inv = [main.make_item(longest[i % len(longest)]) for i in range(main.INV_MAX)]
g.p.inv[19] = main.make_item("いかずちの杖")
g.p.inv[0]["eq"] = True
g.state = "inv"
g.inv_sel = 0
g.draw()
shot("inv2_first")
# 左右キー相当の移動ロジック
g.need_release = False
orig_menu = main.menu_p
main.menu_p = lambda keys: keys is main.KR
g.upd_inv()
print("→キーで", 0, "→", g.inv_sel)
assert g.inv_sel == 10
main.menu_p = lambda keys: keys is main.KL
g.upd_inv()
print("←キーで 10 →", g.inv_sel)
assert g.inv_sel == 0
main.menu_p = orig_menu
g.inv_sel = 19
g.draw()
shot("inv2_last")
g.inv_sel = 13
g.act_sel = 0
g.state = "inv_act"
g.draw()
shot("inv2_act")
too_long = [n for n in main.ITEMS if len(n) > main.ITEM_NAME_MAX]
print("名前が上限を超えるアイテム:", too_long)
assert not too_long
widest = max(main.tw(main.item_label(main.make_item(n))) for n in names)
print("一番長い表示の幅:", widest, "px / 列に使える幅:", main.INV_COLW - 16)
assert widest <= main.INV_COLW - 16

# ---------- 3) 攻撃を受けたら、その敵の方向を向く ----------
g.state = "play"
g.p.hp = 9999
g.p.x, g.p.y = 10, 6
cases = {"右上": (11, 5), "左下": (9, 7), "真上": (10, 5), "遠い右(3マス)": (13, 6), "遠い左上(斜め3)": (7, 3)}
for name, (ex, ey) in cases.items():
    e = main.Enemy("マムル", ex, ey, 1)
    g.p.fx, g.p.fy = 0, 1  # わざと別の向きにしておく
    g.damage_player(3, "test", src=e)
    want = (main.sign(ex - 10), main.sign(ey - 6))
    print(f"{name}の敵に攻撃されたあとの向き:", (g.p.fx, g.p.fy), "期待:", want)
    assert (g.p.fx, g.p.fy) == want
# かわしたとき・ミスされたときも向く
g.p.cards = ["evade"] * 9
e = main.Enemy("マムル", 11, 7, 1)
g.p.fx, g.p.fy = -1, 0
g.damage_player(3, "test", src=e)
assert (g.p.fx, g.p.fy) == (1, 1), "かわしたときも向く"
g.p.cards = []
# 空腹ダメージ(攻撃者なし)では向きは変わらない
g.p.fx, g.p.fy = -1, 0
g.damage_player(1, "hunger", False)
assert (g.p.fx, g.p.fy) == (-1, 0)
# 実際の敵の近接攻撃（enemy_step）でも向くか（何もない部屋で試す）
r = main.Room(7, 7)
r.doors = {k: main.DOORS[k] for k in main.DOORS}
r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
g.rooms[(7, 7)] = r
g.room = r
g.p.x, g.p.y = 8, 6
g.p.rx, g.p.ry = 8 * main.TS, 6 * main.TS
e = main.Enemy("マムル", 9, 5, 1)
r.enemies.append(e)
turned = attacks = 0
for _ in range(60):
    e.x, e.y = 9, 5
    e.rx, e.ry = 9 * main.TS, 5 * main.TS
    g.p.fx, g.p.fy = 0, 1
    g.p.hp = 9999
    hp0 = g.p.hp
    g.enemies_act()
    if g.p.hp < hp0 or (g.p.fx, g.p.fy) != (0, 1):
        attacks += 1
        if (g.p.fx, g.p.fy) == (1, -1):
            turned += 1
print("斜めの敵が殴ってきた(またはミス)回数:", attacks, "うち右上を向いた:", turned)
assert attacks >= 40 and turned == attacks
print("ALL_OK")
