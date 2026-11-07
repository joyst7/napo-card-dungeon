"""テストを全部実行する:  python3 tests/run_all.py
画面も保存したいとき:  SHOT_OUT=/保存先フォルダ python3 tests/run_all.py
（Pyxelは1つのプロセスで1回しか初期化できないので、テストは1ファイルずつ別プロセスで動かす）"""
import glob
import os
import subprocess
import sys
import time

here = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(here, "test_*.py")))
if len(sys.argv) > 1:
    files = [f for f in files if any(k in os.path.basename(f) for k in sys.argv[1:])]
bad = []
for f in files:
    t0 = time.time()
    r = subprocess.run([sys.executable, f], capture_output=True, text=True,
                       env=dict(os.environ, NAPO_MUTE="1"))   # テスト中は音を出さない
    ok = r.returncode == 0 and "ALL_OK" in r.stdout
    print(f"{'OK ' if ok else 'NG '} {os.path.basename(f)}  ({time.time() - t0:.0f}秒)")
    if not ok:
        bad.append(f)
        print((r.stdout + r.stderr)[-1500:])
print("すべて成功" if not bad else f"失敗 {len(bad)} 件")
sys.exit(1 if bad else 0)
