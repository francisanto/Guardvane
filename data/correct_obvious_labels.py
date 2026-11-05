import pandas as pd

DATASET_PATH = "data/security_risk_dataset.csv"

data = pd.read_csv(DATASET_PATH)

changes = []


def remove_label(condition, label, reason):
    global data

    mask = condition & (data[label] == 1)
    count = mask.sum()

    if count > 0:
        data.loc[mask, label] = 0

        changes.append({
            "label": label,
            "rows_changed": int(count),
            "reason": reason
        })


# ---------------------------------------------------------
# 1. PostgreSQL/database alone does NOT imply SQL injection
# ---------------------------------------------------------

remove_label(
    data["prompt"].str.contains(
        r"login system.*postgresql|login system.*database",
        case=False,
        regex=True,
        na=False
    ),
    "sqli",
    "Database technology alone does not establish a SQL injection attack surface."
)


# ---------------------------------------------------------
# 2. Basic authentication does NOT automatically imply
#    authorization weakness
# ---------------------------------------------------------

remove_label(
    data["prompt"].str.contains(
        r"login system|registration and login",
        case=False,
        regex=True,
        na=False
    )
    & ~data["prompt"].str.contains(
        r"role|admin|permission|privilege|access control",
        case=False,
        regex=True,
        na=False
    ),
    "authz_weakness",
    "Authentication alone does not establish an authorization weakness."
)


# ---------------------------------------------------------
# 3. Basic login does NOT automatically imply CSRF
# ---------------------------------------------------------

remove_label(
    data["prompt"].str.contains(
        r"login system|registration and login",
        case=False,
        regex=True,
        na=False
    )
    & ~data["prompt"].str.contains(
        r"update|delete|change|transfer|purchase|payment|refund|submit|manage",
        case=False,
        regex=True,
        na=False
    ),
    "csrf",
    "Basic authentication alone does not establish a meaningful CSRF attack surface."
)


# ---------------------------------------------------------
# 4. File upload alone does NOT establish path traversal
# ---------------------------------------------------------

remove_label(
    data["prompt"].str.contains(
        r"upload.*file|upload.*pdf|upload.*image|upload.*document|upload.*csv",
        case=False,
        regex=True,
        na=False
    )
    & ~data["prompt"].str.contains(
        r"path|filename|file name|directory|folder|filesystem|file path",
        case=False,
        regex=True,
        na=False
    ),
    "path_traversal",
    "File upload alone does not establish a path traversal attack surface."
)


# ---------------------------------------------------------
# 5. AI tool access does NOT automatically imply
#    prompt injection
# ---------------------------------------------------------

remove_label(
    (data["ai_tool_risk"] == 1)
    & ~data["prompt"].str.contains(
        r"untrusted|embedded|retrieved|uploaded|document|email|search result|source file|external instruction",
        case=False,
        regex=True,
        na=False
    ),
    "prompt_injection",
    "AI tool access alone does not establish prompt injection."
)


# ---------------------------------------------------------
# 6. ML training does NOT automatically imply model extraction
# ---------------------------------------------------------

remove_label(
    (data["data_poisoning"] == 1)
    & ~data["prompt"].str.contains(
        r"api|endpoint|query|prediction|inference|model access|black.box",
        case=False,
        regex=True,
        na=False
    ),
    "model_extraction",
    "Training data access alone does not establish model extraction exposure."
)


# ---------------------------------------------------------
# Save corrected dataset
# ---------------------------------------------------------

data.to_csv(DATASET_PATH, index=False)

print("\nDataset correction completed.")

print("\nChanges made:")

for change in changes:
    print(
        f"- {change['label']}: "
        f"{change['rows_changed']} rows"
    )
    print(f"  Reason: {change['reason']}")

print("\nNew risk distribution:")

risk_labels = [
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

print(data[risk_labels].sum().sort_values())