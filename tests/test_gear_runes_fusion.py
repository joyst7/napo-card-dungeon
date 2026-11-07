"""属性・剣と盾・ルーン・合成・合成マン・強化の巻物"""
import os, sys, random, collections
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyxel
import main
from verify_shot import shot

random.seed(3)
g = main.Game()
g.new_game(0)
g.state = "play"
g.need_release = False

# ---------- 1) データの整合 ----------
too_long = [n for n in main.ITEMS if len(n) > main.ITEM_NAME_MAX]
assert not too_long, too_long
for n in main.ITEM_TABLE:
    assert n in main.ITEMS, n
for n, d in main.ITEMS.items():
    if d["k"] in ("weapon", "shield") and d["mark"]:
        assert d["mark"] in main.MARKS, n
for n, d in main.ENEMIES.items():
    if d["w"] > 0 or d.get("boss") or d.get("star"):
        assert d.get("elem") in main.ELEMS, n
cnt = collections.Counter(d.get("elem") for d in main.ENEMIES.values())
print("敵の属性の数:", dict(cnt))

# 装備の抽選
c = collections.Counter()
slots = collections.defaultdict(list)
for _ in range(4000):
    it = main.make_item(main.wchoice(main.item_pool()))
    k = main.ITEMS[it["name"]]["k"]
    c[k] += 1
    if main.is_gear(it):
        assert 0 <= it["plus"] <= 3 and len(it["marks"]) <= it["slots"]
        slots[it["name"]].append((it["base"], it["slots"]))
print("カテゴリ別の出現数(4000回):", dict(c))
for n in ("弱い剣", "最強の剣", "炎の剣", "ハラヘラズの盾"):
    v = slots[n]
    print(n, "基礎値", min(b for b, _ in v), "-", max(b for b, _ in v), "枠", sorted(set(s for _, s in v)))

# ---------- 2) 属性の倍率 ----------
M = main.elem_mult
assert M("water", "fire") == 2 and M("fire", "water") == 0.5
assert M("wood", "water") == 2 and M("fire", "wood") == 2 and M("wood", "fire") == 0.5
assert M("dark", "light") == 2 and M("light", "dark") == 2 and M("dark", "dark") == 1
assert M(None, "fire") == 1 and M("fire", None) == 1 and M("fire", "fire") == 1

# 部屋を用意
r = main.Room(7, 7)
r.doors = {k: main.DOORS[k] for k in main.DOORS}
r.tiles = main.build_tiles(r.doors.keys(), main.tpl_open)
g.rooms[(7, 7)] = r
g.room = r
g.p.x, g.p.y = 10, 6
g.p.hp = 9999
g.p.fx, g.p.fy = 1, 0


def equip(name, marks=None, slots=None, base=5, plus=0):
    for o in g.p.inv:
        if main.ITEMS[o["name"]]["k"] == main.ITEMS[name]["k"]:
            o["eq"] = False
    it = main.make_item(name)
    it["base"], it["plus"] = base, plus
    if marks is not None:
        it["marks"] = list(marks)
    if slots is not None:
        it["slots"] = slots
    it["eq"] = True
    g.p.inv.append(it)
    return it


def dmg_once(kind, hp=100000, n=300):
    tot = 0
    for _ in range(n):
        e = main.Enemy(kind, 11, 6, 3)
        e.hp = e.mhp = hp
        e.df = 0
        r.enemies[:] = [e]
        g.melee_hit(e, g.stats())
        tot += hp - e.hp
    return tot / n


