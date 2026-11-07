"""手ぶら・カードなしで始まる"""
import os, sys, random
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyxel, main
from verify_shot import shot
random.seed(2)
g = main.Game(); g.new_game(1)
assert g.state == "play" and not g.p.inv and not g.p.cards
# 持ち物・カード・わざ画面を、空の状態で開く
g.need_release = False
g.state = "inv"; g.upd_inv(); assert g.state == "play"
g.state = "skills"; g.draw()
try:
    g.upd_skills()
except Exception as e:
    print("わざ画面の例外:", repr(e)); raise
g.state = "play"; g.need_release = False
# 手ぶらで素手のまま、敵と戦える
r = g.room
g.p.hp = 9999
e = main.Enemy("マムル", g.p.x + 1, g.p.y, 1)
r.enemies.append(e)
g.p.fx, g.p.fy = 1, 0
for _ in range(10):
    g.player_attack()
    if e.hp <= 0: break
print("素手(攻撃", g.stats()["atk"], ")でマムルをたおせた:", e.hp <= 0)
assert e.hp <= 0
g.draw(); shot("bare_start")
g.help = True; g.draw(); shot("help")
# ランダム歩行（手ぶらから始めて、数フロア進む）
steps = 0
for fl in range(1, 6):
    g.floor = fl; g.gen_floor(); g.state = "play"; g.help = False
    g.p.hp = 99999; g.p.full = 100
    for _ in range(150):
        dx, dy = random.choice(main.DIRS8)
        g.state = "play"; g.need_release = False
        g.try_move(dx, dy); g.end_turn(); g.pending_cards = 0
        steps += 1
print("手ぶらスタートの歩行", steps, "ステップ 例外なし")
print("ALL_OK")
