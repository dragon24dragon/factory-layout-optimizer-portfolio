# heuristic_search.py の関数が正しく動くかを、pytest で自動確認するファイル。
# 「置いた結果が条件を満たしているか」を geometry.py の判定で確かめる。

import pytest  # pytest.raises（エラーの確認）に使う

from layout_optimizer.constraints import (
    satisfies_adjacency_constraint,
    satisfies_minimum_separation_constraint,
)
from layout_optimizer.geometry import is_inside_factory, is_overlapping
from layout_optimizer.distance import calculate_total_flow_distance
from layout_optimizer.heuristic_search import (
    find_first_valid_layout,
    find_valid_layouts,
    rank_layouts_by_flow_distance,
    select_top_layouts,
)
from layout_optimizer.models import Area, Factory, PlacedArea
from layout_optimizer.sample_data import SAMPLE_AREAS, SAMPLE_FACTORY, SAMPLE_PROCESS_ORDER

# テスト用の小さな工場とエリア
SMALL_FACTORY = Factory(width=10, height=5)
AREA_A = Area(name="A", width=4, height=3)
AREA_B = Area(name="B", width=3, height=2)


def assert_all_inside(factory, layout):
    """すべてのエリアが工場内に収まっていることを確かめる。"""
    for placed in layout:
        assert is_inside_factory(factory, placed)


def assert_no_overlaps(layout):
    """どの2つのエリアも重なっていないことを確かめる。"""
    # i 番目と、それより後ろの j 番目の組み合わせをすべて比べる
    for i in range(len(layout)):
        for j in range(i + 1, len(layout)):
            assert not is_overlapping(layout[i], layout[j])


def test_小さな工場に2エリアの配置案を作れる():
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    # 左下から詰めるので、A は (0, 0)、B は A の右隣 (4, 0) に置かれる
    assert (layout[0].x, layout[0].y) == (0, 0)
    assert (layout[1].x, layout[1].y) == (4, 0)


def test_返る要素数が入力したエリア数と同じ():
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    assert len(layout) == 2


def test_すべてのエリアが工場内に収まる():
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    assert_all_inside(SMALL_FACTORY, layout)


def test_どの2エリアも重ならない():
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    assert_no_overlaps(layout)


def test_入力した順番のまま返る():
    # わざと B → A の順で渡す
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_B, AREA_A])
    assert [placed.area for placed in layout] == [AREA_B, AREA_A]


def test_エリアが1つだけでも置ける():
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A])
    assert len(layout) == 1
    assert (layout[0].x, layout[0].y) == (0, 0)


def test_エリアが空なら空のリスト():
    assert find_first_valid_layout(SMALL_FACTORY, []) == []


def test_工場より大きいエリアはValueError():
    too_big = Area(name="大きすぎる", width=11, height=3)
    with pytest.raises(ValueError):
        find_first_valid_layout(SMALL_FACTORY, [too_big])


def test_置く余地がなくなったらValueError():
    # 4×2 の工場を、1つ目の 4×2 のエリアでちょうど埋めてしまう
    # → 2つ目の 1×1 はどこにも置けない
    factory = Factory(width=4, height=2)
    full = Area(name="全面", width=4, height=2)
    small = Area(name="小", width=1, height=1)
    with pytest.raises(ValueError):
        find_first_valid_layout(factory, [full, small])


def test_サンプルの6エリアをすべて配置できる():
    layout = find_first_valid_layout(SAMPLE_FACTORY, SAMPLE_AREAS)
    assert len(layout) == 6
    assert [placed.area for placed in layout] == SAMPLE_AREAS
    assert_all_inside(SAMPLE_FACTORY, layout)
    assert_no_overlaps(layout)
    # x, y が整数になっている
    for placed in layout:
        assert isinstance(placed.x, int)
        assert isinstance(placed.y, int)


# ------------------------------------------------------------
# ここから第二段階：隣接条件・最低離隔条件つきの探索
# ------------------------------------------------------------

AREA_C = Area(name="C", width=3, height=2)


def find_by_name(layout, name):
    """配置案の中から、名前が name の PlacedArea を探して返す。"""
    for placed in layout:
        if placed.area.name == name:
            return placed
    raise AssertionError(f"{name} が配置案にありません")


