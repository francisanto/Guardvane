import json
import pandas as pd

SOURCE = "data/raw/web_security_payloads_clean.json"

OUTPUT = "data/processed/web_security_payloads.csv"


def process_dataset():
    with open(SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for item in data:
        vulnerability = item["id"].split("-")[0]

        rows.append({
            "id": item["id"],
            "vulnerability": vulnerability,
            "subtype": item.get("type", ""),
            "description": item.get("description", ""),
            "payload": item.get("payload", ""),
            "context": item.get("context", ""),
            "severity": item.get("severity", "")
        })

    df = pd.DataFrame(rows)

    print("Total records:", len(df))
    print("\nVulnerability counts:")
    print(df["vulnerability"].value_counts())

    print("\nSample:")
    print(df.head())

    df.to_csv(OUTPUT, index=False)

    print(f"\nSaved to: {OUTPUT}")


if __name__ == "__main__":
    process_dataset()