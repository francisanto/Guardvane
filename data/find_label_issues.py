import pandas as pd

DATASET_PATH = "data/security_risk_dataset.csv"

data = pd.read_csv(DATASET_PATH)


def show_cases(title, condition):
    cases = data[condition]

    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

    print("Number of cases:", len(cases))

    for _, row in cases.head(10).iterrows():
        print("\nPrompt:")
        print(row["prompt"])

        print("Labels:")
        labels = [
            column
            for column in [
                "sqli",
                "xss",
                "ssrf",
                "idor",
                "auth_weakness",
                "authz_weakness",
                "file_upload",
                "path_traversal",
                "command_injection",
                "csrf",
                "sensitive_data",
                "prompt_injection",
                "data_poisoning",
                "model_extraction",
                "ai_tool_risk"
            ]
            if row[column] == 1
        ]

        print(labels)


# ---------------------------------------------------------
# 1. Database mentioned but SQL injection marked as 1
# ---------------------------------------------------------

show_cases(
    "DATABASE + SQL INJECTION",
    data["sqli"].eq(1) &
    data["technologies"].fillna("").str.contains(
        "postgres|mysql|database|mongodb|sql",
        case=False,
        regex=True
    )
)


# ---------------------------------------------------------
# 2. Authentication + Authorization + CSRF together
# ---------------------------------------------------------

show_cases(
    "AUTH + AUTHZ + CSRF",
    (data["auth_weakness"] == 1) &
    (data["authz_weakness"] == 1) &
    (data["csrf"] == 1)
)


# ---------------------------------------------------------
# 3. File upload + Path Traversal
# ---------------------------------------------------------

show_cases(
    "FILE UPLOAD + PATH TRAVERSAL",
    (data["file_upload"] == 1) &
    (data["path_traversal"] == 1)
)


# ---------------------------------------------------------
# 4. AI Tool Risk + Prompt Injection
# ---------------------------------------------------------

show_cases(
    "AI TOOL RISK + PROMPT INJECTION",
    (data["ai_tool_risk"] == 1) &
    (data["prompt_injection"] == 1)
)


# ---------------------------------------------------------
# 5. Model Extraction + Data Poisoning
# ---------------------------------------------------------

show_cases(
    "MODEL EXTRACTION + DATA POISONING",
    (data["model_extraction"] == 1) &
    (data["data_poisoning"] == 1)
)