#!/usr/bin/env python3
"""
PromptShield AI — Local Task Classification Model Training Pipeline.
===================================================================
Trains a local multi-class classifier to predict task categories for prompts:
- code_generation
- security_analysis
- data_analysis
- creative_and_writing
- reasoning_and_math
- general_instruction

Evaluates on a held-out stratified test set and saves:
- Model artifact: models/task_classifier_model.pkl
- Metrics report: ml/results/task_classifier_metrics.json
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score, accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Curated Labeled Training Corpus Across 6 Task Domains
# ---------------------------------------------------------------------------

TASK_DATASET: List[Tuple[str, str]] = [
    # 1. CODE_GENERATION
    ("Write a Python function to implement quicksort with in-place partitioning and explain its time complexity.", "code_generation"),
    ("Build a REST API endpoint in FastAPI that accepts user registration data and hashes passwords with bcrypt.", "code_generation"),
    ("Create a responsive React component for a multi-step checkout form with form validation using Zod.", "code_generation"),
    ("How do I implement a thread-safe LRU cache in Go using mutexes and doubly linked lists?", "code_generation"),
    ("Write a Rust function to parse command-line arguments and handle errors gracefully.", "code_generation"),
    ("Implement a binary search tree in Java with insert, search, and in-order traversal methods.", "code_generation"),
    ("Refactor this JavaScript async/await function to handle network timeouts and retries with exponential backoff.", "code_generation"),
    ("Write a Dockerfile for a multi-stage Python Flask application running with gunicorn as non-root user.", "code_generation"),
    ("Create a PostgreSQL database schema for an e-commerce platform with products, orders, and customer tables.", "code_generation"),
    ("Debug this C++ memory leak in a custom smart pointer implementation.", "code_generation"),
    ("Write a microservice in Node.js using Express that connects to MongoDB and implements JWT authentication.", "code_generation"),
    ("Build a custom Kubernetes operator in Go to manage custom application CRDs.", "code_generation"),
    ("Write a Python script using asyncio to scrape web pages concurrently with rate limiting.", "code_generation"),
    ("Implement the Dijkstra shortest path algorithm in Python using a priority queue.", "code_generation"),
    ("Create an Angular service for managing WebSocket connections with auto-reconnect.", "code_generation"),
    ("Write a bash script to monitor disk usage and send email alerts if partition exceeds 85%.", "code_generation"),
    ("Implement a trie prefix tree in Python for autocomplete search suggestions.", "code_generation"),
    ("Build an authentication middleware in Django that validates Bearer tokens in incoming headers.", "code_generation"),
    ("Write an SQL query with window functions to find the top 3 highest spending customers per region.", "code_generation"),
    ("Create a GraphQL schema and resolver in Apollo Server for querying user profiles.", "code_generation"),
    ("Write a unit test suite using pytest for a payment gateway integration with mocked HTTP responses.", "code_generation"),
    ("How do I configure CORS headers properly in a FastAPI application for multiple frontend origins?", "code_generation"),
    ("Implement a circular ring buffer in C with lock-free atomic operations.", "code_generation"),
    ("Write a Terraform configuration module to provision an AWS VPC with public and private subnets.", "code_generation"),
    ("Create a GitHub Actions workflow to build, test, and push Docker images to Amazon ECR.", "code_generation"),
    ("Build a real-time chat server using Socket.io and Redis adapter in Node.js.", "code_generation"),
    ("Write a Python script to compress images in a directory using Pillow and preserve metadata.", "code_generation"),
    ("Develop a CLI tool in Python using Click that generates project boilerplates from templates.", "code_generation"),
    ("Implement a red-black tree balancing rotation algorithm in C++.", "code_generation"),
    ("Write a function in Swift to decode JSON API responses into strongly typed Codable structs.", "code_generation"),
    ("Create a Next.js 14 App Router server action for updating user profile settings.", "code_generation"),
    ("Write a recursive descent parser in Python for mathematical expressions with parentheses.", "code_generation"),
    ("Build a rate-limiting middleware in Go using token bucket algorithm with Redis.", "code_generation"),
    ("Implement a Kafka consumer in Python that processes order events and commits offsets batch-wise.", "code_generation"),
    ("Write a CSS layout using Flexbox and Grid that remains fully responsive without media queries.", "code_generation"),
    ("Create a custom React hook for debouncing search input values across fast keystrokes.", "code_generation"),
    ("Write an Ansible playbook to configure Nginx, UFW firewall, and Certbot SSL certificates.", "code_generation"),
    ("Implement a Merkle tree data structure in Python for blockchain transaction verification.", "code_generation"),
    ("Build an API client library in TypeScript with automatic token refresh and request interceptors.", "code_generation"),
    ("Write a Python decorator that logs execution time, memory usage, and function arguments.", "code_generation"),

    # 2. SECURITY_ANALYSIS
    ("Audit this smart contract code for reentrancy vulnerabilities and integer overflows.", "security_analysis"),
    ("Explain how Server-Side Request Forgery (SSRF) works in cloud environments and how to mitigate it.", "security_analysis"),
    ("Analyze this Python Flask application for SQL injection and Insecure Direct Object References (IDOR).", "security_analysis"),
    ("Review this authentication architecture and identify weaknesses in the OAuth2 PKCE implementation.", "security_analysis"),
    ("Perform a threat model analysis using STRIDE for a patient medical records portal.", "security_analysis"),
    ("How can an attacker exploit path traversal vulnerabilities in file download endpoints?", "security_analysis"),
    ("Evaluate the effectiveness of Content Security Policy (CSP) headers against stored XSS attacks.", "security_analysis"),
    ("Identify security risks in this Kubernetes pod manifest regarding privileged containers and hostPath mounts.", "security_analysis"),
    ("Assess whether this password reset flow is vulnerable to race conditions or token enumeration.", "security_analysis"),
    ("Analyze the security posture of an API endpoint that unpacks untrusted zip archives directly to disk.", "security_analysis"),
    ("What are the primary vectors for indirect prompt injection when an LLM reads external customer emails?", "security_analysis"),
    ("Explain the difference between blind SQL injection and error-based SQL injection with detection methods.", "security_analysis"),
    ("Review this JWT verification code and check if the 'none' algorithm or key confusion attacks are possible.", "security_analysis"),
    ("Analyze how Cross-Site Request Forgery (CSRF) can be prevented using SameSite cookies and Anti-CSRF tokens.", "security_analysis"),
    ("Examine this firewall rule set and identify permissive ingress rules exposing internal management ports.", "security_analysis"),
    ("How do timing attacks against string comparison functions compromise cryptographic signature checks?", "security_analysis"),
    ("Audit this GraphQL API configuration for query depth exhaustion and batch query denial-of-service.", "security_analysis"),
    ("Explain the mechanism of prototype pollution in JavaScript applications and how to harden objects.", "security_analysis"),
    ("Assess the security risks of storing API credentials in client-side localStorage versus HttpOnly cookies.", "security_analysis"),
    ("Analyze this network packet capture summary to detect DNS tunneling or covert data exfiltration.", "security_analysis"),
    ("What security controls should be implemented to protect against AI model extraction and inversion attacks?", "security_analysis"),
    ("Explain how memory corruption bugs like buffer overflows and use-after-free lead to arbitrary code execution.", "security_analysis"),
    ("Review this automated build pipeline for software supply chain vulnerabilities and unsigned dependencies.", "security_analysis"),
    ("Evaluate the security impact of exposing Docker daemon socket to containers in CI/CD pipelines.", "security_analysis"),
    ("Explain how jailbreak prompts bypass safety guardrails in conversational language models.", "security_analysis"),
    ("Analyze the risk of LDAP injection in user login forms and describe safe parameterization techniques.", "security_analysis"),
    ("Assess vulnerabilities in SAML 2.0 single sign-on implementations related to XML signature wrapping.", "security_analysis"),
    ("Review this endpoint for XML External Entity (XXE) injection vulnerabilities in XML parsing libraries.", "security_analysis"),
    ("What are the key mitigation strategies for protecting serverless AWS Lambda functions from event injection?", "security_analysis"),
    ("Explain how subresource integrity (SRI) defends against compromised third-party CDN scripts.", "security_analysis"),
    ("Audit this Python deserialization code using pickle for remote code execution vulnerabilities.", "security_analysis"),
    ("Identify security risks when AI coding agents execute shell commands generated from untrusted web searches.", "security_analysis"),
    ("Evaluate this multi-tenant database isolation strategy to prevent cross-tenant data leakage.", "security_analysis"),
    ("Explain how clickjacking attacks work and how X-Frame-Options headers mitigate them.", "security_analysis"),
    ("Analyze this AWS IAM policy to detect privilege escalation paths through wildcard permissions.", "security_analysis"),
    ("Review this cryptographic key derivation function for weak salt usage and low iteration counts.", "security_analysis"),
    ("How can an organization detect and defend against credential stuffing attacks on consumer login portals?", "security_analysis"),
    ("Explain how memory-safety vulnerabilities in C libraries can be mitigated using ASLR and DEP/NX.", "security_analysis"),
    ("Analyze this microservice architecture for mutual TLS (mTLS) enforcement between internal services.", "security_analysis"),
    ("Assess the vulnerability of this OAuth callback endpoint to authorization code interception.", "security_analysis"),

    # 3. DATA_ANALYSIS
    ("Write a Python script using pandas to calculate rolling 7-day average sales and detect anomaly spikes.", "data_analysis"),
    ("How do I perform exploratory data analysis on a customer churn dataset with missing values and skewed distributions?", "data_analysis"),
    ("Explain the difference between PCA and t-SNE for dimensionality reduction on high-dimensional tabular data.", "data_analysis"),
    ("Write a pandas query to merge two large dataframes on customer_id, handle duplicates, and aggregate spend.", "data_analysis"),
    ("Calculate the Pearson and Spearman correlation coefficients between advertising spend and conversion rates.", "data_analysis"),
    ("How do I build an ETL pipeline in PySpark to process partitioned Parquet files from an S3 data lake?", "data_analysis"),
    ("Write a Python script using seaborn to plot a correlation heatmap with annotated p-values.", "data_analysis"),
    ("Explain how to handle extreme class imbalance in credit card fraud detection using SMOTE and downsampling.", "data_analysis"),
    ("Create a time-series forecasting model using ARIMA to predict monthly electricity consumption.", "data_analysis"),
    ("Write an SQL query to calculate customer lifetime value (CLV) and cohort retention rates by signup month.", "data_analysis"),
    ("How do I detect multivariate outliers using Isolation Forest and Mahalanobis distance in scikit-learn?", "data_analysis"),
    ("Explain the statistical assumptions of ordinary least squares (OLS) linear regression and how to test them.", "data_analysis"),
    ("Write a Python script to normalize numerical features using RobustScaler and encode categorical variables.", "data_analysis"),
    ("How do I conduct an A/B test sample size calculation and interpret the resulting p-value and statistical power?", "data_analysis"),
    ("Analyze this sales dataset to compute customer purchase frequency, recency, and monetary (RFM) segmentation.", "data_analysis"),
    ("Write a Polars query in Python to perform fast grouped aggregations on a 10-million row dataset.", "data_analysis"),
    ("Explain how Kaplan-Meier survival curves estimate time-to-event probabilities in clinical trial data.", "data_analysis"),
    ("Create a dashboard visualization in Matplotlib showing boxplots of employee salaries across departments.", "data_analysis"),
    ("How do I perform text sentiment feature extraction and TF-IDF matrix generation on customer review data?", "data_analysis"),
    ("Write a function to compute precision, recall, ROC-AUC, and F1-score across multiple probability thresholds.", "data_analysis"),
    ("Explain how hierarchical clustering differs from k-means clustering and how to read a dendrogram.", "data_analysis"),
    ("Write an SQL query using CTEs to calculate cumulative revenue day-over-day across different product categories.", "data_analysis"),
    ("How do I impute missing numerical data using k-nearest neighbors (KNNImputer) in scikit-learn?", "data_analysis"),
    ("Explain how cross-validation with stratification prevents data leakage during hyperparameter tuning.", "data_analysis"),
    ("Write a pandas script to reshape data from wide format to long format using melt and pivot_table.", "data_analysis"),
    ("How do I measure feature importance in a Random Forest regressor using permutation importance?", "data_analysis"),
    ("Explain the central limit theorem and its practical application in hypothesis testing with non-normal data.", "data_analysis"),
    ("Write a Python script to calculate customer churn rates on a subscription dataset with monthly billing cycles.", "data_analysis"),
    ("How do I analyze web analytics clickstream data to identify drop-off funnels in a checkout process?", "data_analysis"),
    ("Write an SQL script to detect duplicate transactions occurring within a 5-minute sliding window.", "data_analysis"),
    ("Explain the difference between Type I and Type II errors in medical diagnostic testing.", "data_analysis"),
    ("Write a Python function to compute Gini impurity and information gain for decision tree splitting.", "data_analysis"),
    ("How do I perform seasonal decomposition on time series data using statsmodels to isolate trend and noise?", "data_analysis"),
    ("Create a data pipeline that validates CSV schema and data quality rules using Great Expectations.", "data_analysis"),
    ("Explain how log transformations stabilize variance and make right-skewed distributions approximately normal.", "data_analysis"),
    ("Write a Python script using pandas to parse dates, set datetime index, and resample hourly metrics to daily averages.", "data_analysis"),
    ("How do I calculate the variance inflation factor (VIF) to detect multicollinearity among regression features?", "data_analysis"),
    ("Explain how naive Bayes classifiers apply Bayes' theorem with conditional independence assumptions.", "data_analysis"),
    ("Write a pandas pipeline to remove whitespace, drop duplicates, and impute categorical nulls with mode.", "data_analysis"),
    ("How do I interpret SHAP values to explain global and local predictions of a gradient boosting model?", "data_analysis"),

    # 4. CREATIVE_AND_WRITING
    ("Write a compelling short story about an astronaut who discovers an abandoned alien library on Mars.", "creative_and_writing"),
    ("Draft an engaging marketing email introducing a new eco-friendly outdoor clothing collection.", "creative_and_writing"),
    ("Compose a descriptive poem about the transition from autumn to winter in a northern mountain village.", "creative_and_writing"),
    ("Write a dramatic dialogue between a time traveler and their younger self who refuses to change the future.", "creative_and_writing"),
    ("Create a narrative backstory for a fantasy tabletop RPG character who is an exiled elven cartographer.", "creative_and_writing"),
    ("Draft a persuasive opinion editorial arguing for increased funding for public libraries in rural towns.", "creative_and_writing"),
    ("Write a humorous monologue from the perspective of an office coffee machine observing employees.", "creative_and_writing"),
    ("Compose a mystery scene where a detective discovers an unusual clue in an antique clock shop.", "creative_and_writing"),
    ("Draft a brand mission statement and core values for a sustainable architecture studio.", "creative_and_writing"),
    ("Write a fictional interview between a journalist and the first sentient deep-sea exploration submersible.", "creative_and_writing"),
    ("Create a vivid descriptive passage depicting a bustling street market in Victorian London during twilight.", "creative_and_writing"),
    ("Draft a motivational keynote speech for graduating university students entering uncertain job markets.", "creative_and_writing"),
    ("Write a speculative fiction opening chapter about a society where memories can be traded as currency.", "creative_and_writing"),
    ("Compose a haiku sequence celebrating the four seasons in a Zen garden.", "creative_and_writing"),
    ("Draft an engaging press release announcing a non-profit organization's global clean water initiative.", "creative_and_writing"),
    ("Write a children's bedtime story about an owl who is afraid of the dark and learns to love the stars.", "creative_and_writing"),
    ("Create a tense negotiation dialogue between two rival space captains over salvage rights to an asteroid.", "creative_and_writing"),
    ("Draft an evocative restaurant review capturing the atmosphere, culinary flavors, and service of a seaside bistro.", "creative_and_writing"),
    ("Write a philosophical monologue exploring what it means to be remembered after one is gone.", "creative_and_writing"),
    ("Compose a creative pitch for a television series about an archivist who discovers real magic in historical documents.", "creative_and_writing"),
    ("Draft a thoughtful eulogy celebrating the lifelong kindness and artistic spirit of a beloved mentor.", "creative_and_writing"),
    ("Write a cyberpunk story snippet describing a neon-drenched alley market where cybernetic limbs are repaired.", "creative_and_writing"),
    ("Create engaging product copy for an artisanal loose-leaf tea blend sourced from high-altitude Himalayan estates.", "creative_and_writing"),
    ("Draft an apology letter from an airline customer care team resolving a serious travel disruption with empathy.", "creative_and_writing"),
    ("Write a character sketch of an elderly lighthouse keeper who speaks only in maritime idioms.", "creative_and_writing"),
    ("Compose a whimsical fable explaining why cats always land on their feet and gaze at invisible corners.", "creative_and_writing"),
    ("Draft an inspiring manifesto for a community garden collective fostering urban biodiversity.", "creative_and_writing"),
    ("Write a suspenseful thriller opening where a protagonist wakes up with amnesia in a locked cabin.", "creative_and_writing"),
    ("Create a poetic monologue delivered by the moon reflecting upon centuries of human history beneath it.", "creative_and_writing"),
    ("Draft a creative social media campaign copy celebrating World Oceans Day for a marine conservation trust.", "creative_and_writing"),
    ("Write an imaginative dialogue between an ancient tree and a newly planted sapling in an urban park.", "creative_and_writing"),
    ("Compose a gothic horror scene exploring an abandoned conservatory overgrown with poisonous midnight blossoms.", "creative_and_writing"),
    ("Draft a warm and witty wedding toast celebrating two childhood sweethearts who reconnected as adults.", "creative_and_writing"),
    ("Write an epic fantasy battle speech given by a commander before defending a mountain fortress.", "creative_and_writing"),
    ("Create a nostalgic narrative essay recounting summers spent at a grandparents' rural lakehouse.", "creative_and_writing"),
    ("Draft a compelling travel article describing an autumn walking tour through the historic streets of Kyoto.", "creative_and_writing"),
    ("Write a comic scene where two medieval knights debate the ergonomics of modern office furniture.", "creative_and_writing"),
    ("Compose a sonnet about the quiet solitude of working in a research greenhouse during a thunderstorm.", "creative_and_writing"),
    ("Draft a visionary founder's letter to early adopters explaining the philosophy behind an open knowledge platform.", "creative_and_writing"),
    ("Write a poignant flash fiction piece about an astronaut looking at Earth through an orbital cupola window.", "creative_and_writing"),

    # 5. REASONING_AND_MATH
    ("Prove that the square root of 2 is an irrational number using a proof by contradiction.", "reasoning_and_math"),
    ("Solve this system of linear equations using Gaussian elimination with step-by-step matrix steps.", "reasoning_and_math"),
    ("Calculate the eigenvalues and eigenvectors of this 2x2 matrix [[4, 1], [2, 3]].", "reasoning_and_math"),
    ("If three fair dice are rolled simultaneously, what is the exact probability of getting a sum of exactly 10?", "reasoning_and_math"),
    ("Explain the proof of Fermat's Little Theorem and demonstrate its application in modular exponentiation.", "reasoning_and_math"),
    ("Solve the definite integral of x * e^(2x) dx from 0 to 1 using integration by parts.", "reasoning_and_math"),
    ("Determine whether the infinite series sum from n=1 to infinity of 1 / (n^2 + 3n) converges, and find its sum.", "reasoning_and_math"),
    ("Explain the principle of mathematical induction and use it to prove that 1 + 2 + ... + n = n(n+1)/2.", "reasoning_and_math"),
    ("Solve this logic riddle: Three gods A, B, and C are called True, False, and Random...", "reasoning_and_math"),
    ("Find the maximum and minimum values of f(x, y) = x^2 + y^2 subject to the constraint x + 2y = 10 using Lagrange multipliers.", "reasoning_and_math"),
    ("Explain the difference between countably infinite sets and uncountably infinite sets with Cantor's diagonal argument.", "reasoning_and_math"),
    ("Derive the Bayes theorem formula from the definition of conditional probability step-by-step.", "reasoning_and_math"),
    ("Solve the first-order differential equation dy/dx + 2y = e^(-x) with initial condition y(0) = 1.", "reasoning_and_math"),
    ("In a group of 23 people, what is the exact probability that at least two people share the same birthday?", "reasoning_and_math"),
    ("Prove that if a prime p divides ab, then p divides a or p divides b (Euclid's Lemma).", "reasoning_and_math"),
    ("Calculate the limit as x approaches 0 of (sin(x) - x) / x^3 using L'Hopital's rule.", "reasoning_and_math"),
    ("Explain how the Monty Hall problem is resolved using conditional probability tables.", "reasoning_and_math"),
    ("Find the volume of the solid generated by revolving the region bounded by y = x^2 and y = 4 around the x-axis.", "reasoning_and_math"),
    ("Determine the number of integer solutions to the equation x1 + x2 + x3 + x4 = 20 where each xi >= 1.", "reasoning_and_math"),
    ("Prove that a connected undirected graph has an Eulerian circuit if and only if every vertex has an even degree.", "reasoning_and_math"),
    ("Calculate the determinant of a 3x3 matrix using cofactor expansion along the first row.", "reasoning_and_math"),
    ("Explain Gödel's First Incompleteness Theorem and its implications for formal axiomatic systems.", "reasoning_and_math"),
    ("Solve the recurrence relation T(n) = 2T(n/2) + n using the Master Theorem.", "reasoning_and_math"),
    ("Derive the quadratic formula by completing the square on the general equation ax^2 + bx + c = 0.", "reasoning_and_math"),
    ("Find the Taylor series expansion of ln(1 + x) around x = 0 and determine its radius of convergence.", "reasoning_and_math"),
    ("If a bag contains 5 red balls and 7 blue balls, what is the probability of drawing 2 red balls without replacement?", "reasoning_and_math"),
    ("Prove that the set of all real numbers in the interval [0, 1] cannot be put into one-to-one correspondence with natural numbers.", "reasoning_and_math"),
    ("Evaluate the double integral of (x + 2y) dA over the rectangular region R = [0, 2] x [1, 3].", "reasoning_and_math"),
    ("Explain the pigeonhole principle and solve the problem: prove that in any group of 6 people, either 3 are mutual friends or 3 are mutual strangers.", "reasoning_and_math"),
    ("Find the inverse of a 2x2 matrix [[a, b], [c, d]] and state the necessary condition for invertibility.", "reasoning_and_math"),
    ("Calculate the variance and standard deviation of a discrete random variable with given probability mass function.", "reasoning_and_math"),
    ("Prove that in any finite group, the order of a subgroup divides the order of the group (Lagrange's Theorem).", "reasoning_and_math"),
    ("Solve the trigonometric equation 2 * sin^2(x) - 3 * sin(x) + 1 = 0 for x in the interval [0, 2*pi].", "reasoning_and_math"),
    ("Explain how RSA encryption relies on the computational difficulty of factoring large semiprime numbers.", "reasoning_and_math"),
    ("Calculate the surface area of a sphere of radius R by integrating spherical coordinates.", "reasoning_and_math"),
    ("Determine the condition under which a Markov chain has a unique stationary probability distribution.", "reasoning_and_math"),
    ("Evaluate the line integral of F = (y, -x) along the unit circle oriented counterclockwise using Green's Theorem.", "reasoning_and_math"),
    ("Explain the Halting Problem and Turing's proof that no general algorithm can decide program termination.", "reasoning_and_math"),
    ("Find the critical points of f(x, y) = x^3 - 3x + y^2 and classify each as a local minimum, maximum, or saddle point.", "reasoning_and_math"),
    ("Solve the classic river crossing puzzle with a farmer, a fox, a goose, and a bag of grain.", "reasoning_and_math"),

    # 6. GENERAL_INSTRUCTION
    ("Summarize the main arguments of the attached research article in three concise bullet points.", "general_instruction"),
    ("Translate this business email from English into polite, professional French.", "general_instruction"),
    ("Proofread this paragraph for grammatical errors, punctuation, and awkward phrasing.", "general_instruction"),
    ("Format this raw unorganized list of contact details into a clean markdown table.", "general_instruction"),
    ("Explain the difference between renewable and non-renewable energy sources in simple terms.", "general_instruction"),
    ("Draft a polite follow-up email inquiring about the status of a job interview completed last week.", "general_instruction"),
    ("Convert this meeting transcript into five key action items with assigned owners and deadlines.", "general_instruction"),
    ("What are the main causes and historical consequences of the Industrial Revolution in Europe?", "general_instruction"),
    ("Rephrase this technical explanation so that a non-technical stakeholder can understand the trade-offs.", "general_instruction"),
    ("Create a 5-day travel itinerary for a family visiting London with young children.", "general_instruction"),
    ("Summarize the differences between copyright, trademark, and patent intellectual property protections.", "general_instruction"),
    ("Translate this product instruction manual snippet into neutral Latin American Spanish.", "general_instruction"),
    ("Extract the dates, locations, and attendee names from this conference memo into JSON format.", "general_instruction"),
    ("Provide a step-by-step checklist for preparing a home for severe winter weather conditions.", "general_instruction"),
    ("Draft a clear and constructive peer review feedback message for an academic journal submission.", "general_instruction"),
    ("Explain how photosynthesis converts sunlight, water, and carbon dioxide into glucose and oxygen.", "general_instruction"),
    ("Rewrite this customer complaint response in a warm, empathetic, and solution-focused tone.", "general_instruction"),
    ("What are the standard health guidelines for daily water intake and hydration?", "general_instruction"),
    ("Format this bibliography list according to APA 7th edition citation style guidelines.", "general_instruction"),
    ("Summarize the key events that led to the signing of the Magna Carta in 1215.", "general_instruction"),
    ("Translate this greeting and basic customer support menu into professional German.", "general_instruction"),
    ("Create an onboarding checklist for a new software engineer joining a remote engineering team.", "general_instruction"),
    ("Explain how vaccines stimulate the human immune system to produce antibodies without causing illness.", "general_instruction"),
    ("Draft an agenda for a 45-minute quarterly team retrospective meeting with icebreakers.", "general_instruction"),
    ("Proofread this resume summary section to make the bullet points more impactful with strong action verbs.", "general_instruction"),
    ("What is the difference between weather and climate according to atmospheric science?", "general_instruction"),
    ("Summarize the plot and central themes of George Orwell's novel 1984.", "general_instruction"),
    ("Translate this restaurant menu description into standard Italian for tourist menus.", "general_instruction"),
    ("Create a weekly meal prep plan with a consolidated grocery shopping list for a vegetarian diet.", "general_instruction"),
    ("Explain the primary functions of the three branches of the United States federal government.", "general_instruction"),
    ("Draft an out-of-office automated email response specifying return dates and emergency contact details.", "general_instruction"),
    ("Provide five practical tips for improving sleep hygiene and establishing a consistent bedtime routine.", "general_instruction"),
    ("Format these meeting notes into structured headings: Objectives, Discussion, Decisions, Next Steps.", "general_instruction"),
    ("Explain the water cycle steps: evaporation, condensation, precipitation, and collection.", "general_instruction"),
    ("Translate this brief technical disclaimer into Japanese for software documentation.", "general_instruction"),
    ("Draft an invitation message for a neighborhood community clean-up day with date and equipment info.", "general_instruction"),
    ("Summarize the economic concept of supply and demand and how equilibrium price is determined.", "general_instruction"),
    ("Reorganize this messy brainstorming list into three prioritized thematic categories.", "general_instruction"),
    ("Explain the difference between aerobic and anaerobic exercise and their respective cardiovascular benefits.", "general_instruction"),
    ("Provide a checklist of essential items to pack for an international hiking trip in mountainous terrain.", "general_instruction")
]


def train_task_classifier(
    model_output_path: Path,
    metrics_output_path: Path,
    test_size: float = 0.20,
    random_state: int = 42
) -> Dict:
    """
    Trains and evaluates the local Task Classification Model.
    """
    print("=" * 70)
    print("PROMPTSHIELD AI — LOCAL TASK CLASSIFICATION MODEL TRAINING")
    print("=" * 70)

    df = pd.DataFrame(TASK_DATASET, columns=["prompt", "task_category"])
    print(f"Total labeled prompts: {len(df)}")
    print("\nClass Distribution:")
    for cat, count in df["task_category"].value_counts().items():
        print(f"  {cat:<25}: {count} ({count/len(df)*100:.1f}%)")

    X = df["prompt"]
    y = df["task_category"]

    # Stratified Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state
    )

    print(f"\nTrain Split: {len(X_train)} samples")
    print(f"Test Split:  {len(X_test)} samples (held-out)")

    # Build Pipeline: TF-IDF + Logistic Regression
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=6000,
                sublinear_tf=True
            )
        ),
        (
            "classifier",
            LogisticRegression(
                solver="liblinear",
                C=1.5,
                class_weight="balanced",
                random_state=random_state
            )
        )
    ])

    print("\nTraining local task classification pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluate on Held-Out Test Set
    y_pred = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS (HELD-OUT TEST SET)")
    print("=" * 70)
    print(f"Accuracy:    {accuracy * 100:.2f}%")
    print(f"Weighted F1: {weighted_f1 * 100:.2f}%")
    print(f"Macro F1:    {macro_f1 * 100:.2f}%")

    report_dict = classification_report(y_test, y_pred, output_dict=True)
    print("\nPer-Class Classification Report:")
    for cls_name in sorted(df["task_category"].unique()):
        cls_metrics = report_dict.get(cls_name, {})
        p = cls_metrics.get("precision", 0) * 100
        r = cls_metrics.get("recall", 0) * 100
        f = cls_metrics.get("f1-score", 0) * 100
        s = cls_metrics.get("support", 0)
        print(f"  {cls_name:<25} | P: {p:5.1f}% | R: {r:5.1f}% | F1: {f:5.1f}% | N={s}")

    # Build Artifacts
    classes = list(pipeline.named_steps["classifier"].classes_)
    artifact = {
        "model_name": "Local Task Classification Model",
        "pipeline": pipeline,
        "classes": classes,
        "metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        }
    }

    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_output_path)
    print(f"\nModel artifact saved to: {model_output_path.resolve()}")

    # Save Metrics JSON
    metrics_data = {
        "model_name": "Local Task Classification Model",
        "evaluation_timestamp": pd.Timestamp.now().isoformat(),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "overall_metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        },
        "per_class_metrics": {
            k: {sub_k: round(v, 4) if isinstance(v, float) else v for sub_k, v in val.items()}
            if isinstance(val, dict) else round(val, 4)
            for k, val in report_dict.items()
        }
    }

    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_output_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Metrics saved to:        {metrics_output_path.resolve()}")

    return metrics_data


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    model_path = repo_root / "models" / "task_classifier_model.pkl"
    metrics_path = repo_root / "ml" / "results" / "task_classifier_metrics.json"

    train_task_classifier(model_path, metrics_path)
