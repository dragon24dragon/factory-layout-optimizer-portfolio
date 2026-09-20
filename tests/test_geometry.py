# geometry.py の関数が正しく動くかを、pytest で自動確認するファイル。
# pytest は「test_ で始まる関数」を見つけて、順番に実行してくれる。
# assert（アサート）は「この式が正しいはず」という確認。違えばテスト失敗になる。

import pytest  # 小数を「だいたい等しいか」で比べる pytest.approx に使う

from layout_optimizer.geometry import (
    center_manhattan_distance,
    is_adjacent,
    is_inside_factory,
    is_overlapping,
    minimum_separation_distance,
)
from layout_optimizer.models import Area, Factory, PlacedArea

# すべてのテストで使う工場とエリア
FACTORY = Factory(width=20, height=15)
AREA = Area(name="製造", width=6, height=4)


# ---- is_inside_factory のテスト ----

def test_普通に工場内():
    # 右端11・上端11。工場（20×15）に余裕を持って収まる
    placed = PlacedArea(area=AREA, x=5, y=7)
    assert is_inside_factory(FACTORY, placed) is True


def test_右にはみ出す():
    # 右端が 16 + 6 = 22 になり、工場の幅20を超える
    placed = PlacedArea(area=AREA, x=16, y=7)
    assert is_inside_factory(FACTORY, placed) is False


def test_境界ぴったり():
    # 右端 14 + 6 = 20、上端 11 + 4 = 15。境界ぴったりはOK
    placed = PlacedArea(area=AREA, x=14, y=11)
    assert is_inside_factory(FACTORY, placed) is True


def test_xがマイナス():
    # 左端が -1 で、工場の左にはみ出している
    placed = PlacedArea(area=AREA, x=-1, y=5)
    assert is_inside_factory(FACTORY, placed) is False


def test_yがマイナス():
    # 下端が -1 で、工場の下にはみ出している
    placed = PlacedArea(area=AREA, x=5, y=-1)
    assert is_inside_factory(FACTORY, placed) is False


def test_上にはみ出す():
    # 上端が 12 + 4 = 16 になり、工場の高さ15を超える
    placed = PlacedArea(area=AREA, x=5, y=12)
    assert is_inside_factory(FACTORY, placed) is False


def test_左下の角():
    # 工場の左下 (0, 0) にぴったり置く。これもOK
    placed = PlacedArea(area=AREA, x=0, y=0)
    assert is_inside_factory(FACTORY, placed) is True


# ---- is_overlapping のテスト ----
# AREA は幅6×高さ4。(0, 0) に置くと、横 0〜6、縦 0〜4 を占める。

# 中に入れる用の小さいエリア（幅2×高さ2）
SMALL_AREA = Area(name="小物", width=2, height=2)


def test_一部が重なる():
    # A：横 0〜6、縦 0〜4 ／ B：横 4〜10、縦 2〜6。右上の一部が重なる
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=4, y=2)
    assert is_overlapping(a, b) is True


def test_一方がもう一方の中に完全に入る():
    # 小さいエリア（横 2〜4、縦 1〜3）が、大きいエリア（横 0〜6、縦 0〜4）の中にある
    big = PlacedArea(area=AREA, x=0, y=0)
    small = PlacedArea(area=SMALL_AREA, x=2, y=1)
    assert is_overlapping(big, small) is True


def test_横方向に離れている():
    # A の右端6、B の左端10。すき間がある
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=10, y=0)
    assert is_overlapping(a, b) is False


def test_縦方向に離れている():
    # A の上端4、B の下端8。すき間がある
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=0, y=8)
    assert is_overlapping(a, b) is False


def test_辺だけ接している():
    # A の右端6と B の左端6がぴったり接する。面積は重ならない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert is_overlapping(a, b) is False


def test_角だけ接している():
    # A の右上の角 (6, 4) と B の左下の角 (6, 4) だけが触れている
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=4)
    assert is_overlapping(a, b) is False


def test_同じ位置_同じ大きさ():
    # まったく同じ場所に同じ大きさで置くと、全面が重なる
    a = PlacedArea(area=AREA, x=5, y=7)
    b = PlacedArea(area=AREA, x=5, y=7)
    assert is_overlapping(a, b) is True


# ---- is_adjacent のテスト ----
# ここでも A は (0, 0) に置いた AREA（横 0〜6、縦 0〜4）を基本にする。

def test_隣接_右辺と左辺が接する():
    # A の右端6と B の左端6が、縦 0〜4 の長さ4で接する
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert is_adjacent(a, b) is True


def test_隣接_上辺と下辺が接する():
    # A の上端4と B の下端4が、横 0〜6 の長さ6で接する
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=0, y=4)
    assert is_adjacent(a, b) is True


def test_隣接_辺の一部分だけ接する():
    # B は縦 2〜6。A（縦 0〜4）と接するのは縦 2〜4 の長さ2だけ。それでも隣接
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=2)
    assert is_adjacent(a, b) is True


def test_隣接_角だけ接する():
    # (6, 4) の1点だけが触れている。接する長さが0なので隣接ではない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=4)
    assert is_adjacent(a, b) is False


def test_隣接_端はそろうが縦にずれて触れていない():
    # A の右端6と B の左端6は同じだが、B は縦 5〜9 で A（縦 0〜4）と触れていない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=5)
    assert is_adjacent(a, b) is False


def test_隣接_少し離れる():
    # A の右端6、B の左端7。1m のすき間がある
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=7, y=0)
    assert is_adjacent(a, b) is False


