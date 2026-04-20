import streamlit as st
import pandas as pd
import plotly.express as px


def render(reject_df: pd.DataFrame):
    st.subheader("Reject 理由ランキング")

    reason_df = (
        reject_df["ERR_DS"]
        .fillna("(不明)")
        .value_counts()
        .reset_index()
        .rename(columns={"ERR_DS": "Reject 理由", "count": "件数"})
    )
    reason_df["順位"] = range(1, len(reason_df) + 1)
    reason_df = reason_df[["順位", "Reject 理由", "件数"]]

    col_c, col_d = st.columns(2)

    with col_c:
        fig4 = px.bar(
            reason_df.head(10),
            x="件数", y="Reject 理由", orientation="h",
            text="件数", title="Reject 理由 TOP10",
            color="件数", color_continuous_scale="Reds",
        )
        fig4.update_layout(
            yaxis={"categoryorder": "total ascending"}, showlegend=False
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col_d:
        fig5 = px.pie(
            reason_df.head(10),
            names="Reject 理由", values="件数",
            title="Reject 理由 構成比 (TOP10)", hole=0.4,
        )
        st.plotly_chart(fig5, use_container_width=True)

    # Entity 別内訳
    st.subheader("Entity 別 Reject 理由内訳")
    entity_reason = (
        reject_df.groupby(["ENTY_CD", "ERR_DS"])
        .size().reset_index(name="件数")
        .sort_values(["ENTY_CD", "件数"], ascending=[True, False])
    )
    entity_reason["ERR_DS"] = entity_reason["ERR_DS"].fillna("(不明)")

    fig6 = px.bar(
        entity_reason,
        x="ENTY_CD", y="件数", color="ERR_DS",
        title="Entity 別 Reject 理由内訳",
        labels={"ENTY_CD": "Entity", "件数": "Reject 件数", "ERR_DS": "理由"},
        barmode="stack",
    )
    fig6.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig6, use_container_width=True)

    st.subheader("Reject 理由一覧テーブル")
    st.dataframe(reason_df, use_container_width=True, hide_index=True)