def test_隣接条件を1つ指定すると満たす配置になる():
    # A, C, B の順に置く。何もしなければ B は A から離れた位置に置かれる
    layout = find_first_valid_layout(
        SMALL_FACTORY, [AREA_A, AREA_C, AREA_B], adjacency_pairs=[("A", "B")]
    )
    assert len(layout) == 3
    assert satisfies_adjacency_constraint(find_by_name(layout, "A"), find_by_name(layout, "B"))


def test_最低離隔条件を1つ指定すると満たす配置になる():
    layout = find_first_valid_layout(
        SMALL_FACTORY, [AREA_A, AREA_B], minimum_separations=[("A", "B", 3.0)]
    )
    assert len(layout) == 2
    assert satisfies_minimum_separation_constraint(
        find_by_name(layout, "A"), find_by_name(layout, "B"), 3.0
    )


def test_隣接条件と最低離隔条件を同時に満たす配置になる():
    layout = find_first_valid_layout(
        SMALL_FACTORY,
        [AREA_A, AREA_B, AREA_C],
        adjacency_pairs=[("A", "B")],
        minimum_separations=[("A", "C", 3.0)],
    )
    assert satisfies_adjacency_constraint(find_by_name(layout, "A"), find_by_name(layout, "B"))
    assert satisfies_minimum_separation_constraint(
        find_by_name(layout, "A"), find_by_name(layout, "C"), 3.0
    )


def test_物理的に不可能な隣接条件はValueError():
    # 幅3×高さ1 の工場に 1×1 を3つ置くと、一列に並ぶしかない
    # 「3つとも互いに隣接」は、両端どうしがくっつけないので不可能
    factory = Factory(width=3, height=1)
    areas = [Area(name=n, width=1, height=1) for n in ["P", "Q", "R"]]
    with pytest.raises(ValueError):
        find_first_valid_layout(
            factory, areas, adjacency_pairs=[("P", "Q"), ("Q", "R"), ("P", "R")]
        )


def test_物理的に不可能な最低離隔条件はValueError():
    # 幅5×高さ1 の工場では、10m 以上離すことはできない
    factory = Factory(width=5, height=1)
    areas = [Area(name="P", width=1, height=1), Area(name="Q", width=1, height=1)]
    with pytest.raises(ValueError):
        find_first_valid_layout(factory, areas, minimum_separations=[("P", "Q", 10.0)])


def test_条件を指定しなければ第一段階と同じ配置になる():
    # 条件なしの呼び方では、左下から詰めた位置になる
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    assert [(p.x, p.y) for p in layout] == [(0, 0), (4, 0)]

    sample_layout = find_first_valid_layout(SAMPLE_FACTORY, SAMPLE_AREAS)
    assert [(p.x, p.y) for p in sample_layout] == [
        (0, 0), (4, 0), (9, 0), (15, 0), (0, 3), (4, 3)
    ]


def test_隣接条件に存在しないエリア名があるとValueError():
    with pytest.raises(ValueError):
        find_first_valid_layout(
            SMALL_FACTORY, [AREA_A, AREA_B], adjacency_pairs=[("A", "存在しない")]
        )


def test_離隔条件に存在しないエリア名があるとValueError():
    with pytest.raises(ValueError):
        find_first_valid_layout(
            SMALL_FACTORY, [AREA_A, AREA_B], minimum_separations=[("存在しない", "B", 3.0)]
        )


def test_条件つきの配置もすべて工場内に収まる():
    layout = find_first_valid_layout(
        SMALL_FACTORY,
        [AREA_A, AREA_B, AREA_C],
        adjacency_pairs=[("A", "B")],
        minimum_separations=[("A", "C", 3.0)],
    )
    assert_all_inside(SMALL_FACTORY, layout)


def test_条件つきの配置もどの2エリアも重ならない():
    layout = find_first_valid_layout(
        SMALL_FACTORY,
        [AREA_A, AREA_B, AREA_C],
        adjacency_pairs=[("A", "B")],
        minimum_separations=[("A", "C", 3.0)],
    )
    assert_no_overlaps(layout)


def test_サンプルの6エリアに条件を付けても配置できる():
    layout = find_first_valid_layout(
        SAMPLE_FACTORY,
        SAMPLE_AREAS,
        adjacency_pairs=[("製造", "検査")],
        minimum_separations=[("入庫", "出庫", 3.0)],
    )
    assert len(layout) == 6
    assert_all_inside(SAMPLE_FACTORY, layout)
    assert_no_overlaps(layout)
    assert satisfies_adjacency_constraint(find_by_name(layout, "製造"), find_by_name(layout, "検査"))
    assert satisfies_minimum_separation_constraint(
        find_by_name(layout, "入庫"), find_by_name(layout, "出庫"), 3.0
    )


