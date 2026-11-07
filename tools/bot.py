"""自動で遊ぶボット（バランス調整用）。

使い方:
    python3 tools/bot.py                 # 30F本番を100回
    python3 tools/bot.py 200 0           # 10F練習を200回
    python3 tools/bot.py 100 1 --seed 5  # 乱数の種を変える
    python3 tools/bot.py 100 1 --json out.json   # 集計をJSONにも保存

ボットは「ふつうに遊ぶ人」をまねる単純な作り。
- 部屋の敵は全部たおす。床の道具は拾う。部屋を一通り見てから階段へ（風の前には降りる）
- HPが減ったら草、おなかが減ったらおにぎり。強い剣・盾が出たら持ちかえる
- 強化の巻物はすぐ読む。合成の巻物は、そうび中の剣か盾に、修正値かルーンのある素材をまとめる
- わざ（魔法）はMPがあれば使う。カードは、強そうなものを選ぶ
- ショップでは、強化になる装備と、足りない草・おにぎりだけ買う
- ガチャがあれば、ギタンが続くかぎり回す（--no-gacha で回さない）
しないこと: 宝箱のパズル、杖の細かい使い分け、敵から逃げること。
- 杖・巻物・ドラゴン草は、強い敵や敵が多いときに使う
持ち物がいっぱいのときは、いちばんいらない物をその場で捨てる（ターンは使わない。測定のための簡略化）。
"""
import argparse
import collections
import json
import os
import random
import statistics
import sys
from collections import deque

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
import pyxel  # noqa: E402,F401
import main  # noqa: E402
from main import CARDS, DIRS8, DOORS, DIR_VEC, ITEMS, RH, RW, cheb, gear_val, is_gear, sign  # noqa: E402

# カードの好み（大きいほど先に取る）
CARD_SCORE = {
    "atk7": 30, "allup": 29, "soul": 27, "atk4": 25, "hp20": 22, "crit": 21, "def4": 20, "renda": 19,
    "spirit": 18, "drain": 17, "flare": 16, "skin": 15, "evade": 15, "magsword": 14, "thunder": 13,
    "atk2": 12, "hp10": 11, "heal": 11, "def2": 10, "counter": 10, "fire": 9, "medit": 8,
    "mag4": 7, "mp6": 7, "mag2": 5, "hara": 5, "hoshi": 4, "pierce": 4, "staffer": 3,
    "goldrush": 2, "warp": 2, "steal": 1,
    "i_herb": 12, "i_food": 6, "i_staff": 6, "i_gold": 4,
}
RUNE_WORTH = {"scythe": 3, "renda": 3, "crit": 3, "sleep": 2, "confuse": 2, "dragon": 1,
              "fire": 2, "water": 2, "wood": 2, "dark": 2, "light": 2,
              "res_fire": 1, "res_water": 1, "res_wood": 1, "res_dark": 1, "res_light": 1,
              "res_dragon": 1, "res_mage": 1, "hara": 2}


def gear_score(it):
    return gear_val(it) + sum(RUNE_WORTH.get(m, 1) for m in it["marks"])


