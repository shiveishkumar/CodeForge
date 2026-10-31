# CodeForge – Tamper-Evident Query Auditing Layer

## 1. Project Overview

CodeForge is a database security project that implements a tamper-evident auditing layer for relational database applications.

The system records database operations, generates cryptographic hashes, organizes audit events into Merkle batches, and maintains chained root checkpoints. It verifies the integrity of audit records and checks whether the current business database state matches the authenticated audit history.

The application demonstrates these concepts through banking and inventory management modules.

## 2. Project Objectives

- Maintain a verifiable history of database operations.
- Detect unauthorized modification or deletion of audit records.
- Use SHA-256 hashing and hash chaining to protect audit history.
- Group audit events using Merkle trees.
- Maintain chained Merkle root checkpoints.
- Verify current business records against authenticated audit history.
- Demonstrate authentication and role-based access control.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Backend Framework | Flask |
| Database | PostgreSQL |
| Database Integration | SQLAlchemy ORM and SQL |
| Database Management | pgAdmin |
| Cryptographic Hashing | SHA-256 |
| Integrity Structure | Hash Chain and Merkle Tree |
| Frontend | HTML, CSS, JavaScript |
| Version Control | Git and GitHub |

## 4. Main Application Modules

### Banking
- Account management
- Deposits
- Withdrawals
- Fund transfers

### Inventory
- Add products
- Update product quantities and prices
- Delete products
- Record inventory changes in the audit history

### Audit and Integrity Verification
- Record authenticated database changes.
- Generate cryptographic hashes.
- Organize events into Merkle batches.
- Maintain chained root checkpoints.
- Verify audit history and current database state.
- Detect tampering and report integrity failures.

### Authentication
- Admin and Staff login.
- Session-based authentication.
- Role-based access restrictions.

## 5. System Architecture

The application follows this general processing flow:

1. A user logs into the application.
2. The user performs a banking or inventory operation.
3. The backend processes the business operation.
4. The corresponding database change is recorded in the audit history.
5. Audit events are linked using SHA-256 hash chaining.
6. Events are grouped into Merkle batches.
7. Merkle roots are chained and stored as checkpoints.
8. The verification module checks audit integrity and current business data.

## 6. Installation and Setup

### Prerequisites

- Python 3.10 or later
- PostgreSQL
- pgAdmin (recommended)
- Git

### Clone the Repository

```bash
git clone https://github.com/shiveishkumar/CodeForge.git
cd CodeForge
```

### Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Database Configuration

1. Open PostgreSQL using pgAdmin.
2. Create the database named `codeforge_db`.
3. Configure the database connection using the application's environment configuration.
4. Add the required database credentials and secret values to your local environment file.
5. Initialize the database using the project's supported setup procedure.

Do not upload database passwords, secret keys, or `.env` files to GitHub.

## 7. Running the Application

After completing the database configuration and installing the dependencies, run:

```bash
python app.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

Use the configured application login credentials to access the dashboard.

## 8. Repository Structure

The project includes the following major components:

- `app.py` – Flask application and application routes.
- `services.py` – Business operations and application services.
- `audit.py` – Audit event processing and cryptographic audit logic.
- `merkle.py` – Merkle tree and root generation.
- `verifier.py` – Audit integrity verification.
- `checkpoint.py` – Checkpoint management.
- `templates/` – HTML application pages.
- `static/` – Frontend styles and scripts.
- `requirements.txt` – Python dependencies.
- `checkpoint.json` – Latest chained-root checkpoint.

The actual repository may contain additional modules and supporting files.

## 9. Team Members

| Name | Registration Number |
|---|---|
| Shiveish Kumar | 23BDS0285 |
| Bhavyendra Manish | 23BAI0176 |

**Team Name:** CodeForge

**Institution:** Vellore Institute of Technology (VIT)

**School:** School of Computer Science and Engineering (SCOPE)

## 10. Project Repository

GitHub: https://github.com/shiveishkumar/CodeForge

## 11. Limitations

- The application is currently intended as an academic demonstration.
- The vulnerable demonstration functionality is intended for local testing only.
- Integrity verification depends on the availability and protection of audit records and checkpoint information.
- The project has not been presented as a production-certified banking security system.

## 12. Conclusion

CodeForge demonstrates how cryptographic hash chaining, Merkle trees, and checkpoint verification can be integrated with a relational database application to provide tamper-evident query auditing.

The project combines practical banking and inventory operations with database integrity verification to demonstrate the detection of unauthorized changes.
