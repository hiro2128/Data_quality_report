import pandas as pd
import streamlit as st
import json
from pathlib import Path
from datetime import datetime

DATA_DIR   = Path(__file__).parent / "data"
SALES_PKL  = DATA_DIR / "lnd_sales.parquet"
ENTITY_PKL = DATA_DIR / "entity_dim.parquet"
META_FILE  = DATA_DIR / "metadata.json"

# ベースファイルパス（共有フォルダ上の初回読み込み元）
BASE_SALES_CSV  = Path(r"C:\Users\N206876\Documents\Kiro_developed\Data_quality_report\LND_sales.csv")
BASE_ENTITY_CSV = Path(r"C:\Users\N206876\Documents\Kiro_developed\Data_quality_report\Entity_DIM.csv")

SALES_COLS = [
    "LND_SLS_ID", "ENTY_DIM_ID", "REC_ADD_TS", "ERR_FLG",
    "FLD_LVL_ERR_IND", "LGC_ERR_IND", "LGC_WRNG_IND", "ERR_DS"
]

DATA_DIR.mkdir(exist_ok=True)


# ── メタデータ ──────────────────────────────
def load_meta() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    return {"uploads": [], "rec_min": None, "rec_max": None, "total_rows": 0}


def save_meta(meta: dict):
    META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── CSV 読み込み（pyarrow で高速化）────────────
def read_sales_csv(file) -> pd.DataFrame:
    df = pd.read_csv(
        file,
        usecols=SALES_COLS,
        dtype={
            "LND_SLS_ID":      "int64",
            "ENTY_DIM_ID":     "int32",
            "ERR_FLG":         "category",
            "FLD_LVL_ERR_IND": "category",
            "LGC_ERR_IND":     "category",
            "LGC_WRNG_IND":    "category",
            "ERR_DS":          "string",
        },
        parse_dates=["REC_ADD_TS"],
        engine="pyarrow",
    )
    return df


# ── 増分マージ & Parquet 保存 ────────────────
def merge_and_save(new_df: pd.DataFrame, filename: str) -> pd.DataFrame:
    if SALES_PKL.exists():
        existing = pd.read_parquet(SALES_PKL, engine="pyarrow")
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["LND_SLS_ID"], keep="last")
    else:
        combined = new_df

    combined.to_parquet(SALES_PKL, engine="pyarrow", index=False)

    meta = load_meta()
    meta["uploads"].append({
        "filename":    filename,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_added":  len(new_df),
    })
    meta["rec_min"]    = str(combined["REC_ADD_TS"].min())
    meta["rec_max"]    = str(combined["REC_ADD_TS"].max())
    meta["total_rows"] = int(len(combined))
    save_meta(meta)
    return combined


# ── Parquet ロード（mtime キャッシュ）──────────
@st.cache_data(show_spinner="データを読み込み中...")
def load_parquet(mtime: float) -> pd.DataFrame:
    df = pd.read_parquet(SALES_PKL, engine="pyarrow")
    df["YM"] = df["REC_ADD_TS"].dt.to_period("M").astype(str)
    return df


# ── ベースCSV → Parquet 初回変換 ────────────
def init_from_base_csv(progress_callback=None) -> int:
    """
    共有フォルダの BASE_SALES_CSV を読み込み Parquet に変換して保存する。
    既に Parquet が存在する場合は何もしない。
    戻り値: 変換した行数（スキップ時は -1）
    """
    if SALES_PKL.exists():
        return -1

    if not BASE_SALES_CSV.exists():
        raise FileNotFoundError(f"ベースCSVが見つかりません: {BASE_SALES_CSV}")

    if progress_callback:
        progress_callback("ベース CSV を読み込み中（初回のみ）...")

    df = read_sales_csv(BASE_SALES_CSV)
    df.to_parquet(SALES_PKL, engine="pyarrow", index=False)

    meta = load_meta()
    meta["uploads"].append({
        "filename":    BASE_SALES_CSV.name,
        "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows_added":  len(df),
        "source":      "base_csv",
    })
    meta["rec_min"]    = str(df["REC_ADD_TS"].min())
    meta["rec_max"]    = str(df["REC_ADD_TS"].max())
    meta["total_rows"] = int(len(df))
    save_meta(meta)

    # Entity マスタも同時に変換
    if BASE_ENTITY_CSV.exists() and not ENTITY_PKL.exists():
        load_entity(BASE_ENTITY_CSV)

    return len(df)


# ── Entity マスタ ────────────────────────────
def load_entity(file=None) -> pd.DataFrame:
    if file is not None:
        df = pd.read_csv(
            file,
            usecols=["ENTY_DIM_ID", "ENTY_CD", "ENTY_NM", "CNTRY_NM"]
        )
        df["ENTY_DIM_ID"] = df["ENTY_DIM_ID"].astype("int32")
        df.to_parquet(ENTITY_PKL, engine="pyarrow", index=False)
        return df
    if ENTITY_PKL.exists():
        return pd.read_parquet(ENTITY_PKL, engine="pyarrow")
    return pd.DataFrame(columns=["ENTY_DIM_ID", "ENTY_CD", "ENTY_NM", "CNTRY_NM"])
