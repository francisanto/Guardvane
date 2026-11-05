import pandas as pd

DATASET_PATH = "data/security_risk_dataset.csv"

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

data = pd.read_csv(DATASET_PATH)

print("Dataset size:", len(data))
print("Number of risk labels:", len(risk_labels))

print("\nRisk distribution:")
print(data[risk_labels].sum().sort_values())

print("\nApplication types:")
print(data["application_type"].value_counts())

print("\nExamples by risk:")
for risk in risk_labels:
    examples = data[data[risk] == 1]["prompt"].head(3)

    print("\n==============================")
    print(risk)
    print("==============================")

    for prompt in examples:
        print("-", prompt)