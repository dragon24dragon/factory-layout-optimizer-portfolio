# 工場レイアウト設計最適化 PoC の画面
# 起動方法: streamlit run app.py
#
# この画面は計算をしない。layout_optimizer の関数を順番に呼んで、結果を表示するだけ。

# 工場の対角線の長さ（三平方の定理）を math.hypot で求めるために使う
import math

# Streamlit（Pythonだけで Web 画面を作れるライブラリ）を「st」という短い名前で読み込む
import streamlit as st

from layout_optimizer.heuristic_search import (
    find_valid_layouts,
    rank_layouts_by_flow_distance,
    select_top_layouts,
)
from layout_optimizer.models import Area, Factory
from layout_optimizer.plotting import create_ranked_layout_figures
from layout_optimizer.sample_data import (
    SAMPLE_AREAS,
    SAMPLE_FACTORY,
    SAMPLE_PROCESS_ORDER,
)

# 配置条件の初期値（画面の入力欄に最初から入れておく値）。
# 条件は画面から変えられるので、探索にはここではなく画面の入力値を渡す。
SAMPLE_ADJACENCY_PAIRS = [("製造", "検査")]
SAMPLE_MINIMUM_SEPARATIONS = [("入庫", "出庫", 3.0)]
MAX_LAYOUTS = 10  # 何案まで集めてから上位3案を選ぶか

# ブラウザのタブに表示される名前を設定する（画面の命令より先に書く決まり）
st.set_page_config(page_title="工場レイアウト設計最適化 PoC")

# 画面の一番上に大きな見出しを表示する
st.title("工場レイアウト設計最適化 PoC")

# 見出しの下に説明文を表示する
st.write("条件を満たす配置案を探索し、総動線距離が短い上位3案を表示します。")

# 工場の大きさは画面から入力する（初期値はサンプルと同じ 20m × 15m）
st.subheader("工場の大きさ")
factory_width = st.number_input(
    "工場の幅（m）", min_value=1, value=SAMPLE_FACTORY.width, step=1
)
factory_height = st.number_input(
    "工場の高さ（奥行き、m）", min_value=1, value=SAMPLE_FACTORY.height, step=1
)

# 入力された値から、探索に渡す工場を作る
factory = Factory(width=int(factory_width), height=int(factory_height))

st.write(f"現在の工場サイズ：幅 {factory.width} m × 高さ {factory.height} m")

# エリアは画面から入力する（初期値はサンプルと同じ6エリア）
# 第一版ではエリアの数は6個で固定する。増減は次のステップ以降で扱う。
st.subheader("エリアの情報")
st.write("エリアの数は6個で固定です。名前・幅・高さを変えられます。")

# 入力された値から作った Area を、ここに順番に入れていく
areas = []

# enumerate(..., start=1) で「1から始まる番号」とサンプルのエリアを同時に取り出す
for number, sample_area in enumerate(SAMPLE_AREAS, start=1):
    st.markdown(f"**エリア{number}**")

    # 3つの入力欄を横に並べる（columns は画面を左右に分ける機能）
    name_column, width_column, height_column = st.columns(3)

    # key= は入力欄を見分けるための名札。同じ名前の欄が6組あるので必ず付ける
    name = name_column.text_input(
        "名前", value=sample_area.name, key=f"area_name_{number}"
    )
    width = width_column.number_input(
        "幅（m）", min_value=1, value=sample_area.width, step=1, key=f"area_width_{number}"
    )
    height = height_column.number_input(
        "高さ（m）",
        min_value=1,
        value=sample_area.height,
        step=1,
        key=f"area_height_{number}",
    )

    # 名前の前後の余分な空白は取り除いてから使う
    areas.append(Area(name=name.strip(), width=int(width), height=int(height)))

# 工程順序は画面から入力する（モノが流れる順番を、エリア名で並べる）
# 第一版では工程の数は6個で固定し、6つのエリアをそれぞれ1回ずつ使う決まりにする。
st.subheader("工程順序")
st.write("6つの工程に、上で入力したエリアを1つずつ割り当てます（同じエリアは1回だけ）。")

# 選択肢は、いま画面に入力されている6つのエリア名
area_names = [area.name for area in areas]

# 選んだエリア名を、工程1から順番にここへ入れていく
process_order = []

