import os
import pandas as pd

MPDD_DIR = r"C:\Users\franc\.cache\kagglehub\datasets\mohammedaminejebbar\malicious-prompt-detection-dataset-mpdd\versions\2"

file_path = os.path.join(MPDD_DIR, "MPDD.csv")

df = pd.read_csv(file_path)

print("\n===== DATASET SIZE =====")
print(df.shape)

print("\n===== COLUMNS =====")
print(df.columns.tolist())

print("\n===== FIRST 10 ROWS =====")
print(df.head(10).to_string())

print("\n===== DATA TYPES =====")
print(df.dtypes)

print("\n===== MISSING VALUES =====")
print(df.isnull().sum())

print("\n===== UNIQUE VALUES =====")
for column in df.columns:
    print(f"\n--- {column} ---")
    print(df[column].value_counts().head(20))