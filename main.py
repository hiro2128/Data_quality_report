import streamlit as st
import pandas as pd
from data_manager import (
    SALES_PKL, ENTITY_PKL, BASE_SALES_CSV, BASE_ENTITY_CSV,
    load_meta, read_sales_csv, merge_and_save,
    load_parquet, load_entity, init_from_base_csv,
)
import tab_trend
import tab_ranking
import tab_advice

st.set_page_config(
    page_title="Data Quality Report",
    page_icon="📊",
    layout="wide",
)

# ─────────────────────────────────────────
# サイドバー：ファイルアップロード
# ─────────────────────────────────────────
st.sidebar.title("📂 データ管理")

# ── 初回セットアップ（Parquet未作成時のみ表示）──
if not SALES_PKL.exists():
    st.sidebar.markdown("### 🚀 初回セットアップ")
    if BASE_SALES_CSV.exists():
        st.sidebar.info(
            f"ベースCSVが見つかりました。\n\n"
            f"`{BASE_SALES_CSV.name}`\n\n"
            "ボタンを押すと Parquet に変換します（初回のみ時間がかかります）。"
        )
        if st.sidebar.button("⚙️ ベースCSVから初期化する", type="primary"):
            with st.spinner("ベース CSV を変換中... しばらくお待ちください"):
                n = init_from_base_csv()
            st.sidebar.success(f"✅ {n:,} 件を変換しました")
            st.cache_data.clear()
            st.rerun()
    else:
        st.sidebar.warning(
            f"ベースCSVが見つかりません。\n\n`{BASE_SALES_CSV}`\n\n"
            "パスを確認するか、下の増分アップロードから CSV を直接アップロードしてください。"
        )

st.sidebar.divider()

# ── 増分アップロード ──────────────────────────
with st.sidebar.expander(
    "📤 増分データのアップロード",
    expanded=not SALES_PKL.exists() and not BASE_SALES_CSV.exists()
):
    st.caption("前回以降の差分 CSV をアップロードしてください。既存データに自動マージします。")
    sales_file = st.file_uploader("LND_Sales 増分 CSV", type="csv", key="sales_upload")
    if sales_file:
        with st.spinner(f"読み込み中: {sales_file.name}"):
            new_df = read_sales_csv(sales_file)
            merge_and_save(new_df, sales_file.name)
            st.cache_data.clear()
        st.success(f"✅ {len(new_df):,} 件を追加しました")
        st.rerun()

    st.caption("Entity DIM CSV（マスタ更新時のみ）")
    entity_file = st.file_uploader("Entity DIM CSV", type="csv", key="entity_upload")
    if entity_file:
        load_entity(entity_file)
        st.success("✅ Entity マスタを更新しました")
        st.rerun()

# データ未ロード時はここで停止
if not SALES_PKL.exists():
    st.title("📊 Data Quality Report")
    st.info("👈 サイドバーの「初回セットアップ」または「増分アップロード」からデータを読み込んでください。")
    st.stop()

# ─────────────────────────────────────────
# データロード（Parquet キャッシュ）
# ─────────────────────────────────────────
mtime     = SALES_PKL.stat().st_mtime
sales_df  = load_parquet(mtime)
entity_df = load_entity()
df        = sales_df.merge(entity_df, on="ENTY_DIM_ID", how="left")
meta      = load_meta()

# ─────────────────────────────────────────
# サイドバー：データ範囲 & アップロード履歴
# ─────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 📅 データ範囲")
if meta["rec_min"] and meta["rec_max"]:
    rec_min = pd.to_datetime(meta["rec_min"]).strftime("%Y-%m-%d")
    rec_max = pd.to_datetime(meta["rec_max"]).strftime("%Y-%m-%d")
    st.sidebar.success(f"**{rec_min}**  〜  **{rec_max}**")
st.sidebar.metric("累計レコード数", f"{meta['total_rows']:,}")

if meta["uploads"]:
    st.sidebar.markdown("### 📋 アップロード履歴（直近5件）")
    for u in reversed(meta["uploads"][-5:]):
        st.sidebar.caption(
            f"🗂 {u['filename']}\n"
            f"{u['uploaded_at']}  ({u['rows_added']:,} 件)"
        )

# ─────────────────────────────────────────
# サイドバー：フィルター
# ─────────────────────────────────────────
st.sidebar.divider()
st.sidebar.markdown("### 🔍 フィルター")

months_all   = sorted(df["YM"].unique())
sel_months   = st.sidebar.multiselect("月を選択", months_all, default=months_all)

entities_all = sorted(df["ENTY_CD"].dropna().unique())
sel_entities = st.sidebar.multiselect("Entity を選択", entities_all, default=entities_all)

mask      = df["YM"].isin(sel_months) & df["ENTY_CD"].isin(sel_entities)
fdf       = df[mask]
reject_df = fdf[fdf["ERR_FLG"] == "Y"]

# ─────────────────────────────────────────
# ヘッダー & KPI
# ─────────────────────────────────────────
st.title("📊 Monthly Data Quality Report")

if meta["rec_min"] and meta["rec_max"]:
    last_upload = meta["uploads"][-1]["uploaded_at"] if meta["uploads"] else "-"
    st.caption(
        f"データ範囲: **{rec_min}** 〜 **{rec_max}**　｜　"
        f"最終更新: {last_upload}"
    )

total   = len(fdf)
rejects = len(reject_df)
rate    = rejects / total * 100 if total > 0 else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("総レコード数", f"{total:,}")
c2.metric("Reject 件数",  f"{rejects:,}")
c3.metric("Reject 率",    f"{rate:.2f}%")
c4.metric("対象期間",     f"{len(sel_months)} ヶ月")

st.divider()

# ─────────────────────────────────────────
# タブ
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📈 月次 Reject トレンド",
    "🏆 Reject 理由ランキング",
    "💡 アドバイス & Feedback",
])

with tab1:
    tab_trend.render(fdf, reject_df)

with tab2:
    tab_ranking.render(reject_df)

with tab3:
    tab_advice.render(reject_df)