for number, sample_name in enumerate(SAMPLE_PROCESS_ORDER, start=1):
    # 初期値はサンプルの工程順序と同じにする。
    # エリア名が変更されて候補に無くなっていたら、先頭の候補を初期値にする。
    if sample_name in area_names:
        default_index = area_names.index(sample_name)
    else:
        default_index = 0

    # selectbox は「決まった候補から1つ選ぶ」入力欄。
    # 候補を画面のエリア名に限ることで、打ち間違いによるエラーを防げる。
    selected_name = st.selectbox(
        f"工程{number}",
        options=area_names,
        index=default_index,
    )
    process_order.append(selected_name)

st.write(f"現在の工程順序：{' → '.join(process_order)}")

# 隣接条件は画面から入力する（第一版では1組だけ）
st.subheader("隣接条件")
st.write("選んだ2エリアを、辺で接する（となり合う）ように配置します。")


def find_default_index(names, wanted_name):
    """候補の中の wanted_name の位置を返す。無ければ 0（先頭）を返す。

    エリア名が変更されて候補から消えても、画面が落ちないようにするための関数。
    """
    if wanted_name in names:
        return names.index(wanted_name)
    return 0


# 初期値は、これまで固定で使っていた隣接条件と同じ組（製造 と 検査）
default_adjacency = SAMPLE_ADJACENCY_PAIRS[0]

adjacency_column_a, adjacency_column_b = st.columns(2)

adjacency_name_a = adjacency_column_a.selectbox(
    "エリアA",
    options=area_names,
    index=find_default_index(area_names, default_adjacency[0]),
)
adjacency_name_b = adjacency_column_b.selectbox(
    "エリアB",
    options=area_names,
    index=find_default_index(area_names, default_adjacency[1]),
)

# 探索に渡す形（エリア名2つの組のリスト）にする。第一版では1組だけ
adjacency_pairs = [(adjacency_name_a, adjacency_name_b)]

st.write(f"現在の隣接条件：{adjacency_name_a} と {adjacency_name_b} を隣接させる")

# 最低離隔条件も画面から入力する（第一版では1組だけ）
st.subheader("最低離隔条件")
st.write("選んだ2エリアを、指定した距離以上離して配置します。")

# 初期値は、これまで固定で使っていた最低離隔条件と同じ（入庫 と 出庫 を 3.0m 以上）
default_separation = SAMPLE_MINIMUM_SEPARATIONS[0]

separation_column_a, separation_column_b, separation_column_distance = st.columns(3)

separation_name_a = separation_column_a.selectbox(
    "エリアA",
    options=area_names,
    index=find_default_index(area_names, default_separation[0]),
    key="separation_area_a",
)
separation_name_b = separation_column_b.selectbox(
    "エリアB",
    options=area_names,
    index=find_default_index(area_names, default_separation[1]),
    key="separation_area_b",
)
# 0m も有効な指定（constraints.py は「すき間 >= 指定距離」で判定するため、
# 0m は「接していてもよい」という意味になる）
separation_distance = separation_column_distance.number_input(
    "最低離隔距離（m）",
    min_value=0.0,
    value=float(default_separation[2]),
    step=0.5,
)

# 探索に渡す形（エリア名2つと距離の組のリスト）にする。第一版では1組だけ
minimum_separations = [
    (separation_name_a, separation_name_b, float(separation_distance))
]

st.write(
    f"現在の最低離隔条件：{separation_name_a} と {separation_name_b} を "
    f"{float(separation_distance):.1f} m 以上離す"
)


