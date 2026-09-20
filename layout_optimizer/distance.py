# 1つの配置案について、工程順序どおりに移動した総動線距離を計算するファイル。
#
# 区間ごとの距離の計算は geometry.py の center_manhattan_distance に任せ、
# ここでは「工程順に並べて、足し合わせる」だけを担当する。

from layout_optimizer.geometry import center_manhattan_distance
from layout_optimizer.models import PlacedArea


def calculate_total_flow_distance(
    placed_areas: list[PlacedArea],
    process_order: list[str],
) -> float:
    """工程順序に沿ってエリアを移動したときの、総動線距離（m）を返す。

    例：工程順序が ["入庫", "製造", "出庫"] なら、
    「入庫→製造」と「製造→出庫」の2区間の距離を足す。

    工程順序が0件または1件なら、移動が無いので 0.0。
    工程順序にある名前のエリアが placed_areas に無ければ ValueError を出す。
    """
    # 1. エリア名から PlacedArea を探せる辞書を作る
    #    例：{"入庫": 入庫のPlacedArea, "製造": 製造のPlacedArea, ...}
    areas_by_name = {}
    for placed_area in placed_areas:
        areas_by_name[placed_area.area.name] = placed_area

    # 2. 工程順序にある名前が、すべて配置されているか確かめる
    for name in process_order:
        if name not in areas_by_name:
            raise ValueError(f"工程順序にある「{name}」のエリアが、配置の中に見つかりません")

    # 3. 隣り合う2つの工程ごとに距離を求めて、足していく
    #    6工程なら i = 0〜4 の5区間（0番→1番、1番→2番、…、4番→5番）
    total_distance = 0.0
    for i in range(len(process_order) - 1):
        from_area = areas_by_name[process_order[i]]
        to_area = areas_by_name[process_order[i + 1]]
        total_distance += center_manhattan_distance(from_area, to_area)

    return total_distance
