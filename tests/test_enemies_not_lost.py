"""部屋移動で敵が消えない"""
import os, sys, random
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
import pyxel, main
random.seed(4)
g = main.Game(); g.new_game(1); g.state = "play"
def total():
    n = sum(len(r.enemies) for r in g.rooms.values())
    n += sum(len(r.pending) for r in g.rooms.values())
    return n
lost = 0; cases = []
for t in range(60):
    g.floor = random.randint(3, 25)
    g.gen_floor()
    g.state = "play"; g.p.hp = 99999; g.p.full = 100
    for step in range(60):
        r = g.room
        ds = [d for d in r.doors if (r.gx + main.DIR_VEC[d][0], r.gy + main.DIR_VEC[d][1]) in g.rooms]
        if not ds: break
        d = random.choice(ds)
        # 敵を何体か置く（起きている・遠い・近い）
        if random.random() < 0.5 and len(r.enemies) < 5:
            pos = g.free_tile(r)
            if pos:
                r.enemies.append(g.spawn(main.wchoice(main.enemy_pool(g.floor)), pos, g.floor))
        before = total()
        g.change_room(d)
        g.state = "play"; g.pending_cards = 0
        after = total()
        if after < before:   # モンスターハウスで増えるのはよい。減るのはだめ
            lost += 1
            cases.append((before, after))
        for _ in range(random.randint(0, 12)):
            g.end_turn(); g.state = "play"; g.pending_cards = 0
            g.p.hp = 99999
    # 風やボスで死んだ状態を戻す
print("部屋移動で敵が減った回数:", lost, cases[:8])
assert lost == 0
print("ALL_OK")
