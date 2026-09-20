# データの形を決めるファイル。
# ここでは「工場」と「エリア」を表すクラスだけを定義する。

# dataclass（データクラス）を使うと、
# 値を入れておくためのクラスを短く書ける。
from dataclasses import dataclass


@dataclass
class Factory:
    """工場の大きさを表す。工場は長方形として扱う。"""

    width: int   # 工場の幅（m）
    height: int  # 工場の高さ（奥行き、m）


@dataclass
class Area:
    """工場の中に置くエリア（入庫・製造など）を表す。位置はまだ持たない。"""

    name: str    # エリア名（例："製造"）
    width: int   # エリアの幅（m）
    height: int  # エリアの高さ（奥行き、m）


@dataclass
class PlacedArea:
    """エリアを工場のどこに置いたかを表す。

    Area は「エリアそのものの大きさ」、
    PlacedArea は「そのエリアをどこに置いたか」。
    (x, y) は、工場の左下を (0, 0) としたときの、エリアの左下の角の位置。
    """

    area: Area  # 置いたエリア（名前と大きさ）
    x: int      # 工場の左下から右へ何m の位置か
    y: int      # 工場の左下から上へ何m の位置か
