import pandas as pd
from pathlib import Path

DATASET = Path("data/security_risk_dataset.csv")


def make_row(
    prompt,
    application_type,
    features,
    data_types,
    technologies,
    user_roles,
    external_inputs,
    security_controls,
    risks
):
    labels = [
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
        "ai_tool_risk",
    ]

    row = {
        "prompt": prompt,
        "application_type": application_type,
        "features": features,
        "data_types": data_types,
        "technologies": technologies,
        "user_roles": user_roles,
        "external_inputs": external_inputs,
        "security_controls": security_controls,
    }

    for label in labels:
        row[label] = 1 if label in risks else 0

    return row


examples = []


# ---------------------------------------------------------
# CSRF
# ---------------------------------------------------------

csrf_prompts = [
    "Build a banking website where logged-in users can transfer money using a web form.",
    "Create a web application where authenticated users can change their email address.",
    "Build an admin portal where administrators can delete user accounts through browser forms.",
    "Create a shopping website where logged-in customers can change their shipping address.",
    "Build a web application allowing authenticated users to update their profile information.",
    "Create a payment dashboard where users can add and remove saved payment methods.",
    "Build a web application where users can change their account password from a browser.",
    "Create an employee portal where employees can submit requests while logged in.",
    "Build an application where administrators can modify user permissions through forms.",
    "Create a web application where users can create API keys from their account settings.",
    "Build a customer portal where authenticated customers can cancel subscriptions.",
    "Create a web application allowing users to modify notification settings.",
    "Build an online store where authenticated users can place orders.",
    "Create a web application where users can change their phone number.",
    "Build an admin dashboard where administrators can approve submitted applications.",
    "Create a web application where users can update their billing information.",
    "Build a web portal where employees can submit expense claims.",
    "Create an application where authenticated users can deactivate their accounts.",
    "Build a website where logged-in users can create and delete saved addresses.",
    "Create an admin application where administrators can change account roles.",
    "Build a customer portal where users can request refunds.",
    "Create a web application where authenticated users can connect external accounts.",
    "Build a web application where users can modify account preferences.",
    "Create an application where administrators can disable user accounts.",
]


for prompt in csrf_prompts:
    examples.append(
        make_row(
            prompt,
            "web_application",
            ["authenticated_actions", "browser_forms"],
            ["user_account_data"],
            ["Next.js"],
            ["user", "admin"],
            ["form_input"],
            [],
            ["csrf"],
        )
    )


# ---------------------------------------------------------
# SENSITIVE DATA
# ---------------------------------------------------------

sensitive_prompts = [
    "Build a healthcare application that stores patient medical records and allows doctors to view them.",
    "Create an application that stores customer names, addresses, phone numbers and email addresses.",
    "Build a banking application that stores customer account information and transaction history.",
    "Create a user management system that stores passwords, email addresses and phone numbers.",
    "Build a recruitment platform that stores candidate resumes and personal information.",
    "Create a school management system containing student records and parent contact information.",
    "Build an insurance application storing customer identity and policy information.",
    "Create a finance dashboard containing customer transactions and account information.",
    "Build an HR application storing employee salary and personal information.",
    "Create a medical appointment system storing patient information and appointment history.",
    "Build an application that stores government identification information for users.",
    "Create a customer support system containing private customer conversations.",
    "Build a platform storing user authentication credentials and account recovery information.",
    "Create an application storing employee tax and payroll information.",
    "Build a healthcare portal containing medical reports uploaded by patients.",
    "Create a financial application storing credit card and banking information.",
    "Build an application that stores private user documents and identity information.",
    "Create a student portal containing grades, addresses and personal records.",
    "Build a recruitment system storing candidate identification documents.",
    "Create an application storing confidential business documents uploaded by employees.",
    "Build a customer database containing names, phone numbers and purchase history.",
    "Create a legal application storing confidential client documents.",
    "Build a platform storing user location history and personal profiles.",
    "Create an application that stores employee performance and salary information.",
]


for prompt in sensitive_prompts:
    examples.append(
        make_row(
            prompt,
            "web_application",
            ["data_storage", "user_records"],
            ["PII", "confidential_data"],
            ["PostgreSQL"],
            ["user", "admin"],
            ["user_input"],
            [],
            ["sensitive_data"],
        )
    )


# ---------------------------------------------------------
# COMMAND INJECTION
# ---------------------------------------------------------

