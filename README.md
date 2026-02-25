# SENTIFY - Review Sentiment Analyzer (VADER)

SENTIFY is a Streamlit app that can either read a CSV file of reviews or fetch Google Play Store reviews by app ID, label each review as **Positive**, **Negative**, or **Neutral** using VADER, and show overall sentiment percentages.

## Features

- Upload a CSV file
- Select the review text column
- Fetch Play Store reviews using app ID (no API key)
- **Stratified sampling**: Reviews fetched across all star ratings (1-5) for balanced sentiment representation
- Batch fetch and batch sentiment processing with live progress bars
- Per-review sentiment label and compound score
- Overall Positive/Negative/Neutral percentage summary
- Final verdict based on dominant sentiment
- Download labeled CSV output with star ratings (Play Store mode)

## Tech Stack

- Python
- Streamlit
- Pandas
- vaderSentiment (VADER)
- google-play-scraper

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

## Input format

- CSV with at least one column containing review text
- Choose that column in the app UI
- For Play Store mode, provide app ID (example: `com.whatsapp`)

## Why Stratified Sampling?

When fetching Play Store reviews, SENTIFY uses **stratified sampling** by fetching reviews across all 5 star ratings (1-5 stars) instead of just the newest reviews. This ensures:
- Balanced representation of negative, neutral, and positive reviews
- More accurate overall sentiment analysis
- True reflection of the app's actual sentiment distribution