def test_隣接_面積が重なる():
    # 重なっているものは隣接とはみなさない
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=4, y=2)
    assert is_adjacent(a, b) is False


def test_隣接_同じ位置_同じ大きさ():
    # 全面が重なっているので隣接ではない
    a = PlacedArea(area=AREA, x=5, y=7)
    b = PlacedArea(area=AREA, x=5, y=7)
    assert is_adjacent(a, b) is False


def test_隣接_完全に離れる():
    # 横にも縦にも大きく離れている
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=12, y=10)
    assert is_adjacent(a, b) is False


# ---- minimum_separation_distance のテスト ----
# ここでも A は (0, 0) に置いた AREA（横 0〜6、縦 0〜4）を基本にする。

def test_離隔_横方向に3m離れている():
    # B は横 9〜15。A の右端6との間に 3m のすき間
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=9, y=0)
    assert minimum_separation_distance(a, b) == 3.0


def test_離隔_縦方向に4m離れている():
    # B は縦 8〜12。A の上端4との間に 4m のすき間
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=0, y=8)
    assert minimum_separation_distance(a, b) == 4.0


def test_離隔_横3m_縦4m離れている():
    # B は横 9〜15・縦 8〜12。角どうしの直線距離は √(3² + 4²) = 5
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=9, y=8)
    assert minimum_separation_distance(a, b) == 5.0


def test_離隔_辺が接している():
    # A の右端6と B の左端6がぴったり接する。すき間は無い
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=0)
    assert minimum_separation_distance(a, b) == 0.0


def test_離隔_角だけ接している():
    # (6, 4) の1点で触れている。すき間は無い
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=6, y=4)
    assert minimum_separation_distance(a, b) == 0.0


def test_離隔_面積が重なっている():
    # 重なっているときも 0.0
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=4, y=2)
    assert minimum_separation_distance(a, b) == 0.0


def test_離隔_一方がもう一方の中にある():
    # 小さいエリア（横 2〜4、縦 1〜3）が A の中にある
    big = PlacedArea(area=AREA, x=0, y=0)
    small = PlacedArea(area=SMALL_AREA, x=2, y=1)
    assert minimum_separation_distance(big, small) == 0.0


def test_離隔_AとBを入れ替えても同じ距離():
    # 渡す順番を逆にしても、距離は変わらないはず
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=9, y=8)
    assert minimum_separation_distance(a, b) == minimum_separation_distance(b, a)


# ---- center_manhattan_distance のテスト ----
# AREA（幅6×高さ4）を (x, y) に置くと、中心点は (x + 3, y + 2)。
# (0, 0) に置いた A の中心点は (3, 2)。

# 幅も高さも奇数のエリア（中心点が小数になる）
ODD_AREA = Area(name="材料置場", width=5, height=3)


def test_中心_横と縦の両方に離れている():
    # A の中心 (3, 2)、B の中心 (8, 5)。横5 ＋ 縦3 ＝ 8
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=5, y=3)
    assert center_manhattan_distance(a, b) == pytest.approx(8.0)


def test_中心_横方向だけ離れている():
    # A の中心 (3, 2)、B の中心 (12, 2)。横9 ＋ 縦0 ＝ 9
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=9, y=0)
    assert center_manhattan_distance(a, b) == pytest.approx(9.0)


def test_中心_縦方向だけ離れている():
    # A の中心 (3, 2)、B の中心 (3, 10)。横0 ＋ 縦8 ＝ 8
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=0, y=8)
    assert center_manhattan_distance(a, b) == pytest.approx(8.0)


def test_中心_大きさは違うが中心点が同じ():
    # 大きいエリアの中心 (3, 2)、小さいエリア（2×2 を (2, 1) に置く）の中心も (3, 2)
    big = PlacedArea(area=AREA, x=0, y=0)
    small = PlacedArea(area=SMALL_AREA, x=2, y=1)
    assert center_manhattan_distance(big, small) == pytest.approx(0.0)


def test_中心_奇数の大きさで中心点が小数になる():
    # 5×3 を (0, 0) に置くと中心は (2.5, 1.5)
    # B（AREA を (10, 0)）の中心は (13, 2)。横10.5 ＋ 縦0.5 ＝ 11
    a = PlacedArea(area=ODD_AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=10, y=0)
    assert center_manhattan_distance(a, b) == pytest.approx(11.0)


def test_中心_AとBを入れ替えても同じ距離():
    # 渡す順番を逆にしても、距離は変わらないはず
    a = PlacedArea(area=ODD_AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=10, y=0)
    assert center_manhattan_distance(a, b) == pytest.approx(center_manhattan_distance(b, a))


def test_中心_重なっていても中心点がずれていれば0ではない():
    # A の中心 (3, 2)、B の中心 (7, 4)。面積は重なっているが、横4 ＋ 縦2 ＝ 6
    a = PlacedArea(area=AREA, x=0, y=0)
    b = PlacedArea(area=AREA, x=4, y=2)
    assert is_overlapping(a, b) is True  # 本当に重なっていることを確認
    assert center_manhattan_distance(a, b) == pytest.approx(6.0)


def test_中心_同じ位置_同じ大きさ():
    # まったく同じ場所なので、中心点も同じ
    a = PlacedArea(area=AREA, x=5, y=7)
    b = PlacedArea(area=AREA, x=5, y=7)
    assert center_manhattan_distance(a, b) == pytest.approx(0.0)
