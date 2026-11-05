#!/usr/bin/env python3
"""
PromptShield AI — Prompt Complexity Scoring Model Training Pipeline.
===================================================================
Trains a local multi-class classifier to assess prompt complexity across 4 tiers:
- simple: Basic syntax questions, single-turn lookups, elementary explanations
- moderate: Single-file scripts, standard CRUD APIs, basic data analysis
- complex: Multi-service systems, concurrency, security audits, database schemas
- extreme: Distributed consensus, lock-free memory, multi-agent frameworks, formal proofs

Saves to:
- artifacts/complexity_model/model.pkl
- artifacts/complexity_model/metadata.json
- artifacts/complexity_model/metrics.json
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


COMPLEXITY_DATASET: List[Tuple[str, str]] = [
    # 1. SIMPLE
    ("How do I check the length of a string in Python?", "simple"),
    ("What does the HTTP 404 status code mean?", "simple"),
    ("Write a one-line bash command to list all files in reverse chronological order.", "simple"),
    ("How do I convert an integer to a float in JavaScript?", "simple"),
    ("Explain the difference between let and const in ES6 in two sentences.", "simple"),
    ("What is the syntax for a for-loop in Go?", "simple"),
    ("How do I exit vim without saving changes?", "simple"),
    ("What does git pull do?", "simple"),
    ("Write a basic Python print statement saying Hello World.", "simple"),
    ("How do I comment out a block of code in HTML?", "simple"),
    ("What is the default port for PostgreSQL?", "simple"),
    ("How do I add an element to an array in Ruby?", "simple"),
    ("Explain what a boolean variable is in programming.", "simple"),
    ("What command shows the current working directory in Linux terminal?", "simple"),
    ("How do I find the maximum number in a list in Python using built-in functions?", "simple"),
    ("What is JSON and what does the acronym stand for?", "simple"),
    ("How do I format a date string as YYYY-MM-DD in Python?", "simple"),
    ("What is the difference between null and undefined in JavaScript?", "simple"),
    ("How do I reverse a string in Python using slicing?", "simple"),
    ("What does SQL SELECT * FROM users do?", "simple"),

    # 2. MODERATE
    ("Write a Python function to sort a list of dictionaries by a specific key with error handling.", "moderate"),
    ("Create a FastAPI endpoint that accepts user signup JSON and validates email format with Pydantic.", "moderate"),
    ("Write a React functional component for an accordion FAQ with expand and collapse state.", "moderate"),
    ("How do I calculate a 7-day rolling average in pandas on a sales dataframe with timestamps?", "moderate"),
    ("Write a Python script to parse a CSV file, filter rows where age > 30, and write to JSON.", "moderate"),
    ("Create a Dockerfile for a Node.js Express application with multi-stage build.", "moderate"),
    ("Implement binary search in Python to find the index of a target element in an ascending array.", "moderate"),
    ("Write a SQL query using GROUP BY and HAVING to find customers who placed more than 5 orders.", "moderate"),
    ("Build a Flask middleware to log response time and status code for each HTTP request.", "moderate"),
    ("Write a bash script to backup a MySQL database daily and compress it with gzip.", "moderate"),
    ("Create an Express route that handles image file uploads using multer and saves to disk.", "moderate"),
    ("Implement an LRU cache decorator in Python using functools and lru_cache.", "moderate"),
    ("Write a CSS layout for a 3-column pricing card grid using CSS Grid and Flexbox.", "moderate"),
    ("Create a simple CLI in Python using argparse with flags for input file and verbosity.", "moderate"),
    ("Write a unit test suite in pytest for an authentication helper that validates JWT expirations.", "moderate"),
    ("How do I perform exploratory data analysis with seaborn pairplots and missing value imputation?", "moderate"),
    ("Write an async Python function to fetch 5 URLs concurrently using aiohttp with a timeout.", "moderate"),
    ("Create a reusable React custom hook to manage localStorage synchronization.", "moderate"),
    ("Write a MongoDB aggregation pipeline to calculate average revenue per product category.", "moderate"),
    ("Implement a basic stack data structure in C++ with push, pop, and top methods.", "moderate"),

    # 3. COMPLEX
    ("Design a scalable microservices architecture for an e-commerce platform handling 50k RPS with Stripe payments, idempotency keys, and Kafka event streaming.", "complex"),
    ("Perform a comprehensive STRIDE threat modeling analysis and security audit for an OAuth2.0 PKCE authentication flow with refresh token rotation.", "complex"),
    ("Write a high-throughput event processing worker in Python using asyncio, Redis streams, and PostgreSQL with connection pooling and dead-letter queue.", "complex"),
    ("Implement a B-tree indexing engine from scratch in Go with node splitting, merging, and binary disk persistence.", "complex"),
    ("Create an end-to-end CI/CD pipeline using Terraform, AWS ECS Fargate, GitHub Actions, and canary deployments with automated rollback on CloudWatch error alarms.", "complex"),
    ("Audit this smart contract for reentrancy bugs, flash loan attack vectors, and integer overflow edge cases with formal Slither annotations.", "complex"),
    ("Design a distributed caching tier with Redis Cluster, consistent hashing, cache-aside strategy, and cache stampede prevention via probabilistic early expiration.", "complex"),
    ("Build an autonomous agent workflow in Python with tool-calling capabilities, vector memory store retrieval, and human-in-the-loop approval hooks.", "complex"),
    ("Write an SQL migration script for a zero-downtime database schema refactor splitting a 20-million row monolith table into partitioned tables.", "complex"),
    ("Implement a Raft distributed consensus state machine in Rust with leader election, log replication, and heartbeats.", "complex"),
    ("Build a secure multi-tenant SaaS authorization system with granular RBAC and ABAC using Open Policy Agent (OPA) and Casbin.", "complex"),
    ("Analyze a packet capture file and detect sophisticated DNS covert channels, domain fronting, and TLS fingerprint evasion techniques.", "complex"),
    ("Design a real-time collaborative document editor with Operational Transformation (OT) or CRDT algorithms over WebSockets.", "complex"),
    ("Implement a custom Kubernetes operator in Go with custom resource definitions (CRDs), reconciler loops, and leader election across pods.", "complex"),
    ("Build an ETL data lakehouse pipeline processing 500GB daily streaming logs with Apache Spark, Delta Lake, and automated schema evolution.", "complex"),
    ("Design a distributed job scheduling engine with DAG dependency resolution, retry budgets, and worker failure detection.", "complex"),
    ("Develop a comprehensive IAM policy analyzer detecting privilege escalation paths across AWS IAM roles and policies.", "complex"),
    ("Create a full-stack real-time trading simulator with WebSockets, order matching engine, and Redis cache.", "complex"),
    ("Implement two-phase locking and deadlock detection graph algorithms for a relational database storage engine.", "complex"),
    ("Build a federated GraphQL gateway aggregating 6 microservices with distributed tracing and rate limiting.", "complex"),

    # 4. EXTREME
    ("Architect a fault-tolerant, globally distributed Byzantine Fault Tolerant (BFT) consensus protocol with formal TLA+ specifications, cross-shard atomic commit, and zero-knowledge proof state compression.", "extreme"),
    ("Develop a lock-free, wait-free multi-producer multi-consumer ring buffer in C++23 with memory ordering semantics (acquire-release fences) for ultra-low-latency financial trading.", "extreme"),
    ("Formally verify a kernel-level eBPF security sandbox using Coq or Isabelle, proving memory safety and non-interference against kernel privilege escalation exploits.", "extreme"),
    ("Design an autonomous multi-agent distributed operating system runtime with asynchronous message actors, capability-based security tokens, and verifiable multi-party computation.", "extreme"),
    ("Reverse engineer and develop an automated exploit payload chain combining kernel heap Feng Shui, ROP gadget synthesizers, and hypervisor escape mitigations for x86_64 virtualization.", "extreme"),
    ("Synthesize a custom optimizing compiler backend with SSA intermediate representation, polyhedral loop transformation, and LLVM machine code generation for sparse tensor accelerators.", "extreme"),
    ("Implement a zero-knowledge succinct non-interactive argument of knowledge (zk-SNARK) circuit compiler with Plonk proof systems and elliptic curve pairing cryptography.", "extreme"),
    ("Architect a planetary-scale distributed database engine with spanner-like TrueTime API, Paxos replication groups, multi-version concurrency control (MVCC), and distributed deadlock detection.", "extreme"),
    ("Formally verify cryptographic zero-knowledge rollups with polynomial commitment schemes and Halo2 recursive SNARKs.", "extreme"),
    ("Design a bare-metal hypervisor in Rust for ARM64 with stage-2 address translation, secure monitor calls, and formal isolation proofs.", "extreme"),
    ("Develop an automated binary symbolic execution and SMT constraint solver engine to synthesize zero-day remote code execution exploits.", "extreme"),
    ("Build a distributed hardware transactional memory simulator with cache coherence protocols (MESI/MOESI) and cache line invalidation models.", "extreme"),
    ("Synthesize an asynchronous actor runtime with linearizability checking and verified model-checked safety invariants.", "extreme"),
    ("Implement an end-to-end quantum circuit simulator with density matrix decoherence models and Clifford+T gate synthesis.", "extreme"),
    ("Architect a verifiable decentralized computing protocol with trusted execution environment (TEE) attestation and homomorphic encryption.", "extreme"),
    ("Develop a real-time kernel memory allocator with deterministic O(1) latency, zero fragmentation bounds, and hardware isolation.", "extreme"),
    ("Build an autonomous multi-agent swarming framework with formal game-theoretic Nash equilibrium coordination under adversarial network partitions.", "extreme"),
    ("Design a formal verification engine for smart contracts using abstract interpretation and Horn clause constraint solvers.", "extreme"),
    ("Implement a low-level JIT compiler for WebAssembly targeting RISC-V with register allocation via graph coloring.", "extreme"),
    ("Architect a quantum-resistant lattice-based cryptographic key exchange protocol with side-channel timing attack resilience.", "extreme")
]


def train_complexity_model(
    artifact_model_path: Path,
    artifact_metadata_path: Path,
    artifact_metrics_path: Path,
    test_size: float = 0.20,
    random_state: int = 42
) -> Dict:
    """
    Trains and evaluates the Prompt Complexity Scoring Model.
    """
    print("=" * 70)
    print("PROMPTSHIELD AI — PROMPT COMPLEXITY MODEL TRAINING PIPELINE")
    print("=" * 70)

    df = pd.DataFrame(COMPLEXITY_DATASET, columns=["prompt", "complexity_tier"])
    print(f"Total labeled complexity samples: {len(df)}")
    print("\nTier Distribution:")
    for tier, count in df["complexity_tier"].value_counts().items():
        print(f"  {tier:<15}: {count} ({count/len(df)*100:.1f}%)")

    X = df["prompt"]
    y = df["complexity_tier"]

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
                max_features=4000,
                sublinear_tf=True
            )
        ),
        (
            "classifier",
            LogisticRegression(
                solver="liblinear",
                C=2.0,
                class_weight="balanced",
                random_state=random_state
            )
        )
    ])

    print("\nTraining complexity classification pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluate on Test Set
    y_pred = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS (HELD-OUT TEST SET)")
    print("=" * 70)
    print(f"Accuracy:    {accuracy * 100:.2f}%")
    print(f"Weighted F1: {weighted_f1 * 100:.2f}%")
    print(f"Macro F1:    {macro_f1 * 100:.2f}%")

    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Build Model Artifact
    classes = list(pipeline.named_steps["classifier"].classes_)
    tier_order = {"simple": 1, "moderate": 2, "complex": 3, "extreme": 4}

    artifact = {
        "model_name": "PromptShield Complexity Model",
        "pipeline": pipeline,
        "classes": classes,
        "tier_order": tier_order,
        "metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        }
    }

    # Save artifact
    artifact_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_model_path)
    joblib.dump(artifact, artifact_model_path.parent / "complexity_model.pkl")
    print(f"\nModel artifact saved to: {artifact_model_path.resolve()}")

    # Save metadata
    metadata = {
        "model_name": "PromptShield Complexity Scoring Model",
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": "TfidfVectorizer + Balanced Logistic Regression",
        "tiers": ["simple", "moderate", "complex", "extreme"],
        "tier_descriptions": {
            "simple": "Basic syntax lookups, elementary questions, single-turn prompts",
            "moderate": "Standard CRUD APIs, single-file scripts, basic data analysis",
            "complex": "Multi-component architectures, concurrency, security audits",
            "extreme": "Distributed consensus, formal verification, low-level concurrency"
        },
        "performance": {
            "test_accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4)
        }
    }

    with open(artifact_metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    # Save metrics
    metrics_data = {
        "model_name": "PromptShield Complexity Model",
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "overall_metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        },
        "per_class_metrics": report_dict
    }

    with open(artifact_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    return metrics_data


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    artifact_m = repo_root / "artifacts" / "complexity_model" / "model.pkl"
    artifact_meta = repo_root / "artifacts" / "complexity_model" / "metadata.json"
    artifact_met = repo_root / "artifacts" / "complexity_model" / "metrics.json"

    train_complexity_model(artifact_m, artifact_meta, artifact_met)