# ------------------------------------------------------------
# ここから Step 11：有効な配置案を複数作る find_valid_layouts
# ------------------------------------------------------------


def test_複数_2件以上の異なる配置案を作れる():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B], max_layouts=5)
    assert len(layouts) >= 2


def test_複数_配置案同士が重複していない():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B], max_layouts=10)
    # 各案を (名前, x, y) の並びに変えて、set に入れても数が減らなければ重複なし
    keys = [tuple((p.area.name, p.x, p.y) for p in layout) for layout in layouts]
    assert len(set(keys)) == len(keys)


def test_複数_max_layoutsが3なら3件を超えない():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B], max_layouts=3)
    assert len(layouts) <= 3


def test_複数_max_layoutsが1なら1件だけ():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B], max_layouts=1)
    assert len(layouts) == 1


def test_複数_max_layoutsが0ならValueError():
    with pytest.raises(ValueError):
        find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B], max_layouts=0)


def test_複数_すべての案で全エリアが工場内():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B, AREA_C], max_layouts=10)
    for layout in layouts:
        assert_all_inside(SMALL_FACTORY, layout)


def test_複数_すべての案でどの2エリアも重ならない():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B, AREA_C], max_layouts=10)
    for layout in layouts:
        assert_no_overlaps(layout)


def test_複数_隣接条件をすべての案が満たす():
    layouts = find_valid_layouts(
        SMALL_FACTORY, [AREA_A, AREA_C, AREA_B], adjacency_pairs=[("A", "B")], max_layouts=10
    )
    assert len(layouts) >= 2
    for layout in layouts:
        assert satisfies_adjacency_constraint(find_by_name(layout, "A"), find_by_name(layout, "B"))


def test_複数_最低離隔条件をすべての案が満たす():
    layouts = find_valid_layouts(
        SMALL_FACTORY, [AREA_A, AREA_B], minimum_separations=[("A", "B", 3.0)], max_layouts=10
    )
    assert len(layouts) >= 2
    for layout in layouts:
        assert satisfies_minimum_separation_constraint(
            find_by_name(layout, "A"), find_by_name(layout, "B"), 3.0
        )


def test_複数_条件を満たす配置が無ければValueError():
    # 幅3×高さ1 に 1×1 を3つ。「3つとも互いに隣接」は不可能
    factory = Factory(width=3, height=1)
    areas = [Area(name=n, width=1, height=1) for n in ["P", "Q", "R"]]
    with pytest.raises(ValueError):
        find_valid_layouts(
            factory, areas, adjacency_pairs=[("P", "Q"), ("Q", "R"), ("P", "R")]
        )


def test_複数_エリアが空なら空の配置が1案():
    assert find_valid_layouts(SMALL_FACTORY, []) == [[]]


def test_複数_find_first_valid_layoutはこれまでどおり動く():
    # 条件なし：左下から詰めた位置、空なら空のリスト
    layout = find_first_valid_layout(SMALL_FACTORY, [AREA_A, AREA_B])
    assert [(p.x, p.y) for p in layout] == [(0, 0), (4, 0)]
    assert find_first_valid_layout(SMALL_FACTORY, []) == []

    # 条件つき：find_valid_layouts の1件目と同じ
    first = find_first_valid_layout(
        SMALL_FACTORY, [AREA_A, AREA_C, AREA_B], adjacency_pairs=[("A", "B")]
    )
    many = find_valid_layouts(
        SMALL_FACTORY, [AREA_A, AREA_C, AREA_B], adjacency_pairs=[("A", "B")], max_layouts=5
    )
    assert first == many[0]


def test_複数_サンプルの6エリアで複数案を作れる():
    layouts = find_valid_layouts(
        SAMPLE_FACTORY,
        SAMPLE_AREAS,
        adjacency_pairs=[("製造", "検査")],
        minimum_separations=[("入庫", "出庫", 3.0)],
        max_layouts=5,
    )
    assert len(layouts) == 5
    keys = [tuple((p.area.name, p.x, p.y) for p in layout) for layout in layouts]
    assert len(set(keys)) == 5
    for layout in layouts:
        assert len(layout) == 6
        assert_all_inside(SAMPLE_FACTORY, layout)
        assert_no_overlaps(layout)