class Bot:
    def __init__(self, g, gacha=True):
        self.g = g
        self.use_gacha = gacha
        self.reset()

    def reset(self):
        self.st = collections.Counter()
        self.floors = []          # 各階に着いた時点の記録
        self.last_pos = None
        self.still = 0
        self.picked = collections.Counter()

    # ------------------------------------------------------------ 道具
    def inv(self, name=None, kind=None):
        out = []
        for it in self.g.p.inv:
            if name and it["name"] != name:
                continue
            if kind and ITEMS[it["name"]]["k"] != kind:
                continue
            out.append(it)
        return out

    def keep_value(self, it):
        """持ち物を捨てるときの優先度（小さいものから捨てる）。"""
        d = ITEMS[it["name"]]
        k = d["k"]
        if is_gear(it):
            cur = self.equipped(k)
            if cur is None or gear_score(it) > gear_score(cur):
                return 70
            return 20 + (10 if (it["marks"] or it["plus"]) and self.inv("合成の巻物") else 0)
        same = len(self.inv(it["name"]))
        base = {"food": 100, "seed": 95, "herb": 85, "scroll": 60, "staff": 50, "dgrass": 45}.get(k, 30)
        if k == "staff":
            base = 20 + 10 * it["n"]
        if k == "scroll" and d["v"] in ("fuse", "wup", "sup"):
            base = 90
        return base - 8 * (same - 1)

    def equipped(self, kind):
        return next((o for o in self.g.p.inv if o["eq"] and ITEMS[o["name"]]["k"] == kind), None)

    def use(self, it, verb):
        g = self.g
        if g.do_item(it, verb):
            g.end_turn()
        return True

    def manage_items(self):
        """草・おにぎり・装備・巻物。行動したら True。"""
        g = self.g
        p = g.p
        st = g.stats()
        # 持ち物がいっぱいなら、いちばんいらない物を捨てる（測定用の簡略化）
        while len(p.inv) >= main.INV_MAX - 1:
            junk = [o for o in p.inv if not o["eq"]]
            if not junk:
                break
            g.remove_item(min(junk, key=self.keep_value))
            self.st["捨てた"] += 1
        # HP
        if p.hp <= st["mhp"] * 0.35:
            big = self.inv("弟切草")
            small = self.inv("薬草")
            if p.hp <= st["mhp"] * 0.2 and big:
                self.st["草を飲んだ"] += 1
                return self.use(big[0], "のむ")
            if small or big:
                self.st["草を飲んだ"] += 1
                return self.use((small or big)[0], "のむ")
            if "heal" in p.cards and p.mp >= CARDS["heal"]["fx"]["mp"]:
                return self.cast("heal")
        # おなか
        if p.full <= 12:
            food = self.inv(kind="food")
            if food:
                self.st["食べた"] += 1
                return self.use(min(food, key=lambda o: ITEMS[o["name"]]["v"]), "たべる")
        # たね
        for it in self.inv(kind="seed"):
            return self.use(it, "のむ")
        # 装備の持ちかえ
        for kind in ("weapon", "shield"):
            cur = self.equipped(kind)
            cands = self.inv(kind=kind)
            if not cands:
                continue
            best = max(cands, key=gear_score)
            if best is not cur and (cur is None or gear_score(best) > gear_score(cur)):
                self.st["持ちかえ"] += 1
                return self.use(best, "そうび")
        # 強化の巻物
        for name, kind in (("武器強化の巻物", "weapon"), ("盾強化の巻物", "shield")):
            sc = self.inv(name)
            if sc and self.equipped(kind):
                self.st["強化した"] += 1
                return self.use(sc[0], "よむ")
        # 合成の巻物
        sc = self.inv("合成の巻物")
        if sc:
            for kind in ("weapon", "shield"):
                base = self.equipped(kind)
                if not base:
                    continue
                mats = [o for o in self.inv(kind=kind) if o is not base and (o["plus"] > 0 or o["marks"])]
                if mats:
                    g.do_item(sc[0], "よむ")
                    if g.state != "fuse_base":
                        return True
                    mats.sort(key=lambda o: o["plus"] + 3 * len(o["marks"]), reverse=True)
                    g.fuse_base = base
                    g.fuse_picks = mats[:g.fuse_n]
                    g.do_fuse()
                    self.st["合成した"] += 1
                    return True
        return False

    # ------------------------------------------------------------ わざ
    def cast(self, cid):
        g = self.g
        g.p.mp -= CARDS[cid]["fx"]["mp"]
        g.use_skill(cid)
        g.end_turn()
        self.st["わざ"] += 1
        return True

    def try_tools(self, e, foes):
        """杖・巻物・ドラゴン草。強い敵や、敵が多いときに使う。"""
        g = self.g
        p = g.p
        st = g.stats()
        melee = max(1, st["atk"] - e.df)
        if len(foes) >= 3:
            sc = [o for o in self.inv("真空斬りの巻物")]
            if sc:
                self.st["道具で攻撃"] += 1
                return self.use(sc[0], "よむ")
        tough = e.hp > melee * 2 or e.boss
        if tough:
            for name in ("いかずちの杖",):
                st_ = [o for o in self.inv(name) if o["n"] > 0]
                if st_:
                    self.st["道具で攻撃"] += 1
                    return self.use(st_[0], "ふる")
            dg = self.inv("ドラゴン草")
            if dg:
                self.st["道具で攻撃"] += 1
                return self.use(dg[0], "のむ")
        if p.hp < st["mhp"] * 0.5 and tough:
            for name in ("かなしばりの杖", "ふきとばしの杖"):
                st_ = [o for o in self.inv(name) if o["n"] > 0]
                if st_ and not e.boss:
                    self.st["道具で守る"] += 1
                    return self.use(st_[0], "ふる")
        return False

    def try_skills(self, e, foes):
        g = self.g
        p = g.p
        mp = p.mp
        has = lambda c: c in p.cards and mp >= CARDS[c]["fx"]["mp"]  # noqa: E731
        if e.star and has("hoshi"):
            return self.cast("hoshi")
        if len(foes) >= 2 and has("flare"):
            return self.cast("flare")
        if len(foes) >= 3 and has("thunder"):
            return self.cast("thunder")
        st = g.stats()
        melee = max(1, st["atk"] - e.df)
        if has("fire") and e.hp > melee * 2 and st["mag"] * 2 + 4 > melee:
            return self.cast("fire")
        return False

    # ------------------------------------------------------------ 移動
    def blocked(self, r):
        b = set(r.shop.keys()) | set(r.arrows.keys())
        for e in r.enemies:
            b.add((e.x, e.y))
        return b

    def path_step(self, goals, adjacent=False):
        """プレイヤーから goals（マスの集合）へ向かう最初の一歩。adjacent=Trueなら goals のとなりで止まる。"""
        g = self.g
        r = g.room
        p = g.p
        blk = self.blocked(r)
        start = (p.x, p.y)
        if adjacent:
            if any(cheb(p.x, p.y, gx, gy) == 1 and g.diag_ok(r, p.x, p.y, gx - p.x, gy - p.y) for gx, gy in goals):
                return None
        elif start in goals:
            return None
        prev = {start: None}
        q = deque([start])
        hit = None
        while q:
            cur = q.popleft()
            x, y = cur
            done = (any(cheb(x, y, gx, gy) == 1 and g.diag_ok(r, x, y, gx - x, gy - y) for gx, gy in goals)
                    if adjacent else cur in goals)
            if done and cur != start:
                hit = cur
                break
            for dx, dy in DIRS8:
                nx, ny = x + dx, y + dy
                if (nx, ny) in prev or not g.can_step(r, x, y, dx, dy):
                    continue
                if (nx, ny) in blk and (nx, ny) not in goals:
                    continue
                if (nx, ny) in blk and adjacent:
                    continue
                prev[(nx, ny)] = cur
                q.append((nx, ny))
        if not hit:
            return False
        while prev[hit] != start:
            hit = prev[hit]
        return (hit[0] - p.x, hit[1] - p.y)

    def step(self, d):
        g = self.g
        if d and g.try_move(*d):
            g.slide = None
            if g.state == "play":
                g.end_turn()
            return True
        return False

    def room_route(self, goal_fn):
        """部屋のつながりをたどって、goal_fn(部屋)を満たす一番近い部屋へ向かう最初の扉。"""
        g = self.g
        start = g.room
        prev = {(start.gx, start.gy): None}
        q = deque([start])
        while q:
            r = q.popleft()
            if r is not start and goal_fn(r):
                key = (r.gx, r.gy)
                while prev[key][0] != (start.gx, start.gy):
                    key = prev[key][0]
                return prev[key][1]
            for d in r.doors:
                if d in r.oneway_block:
                    continue
                nk = (r.gx + DIR_VEC[d][0], r.gy + DIR_VEC[d][1])
                if nk in g.rooms and nk not in prev:
                    prev[nk] = ((r.gx, r.gy), d)
                    q.append(g.rooms[nk])
        return None

    def go_door(self, d):
        g = self.g
        p = g.p
        r = g.room
        if r.locked:
            return False
        door = DOORS[d]
        if (p.x, p.y) == door:
            dx, dy = DIR_VEC[d]
            return self.step((dx, dy))
        s = self.path_step({door})
        if s:
            return self.step(s)
        return False

    # ------------------------------------------------------------ 1手
    def handle_state(self):
        g = self.g
        s = g.state
        if s == "card_intro":
            g.open_cards(g.ci_ids, g.ci_src)
        elif s == "cards":
            ids = g.cp_ids
            cid = max(ids, key=lambda c: CARD_SCORE.get(c, 0))
            if g.cp_src == "shop":
                g.shop_pending = None
                g.after_cards()
                return
            self.take_or_skip(cid)
            g.after_cards()
        elif s == "shop_buy":
            self.shop()
            g.state = "play"
        elif s == "stairs":
            if g.floor >= g.last:
                g.state = "clear"
            else:
                g.state = "play"
                g.next_floor()
                self.on_floor()
        elif s == "discard":
            g.after_cards()
        else:
            g.state = "play"

    def take_or_skip(self, cid):
        """カードを1枚もらうか見送るか（いっぱいなら、いちばん弱いカードと入れかえる）。"""
        g = self.g
        c = CARDS[cid]
        if c["t"] == "item" or len(g.p.cards) < main.CARD_MAX:
            g.take_card(cid)
            self.st["カード"] += 1
            return
        worst = min(range(len(g.p.cards)), key=lambda i: CARD_SCORE.get(g.p.cards[i], 0))
        if CARD_SCORE.get(cid, 0) > CARD_SCORE.get(g.p.cards[worst], 0):
            g.p.cards.pop(worst)
            g.take_card(cid)
            self.st["カード入れかえ"] += 1

    def spin_gacha(self):
        """ガチャを、ギタンが続くかぎり回す（人間がやりそうなこと）。"""
        g = self.g
        p = g.p
        cost = main.gacha_cost(g.floor)
        while p.gold >= cost and g.room.gacha_left > 0:
            p.gold -= cost
            g.room.gacha_left -= 1
            self.st["ガチャ"] += 1
            if random.random() < 0.15:
                pool = ["弟切草", "大きなおにぎり", "ドラゴン草", "いのちの草", "ちからの草"] + main.RARE_GEAR
                it = main.make_item(random.choice(pool))
                if not g.add_item(it):
                    break
            else:
                self.take_or_skip(g.draw_cards(1, g.gacha_rates(), True)[0])
            g.clamp_player()
        g.room.bot_gacha_done = True

    def want_buy(self, it, price):
        g = self.g
        if g.p.gold < price or len(g.p.inv) >= main.INV_MAX - 2:
            return False
        k = ITEMS[it["name"]]["k"]
        if is_gear(it):
            cur = self.equipped(k)
            return cur is None or gear_score(it) > gear_score(cur) + 2
        if k == "herb":
            return len(self.inv(kind="herb")) < 3
        if k == "food":
            return len(self.inv(kind="food")) < 2
        return False

    def shop(self):
        g = self.g
        r = g.room
        sp = r.shop.get(g.shop_pos)
        if sp and "item" in sp and self.want_buy(sp["item"], sp["price"]):
            g.p.gold -= sp["price"]
            g.add_item(sp["item"])
            r.shop.pop(g.shop_pos)
            self.st["買った"] += 1

    def on_floor(self):
        g = self.g
        p = g.p
        st = g.stats()
        w = self.equipped("weapon")
        s = self.equipped("shield")
        self.floors.append(dict(
            floor=g.floor, turn=g.turn, hp=p.hp, mhp=st["mhp"], atk=st["atk"], df=st["df"],
            wval=gear_val(w) if w else 0, sval=gear_val(s) if s else 0,
            wrunes=len(w["marks"]) if w else 0, srunes=len(s["marks"]) if s else 0,
            food=len(self.inv(kind="food")), herb=len(self.inv(kind="herb")), full=p.full,
            gold=p.gold, cards=len(p.cards), mp=p.mp, mmp=st["mmp"]))

    def act(self):
        g = self.g
        p = g.p
        r = g.room
        if p.full <= 0:
            self.st["空腹ダメージのターン"] += 1
        if self.manage_items():
            return
        foes = [e for e in r.enemies if not (e.star and "hoshi" not in p.cards)]
        # となりの敵をなぐる（または、わざ）
        adj = [e for e in foes if cheb(e.x, e.y, p.x, p.y) == 1 and g.diag_ok(r, p.x, p.y, e.x - p.x, e.y - p.y)]
        if adj:
            e = min(adj, key=lambda e: e.hp)
            p.fx, p.fy = sign(e.x - p.x), sign(e.y - p.y)
            if self.try_skills(e, foes) or self.try_tools(e, foes):
                return
            g.player_attack()
            g.end_turn()
            return
        # 部屋の敵へ近づく
        if foes:
            s = self.path_step({(e.x, e.y) for e in foes}, adjacent=True)
            if s and self.step(s):
                return
        # 道具を拾う（ショップの品は、買いたいものだけ）
        if len(p.inv) < main.INV_MAX - 1:
            goals = set(r.items.keys())
            for pos, sp in r.shop.items():
                if "item" in sp and self.want_buy(sp["item"], sp["price"]):
                    goals.add(pos)
            if goals:
                s = self.path_step(goals)
                if s and self.step(s):
                    return
        else:
            goals = {pos for pos in r.items if r.items[pos]["name"] == "ギタン"}
            if goals:
                s = self.path_step(goals)
                if s and self.step(s):
                    return
        # ガチャ
        if (self.use_gacha and r.gacha and not getattr(r, "bot_gacha_done", False)
                and p.gold >= main.gacha_cost(g.floor)):
            if cheb(p.x, p.y, *r.gacha) == 1 and g.diag_ok(r, p.x, p.y, r.gacha[0] - p.x, r.gacha[1] - p.y):
                self.spin_gacha()
                return
            s = self.path_step({r.gacha}, adjacent=True)
            if s and self.step(s):
                return
        # 階段（部屋を見終えたか、風が近い）
        # 風が近いとき、たおせない「ななつぼし」がいるときは、先へ進む
        stars = any(e.star for e in r.enemies) and "hoshi" not in p.cards
        rush = g.fturn > main.FLOOR_TURN_LIMIT - 200 or stars
        unvisited = self.room_route(lambda rr: not rr.visited)
        if r.stairs and (rush or unvisited is None):
            if (p.x, p.y) == r.stairs:
                g.state = "stairs"
                return
            s = self.path_step({r.stairs})
            if s and self.step(s):
                return
        # 次の部屋へ
        d = None if rush else unvisited
        if d is None:
            d = self.room_route(lambda rr: rr.stairs is not None or rr.boss_room)
        if d and self.go_door(d):
            return
        # どうにもならないとき
        self.st["うろうろ"] += 1
        dirs = list(DIRS8)
        random.shuffle(dirs)
        for dd in dirs:
            if self.step(dd):
                return
        g.end_turn()


