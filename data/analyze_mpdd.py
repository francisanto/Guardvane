"""
MPDD Dataset Analysis Script for PromptShield AI.
Inspects the Kaggle MPDD (Malicious Prompt Detection Dataset) without modifying the source file.
"""

import os
from pathlib import Path
import pandas as pd


def get_mpdd_path() -> Path:
    """
    Resolves the path to MPDD.csv.
    Checks environment variable, default KaggleHub cache directory, or attempts download via kagglehub.
    """
    env_path = os.environ.get("MPDD_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    cache_path = (
        Path.home()
        / ".cache"
        / "kagglehub"
        / "datasets"
        / "mohammedaminejebbar"
        / "malicious-prompt-detection-dataset-mpdd"
        / "versions"
        / "2"
        / "MPDD.csv"
    )
    if cache_path.exists():
        return cache_path

    # Fallback to kagglehub if available
    try:
        import kagglehub

        downloaded_dir = kagglehub.dataset_download(
            "mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd"
        )
        downloaded_file = Path(downloaded_dir) / "MPDD.csv"
        if downloaded_file.exists():
            return downloaded_file
    except Exception:
        pass

    raise FileNotFoundError(
        f"MPDD.csv not found at default cache path: {cache_path}. "
        "Please specify MPDD_PATH environment variable."
    )


def analyze_dataset(file_path: Path) -> pd.DataFrame:
    """
    Loads and runs diagnostic inspection on MPDD.csv.
    """
    print("=" * 60)
    print("MPDD DATASET INSPECTION")
    print("=" * 60)
    print(f"Loading dataset from: {file_path.resolve()}\n")

    df = pd.read_csv(file_path)

    # 1 & 2. Dataset Shape
    print("----- 1. DATASET SHAPE -----")
    print(f"Rows: {df.shape[0]:,}, Columns: {df.shape[1]}")

    # 3. Columns
    print("\n----- 2. COLUMNS -----")
    print(df.columns.tolist())

    # 4. Data Types
    print("\n----- 3. DATA TYPES -----")
    print(df.dtypes.to_string())

    # 5. Missing Values
    print("\n----- 4. MISSING VALUES -----")
    missing = df.isnull().sum()
    print(missing.to_string())

    # 6. Duplicate Count
    print("\n----- 5. DUPLICATES -----")
    exact_duplicates = df.duplicated().sum()
    prompt_col = "Prompt" if "Prompt" in df.columns else df.columns[0]
    prompt_duplicates = df.duplicated(subset=[prompt_col]).sum()
    print(f"Exact full-row duplicates: {exact_duplicates}")
    print(f"Duplicate prompts ('{prompt_col}'): {prompt_duplicates}")

    # 7 & 8. Label Distribution & Percentage
    label_col = "isMalicious" if "isMalicious" in df.columns else df.columns[1]
    print(f"\n----- 6. LABEL DISTRIBUTION ('{label_col}') -----")
    counts = df[label_col].value_counts(dropna=False)
    percentages = df[label_col].value_counts(normalize=True, dropna=False) * 100
    distribution_df = pd.DataFrame({"Count": counts, "Percentage (%)": percentages.round(2)})
    print(distribution_df.to_string())

    # 9. Random Examples from Both Classes
    print("\n----- 7. RANDOM EXAMPLES (BENIGN: 0) -----")
    benign_samples = df[df[label_col] == 0].sample(n=min(3, len(df[df[label_col] == 0])), random_state=42)
    for idx, row in benign_samples.iterrows():
        print(f"\n[Index {idx}]")
        print(f"Prompt: {row[prompt_col]}")

    print("\n----- 8. RANDOM EXAMPLES (MALICIOUS: 1) -----")
    malicious_samples = df[df[label_col] == 1].sample(n=min(3, len(df[df[label_col] == 1])), random_state=42)
    for idx, row in malicious_samples.iterrows():
        print(f"\n[Index {idx}]")
        print(f"Prompt: {row[prompt_col]}")

    print("\n" + "=" * 60)
    print("DATASET INSPECTION COMPLETE")
    print("=" * 60)

    return df


if __name__ == "__main__":
    mpdd_file = get_mpdd_path()
    analyze_dataset(mpdd_file)
