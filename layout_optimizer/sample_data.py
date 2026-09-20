# 動作確認に使うサンプルデータ。
# 画面から入力しなくても、ここにある値で試せるようにしておく。

from layout_optimizer.models import Area, Factory

# 工場：幅20m × 高さ15m
SAMPLE_FACTORY = Factory(width=20, height=15)

# 工場に置くエリアの一覧（位置はまだ決めない）
SAMPLE_AREAS = [
    Area(name="入庫", width=4, height=3),
    Area(name="材料置場", width=5, height=3),
    Area(name="製造", width=6, height=4),
    Area(name="検査", width=4, height=3),
    Area(name="梱包", width=4, height=3),
    Area(name="出庫", width=4, height=3),
]

# 工程順序：モノが流れる順番を、エリア名で並べる
SAMPLE_PROCESS_ORDER = ["入庫", "材料置場", "製造", "検査", "梱包", "出庫"]
