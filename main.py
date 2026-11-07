# -*- coding: utf-8 -*-
# ナポのカードダンジョン（仮）  プロトタイプ3  10F練習 / 30F本番
# Pyxel製 画面切り替え式ターン制ローグライク
import os
import random
from collections import deque

import pyxel

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------
W, H = 320, 272
TS = 16
RW, RH = 20, 13            # 1部屋(=1画面)のマス数
HUD_H = 24
ROOM_Y = HUD_H
LOG_Y = HUD_H + RH * TS    # 232
GW, GH = 4, 3              # フロアの部屋グリッド
LAST_FLOOR = 10

DUNGEONS = [
    dict(name="はじまりの10F", last=10, star=7, guards=[3, 6, 9], mids=[], items={},
         desc=["練習用。走りぬけてもクリアできる", "まずはここでカードと敵になれよう"]),
    dict(name="ゆめくいの試練", last=30, star=17, guards=[5, 15, 25], mids=[10, 20], items={},
         desc=["本番。30Fの奥のゆめくいをたおせ", "ショップ・モンスターハウスあり"]),
]
FLOOR_TURN_LIMIT = 600     # 1フロアに居られるターン数
INV_MAX = 20
INV_ROWS = 12              # もちもの画面で一度に見せる行数（超えたらスクロール）
CARD_MAX = 10
SLIDE_FRAMES = 8

DOORS = {"L": (0, 6), "R": (RW - 1, 6), "U": (10, 0), "D": (10, RH - 1)}
DOOR_IN = {"L": [(1, 6), (2, 6)], "R": [(RW - 2, 6), (RW - 3, 6)],
           "U": [(10, 1), (10, 2)], "D": [(10, RH - 2), (10, RH - 3)]}
DIR_VEC = {"L": (-1, 0), "R": (1, 0), "U": (0, -1), "D": (0, 1)}
OPP = {"L": "R", "R": "L", "U": "D", "D": "U"}
DIRS8 = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]

FONT = None


def gacha_cost(f):
    return 40 + f * 10


# ---------------------------------------------------------------------------
# カード
# ---------------------------------------------------------------------------
def C(name, r, t, fx, desc, g=False, w=1.0):
    return dict(name=name, r=r, t=t, fx=fx, desc=desc, g=g, w=w)


CARDS = {
    # ---- ★ ----
    "atk2": C("ちから+2", 1, "stat", {"atk": 2}, "攻撃力が2上がる"),
    "def2": C("まもり+2", 1, "stat", {"def": 2}, "防御力が2上がる"),
    "hp10": C("たいりょく+10", 1, "stat", {"mhp": 10}, "最大HPが10上がる"),
    "mag2": C("まりょく+2", 1, "stat", {"mag": 2}, "魔力が2上がる。魔法の威力と回復量がのびる"),
    "mp6": C("MPタンク", 1, "stat", {"mmp": 6}, "最大MPが6上がる"),
    "fire": C("ファイア", 1, "skill", {"mp": 3}, "前方へ火の玉。魔法ダメージ（魔力×2+4）"),
    "heal": C("ヒール", 1, "skill", {"mp": 4}, "HPを回復する（魔力×3+12）"),
    "hara": C("はらもち", 1, "passive", {}, "満腹度の減りが半分になる"),
    "i_staff": C("つえ箱", 1, "item", {"give": "いかずちの杖", "n": 1}, "いかずちの杖をもらう。カード枠は使わない"),
    "i_food": C("おべんとう", 1, "item", {"give": "大きなおにぎり", "n": 1}, "大きなおにぎりをもらう。カード枠は使わない"),
    "i_gold": C("おこづかい", 1, "item", {"gold": 80}, "80ギタンもらう。カード枠は使わない"),
    # ---- ★★ ----
    "atk4": C("ちから+4", 2, "stat", {"atk": 4}, "攻撃力が4上がる"),
    "def4": C("まもり+4", 2, "stat", {"def": 4}, "防御力が4上がる"),
    "hp20": C("たいりょく+20", 2, "stat", {"mhp": 20}, "最大HPが20上がる"),
    "mag4": C("まりょく+4", 2, "stat", {"mag": 4}, "魔力が4上がる"),
    "thunder": C("サンダー", 2, "skill", {"mp": 7}, "部屋の敵すべてに魔法ダメージ（魔力+6）"),
    "pierce": C("つらぬき", 2, "skill", {"mp": 3}, "前方2マスを貫く物理攻撃（攻撃力×1.3）"),
    "steal": C("ぬすむ", 2, "skill", {"mp": 2}, "前の敵から道具を盗む（成功率60%）"),
    "warp": C("ワープ", 2, "skill", {"mp": 4}, "部屋の中の、敵から遠い場所へ飛ぶ"),
    "hoshi": C("ほしくだき", 2, "skill", {"mp": 4},
               "前の敵に耐性むしの一撃（攻撃力ぶん）。ななつぼしには4倍"),
    "renda": C("れんげき", 2, "passive", {}, "通常攻撃が30%で2回攻撃になる"),
    "drain": C("きゅうけつ", 2, "passive", {}, "物理ダメージの25%ぶんHPを吸い取る"),
    "skin": C("かたいひふ", 2, "passive", {}, "受けるダメージがいつも2へる"),
    "counter": C("はんげき", 2, "passive", {}, "なぐられた時30%で同じダメージを返す（物理）"),
    "evade": C("みかわし", 2, "passive", {}, "敵の攻撃を12%でかわす"),
    "staffer": C("つえの名手", 2, "passive", {}, "杖と巻物のダメージが1.5倍になる"),
    "goldrush": C("ゴールドラッシュ", 2, "passive", {}, "拾うギタンが2倍になる"),
    "medit": C("めいそう", 2, "passive", {}, "MPの自然回復が3倍になる"),
    "i_herb": C("くすりばこ", 2, "item", {"give": "弟切草", "n": 2}, "弟切草を2つもらう。カード枠は使わない"),
    # ---- ★★★ ----
    "atk7": C("ちから+7", 3, "stat", {"atk": 7}, "攻撃力が7上がる"),
    "allup": C("オールアップ", 3, "stat", {"atk": 3, "def": 3, "mag": 3, "mhp": 10},
               "攻撃・防御・魔力+3 最大HP+10"),
    "flare": C("ギガフレア", 3, "skill", {"mp": 12}, "部屋の敵すべてに大魔法（魔力×2+16）"),
    "crit": C("かいしん", 3, "passive", {}, "通常攻撃が25%で会心（3倍）になる"),
    "magsword": C("まほうけん", 3, "passive", {},
                  "通常攻撃に魔力ぶんの魔法ダメージが乗る。物理が効かない敵にも届く", g=True),
    "spirit": C("せいれいのかご", 3, "passive", {}, "HPとMPの自然回復がとても速くなる", g=True),
    "soul": C("ふたつめのいのち", 3, "passive", {}, "倒れた時1度だけHP半分で復活。使うと消える", g=True),
}
RARITY_COL = {1: 13, 2: 12, 3: 10}
TYPE_LABEL = {"stat": ("ステータス", 9), "skill": ("わざ", 8), "passive": ("パッシブ", 11),
              "item": ("どうぐ", 3)}
TYPE_GLYPH = {"stat": "力", "skill": "技", "passive": "常", "item": "袋"}


# ---------------------------------------------------------------------------
# 敵
# ---------------------------------------------------------------------------
def E(hp, atk, df=0, phys=True, mag=True, spr="", fmin=1, fmax=10, w=10, **kw):
    d = dict(hp=hp, atk=atk, df=df, phys=phys, mag=mag, spr=spr, fmin=fmin, fmax=fmax, w=w)
    d.update(kw)
    return d


ENEMIES = {
    # ---- 1〜10F ----
    "マムル": E(9, 3, spr="mamuru", fmin=1, fmax=4, w=30),
    "キラーバット": E(7, 3, spr="bat", fmin=1, fmax=6, w=18, acts=2, erratic=0.3),
    "ゆうれい": E(12, 4, phys=False, spr="ghost", fmin=2, fmax=7, w=14),
    "アイアンヘッド": E(18, 5, 2, mag=False, spr="iron", fmin=3, fmax=8, w=14),
    "ぬすっと": E(13, 3, spr="thief", fmin=3, fmax=9, w=8, ai="thief"),
    "ガイコツまどう": E(14, 4, spr="skull", fmin=4, fmax=11, w=12, ai="ranged"),
    "こうらがめ": E(11, 5, phys=False, mag=False, spr="turtle", fmin=4, fmax=10, w=6),
    "ぼうれい武者": E(26, 8, phys=False, spr="musha", fmin=6, fmax=13, w=9),
    "はがねゴーレム": E(42, 10, 4, mag=False, spr="golem", fmin=7, fmax=15, w=12, slow=True),
    "ドラゴン": E(45, 11, 1, spr="dragon", fmin=8, fmax=16, w=10, ai="breath"),
    # ---- 11〜20F（上位種は色ちがい） ----
    "あなぐらマムル": E(34, 13, 2, spr="mamuru", fmin=11, fmax=16, w=24, pal={9: 4, 14: 8}),
    "ブラッドバット": E(26, 11, spr="bat", fmin=11, fmax=19, w=16, acts=2, erratic=0.3, pal={2: 8}),
    "しにがみ": E(40, 14, phys=False, spr="ghost", fmin=12, fmax=20, w=13, pal={7: 13, 6: 2}),
    "メタルヘッド": E(52, 15, 5, mag=False, spr="iron", fmin=12, fmax=21, w=13, pal={13: 10, 5: 9}),
    "おおどろぼう": E(36, 10, 2, spr="thief", fmin=11, fmax=22, w=7, ai="thief", pal={3: 8}),
    "リッチ": E(40, 13, 2, spr="skull", fmin=13, fmax=24, w=11, ai="ranged", pal={2: 3, 8: 11}),
    "てっこうがめ": E(34, 15, phys=False, mag=False, spr="turtle", fmin=14, fmax=23, w=5, pal={3: 13, 11: 7}),
    # ---- 21〜30F ----
    "かげ武者": E(78, 24, 4, phys=False, spr="musha", fmin=20, fmax=30, w=13, pal={7: 5, 8: 1, 13: 2}),
    "ミスリルゴーレム": E(120, 26, 9, mag=False, spr="golem", fmin=21, fmax=30, w=12, slow=True,
                       pal={13: 12, 5: 6}),
    "スカイドラゴン": E(105, 24, 4, spr="dragon", fmin=20, fmax=30, w=11, ai="breath", pal={8: 12, 9: 6}),
    "トロル": E(110, 28, 3, spr="ogre", fmin=21, fmax=30, w=10, slow=True, pal={4: 3, 8: 5}),
    "アークリッチ": E(70, 22, 3, spr="skull", fmin=22, fmax=30, w=10, ai="ranged", pal={2: 1, 8: 10}),
    "たたりがめ": E(55, 22, phys=False, mag=False, spr="turtle", fmin=23, fmax=30, w=4, pal={3: 2, 11: 14}),
    "ヘルバット": E(48, 20, 2, spr="bat", fmin=22, fmax=30, w=12, acts=2, erratic=0.3, pal={2: 1, 7: 8}),
    # ---- 特別 ----
    "オーガ": E(40, 8, 1, spr="ogre", fmin=0, fmax=0, w=0, slow=True, boss=True),
    "オーガキング": E(160, 20, 4, spr="ogre", fmin=0, fmax=0, w=0, boss=True, pal={4: 10, 8: 2, 10: 7}),
    "ななつぼし": E(55, 9, phys=False, mag=False, spr="star", fmin=0, fmax=0, w=0, star=True, slow=True),
    "ゆめくい": E(260, 14, 2, spr="yume", fmin=0, fmax=0, w=0, ai="boss", boss=True),
}


def enemy_pool(f):
    return [(k, d["w"]) for k, d in ENEMIES.items() if d["fmin"] <= f <= d["fmax"] and d["w"] > 0]


# ---------------------------------------------------------------------------
# 道具
# ---------------------------------------------------------------------------
ITEMS = {
    "薬草": dict(k="herb", v=25, desc="HPを25回復する", price=40),
    "弟切草": dict(k="herb", v=100, desc="HPを100回復する", price=150),
    "ドラゴン草": dict(k="dgrass", v=35, desc="のむと前方に炎を吐く。35の固定ダメージ", price=120),
    "いのちの草": dict(k="seed", v="mhp", desc="最大HPがずっと5上がる", price=400),
    "ちからの草": dict(k="seed", v="atk", desc="攻撃力がずっと1上がる", price=400),
    "おにぎり": dict(k="food", v=50, desc="満腹度が50回復する", price=60),
    "大きなおにぎり": dict(k="food", v=100, desc="満腹度が100回復する", price=120),
    "いかずちの杖": dict(k="staff", v="bolt", desc="ふると雷。当たった敵に固定ダメージ（12+階数）。どんな敵にも効く", price=220),
    "ふきとばしの杖": dict(k="staff", v="blow", desc="ふると魔法弾。当たった敵を遠くへ吹き飛ばす", price=160),
    "かなしばりの杖": dict(k="staff", v="para", desc="ふると魔法弾。当たった敵をしばらく動けなくする", price=180),
    "真空斬りの巻物": dict(k="scroll", v=20, desc="部屋の敵すべてに固定ダメージ（20+階数）", price=180),
    "こん棒": dict(k="weapon", v=2, desc="武器 攻撃力+2", price=60),
    "カタナ": dict(k="weapon", v=5, desc="武器 攻撃力+5", price=250),
    "どうたぬき": dict(k="weapon", v=7, desc="武器 攻撃力+7", price=400),
    "ドラゴンキラー": dict(k="weapon", v=10, desc="武器 攻撃力+10", price=700),
    "まさむね": dict(k="weapon", v=14, desc="武器 攻撃力+14", price=1100),
    "かぐらのつるぎ": dict(k="weapon", v=19, desc="武器 攻撃力+19", price=1600),
    "木甲の盾": dict(k="shield", v=3, desc="盾 防御力+3", price=60),
    "青銅甲の盾": dict(k="shield", v=6, desc="盾 防御力+6", price=300),
    "重装の盾": dict(k="shield", v=10, desc="盾 防御力+10", price=700),
    "ドラゴンシールド": dict(k="shield", v=14, desc="盾 防御力+14", price=1100),
    "かがみの盾": dict(k="shield", v=19, desc="盾 防御力+19", price=1600),
    "ギタン": dict(k="gold", v=0, desc="お金", price=0),
}
# 出現テーブル（名前: 重み）。階数には依存しない。強い物は「出にくい」だけ
ITEM_TABLE = {
    "薬草": 24, "弟切草": 6, "ドラゴン草": 5, "いのちの草": 2, "ちからの草": 2,
    "おにぎり": 15, "大きなおにぎり": 5,
    "いかずちの杖": 6, "ふきとばしの杖": 5, "かなしばりの杖": 5, "真空斬りの巻物": 6,
    "こん棒": 4, "カタナ": 4, "どうたぬき": 3, "ドラゴンキラー": 2, "まさむね": 1.2, "かぐらのつるぎ": 0.6,
    "木甲の盾": 4, "青銅甲の盾": 4, "重装の盾": 2, "ドラゴンシールド": 1.2, "かがみの盾": 0.6,
}
# ダンジョンごとの調整（重みの上書き。0で出なくなる）。バランスが壊れたらここで絞る
ITEM_OVERRIDE = {}
RARE_GEAR = ["どうたぬき", "ドラゴンキラー", "まさむね", "かぐらのつるぎ",
             "青銅甲の盾", "重装の盾", "ドラゴンシールド", "かがみの盾"]
VERB = {"herb": "のむ", "dgrass": "のむ", "seed": "のむ", "food": "たべる", "staff": "ふる", "scroll": "よむ"}
SORT_ORDER = {"weapon": 0, "shield": 1, "food": 2, "herb": 3, "seed": 4, "dgrass": 5, "scroll": 6, "staff": 7,
              "gold": 9}


def item_pool(f=None):
    t = dict(ITEM_TABLE)
    t.update(ITEM_OVERRIDE)
    return [(n, w) for n, w in t.items() if w > 0]


def wchoice(pairs):
    tot = sum(w for _, w in pairs)
    r = random.uniform(0, tot)
    for k, w in pairs:
        r -= w
        if r <= 0:
            return k
    return pairs[-1][0]


def make_item(name):
    it = {"name": name, "n": 1, "eq": False}
    k = ITEMS[name]["k"]
    if k == "staff":
        it["n"] = random.randint(3, 5)
    elif k == "gold":
        it["n"] = random.randint(15, 40)
    return it


def item_label(it):
    k = ITEMS[it["name"]]["k"]
    if k == "staff":
        return f"{it['name']}[{it['n']}]"
    if k == "gold":
        return f"{it['n']}ギタン"
    return it["name"]


# ---------------------------------------------------------------------------
# ドット絵
# ---------------------------------------------------------------------------
PAL = {".": 0, "k": 1, "v": 2, "g": 3, "n": 4, "B": 5, "b": 6, "w": 7, "r": 8,
       "o": 9, "y": 10, "G": 11, "c": 12, "d": 13, "p": 14, "s": 15}

