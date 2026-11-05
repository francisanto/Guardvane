# PromptShield AI Security Risk Labeling Policy

## General Rule

A risk label is 1 when the prompt creates a meaningful potential
attack surface for that risk and does not sufficiently specify
appropriate security controls.

A risk label is 0 when the prompt does not provide meaningful
evidence for that risk.

The labels represent potential security risks, not confirmed
vulnerabilities.

---

## SQL Injection

Label 1 when:
- The application accepts user-controlled input that is used in
  database queries.
- The prompt describes dynamic SQL/database query construction.
- User input is directly associated with database lookup/filtering.

Label 0 when:
- A database is merely mentioned.
- PostgreSQL/MySQL/etc. is mentioned without a relevant input/query
  attack surface.

---

## XSS

Label 1 when:
- User-controlled content is displayed in a web page.
- The application stores and renders user-generated content.
- The prompt explicitly involves HTML/JavaScript rendering from
  untrusted input.

Label 0 when:
- A web application exists but there is no meaningful
  user-controlled content rendering.

---

## SSRF

Label 1 when:
- The server fetches a URL supplied by a user.
- The application retrieves external resources based on user input.

Label 0 when:
- URLs are mentioned but the server does not fetch them.

---

## IDOR

Label 1 when:
- Users access objects/resources using IDs or similar identifiers.
- The prompt involves user-specific resources where object-level
  authorization is important.

Label 0 when:
- There is no meaningful object/resource access scenario.

---

## Authentication Weakness

Label 1 when:
- The application implements login, registration, password reset,
  authentication, sessions, or credential handling.

Label 0 when:
- Authentication is not part of the requested application.

---

## Authorization Weakness

Label 1 when:
- Multiple roles/users have different permissions.
- Admin/user privileges are explicitly involved.
- Users can manage resources belonging to other users.

Label 0 when:
- Authentication exists but there is no meaningful authorization
  or role-based access requirement.

---

## Unrestricted File Upload

Label 1 when:
- Users can upload files.
- The prompt does not specify meaningful file validation,
  type restrictions, size limits, or safe storage.

Label 0 when:
- There is no file upload functionality.
- Strong upload restrictions are explicitly specified.

---

## Path Traversal

Label 1 when:
- User-controlled filenames or paths are used to access server files.
- Uploaded files or requested files are accessed using user-controlled
  paths.

Label 0 when:
- File upload exists but there is no meaningful path/file-system
  access scenario.

---

## Command Injection

Label 1 when:
- User-controlled input is passed to operating-system commands.
- The application executes shell/terminal/system commands using
  external input.

Label 0 when:
- Commands are not dynamically influenced by untrusted input.

---

## CSRF

Label 1 when:
- A browser-based application performs authenticated state-changing
  actions based on user requests.
- The prompt describes operations such as changing profile data,
  passwords, payments, orders, etc.

Label 0 when:
- There is no meaningful authenticated state-changing web action.

---

## Sensitive Data Exposure

Label 1 when:
- The application handles passwords, medical records, financial data,
  personal information, private logs, API keys, secrets, or similarly
  sensitive information.

Label 0 when:
- No meaningful sensitive data is involved.

---

## Prompt Injection

Label 1 when:
- An AI system processes untrusted instructions from user input,
  documents, emails, web pages, search results, source files, etc.
- The AI is expected to follow instructions contained in external
  content.

Label 0 when:
- No AI instruction-following from untrusted external content occurs.

---

## Data Poisoning

Label 1 when:
- User-controlled or external data is used for model training,
  retraining, fine-tuning, or updating.

Label 0 when:
- External data is used only for inference and not for training.

---

## Model Extraction

Label 1 when:
- Users can repeatedly query a model/API and obtain predictions
  or outputs that could enable replication of model behavior.
- The application explicitly exposes a trained model through an API.

Label 0 when:
- There is no meaningful externally accessible model inference
  interface.

---

## AI/Agent Tool Risk

Label 1 when:
- An AI agent can execute commands.
- An AI agent can modify files.
- An AI agent can access databases, APIs, cloud resources,
  production systems, or other external tools.
- The AI can perform consequential actions autonomously.

Label 0 when:
- The AI only generates text without meaningful external actions.