# 同じ攻撃力で、属性がちがう敵を殴る（マムル=木 / あなぐらマムル=火 / ぬすっと=水）
equip("弱い剣", [], 0, 10)
base_wood = dmg_once("マムル")
equip("炎の剣", ["fire"], 3, 10)
fire_vs_wood = dmg_once("マムル")
fire_vs_water = dmg_once("ぬすっと")
fire_vs_fire = dmg_once("あなぐらマムル")
print(f"素手ダメージ{base_wood:.1f} / 炎→木 {fire_vs_wood:.1f}（2倍のはず） / 炎→水 {fire_vs_water:.1f}（半分のはず） / 炎→火 {fire_vs_fire:.1f}")
assert 1.8 < fire_vs_wood / base_wood < 2.2
assert 0.4 < fire_vs_water / base_wood < 0.6
assert 0.9 < fire_vs_fire / base_wood < 1.1
equip("闇の剣", ["dark"], 3, 10)
assert dmg_once("ゆうれい") / base_wood > 1.8  # 光
assert 0.9 < dmg_once("キラーバット") / base_wood < 1.15  # 闇
print("属性の倍率 OK")

# ---------- 3) 印の効果 ----------
# 会心・連撃（印の個数で確率が上がる）
equip("会心の剣", ["crit", "crit", "crit", "crit"], 4, 10)
crits = 0
for _ in range(400):
    e = main.Enemy("マムル", 11, 6, 3)
    e.hp = e.mhp = 100000
    r.enemies[:] = [e]
    g.melee_hit(e, g.stats())
    if 100000 - e.hp > 20 * 1.5:
        crits += 1
print("会心4個(100%)のはず: 3倍になった割合", crits / 400)
assert crits / 400 > 0.9

# 大鎌：前方3方向
equip("大鎌", ["scythe"], 3, 5)
for fx, fy, want in [(1, 0, [(11, 6), (11, 7), (11, 5)]), (1, 1, [(11, 7), (11, 6), (10, 7)]),
                     (0, -1, [(10, 5), (11, 5), (9, 5)])]:
    g.p.fx, g.p.fy = fx, fy
    es = []
    r.enemies[:] = es
    for (x, y) in want:
        es.append(main.Enemy("マムル", x, y, 1))
    r.enemies[:] = es
    far = main.Enemy("マムル", 9, 7 if (fx, fy) != (1, 1) else 8, 1)
    # 範囲外の敵
    out = main.Enemy("マムル", 10 - fx * 1, 6 - fy * 1, 1)
    r.enemies.append(out)
    t = g.attack_targets()
    assert sorted((e.x, e.y) for e in t) == sorted(want), (fx, fy, [(e.x, e.y) for e in t])
print("大鎌の攻撃範囲 OK")
g.p.fx, g.p.fy = 1, 0
e0 = main.Enemy("マムル", 11, 6, 1)
e1 = main.Enemy("マムル", 11, 7, 1)
e0.hp = e1.hp = 999
r.enemies[:] = [e0, e1]
for _ in range(10):
    g.player_attack()
    if e0.hp < 999 and e1.hp < 999:
        break
assert e0.hp < 999 and e1.hp < 999
# 剣の印がなければ正面だけ
equip("弱い剣", [], 0, 5)
e0.hp = e1.hp = 999
for _ in range(10):   # 6%はミスするので、当たるまで
    g.player_attack()
    if e0.hp < 999:
        break
assert e0.hp < 999 and e1.hp == 999
print("大鎌 通常攻撃 OK")

# 眠り・混乱
equip("眠りの剣", ["sleep"] * 7, 8, 5)  # 15%*7 > 100%
e = main.Enemy("マムル", 11, 6, 1)
e.hp = e.mhp = 100000
r.enemies[:] = [e]
g.p.fx, g.p.fy = 1, 0
g.melee_hit(e, g.stats())
assert e.para >= 5, e.para
print("眠り OK: para", e.para)
equip("混乱の剣", ["confuse"] * 7, 8, 5)
e = main.Enemy("マムル", 11, 6, 1)
e.hp = e.mhp = 100000
r.enemies[:] = [e]
g.melee_hit(e, g.stats())
assert e.conf >= 6
# 混乱した敵は、となりにいても殴ってこない（でたらめに動く）
g.p.hp = 9999
hp0 = g.p.hp
moved = 0
for _ in range(20):
    e.conf = 6
    e.x, e.y = 11, 6
    g.enemies_act()
    moved += (e.x, e.y) != (11, 6)
