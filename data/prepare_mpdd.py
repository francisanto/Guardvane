"""
MPDD Data Preprocessing Pipeline for PromptShield AI.
Cleans and normalizes the MPDD dataset and saves the processed dataset to data/processed/mpdd_clean.csv.
"""

import os
from pathlib import Path
import pandas as pd


def get_raw_mpdd_path() -> Path:
    """
    Locates MPDD.csv from the environment variable, KaggleHub cache, or raises FileNotFoundError.
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

    raise FileNotFoundError(
        f"Raw MPDD dataset not found at: {cache_path}. "
        "Set the MPDD_PATH environment variable to point to MPDD.csv."
    )


def minimal_normalize_text(text: str) -> str:
    """
    Performs minimal text normalization:
    - Strips leading and trailing whitespace
    - Normalizes null bytes and carriage returns
    - Preserves case, punctuation, and critical security keywords ('ignore', 'system', 'previous', etc.)
    """
    if not isinstance(text, str):
        return ""
    # Strip null characters
    cleaned = text.replace("\x00", "")
    # Standardize newline characters
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    # Strip outer whitespace
    return cleaned.strip()


def prepare_dataset(
    input_path: Path,
    output_path: Path,
    prompt_col: str = "Prompt",
    label_col: str = "isMalicious"
) -> pd.DataFrame:
    """
    Preprocesses the raw MPDD dataset:
    1. Loads dataset
    2. Validates presence of prompt and label columns
    3. Validates labels are strictly binary (0 and 1)
    4. Applies minimal normalization
    5. Filters empty prompts
    6. Removes duplicate prompts
    7. Saves clean dataset to output_path
    """
    print(f"Loading raw dataset from: {input_path.resolve()}")
    df = pd.read_csv(input_path)
    initial_count = len(df)
    print(f"Initial raw record count: {initial_count:,}")

    # Validate columns
    if prompt_col not in df.columns or label_col not in df.columns:
        raise ValueError(
            f"Expected columns '{prompt_col}' and '{label_col}', "
            f"but found: {df.columns.tolist()}"
        )

    # Validate label types & values
    df[label_col] = pd.to_numeric(df[label_col], errors="coerce")
    invalid_labels = df[~df[label_col].isin([0, 1])]
    if not invalid_labels.empty:
        print(f"Dropping {len(invalid_labels)} rows with non-binary labels.")
        df = df[df[label_col].isin([0, 1])].copy()
    df[label_col] = df[label_col].astype(int)

    # Minimal text normalization
    df[prompt_col] = df[prompt_col].astype(str).apply(minimal_normalize_text)

    # Remove missing/empty prompts
    empty_mask = df[prompt_col].str.len() == 0
    empty_count = empty_mask.sum()
    if empty_count > 0:
        print(f"Dropping {empty_count} rows with empty prompt text.")
        df = df[~empty_mask].copy()

    # Deduplicate prompts
    # If duplicates have conflicting labels, keep the first occurrence or drop conflicts
    duplicate_count = df.duplicated(subset=[prompt_col]).sum()
    if duplicate_count > 0:
        print(f"Removing {duplicate_count:,} duplicate prompts.")
        df = df.drop_duplicates(subset=[prompt_col], keep="first").copy()

    final_count = len(df)
    print(f"Final clean record count: {final_count:,} (Removed: {initial_count - final_count:,})")

    # Verify label distribution
    dist = df[label_col].value_counts()
    print("\nCleaned Label Distribution:")
    for label_val, count in dist.items():
        label_name = "Malicious (1)" if label_val == 1 else "Benign (0)"
        pct = (count / final_count) * 100
        print(f"  {label_name}: {count:,} ({pct:.2f}%)")

    # Ensure output directory exists and save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved clean dataset to: {output_path.resolve()}")

    return df


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    raw_path = get_raw_mpdd_path()
    processed_file = base_dir / "data" / "processed" / "mpdd_clean.csv"

    prepare_dataset(raw_path, processed_file)
