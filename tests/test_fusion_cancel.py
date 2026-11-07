"""合成の巻物: 途中でやめても巻物は残り、ターンも進まない。合成できる個数は読み直しても変わらない。"""
import os
import random
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJ)
import main  # noqa: E402

random.seed(9)
g = main.Game()
g.new_game(0)
g.state = "play"
p = g.p
a = main.make_item("普通の剣"); a["eq"] = True
b = main.make_item("炎の剣")
c = main.make_item("弱い盾")
sc = main.make_item("合成の巻物")
p.inv = [a, b, c, sc]
orig_pressed, orig_menu = main.pressed, main.menu_p
main.menu_p = lambda keys: False


def press(key):
    main.pressed = lambda keys, *x: keys is key
    g.need_release = False
    getattr(g, "upd_" + g.state)()
    main.pressed = orig_pressed


# 1) 読んで、すぐやめる
t0 = g.turn
g.state = "inv_act"
g.state = "play"
assert g.do_item(sc, "よむ") is False and g.state == "fuse_base"
n1 = g.fuse_n
press(main.KX)
assert g.state == "play" and sc in p.inv and g.turn == t0
print("土台えらびでやめた: 巻物は残った / ターンは進まない OK  個数", n1)

# 2) 読み直しても個数は同じ
for _ in range(5):
    g.do_item(sc, "よむ")
    assert g.fuse_n == n1
    press(main.KX)
print("読み直しても個数は同じ OK")

# 3) 土台を選んでから X → 土台えらびにもどる。さらに X でやめる
g.do_item(sc, "よむ")
g.fuse_sel = g.fuse_candidates().index(a)
press(main.KZ)
assert g.state == "fuse_mat" and g.fuse_base is a
press(main.KX)
assert g.state == "fuse_base" and g.fuse_base is None
press(main.KX)
assert g.state == "play" and sc in p.inv and g.turn == t0
print("素材えらびのXで土台えらびにもどる OK")

# 4) 素材がない土台（盾が1つだけ）を選んでも、巻物はなくならず選び直せる
g.do_item(sc, "よむ")
g.fuse_sel = g.fuse_candidates().index(c)
press(main.KZ)
assert g.state == "fuse_base" and g.fuse_base is None and sc in p.inv
press(main.KX)
print("素材のない土台: 選び直しになる OK")

# 5) 剣や盾が1つしかないとき、巻物は燃えない
p.inv = [a, sc]
assert g.do_item(sc, "よむ") is False and g.state == "play" and sc in p.inv
print("装備が足りないとき: 巻物はそのまま OK")

# 6) けっていで合成すると、巻物がなくなり1ターン進む
p.inv = [a, b, sc]
g.do_item(sc, "よむ")
g.fuse_sel = g.fuse_candidates().index(a)
press(main.KZ)
g.fuse_sel = g.fuse_candidates().index(b)
press(main.KZ)
g.fuse_sel = len(g.fuse_candidates())
press(main.KZ)
assert g.state == "play" and sc not in p.inv and b not in p.inv and g.turn == t0 + 1
print("けっていで合成: 巻物と素材がなくなり、1ターン進む OK")
print("ALL_OK")
