import pandas as pd
import streamlit as st
import math
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    from google_play_scraper import Sort, reviews
    PLAYSTORE_IMPORT_ERROR = None
except ModuleNotFoundError as exc:
    Sort = None
    reviews = None
    PLAYSTORE_IMPORT_ERROR = str(exc)


def label_sentiment(compound_score: float) -> str:
    if compound_score >= 0.05:
        return "Positive"
    if compound_score <= -0.05:
        return "Negative"
    return "Neutral"


def analyze_reviews_in_batches(
    input_df: pd.DataFrame,
    review_col: str,
    batch_size: int = 500,
    progress_callback=None,
) -> pd.DataFrame:
    analyzer = SentimentIntensityAnalyzer()
    processed_batches = []
    total_rows = len(input_df)
    total_batches = max(1, math.ceil(total_rows / batch_size))

    if total_rows == 0:
        empty_df = input_df.copy()
        empty_df["compound_score"] = []
        empty_df["sentiment_label"] = []
        return empty_df

    for batch_number, start in enumerate(range(0, total_rows, batch_size), start=1):
        end = min(start + batch_size, total_rows)
        batch = input_df.iloc[start:end].copy()
        batch["compound_score"] = batch[review_col].apply(
            lambda text: analyzer.polarity_scores(text)["compound"]
        )
        batch["sentiment_label"] = batch["compound_score"].apply(label_sentiment)
        processed_batches.append(batch)

        if progress_callback is not None:
            progress_callback(batch_number, total_batches, end, total_rows)

    return pd.concat(processed_batches, ignore_index=True)


def render_summary(working_df: pd.DataFrame, review_col: str, source_name: str, show_rating: bool = False) -> None:
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
    if show_rating and "rating" in working_df.columns:
        display_cols = [review_col, "rating", "sentiment_label", "compound_score"]
    else:
        display_cols = [review_col, "sentiment_label", "compound_score"]
    
    st.dataframe(
        working_df[display_cols],
        use_container_width=True,
    )

    csv_out = working_df[display_cols].to_csv(index=False)
    st.download_button(
        label=f"Download labeled {source_name} CSV",
        data=csv_out,
        file_name=f"labeled_{source_name.lower()}_reviews.csv",
        mime="text/csv",
    )


def fetch_playstore_reviews(
    app_id: str,
    total_reviews: int,
    batch_size: int,
    progress_callback=None,
) -> pd.DataFrame:
    """
    Fetch reviews with stratified sampling across all 5 star ratings (1-5).
    This ensures balanced representation of negative, neutral, and positive reviews.
    """
    if reviews is None or Sort is None:
        raise RuntimeError(
            "Play Store review fetching requires the 'google-play-scraper' package. "
            "Install dependencies with: pip install -r requirements.txt"
        )

    all_reviews = []
    star_ratings = [1, 2, 3, 4, 5]
    base_target = total_reviews // len(star_ratings)
    remainder = total_reviews % len(star_ratings)
    target_per_star = {
        star: base_target + (1 if index < remainder else 0)
        for index, star in enumerate(star_ratings)
    }
    total_batches = len(star_ratings)

    for batch_number, star_rating in enumerate(star_ratings, start=1):
        star_reviews = []
        continuation_token = None
        star_target = target_per_star[star_rating]

        try:
            # Fetch multiple batches for this star rating if needed
            while len(star_reviews) < star_target:
                fetch_count = min(batch_size, star_target - len(star_reviews))
                result, continuation_token = reviews(
                    app_id,
                    lang="en",
                    country="us",
                    sort=Sort.NEWEST,
                    count=fetch_count,
                    filter_score_with=star_rating,
                    continuation_token=continuation_token,
                )

                if not result:
                    break

                star_reviews.extend(result)

                if len(star_reviews) > star_target:
                    star_reviews = star_reviews[:star_target]

                if continuation_token is None:
                    break
        except Exception:
            star_reviews = []

        all_reviews.extend(star_reviews[:star_target])

        if len(all_reviews) > total_reviews:
            all_reviews = all_reviews[:total_reviews]

        fetched_count = len(all_reviews)
        if progress_callback is not None:
            progress_callback(
                batch_number,
                total_batches,
                fetched_count,
                total_reviews,
            )

    if not all_reviews:
        return pd.DataFrame(columns=["review_text", "rating"])

    play_df = pd.DataFrame(all_reviews)
    play_df["review_text"] = play_df["content"].astype(str).fillna("")
    play_df["rating"] = play_df["score"].astype(int)
    play_df = play_df[play_df["review_text"].str.strip() != ""]
    return play_df[["review_text", "rating"]].reset_index(drop=True)


