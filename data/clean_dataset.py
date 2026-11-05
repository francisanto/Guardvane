import json
import re

SOURCE = "data/raw/web_security_payloads.json"
OUTPUT = "data/raw/web_security_payloads_clean.json"


def clean_dataset():
    with open(SOURCE, "r", encoding="utf-8") as f:
        text = f.read()

    # Fix non-breaking spaces
    text = text.replace("\xa0", " ")

    # Fix invalid JSON \xNN escapes
    text = re.sub(
        r"\\x([0-9a-fA-F]{2})",
        lambda m: "\\u00" + m.group(1),
        text
    )

    # Add missing commas between JSON objects
    text = re.sub(
        r"(\})\s*(\{)",
        r"\1,\2",
        text
    )

    # Parse the cleaned JSON
    data = json.loads(text)

    # Save clean dataset
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Cleaned successfully: {len(data)} records")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    clean_dataset()