SPR = {
    "napo_f": [
        "......kkkk......",
        ".....krrrrk.....",
        ".....kprrpk.....",
        "...kkppppppkk...",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kpsssssssspk..",
        "..kssksssskssk..",
        "..kssksssskssk..",
        "..ksrssssssrsk..",
        "...ksssnnsssk...",
        "....kkwwwwkk....",
        "...kswwwwwwsk...",
        "....knnnnnnk....",
        "....knnkknnk....",
        "....kkk..kkk....",
    ],
    "napo_b": [
        "......kkkk......",
        ".....krrrrk.....",
        ".....kprrpk.....",
        "...kkppppppkk...",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "...kppppppppk...",
        "....kkwwwwkk....",
        "...kswwwwwwsk...",
        "....knnnnnnk....",
        "....knnkknnk....",
        "....kkk..kkk....",
    ],
    "napo_s": [
        ".....kkkk.......",
        "....krrrrk......",
        "....kprrpk......",
        "...kkppppppkk...",
        "..kppppppppppk..",
        "..kppppppppppk..",
        "..kpppsssssssk..",
        "..kpppsssssksk..",
        "..kpppsssssksk..",
        "..kppppssssrsk..",
        "...kppssssssk...",
        "....kkwwwwkk....",
        "....kwwwwwsk....",
        "....knnnnnnk....",
        "....knnkknnk....",
        "....kkk..kkk....",
    ],
    "mamuru": [
        "................",
        "...kk......kk...",
        "..kook....kook..",
        "..koookkkkoook..",
        "...kooooooook...",
        "..koooooooooook.",
        ".kooookoookoook.",
        ".kooookoookoook.",
        ".kopoooooooopok.",
        ".koooookkkooook.",
        ".kooooooooooook.",
        "..kooooooooook..",
        "...kkookkookk...",
        "...kook..kook...",
        "....kk....kk....",
        "................",
    ],
    "bat": [
        "................",
        "................",
        ".k............k.",
        ".kvk........kvk.",
        ".kvvk..kk..kvvk.",
        ".kvvvkkvvkkvvvk.",
        ".kvvvvvvvvvvvvk.",
        ".kvvvvwkkwvvvvk.",
        "..kvvvvvvvvvvk..",
        "...kvvkvvkvvk...",
        "....kk.kk.kk....",
    ],
    "ghost": [
        "................",
        ".....kkkkkk.....",
        "....kwwwwwwk....",
        "...kwwwwwwwwk...",
        "..kwwwwwwwwwwk..",
        "..kwwkwwwwkwwk..",
        "..kwwkwwwwkwwk..",
        "..kwwwwwwwwwwk..",
        ".kwwwwwkkwwwwwk.",
        ".kwwwwwwwwwwwbk.",
        ".kwwwwwwwwwwbbk.",
        ".kwwwwwwwwwbbbk.",
        ".kwwbwwbwwbbbbk.",
        ".kbk.kbk.kbk.kk.",
        "..k...k...k.....",
    ],
    "iron": [
        "................",
        ".....kkkkkk.....",
        "....kddddddk....",
        "...kddwddddddk..",
        "..kddwddddddddk.",
        "..kddddddddddk..",
        "..kkkkkkkkkkkk..",
        "..kBBkrrBBkrrk..",
        "..kkkkkkkkkkkk..",
        "..kddddddddddk..",
        "...kddkkkkddk...",
        "...kddddddddk...",
        "..kBkddddddkBk..",
        "..kBk.kddk.kBk..",
        "...k..kkkk..k...",
    ],
    "turtle": [
        "................",
        "................",
        "................",
        "................",
        ".....kkkkkk.....",
        "....kgGgGgGk....",
        "...kgGgggGggk...",
        "..kgggGgGgggkkk.",
        ".kgGgggggGggkGGk",
        ".kggGgGgggggkGkk",
        ".kkkkkkkkkkkkGGk",
        "..kGGk....kGGkk.",
        "...kk......kk...",
    ],
    "ogre": [
        "...k........k...",
        "..kyk......kyk..",
        "..kyykkkkkkyyk..",
        "..knnnnnnnnnnk..",
        ".knnwknnnnwknnk.",
        ".knnkknnnnkknnk.",
        ".knnnnnnnnnnnnk.",
        ".knnkwkwkwkwnnk.",
        "..knnkkkkkknnk..",
        ".krrknnnnnnkrrk.",
        "krrrknnnnnnkrrrk",
        "krrkkddddddkkrrk",
        ".kk.knnnnnnk.kk.",
        "....knnkknnk....",
        "...kknnk.knnkk..",
        "...kkkk..kkkk...",
    ],
    "thief": [
        "................",
        ".....kkkkk......",
        "....kgggggk.....",
        "...kgggggggk....",
        "...kggkkkkgk....",
        "...kgksskskk....",
        "...kgkssssk.kk..",
        "....kkssssk.kyk.",
        "...kggkkkkgkkyyk",
        "..kgggggggggkyyk",
        "..kgkgggggkgkkk.",
        "..kskgggggksk...",
        "...k.kgggk.k....",
        ".....kgkgk......",
        ".....kkkkk......",
    ],
    "skull": [
        "................",
        ".....kkkkkk.....",
        "....kwwwwwwk....",
        "...kwwwwwwwwk...",
        "...kwkkwwkkwk...",
        "...kwkrwwkrwk...",
        "...kwwwkkwwwk...",
        "....kwkwwkwk....",
        "...kvkkkkkkvk.k.",
        "..kvvvvvvvvvvkyk",
        "..kvvkvvvvkvvkok",
        "..kvwkvvvvkwvkk.",
        "..kvvvvvvvvvvk..",
        "...kvvvvvvvvk...",
        "...kkkkkkkkkk...",
    ],
    "musha": [
        "......k..k......",
        ".....kyk.kyk....",
        "....krrrkrrrk...",
        "...krrrrrrrrrk..",
        "..kkkkkkkkkkkkk.",
        "...kwwkwwwkwwk..",
        "...kwwkwwwkwwk..",
        "...kwwwwwwwwwk..",
        "..kddkwwwwwkddk.",
        "..kdddkwwwkdddk.",
        "..kwddddddddwwk.",
        "..kwwddddddwwbk.",
        "..kwwwwwwwwwbbk.",
        "..kwbwwbwwbbbbk.",
        "..kbk.kbk.kbkk..",
    ],
    "golem": [
        "................",
        "....kkkkkkkk....",
        "...kddddddddk...",
        "...kdrrddrrdk...",
        "...kddddddddk...",
        "..kkkkkkkkkkkk..",
        ".kddkddddddkddk.",
        ".kddkdBBBBdkddk.",
        ".kddkddddddkddk.",
        ".kBBkdBBBBdkBBk.",
        ".kkkkddddddkkkk.",
        "....kddkkddk....",
        "....kddkkddk....",
        "...kBBBkkBBBk...",
        "...kkkkk.kkkk...",
    ],
    "dragon": [
        "................",
        "..k.k...........",
        ".krkrk..........",
        ".krrrrkk......k.",
        "krwkrrrrk....krk",
        "krrrrrrrrk..krrk",
        ".kkrrooorrk.krk.",
        "...krooorrrkrk..",
        "..krrooorrrrrk..",
        ".krrkoooorrrrk..",
        ".kk.kooorrrrk...",
        "....krrrrkrrk...",
        "...krrk.krrk....",
        "...kkk..kkk.....",
    ],
    "star": [
        "................",
        ".......kk.......",
        "......kyyk......",
        "......kyyk......",
        ".....kyyyyk.....",
        "kkkkkkyyyyykkkkk",
        "kyyyyyyyyyyyyyyk",
        ".kyyykyyyykyyyk.",
        "..kyykyyyykyyk..",
        "...kyyyyyyyyk...",
        "...kyyyrryyyk...",
        "..kyyyykkyyyyk..",
        "..kyyyk..kyyyk..",
        ".kyyk......kyyk.",
        ".kkk........kkk.",
    ],
    "yume": [
        "..k..........k..",
        ".kvk..kkkk..kvk.",
        ".kvvkkvvvvkkvvk.",
        "..kvvvvvvvvvvk..",
        ".kvvvvvvvvvvvvk.",
        "kvvwwkvvvvwwkvvk",
        "kvvwrkvvvvwrkvvk",
        "kvvvvvvvvvvvvvvk",
        "kvvvkwkwkwkwvvvk",
        ".kvvvkkkkkkvvvk.",
        "kBvvvvvvvvvvvvBk",
        "kBBvvvvvvvvvvBBk",
        ".kBBvvBvvBvvBBk.",
        "..kBBkBBkBBkBk..",
        "...kk.kk.kk.kk..",
    ],
}
SPR_IDX = {}


