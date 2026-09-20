# plotting.py の関数が正しく動くかを、pytest で自動確認するファイル。
# 絵の見た目そのものは目で確認する。ここでは「中身の数や範囲」と「保存できるか」を確かめる。

import matplotlib

# 画面（ウィンドウ）を開かずに描く方式（Agg）を使う。テスト中に窓が開かないようにするため
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from layout_optimizer.heuristic_search import (
    find_valid_layouts,
    rank_layouts_by_flow_distance,
    select_top_layouts,
)
from layout_optimizer.models import Area, Factory, PlacedArea
from layout_optimizer.plotting import (
    create_layout_figure,
    create_ranked_layout_figures,
    save_layout_figure,
)
from layout_optimizer.sample_data import SAMPLE_AREAS, SAMPLE_FACTORY, SAMPLE_PROCESS_ORDER

# テスト用のデータ（日本語フォントの有無に左右されないよう、名前は英字）
FACTORY = Factory(width=20, height=15)
AREA_A = PlacedArea(area=Area(name="A", width=6, height=4), x=0, y=0)
AREA_B = PlacedArea(area=Area(name="B", width=5, height=5), x=10, y=8)


def count_area_rectangles(fig):
    """図の中にある「エリアの長方形」（gid が "area"）の数を返す。"""
    ax = fig.axes[0]
    return len([patch for patch in ax.patches if patch.get_gid() == "area"])


def test_Figureが返る():
    fig = create_layout_figure(FACTORY, [AREA_A, AREA_B], title="test")
    assert isinstance(fig, Figure)
    plt.close(fig)


def test_エリアが2個なら長方形も2個():
    fig = create_layout_figure(FACTORY, [AREA_A, AREA_B], title="test")
    assert count_area_rectangles(fig) == 2
    plt.close(fig)


def test_表示範囲が工場の幅と高さに合う():
    fig = create_layout_figure(FACTORY, [AREA_A, AREA_B], title="test")
    ax = fig.axes[0]
    assert ax.get_xlim() == (0, 20)
    assert ax.get_ylim() == (0, 15)
    plt.close(fig)


def test_エリアが空でも工場枠だけの図を作れる():
    fig = create_layout_figure(FACTORY, [], title="test")
    ax = fig.axes[0]
    assert isinstance(fig, Figure)
    assert count_area_rectangles(fig) == 0
    # 工場の外枠は1つだけ描かれている
    assert len([patch for patch in ax.patches if patch.get_gid() == "factory"]) == 1
    plt.close(fig)


def test_PNGとして保存できる(tmp_path):
    # tmp_path は pytest が用意する、テスト用の一時フォルダ
    fig = create_layout_figure(FACTORY, [AREA_A, AREA_B], title="test")
    output_path = tmp_path / "layout.png"

    save_layout_figure(fig, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    plt.close(fig)


# ------------------------------------------------------------
# ここから：上位の配置案をまとめて図にする create_ranked_layout_figures
# ------------------------------------------------------------

# 距離順に並んだ結果の見本（配置案の中身は同じでよいので、A と B を使う）
RANKED_THREE = [
    ([AREA_A, AREA_B], 42.0),
    ([AREA_A, AREA_B], 43.0),
    ([AREA_A, AREA_B], 44.0),
]


def test_順位図_3件渡すと3つ返る():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    assert len(figures) == 3
    for fig in figures:
        plt.close(fig)


def test_順位図_2件なら2つ返る():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE[:2])
    assert len(figures) == 2
    for fig in figures:
        plt.close(fig)


def test_順位図_1件なら1つ返る():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE[:1])
    assert len(figures) == 1
    plt.close(figures[0])


def test_順位図_空なら空のリスト():
    assert create_ranked_layout_figures(FACTORY, []) == []


def test_順位図_すべてFigureである():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    for fig in figures:
        assert isinstance(fig, Figure)
        plt.close(fig)


def test_順位図_タイトルに順位が入る():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    titles = [fig.axes[0].get_title() for fig in figures]
    assert titles[0].startswith("第1位")
    assert titles[1].startswith("第2位")
    assert titles[2].startswith("第3位")
    for fig in figures:
        plt.close(fig)


def test_順位図_タイトルに総動線距離が入る():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    titles = [fig.axes[0].get_title() for fig in figures]
    assert "42.0" in titles[0]
    assert "43.0" in titles[1]
    assert "44.0" in titles[2]
    for fig in figures:
        plt.close(fig)


def test_順位図_エリアの数だけ長方形が描かれる():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    for fig in figures:
        # 見本の配置案はどれもエリア2つ
        assert count_area_rectangles(fig) == 2
        plt.close(fig)


def test_順位図_表示範囲が工場の幅と高さに合う():
    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)
    for fig in figures:
        ax = fig.axes[0]
        assert ax.get_xlim() == (0, 20)
        assert ax.get_ylim() == (0, 15)
        plt.close(fig)


def test_順位図_元のranked_layoutsを変えない():
    before = list(RANKED_THREE)
    before_positions = [
        [(p.area.name, p.x, p.y) for p in layout] for layout, _ in RANKED_THREE
    ]
    before_distances = [distance for _, distance in RANKED_THREE]

    figures = create_ranked_layout_figures(FACTORY, RANKED_THREE)

    assert RANKED_THREE == before
    assert [
        [(p.area.name, p.x, p.y) for p in layout] for layout, _ in RANKED_THREE
    ] == before_positions
    assert [distance for _, distance in RANKED_THREE] == before_distances
    for fig in figures:
        plt.close(fig)


def test_順位図_サンプルの上位3案を図にできる():
    # 探索 → ランキング → 上位3案 の結果を、そのまま図にできるか
    layouts = find_valid_layouts(
        SAMPLE_FACTORY,
        SAMPLE_AREAS,
        adjacency_pairs=[("製造", "検査")],
        minimum_separations=[("入庫", "出庫", 3.0)],
        max_layouts=10,
    )
    top = select_top_layouts(rank_layouts_by_flow_distance(layouts, SAMPLE_PROCESS_ORDER))

    figures = create_ranked_layout_figures(SAMPLE_FACTORY, top)
    assert len(figures) == 3
    for fig in figures:
        assert isinstance(fig, Figure)
        # サンプルはエリア6つ
        assert count_area_rectangles(fig) == 6
        plt.close(fig)
