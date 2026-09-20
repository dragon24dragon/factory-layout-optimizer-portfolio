# 1つの配置案を、matplotlib で図にするファイル。
#
# ここでは計算はしない。受け取った配置を「描くだけ」を担当する。
# plt.show() は呼ばず、Figure（1枚の絵）を返す。
# そうしておくと、同じ図を Streamlit の st.pyplot(fig) で表示したり、
# save_layout_figure で画像として保存したりできる。

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from layout_optimizer.models import Factory, PlacedArea

# 日本語を表示できるフォントの候補（上から順に探す）。どれも Windows に入っていることが多い
JAPANESE_FONT_CANDIDATES = ["Yu Gothic", "Meiryo", "MS Gothic"]


def find_japanese_font() -> str | None:
    """使える日本語フォントの名前を返す。1つも無ければ None を返す。"""
    # matplotlib が見つけているフォントの名前をすべて集める
    available_names = {font.name for font in font_manager.fontManager.ttflist}

    for candidate in JAPANESE_FONT_CANDIDATES:
        if candidate in available_names:
            return candidate

    # 見つからなくてもエラーにはしない（日本語は □ になるが、図は作れる）
    return None


def create_layout_figure(
    factory: Factory,
    placed_areas: list[PlacedArea],
    title: str = "工場レイアウト",
) -> Figure:
    """工場と配置エリアを長方形で描いた Figure を返す。

    工場の左下を (0, 0) とし、x は 0〜工場の幅、y は 0〜工場の高さを表示する。
    """
    # 0. 日本語フォントを探す（見つからなければ None ＝ 標準のフォントで描く）
    font_name = find_japanese_font()

    # 1. 絵（Figure）と、その上に描くための座標軸（Axes）を1つ作る
    fig, ax = plt.subplots()

    # グラフの枠線（spines）を消す。工場の外枠と重なって見分けにくくなるため
    for spine in ax.spines.values():
        spine.set_visible(False)

    # 2. 工場の外枠を描く（塗りつぶさず、太めの黒い線だけ）
    #    gid は「この長方形が何か」を見分けるための名札。テストで数えるときに使う
    #    clip_on=False：表示範囲の端で線が半分切れないようにする
    #    zorder=3：エリアの長方形より手前に描く
    factory_frame = Rectangle(
        (0, 0),
        factory.width,
        factory.height,
        fill=False,
        edgecolor="black",
        linewidth=2,
        gid="factory",
        clip_on=False,
        zorder=3,
    )
    ax.add_patch(factory_frame)

    # 3. 各エリアを長方形で描き、真ん中に名前を書く
    for placed_area in placed_areas:
        area = placed_area.area
        area_rect = Rectangle(
            (placed_area.x, placed_area.y),  # 左下の位置
            area.width,
            area.height,
            facecolor="lightblue",
            edgecolor="steelblue",
            linewidth=1,
            gid="area",
        )
        ax.add_patch(area_rect)

        # 中心点は「左下 ＋ 幅や高さの半分」
        center_x = placed_area.x + area.width / 2
        center_y = placed_area.y + area.height / 2
        ax.text(
            center_x, center_y, area.name, ha="center", va="center", fontfamily=font_name
        )

    # 4. 表示範囲を工場の大きさに合わせる
    ax.set_xlim(0, factory.width)
    ax.set_ylim(0, factory.height)

    # 5. 縦と横を同じ縮尺にする（工場の形が歪んで見えないように）
    ax.set_aspect("equal")

    # 6. 軸のラベル・タイトル・格子（グリッド）
    ax.set_xlabel("x (m)")
    ax.set_ylabel("y (m)")
    ax.set_title(title, fontfamily=font_name)
    ax.grid(True, linestyle=":", linewidth=0.5)

    return fig


def create_ranked_layout_figures(
    factory: Factory,
    ranked_layouts: list[tuple[list[PlacedArea], float]],
) -> list[Figure]:
    """距離順に並んだ配置案を、順位つきの図（Figure）のリストにする。

    - ranked_layouts は (配置案, 総動線距離) の組が距離順に並んだもの
      （heuristic_search.py の rank_layouts_by_flow_distance → select_top_layouts の結果）
    - **並べ替え・距離の計算・件数の絞り込みはしない**。渡された数だけ図にする
    - 3件なら3図、2件なら2図、空なら []
    - 描く処理は create_layout_figure に任せる
    """
    figures: list[Figure] = []

    # enumerate(..., start=1) で「1から始まる番号」と中身を同時に取り出す
    for rank, (placed_areas, distance) in enumerate(ranked_layouts, start=1):
        # 距離は小数第1位まで表示する（例：42.0）
        title = f"第{rank}位 - 総動線距離 {distance:.1f} m"
        figures.append(create_layout_figure(factory, placed_areas, title=title))

    return figures


def save_layout_figure(fig: Figure, output_path) -> None:
    """Figure を画像ファイル（PNG など）として保存する。

    保存したあとに Figure を閉じる処理はしない。閉じたいときは呼び出し側で
    matplotlib.pyplot.close(fig) を呼ぶ。
    """
    fig.savefig(output_path)
