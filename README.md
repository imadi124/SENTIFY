# SENTIFY - CSV Sentiment Analyzer (VADER)

SENTIFY is a Streamlit app that reads a CSV file of reviews, labels each review as **Positive**, **Negative**, or **Neutral** using VADER, and shows overall sentiment percentages.

## Features

- Upload a CSV file
- Select the review text column
- Per-review sentiment label and compound score
- Overall Positive/Negative/Neutral percentage summary
- Final verdict based on dominant sentiment
- Download labeled CSV output

## Tech Stack

- Python
- Streamlit
- Pandas
- vaderSentiment (VADER)

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