def run(n, dg, seed=1, gacha=True):
    random.seed(seed)
    g = main.Game()
    bot = Bot(g, gacha)
    results = []
    for i in range(n):
        g.new_game(dg)
        bot.reset()
        bot.on_floor()
        guard = 0
        while g.state not in ("gameover", "clear") and guard < 60000:
            guard += 1
            if g.state != "play":
                bot.handle_state()
                continue
            g.slide = None
            bot.act()
        results.append(dict(
            clear=g.state == "clear", floor=g.floor, cause=g.cause if g.state == "gameover" else "クリア",
            turns=g.turn, kills=g.kills, cards=len(g.p.cards), floors=bot.floors, stats=dict(bot.st),
            stuck=guard >= 60000))
    return results


def summarize(res, last):
    n = len(res)
    out = collections.OrderedDict()
    out["回数"] = n
    out["クリア率"] = f"{100 * sum(r['clear'] for r in res) / n:.0f}%"
    fl = [r["floor"] for r in res]
    out["到達階 (中央値/平均)"] = f"{statistics.median(fl):.0f} / {statistics.mean(fl):.1f}"
    reach = {f: sum(1 for x in fl if x >= f) for f in range(1, last + 1)}
    out["その階まで行けた割合"] = " ".join(f"{f}F:{100 * reach[f] / n:.0f}%" for f in range(1, last + 1, max(1, last // 10)))
    causes = collections.Counter(r["cause"] for r in res)
    out["終わり方"] = ", ".join(f"{k} {v}" for k, v in causes.most_common(6))
    tpf = [r["turns"] / max(1, r["floor"]) for r in res]
    out["1フロアの平均ターン"] = f"{statistics.mean(tpf):.0f}"
    tot = collections.Counter()
    for r in res:
        tot.update(r["stats"])
    out["1回あたり"] = ", ".join(f"{k} {v / n:.1f}" for k, v in sorted(tot.items()))
    # 階ごとの平均（着いた時点）
    rows = collections.defaultdict(list)
    for r in res:
        for f in r["floors"]:
            rows[f["floor"]].append(f)
    table = []
    for f in sorted(rows):
        if f not in (1, 2, 3, 5, 8, 10, 13, 15, 18, 20, 23, 25, 28, 30):
            continue
        a = rows[f]
        m = lambda k: statistics.mean(x[k] for x in a)  # noqa: E731
        table.append(f"{f:>2}F n={len(a):>3}  HP{m('hp'):5.0f}/{m('mhp'):<4.0f} 攻{m('atk'):5.1f} 防{m('df'):5.1f}"
                     f"  剣{m('wval'):4.1f}(ルーン{m('wrunes'):.1f}) 盾{m('sval'):4.1f}(ルーン{m('srunes'):.1f})"
                     f"  草{m('herb'):.1f} 食{m('food'):.1f} 満腹{m('full'):3.0f} カード{m('cards'):.1f}"
                     f" MP{m('mmp'):.0f} {m('gold'):.0f}G")
    out["階ごと（着いた時点の平均）"] = table
    out["止まってしまった回数"] = sum(r["stuck"] for r in res)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("n", nargs="?", type=int, default=100)
    ap.add_argument("dg", nargs="?", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--json")
    ap.add_argument("--no-gacha", action="store_true")
    a = ap.parse_args()
    res = run(a.n, a.dg, a.seed, not a.no_gacha)
    s = summarize(res, main.DUNGEONS[a.dg]["last"])
    for k, v in s.items():
        if isinstance(v, list):
            print(k)
            for line in v:
                print("  " + line)
        else:
            print(f"{k}: {v}")
    if a.json:
        json.dump(dict(summary=s, runs=res), open(a.json, "w"), ensure_ascii=False, indent=1)