def load_sprites():
    img = pyxel.images[0]
    for i, (name, rows) in enumerate(SPR.items()):
        ox, oy = (i % 16) * 16, (i // 16) * 16
        rows = (rows + ["." * 16] * 16)[:16]
        for y, row in enumerate(rows):
            row = (row + "." * 16)[:16]
            for x, ch in enumerate(row):
                img.pset(ox + x, oy + y, PAL[ch])
        SPR_IDX[name] = (ox, oy)
    oy = 32
    # 階段
    img.rect(32, oy, 16, 16, 0)
    for i in range(4):
        img.rect(34 + i * 3, oy + 3 + i * 3, 12 - i * 3, 3, 13 if i % 2 == 0 else 7)
        img.line(34 + i * 3, oy + 5 + i * 3, 45, oy + 5 + i * 3, 1)
    SPR_IDX["stairs"] = (32, oy)
    # ガチャ台（背景は透過色0）
    img.rect(48, oy, 16, 16, 0)
    img.rect(50, oy + 8, 12, 8, 8)
    img.rectb(50, oy + 8, 12, 8, 1)
    img.circ(56, oy + 6, 5, 6)
    img.circb(56, oy + 6, 5, 1)
    img.pset(54, oy + 5, 10)
    img.pset(57, oy + 4, 14)
    img.pset(58, oy + 7, 11)
    img.pset(55, oy + 8, 12)
    img.rect(54, oy + 11, 4, 3, 10)
    img.pset(59, oy + 12, 7)
    SPR_IDX["gacha"] = (48, oy)


# 階層ごとの色合い（床, 床の点, 壁, 壁ハイライト, 壁の線）
FLOOR_THEME = [
    (4, 2, 5, 12, 1),    # 0: 赤土とれんが
    (3, 1, 13, 7, 5),    # 1: 苔と石
    (5, 1, 2, 14, 1),    # 2: 夜と紫
    (1, 2, 2, 8, 0),     # 3: ボス・中ボス
    (12, 6, 5, 7, 1),    # 4: 氷
    (2, 8, 1, 8, 0),     # 5: 溶岩
    (13, 5, 4, 9, 1),    # 6: 砂岩
    (1, 5, 2, 14, 0),    # 7: 奈落
]


def theme_for(f, last=10):
    if f == last or f in (10, 20):
        return FLOOR_THEME[3]
    if f <= 9:
        return FLOOR_THEME[(f - 1) // 3]
    return FLOOR_THEME[4 + min(3, (f - 11) // 5)]


def init_sounds():
    S = pyxel.sounds
    S[0].set("c2", "n", "5", "f", 4)                 # 空振り
    S[1].set("c3a2", "n", "76", "f", 5)              # ヒット
    S[2].set("c1", "t", "4", "f", 8)                 # 効かない
    S[3].set("c3e3g3c4", "p", "6", "n", 4)           # 撃破
    S[4].set("e3g3c4e4g4", "s", "5", "n", 5)         # カード
    S[5].set("g4", "p", "3", "f", 3)                 # ガチャ回転
    S[6].set("c3e3g3c4", "s", "6", "n", 7)           # ガチャ普通
    S[7].set("c3e3g3c4e4g4c4", "s", "6", "n", 6)     # ガチャレア
    S[8].set("a1f1", "n", "76", "f", 6)              # 被ダメ
    S[9].set("c3g3c4", "t", "6", "n", 7)             # 回復
    S[10].set("c4d4e4", "p", "5", "n", 5)            # 拾う
    S[11].set("c2c3c2c3", "s", "5", "n", 4)          # 魔法
    S[12].set("g3e3c3g2", "t", "6", "f", 10)         # 階段
    S[13].set("a2a1", "n", "65", "f", 8)             # 敵の魔法/ブレス
    S[14].set("e2c2a1", "s", "765", "f", 12)         # ボス


def sfx(n, ch=None):
    if ch is None:
        ch = {0: 0, 1: 0, 2: 0, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2, 8: 3, 9: 1, 10: 1,
              11: 1, 12: 2, 13: 3, 14: 2}.get(n, 0)
    pyxel.play(ch, n)


def find_font():
    cands = []
    try:
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "umplus_j10r.bdf"))
    except NameError:
        pass
    cands += [os.path.join("assets", "umplus_j10r.bdf"),
              os.path.join("napo_card", "assets", "umplus_j10r.bdf")]
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[-1]


def txt(x, y, s, col):
    pyxel.text(x, y, s, col, FONT)


def txts(x, y, s, col, sh=1):
    pyxel.text(x + 1, y + 1, s, sh, FONT)
    pyxel.text(x, y, s, col, FONT)


def tw(s):
    return FONT.text_width(s)


def wrap(s, width):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for ch in para:
            if tw(cur + ch) > width:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# 入力
# ---------------------------------------------------------------------------
KU = [pyxel.KEY_UP, pyxel.GAMEPAD1_BUTTON_DPAD_UP]
KD = [pyxel.KEY_DOWN, pyxel.GAMEPAD1_BUTTON_DPAD_DOWN]
KL = [pyxel.KEY_LEFT, pyxel.GAMEPAD1_BUTTON_DPAD_LEFT]
KR = [pyxel.KEY_RIGHT, pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT]
KZ = [pyxel.KEY_Z, pyxel.KEY_RETURN, pyxel.GAMEPAD1_BUTTON_A]
KX = [pyxel.KEY_X, pyxel.GAMEPAD1_BUTTON_B]
KC = [pyxel.KEY_C, pyxel.GAMEPAD1_BUTTON_X]
KTURN = [pyxel.KEY_A, pyxel.GAMEPAD1_BUTTON_LEFTSHOULDER]
KDIAG = [pyxel.KEY_S, pyxel.GAMEPAD1_BUTTON_RIGHTSHOULDER]
KWAIT = [pyxel.KEY_SPACE, pyxel.GAMEPAD1_BUTTON_Y]
KDASH = [pyxel.KEY_SHIFT]
ARROWS = KU + KD + KL + KR


def held(keys):
    return any(pyxel.btn(k) for k in keys)


def pressed(keys, hold=0, rep=0):
    return any(pyxel.btnp(k, hold=hold, repeat=rep) for k in keys)


def menu_p(keys):
    return pressed(keys, 12, 3)


# ---------------------------------------------------------------------------
# エンティティ
# ---------------------------------------------------------------------------
class Enemy:
    def __init__(self, kind, x, y, f=1):
        d = ENEMIES[kind]
        self.kind = kind
        lv = max(0, f - d["fmin"]) if d["fmin"] > 0 else 0
        self.hp = self.mhp = int(d["hp"] * (1 + 0.10 * lv))
        self.atk = d["atk"] + lv // 2
        self.df = d["df"]
        self.phys = d["phys"]
        self.mag = d["mag"]
        self.acts = d.get("acts", 1)
        self.slow = d.get("slow", False)
        self.erratic = d.get("erratic", 0)
        self.ai = d.get("ai")
        self.star = d.get("star", False)
        self.spr = d["spr"]
        self.boss = d.get("boss", False)
        self.x, self.y = x, y
        self.rx, self.ry = x * TS, y * TS
        self.flash = 0
        self.lx = self.ly = 0
        self.para = 0
        self.sleep = False
        self.stolen = False
        self.loot = 0
        self.face = -1
        self.phase = 0
        self.timer = 0
        self.pal = d.get("pal")


class Player:
    def __init__(self):
        self.x = self.y = 0
        self.rx = self.ry = 0
        self.fx, self.fy = 0, 1
        self.hp = 40
        self.mp = 8
        self.full = 100
        self.gold = 0
        self.cards = []
        self.inv = []
        self.flash = 0
        self.lx = self.ly = 0
        self.regen = 0.0
        self.mpregen = 0.0
        self.bonus_mhp = 0
        self.bonus_atk = 0


class Room:
    def __init__(self, gx, gy):
        self.gx, self.gy = gx, gy
        self.tiles = None
        self.doors = {}
        self.enemies = []
        self.items = {}
        self.stairs = None
        self.gacha = None
        self.visited = False
        self.boss_room = False
        self.pending = []   # [delay, enemy, door]
        self.kind = "normal"        # normal / shop / mhouse / dark / gimmick
        self.locked = False
        self.mh_state = 0           # 0:未発動 1:戦闘中 2:済み
        self.oneway_block = set()   # この部屋から出られない扉の向き
        self.boxes = set()
        self.boxes_init = set()
        self.switches = set()
        self.gates = set()
        self.chest = None
        self.solved = False
        self.shop = {}              # pos -> {"item": it} or {"card": cid}, "price"


# ---------------------------------------------------------------------------
# 部屋生成
# ---------------------------------------------------------------------------
def tpl_open(t):
    pass


def tpl_pillars(t):
    for x in (4, 8, 11, 15):
        for y in (3, 9):
            t[y][x] = "#"


def tpl_block(t):
    for y in range(4, 9):
        for x in range(7, 13):
            t[y][x] = "#"


def tpl_lanes(t):
    for y in (4, 8):
        for x in range(2, 18):
            t[y][x] = "#"
        for g in random.sample(range(3, 17), 2):
            t[y][g] = "."


def tpl_ring(t):
    for x in range(5, 15):
        t[3][x] = "#"
        t[9][x] = "#"
    for y in range(3, 10):
        t[y][5] = "#"
        t[y][14] = "#"
    gaps = [(10, 3), (9, 9), (5, 6), (14, 6)]
    for gx, gy in random.sample(gaps, random.randint(2, 3)):
        t[gy][gx] = "."


def tpl_cols(t):
    for x in (6, 13):
        for y in range(1, 12):
            t[y][x] = "#"
        for g in random.sample([2, 3, 5, 7, 9, 10], 2):
            t[g][x] = "."


def tpl_scatter(t):
    for _ in range(random.randint(8, 13)):
        t[random.randint(2, 10)][random.randint(2, 17)] = "#"


def tpl_L(t):
    for x in range(3, 10):
        t[3][x] = "#"
    for y in range(3, 8):
        t[y][9] = "#"
    for x in range(11, 17):
        t[9][x] = "#"
    for y in range(5, 10):
        t[y][11] = "#"


def tpl_cross(t):
    for x in range(3, 17):
        if x not in (9, 10):
            t[6][x] = "#"
    for y in range(2, 11):
        if y not in (4, 6, 8):
            t[y][9] = "#"


def tpl_maze(t):
    for x in range(3, 17, 3):
        gap = random.randint(2, 10)
        for y in range(1, 12):
            if abs(y - gap) > 1:
                t[y][x] = "#"


TEMPLATES = [tpl_open, tpl_pillars, tpl_block, tpl_lanes, tpl_ring, tpl_cols, tpl_scatter,
             tpl_L, tpl_cross, tpl_maze, tpl_pillars, tpl_lanes, tpl_ring]


def build_tiles(doors, tpl=None):
    t = None
    for attempt in range(14):
        t = [["." for _ in range(RW)] for _ in range(RH)]
        f = tpl if (tpl and attempt == 0) else random.choice(TEMPLATES)
        if attempt >= 12:
            f = tpl_open
        f(t)
        if random.random() < 0.5:
            t = [row[::-1] for row in t]
        if random.random() < 0.5:
            t = t[::-1]
        for x in range(RW):
            t[0][x] = t[RH - 1][x] = "#"
        for y in range(RH):
            t[y][0] = t[y][RW - 1] = "#"
        for d in doors:
            x, y = DOORS[d]
            t[y][x] = "."
            for (ix, iy) in DOOR_IN[d]:
                t[iy][ix] = "."
        starts = [DOOR_IN[d][0] for d in doors] or [(10, 6)]
        sx, sy = starts[0]
        seen = {(sx, sy)}
        q = deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < RW and 0 <= ny < RH and t[ny][nx] == "." and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    q.append((nx, ny))
        if all(s in seen for s in starts) and len(seen) >= 90:
            for y in range(RH):
                for x in range(RW):
                    if t[y][x] == "." and (x, y) not in seen:
                        t[y][x] = "#"
            return t
    return t


def cheb(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


def sign(v):
    return (v > 0) - (v < 0)


# ---------------------------------------------------------------------------
# ゲーム本体
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        global FONT
        pyxel.init(W, H, title="ナポのカードダンジョン", fps=60)
        FONT = pyxel.Font(find_font())
        load_sprites()
        init_sounds()
        self.state = "title"
        self.frame = 0
        self.help = False
        self.best = {i: 0 for i in range(len(DUNGEONS))}
        self.dg_idx = 0
        self.title_sel = 0
        self.dg = DUNGEONS[0]
        self.last = self.dg["last"]
        self.slide = None
        self.banner = 0
        self.reset_fx()

    def run(self):
        pyxel.run(self.update, self.draw)

    def reset_fx(self):
        self.popups = []
        self.parts = []
        self.projs = []
        self.log = []
        self.shake = 0
        self.flash_screen = 0

    # ------------------------------------------------------------------ 新規
    def new_game(self, dg=None):
        if dg is not None:
            self.dg_idx = dg
        self.dg = DUNGEONS[self.dg_idx]
        self.last = self.dg["last"]
        ITEM_OVERRIDE.clear()
        ITEM_OVERRIDE.update(self.dg.get("items", {}))
        self.reset_fx()
        self.p = Player()
        self.floor = 1
        self.turn = 0
        self.fturn = 0
        self.kills = 0
        self.kill_prog = 0
        self.kill_need = 3
        self.pending_cards = 0
        self.hold_t = 0
        self.dash = None
        self.dash_t = 0
        self.need_release = True
        self.inv_sel = 0
        self.inv_top = 0
        self.sk_sel = 0
        self.anim_t = 0
        self.slide = None
        self.banner = 60
        self.cause = ""
        self.shop_pending = None
        self.best[self.dg_idx] = max(self.best[self.dg_idx], 1)
        self.gen_floor()
        p = self.p
        for n in ("薬草", "おにぎり", "いかずちの杖"):
            it = make_item(n)
            if n == "いかずちの杖":
                it["n"] = 3
            p.inv.append(it)
        club = make_item("こん棒")
        club["eq"] = True
        p.inv.insert(0, club)
        p.gold = 20
        self.msg(f"ナポは「{self.dg['name']}」に足をふみ入れた。", 7)
        self.msg(f"目指すは{self.last}Fの奥。まずはカードを1枚えらぼう。", 10)
        skills = [k for k, c in CARDS.items() if c["r"] == 1 and c["t"] == "skill"]
        others = [k for k, c in CARDS.items() if c["r"] == 1 and c["t"] in ("stat", "passive")]
        pick = [random.choice(skills)] + random.sample(others, 2)
        random.shuffle(pick)
        self.open_cards(pick, "start")

    def next_floor(self):
        self.floor += 1
        self.fturn = 0
        self.projs = []
        self.dash = None
        self.gen_floor()
        self.banner = 70
        self.best[self.dg_idx] = max(self.best[self.dg_idx], self.floor)
        f = self.floor
        star = self.dg["star"]
        self.msg(f"{f}Fについた。", 10)
        if f in (star - 2, star - 1):
            self.msg(f"うわさ: {star}Fの『ななつぼし』は物理も魔法も効かないらしい", 9)
        if f == star:
            self.msg("…ただならぬ光を感じる。ななつぼしのフロアだ！", 10)
        if f in self.dg["mids"]:
            self.msg("強い気配がする…。階段の前に何かがいる", 8)
            sfx(14)
        if f == self.last:
            self.msg("ふかい眠りの気配…。このフロアの奥に何かいる", 8)
            sfx(14)

    def gen_floor(self):
        f = self.floor
        last = f == self.last
        deep = self.last >= 30
        start = (random.randrange(GW), random.randrange(GH))
        cells = [start]
        conn = set()
        target = random.randint(4, 5) if last else random.randint(6, 9)
        guard = 0
        while len(cells) < target and guard < 500:
            guard += 1
            a = random.choice(cells)
            nbs = [(a[0] + dx, a[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nbs = [n for n in nbs if 0 <= n[0] < GW and 0 <= n[1] < GH and n not in cells]
            if not nbs:
                continue
            b = random.choice(nbs)
            cells.append(b)
            conn.add(frozenset((a, b)))
        extra = []
        for _ in range(0 if last else 2):
            a = random.choice(cells)
            nbs = [(a[0] + dx, a[1] + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            nbs = [n for n in nbs if n in cells and frozenset((a, n)) not in conn]
            if nbs:
                b = random.choice(nbs)
                conn.add(frozenset((a, b)))
                extra.append((a, b))
        self.rooms = {}
        for c in cells:
            r = Room(*c)
            for d, (dx, dy) in DIR_VEC.items():
                if frozenset((c, (c[0] + dx, c[1] + dy))) in conn:
                    r.doors[d] = DOORS[d]
            self.rooms[c] = r
        # 一方通行（ループになっている通路だけ。行き止まりにはならない）
        for a, b in extra:
            if f >= 2 and random.random() < 0.6:
                if random.random() < 0.5:
                    a, b = b, a
                d = [k for k, v in DIR_VEC.items() if (b[0] + v[0], b[1] + v[1]) == a][0]
                self.rooms[b].oneway_block.add(d)
        dist = {start: 0}
        q = deque([start])
        while q:
            a = q.popleft()
            for dx, dy in DIR_VEC.values():
                b = (a[0] + dx, a[1] + dy)
                if b in self.rooms and b not in dist and frozenset((a, b)) in conn:
                    dist[b] = dist[a] + 1
                    q.append(b)
        far = max(dist, key=lambda k: dist[k])
        others = [c for c in cells if c not in (start, far)]
        gacha_cell = random.choice(others) if others else start
        # 部屋の種類
        cand = [c for c in others if c != gacha_cell]
        random.shuffle(cand)
        if not last:
            if f >= 3 and cand and random.random() < (0.4 if deep else 0.25):
                self.rooms[cand.pop()].kind = "shop"
            if f >= 2 and cand and random.random() < 0.3:
                self.rooms[cand.pop()].kind = "gimmick"
            if f >= 3 and cand and random.random() < 0.22:
                self.rooms[cand.pop()].kind = "mhouse"
            if f >= 4:
                for c in cand:
                    if random.random() < 0.13:
                        self.rooms[c].kind = "dark"
        for c, r in self.rooms.items():
            tpl = tpl_open if c == start else None
            if c == gacha_cell:
                tpl = random.choice([tpl_open, tpl_pillars])
            if r.kind in ("shop", "gimmick"):
                tpl = tpl_open
            if last and c == far:
                tpl = tpl_pillars
            r.tiles = build_tiles(r.doors.keys(), tpl)
            if r.kind == "gimmick":
                self.setup_gimmick(r)
            elif r.kind == "shop":
                self.setup_shop(r)
        sr = self.rooms[start]
        sr.visited = True
        self.room = sr
        self.p.x, self.p.y = 10, 6
        if sr.tiles[6][10] != ".":
            self.p.x, self.p.y = self.free_tile(sr)
        self.p.rx, self.p.ry = self.p.x * TS, self.p.y * TS
        fr = self.rooms[far]
        gr = self.rooms[gacha_cell]
        gr.gacha = self.free_tile(gr, avoid_doors=True, center=True)
        if last:
            fr.boss_room = True
            pos = (10, 6) if fr.tiles[6][10] == "." else self.free_tile(fr, avoid_doors=True)
            boss = Enemy("ゆめくい", *pos, f)
            if deep:
                boss.hp = boss.mhp = 720
                boss.atk, boss.df = 32, 6
            fr.enemies.append(boss)
        else:
            fr.stairs = self.free_tile(fr, avoid_doors=True)
        # 敵
        pool = enemy_pool(f)
        must = []
        if f == 2:
            must = ["ゆうれい"]
        elif f == 3:
            must = ["アイアンヘッド"]
        elif f == 4:
            must = ["こうらがめ"]
        star_floor = f == self.dg["star"]
        stars = (4 if deep else 3) if star_floor else 0
        for c, r in self.rooms.items():
            if c == start or r.boss_room or r.kind in ("shop", "gimmick", "mhouse"):
                continue
            n = random.randint(1, 3) + (1 if f >= 5 and random.random() < 0.4 else 0)
            for _ in range(n):
                if stars and random.random() < 0.45:
                    kind = "ななつぼし"
                    stars -= 1
                else:
                    kind = must.pop() if must else wchoice(pool)
                pos = self.free_tile(r, avoid_doors=True)
                if pos:
                    e = self.spawn(kind, pos, f)
                    e.sleep = random.random() < 0.3 and not e.star
                    r.enemies.append(e)
        if star_floor:
            for _ in range(stars):
                pos = self.free_tile(fr, avoid_doors=True, near=fr.stairs)
                if pos:
                    fr.enemies.append(self.spawn("ななつぼし", pos, f))
        if fr.stairs and (f in self.dg["guards"] or f in self.dg["mids"]):
            pos = self.free_tile(fr, avoid_doors=True, near=fr.stairs)
            if pos:
                fr.enemies.append(self.spawn("オーガキング" if f in self.dg["mids"] else "オーガ", pos, f))
        # 道具
        ipool = item_pool(f)
        for c, r in self.rooms.items():
            if r.boss_room or r.kind in ("shop", "gimmick"):
                continue
            for _ in range(random.randint(1, 3)):
                pos = self.free_tile(r)
                if pos:
                    r.items[pos] = make_item(wchoice(ipool))
            if random.random() < 0.6:
                pos = self.free_tile(r)
                if pos:
                    g = make_item("ギタン")
                    g["n"] = int(g["n"] * (1 + 0.25 * (f - 1)))
                    r.items[pos] = g

    def spawn(self, kind, pos, f):
        e = Enemy(kind, pos[0], pos[1], f)
        if kind == "ななつぼし":
            e.hp = e.mhp = 55 + max(0, f - 7) * 9
            e.atk = 9 + max(0, f - 7)
        elif kind == "オーガ":
            e.hp = e.mhp = 30 + f * 12
            e.atk = 6 + f
        elif kind == "オーガキング":
            e.hp = e.mhp = 150 if f <= 10 else 320
            e.atk = 18 if f <= 10 else 30
            e.df = 4 if f <= 10 else 8
        return e

    def price_scale(self):
        return 1 + 0.15 * (self.floor - 1)

    def setup_shop(self, r):
        spots = [(7, 4), (10, 4), (13, 4), (7, 8), (10, 8), (13, 8)]
        pool = [(n, w) for n, w in item_pool(self.floor)]
        for pos in spots[:5]:
            it = make_item(wchoice(pool))
            r.shop[pos] = {"item": it, "price": int(ITEMS[it["name"]]["price"] * self.price_scale() / 10) * 10}
        cid = self.draw_cards(1, self.gacha_rates(), False, items=False)[0]
        price = {1: 150, 2: 350, 3: 700}[CARDS[cid]["r"]]
        r.shop[spots[5]] = {"card": cid, "price": int(price * self.price_scale() / 10) * 10}

    def setup_gimmick(self, r):
        layouts = [
            ([(6, 4), (14, 8)], [(4, 9), (16, 3)], [(8, 8), (12, 4)]),
            ([(6, 8), (13, 4), (7, 3)], [(4, 4), (16, 9), (15, 2)], [(8, 9), (12, 3)]),
            ([(5, 4), (15, 8)], [(8, 10), (12, 2)], [(7, 7), (13, 5)]),
        ]
        boxes, sw, pil = random.choice(layouts)
        for x, y in pil:
            r.tiles[y][x] = "#"
        r.boxes = set(boxes)
        r.boxes_init = set(boxes)
        r.switches = set(sw)
        r.chest = (10, 6)
        r.gates = {(10 + dx, 6 + dy) for dx, dy in DIRS8}
        for (x, y) in list(r.gates) + [r.chest]:
            r.tiles[y][x] = "."

    def free_tile(self, r, avoid_doors=False, center=False, near=None):
        cands = []
        bad = set()
        if avoid_doors:
            for d in r.doors:
                x, y = DOORS[d]
                for dx in range(-3, 4):
                    for dy in range(-3, 4):
                        bad.add((x + dx, y + dy))
        for y in range(1, RH - 1):
            for x in range(1, RW - 1):
                if not self.passable(r, x, y) or (x, y) in r.switches or (x, y) in r.shop:
                    continue
                if (x, y) in bad or (x, y) in r.items or (x, y) == r.stairs or (x, y) == r.gacha:
                    continue
                if any(e.x == x and e.y == y for e in r.enemies):
                    continue
                if r is getattr(self, "room", None) and (x, y) == (self.p.x, self.p.y):
                    continue
                if center and not (5 <= x <= 14 and 3 <= y <= 9):
                    continue
                if center and any(r.tiles[y + dy][x + dx] != "." for dx, dy in DIRS8):
                    continue
                cands.append((x, y))
        if not cands:
            if center or avoid_doors:
                return self.free_tile(r, near=near)
            return None
        if near:
            cands.sort(key=lambda c: cheb(c[0], c[1], near[0], near[1]))
            return cands[min(len(cands) - 1, random.randint(1, 3))]
        return random.choice(cands)

    # ------------------------------------------------------------------ 補助
    def msg(self, s, col=7):
        self.log.append([s, col, 0])
        if len(self.log) > 30:
            self.log = self.log[-30:]

    def popup(self, x, y, s, col, delay=0):
        self.popups.append(dict(x=x * TS + 8, y=ROOM_Y + y * TS, s=str(s), col=col, t=0, d=delay))

    def burst(self, x, y, col, n=10, delay=0):
        for _ in range(n):
            self.parts.append(dict(x=x * TS + 8, y=ROOM_Y + y * TS + 8,
                                   vx=random.uniform(-2, 2), vy=random.uniform(-2.5, 1),
                                   col=col, life=random.randint(12, 24), d=delay))

    def is_wall(self, r, x, y):
        return not (0 <= x < RW and 0 <= y < RH) or r.tiles[y][x] == "#"

    def passable(self, r, x, y):
        return (0 <= x < RW and 0 <= y < RH and r.tiles[y][x] == "." and (x, y) != r.gacha
                and (x, y) not in r.boxes and (x, y) not in r.gates and (x, y) != r.chest)

    def can_exit(self, r, d):
        return d in r.doors and d not in r.oneway_block and not r.locked

    def can_step(self, r, x, y, dx, dy):
        if not self.passable(r, x + dx, y + dy):
            return False
        if dx and dy and (self.is_wall(r, x + dx, y) or self.is_wall(r, x, y + dy)):
            return False
        return True

    def diag_ok(self, r, x, y, dx, dy):
        if dx and dy and (self.is_wall(r, x + dx, y) or self.is_wall(r, x, y + dy)):
            return False
        return True

    def enemy_at(self, x, y, r=None):
        r = r or self.room
        for e in r.enemies:
            if e.x == x and e.y == y:
                return e
        return None

    def bfs(self, r, sx, sy, maxd=40):
        dist = {(sx, sy): 0}
        q = deque([(sx, sy)])
        while q:
            x, y = q.popleft()
            d = dist[(x, y)]
            if d >= maxd:
                continue
            for dx, dy in DIRS8:
                nx, ny = x + dx, y + dy
                if (nx, ny) in dist:
                    continue
                if self.can_step(r, x, y, dx, dy):
                    dist[(nx, ny)] = d + 1
                    q.append((nx, ny))
        return dist

    def stats(self):
        p = self.p
        s = dict(atk=3 + p.bonus_atk, df=0, mhp=40 + p.bonus_mhp, mag=3, mmp=8)
        for it in p.inv:
            if it["eq"]:
                k = ITEMS[it["name"]]["k"]
                if k == "weapon":
                    s["atk"] += ITEMS[it["name"]]["v"]
                elif k == "shield":
                    s["df"] += ITEMS[it["name"]]["v"]
        for cid in p.cards:
            for k, v in CARDS[cid]["fx"].items():
                if k == "def":
                    s["df"] += v
                elif k in s:
                    s[k] += v
        return s

    def ncard(self, cid):
        return self.p.cards.count(cid)

    def clamp_player(self):
        st = self.stats()
        self.p.hp = min(self.p.hp, st["mhp"])
        self.p.mp = min(self.p.mp, st["mmp"])

    # ------------------------------------------------------------------ update
    def update(self):
        self.frame += 1
        self.update_fx()
        if pyxel.btnp(pyxel.KEY_H) and self.state != "title":
            self.help = not self.help
            return
        if self.help:
            if pressed(KX) or pressed(KZ):
                self.help = False
            return
        st = self.state
        if st == "title":
            if menu_p(KU) or menu_p(KD):
                self.title_sel = 1 - self.title_sel
            if pressed(KZ):
                self.new_game(self.title_sel)
            return
        if st in ("gameover", "clear"):
            self.anim_t += 1
            if pyxel.btnp(pyxel.KEY_R) or (self.anim_t > 40 and pressed(KZ)):
                self.new_game()
            elif self.anim_t > 40 and pressed(KX):
                self.state = "title"
            return
        if self.need_release:
            if not held(KZ + KX + KC):
                self.need_release = False
            if st != "play":
                return
        getattr(self, "upd_" + st)()

    def update_fx(self):
        if self.slide:
            self.slide["t"] += 1
            if self.slide["t"] >= SLIDE_FRAMES:
                self.slide = None
        if self.banner > 0:
            self.banner -= 1
        ents = []
        if hasattr(self, "room") and self.state != "title":
            ents = [self.p] + self.room.enemies
        for e in ents:
            tx, ty = e.x * TS, e.y * TS
            e.rx += (tx - e.rx) * 0.5
            e.ry += (ty - e.ry) * 0.5
            if abs(tx - e.rx) < 0.5:
                e.rx = tx
            if abs(ty - e.ry) < 0.5:
                e.ry = ty
            e.lx *= 0.6
            e.ly *= 0.6
            if e.flash > 0:
                e.flash -= 1
        for pp in self.popups:
            if pp["d"] > 0:
                pp["d"] -= 1
            else:
                pp["t"] += 1
        self.popups = [pp for pp in self.popups if pp["t"] < 32]
        for pa in self.parts:
            if pa["d"] > 0:
                pa["d"] -= 1
                continue
            pa["x"] += pa["vx"]
            pa["y"] += pa["vy"]
            pa["vy"] += 0.15
            pa["life"] -= 1
        self.parts = [pa for pa in self.parts if pa["life"] > 0]
        for pr in self.projs:
            dx, dy = pr["tx"] - pr["x"], pr["ty"] - pr["y"]
            dist = (dx * dx + dy * dy) ** 0.5
            sp = 9
            if dist <= sp:
                pr["done"] = True
            else:
                pr["x"] += dx / dist * sp
                pr["y"] += dy / dist * sp
        self.projs = [pr for pr in self.projs if not pr.get("done")]
        for l in self.log:
            l[2] += 1
        if self.shake > 0:
            self.shake -= 1
        if self.flash_screen > 0:
            self.flash_screen -= 1

    # ---------------------------------------------------------------- play
    def read_dir(self):
        dx = (1 if held(KR) else 0) - (1 if held(KL) else 0)
        dy = (1 if held(KD) else 0) - (1 if held(KU) else 0)
        return dx, dy

    def upd_play(self):
        p = self.p
        if self.slide:
            # 画面スライド中は待つ（長押しの連続移動は途切れない）
            if held(ARROWS):
                self.hold_t += 1
            return
        if self.dash:
            if pressed(KZ + KX + KC + KWAIT):
                self.dash = None
            else:
                self.dash_t += 1
                if self.dash_t % 2 == 0:
                    dx, dy = self.dash
                    if not self.dash_ok(dx, dy):
                        self.dash = None
                    else:
                        moved = self.try_move(dx, dy)
                        if not moved or self.state != "play":
                            self.dash = None
                        else:
                            self.end_turn()
                            if self.dash_should_stop():
                                self.dash = None
                return
        dx, dy = self.read_dir()
        if held(ARROWS):
            self.hold_t += 1
        else:
            self.hold_t = 0
        trig = pressed(ARROWS) or (self.hold_t > 8 and (self.hold_t - 8) % 5 == 0)

        if held(KTURN):
            if trig and (dx or dy):
                p.fx, p.fy = dx, dy
            return
        if trig and (dx or dy):
            if held(KDIAG) and not (dx and dy):
                return
            if held(KDASH):
                p.fx, p.fy = dx, dy
                if self.dash_ok(dx, dy):
                    self.dash = (dx, dy)
                    self.dash_t = 1
                if self.try_move(dx, dy):
                    self.end_turn()
                    if self.dash and self.dash_should_stop():
                        self.dash = None
                else:
                    self.dash = None
                return
            if self.try_move(dx, dy):
                self.end_turn()
            return
        if self.need_release:
            return
        if pressed(KZ, 14, 8):
            self.on_action()
            return
        if pressed(KWAIT, 10, 4):
            self.end_turn()
            return
        if pressed(KX):
            if p.inv:
                self.state = "inv"
                self.inv_sel = min(self.inv_sel, len(p.inv) - 1)
            else:
                self.msg("何も持っていない。", 13)
            return
        if pressed(KC):
            self.state = "skills"
            self.sk_sel = min(self.sk_sel, max(0, len(p.cards) - 1))
            return

    def dash_ok(self, dx, dy):
        p = self.p
        return not any(cheb(e.x, e.y, p.x, p.y) <= 4 and not e.sleep for e in self.room.enemies)

    def dash_should_stop(self):
        p = self.p
        r = self.room
        if any(cheb(e.x, e.y, p.x, p.y) <= 4 for e in r.enemies):
            return True
        if (p.x, p.y) in r.doors.values():
            return True
        for dx, dy in DIRS8:
            q = (p.x + dx, p.y + dy)
            if q in r.items or q == r.stairs or q == r.gacha:
                return True
        return False

    def on_action(self):
        p = self.p
        r = self.room
        if (p.x, p.y) == r.stairs:
            self.state = "stairs"
            self.need_release = True
            return
        tx, ty = p.x + p.fx, p.y + p.fy
        if (tx, ty) == r.gacha:
            self.state = "gacha_confirm"
            self.need_release = True
            return
        if (tx, ty) == r.chest and self.diag_ok(r, p.x, p.y, p.fx, p.fy):
            if not r.solved:
                self.msg("さくがあって開けられない。光る床を箱でうめよう", 13)
                return
            r.chest = None
            self.burst(tx, ty, 10, 20)
            sfx(7)
            self.msg("宝箱を開けた！ ガチャ限定もふくむ3枚から1枚えらべる", 10)
            self.open_cards(self.draw_cards(3, self.gacha_rates(), True), "chest")
            return
        self.player_attack()
        self.end_turn()

    def try_move(self, dx, dy):
        p = self.p
        r = self.room
        p.fx, p.fy = dx, dy
        nx, ny = p.x + dx, p.y + dy
        if not (0 <= nx < RW and 0 <= ny < RH):
            if dx and dy:
                return False
            d = "L" if nx < 0 else "R" if nx >= RW else "U" if ny < 0 else "D"
            if d in r.doors and r.doors[d] == (p.x, p.y):
                if r.locked:
                    self.msg("扉がしまっている！敵をすべてたおそう", 8)
                    return False
                if d in r.oneway_block:
                    self.msg("この扉は向こう側からしか通れない", 13)
                    return False
                self.change_room(d)
                return True
            return False
        if (nx, ny) in r.boxes and not (dx and dy):
            return self.push_box(nx, ny, dx, dy)
        if not self.can_step(r, p.x, p.y, dx, dy):
            return False
        if self.enemy_at(nx, ny):
            return False
        p.x, p.y = nx, ny
        self.on_step()
        return True

    def push_box(self, bx, by, dx, dy):
        p = self.p
        r = self.room
        tx, ty = bx + dx, by + dy
        bad = set(DOORS.values())
        for v in DOOR_IN.values():
            bad.update(v)
        if (not self.passable(r, tx, ty) or self.enemy_at(tx, ty) or (tx, ty) in bad
                or (tx, ty) in r.items or (tx, ty) in r.shop):
            return False
        r.boxes.discard((bx, by))
        r.boxes.add((tx, ty))
        p.x, p.y = bx, by
        sfx(0)
        if not r.solved and r.switches <= r.boxes:
            r.solved = True
            r.gates = set()
            self.flash_screen = 6
            sfx(7)
            self.msg("カチッ！ 宝箱のさくが開いた！（宝箱の前でZ）", 10)
        return True

    def on_step(self):
        p = self.p
        r = self.room
        pos = (p.x, p.y)
        if pos in r.items:
            it = r.items[pos]
            if it["name"] == "ギタン":
                n = it["n"] * (1 + self.ncard("goldrush"))
                p.gold += n
                del r.items[pos]
                self.msg(f"{n}ギタンを拾った。", 10)
                sfx(10)
            else:
                if self.add_item(it):
                    del r.items[pos]
                    self.msg(f"{item_label(it)}を拾った。", 7)
                    sfx(10)
                else:
                    self.msg(f"{item_label(it)}に乗った。持ち物がいっぱい。", 13)
        if pos == r.stairs:
            self.msg("階段がある。Zで降りる。", 10)
        if pos in r.shop:
            sp = r.shop[pos]
            self.shop_pos = pos
            self.state = "shop_buy"
            self.need_release = True
            self.dash = None

    def add_item(self, it):
        p = self.p
        if len(p.inv) >= INV_MAX:
            return False
        p.inv.append(it)
        return True

    def change_room(self, d):
        p = self.p
        old = self.room
        dx, dy = DIR_VEC[d]
        new = self.rooms[(old.gx + dx, old.gy + dy)]
        door = DOORS[d]
        followers = [e for e in old.enemies
                     if cheb(e.x, e.y, p.x, p.y) <= 1 and e.para <= 0 and not e.sleep and not e.boss]
        dist = self.bfs(old, door[0], door[1], 14)
        for e in list(old.enemies):
            if e in followers:
                old.enemies.remove(e)
            elif (e.para <= 0 and not e.sleep and not e.boss and not e.star
                  and (e.x, e.y) in dist and dist[(e.x, e.y)] <= 12):
                old.enemies.remove(e)
                new.pending.append([dist[(e.x, e.y)] + 1, e, OPP[d]])
        for pd in old.pending:
            new.pending.append([pd[0] + 8, pd[1], OPP[d]])
        old.pending = []
        if old.kind == "gimmick" and not old.solved:
            old.boxes = set(old.boxes_init)
        self.slide = dict(t=0, d=d, old=old)
        self.room = new
        first = not new.visited
        new.visited = True
        p.x, p.y = DOORS[OPP[d]]
        p.rx, p.ry = p.x * TS, p.y * TS
        for e in followers:
            pos = self.nearest_free(new, p.x, p.y)
            if pos:
                e.x, e.y = pos
                new.enemies.append(e)
        for e in new.enemies:
            e.rx, e.ry = e.x * TS, e.y * TS
        self.projs = []
        if followers:
            self.msg(f"{followers[0].kind}がついてきた！", 8)
        if new.boss_room and first:
            self.msg("ゆめくい「…だれだ、わたしの眠りをじゃまするのは」", 8)
            self.msg("ゆめくいは物理と魔法、どちらかが効かない体に入れかわる！", 9)
            sfx(14)
        if first:
            if new.kind == "shop":
                self.msg("ショップだ！ 品物の上に乗ると買える", 10)
            elif new.kind == "dark":
                self.msg("暗い部屋だ…。まわりしか見えない", 13)
            elif new.kind == "gimmick":
                self.msg("箱を押して、光る床を全部うめよう（出入りでやりなおし）", 11)
        if new.kind == "mhouse" and new.mh_state == 0:
            self.start_mhouse(new)
        self.on_step()

    def start_mhouse(self, r):
        r.mh_state = 1
        r.locked = True
        f = self.floor
        n = 5 + f // 5
        pool = enemy_pool(f)
        p = self.p
        for _ in range(n):
            for _t in range(20):
                pos = self.free_tile(r)
                if pos and cheb(pos[0], pos[1], p.x, p.y) >= 3:
                    r.enemies.append(self.spawn(wchoice(pool), pos, f))
                    break
        for _ in range(3):
            pos = self.free_tile(r)
            if pos:
                r.items[pos] = make_item(wchoice(item_pool(f)))
        self.msg("モンスターハウスだ！ 扉がしまった！", 8)
        self.shake = 10
        sfx(14)

    def check_mhouse(self):
        r = self.room
        if r.locked and not r.enemies and not r.pending:
            r.locked = False
            r.mh_state = 2
            self.msg("モンスターハウスをせいはした！ 扉が開いた", 10)
            sfx(7)
            for _ in range(2):
                pos = self.free_tile(r)
                if pos:
                    g = make_item("ギタン")
                    g["n"] = int(g["n"] * (2 + 0.3 * self.floor))
                    r.items[pos] = g

    def nearest_free(self, r, x, y):
        dist = self.bfs(r, x, y, 10)
        for pos, d in sorted(dist.items(), key=lambda kv: kv[1]):
            if d == 0:
                continue
            if self.enemy_at(*pos, r) or pos == (self.p.x, self.p.y):
                continue
            return pos
        return None

    # ---------------------------------------------------------------- 戦闘
    def facing_enemy(self):
        p = self.p
        if not self.diag_ok(self.room, p.x, p.y, p.fx, p.fy):
            return None
        return self.enemy_at(p.x + p.fx, p.y + p.fy)

    def wake(self, e):
        e.sleep = False

    def player_attack(self):
        p = self.p
        p.lx, p.ly = p.fx * 5, p.fy * 5
        e = self.facing_enemy()
        if not e:
            sfx(0)
            return
        st = self.stats()
        hits = 2 if random.random() < 0.3 * self.ncard("renda") else 1
        immune_said = False
        for h in range(hits):
            if e.hp <= 0 or e not in self.room.enemies:
                break
            if random.random() < 0.06:
                self.popup(e.x, e.y, "MISS", 13)
                sfx(0)
                self.wake(e)
                continue
            dmg = 0
            crit = False
            if e.phys:
                dmg = max(1, round(st["atk"] * random.uniform(0.87, 1.13) - e.df))
                if random.random() < 0.25 * self.ncard("crit"):
                    dmg *= 3
                    crit = True
            elif not immune_said:
                self.msg(f"{e.kind}に物理攻撃は効かない！", 13)
                immune_said = True
            if self.ncard("magsword") and e.mag:
                dmg += max(1, st["mag"] * self.ncard("magsword"))
            if dmg <= 0:
                self.popup(e.x, e.y, "×", 13)
                sfx(2)
                self.wake(e)
                continue
            if crit:
                self.msg("会心の一撃！", 10)
                self.shake = 6
            self.hurt_enemy(e, dmg, 10 if crit else 7)
            if e.phys and self.ncard("drain"):
                heal = max(1, dmg * self.ncard("drain") // 4)
                p.hp = min(st["mhp"], p.hp + heal)
        if hits == 2 and e.hp > 0:
            self.msg("れんげき！", 11)

    def hurt_enemy(self, e, dmg, col=7, delay=0):
        if e not in self.room.enemies:
            return
        self.wake(e)
        e.hp -= dmg
        e.flash = 8 + delay
        self.popup(e.x, e.y, dmg, col, delay)
        sfx(1)
        if e.hp <= 0:
            self.kill_enemy(e, delay)

    def kill_enemy(self, e, delay=0):
        r = self.room
        if e in r.enemies:
            r.enemies.remove(e)
        f = self.floor
        self.msg(f"{e.kind}をたおした！", 10)
        self.burst(e.x, e.y, 10 if e.boss else 7, 30 if e.ai == "boss" else (16 if e.boss else 10), delay)
        sfx(3)
        self.kills += 1
        self.kill_prog += 1 + (2 if e.boss or e.star else 0)
        while self.kill_prog >= self.kill_need:
            self.kill_prog -= self.kill_need
            self.kill_need = min(7, self.kill_need + 1)
            self.pending_cards += 1
        if not self.pending_cards and e.ai != "boss":
            self.msg(f"カードまで あと{self.kill_need - self.kill_prog}体", 11)
        if e.ai == "boss":
            self.shake = 20
            self.flash_screen = 14
            r.stairs = (e.x, e.y)
            r.enemies.clear()
            self.msg("ゆめくいは消えていった…。光の階段があらわれた！", 10)
            return
        drop = None
        if e.loot:
            drop = make_item("ギタン")
            drop["n"] = e.loot
        elif e.boss or e.star:
            drop = make_item(random.choice(RARE_GEAR + ["弟切草", "ドラゴン草", "いのちの草"]))
        elif random.random() < 0.45:
            drop = make_item("ギタン")
            drop["n"] = int(random.randint(6, 18) * (1 + 0.25 * (f - 1)))
        elif random.random() < 0.10:
            drop = make_item(wchoice(item_pool(f)))
        if drop:
            pos = (e.x, e.y)
            if pos in r.items or pos == r.stairs:
                pos = None
                for dx, dy in DIRS8:
                    q = (e.x + dx, e.y + dy)
                    if self.passable(r, *q) and q not in r.items and q != r.stairs:
                        pos = q
                        break
            if pos:
                r.items[pos] = drop

    def damage_player(self, dmg, cause, evadable=True):
        p = self.p
        if evadable and random.random() < 0.12 * self.ncard("evade"):
            self.popup(p.x, p.y, "かわした", 11)
            return 0
        dmg = max(1, dmg - 2 * self.ncard("skin"))
        p.hp -= dmg
        p.flash = 10
        self.shake = 4
        self.popup(p.x, p.y, dmg, 8)
        sfx(8)
        if p.hp <= 0:
            if "soul" in p.cards:
                p.cards.remove("soul")
                p.hp = self.stats()["mhp"] // 2
                self.flash_screen = 12
                self.burst(p.x, p.y, 10, 24)
                self.msg("ふたつめのいのちが燃えた！ナポは立ち上がった！", 10)
                sfx(9)
                return dmg
            p.hp = 0
            self.game_over(cause)
        return dmg

    def game_over(self, cause):
        if self.state in ("gameover", "clear"):
            return
        self.state = "gameover"
        self.cause = cause
        self.anim_t = 0
        self.dash = None
        self.best[self.dg_idx] = max(self.best[self.dg_idx], self.floor)

    # ---------------------------------------------------------------- ターン
    def end_turn(self):
        if self.state in ("gameover", "clear", "title"):
            return
        self.enemies_act()
        if self.state == "gameover":
            return
        self.check_mhouse()
        self.turn += 1
        self.fturn += 1
        p = self.p
        st = self.stats()
        step = 20 if self.ncard("hara") else 10
        if self.turn % step == 0 and p.full > 0:
            p.full -= 1
            if p.full == 20:
                self.msg("おなかが減ってきた…", 9)
            elif p.full == 0:
                self.msg("おなかがペコペコで倒れそうだ！", 8)
        if p.full <= 0:
            self.damage_player(1, "おなかがへって倒れた", False)
            if self.state == "gameover":
                return
        else:
            sp = 1 + 2 * self.ncard("spirit")
            p.regen += st["mhp"] / 150 * sp
            while p.regen >= 1:
                p.regen -= 1
                p.hp = min(st["mhp"], p.hp + 1)
        p.mpregen += 0.2 * (1 + 2 * self.ncard("spirit") + 2 * self.ncard("medit"))
        while p.mpregen >= 1:
            p.mpregen -= 1
            p.mp = min(st["mmp"], p.mp + 1)
        r = self.room
        for pd in r.pending:
            pd[0] -= 1
        for pd in list(r.pending):
            if pd[0] <= 0:
                x, y = DOORS[pd[2]]
                if (x, y) != (p.x, p.y) and not self.enemy_at(x, y):
                    e = pd[1]
                    e.x, e.y = x, y
                    e.rx, e.ry = x * TS, y * TS
                    r.enemies.append(e)
                    r.pending.remove(pd)
                    self.msg(f"{e.kind}が追いかけてきた！", 8)
        if (self.fturn % 45 == 0 and random.random() < 0.55 and len(r.enemies) < 6
                and r.doors and not r.boss_room and r.kind not in ("shop", "gimmick") and not r.locked):
            d = random.choice(list(r.doors.keys()))
            x, y = DOORS[d]
            if (x, y) != (p.x, p.y) and not self.enemy_at(x, y) and cheb(x, y, p.x, p.y) > 2:
                e = Enemy(wchoice(enemy_pool(self.floor)), x, y, self.floor)
                r.enemies.append(e)
                self.msg(f"{e.kind}が部屋に入ってきた！", 9)
        left = FLOOR_TURN_LIMIT - self.fturn
        if left == 200:
            self.msg("遠くで風の音がする…（あと200ターン）", 9)
        elif left == 100:
            self.msg("風が強まってきた。階段を急ごう！（あと100ターン）", 9)
        elif left == 30:
            self.shake = 12
            self.msg("風がうなる！飛ばされるぞ！（あと30ターン）", 8)
        elif left <= 0:
            self.game_over("風に吹き飛ばされた")
            return
        if self.pending_cards > 0 and self.state == "play":
            self.pending_cards -= 1
            self.start_card_intro(self.draw_cards(3, self.level_rates(), False), "level")

    def start_card_intro(self, ids, src):
        """敵をたおした直後にいきなりカード画面へ飛ばず、「目標たっせい！」の間を挟む。"""
        self.ci_ids = ids
        self.ci_src = src
        self.ci_t = 0
        self.state = "card_intro"
        self.need_release = True
        self.dash = None
        self.flash_screen = 6
        sfx(10)

    def upd_card_intro(self):
        self.ci_t += 1
        if self.ci_t >= 55 or (self.ci_t > 18 and pressed(KZ)):
            self.open_cards(self.ci_ids, self.ci_src)

    def draw_card_intro(self):
        k = min(1.0, self.ci_t / 8)
        lines = ["たおした数が たまった！", "★ カードがもらえる ★"]
        w = max(tw(s) for s in lines) + 28
        h = int(46 * k)
        x = (W - w) // 2
        y = ROOM_Y + 84
        pyxel.rect(x, y, w, h, 1)
        pyxel.rectb(x, y, w, h, 10 if (self.ci_t // 6) % 2 else 7)
        if k >= 1.0:
            txts((W - tw(lines[0])) // 2, y + 10, lines[0], 7)
            txts((W - tw(lines[1])) // 2, y + 26, lines[1], 10)

    def enemies_act(self):
        p = self.p
        r = self.room
        if not r.enemies:
            return
        dist = self.bfs(r, p.x, p.y, 40)
        for e in list(r.enemies):
            if e not in r.enemies or e.hp <= 0:
                continue
            if e.para > 0:
                e.para -= 1
                continue
            if e.sleep:
                if cheb(e.x, e.y, p.x, p.y) <= 2 and random.random() < 0.5:
                    e.sleep = False
                    self.popup(e.x, e.y, "!", 10)
                continue
            if e.ai == "boss":
                self.boss_tick(e)
            if e.slow and self.turn % 2 == 1:
                continue
            for _ in range(e.acts):
                if self.state == "gameover" or e not in r.enemies:
                    break
                self.enemy_step(e, dist)

    def boss_tick(self, e):
        e.timer += 1
        if e.timer % 5 == 1:
            e.phase = 1 - e.phase
            if e.phase == 1:
                e.phys, e.mag = False, True
                self.msg("ゆめくいの体がゆらめいた！物理が効かない！", 9)
            else:
                e.phys, e.mag = True, False
                self.msg("ゆめくいの体がかたくなった！魔法が効かない！", 6)
            self.flash_screen = 4
        r = self.room
        if e.timer % 11 == 0 and len(r.enemies) < 4:
            pos = self.nearest_free(r, e.x, e.y)
            if pos:
                if self.last >= 30:
                    kind = random.choice(["かげ武者", "アークリッチ", "ヘルバット", "たたりがめ"])
                else:
                    kind = random.choice(["ぼうれい武者", "ガイコツまどう", "キラーバット", "こうらがめ"])
                m = self.spawn(kind, pos, self.floor)
                r.enemies.append(m)
                self.msg(f"ゆめくいは悪夢から{kind}を呼び出した！", 8)
                self.burst(pos[0], pos[1], 2, 10)

    def clear_line(self, r, sx, sy, tx, ty):
        dx, dy = tx - sx, ty - sy
        if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
            return False
        ux, uy = sign(dx), sign(dy)
        x, y = sx, sy
        for _ in range(max(abs(dx), abs(dy))):
            if not self.diag_ok(r, x, y, ux, uy):
                return False
            x, y = x + ux, y + uy
            if (x, y) == (tx, ty):
                return True
            if self.is_wall(r, x, y) or self.enemy_at(x, y) or (x, y) == r.gacha:
                return False
        return False

    def enemy_shot(self, e, col, dmg, name, cause):
        p = self.p
        self.projs.append(dict(x=e.x * TS + 8, y=ROOM_Y + e.y * TS + 8,
                               tx=p.x * TS + 8, ty=ROOM_Y + p.y * TS + 8,
                               col=col, kind="ball", fx=0, fy=0))
        sfx(13)
        self.msg(f"{e.kind}は{name}！", 8)
        self.damage_player(dmg, cause)

    def enemy_step(self, e, dist):
        p = self.p
        r = self.room
        dx, dy = p.x - e.x, p.y - e.y
        adj = cheb(e.x, e.y, p.x, p.y) == 1 and self.diag_ok(r, e.x, e.y, dx, dy)
        if dx:
            e.face = 1 if dx > 0 else -1
        # 遠距離
        if not adj and e.ai in ("ranged", "breath") and cheb(e.x, e.y, p.x, p.y) <= 6:
            if self.clear_line(r, e.x, e.y, p.x, p.y) and random.random() < (0.5 if e.ai == "ranged" else 0.35):
                if e.ai == "ranged":
                    self.enemy_shot(e, 2, max(1, e.atk + random.randint(-1, 1)), "魔法の弾をはなった",
                                    f"{e.kind}の魔法にやられた")
                else:
                    self.enemy_shot(e, 8, 10 + self.floor, "炎をはいた", "ドラゴンの炎にやられた")
                return
        if adj and not (e.erratic and random.random() < e.erratic * 0.5):
            if e.ai == "thief" and p.gold > 0 and not e.loot:
                n = max(1, min(p.gold, random.randint(p.gold // 3, p.gold // 2 + 10)))
                p.gold -= n
                e.loot = n
                self.msg(f"{e.kind}に{n}ギタンぬすまれた！", 8)
                pos = self.free_tile(r)
                if pos:
                    self.burst(e.x, e.y, 3, 8)
                    e.x, e.y = pos
                    e.rx, e.ry = pos[0] * TS, pos[1] * TS
                return
            e.lx, e.ly = dx * 5, dy * 5
            if random.random() < 0.1:
                self.popup(p.x, p.y, "MISS", 13)
                return
            st = self.stats()
            dmg = max(1, round(e.atk * random.uniform(0.87, 1.13) - st["df"] * 0.5))
            got = self.damage_player(dmg, f"{e.kind}にやられた")
            if got and self.state != "gameover" and e.phys and random.random() < 0.3 * self.ncard("counter"):
                self.msg("はんげき！", 11)
                self.hurt_enemy(e, got, 11)
            return
        flee = e.ai == "thief" and e.loot
        cur = dist.get((e.x, e.y), 999)
        opts = []
        for ddx, ddy in DIRS8:
            nx, ny = e.x + ddx, e.y + ddy
            if not self.can_step(r, e.x, e.y, ddx, ddy):
                continue
            if self.enemy_at(nx, ny) or (nx, ny) == (p.x, p.y):
                continue
            if r.locked and (nx, ny) in DOORS.values():
                continue
            dv = dist.get((nx, ny), 999)
            if flee:
                dv = -dv
            # シレン式：同じ近さなら、プレイヤーと縦か横に並ぶマスを優先する
            opts.append((dv, self.align_rank(nx, ny), random.random(), nx, ny, ddx))
        if not opts:
            return
        if e.erratic and random.random() < e.erratic:
            o = random.choice(opts)
        else:
            opts.sort()
            o = opts[0]
            curv = -cur if flee else cur
            if o[0] > curv:
                return
            if o[0] == curv and not (o[1] < self.align_rank(e.x, e.y)) and random.random() < 0.5:
                return
        e.x, e.y = o[3], o[4]
        if o[5]:
            e.face = 1 if o[5] > 0 else -1

    def align_rank(self, x, y):
        p = self.p
        if x == p.x or y == p.y:
            return 0 if cheb(x, y, p.x, p.y) == 1 else 1
        return 2

    # ---------------------------------------------------------------- カード
    def level_rates(self):
        f = self.floor
        r3 = min(18, 3 + 1.5 * f)
        r1 = max(40, 75 - 4 * f)
        return (r1, 100 - r1 - r3, r3)

    def gacha_rates(self):
        f = self.floor
        r3 = min(45, 15 + 3.5 * f)
        r1 = max(5, 35 - 4 * f)
        return (r1, 100 - r1 - r3, r3)

    def card_weight(self, cid):
        c = CARDS[cid]
        w = c["w"]
        star = self.dg["star"]
        if cid == "hoshi" and star - 3 <= self.floor <= star:
            w *= 4
        if c["t"] == "item":
            w *= 0.6
        return w

    def draw_cards(self, n, rates, gacha, items=True):
        pool = [k for k, c in CARDS.items() if (gacha or not c["g"])]
        if gacha or not items:
            pool = [k for k in pool if CARDS[k]["t"] != "item"]
        res = []
        guard = 0
        while len(res) < n and guard < 300:
            guard += 1
            rr = wchoice([(1, rates[0]), (2, rates[1]), (3, rates[2])])
            cands = [(k, self.card_weight(k)) for k in pool if CARDS[k]["r"] == rr and k not in res]
            if gacha:
                cands = [(k, w * (3 if CARDS[k]["g"] else 1)) for k, w in cands]
            if cands:
                res.append(wchoice(cands))
        return res

    def open_cards(self, ids, src):
        self.cp_ids = ids
        self.cp_sel = len(ids) // 2 if len(ids) == 3 else 0
        self.cp_src = src
        self.cp_t = 0
        self.state = "cards"
        self.need_release = True
        self.dash = None
        sfx(4)

    def upd_cards(self):
        self.cp_t += 1
        n = len(self.cp_ids)
        if menu_p(KL):
            self.cp_sel = (self.cp_sel - 1) % n
        if menu_p(KR):
            self.cp_sel = (self.cp_sel + 1) % n
        if pressed(KZ):
            cid = self.cp_ids[self.cp_sel]
            if CARDS[cid]["t"] == "item" or len(self.p.cards) < CARD_MAX:
                self.pay_shop()
                self.take_card(cid)
                self.after_cards()
            else:
                self.dc_new = cid
                self.dc_sel = CARD_MAX
                self.state = "discard"
                self.need_release = True
        elif pressed(KX) and self.cp_src != "start":
            self.msg("買うのをやめた。" if self.cp_src == "shop" else "カードを見送った。", 13)
            self.shop_pending = None
            self.after_cards()

    def pay_shop(self):
        if self.cp_src == "shop" and self.shop_pending:
            pos, price = self.shop_pending
            self.p.gold -= price
            self.room.shop.pop(pos, None)
            self.msg(f"{price}ギタンはらった。まいど！", 10)
        self.shop_pending = None

    def take_card(self, cid):
        c = CARDS[cid]
        p = self.p
        fx = c["fx"]
        if c["t"] == "item":
            if "gold" in fx:
                p.gold += fx["gold"]
                self.msg(f"{fx['gold']}ギタンを手に入れた！", 10)
            else:
                for _ in range(fx["n"]):
                    one = make_item(fx["give"])
                    if not self.add_item(one):
                        self.room.items.setdefault((p.x, p.y), one)
                self.msg(f"「{c['name']}」で{fx['give']}を手に入れた！", 10)
            sfx(10)
            return
        p.cards.append(cid)
        if "mhp" in fx:
            p.hp += fx["mhp"]
        if "mmp" in fx:
            p.mp += fx["mmp"]
        self.msg(f"カード「{c['name']}」を手に入れた！", RARITY_COL[c["r"]] if c["r"] > 1 else 7)

    def after_cards(self):
        self.clamp_player()
        self.state = "play"
        self.need_release = True
        if self.pending_cards > 0:
            self.pending_cards -= 1
            self.start_card_intro(self.draw_cards(3, self.level_rates(), False), "level")

    def upd_discard(self):
        n = CARD_MAX + 1
        if menu_p(KU):
            self.dc_sel = (self.dc_sel - 1) % n
        if menu_p(KD):
            self.dc_sel = (self.dc_sel + 1) % n
        if pressed(KZ):
            if self.dc_sel == CARD_MAX:
                self.msg(f"「{CARDS[self.dc_new]['name']}」はあきらめた。", 13)
                self.shop_pending = None
            else:
                old = self.p.cards.pop(self.dc_sel)
                self.msg(f"「{CARDS[old]['name']}」をすてた。", 13)
                self.pay_shop()
                self.take_card(self.dc_new)
            self.after_cards()
        elif pressed(KX):
            self.state = "cards"
            self.need_release = True

    # ---------------------------------------------------------------- わざ
    def upd_skills(self):
        p = self.p
        if pressed(KX) or pressed(KC):
            self.state = "play"
            self.need_release = True
            return
        if not p.cards:
            return
        n = len(p.cards)
        self.sk_sel = min(self.sk_sel, n - 1)
        if menu_p(KU):
            self.sk_sel = (self.sk_sel - 1) % n
        if menu_p(KD):
            self.sk_sel = (self.sk_sel + 1) % n
        if pressed(KZ):
            cid = p.cards[self.sk_sel]
            c = CARDS[cid]
            if c["t"] != "skill":
                return
            cost = c["fx"]["mp"]
            if p.mp < cost:
                self.msg("MPが足りない。", 13)
                sfx(2)
                return
            self.state = "play"
            self.need_release = True
            p.mp -= cost
            self.use_skill(cid)
            self.end_turn()

    def line_target(self, maxd=12):
        p = self.p
        r = self.room
        x, y = p.x, p.y
        dx, dy = p.fx, p.fy
        for _ in range(maxd):
            if not self.diag_ok(r, x, y, dx, dy):
                return (x, y), None
            nx, ny = x + dx, y + dy
            if self.is_wall(r, nx, ny) or (nx, ny) == r.gacha:
                return (x, y), None
            e = self.enemy_at(nx, ny)
            if e:
                return (nx, ny), e
            x, y = nx, ny
        return (x, y), None

    def shoot(self, end, col, kind="ball"):
        p = self.p
        d = max(1, cheb(p.x, p.y, end[0], end[1]))
        self.projs.append(dict(x=p.x * TS + 8, y=ROOM_Y + p.y * TS + 8,
                               tx=end[0] * TS + 8, ty=ROOM_Y + end[1] * TS + 8,
                               col=col, kind=kind, fx=p.fx, fy=p.fy))
        return int(d * TS / 9)

    def use_skill(self, cid):
        p = self.p
        st = self.stats()
        name = CARDS[cid]["name"]
        self.msg(f"ナポは{name}をつかった！", 12)
        sfx(11)
        if cid == "fire":
            end, e = self.line_target()
            delay = self.shoot(end, 9)
            if e:
                if e.mag:
                    self.hurt_enemy(e, max(1, round((st["mag"] * 2 + 4) * random.uniform(0.9, 1.1))), 9, delay)
                else:
                    self.popup(e.x, e.y, "×", 13, delay)
                    self.msg(f"{e.kind}に魔法は効かない！", 13)
                    self.wake(e)
        elif cid == "heal":
            v = st["mag"] * 3 + 12
            p.hp = min(st["mhp"], p.hp + v)
            self.popup(p.x, p.y, f"+{v}", 11)
            self.burst(p.x, p.y, 11, 8)
            sfx(9)
        elif cid in ("thunder", "flare"):
            self.flash_screen = 6 if cid == "thunder" else 10
            targets = list(self.room.enemies)
            for e in targets:
                if not e.mag:
                    self.popup(e.x, e.y, "×", 13)
                    self.wake(e)
                    continue
                base = st["mag"] + 6 if cid == "thunder" else st["mag"] * 2 + 16
                self.hurt_enemy(e, max(1, round(base * random.uniform(0.9, 1.1))), 10)
            if not targets:
                self.msg("しかし敵はいなかった。", 13)
        elif cid == "pierce":
            p.lx, p.ly = p.fx * 7, p.fy * 7
            r = self.room
            x, y = p.x, p.y
            for _ in range(2):
                if not self.diag_ok(r, x, y, p.fx, p.fy):
                    break
                x, y = x + p.fx, y + p.fy
                if self.is_wall(r, x, y):
                    break
                e = self.enemy_at(x, y)
                if e:
                    if e.phys:
                        self.hurt_enemy(e, max(1, round(st["atk"] * 1.3 * random.uniform(0.9, 1.1) - e.df)), 7)
                    else:
                        self.popup(e.x, e.y, "×", 13)
                        self.wake(e)
        elif cid == "hoshi":
            p.lx, p.ly = p.fx * 7, p.fy * 7
            e = self.facing_enemy()
            if not e:
                self.msg("前には誰もいない。", 13)
            else:
                dmg = max(1, round(st["atk"] * random.uniform(0.9, 1.1)))
                if e.star:
                    dmg *= 4
                    self.msg("星がくだけ散る！", 10)
                    self.shake = 8
                self.hurt_enemy(e, dmg, 10)
        elif cid == "warp":
            r = self.room
            best = None
            for _ in range(30):
                pos = self.free_tile(r)
                if not pos:
                    break
                sc = min([cheb(pos[0], pos[1], e.x, e.y) for e in r.enemies] or [99])
                if best is None or sc > best[0]:
                    best = (sc, pos)
            if best:
                self.burst(p.x, p.y, 12, 10)
                p.x, p.y = best[1]
                p.rx, p.ry = p.x * TS, p.y * TS
                self.burst(p.x, p.y, 12, 10)
                self.on_step()
        elif cid == "steal":
            e = self.facing_enemy()
            if not e:
                self.msg("前には誰もいない。", 13)
            elif e.stolen or random.random() > 0.6:
                self.msg("ぬすむのに失敗した！", 13)
                self.wake(e)
            else:
                e.stolen = True
                it = make_item(wchoice(item_pool(self.floor)))
                if self.add_item(it):
                    self.msg(f"{e.kind}から{item_label(it)}をぬすんだ！", 10)
                    sfx(10)
                else:
                    self.msg("持ち物がいっぱいだ。", 13)

    # ---------------------------------------------------------------- 道具
    def item_actions(self, it):
        k = ITEMS[it["name"]]["k"]
        if k in ("weapon", "shield"):
            return ["はずす" if it["eq"] else "そうび", "なげる", "おく"]
        return [VERB[k], "なげる", "おく"]

    def upd_inv(self):
        p = self.p
        if not p.inv:
            self.state = "play"
            return
        n = len(p.inv)
        self.inv_sel = min(self.inv_sel, n - 1)
        if menu_p(KU):
            self.inv_sel = (self.inv_sel - 1) % n
        if menu_p(KD):
            self.inv_sel = (self.inv_sel + 1) % n
        if pressed(KX):
            self.state = "play"
            self.need_release = True
        elif pressed(KC):
            self.sort_inv()
        elif pressed(KZ):
            self.act_sel = 0
            self.state = "inv_act"
            self.need_release = True

    def upd_inv_act(self):
        it = self.p.inv[self.inv_sel]
        acts = self.item_actions(it)
        if menu_p(KU):
            self.act_sel = (self.act_sel - 1) % len(acts)
        if menu_p(KD):
            self.act_sel = (self.act_sel + 1) % len(acts)
        if pressed(KX):
            self.state = "inv"
            self.need_release = True
        elif pressed(KZ):
            a = acts[self.act_sel]
            self.state = "play"
            self.need_release = True
            if self.do_item(it, a):
                self.end_turn()

    def remove_item(self, it):
        if it in self.p.inv:
            self.p.inv.remove(it)
        self.inv_sel = max(0, min(self.inv_sel, len(self.p.inv) - 1))

    def do_item(self, it, a):
        p = self.p
        r = self.room
        st = self.stats()
        name = it["name"]
        d = ITEMS[name]
        k = d["k"]
        if a in ("そうび", "はずす"):
            if a == "そうび":
                for o in p.inv:
                    if ITEMS[o["name"]]["k"] == k:
                        o["eq"] = False
                it["eq"] = True
                self.msg(f"{name}をそうびした。", 7)
            else:
                it["eq"] = False
                self.msg(f"{name}をはずした。", 7)
            self.clamp_player()
            return True
        if a == "おく":
            if (p.x, p.y) in r.items or (p.x, p.y) == r.stairs:
                self.msg("ここには置けない。", 13)
                return False
            it["eq"] = False
            self.remove_item(it)
            r.items[(p.x, p.y)] = it
            self.msg(f"{item_label(it)}を置いた。", 7)
            return True
        if a in ("なげる", "うつ"):
            self.throw(it)
            return True
        if k == "herb":
            p.hp = min(st["mhp"], p.hp + d["v"])
            self.popup(p.x, p.y, f"+{d['v']}", 11)
            self.burst(p.x, p.y, 11, 8)
            sfx(9)
            self.msg(f"{name}をのんだ。HPが回復した。", 11)
            self.remove_item(it)
            return True
        if k == "dgrass":
            self.remove_item(it)
            self.msg(f"{name}をのんだ！ナポは炎をはいた！", 9)
            end, e = self.line_target()
            delay = self.shoot(end, 8)
            sfx(13)
            if e:
                self.hurt_enemy(e, d["v"], 9, delay)
            return True
        if k == "food":
            p.full = min(100, p.full + d["v"])
            sfx(9)
            self.msg(f"{name}をたべた。おなかがふくれた。", 11)
            self.remove_item(it)
            return True
        if k == "seed":
            self.remove_item(it)
            if d["v"] == "mhp":
                p.bonus_mhp += 5
                p.hp += 5
                self.msg(f"{name}をのんだ。最大HPが5上がった！", 11)
            else:
                p.bonus_atk += 1
                self.msg(f"{name}をのんだ。攻撃力が1上がった！", 11)
            self.burst(p.x, p.y, 10, 10)
            sfx(9)
            return True
        if k == "scroll":
            self.remove_item(it)
            self.msg(f"{name}をよんだ！", 12)
            self.flash_screen = 6
            targets = list(r.enemies)
            dmg = int((d["v"] + self.floor) * (1 + 0.5 * self.ncard("staffer")))
            for e in targets:
                self.hurt_enemy(e, dmg, 7)
            if not targets:
                self.msg("しかし何も起こらなかった。", 13)
            return True
        if k == "staff":
            p.lx, p.ly = p.fx * 3, p.fy * 3
            if it["n"] <= 0:
                self.msg(f"{name}をふった。しかし何も起こらない。", 13)
                return True
            it["n"] -= 1
            end, e = self.line_target()
            delay = self.shoot(end, {"blow": 12, "para": 10, "bolt": 7}[d["v"]])
            sfx(11)
            self.msg(f"{name}をふった！", 7)
            if e:
                if d["v"] == "bolt":
                    dmg = int((12 + self.floor) * (1 + 0.5 * self.ncard("staffer")))
                    self.hurt_enemy(e, dmg, 10, delay)
                elif e.ai == "boss":
                    self.msg("ゆめくいには効かなかった！", 13)
                elif d["v"] == "para":
                    e.para = 15
                    e.sleep = False
                    self.msg(f"{e.kind}はかなしばりにあった！", 10)
                    self.popup(e.x, e.y, "STOP", 10, delay)
                else:
                    self.blow(e)
            return True
        return False

    def blow(self, e):
        p = self.p
        r = self.room
        dx, dy = p.fx, p.fy
        moved = 0
        hit = False
        while moved < 10:
            nx, ny = e.x + dx, e.y + dy
            if not self.can_step(r, e.x, e.y, dx, dy) or self.enemy_at(nx, ny) or (nx, ny) == (p.x, p.y):
                hit = True
                break
            e.x, e.y = nx, ny
            moved += 1
        self.msg(f"{e.kind}をふきとばした！", 10)
        if hit:
            self.hurt_enemy(e, 5, 7, 6)

    def throw(self, it):
        p = self.p
        r = self.room
        p.lx, p.ly = p.fx * 4, p.fy * 4
        it["eq"] = False
        self.remove_item(it)
        end, e = self.line_target(10)
        delay = self.shoot(end, 7, "item")
        sfx(0)
        if e and random.random() < 0.9:
            self.hurt_enemy(e, 2, 7, delay)
            return
        x, y = end
        if e:
            self.popup(e.x, e.y, "MISS", 13, delay)
            self.wake(e)
            x, y = e.x - p.fx, e.y - p.fy
        spots = [(x, y)] + [(x + a, y + b) for a, b in DIRS8]
        for sp in spots:
            if self.passable(r, *sp) and sp not in r.items and sp != r.stairs and sp not in r.shop:
                r.items[sp] = it
                return
        self.msg(f"{item_label(it)}はどこかへ消えた。", 13)

    def sort_inv(self):
        p = self.p
        p.inv.sort(key=lambda it: (0 if it["eq"] else 1, SORT_ORDER.get(ITEMS[it["name"]]["k"], 8),
                                   -ITEMS[it["name"]]["v"] if isinstance(ITEMS[it["name"]]["v"], int) else 0,
                                   it["name"]))
        self.inv_sel = 0
        self.msg("もちものをせいとんした。", 13)

    # ---------------------------------------------------------------- ショップ
    def upd_shop_buy(self):
        r = self.room
        sp = r.shop.get(self.shop_pos)
        if not sp:
            self.state = "play"
            return
        if pressed(KX):
            self.state = "play"
            self.need_release = True
        elif pressed(KZ):
            self.need_release = True
            if self.p.gold < sp["price"]:
                self.msg("ギタンが足りない。", 13)
                sfx(2)
                self.state = "play"
            elif "item" in sp:
                if len(self.p.inv) >= INV_MAX:
                    self.msg("持ち物がいっぱいだ。", 13)
                else:
                    self.p.gold -= sp["price"]
                    self.add_item(sp["item"])
                    r.shop.pop(self.shop_pos)
                    self.msg(f"{item_label(sp['item'])}を{sp['price']}ギタンで買った。まいど！", 10)
                    sfx(10)
                self.state = "play"
            else:
                self.shop_pending = (self.shop_pos, sp["price"])
                self.open_cards([sp["card"]], "shop")

    # ---------------------------------------------------------------- ガチャ
    def upd_gacha_confirm(self):
        if pressed(KX):
            self.state = "play"
            self.need_release = True
        elif pressed(KZ):
            p = self.p
            cost = gacha_cost(self.floor)
            if p.gold < cost:
                self.msg(f"ギタンが足りない。（{cost}ギタン必要）", 13)
                sfx(2)
                self.state = "play"
                self.need_release = True
                return
            p.gold -= cost
            if random.random() < 0.15:
                pool = ["弟切草", "大きなおにぎり", "ドラゴン草", "いのちの草", "ちからの草"] + RARE_GEAR
                self.g_item = make_item(random.choice(pool))
                self.g_card = None
                self.g_rar = 2
            else:
                self.g_item = None
                self.g_card = self.draw_cards(1, self.gacha_rates(), True)[0]
                self.g_rar = CARDS[self.g_card]["r"]
            self.g_t = 0
            self.state = "gacha"
            self.need_release = True

    def upd_gacha(self):
        self.g_t += 1
        t = self.g_t
        if t < 34 and t % 6 == 0:
            sfx(5)
        if t == 78:
            sfx(7 if self.g_rar >= 3 else 6)
            self.flash_screen = 8 if self.g_rar >= 3 else 4
            col = RARITY_COL[self.g_rar]
            for _ in range(40 if self.g_rar >= 3 else 20):
                a = random.uniform(0, 360)
                s = random.uniform(1, 4)
                self.parts.append(dict(x=W / 2, y=126, vx=pyxel.cos(a) * s,
                                       vy=pyxel.sin(a) * s - 1, col=random.choice([col, 7, col]),
                                       life=random.randint(20, 40), d=0))
        if pressed(KZ) and not self.need_release:
            if t < 78:
                self.g_t = 77
                return
            if t > 82:
                self.finish_gacha()

    def finish_gacha(self):
        if self.g_card:
            self.open_cards([self.g_card], "gacha")
        else:
            it = self.g_item
            if self.add_item(it):
                self.msg(f"ガチャから{item_label(it)}が出た！", 10)
            else:
                self.room.items.setdefault((self.p.x, self.p.y), it)
                self.msg(f"ガチャから{item_label(it)}が出た！（足元に置いた）", 10)
            self.state = "play"
            self.need_release = True

    def upd_stairs(self):
        if pressed(KX):
            self.state = "play"
            self.need_release = True
        elif pressed(KZ):
            sfx(12)
            if self.floor >= self.last:
                self.state = "clear"
                self.anim_t = 0
                self.best[self.dg_idx] = self.last + 1
            else:
                self.state = "play"
                self.need_release = True
                self.next_floor()

    # ================================================================ 描画
    def draw(self):
        pyxel.cls(0)
        if self.state == "title":
            self.draw_title()
            if self.help:
                self.draw_help()
            return
        ox = random.randint(-1, 1) if self.shake else 0
        oy = random.randint(-1, 1) if self.shake else 0
        pyxel.clip(0, ROOM_Y, W, RH * TS)
        if self.slide:
            k = (self.slide["t"] + 1) / SLIDE_FRAMES
            k = 1 - (1 - k) * (1 - k)
            dx, dy = DIR_VEC[self.slide["d"]]
            sw, sh = W, RH * TS
            pyxel.camera(int(dx * sw * k) + ox, int(dy * sh * k) + oy)
            self.draw_tiles(self.slide["old"])
            pyxel.camera(int(dx * sw * (k - 1)) + ox, int(dy * sh * (k - 1)) + oy)
            self.draw_room()
        else:
            pyxel.camera(ox, oy)
            self.draw_room()
        pyxel.camera()
        pyxel.clip()
        self.draw_hud()
        self.draw_log()
        if self.flash_screen:
            pyxel.dither(0.5)
            pyxel.rect(0, ROOM_Y, W, RH * TS, 7)
            pyxel.dither(1)
        if self.banner and self.state == "play":
            s = f"{self.floor}F" if self.floor < self.last else f"{self.last}F  さいごのフロア"
            w = tw(s) + 40
            bx = (W - w) // 2
            pyxel.rect(bx, ROOM_Y + 90, w, 24, 0)
            pyxel.rectb(bx, ROOM_Y + 90, w, 24, 10)
            txts((W - tw(s)) // 2, ROOM_Y + 97, s, 10)
        st = self.state
        if st in ("inv", "inv_act"):
            self.draw_inv()
        elif st == "skills":
            self.draw_skills()
        elif st == "card_intro":
            self.draw_card_intro()
        elif st == "cards":
            self.draw_cards_ui()
        elif st == "discard":
            self.draw_discard()
        elif st == "gacha_confirm":
            r1, r2, r3 = self.gacha_rates()
            self.box_msg([f"ガチャ台だ。{gacha_cost(self.floor)}ギタンでまわす？",
                          f"（もちギタン {self.p.gold}）",
                          f"★★★{int(r3)}%  ★★{int(r2)}%  ★{int(r1)}%  ときどき道具",
                          "Z:まわす  X:やめる"])
        elif st == "gacha":
            self.draw_gacha()
        elif st == "shop_buy":
            sp = self.room.shop.get(self.shop_pos)
            if sp:
                nm = item_label(sp["item"]) if "item" in sp else "カード「" + CARDS[sp["card"]]["name"] + "」"
                desc = ITEMS[sp["item"]["name"]]["desc"] if "item" in sp else "★" * CARDS[sp["card"]]["r"] + " " + TYPE_LABEL[CARDS[sp["card"]]["t"]][0]
                self.box_msg([f"{nm}  {sp['price']}ギタン", desc[:26], f"（もちギタン {self.p.gold}）",
                              "Z:買う（カードは中身を見てから）  X:やめる"])
        elif st == "stairs":
            if self.floor >= self.last:
                self.box_msg(["光の階段だ。ダンジョンの外へ出ますか？", "Z:出る  X:やめる"])
            else:
                self.box_msg([f"階段を降りますか？（{self.floor + 1}Fへ）", "Z:降りる  X:やめる"])
        elif st == "gameover":
            self.draw_end(False)
        elif st == "clear":
            self.draw_end(True)
        if self.help:
            self.draw_help()

    def draw_tiles(self, r):
        fcol, fdot, wcol, whl, wline = theme_for(self.floor, self.last)
        for y in range(RH):
            for x in range(RW):
                px, py = x * TS, ROOM_Y + y * TS
                if r.tiles[y][x] == "#":
                    pyxel.rect(px, py, TS, TS, wcol)
                    pyxel.rect(px, py, TS, 2, whl)
                    pyxel.line(px, py + 7, px + 15, py + 7, wline)
                    pyxel.line(px, py + 15, px + 15, py + 15, wline)
                    if (x + y) % 2 == 0:
                        pyxel.line(px + 7, py + 2, px + 7, py + 7, wline)
                        pyxel.line(px + 12, py + 8, px + 12, py + 15, wline)
                    else:
                        pyxel.line(px + 3, py + 2, px + 3, py + 7, wline)
                        pyxel.line(px + 10, py + 8, px + 10, py + 15, wline)
                else:
                    pyxel.rect(px, py, TS, TS, fcol)
                    if (x * 7 + y * 3) % 5 == 0:
                        pyxel.pset(px + 4, py + 5, fdot)
                    if (x * 3 + y * 5) % 4 == 0:
                        pyxel.pset(px + 11, py + 11, fdot)
        for (x, y) in r.shop:
            px, py = x * TS, ROOM_Y + y * TS
            pyxel.rect(px + 1, py + 1, TS - 2, TS - 2, 2)
            pyxel.rectb(px + 1, py + 1, TS - 2, TS - 2, 14)
        for (x, y) in r.switches:
            px, py = x * TS, ROOM_Y + y * TS
            on = (x, y) in r.boxes
            pyxel.rectb(px + 2, py + 2, 12, 12, 11 if on else 10)
            pyxel.rect(px + 5, py + 5, 6, 6, 11 if on else (10 if (self.frame // 15) % 2 else 9))

    def visible(self, x, y):
        return self.room.kind != "dark" or cheb(x, y, self.p.x, self.p.y) <= 2

    def draw_doors(self, r):
        for d, (x, y) in r.doors.items():
            px, py = x * TS, ROOM_Y + y * TS
            if r.locked or d in r.oneway_block:
                col = 8 if r.locked else 13
                for i in range(3):
                    if d in ("L", "R"):
                        pyxel.line(px + 2, py + 3 + i * 5, px + 13, py + 3 + i * 5, col)
                    else:
                        pyxel.line(px + 3 + i * 5, py + 2, px + 3 + i * 5, py + 13, col)
                continue
            col = 10 if self.rooms_visited_dir(d) else 6
            dx, dy = DIR_VEC[d]
            nb = self.rooms.get((r.gx + dx, r.gy + dy))
            if nb and OPP[d] in nb.oneway_block:
                col = 9
            if d == "L":
                pyxel.tri(px + 2, py + 8, px + 6, py + 4, px + 6, py + 12, col)
            elif d == "R":
                pyxel.tri(px + 13, py + 8, px + 9, py + 4, px + 9, py + 12, col)
            elif d == "U":
                pyxel.tri(px + 8, py + 2, px + 4, py + 6, px + 12, py + 6, col)
            else:
                pyxel.tri(px + 8, py + 13, px + 4, py + 9, px + 12, py + 9, col)

    def draw_room(self):
        r = self.room
        self.draw_tiles(r)
        if r.kind != "dark":
            self.draw_doors(r)
        for (x, y) in r.boxes:
            px, py = x * TS, ROOM_Y + y * TS
            pyxel.rect(px + 1, py + 1, 14, 14, 4)
            pyxel.rectb(px + 1, py + 1, 14, 14, 1)
            pyxel.line(px + 2, py + 2, px + 13, py + 13, 9)
            pyxel.line(px + 13, py + 2, px + 2, py + 13, 9)
        if r.chest:
            px, py = r.chest[0] * TS, ROOM_Y + r.chest[1] * TS
            pyxel.rect(px + 2, py + 5, 12, 9, 9)
            pyxel.rect(px + 2, py + 3, 12, 4, 4)
            pyxel.rectb(px + 2, py + 3, 12, 11, 1)
            pyxel.rect(px + 7, py + 7, 2, 3, 10)
        for (x, y) in r.gates:
            px, py = x * TS, ROOM_Y + y * TS
            for i in range(3):
                pyxel.line(px + 3 + i * 5, py + 1, px + 3 + i * 5, py + 14, 13)
            pyxel.line(px, py + 4, px + 15, py + 4, 5)
        for (x, y), sp in r.shop.items():
            if "item" in sp:
                self.draw_item_icon(sp["item"]["name"], x * TS, ROOM_Y + y * TS)
            else:
                c = CARDS[sp["card"]]
                px, py = x * TS, ROOM_Y + y * TS
                pyxel.rect(px + 4, py + 2, 8, 12, 1)
                pyxel.rectb(px + 4, py + 2, 8, 12, RARITY_COL[c["r"]])
                pyxel.pset(px + 8, py + 8, TYPE_LABEL[c["t"]][1])
        if r.stairs:
            sx, sy = SPR_IDX["stairs"]
            px, py = r.stairs[0] * TS, ROOM_Y + r.stairs[1] * TS
            if self.floor >= self.last:
                pyxel.circb(px + 8, py + 8, 9 + (self.frame // 6) % 3, 10)
            pyxel.blt(px, py, 0, sx, sy, TS, TS, 0)
        if r.gacha:
            gx, gy = SPR_IDX["gacha"]
            bob = 1 if (self.frame // 20) % 2 else 0
            pyxel.blt(r.gacha[0] * TS, ROOM_Y + r.gacha[1] * TS - bob, 0, gx, gy, TS, TS, 0)
        for (x, y), it in r.items.items():
            self.draw_item_icon(it["name"], x * TS, ROOM_Y + y * TS)
        if r.locked and (self.frame // 20) % 2 == 0:
            txts(4, ROOM_Y + 3, "モンスターハウス！", 8)
        p = self.p
        if self.state == "play" and (held(KTURN) or held(KDIAG)):
            for dx, dy in DIRS8:
                if held(KDIAG) and not (dx and dy):
                    continue
                cx = p.x * TS + 8 + dx * 14
                cy = ROOM_Y + p.y * TS + 8 + dy * 14
                pyxel.circ(cx, cy, 2, 10 if (dx, dy) == (p.fx, p.fy) else 13)
        for e in r.enemies:
            if self.visible(e.x, e.y):
                self.draw_enemy(e)
        self.draw_player()
        if r.kind == "dark":
            p = self.p
            for y in range(RH):
                for x in range(RW):
                    if cheb(x, y, p.x, p.y) > 2:
                        pyxel.rect(x * TS, ROOM_Y + y * TS, TS, TS, 0)
                    elif cheb(x, y, p.x, p.y) == 2:
                        pyxel.dither(0.5)
                        pyxel.rect(x * TS, ROOM_Y + y * TS, TS, TS, 0)
                        pyxel.dither(1)
            self.draw_doors(r)
        for pr in self.projs:
            x, y = pr["x"], pr["y"]
            if pr["kind"] == "arrow":
                pyxel.line(x - pr["fx"] * 5, y - pr["fy"] * 5, x + pr["fx"] * 3, y + pr["fy"] * 3, 7)
            elif pr["kind"] == "item":
                pyxel.rect(x - 2, y - 2, 4, 4, 7)
            else:
                pyxel.circ(x, y, 3, pr["col"])
                pyxel.circ(x, y, 1, 7)
        for pa in self.parts:
            if pa["d"] <= 0:
                pyxel.pset(pa["x"], pa["y"], pa["col"])
        for pp in self.popups:
            if pp["d"] > 0:
                continue
            t = pp["t"]
            yy = pp["y"] - min(t, 10) * 1.2
            w = tw(pp["s"])
            if t < 28 or t % 2 == 0:
                txts(pp["x"] - w // 2, yy, pp["s"], pp["col"])

    def rooms_visited_dir(self, d):
        dx, dy = DIR_VEC[d]
        nr = self.rooms.get((self.room.gx + dx, self.room.gy + dy))
        return nr is not None and nr.visited

    def draw_player(self):
        p = self.p
        x = p.rx + p.lx
        y = ROOM_Y + p.ry + p.ly
        moving = abs(p.rx - p.x * TS) > 1 or abs(p.ry - p.y * TS) > 1
        bob = 1 if moving and (self.frame // 3) % 2 else 0
        if p.fy < 0 and p.fx == 0:
            u, v = SPR_IDX["napo_b"]
            w = TS
        elif p.fx == 0:
            u, v = SPR_IDX["napo_f"]
            w = TS
        else:
            u, v = SPR_IDX["napo_s"]
            w = TS if p.fx > 0 else -TS
        if p.flash and p.flash % 4 < 2:
            pyxel.pal(14, 7)
            pyxel.pal(15, 7)
        pyxel.blt(x, y - bob, 0, u, v, w, TS, 0)
        pyxel.pal()
        pyxel.pset(x + 8 + p.fx * 9, y + 8 + p.fy * 9, 10)

    def draw_enemy(self, e):
        x = e.rx + e.lx
        y = ROOM_Y + e.ry + e.ly
        u, v = SPR_IDX[e.spr]
        w = TS if e.face > 0 else -TS
        if e.spr == "bat":
            y += (self.frame // 8) % 2
        if e.spr in ("ghost", "musha"):
            y += pyxel.sin(self.frame * 6) * 1.5
        if e.ai == "boss":
            col = 9 if not e.phys else 6
            rr = 9 + (self.frame // 5) % 3
            pyxel.circb(x + 8, y + 8, rr, col)
            pyxel.circb(x + 8, y + 8, rr + 2, col)
        if e.star and (self.frame // 4) % 4 == 0:
            pyxel.pset(x + (self.frame * 7) % 16, y + (self.frame * 3) % 16, 7)
        if e.pal:
            for a, b in e.pal.items():
                pyxel.pal(a, b)
        if e.flash and e.flash % 4 < 2:
            for c in range(1, 16):
                pyxel.pal(c, 7)
        if e.para > 0:
            pyxel.pal(1, 10)
        pyxel.blt(x, y, 0, u, v, w, TS, 0)
        pyxel.pal()
        if e.sleep:
            zz = (self.frame // 20) % 2
            txt(x + 11, y - 6 - zz, "z", 12)
        if not e.phys:
            pyxel.rect(x, y, 4, 4, 9)
            pyxel.rectb(x, y, 4, 4, 1)
        if not e.mag:
            pyxel.rect(x + 12, y, 4, 4, 2)
            pyxel.rectb(x + 12, y, 4, 4, 7)
        if e.hp < e.mhp:
            pyxel.rect(x + 1, y + 15, 14, 2, 1)
            pyxel.rect(x + 1, y + 15, max(1, 14 * e.hp // e.mhp), 2, 11 if e.hp * 3 > e.mhp else 8)

    def draw_item_icon(self, name, px, py):
        k = ITEMS[name]["k"]
        cx, cy = px + 8, py + 8
        if k == "herb":
            col = 3 if name == "薬草" else 11
            pyxel.elli(cx - 5, cy - 3, 10, 6, col)
            pyxel.line(cx - 4, cy, cx + 4, cy, 1)
            if name == "弟切草":
                pyxel.pset(cx, cy - 2, 8)
        elif k == "seed":
            col = 14 if ITEMS[name]["v"] == "mhp" else 9
            pyxel.elli(cx - 5, cy - 3, 10, 6, col)
            pyxel.line(cx - 4, cy, cx + 4, cy, 1)
            pyxel.pset(cx, cy - 2, 7)
        elif k == "dgrass":
            pyxel.elli(cx - 5, cy - 3, 10, 6, 8)
            pyxel.line(cx - 4, cy, cx + 4, cy, 1)
            pyxel.pset(cx, cy - 2, 10)
        elif k == "food":
            s = 6 if name == "おにぎり" else 7
            pyxel.tri(cx, cy - s, cx - s, cy + s - 2, cx + s, cy + s - 2, 7)
            pyxel.rect(cx - 3, cy + 1, 6, s - 2, 1)
        elif k == "arrow":
            col = 9 if name == "木の矢" else 13
            pyxel.line(cx - 5, cy + 5, cx + 4, cy - 4, col)
            pyxel.line(cx - 4, cy + 5, cx + 5, cy - 4, col)
            pyxel.pset(cx + 5, cy - 5, 7)
            pyxel.line(cx - 6, cy + 3, cx - 4, cy + 6, 7)
        elif k == "staff":
            pyxel.line(cx - 5, cy + 6, cx + 3, cy - 4, 4)
            pyxel.line(cx - 4, cy + 6, cx + 4, cy - 4, 9)
            pyxel.circ(cx + 4, cy - 5, 2, {"blow": 12, "para": 10, "bolt": 7}[ITEMS[name]["v"]])
        elif k == "scroll":
            pyxel.rect(cx - 5, cy - 4, 10, 8, 7)
            pyxel.rect(cx - 6, cy - 5, 2, 10, 4)
            pyxel.rect(cx + 4, cy - 5, 2, 10, 4)
            pyxel.line(cx - 3, cy - 1, cx + 2, cy - 1, 13)
            pyxel.line(cx - 3, cy + 1, cx + 2, cy + 1, 13)
        elif k == "weapon":
            if name == "こん棒":
                pyxel.line(cx - 5, cy + 5, cx + 3, cy - 3, 4)
                pyxel.circ(cx + 3, cy - 3, 2, 9)
            else:
                col = {"ドラゴンキラー": 10, "まさむね": 12, "かぐらのつるぎ": 14}.get(name, 7)
                pyxel.line(cx - 4, cy + 4, cx + 5, cy - 5, col)
                pyxel.line(cx - 3, cy + 4, cx + 5, cy - 4, 13)
                pyxel.line(cx - 6, cy + 1, cx - 1, cy + 6, 10)
                pyxel.line(cx - 6, cy + 6, cx - 5, cy + 5, 4)
        elif k == "shield":
            col = {"木甲の盾": 9, "青銅甲の盾": 10, "重装の盾": 6, "ドラゴンシールド": 8}.get(name, 12)
            pyxel.rect(cx - 5, cy - 5, 10, 8, col)
            pyxel.tri(cx - 5, cy + 3, cx + 4, cy + 3, cx, cy + 7, col)
            pyxel.rectb(cx - 5, cy - 5, 10, 8, 1)
            pyxel.pset(cx, cy - 1, 7)
        elif k == "gold":
            pyxel.circ(cx - 2, cy + 2, 3, 10)
            pyxel.circ(cx + 3, cy, 3, 10)
            pyxel.circb(cx + 3, cy, 3, 9)
            pyxel.pset(cx + 3, cy, 7)

    def draw_hud(self):
        p = self.p
        st = self.stats()
        pyxel.rect(0, 0, W, HUD_H, 1)
        pyxel.line(0, HUD_H - 1, W, HUD_H - 1, 5)
        txt(3, 2, f"{self.floor}F", 10)
        hpcol = 7 if p.hp * 4 > st["mhp"] else 8
        txt(24, 2, f"HP{p.hp:>3}/{st['mhp']}", hpcol)
        pyxel.rect(84, 5, 36, 4, 0)
        pyxel.rect(84, 5, max(0, 36 * p.hp // st["mhp"]), 4, 11 if p.hp * 4 > st["mhp"] else 8)
        txt(126, 2, f"MP{p.mp}/{st['mmp']}", 12)
        fcol = 7 if p.full > 20 else 9 if p.full > 0 else 8
        txt(176, 2, f"満腹{p.full}%", fcol)
        txt(228, 2, f"{p.gold}G", 10)
        e = self.facing_enemy()
        front = e is not None
        vis = [en for en in self.room.enemies if self.visible(en.x, en.y)]
        if e is None and vis:
            e = min(vis, key=lambda en: cheb(en.x, en.y, p.x, p.y))
        if e:
            nm = ("▶" if front else "・") + e.kind
            txt(3, 13, nm, 7 if front else 13)
            x = 3 + tw(nm) + 4
            s = f"{e.hp}"
            txt(x, 13, s, 7 if front else 13)
            x += tw(s) + 4
            txt(x, 13, "物", 9 if e.phys else 13)
            txt(x + 10, 13, "○" if e.phys else "×", 7 if e.phys else 8)
            txt(x + 20, 13, "魔", 6 if e.mag else 13)
            txt(x + 30, 13, "○" if e.mag else "×", 7 if e.mag else 8)
        txt(164, 13, f"カード{len(p.cards)}/{CARD_MAX}", 14)
        # 次のカードまでの撃破数（強敵は3体ぶん）
        txt(222, 13, f"あと{self.kill_need - self.kill_prog}体", 11)
        mx, my = 275, 1
        for (gx, gy), rr in self.rooms.items():
            x = mx + gx * 11
            y = my + gy * 7
            if rr.visited:
                col = 10 if rr is self.room else 6
                pyxel.rect(x, y, 10, 6, col)
                if rr.stairs:
                    pyxel.rect(x + 4, y + 2, 2, 2, 8)
                if rr.gacha:
                    pyxel.rect(x + 4, y + 2, 2, 2, 14)
                if rr.boss_room:
                    pyxel.rect(x + 3, y + 1, 4, 4, 2)
                if rr.kind == "shop":
                    pyxel.rect(x + 1, y + 1, 2, 2, 11)
                if rr.kind == "gimmick" and rr.chest:
                    pyxel.rect(x + 7, y + 1, 2, 2, 9)
            else:
                pyxel.rectb(x, y, 10, 6, 5)

    def draw_log(self):
        pyxel.rect(0, LOG_Y, W, H - LOG_Y, 0)
        pyxel.line(0, LOG_Y, W, LOG_Y, 5)
        lines = self.log[-3:]
        for i, (s, col, age) in enumerate(lines):
            c = col if age < 240 else 13
            txt(4, LOG_Y + 3 + i * 12, s, c)
        if not lines or tw(lines[-1][0]) < W - 60:
            txt(W - tw("H:そうさ") - 3, LOG_Y + 27, "H:そうさ", 5)

    def panel(self, x, y, w, h):
        pyxel.rect(x, y, w, h, 1)
        pyxel.rectb(x, y, w, h, 7)
        pyxel.rectb(x + 1, y + 1, w - 2, h - 2, 5)

    def box_msg(self, lines):
        w = max(tw(s) for s in lines) + 20
        h = len(lines) * 13 + 12
        x = (W - w) // 2
        y = ROOM_Y + 70
        self.panel(x, y, w, h)
        for i, s in enumerate(lines):
            txt(x + 10, y + 7 + i * 13, s, 7 if i < len(lines) - 1 else 10)

    def draw_inv(self):
        p = self.p
        x, y, w = 150, ROOM_Y + 4, 166
        n = len(p.inv)
        rows = min(n, INV_ROWS)
        # 持ち物が多いときはリストをスクロールさせる（画面からはみ出さない）
        top = getattr(self, "inv_top", 0)
        top = max(0, min(top, self.inv_sel, n - rows))
        if self.inv_sel >= top + rows:
            top = self.inv_sel - rows + 1
        self.inv_top = top
        h = 20 + 12 * rows
        self.panel(x, y, w, h)
        txt(x + 6, y + 4, f"もちもの {n}/{INV_MAX}", 10)
        txt(x + w - tw("C:せいとん") - 6, y + 4, "C:せいとん", 13)
        for row in range(rows):
            i = top + row
            it = p.inv[i]
            yy = y + 17 + row * 12
            if i == self.inv_sel:
                pyxel.rect(x + 3, yy - 1, w - 6, 12, 5)
            txt(x + 6, yy, "E" if it["eq"] else " ", 10)
            txt(x + 14, yy, item_label(it), 7)
        if top > 0:
            txt(x + w - 14, y + 17, "▲", 10)
        if top + rows < n:
            txt(x + w - 14, y + 17 + (rows - 1) * 12, "▼", 10)
        # 説明は画面下の固定欄に出す（長い説明も3行まで読める）
        it = p.inv[self.inv_sel]
        dx, dy, dw, dh = 4, 208, W - 8, 60
        self.panel(dx, dy, dw, dh)
        txt(dx + 8, dy + 5, item_label(it), 10)
        for i, line in enumerate(wrap(ITEMS[it["name"]]["desc"], dw - 16)[:3]):
            txt(dx + 8, dy + 18 + i * 11, line, 7)
        if self.state == "inv_act":
            acts = self.item_actions(it)
            ah = 8 + 12 * len(acts)
            ax = x - 62
            ay = min(y + 17 + (self.inv_sel - top) * 12, dy - 4 - ah)
            self.panel(ax, ay, 58, ah)
            for i, a in enumerate(acts):
                if i == self.act_sel:
                    pyxel.rect(ax + 3, ay + 3 + i * 12, 52, 12, 5)
                txt(ax + 8, ay + 4 + i * 12, a, 7)

    def draw_skills(self):
        p = self.p
        st = self.stats()
        x, y, w = 56, ROOM_Y + 4, 260
        h = 34 + 12 * max(1, len(p.cards)) + 34
        self.panel(x, y, w, h)
        txt(x + 6, y + 4, f"カード {len(p.cards)}/{CARD_MAX}   MP {p.mp}/{st['mmp']}", 10)
        txt(x + 6, y + 16, f"攻撃{st['atk']}  防御{st['df']}  魔力{st['mag']}  最大HP{st['mhp']}", 7)
        if not p.cards:
            txt(x + 10, y + 32, "まだカードがない", 13)
            return
        for i, cid in enumerate(p.cards):
            c = CARDS[cid]
            yy = y + 30 + i * 12
            if i == self.sk_sel:
                pyxel.rect(x + 3, yy - 1, w - 6, 12, 5)
            txt(x + 6, yy, "★" * c["r"], RARITY_COL[c["r"]])
            lab, lc = TYPE_LABEL[c["t"]]
            txt(x + 40, yy, c["name"], 7)
            if c["t"] == "skill":
                cost = c["fx"]["mp"]
                txt(x + 160, yy, f"MP{cost}", 12 if p.mp >= cost else 8)
            txt(x + 204, yy, lab, lc)
        c = CARDS[p.cards[self.sk_sel]]
        for i, line in enumerate(wrap(c["desc"], w - 12)[:2]):
            txt(x + 6, y + h - 28 + i * 11, line, 6)

    def draw_card(self, cid, x, y, sel):
        c = CARDS[cid]
        cw, ch = 94, 138
        rc = RARITY_COL[c["r"]]
        if sel:
            y -= 6
        pyxel.rect(x + 3, y + 3, cw, ch, 0)
        pyxel.rect(x, y, cw, ch, 1)
        bc = rc
        if sel and (self.frame // 8) % 2:
            bc = 7
        pyxel.rectb(x, y, cw, ch, bc)
        pyxel.rectb(x + 1, y + 1, cw - 2, ch - 2, bc)
        if c["r"] == 3:
            k = (self.frame * 2) % cw
            pyxel.pset(x + k, y + 2, 7)
            pyxel.pset(x + cw - 1 - k, y + ch - 3, 7)
        txt(x + 6, y + 5, "★" * c["r"], rc)
        lab, lc = TYPE_LABEL[c["t"]]
        txt(x + cw - tw(lab) - 6, y + 5, lab, lc)
        pyxel.circ(x + cw // 2, y + 36, 14, lc)
        pyxel.circb(x + cw // 2, y + 36, 14, 7)
        txts(x + cw // 2 - 5, y + 31, TYPE_GLYPH[c["t"]], 7)
        nm = c["name"]
        txts(x + (cw - tw(nm)) // 2, y + 58, nm, 7)
        sub = ""
        subc = 12
        if c["t"] == "skill":
            sub = f"MP{c['fx']['mp']}"
        n_have = self.p.cards.count(cid)
        if n_have and c["t"] != "item":
            sub = (sub + " " if sub else "") + f"もってる{n_have}"
            subc = 11
        if sub:
            txt(x + (cw - tw(sub)) // 2, y + 71, sub, subc)
        for i, line in enumerate(wrap(c["desc"], cw - 12)[:4]):
            txt(x + 6, y + 84 + i * 11, line, 6)
        if c["g"]:
            txt(x + 6, y + ch - 13, "ガチャ限定", 14)

    def draw_cards_ui(self):
        pyxel.rect(0, 0, W, H, 0)
        n = len(self.cp_ids)
        title = {"start": "最初のカードを1枚えらぼう",
                 "level": "レベルアップ！ カードを1枚えらぼう",
                 "gacha": "ガチャの景品！",
                 "chest": "宝箱の中身！ 1枚えらぼう",
                 "shop": "このカードを買う？"}[self.cp_src]
        txts((W - tw(title)) // 2, 28, title, 10)
        cw, gap = 94, 8
        total = n * cw + (n - 1) * gap
        x0 = (W - total) // 2
        for i, cid in enumerate(self.cp_ids):
            appear = min(1.0, (self.cp_t - i * 3) / 8) if self.cp_t < 20 else 1.0
            yoff = int((1 - max(0, appear)) * 30)
            self.draw_card(cid, x0 + i * (cw + gap), 50 + yoff, i == self.cp_sel)
        full = len(self.p.cards) >= CARD_MAX
        info = f"所持カード {len(self.p.cards)}/{CARD_MAX}" + ("  （満杯：とったら1枚すてる）" if full else "")
        txt((W - tw(info)) // 2, 200, info, 8 if full else 7)
        ctrl = "←→:えらぶ  Z:とる" + ("" if self.cp_src == "start" else "  X:みおくる")
        if self.cp_src == "shop" and self.shop_pending:
            ctrl = f"Z:{self.shop_pending[1]}ギタンで買う  X:やめる"
        txt((W - tw(ctrl)) // 2, 214, ctrl, 13)
        if self.p.cards:
            names = " / ".join(CARDS[c]["name"] for c in self.p.cards)
            for i, line in enumerate(wrap("もってる: " + names, W - 16)[:3]):
                txt(8, 232 + i * 12, line, 5 if i else 13)

    def draw_discard(self):
        pyxel.rect(0, 0, W, H, 0)
        x, y, w = 40, 16, 240
        h = 26 + 12 * (CARD_MAX + 1) + 30
        self.panel(x, y, w, h)
        txt(x + 6, y + 5, "カードが満杯！ どれをすてる？", 10)
        rows = self.p.cards + [self.dc_new]
        for i, cid in enumerate(rows):
            c = CARDS[cid]
            yy = y + 22 + i * 12
            if i == self.dc_sel:
                pyxel.rect(x + 3, yy - 1, w - 6, 12, 8)
            txt(x + 6, yy, "★" * c["r"], RARITY_COL[c["r"]])
            txt(x + 40, yy, c["name"] + ("（新）" if i == CARD_MAX else ""), 10 if i == CARD_MAX else 7)
            lab, lc = TYPE_LABEL[c["t"]]
            txt(x + 186, yy, lab, lc)
        c = CARDS[rows[self.dc_sel]]
        for i, line in enumerate(wrap(c["desc"], w - 12)[:2]):
            txt(x + 6, y + h - 28 + i * 11, line, 6)
        tip = "↑↓:えらぶ  Z:すてる  X:もどる"
        if self.dc_sel == CARD_MAX:
            tip = "↑↓:えらぶ  Z:新しいのをあきらめる  X:もどる"
        txt(x + 6, y + h + 4, tip, 13)

    def draw_gacha(self):
        t = self.g_t
        pyxel.rect(0, 0, W, H, 0)
        cx, cy = W // 2, 120
        shake = (self.frame % 3) - 1 if t < 34 else 0
        mx = cx - 30 + shake
        pyxel.rect(mx, cy - 6, 60, 54, 8)
        pyxel.rectb(mx, cy - 6, 60, 54, 1)
        pyxel.rect(mx + 4, cy + 30, 52, 4, 2)
        pyxel.circ(cx + shake, cy - 22, 26, 6)
        pyxel.circb(cx + shake, cy - 22, 26, 1)
        balls = [(-14, -8, 8), (-4, -12, 10), (8, -10, 11), (14, 2, 12), (-12, 6, 14), (0, 2, 8),
                 (10, 12, 10), (-6, 14, 11), (4, -2, 14), (-16, -2, 12), (16, -8, 8), (0, 14, 12)]
        for bx, by, bc in balls:
            pyxel.circ(cx + bx + shake, cy - 22 + by, 4, bc)
        ang = min(t, 34) * 22
        hx, hy = cx + shake, cy + 14
        pyxel.circ(hx, hy, 9, 10)
        pyxel.circb(hx, hy, 9, 1)
        pyxel.line(hx - pyxel.cos(ang) * 8, hy - pyxel.sin(ang) * 8,
                   hx + pyxel.cos(ang) * 8, hy + pyxel.sin(ang) * 8, 1)
        ccol = RARITY_COL[self.g_rar] if self.g_rar > 1 else 13
        if 34 <= t < 78:
            k = t - 34
            if k < 14:
                bx, by = cx + 22, cy + 30 + k * 3
            else:
                bx, by = cx + 22, cy + 72 - abs(pyxel.sin((k - 14) * 18)) * 6
            if t > 60:
                bx += (self.frame % 5) - 2
                pcol = ccol if (t // 3) % 2 else 7
            else:
                pcol = 7
            pyxel.circ(bx, by, 9, pcol)
            pyxel.rect(bx - 9, by, 19, 9, 13)
            pyxel.circb(bx, by, 9, 1)
            pyxel.line(bx - 9, by, bx + 9, by, 1)
        for pa in self.parts:
            if pa["d"] <= 0:
                pyxel.pset(pa["x"], pa["y"], pa["col"])
        if t >= 78:
            r = min(60, (t - 78) * 6)
            pyxel.circb(cx, 126, r, ccol)
            if t > 82:
                pyxel.rect(cx - 90, 160, 180, 40, 1)
                pyxel.rectb(cx - 90, 160, 180, 40, ccol)
                if self.g_card:
                    c = CARDS[self.g_card]
                    s1 = "★" * c["r"] + " " + c["name"]
                else:
                    s1 = item_label(self.g_item)
                txts(cx - tw(s1) // 2, 168, s1, ccol if self.g_rar > 1 else 7)
                txt(cx - tw("Z:つぎへ") // 2, 184, "Z:つぎへ", 13)
        else:
            txts(cx - tw("ガラガラ…") // 2, 220, "ガラガラ…", 7)
            txt(cx - tw("Z:スキップ") // 2, 236, "Z:スキップ", 13)

    def draw_end(self, clear):
        pyxel.rect(0, 0, W, H, 0)
        x, y, w, h = 40, 34, 240, 200
        self.panel(x, y, w, h)
        if clear:
            t1 = "ダンジョン踏破！"
            t2 = "ナポは悪夢から帰ってきた。おめでとう！"
            col = 10
        else:
            t1 = "ゲームオーバー"
            t2 = f"{self.floor}Fで{self.cause}"
            col = 8
        txts(x + (w - tw(t1)) // 2, y + 10, t1, col)
        txt(x + (w - tw(t2)) // 2, y + 26, t2, 7)
        txt(x + 12, y + 44, f"到達 {self.floor}F   ターン {self.turn}   たおした敵 {self.kills}", 7)
        bv = self.best[self.dg_idx]
        best = "踏破" if bv > self.last else f"{bv}F"
        txt(x + 12, y + 56, f"{self.dg['name']} 最高記録: {best}", 14)
        txt(x + 12, y + 72, "最後のカード:", 13)
        for i, cid in enumerate(self.p.cards):
            c = CARDS[cid]
            cx = x + 12 + (i % 2) * 112
            cy = y + 86 + (i // 2) * 12
            txt(cx, cy, "★" * c["r"], RARITY_COL[c["r"]])
            txt(cx + 32, cy, c["name"], 7)
        s2 = "Z:もういちど  X:タイトルへ"
        txt(x + (w - tw(s2)) // 2, y + h - 16, s2, 10)

    def draw_title(self):
        pyxel.rect(0, 0, W, H, 1)
        for i in range(0, W, 16):
            for j in range(0, H, 16):
                if (i // 16 + j // 16) % 2 == 0:
                    pyxel.rect(i, j, 16, 16, 5)
        pyxel.dither(0.7)
        pyxel.rect(0, 0, W, H, 1)
        pyxel.dither(1)
        u, v = SPR_IDX["napo_f"]
        bob = 2 if (self.frame // 20) % 2 else 0
        pyxel.blt(W // 2 - 8, 44 - bob, 0, u, v, TS, TS, 0, scale=2)
        t1 = "ナポのカードダンジョン"
        txts((W - tw(t1)) // 2, 80, t1, 14)
        t2 = "（仮）プロトタイプ3"
        txt((W - tw(t2)) // 2, 96, t2, 13)
        for i, dg in enumerate(DUNGEONS):
            y = 116 + i * 40
            sel = i == self.title_sel
            if sel:
                self.panel(40, y, 240, 36)
            else:
                pyxel.rect(40, y, 240, 36, 1)
                pyxel.rectb(40, y, 240, 36, 5)
            bv = self.best[i]
            rec = "" if not bv else ("踏破！" if bv > dg["last"] else f"最高 {bv}F")
            txt(50, y + 4, ("▶ " if sel else "   ") + dg["name"] + f"（{dg['last']}F）", 10 if sel else 13)
            txt(270 - tw(rec), y + 4, rec, 11)
            txt(62, y + 18, dg["desc"][0], 7 if sel else 13)
        s = "↑↓:えらぶ  Z:はじめる  H:そうさ説明"
        txt((W - tw(s)) // 2, 206, s, 7)
        if (self.frame // 30) % 2 == 0:
            s = "Zではじめる"
            txts((W - tw(s)) // 2, 222, s, 10)

    def draw_help(self):
        x, y, w, h = 10, 6, 300, 260
        self.panel(x, y, w, h)
        lines = [
            ("そうさ", 10),
            ("矢印:移動（2つ同時押しでななめ）  Space:足ぶみ", 7),
            ("Shift+矢印:ダッシュ  A+矢印:向きだけ  S+矢印:ななめだけ", 7),
            ("Z:攻撃 / 階段・ガチャ  X:もちもの  C:カード（わざ）", 7),
            ("", 7),
            ("ルール", 10),
            ("いちばん奥の『ゆめくい』をたおせばクリア", 7),
            ("敵をたおすとカードが選べる（あと○体が目安）", 7),
            ("カードは10枚まで。11枚目は1枚すてる", 7),
            ("同じカードは重なって効果が上がる", 7),
            ("どうぐカードはカード枠を使わない", 3),
            ("敵の左上オレンジ=物理が効かない", 9),
            ("敵の右上むらさき=魔法が効かない", 6),
            ("巻物・いかずちの杖・ドラゴン草はどんな敵にも効く", 7),
            ("もちもの画面でC:せいとん  zの敵は眠っている", 12),
            ("モンスターハウスは全滅させるまで出られない", 8),
            ("オレンジの矢印の扉は一方通行（戻れない）", 9),
            ("ガチャは深い階ほどいいものが出る（ガチャ限定あり）", 14),
            ("1フロア600ターンで風に飛ばされる", 7),
            ("H / X:とじる", 13),
        ]
        for i, (s, c) in enumerate(lines):
            txt(x + 10, y + 6 + i * 12.4, s, c)


if __name__ == "__main__":
    Game().run()