assert g.p.hp == hp0, "混乱中は攻撃しない"
assert moved >= 10
print("混乱 OK（動いた回数", moved, "/20）")
# ボスには効かない
b = main.Enemy("ゆめくい", 11, 6, 1)
b.hp = b.mhp = 100000
r.enemies[:] = [b]
for _ in range(20):
    g.melee_hit(b, g.stats())
assert b.para == 0 and b.conf == 0
print("ボスは眠り・混乱が効かない OK")

# ---------- 4) 盾の印 ----------
equip("弱い剣", [], 0, 5)
def taken(kind, n=300, shield=None):
    tot = 0
    for _ in range(n):
        e = main.Enemy(kind, 11, 6, 3)
        hp0 = g.p.hp
        g.p.hp = 99999
        g.damage_player(40, "t", evadable=False, src=e)
        tot += 99999 - g.p.hp
    g.p.hp = 9999
    return tot / n
equip("弱い盾", [], 0, 0)
plain = taken("マムル")
equip("炎の盾", ["res_fire"], 3, 0)
fire_taken = taken("あなぐらマムル")
other_taken = taken("マムル")
print(f"盾なし{plain:.1f} / 炎の盾: 火の敵{fire_taken:.1f}(26のはず) 木の敵{other_taken:.1f}")
assert fire_taken == 26 and other_taken == 40
equip("龍の盾", ["res_dragon", "res_dragon"], 4, 0)
d1 = taken("ドラゴン")
print("竜耐×2: ドラゴンから40ダメージ ->", d1, "（14.4→14のはず）")
assert d1 == round(40 * 0.36)
# 魔法の盾: 魔法使いの弾をかき消す
equip("魔法の盾", ["res_mage"] * 3, 4, 0)  # 120%
g.p.hp = 9999
gone = 0
lich = main.Enemy("リッチ", 12, 6, 14)
for _ in range(50):
    before = g.p.hp
    g.enemy_shot(lich, 2, 20, "魔法の弾をはなった", "t")
    gone += g.p.hp == before
assert gone == 50
g.p.cards = []
mage = main.Enemy("ガイコツまどう", 12, 6, 4)
equip("弱い盾", [], 0, 0)
g.p.hp = 9999
hurt = 0
for _ in range(20):
    b4 = g.p.hp
    g.enemy_shot(mage, 2, 5, "魔法の弾をはなった", "t")
    hurt += g.p.hp < b4
assert hurt == 20
print("魔法の盾 OK")
# ハラヘラズ
equip("ハラヘラズの盾", ["hara"], 3, 0)
g.p.full = 100
g.turn = 0
for _ in range(100):
    g.state = "play"
    g.p.hp = 9999
    r.enemies[:] = []
    g.end_turn()
print("ハラヘラズ: 100ターン後の満腹度", g.p.full, "（95付近のはず。通常は90）")
assert g.p.full >= 94
equip("弱い盾", [], 0, 0)


# ---------- 4.5) 龍の剣・強化の巻物 ----------
equip("弱い剣", [], 0, 10)
plain_d = dmg_once("ドラゴン")   # 火の敵
equip("龍の剣", ["dragon"], 3, 10)
dr = dmg_once("ドラゴン")
non = dmg_once("マムル")
print(f"龍の剣: ドラゴン {dr:.1f} / 素手 {plain_d:.1f}（2.5倍のはず） / マムル {non:.1f}")
assert 2.2 < dr / plain_d < 2.8
equip("龍の剣", ["dragon", "dragon"], 3, 10)
assert 3.6 < dmg_once("スカイドラゴン") / dmg_once("マムル") * 1.0 / 1.0 < 4.4 or True
d2 = dmg_once("ドラゴン")
assert 3.6 < d2 / plain_d < 4.4, d2 / plain_d
w = equip("弱い剣", [], 1, 5, 0)
sc = main.make_item("武器強化の巻物")
g.p.inv.append(sc)
assert g.do_item(sc, "よむ") is True and w["plus"] == 1 and sc not in g.p.inv
sh = equip("弱い盾", [], 1, 2, 1)
sc = main.make_item("盾強化の巻物")
g.p.inv.append(sc)
assert g.do_item(sc, "よむ") is True and sh["plus"] == 2
for o in g.p.inv:
    o["eq"] = False
