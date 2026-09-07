import pandas as pd
from pathlib import Path
import re
from collections import Counter

# READ-ONLY BLUEPRINT PATH
EXCEL_PATH = Path.cwd() / "Magic Card Data Base Current View.xlsx"

def scan_database_for_common_words():
    if not EXCEL_PATH.exists():
        print(f"Error: Could not find your spreadsheet at {EXCEL_PATH}")
        return

    print("Safely reading Excel sheet to isolate text patterns...")
    df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    df.columns = df.columns.str.strip()
    
    text_col = "Text" if "Text" in df.columns else "Rules Text"
    if text_col not in df.columns:
        print(f"Error: Could not find a text column. Available columns: {list(df.columns)}")
        return

    all_words = []
    print("Analyzing text strings across all cards...")
    
    # Isolate every single word used in your entire card pool database
    for _, row in df.iterrows():
        rules_text = str(row.get(text_col, "")).lower()
        if pd.isna(row.get(text_col)) or not rules_text.strip():
            continue
            
        # Clean out punctuation and isolate string words
        clean_text = re.sub(r'[^\w\s{}]', ' ', rules_text)
        words = clean_text.split()
        all_words.extend(words)

    # Count the overall frequencies
    word_counts = Counter(all_words)
    
    print("\n==============================================")
    print("   TOP 3000 MOST COMMON WORDS IN YOUR DATABASE  ")
    print("==============================================")
    print(f"Total individual words processed: {len(all_words)}")
    print(f"Unique words found: {len(word_counts)}")
    print("----------------------------------------------")
    print(f"{'Rank':<6}{'Word':<20}{'Occurrences':<10}")
    print("----------------------------------------------")
    
    for rank, (word, count) in enumerate(word_counts.most_common(3000), 1):
        print(f"{rank:<6}{word:<20}{count:<10}")

if __name__ == "__main__":
    scan_database_for_common_words()
