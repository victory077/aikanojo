"""pytest設定 - srcディレクトリをパスに追加"""
import sys
from pathlib import Path

# src/ をsys.pathに追加（全テストファイルで共通利用）
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