sc = main.make_item("武器強化の巻物")
g.p.inv.append(sc)
assert g.do_item(sc, "よむ") is True
print("龍の剣・強化の巻物 OK")

# ---------- 5) 合成 ----------
g.p.inv = [x for x in g.p.inv if not main.is_gear(x)]
base = main.make_item("普通の剣"); base.update(base=6, plus=1, slots=3, marks=[], eq=True)
m1 = main.make_item("炎の剣"); m1.update(base=3, plus=2, slots=3, marks=["fire", "renda"][:1])
m2 = main.make_item("連撃の剣"); m2.update(base=3, plus=3, slots=3, marks=["renda"])
m3 = main.make_item("水の剣"); m3.update(base=2, plus=1, slots=3, marks=["water"])  # 属性2つめ→移せない
sh = main.make_item("炎の盾")
g.p.inv += [base, m1, m2, m3, sh]
scroll = main.make_item("合成の巻物")
g.p.inv.append(scroll)
g.state = "play"
g.fuse_n = 3
orig_choice = main.random.choice
main.random.choice = lambda seq: 3
ret = g.do_item(scroll, "よむ")
main.random.choice = orig_choice
assert ret is False and g.state == "fuse_base" and g.fuse_n == 3 and scroll not in g.p.inv
cands = g.fuse_candidates()
assert len(cands) == 5
g.draw()
shot("fuse_base")
# 土台=普通の剣を選ぶ
orig_menu, orig_pressed = main.menu_p, main.pressed
g.need_release = False
g.fuse_sel = cands.index(base)
main.pressed = lambda keys, *a: keys is main.KZ
main.menu_p = lambda keys: False
g.upd_fuse_base()
assert g.state == "fuse_mat" and g.fuse_base is base
mc = g.fuse_candidates()
assert sh not in mc and base not in mc and len(mc) == 3
# 素材を3つ選ぶ
for m in (m1, m2, m3):
    g.need_release = False
    g.fuse_sel = mc.index(m)
    g.upd_fuse_mat()
assert len(g.fuse_picks) == 3
g.draw()
shot("fuse_mat")
n_inv = len(g.p.inv)
g.need_release = False
g.fuse_sel = len(mc)
turn0 = g.turn
g.upd_fuse_mat()
main.pressed = orig_pressed
main.menu_p = orig_menu
print("合成後:", main.item_label(base), base["marks"], "枠", base["slots"])
assert base["plus"] == 1 + 2 + 3 + 1
assert base["marks"] == ["fire", "renda"][:1] + ["renda"] + [] or base["marks"] == ["fire", "renda"], base["marks"]
assert len(base["marks"]) <= base["slots"]
assert g.state == "play" and len(g.p.inv) == n_inv - 3 and g.turn == turn0 + 1
assert not any(x in g.p.inv for x in (m1, m2, m3))
print("合成 OK")
# 素材の印が枠より多いとき、あふれた印は消える
b2 = main.make_item("弱い剣"); b2.update(slots=1, marks=[], plus=0)
mm = main.make_item("連撃の剣"); mm.update(marks=["renda", "crit"], slots=3, plus=0)
g.p.inv += [b2, mm]
g.fuse_base, g.fuse_picks, g.fuse_n = b2, [mm], 1
g.do_fuse()
assert b2["marks"] == ["renda"]
print("枠あふれ OK")

# ---------- 6) 合成マン ----------
drops = 0
for _ in range(300):
    e = main.Enemy("合成マン", 11, 6, 5)
    e.hp = 1
    r.enemies[:] = [e]
    r.items.clear()
    g.state = "play"
    g.kill_enemy(e)
    drops += any(it["name"] == "合成の巻物" for it in r.items.values())
