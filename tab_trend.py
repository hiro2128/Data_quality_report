import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render(fdf: pd.DataFrame, reject_df: pd.DataFrame):
    st.subheader("月別 Reject 件数")

    monthly = (
        fdf.groupby("YM")
        .agg(
            total=("LND_SLS_ID", "count"),
            reject=("ERR_FLG", lambda x: (x == "Y").sum()),
        )
        .reset_index()
    )
    monthly["reject_rate"] = (
        monthly["reject"] / monthly["total"] * 100
    ).round(2)

    col_a, col_b = st.columns(2)

    with col_a:
        fig1 = px.bar(
            monthly, x="YM", y="reject", text="reject",
            labels={"YM": "月", "reject": "Reject 件数"},
            title="月別 Reject 件数",
            color_discrete_sequence=["#EF553B"],
        )
        fig1.update_traces(textposition="outside")
        fig1.update_layout(xaxis_title="月", yaxis_title="件数", showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        fig2 = go.Figure()
        fig2.add_bar(
            x=monthly["YM"], y=monthly["total"],
            name="総件数", marker_color="#636EFA"
        )
        fig2.add_bar(
            x=monthly["YM"], y=monthly["reject"],
            name="Reject 件数", marker_color="#EF553B"
        )
        fig2.update_layout(
            barmode="overlay",
            title="総件数 vs Reject 件数",
            xaxis_title="月", yaxis_title="件数",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # ヒートマップ
    st.subheader("Entity 別 × 月別 Reject ヒートマップ")
    pivot = (
        reject_df.groupby(["ENTY_CD", "YM"])
        .size().reset_index(name="reject")
        .pivot(index="ENTY_CD", columns="YM", values="reject")
        .fillna(0).astype(int)
    )
    if not pivot.empty:
        fig3 = px.imshow(
            pivot,
            labels={"x": "月", "y": "Entity", "color": "Reject 件数"},
            title="Entity × 月 Reject ヒートマップ",
            color_continuous_scale="Reds",
            aspect="auto",
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("該当データがありません。")

    # サマリーテーブル
    st.subheader("月別サマリーテーブル")
    st.dataframe(
        monthly.rename(columns={
            "YM": "月", "total": "総件数",
            "reject": "Reject 件数", "reject_rate": "Reject 率(%)"
        }),
        use_container_width=True, hide_index=True,
    )