# ------------------------------------------------------------
# ここから Step 11 の続き：総動線距離で並べる rank_layouts_by_flow_distance
# ------------------------------------------------------------

# 1×1 のエリア P, Q, R を横一列に並べた配置案を作る（中心点は左下 ＋ 0.5）
ORDER_PQR = ["P", "Q", "R"]


def make_layout(positions):
    """[(x, y), (x, y), (x, y)] から P, Q, R の配置案を作る。"""
    names = ["P", "Q", "R"]
    return [
        PlacedArea(area=Area(name=name, width=1, height=1), x=x, y=y)
        for name, (x, y) in zip(names, positions)
    ]


LAYOUT_FAR = make_layout([(0, 0), (5, 0), (10, 0)])    # P→Q 5 ＋ Q→R 5 ＝ 10
LAYOUT_NEAR = make_layout([(0, 0), (1, 0), (2, 0)])    # 1 ＋ 1 ＝ 2
LAYOUT_MIDDLE = make_layout([(0, 0), (3, 0), (6, 0)])  # 3 ＋ 3 ＝ 6
LAYOUT_NEAR_VERTICAL = make_layout([(0, 0), (0, 1), (0, 2)])  # 縦に並べて 1 ＋ 1 ＝ 2


def test_順位_距離が短い順に並ぶ():
    ranked = rank_layouts_by_flow_distance([LAYOUT_FAR, LAYOUT_NEAR, LAYOUT_MIDDLE], ORDER_PQR)
    assert [layout for layout, _ in ranked] == [LAYOUT_NEAR, LAYOUT_MIDDLE, LAYOUT_FAR]
    assert [distance for _, distance in ranked] == [
        pytest.approx(2.0), pytest.approx(6.0), pytest.approx(10.0)
    ]


def test_順位_距離がcalculate_total_flow_distanceと一致する():
    ranked = rank_layouts_by_flow_distance([LAYOUT_FAR, LAYOUT_NEAR, LAYOUT_MIDDLE], ORDER_PQR)
    for layout, distance in ranked:
        assert distance == pytest.approx(calculate_total_flow_distance(layout, ORDER_PQR))


def test_順位_配置案が1つなら1件():
    ranked = rank_layouts_by_flow_distance([LAYOUT_MIDDLE], ORDER_PQR)
    assert len(ranked) == 1
    assert ranked[0][0] == LAYOUT_MIDDLE
    assert ranked[0][1] == pytest.approx(6.0)


def test_順位_配置案が空なら空のリスト():
    assert rank_layouts_by_flow_distance([], ORDER_PQR) == []


def test_順位_同じ距離なら元の順番のまま():
    # NEAR と NEAR_VERTICAL はどちらも距離2。渡した順のまま並ぶ
    ranked = rank_layouts_by_flow_distance([LAYOUT_NEAR_VERTICAL, LAYOUT_NEAR], ORDER_PQR)
    assert [layout for layout, _ in ranked] == [LAYOUT_NEAR_VERTICAL, LAYOUT_NEAR]

    ranked = rank_layouts_by_flow_distance([LAYOUT_NEAR, LAYOUT_NEAR_VERTICAL], ORDER_PQR)
    assert [layout for layout, _ in ranked] == [LAYOUT_NEAR, LAYOUT_NEAR_VERTICAL]


def test_順位_工程順序に存在しない名前があるとValueError():
    with pytest.raises(ValueError):
        rank_layouts_by_flow_distance([LAYOUT_NEAR], ["P", "存在しない"])


def test_順位_元のlayoutsの順番と座標を変えない():
    layouts = [LAYOUT_FAR, LAYOUT_NEAR, LAYOUT_MIDDLE]
    # 呼ぶ前の「並び」と「各案の名前・x・y」を控えておく
    before_order = list(layouts)
    before_positions = [[(p.area.name, p.x, p.y) for p in layout] for layout in layouts]

    rank_layouts_by_flow_distance(layouts, ORDER_PQR)

    assert layouts == before_order
    assert [[(p.area.name, p.x, p.y) for p in layout] for layout in layouts] == before_positions


def test_順位_find_valid_layoutsの結果をそのまま渡せる():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B, AREA_C], max_layouts=10)
    ranked = rank_layouts_by_flow_distance(layouts, ["A", "B", "C"])
    assert len(ranked) == len(layouts)
    distances = [distance for _, distance in ranked]
    assert distances == sorted(distances)


