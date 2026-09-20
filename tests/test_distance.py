# distance.py の関数が正しく動くかを、pytest で自動確認するファイル。
# 区間ごとの距離の細かい計算は test_geometry.py で確認済みなので、
# ここでは「工程順に正しく足し合わせているか」を確かめる。

import pytest  # pytest.approx（小数の比較）と pytest.raises（エラーの確認）に使う

from layout_optimizer.distance import calculate_total_flow_distance
from layout_optimizer.models import Area, PlacedArea
from layout_optimizer.sample_data import SAMPLE_AREAS, SAMPLE_PROCESS_ORDER

# テスト用の配置（どれも幅6×高さ4。中心点は左下 ＋ (3, 2)）
#   入庫：(0, 0)  に置く → 中心 (3, 2)
#   製造：(10, 0) に置く → 中心 (13, 2)
#   出庫：(10, 8) に置く → 中心 (13, 10)
RECEIVING = PlacedArea(area=Area(name="入庫", width=6, height=4), x=0, y=0)
MANUFACTURING = PlacedArea(area=Area(name="製造", width=6, height=4), x=10, y=0)
SHIPPING = PlacedArea(area=Area(name="出庫", width=6, height=4), x=10, y=8)
PLACED_AREAS = [RECEIVING, MANUFACTURING, SHIPPING]


def test_3つのエリアを順番に移動した総距離():
    # 入庫→製造：横10＋縦0＝10、製造→出庫：横0＋縦8＝8、合計18
    order = ["入庫", "製造", "出庫"]
    assert calculate_total_flow_distance(PLACED_AREAS, order) == pytest.approx(18.0)


def test_工程の順番を変えると総距離も変わる():
    # 入庫→出庫：横10＋縦8＝18、出庫→製造：横0＋縦8＝8、合計26
    # 「入庫→製造→出庫」の18とは違う値になる
    order = ["入庫", "出庫", "製造"]
    assert calculate_total_flow_distance(PLACED_AREAS, order) == pytest.approx(26.0)


def test_工程が1件なら0():
    # 移動する区間が無い
    order = ["入庫"]
    assert calculate_total_flow_distance(PLACED_AREAS, order) == pytest.approx(0.0)


def test_工程が空なら0():
    # 工程が1つも無い
    order = []
    assert calculate_total_flow_distance(PLACED_AREAS, order) == pytest.approx(0.0)


def test_配置に無いエリア名があるとValueError():
    # 「検査」は PLACED_AREAS に入っていないので、エラーになるはず
    order = ["入庫", "検査"]
    with pytest.raises(ValueError):
        calculate_total_flow_distance(PLACED_AREAS, order)


def test_工程が1件でも配置に無いエリア名ならValueError():
    # 工程順序に書いた名前は、移動距離が0になる場合でも
    # 必ず配置データに存在していなければならない
    placed = [RECEIVING]  # 配置には「入庫」だけがある
    order = ["存在しないエリア"]
    with pytest.raises(ValueError):
        calculate_total_flow_distance(placed, order)


def test_中心点が小数になるエリアを含む():
    # 材料置場（5×3）を (0, 0) に置くと中心は (2.5, 1.5)
    # 材料置場→製造：横10.5＋縦0.5＝11、製造→出庫：8、合計19
    materials = PlacedArea(area=Area(name="材料置場", width=5, height=3), x=0, y=0)
    placed = [materials, MANUFACTURING, SHIPPING]
    order = ["材料置場", "製造", "出庫"]
    assert calculate_total_flow_distance(placed, order) == pytest.approx(19.0)


def test_工程が2件だけ():
    # 入庫→製造の1区間だけ：横10＋縦0＝10
    order = ["入庫", "製造"]
    assert calculate_total_flow_distance(PLACED_AREAS, order) == pytest.approx(10.0)


def test_サンプルデータの6工程():
    # sample_data.py の6エリアを、下の段と上の段に並べて置く
    #   下の段（y=0）：入庫 x=0、材料置場 x=4、製造 x=9
    #   上の段（y=6）：検査 x=14、梱包 x=9、出庫 x=4
    positions = {
        "入庫": (0, 0),      # 4×3 → 中心 (2, 1.5)
        "材料置場": (4, 0),  # 5×3 → 中心 (6.5, 1.5)
        "製造": (9, 0),      # 6×4 → 中心 (12, 2)
        "検査": (14, 6),     # 4×3 → 中心 (16, 7.5)
        "梱包": (9, 6),      # 4×3 → 中心 (11, 7.5)
        "出庫": (4, 6),      # 4×3 → 中心 (6, 7.5)
    }
    placed = []
    for area in SAMPLE_AREAS:
        x, y = positions[area.name]
        placed.append(PlacedArea(area=area, x=x, y=y))

    # 入庫→材料置場 4.5、材料置場→製造 6.0、製造→検査 9.5、
    # 検査→梱包 5.0、梱包→出庫 5.0、合計 30.0
    assert calculate_total_flow_distance(placed, SAMPLE_PROCESS_ORDER) == pytest.approx(30.0)