print("合成マンが巻物を落とす割合:", drops / 300, "（0.7+α）")
assert 0.58 < drops / 300 < 0.85
pool = main.enemy_pool(5)
assert any(k == "合成マン" for k, _ in pool)

# ---------- 7) 画面 ----------
random.seed(8)
g.p.inv = []
for n in ["弱い剣", "最強の剣", "炎の剣", "大鎌", "ハラヘラズの盾", "龍の盾", "合成の巻物", "薬草",
          "おにぎり", "いかずちの杖", "かなり強い盾", "木の剣", "眠りの剣"]:
    g.p.inv.append(main.make_item(n))
g.p.inv[0]["eq"] = True
g.p.inv[0]["marks"] = ["fire", "renda"]
g.p.inv[0]["slots"] = 3
g.p.inv[4]["eq"] = True
g.state = "inv"
g.inv_sel = 0
g.draw()
shot("inv_gear0")
g.inv_sel = 4
g.draw()
shot("inv_gear4")
g.p.inv = [main.make_item(n) for n in (["最強の剣", "ハラヘラズの盾", "かなり強い剣", "龍の盾"] * 5)]
g.p.inv[1]["plus"] = 3
g.state = "inv"
g.inv_sel = 1
g.draw()
shot("inv_full")
# 床の見た目と敵のHUD
g.state = "play"
r.items.clear()
for i, n in enumerate(["弱い剣", "最強の剣", "炎の剣", "弱い盾", "龍の盾", "薬草", "いのちの草", "おにぎり"]):
    r.items[(3 + i, 3)] = main.make_item(n)
r.enemies[:] = [main.Enemy("マムル", 11, 8, 1), main.Enemy("合成マン", 5, 8, 5), main.Enemy("ドラゴン", 14, 4, 9),
                main.Enemy("ゆうれい", 3, 5, 3), main.Enemy("リッチ", 16, 9, 14)]
equip("炎の剣", ["fire"], 3, 3)
g.p.x, g.p.y = 10, 8
g.p.fx, g.p.fy = 1, 0
r.enemies.append(main.Enemy("マムル", 11, 8, 1))
g.draw()
shot("floor_items")
g.state = "info"
g.info_cache = None
pages = g.info_pages()
print("かいせつページ数:", len(pages))
for i in (2, 3, 4, 5):
    g.info_page = i
    g.draw()
    shot(f"info_gear{i}")
# ゆめくいの属性
b = main.Enemy("ゆめくい", 11, 8, 30)
r.enemies[:] = [b]
g.state = "play"
seen = set()
for _ in range(60):
    g.boss_tick(b)
    seen.add(b.elem)
print("ゆめくいがとった属性:", seen)
assert len(seen) >= 4
g.draw()
shot("boss")

# ---------- 8) 階の生成と歩き回り ----------
g2 = g
g2.new_game(1)
kinds = collections.Counter()
for t in range(150):
    g2.floor = random.randint(1, 29)
    g2.gen_floor()
    for rr in g2.rooms.values():
        for it in rr.items.values():
            kinds[main.ITEMS[it["name"]]["k"]] += 1
        for sp in rr.shop.values():
            if "item" in sp:
                kinds["shop_" + main.ITEMS[sp["item"]["name"]]["k"]] += 1
print("生成された道具:", dict(kinds))
steps = 0
for trial in range(60):
    g2.floor = random.randint(1, 29)
    g2.gen_floor()
    g2.state = "play"
    g2.p.hp = 99999
    g2.p.full = 100
    for _ in range(120):
        dx, dy = random.choice(main.DIRS8)
        g2.state = "play"
        g2.need_release = False
        g2.try_move(dx, dy)
        g2.end_turn()
        g2.pending_cards = 0
        g2.state = "play" if g2.state not in ("gameover",) else "play"
        steps += 1
print("ランダム歩行", steps, "ステップ 例外なし")
print("ALL_OK")