def test_順位_サンプルの工程順序で距離が短い順になる():
    layouts = find_valid_layouts(
        SAMPLE_FACTORY,
        SAMPLE_AREAS,
        adjacency_pairs=[("製造", "検査")],
        minimum_separations=[("入庫", "出庫", 3.0)],
        max_layouts=10,
    )
    ranked = rank_layouts_by_flow_distance(layouts, SAMPLE_PROCESS_ORDER)
    assert len(ranked) == 10
    distances = [distance for _, distance in ranked]
    assert distances == sorted(distances)
    for layout, distance in ranked:
        assert distance == pytest.approx(calculate_total_flow_distance(layout, SAMPLE_PROCESS_ORDER))


# ------------------------------------------------------------
# ここから：距離順に並んだ結果から上位3案を選ぶ select_top_layouts
# ------------------------------------------------------------

# 距離順に並んだ結果の見本（配置案の中身は今回関係ないので、簡単なものを使う）
RANKED_FIVE = [
    (LAYOUT_NEAR, 2.0),
    (LAYOUT_MIDDLE, 6.0),
    (LAYOUT_FAR, 10.0),
    (LAYOUT_NEAR_VERTICAL, 12.0),
    (LAYOUT_NEAR, 14.0),
]


def test_上位_5案から既定で3案返る():
    top = select_top_layouts(RANKED_FIVE)
    assert len(top) == 3
    assert [distance for _, distance in top] == [2.0, 6.0, 10.0]


def test_上位_top_nが2なら2案返る():
    top = select_top_layouts(RANKED_FIVE, top_n=2)
    assert [distance for _, distance in top] == [2.0, 6.0]


def test_上位_2件しかないのにtop_nが3なら2件だけ返る():
    top = select_top_layouts(RANKED_FIVE[:2], top_n=3)
    assert len(top) == 2


def test_上位_空なら空のリスト():
    assert select_top_layouts([]) == []


def test_上位_top_nが1なら1件返る():
    top = select_top_layouts(RANKED_FIVE, top_n=1)
    assert len(top) == 1
    assert top[0][1] == 2.0


def test_上位_top_nが0ならValueError():
    with pytest.raises(ValueError):
        select_top_layouts(RANKED_FIVE, top_n=0)


def test_上位_top_nが負ならValueError():
    with pytest.raises(ValueError):
        select_top_layouts(RANKED_FIVE, top_n=-1)


def test_上位_元のranked_layoutsを変えない():
    before = list(RANKED_FIVE)
    before_distances = [distance for _, distance in RANKED_FIVE]

    select_top_layouts(RANKED_FIVE, top_n=2)

    assert RANKED_FIVE == before
    assert [distance for _, distance in RANKED_FIVE] == before_distances


def test_上位_ランキング結果をそのまま渡せる():
    ranked = rank_layouts_by_flow_distance([LAYOUT_FAR, LAYOUT_NEAR, LAYOUT_MIDDLE], ORDER_PQR)
    top = select_top_layouts(ranked, top_n=2)
    assert [distance for _, distance in top] == [pytest.approx(2.0), pytest.approx(6.0)]


def test_上位_生成からランキングと上位選択までつながる():
    layouts = find_valid_layouts(SMALL_FACTORY, [AREA_A, AREA_B, AREA_C], max_layouts=10)
    ranked = rank_layouts_by_flow_distance(layouts, ["A", "B", "C"])
    top = select_top_layouts(ranked)

    assert len(top) == 3
    distances = [distance for _, distance in top]
    assert distances == sorted(distances)
    # 上位3案の距離は、全案の中で最も短い3つと同じ
    assert distances == sorted(distance for _, distance in ranked)[:3]


def test_上位_サンプルの6エリアで通しで上位3案を選べる():
    layouts = find_valid_layouts(
        SAMPLE_FACTORY,
        SAMPLE_AREAS,
        adjacency_pairs=[("製造", "検査")],
        minimum_separations=[("入庫", "出庫", 3.0)],
        max_layouts=10,
    )
    ranked = rank_layouts_by_flow_distance(layouts, SAMPLE_PROCESS_ORDER)
    top = select_top_layouts(ranked)

    assert len(top) == 3
    distances = [distance for _, distance in top]
    assert distances == sorted(distances)
    for layout, _ in top:
        assert len(layout) == 6
        assert_all_inside(SAMPLE_FACTORY, layout)
        assert_no_overlaps(layout)
