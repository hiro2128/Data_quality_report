import streamlit as st
import pandas as pd

ADVICE = {
    "SOLD_DT is greater than Current_Date": {
        "原因": "販売日が未来日付（9999-12-30 等）になっている。",
        "アドバイス": "販売日の入力時に現在日付以前であることをバリデーションしてください。",
        "NSC Feedback": (
            "Sold Date に未来日付が設定されているレコードが検出されています。"
            "データ入力システム側で日付バリデーションを追加し、"
            "9999-12-30 等のダミー日付を使用しないよう運用ルールを見直してください。"
        ),
    },
    "Multiple records found for same Dealer Id, Deal Number, VIN": {
        "原因": "同一の Dealer ID・Deal Number・VIN の組み合わせで重複レコードが存在する。",
        "アドバイス": "送信前に重複チェックを実施し、同一キーのレコードを排除してください。",
        "NSC Feedback": (
            "同一 Dealer ID / Deal Number / VIN の重複レコードが送信されています。"
            "送信システムに重複排除ロジックを実装するか、"
            "再送時に既存レコードを上書きする仕組みを検討してください。"
        ),
    },
    "Null Values found for fields-Contract Type": {
        "原因": "Contract Type が未入力。",
        "アドバイス": "Contract Type は必須項目です。送信前に必須チェックを追加してください。",
        "NSC Feedback": (
            "Contract Type が NULL のレコードが送信されています。"
            "必須項目として入力チェックを強化し、空値での送信を防いでください。"
        ),
    },
    "Null Values found for fields-Dealer ID, VIN, Dealer Number, Customer Owner ID, Contract TypeSold Date": {
        "原因": "複数の必須フィールドが未入力。",
        "アドバイス": (
            "Dealer ID・VIN・Dealer Number・Customer Owner ID・Contract Type・Sold Date は"
            "すべて必須項目です。一括バリデーションを実施してください。"
        ),
        "NSC Feedback": (
            "複数の必須フィールドが NULL のレコードが検出されています。"
            "送信前バリデーションを強化し、必須項目がすべて入力されていることを"
            "確認してから送信してください。"
        ),
    },
    "Null Values found for fields-Dealer Number,": {
        "原因": "Dealer Number が未入力。",
        "アドバイス": "Dealer Number は必須項目です。マスタデータと照合して正しい値を設定してください。",
        "NSC Feedback": (
            "Dealer Number が NULL のレコードが送信されています。"
            "ディーラーマスタを参照し、正しい Dealer Number を設定してから再送してください。"
        ),
    },
    "Sold date is not valid": {
        "原因": "販売日のフォーマットまたは値が不正。",
        "アドバイス": "日付フォーマット（YYYY-MM-DD）と有効な日付範囲を確認してください。",
        "NSC Feedback": (
            "不正な Sold Date が送信されています。"
            "日付フォーマット（YYYY-MM-DD）および有効範囲（過去日付）を確認し、"
            "正しい値で再送してください。"
        ),
    },
    "The Dealer available in Sales but not in Dealer Profile": {
        "原因": "Sales データに存在する Dealer が Dealer Profile マスタに登録されていない。",
        "アドバイス": "Dealer Profile マスタへの登録を先に完了させてから Sales データを送信してください。",
        "NSC Feedback": (
            "Dealer Profile に未登録のディーラーが Sales データに含まれています。"
            "先に Dealer Profile を登録・更新してから Sales データを再送してください。"
        ),
    },
    "Used sold date is less than new sold date for the same VIN": {
        "原因": "同一 VIN に対して、中古車の販売日が新車の販売日より前になっている。",
        "アドバイス": "同一 VIN の新車・中古車の販売日の前後関係を確認してください。",
        "NSC Feedback": (
            "同一 VIN で中古車販売日 < 新車販売日となるレコードが検出されています。"
            "販売履歴データの整合性を確認し、正しい日付で再送してください。"
        ),
    },
}


def render(reject_df: pd.DataFrame):
    st.subheader("💡 Reject 理由別 アドバイス & NSC へのフィードバック提案")

    active_reasons = reject_df["ERR_DS"].fillna("(不明)").unique().tolist()

    if not active_reasons:
        st.info("選択中のフィルター条件では Reject レコードがありません。")
        return

    for reason in active_reasons:
        count  = int((reject_df["ERR_DS"].fillna("(不明)") == reason).sum())
        advice = ADVICE.get(reason)

        with st.expander(f"🔴 {reason}  （{count:,} 件）", expanded=False):
            if advice:
                st.markdown(f"**📌 原因**  \n{advice['原因']}")
                st.markdown(f"**✅ アドバイス**  \n{advice['アドバイス']}")
                st.info(f"**📨 NSC へのフィードバック提案**\n\n{advice['NSC Feedback']}")
            else:
                st.warning("この理由に対するアドバイスは未登録です。")

    st.divider()
    st.subheader("Entity 別 Reject サマリー")
    entity_summary = (
        reject_df.groupby(["ENTY_CD", "ENTY_NM"])
        .agg(reject_count=("LND_SLS_ID", "count"))
        .reset_index()
        .sort_values("reject_count", ascending=False)
        .rename(columns={
            "ENTY_CD": "Entity Code",
            "ENTY_NM": "Entity 名",
            "reject_count": "Reject 件数",
        })
    )
    st.dataframe(entity_summary, use_container_width=True, hide_index=True)
