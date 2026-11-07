"""ボットで数回遊び、途中で止まったり例外が出たりしないことを確かめる。"""
import os
import sys

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJ, "tools"))
import bot  # noqa: E402

res = bot.run(6, 0, seed=4)
for r in res:
    print(r["floor"], r["cause"], r["turns"])
    assert not r["stuck"], "ボットが止まった"
assert any(r["floor"] >= 3 for r in res)
print("ALL_OK")