st.set_page_config(page_title="SENTIFY", page_icon="📊", layout="wide")
st.title("SENTIFY : Turn Reviews into Clarity")
st.write("Analyze reviews from a CSV file or fetch them directly from Google Play Store.")

tab_csv, tab_play = st.tabs(["Upload CSV", "Play Store App Reviews"])

with tab_csv:
    MAX_CSV_SIZE_MB = 80

    uploaded_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        help=f"Maximum file size: {MAX_CSV_SIZE_MB} MB. Larger files will be rejected.",
    )

    if uploaded_file is not None:
        file_size_mb = uploaded_file.size / (1024 * 1024)

        if file_size_mb > MAX_CSV_SIZE_MB:
            st.error(
                f"**File too large!**\n\n"
                f"Your file is **{file_size_mb:.1f} MB** — "
                f"the maximum allowed size is **{MAX_CSV_SIZE_MB} MB**.\n\n"
                "Try splitting the file into smaller parts or removing unnecessary columns."
            )
            st.stop()

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

        batch_size_csv = st.number_input(
            "CSV sentiment batch size",
            min_value=50,
            max_value=5000,
            value=500,
            step=50,
        )

        if st.button("Analyze CSV Reviews"):
            with st.spinner("Analyzing CSV reviews..."):
                analyzed_df = analyze_reviews_in_batches(
                    working_df,
                    review_col,
                    int(batch_size_csv),
                )
            render_summary(analyzed_df, review_col, "csv")
    else:
        st.info("Upload a CSV file to begin analysis.")

with tab_play:
    st.subheader("Fetch reviews from Google Play Store")
    st.info(
        "**Balanced Sampling**: Reviews are fetched across all star ratings (1-5)"
    )

    if PLAYSTORE_IMPORT_ERROR is not None:
        st.error(
            "Play Store fetching is currently unavailable because the required package "
            "is not installed in this Python environment: "
            f"{PLAYSTORE_IMPORT_ERROR}. Install dependencies with: pip install -r requirements.txt"
        )

    app_id = st.text_input("Play Store App ID", value="com.whatsapp")

    total_reviews = st.number_input(
        "How many reviews to fetch",
        min_value=50,
        max_value=5000,
        value=500,
        step=50,
    )
    fetch_batch_size = st.number_input(
        "Fetch batch size (per star rating)",
        min_value=20,
        max_value=200,
        value=100,
        step=20,
    )
    sentiment_batch_size = st.number_input(
        "Sentiment processing batch size",
        min_value=50,
        max_value=5000,
        value=500,
        step=50,
    )

    if st.button("Fetch & Analyze Play Store Reviews"):
        if not app_id.strip():
            st.error("Please enter a valid Play Store App ID.")
            st.stop()

        try:
            fetch_progress = st.progress(0, text="Fetching reviews from Play Store...")

            def update_fetch_progress(batch_number, total_batches, fetched_count, target_reviews):
                percent = min(100, int((batch_number / max(total_batches, 1)) * 100))
                fetch_progress.progress(
                    percent,
                    text=(
                        f"Fetching reviews from Play Store (stratified)... "
                        f"Star rating {batch_number}/{total_batches} | {fetched_count} reviews fetched"
                    ),
                )

            play_df = fetch_playstore_reviews(
                app_id=app_id.strip(),
                total_reviews=int(total_reviews),
                batch_size=int(fetch_batch_size),
                progress_callback=update_fetch_progress,
            )
            fetch_progress.progress(100, text="Fetching reviews from Play Store... done")
        except Exception as exc:
            st.error(f"Could not fetch Play Store reviews: {exc}")
            st.stop()

        if play_df.empty:
            st.warning("No reviews were fetched for this app ID.")
            st.stop()

        st.success(f"Fetched {len(play_df)} balanced reviews from Play Store.")

        analyze_progress = st.progress(0, text="Analyzing Play Store reviews...")

        def update_analyze_progress(batch_number, total_batches, processed_count, total_count):
            percent = min(100, int((processed_count / max(total_count, 1)) * 100))
            analyze_progress.progress(
                percent,
                text=(
                    f"Analyzing Play Store reviews... "
                    f"Batch {batch_number}/{total_batches} | {processed_count}/{total_count}"
                ),
            )

        analyzed_play_df = analyze_reviews_in_batches(
            play_df,
            review_col="review_text",
            batch_size=int(sentiment_batch_size),
            progress_callback=update_analyze_progress,
        )
        analyze_progress.progress(100, text="Analyzing Play Store reviews... done")

        render_summary(analyzed_play_df, "review_text", "playstore", show_rating=True)

st.divider()
st.markdown("Made with ❣️ by **Abhay Aditya** and **Nimisha Shukla**")