command_prompts = [
    "Build a web application that allows administrators to execute server-side maintenance commands.",
    "Create a backend service where users can submit shell commands for processing.",
    "Build an application that runs system utilities based on parameters supplied by users.",
    "Create a server management dashboard allowing administrators to execute operating system commands.",
    "Build an API that accepts user-provided commands and executes them on the server.",
    "Create a deployment dashboard that runs shell scripts based on user input.",
    "Build a web application that converts user-provided files using command-line utilities.",
    "Create an application that invokes external system programs using user-supplied parameters.",
    "Build a server monitoring tool that executes diagnostic commands selected by users.",
    "Create a web service that accepts command-line arguments through an API.",
    "Build an application that executes image processing utilities using user-provided filenames.",
    "Create a server administration interface for running shell scripts.",
    "Build an API that executes operating system utilities according to request parameters.",
    "Create a web tool that converts documents using locally installed command-line programs.",
    "Build a backend that dynamically constructs shell commands from request parameters.",
    "Create an admin panel for executing maintenance scripts on production servers.",
    "Build a service that executes user-selected system utilities.",
    "Create an API endpoint that runs scripts with parameters received from clients.",
    "Build a web application that uses shell commands to process uploaded files.",
    "Create a deployment platform where project configuration determines shell commands.",
    "Build an application that launches operating-system processes based on user requests.",
    "Create a backend service that dynamically constructs command strings.",
    "Build a server utility that accepts filenames and passes them to command-line tools.",
    "Create a web application that allows users to trigger server-side scripts.",
]


for prompt in command_prompts:
    examples.append(
        make_row(
            prompt,
            "web_application",
            ["server_command_execution"],
            ["user_input"],
            ["Python", "Linux"],
            ["user", "admin"],
            ["command_input"],
            [],
            ["command_injection"],
        )
    )


# ---------------------------------------------------------
# PROMPT INJECTION
# ---------------------------------------------------------

prompt_injection_prompts = [
    "Build an AI assistant that reads user documents and follows instructions contained inside those documents.",
    "Create an AI agent that processes webpages and executes instructions found in the webpage content.",
    "Build a chatbot that summarizes emails and follows action requests contained in email messages.",
    "Create an AI assistant that reads uploaded files and uses their contents as instructions.",
    "Build an AI coding agent that can read project files and follow instructions found inside source files.",
    "Create an AI assistant that processes external documents before deciding what actions to perform.",
    "Build an agent that reads customer messages and performs tasks requested inside those messages.",
    "Create an AI system that retrieves webpages and uses retrieved content to determine its next actions.",
    "Build an autonomous assistant that processes untrusted text and can call tools.",
    "Create an AI agent that reads tickets submitted by users and performs requested administrative actions.",
    "Build an assistant that processes third-party knowledge-base articles and can execute tools.",
    "Create an AI agent that follows instructions embedded in retrieved search results.",
    "Build an AI assistant that reads external documents and can send emails.",
    "Create an agent that processes web content and can update records in a database.",
    "Build an AI assistant that receives arbitrary user text and can invoke application tools.",
    "Create an AI agent that uses retrieved documents as context and can perform external actions.",
    "Build an AI chatbot that can execute commands based on instructions in uploaded documents.",
    "Create an AI assistant that reads untrusted webpages and decides which APIs to call.",
    "Build an autonomous agent that processes user-provided text and can perform account operations.",
    "Create an AI system that treats retrieved content as instructions for tool execution.",
    "Build an AI assistant that reads external files and can modify application data.",
    "Create an AI agent that processes untrusted content before invoking internal APIs.",
    "Build an assistant that reads messages from unknown users and performs requested actions.",
    "Create an AI agent that can execute tools after reading arbitrary external text.",
]


for prompt in prompt_injection_prompts:
    examples.append(
        make_row(
            prompt,
            "ai_agent",
            ["retrieval", "tool_use", "external_content"],
            ["untrusted_text"],
            ["LLM", "Python"],
            ["user"],
            ["documents", "web_content"],
            [],
            ["prompt_injection"],
        )
    )


# ---------------------------------------------------------
# AI TOOL RISK
# ---------------------------------------------------------

ai_tool_prompts = [
    "Build an AI agent that can send emails and modify customer records.",
    "Create an autonomous assistant that can execute shell commands and update files.",
    "Build an AI agent with access to a production database and external APIs.",
    "Create an AI assistant that can create, modify and delete cloud resources.",
    "Build an AI coding agent that can modify project files and run terminal commands.",
    "Create an AI assistant that can make purchases using connected APIs.",
    "Build an autonomous agent that can manage user accounts and permissions.",
    "Create an AI system that can call internal APIs on behalf of users.",
    "Build an AI agent that can execute database queries and modify records.",
    "Create an assistant with access to email, calendar and cloud storage.",
    "Build an autonomous coding agent that can install packages and execute programs.",
    "Create an AI assistant that can access private company documents and send messages.",
    "Build an agent that can create users and assign administrative roles.",
    "Create an AI system that can execute deployment commands in a cloud environment.",
    "Build an AI assistant that can access production logs and perform remediation actions.",
    "Create an agent capable of modifying infrastructure configuration.",
    "Build an AI assistant that can delete files and modify databases.",
    "Create an autonomous agent with access to payment and customer APIs.",
    "Build an AI system that can execute arbitrary tools selected by its reasoning process.",
    "Create an AI agent with unrestricted access to application tools.",
    "Build an assistant that can modify source code and deploy it automatically.",
    "Create an AI agent that can access internal systems without human approval.",
    "Build an autonomous assistant that can perform administrative operations.",
    "Create an AI agent with broad permissions across multiple services.",
]


