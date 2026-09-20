# 配置案を探すファイル。
#
# 1m 単位の整数座標を、左下から順番に試してエリアを置いていく。
# 条件（隣接・最低離隔）があると、先に置いたエリアの位置のせいで
# 後のエリアが置けなくなることがある。そのときは「バックトラッキング」を使う。
# バックトラッキング：行き止まりになったら1つ前のエリアに戻り、別の位置を試すやり方。
#
# 判定そのものは geometry.py と constraints.py に任せ、
# ここでは「どの順で試すか」「いつ戻るか」だけを書く。

from layout_optimizer.constraints import (
    satisfies_adjacency_constraint,
    satisfies_minimum_separation_constraint,
)
from layout_optimizer.distance import calculate_total_flow_distance
from layout_optimizer.geometry import is_inside_factory, is_overlapping
from layout_optimizer.models import Area, Factory, PlacedArea


def find_first_valid_layout(
    factory: Factory,
    areas: list[Area],
    adjacency_pairs: list[tuple[str, str]] | None = None,
    minimum_separations: list[tuple[str, str, float]] | None = None,
) -> list[PlacedArea]:
    """条件を満たす配置案を1つ作って返す。

    - エリアは入力の順番のまま置く。回転はしない
    - adjacency_pairs：隣接させるエリア名の組。例 [("製造", "検査")]
    - minimum_separations：離すエリア名の組と距離(m)。例 [("入庫", "出庫", 3.0)]
    - 条件を省略すると「工場内に収まる」「重ならない」だけで置く
    - 条件に存在しないエリア名がある／条件を満たす配置が無い場合は ValueError
    """
    # 探索は find_valid_layouts に任せ、1件だけ探して、その1件目を返す
    layouts = find_valid_layouts(
        factory,
        areas,
        adjacency_pairs=adjacency_pairs,
        minimum_separations=minimum_separations,
        max_layouts=1,
    )
    return layouts[0]


def find_valid_layouts(
    factory: Factory,
    areas: list[Area],
    adjacency_pairs: list[tuple[str, str]] | None = None,
    minimum_separations: list[tuple[str, str, float]] | None = None,
    max_layouts: int = 10,
) -> list[list[PlacedArea]]:
    """条件を満たす配置案を、最大 max_layouts 件まで集めて返す。

    - 返す形は [配置案1, 配置案2, ...]（配置案1つ＝ list[PlacedArea]）
    - 見つかった順（左下から詰めた順）に並ぶ。距離による並べ替えはしない
    - 同じ配置（名前・x・y がすべて同じ）は1回だけ入れる
    - areas が空なら [[]]（「空の配置」という1案がある扱い）
    - max_layouts が0以下／条件に存在しないエリア名がある／1件も見つからない場合は ValueError
    """
    if max_layouts < 1:
        raise ValueError("max_layouts は1以上を指定してください")

    # 条件の省略（None）は「条件なし」＝空のリストとして扱う
    if adjacency_pairs is None:
        adjacency_pairs = []
    if minimum_separations is None:
        minimum_separations = []

    # 1. 条件に書かれた名前が、すべて areas にあるか確かめる
    area_names = [area.name for area in areas]
    for name_a, name_b in adjacency_pairs:
        for name in (name_a, name_b):
            if name not in area_names:
                raise ValueError(f"隣接条件にある「{name}」のエリアが、エリアの一覧に見つかりません")
    for name_a, name_b, _distance in minimum_separations:
        for name in (name_a, name_b):
            if name not in area_names:
                raise ValueError(f"離隔条件にある「{name}」のエリアが、エリアの一覧に見つかりません")

    # 2. 0 番目のエリアから順に置いていき、見つかった配置案を layouts に集める
    layouts: list[list[PlacedArea]] = []
    seen_keys: set = set()  # すでに入れた配置案の「見分け用の形」を覚えておく
    collect_layouts(
        factory,
        areas,
        0,
        [],
        adjacency_pairs,
        minimum_separations,
        max_layouts,
        layouts,
        seen_keys,
    )

    if len(layouts) == 0:
        raise ValueError("条件を満たす配置が見つかりません")

    return layouts


def rank_layouts_by_flow_distance(
    layouts: list[list[PlacedArea]],
    process_order: list[str],
) -> list[tuple[list[PlacedArea], float]]:
    """各配置案の総動線距離を求め、距離が短い順に (配置案, 距離) の組を並べて返す。

    - 距離の計算は distance.py の calculate_total_flow_distance に任せる
    - 同じ距離の案は、元の layouts の順番のまま（Python の sort は順番を保つ「安定ソート」）
    - layouts が空なら []
    - process_order に配置案に無い名前があれば、calculate_total_flow_distance の ValueError がそのまま出る
    - 渡された layouts は書き換えず、新しいリストを作って返す
    """
    # 1. 各配置案に距離を付けて、(配置案, 距離) の組を作る
    ranked: list[tuple[list[PlacedArea], float]] = []
    for layout in layouts:
        distance = calculate_total_flow_distance(layout, process_order)
        ranked.append((layout, distance))

    # 2. 組の2番目（距離）が小さい順に並べる
    ranked.sort(key=get_distance)

    return ranked


