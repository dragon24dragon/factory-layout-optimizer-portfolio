# constraints.py の関数が正しく動くかを、pytest で自動確認するファイル。
# 図形の細かい計算は test_geometry.py で確認済みなので、
# ここでは「条件を満たしているか」の答えが正しいかを確かめる。

from layout_optimizer.constraints import (
    satisfies_adjacency_constraint,
    satisfies_minimum_separation_constraint,
)
from layout_optimizer.models import Area, PlacedArea

# すべてのテストで使うエリア（幅6×高さ4）
# A は (0, 0) に置いて、横 0〜6、縦 0〜4 を占める
AREA = Area(name="製造", width=6, height=4)


# ---- 隣接条件のテスト ----

def test_隣接条件_辺で隣接している():
    # A の右端6と B の左端6が接する
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert satisfies_adjacency_constraint(a, b) is True


def test_隣接条件_角だけ接触している():
    # (6, 4) の1点だけで触れている。隣接とはみなさない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=4)
    assert satisfies_adjacency_constraint(a, b) is False


def test_隣接条件_面積が重なっている():
    # 重なっていると隣接とはみなさない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=4, y=2)
    assert satisfies_adjacency_constraint(a, b) is False


def test_隣接条件_離れている():
    # B は横 10〜16。4m のすき間がある
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=10, y=0)
    assert satisfies_adjacency_constraint(a, b) is False


# ---- 最低離隔条件のテスト ----

def test_離隔条件_指定より大きく離れている():
    # 実際のすき間 4m（B は横 10〜16）、指定 3m → 満たす
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=10, y=0)
    assert satisfies_minimum_separation_constraint(a, b, 3.0) is True


def test_離隔条件_指定とちょうど同じ距離():
    # 実際のすき間 3m（B は横 9〜15）、指定 3m → 「以上」なので満たす
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=9, y=0)
    assert satisfies_minimum_separation_constraint(a, b, 3.0) is True


def test_離隔条件_指定より近い():
    # 実際のすき間 2m（B は横 8〜14）、指定 3m → 満たさない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=8, y=0)
    assert satisfies_minimum_separation_constraint(a, b, 3.0) is False


def test_離隔条件_接触していて指定0m():
    # 辺が接していてすき間 0m、指定 0m → 満たす
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert satisfies_minimum_separation_constraint(a, b, 0.0) is True


def test_離隔条件_接触していて指定1m():
    # 辺が接していてすき間 0m、指定 1m → 満たさない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert satisfies_minimum_separation_constraint(a, b, 1.0) is False


def test_離隔条件_AとBを入れ替えても同じ結果():
    # 渡す順番を逆にしても、答えは変わらないはず（すき間 2m、指定 3m）
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=8, y=0)
    result_ab = satisfies_minimum_separation_constraint(a, b, 3.0)
    result_ba = satisfies_minimum_separation_constraint(b, a, 3.0)
    assert result_ab == result_ba
