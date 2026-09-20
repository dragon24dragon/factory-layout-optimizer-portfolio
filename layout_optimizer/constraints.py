# ユーザーが指定した配置条件を満たしているかを判定するファイル。
# 例：「製造と検査を隣接させる」「入庫と出庫を3m以上離す」
#
# 図形の計算そのものは geometry.py の関数に任せ、
# ここでは「条件を満たしているか」だけを答える。

from layout_optimizer.geometry import is_adjacent, minimum_separation_distance
from layout_optimizer.models import PlacedArea


def satisfies_adjacency_constraint(area_a: PlacedArea, area_b: PlacedArea) -> bool:
    """隣接条件「AとBをくっつける」を満たしているかを判定する。

    2つのエリアが辺を共有して隣接していれば True、それ以外は False。
    """
    # 隣接しているかの計算は geometry.py の is_adjacent に任せる
    return is_adjacent(area_a, area_b)


def satisfies_minimum_separation_constraint(
    area_a: PlacedArea,
    area_b: PlacedArea,
    minimum_distance: float,
) -> bool:
    """離隔条件「AとBを minimum_distance（m）以上離す」を満たしているかを判定する。

    実際の最短離隔距離が minimum_distance 以上なら True、未満なら False。
    ちょうど同じ距離の場合も True。
    """
    # 実際のすき間の計算は geometry.py の minimum_separation_distance に任せる
    actual_distance = minimum_separation_distance(area_a, area_b)

    # 指定した距離「以上」離れていればOK
    return actual_distance >= minimum_distance