for prompt in ai_tool_prompts:
    examples.append(
        make_row(
            prompt,
            "ai_agent",
            ["tool_use", "external_actions"],
            ["application_data"],
            ["LLM", "Python", "APIs"],
            ["user", "admin"],
            ["tool_calls"],
            [],
            ["ai_tool_risk"],
        )
    )


# ---------------------------------------------------------
# MODEL EXTRACTION
# ---------------------------------------------------------

model_extraction_prompts = [
    "Build an ML prediction API that allows unlimited users to query the trained model.",
    "Create a public machine learning API that returns detailed predictions for arbitrary inputs.",
    "Build a model serving endpoint without restricting the number of prediction requests.",
    "Create an AI API where users can repeatedly query the model and receive prediction outputs.",
    "Build a public inference service exposing a proprietary machine learning model.",
    "Create an API that provides highly detailed model outputs to every client.",
    "Build a prediction platform where users can submit unlimited queries to the model.",
    "Create a public LLM endpoint exposing detailed responses from a proprietary model.",
    "Build an ML service where clients can make unrestricted repeated inference requests.",
    "Create a public model API without request limits.",
    "Build an AI service that exposes model predictions directly to anonymous users.",
    "Create a machine learning API allowing unlimited automated queries.",
    "Build a public inference endpoint for a proprietary classification model.",
    "Create an AI prediction API with no restrictions on client requests.",
    "Build a model-serving platform exposing prediction probabilities to external users.",
    "Create a public AI API that allows large numbers of automated queries.",
    "Build an inference service where users can repeatedly query the same model.",
    "Create a prediction API that exposes detailed confidence scores.",
    "Build a public ML endpoint without query monitoring.",
    "Create an AI service that permits unlimited inference requests.",
    "Build a model API exposing detailed outputs to untrusted clients.",
    "Create an ML prediction endpoint accessible to anonymous users.",
    "Build an AI model service without query quotas.",
    "Create a public inference API with unrestricted access.",
]


for prompt in model_extraction_prompts:
    examples.append(
        make_row(
            prompt,
            "ml_application",
            ["model_serving", "prediction_api"],
            ["model_outputs"],
            ["Python", "scikit-learn", "REST API"],
            ["user"],
            ["API_requests"],
            [],
            ["model_extraction"],
        )
    )


# ---------------------------------------------------------
# DATA POISONING
# ---------------------------------------------------------

data_poisoning_prompts = [
    "Build an ML system that continuously retrains itself using user-submitted training data.",
    "Create a recommendation model that automatically adds user feedback to its training dataset.",
    "Build a machine learning pipeline that retrains from publicly submitted datasets.",
    "Create an AI system where users can directly contribute examples to the training data.",
    "Build a classifier that automatically retrains using data uploaded by customers.",
    "Create an ML pipeline that accepts external data and periodically retrains the model.",
    "Build an AI model that learns continuously from unverified user feedback.",
    "Create a prediction system that adds user-provided labels directly to its training dataset.",
    "Build a recommendation engine that automatically learns from unrestricted user submissions.",
    "Create a machine learning application that retrains on externally supplied datasets.",
    "Build an AI system that incorporates customer-generated examples into future training.",
    "Create an ML service that automatically updates its training set from user input.",
    "Build a model that continuously retrains using data collected from public submissions.",
    "Create an AI application where users can upload examples used for future training.",
    "Build a machine learning pipeline that accepts training data from unknown sources.",
    "Create an ML system that automatically incorporates external datasets.",
    "Build an AI service that learns directly from user feedback without dataset review.",
    "Create a recommendation system that continuously retrains from customer behavior data.",
    "Build a model that automatically updates from newly uploaded training examples.",
    "Create an AI pipeline where external users can influence future training data.",
    "Build a machine learning application that accepts unverified training examples.",
    "Create an AI model that retrains whenever users submit new labeled data.",
    "Build a training pipeline that automatically consumes externally provided datasets.",
    "Create an ML system that allows arbitrary users to contribute training samples.",
]


for prompt in data_poisoning_prompts:
    examples.append(
        make_row(
            prompt,
            "ml_application",
            ["continuous_training", "external_training_data"],
            ["user_submitted_data", "training_data"],
            ["Python", "scikit-learn"],
            ["user", "admin"],
            ["training_examples"],
            [],
            ["data_poisoning"],
        )
    )


# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------

new_df = pd.DataFrame(examples)

if not DATASET.exists():
    raise FileNotFoundError(f"Dataset not found: {DATASET}")

existing_df = pd.read_csv(DATASET)

combined = pd.concat([existing_df, new_df], ignore_index=True)

# Remove exact duplicate rows
combined = combined.drop_duplicates(subset=["prompt"])

combined.to_csv(DATASET, index=False)

print("Existing rows:", len(existing_df))
print("New rows:", len(new_df))
print("Final rows:", len(combined))

print("\nUpdated risk counts:")
labels = [
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
    "ai_tool_risk",
]

print(combined[labels].sum().sort_values(ascending=False))

print("\nApplication types:")
print(combined["application_type"].value_counts())

print(f"\nSaved to: {DATASET}")