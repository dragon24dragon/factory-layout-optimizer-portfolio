# 位置や形に関する判定をまとめるファイル。
# 今は「工場の中に収まっているか」だけを判定する。

import math  # 直線距離の計算（math.hypot）に使う

from layout_optimizer.models import Factory, PlacedArea


def is_inside_factory(factory: Factory, placed_area: PlacedArea) -> bool:
    """置いたエリアが、工場の範囲内に完全に収まっているかを判定する。

    工場の左下を (0, 0) とし、placed_area の (x, y) はエリアの左下の角とする。
    工場の境界線ぴったりに接している場合は「収まっている」(True) とみなす。
    """
    # エリアの4辺の位置を求める
    left = placed_area.x
    bottom = placed_area.y
    right = placed_area.x + placed_area.area.width
    top = placed_area.y + placed_area.area.height

    # 左や下にはみ出していないか（マイナスの位置はNG）
    if left < 0 or bottom < 0:
        return False

    # 右や上にはみ出していないか（ぴったりはOK）
    if right > factory.width or top > factory.height:
        return False

    # どこにもはみ出していなければ、工場内に収まっている
    return True


def is_overlapping(area_a: PlacedArea, area_b: PlacedArea) -> bool:
    """置いた2つのエリアが、面積として重なっているかを判定する。

    辺が接しているだけ、角が接しているだけの場合は重なりではない (False)。
    一方がもう一方の中に入っている場合や、同じ位置・同じ大きさの場合は重なり (True)。
    """
    # エリアAの4辺の位置
    a_left = area_a.x
    a_right = area_a.x + area_a.area.width
    a_bottom = area_a.y
    a_top = area_a.y + area_a.area.height

    # エリアBの4辺の位置
    b_left = area_b.x
    b_right = area_b.x + area_b.area.width
    b_bottom = area_b.y
    b_top = area_b.y + area_b.area.height

    # 横方向で完全に離れているか（辺がぴったり接するのも「離れている」に含める）
    separated_horizontally = a_right <= b_left or b_right <= a_left

    # 縦方向で完全に離れているか（こちらも接するだけなら「離れている」）
    separated_vertically = a_top <= b_bottom or b_top <= a_bottom

    # どちらかの方向で離れていれば重ならない。どちらでもなければ重なっている
    if separated_horizontally or separated_vertically:
        return False
    return True


def is_adjacent(area_a: PlacedArea, area_b: PlacedArea) -> bool:
    """置いた2つのエリアが、辺を共有して隣接しているかを判定する。

    辺どうしが長さ0より大きく接していれば隣接 (True)。
    角だけ接している・面積が重なっている・離れている場合は隣接ではない (False)。
    """
    # 面積が重なっていたら、隣接ではない（同じ位置・同じ大きさもここで除外される）
    if is_overlapping(area_a, area_b):
        return False

    # エリアAの4辺の位置
    a_left = area_a.x
    a_right = area_a.x + area_a.area.width
    a_bottom = area_a.y
    a_top = area_a.y + area_a.area.height

    # エリアBの4辺の位置
    b_left = area_b.x
    b_right = area_b.x + area_b.area.width
    b_bottom = area_b.y
    b_top = area_b.y + area_b.area.height

    # 左右で接しているか（Aの右端＝Bの左端、またはBの右端＝Aの左端）
    if a_right == b_left or b_right == a_left:
        # 縦方向で接している部分の長さ ＝ 上端の小さいほう − 下端の大きいほう
        shared_length = min(a_top, b_top) - max(a_bottom, b_bottom)
        # 長さが0より大きければ辺を共有している（0なら角だけ）
        if shared_length > 0:
            return True

    # 上下で接しているか（Aの上端＝Bの下端、またはBの上端＝Aの下端）
    if a_top == b_bottom or b_top == a_bottom:
        # 横方向で接している部分の長さ ＝ 右端の小さいほう − 左端の大きいほう
        shared_length = min(a_right, b_right) - max(a_left, b_left)
        if shared_length > 0:
            return True

    # どの辺も共有していない
    return False


def minimum_separation_distance(area_a: PlacedArea, area_b: PlacedArea) -> float:
    """置いた2つのエリアの、いちばん近い部分どうしの直線距離（m）を返す。

    重なっている・辺が接している・角が接している場合は 0.0。
    「入庫と出庫を3m以上離す」のような離隔条件に使う。
    """
    # エリアAの4辺の位置
    a_left = area_a.x
    a_right = area_a.x + area_a.area.width
    a_bottom = area_a.y
    a_top = area_a.y + area_a.area.height

    # エリアBの4辺の位置
    b_left = area_b.x
    b_right = area_b.x + area_b.area.width
    b_bottom = area_b.y
    b_top = area_b.y + area_b.area.height

    # 横のすき間 dx
    #   BがAの右にあれば「Bの左端 − Aの右端」がプラスになる
    #   BがAの左にあれば「Aの左端 − Bの右端」がプラスになる
    #   横に重なる・接するときは両方0以下なので、0 が選ばれる
    dx = max(0, b_left - a_right, a_left - b_right)

    # 縦のすき間 dy（考え方は横と同じ）
    dy = max(0, b_bottom - a_top, a_bottom - b_top)

    # 三平方の定理で直線距離にする（√(dx² + dy²)）
    return float(math.hypot(dx, dy))


def center_manhattan_distance(area_a: PlacedArea, area_b: PlacedArea) -> float:
    """置いた2つのエリアの、中心点どうしのマンハッタン距離（m）を返す。

    マンハッタン距離 ＝ 横の差 ＋ 縦の差（斜めには進まない距離）。
    工場内を縦・横に移動する距離の簡易的な目安として、総動線距離の計算に使う。
    """
    # 中心点 ＝ 左下の角 ＋ 幅や高さの半分
    # 「/」は割り算の結果を小数で返すので、幅5なら 2.5 のようになる
    a_center_x = area_a.x + area_a.area.width / 2
    a_center_y = area_a.y + area_a.area.height / 2
    b_center_x = area_b.x + area_b.area.width / 2
    b_center_y = area_b.y + area_b.area.height / 2

    # 横の差と縦の差を、それぞれプラスの値にして（abs＝絶対値）足す
    return float(abs(a_center_x - b_center_x) + abs(a_center_y - b_center_y))
