import pandas as pd
import streamlit as st
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


def label_sentiment(compound_score: float) -> str:
    if compound_score >= 0.05:
        return "Positive"
    if compound_score <= -0.05:
        return "Negative"
    return "Neutral"


st.set_page_config(page_title="SENTIFY", page_icon="📊", layout="wide")
st.title("SENTIFY : Turn Reviews into Clarity")
st.write("Upload a CSV file with one review column to analyze sentiment.")

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
    except Exception as exc:
        st.error(f"Could not read CSV file: {exc}")
        st.stop()

    if df.empty:
        st.warning("The uploaded CSV is empty.")
        st.stop()

    st.subheader("Select the review column")
    default_col = df.columns[0]
    review_col = st.selectbox("Review text column", options=df.columns, index=0)
    if default_col != review_col:
        st.caption(f"Using selected column: {review_col}")

    working_df = df.copy()
    working_df[review_col] = working_df[review_col].astype(str).fillna("")
    working_df = working_df[working_df[review_col].str.strip() != ""]

    if working_df.empty:
        st.warning("No valid review text found in the selected column.")
        st.stop()

    analyzer = SentimentIntensityAnalyzer()

    working_df["compound_score"] = working_df[review_col].apply(
        lambda text: analyzer.polarity_scores(text)["compound"]
    )
    working_df["sentiment_label"] = working_df["compound_score"].apply(label_sentiment)

    total = len(working_df)
    label_counts = (
        working_df["sentiment_label"]
        .value_counts()
        .reindex(["Positive", "Negative", "Neutral"], fill_value=0)
    )

    positive_pct = (label_counts["Positive"] / total) * 100
    negative_pct = (label_counts["Negative"] / total) * 100
    neutral_pct = (label_counts["Neutral"] / total) * 100
    avg_score = working_df["compound_score"].mean()

    if positive_pct > negative_pct and positive_pct >= neutral_pct:
        final_verdict = "Overall Positive 👍"
    elif negative_pct > positive_pct and negative_pct >= neutral_pct:
        final_verdict = "Overall Negative 👎"
    else:
        final_verdict = "Overall Neutral / Mixed 😐"

    st.subheader("Overall Result")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Positive %", f"{positive_pct:.2f}%")
    col2.metric("Negative %", f"{negative_pct:.2f}%")
    col3.metric("Neutral %", f"{neutral_pct:.2f}%")
    col4.metric("Average Compound Score", f"{avg_score:.3f}")

    st.success(final_verdict)

    st.subheader("Labeled Reviews")
    st.dataframe(
        working_df[[review_col, "sentiment_label", "compound_score"]],
        use_container_width=True,
    )

    csv_out = working_df[[review_col, "sentiment_label", "compound_score"]].to_csv(index=False)
    st.download_button(
        label="Download labeled CSV",
        data=csv_out,
        file_name="labeled_reviews.csv",
        mime="text/csv",
    )
else:
    st.info("Upload a CSV file to begin analysis.")