def select_top_layouts(
    ranked_layouts: list[tuple[list[PlacedArea], float]],
    top_n: int = 3,
) -> list[tuple[list[PlacedArea], float]]:
    """距離順に並んだ結果の、先頭から top_n 件を返す。

    - ranked_layouts は rank_layouts_by_flow_distance が並べたもの（すでに距離が短い順）
    - この関数は距離の計算も並べ替えもしない。「先頭から取り出す」だけ
    - 件数が top_n より少なければ、あるだけ返す（エラーにしない）
    - ranked_layouts が空なら []
    - top_n が0以下なら ValueError
    """
    if top_n < 1:
        raise ValueError("top_n は1以上を指定してください")

    # リストの切り出し（スライス）。新しいリストが作られるので、元のリストは変わらない
    return ranked_layouts[:top_n]


def get_distance(ranked_item: tuple[list[PlacedArea], float]) -> float:
    """(配置案, 距離) の組から距離を取り出す。並べ替えの基準に使う。"""
    return ranked_item[1]


def layout_key(placed_areas: list[PlacedArea]) -> tuple:
    """配置案を、重複チェック用の形に変える。

    例：(("入庫", 0, 0), ("材料置場", 4, 0), ...)
    名前・x・y がすべて同じなら、同じ形になる。
    """
    return tuple((placed.area.name, placed.x, placed.y) for placed in placed_areas)


def collect_layouts(
    factory: Factory,
    areas: list[Area],
    index: int,
    placed_areas: list[PlacedArea],
    adjacency_pairs: list[tuple[str, str]],
    minimum_separations: list[tuple[str, str, float]],
    max_layouts: int,
    layouts: list[list[PlacedArea]],
    seen_keys: set,
) -> bool:
    """index 番目以降のエリアを置き、全部置けた配置案を layouts に集める（再帰的バックトラッキング）。

    max_layouts 件集まったら True を返し、呼び出し元もすぐ探索をやめる。
    まだ集まっていなければ False を返し、呼び出し元は次の位置を試し続ける。
    """
    # すべてのエリアを置き終わった → 1つの配置案ができた
    if index == len(areas):
        # 念のため、全部置いた状態ですべての条件をもう一度確かめる
        if satisfies_known_conditions(placed_areas, adjacency_pairs, minimum_separations):
            key = layout_key(placed_areas)
            if key not in seen_keys:
                seen_keys.add(key)
                # placed_areas はこのあと中身が変わるので、コピーを保存する
                layouts.append(list(placed_areas))

        # 上限に達したら True（探索終了）。まだなら False（探索を続ける）
        return len(layouts) >= max_layouts

    area = areas[index]

    # y（下から上）を外側、x（左から右）を内側にして、1m ずつ試す
    for y in range(factory.height):
        for x in range(factory.width):
            candidate = PlacedArea(area=area, x=x, y=y)

            # 1. 工場からはみ出すなら、この位置はだめ
            if not is_inside_factory(factory, candidate):
                continue

            # 2. すでに置いたエリアのどれかと重なるなら、この位置はだめ
            if overlaps_any(candidate, placed_areas):
                continue

            # 3. 仮に置いてみて、今の時点で確かめられる条件を満たすか調べる
            placed_areas.append(candidate)
            if satisfies_known_conditions(placed_areas, adjacency_pairs, minimum_separations):
                # 4. 次のエリアへ進む。上限まで集まったら、ここでもすぐ終了する
                if collect_layouts(
                    factory,
                    areas,
                    index + 1,
                    placed_areas,
                    adjacency_pairs,
                    minimum_separations,
                    max_layouts,
                    layouts,
                    seen_keys,
                ):
                    placed_areas.pop()
                    return True

            # 5. 取り除いて、次の位置を試す（ここが「1つ前に戻る」部分）
            #    配置案が見つかったあとも、ここから別の位置を試し続ける
            placed_areas.pop()

    # この index のエリアの位置をすべて試し終わった → 呼び出し元（1つ前のエリア）に戻る
    return False


def overlaps_any(candidate: PlacedArea, placed_areas: list[PlacedArea]) -> bool:
    """candidate が、置き済みのどれか1つとでも重なっていれば True。"""
    for other in placed_areas:
        if is_overlapping(candidate, other):
            return True
    return False


def satisfies_known_conditions(
    placed_areas: list[PlacedArea],
    adjacency_pairs: list[tuple[str, str]],
    minimum_separations: list[tuple[str, str, float]],
) -> bool:
    """両方のエリアが置き済みの条件だけを確かめる。片方しか無い条件は保留（合格扱い）。"""
    # エリア名から PlacedArea を探せる辞書を作る
    placed_by_name = {placed.area.name: placed for placed in placed_areas}

    # 隣接条件
    for name_a, name_b in adjacency_pairs:
        if name_a in placed_by_name and name_b in placed_by_name:
            if not satisfies_adjacency_constraint(placed_by_name[name_a], placed_by_name[name_b]):
                return False

    # 最低離隔条件
    for name_a, name_b, distance in minimum_separations:
        if name_a in placed_by_name and name_b in placed_by_name:
            if not satisfies_minimum_separation_constraint(
                placed_by_name[name_a], placed_by_name[name_b], distance
            ):
                return False

    return True