def find_input_error(
    input_factory,
    input_areas,
    input_process_order,
    input_adjacency_pairs,
    input_minimum_separations,
):
    """入力された工場・エリア・工程順序・隣接条件・最低離隔条件に問題があれば、
    日本語のメッセージを返す。

    問題が無ければ None を返す。探索を始める前の簡単な確認だけを行う。
    """
    names = [area.name for area in input_areas]

    # 1. 名前が空（または空白だけ）のものがあるか
    if any(name == "" for name in names):
        return "エリア名を入力してください。"

    # 2. 同じ名前が2つ以上あるか（set は重複を取り除いた集まり）
    if len(set(names)) != len(names):
        return "エリア名が重複しています。"

    # 3. 幅や高さが0以下になっていないか（number_input の min_value でも防いでいるが念のため）
    if any(area.width <= 0 or area.height <= 0 for area in input_areas):
        return "幅と高さは1以上の値を入力してください。"

    # 4. 工程順序で同じエリアを2回以上選んでいないか
    if len(set(input_process_order)) != len(input_process_order):
        return (
            "工程順序に同じエリアが複数回選ばれています。"
            "6つのエリアをそれぞれ1回ずつ選んでください。"
        )

    # 5. 工程順序に出てこないエリアが残っていないか
    #    （4で重複が無いことを確かめているので、ここは「使われていないエリア」の確認になる）
    unused_names = [name for name in names if name not in input_process_order]
    if unused_names:
        return (
            "工程順序に含まれていないエリアがあります："
            f"{'、'.join(unused_names)}。"
            "6つのエリアをそれぞれ1回ずつ選んでください。"
        )

    # 6. 隣接条件で同じエリアを2つ選んでいないか（同じエリア同士は隣接できない）
    if any(name_a == name_b for name_a, name_b in input_adjacency_pairs):
        return "隣接条件には異なる2つのエリアを選んでください。"

    # 7. 最低離隔条件で同じエリアを2つ選んでいないか（同じエリア同士は離せない）
    if any(name_a == name_b for name_a, name_b, _distance in input_minimum_separations):
        return "最低離隔条件には異なる2つのエリアを選んでください。"

    # 8. 最低離隔距離がマイナスになっていないか（number_input でも防いでいるが念のため）
    if any(distance < 0 for _name_a, _name_b, distance in input_minimum_separations):
        return "最低離隔距離は0m以上の値を入力してください。"

    # 9. 最低離隔距離が、そもそも工場に収まらない大きさになっていないか
    #    工場の中にある2つのエリアは、どんなに離しても「工場の対角線」より遠くはなれない。
    #    対角線は、その工場の中で取れるいちばん長い直線だから。
    #    math.hypot(幅, 高さ) は三平方の定理（√(幅² + 高さ²)）の計算。
    #    ここで先に気づけば、探すだけ無駄な条件で探索を始めずに済む
    #    （総当たりの探索は、不可能な条件だと終わるまでにとても長い時間がかかる）。
    factory_diagonal = math.hypot(input_factory.width, input_factory.height)

    if any(
        distance > factory_diagonal
        for _name_a, _name_b, distance in input_minimum_separations
    ):
        return (
            "最低離隔距離が工場サイズに対して大きすぎます。"
            "工場サイズまたは最低離隔距離を見直してください。"
            f"（この工場（幅 {input_factory.width} m × 高さ {input_factory.height} m）では、"
            f"どれだけ離しても約 {factory_diagonal:.1f} m までです）"
        )

    return None


# ボタンが押されたときだけ、中の処理が動く
if st.button("この条件で探索する"):
    # 先に入力を確認する。問題があれば探索しない
    input_error = find_input_error(
        factory, areas, process_order, adjacency_pairs, minimum_separations
    )

    if input_error is not None:
        st.error(input_error)

    else:
        try:
            # 1. 条件を満たす配置案を集める
            layouts = find_valid_layouts(
                factory,
                areas,
                adjacency_pairs=adjacency_pairs,
                minimum_separations=minimum_separations,
                max_layouts=MAX_LAYOUTS,
            )

            # 2. 総動線距離を計算して、短い順に並べる
            ranked_layouts = rank_layouts_by_flow_distance(layouts, process_order)

            # 3. 上位3案を選ぶ
            top_layouts = select_top_layouts(ranked_layouts)

            # 4. 選んだ案を図（Figure）にする
            figures = create_ranked_layout_figures(factory, top_layouts)

        except ValueError as error:
            # 置ける場所が無いときや、工程順序にある名前のエリアが無いときなど。
            # アプリを落とさず、画面にメッセージを出す。
            st.error(
                "この条件では配置案を作れませんでした。"
                "工場やエリアの大きさ、隣接条件、最低離隔距離を見直してください。"
                "（条件が厳しすぎると、置ける場所が1つも無くなることがあります）"
                f"（詳しい理由：{error}）"
            )

        else:
            st.success(
                f"{len(layouts)}案の中から、"
                f"総動線距離が短い上位{len(top_layouts)}案を表示します。"
            )

            # 5. 順位・距離・図を順番に表示する
            #    enumerate(..., start=1) で「1から始まる番号」と中身を同時に取り出す
            for rank, ((_placed_areas, distance), figure) in enumerate(
                zip(top_layouts, figures), start=1
            ):
                st.subheader(f"第{rank}位")
                st.write(f"総動線距離：{distance:.1f} m")
                st.pyplot(figure)
