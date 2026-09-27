# Incident Management & Alerting Architecture

**E-Way Bill Data Reliability & Reconciliation Pipeline**  
**Phase 9 Documentation**  
**Status:** Implemented & Verified (122/122 tests passing)

---

## 1. Incident Lifecycle

The incident management layer provides an authoritative record of pipeline data-integrity failures, halting the promotion of unverified records into the trusted warehouse while alerting on-call data engineers.

```
+--------------------------------------------------------------------------+
|                       RELIABILITY DECISION GATE                          |
+--------------------------------------------------------------------------+
                                     |
                          [Integrity Failure Detected]
                                     v
+--------------------------------------------------------------------------+
| 1. INCIDENT CREATION & PERSISTENCE (Authoritative)                       |
|    - Evaluates blocking failures (CRITICAL > ERROR > WARNING)            |
|    - Idempotently records incident in PostgreSQL `incidents` table       |
|    - Generates markdown audit artifact: docs/incidents/incident_<run_id>.md |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| 2. EMAIL NOTIFICATION DISPATCH (Secondary Delivery)                      |
|    - Checks idempotency: skips if alert already sent for this run        |
|    - Formats Subject: [EWAYBILL PIPELINE] <SEVERITY> - Run <run_id>       |
|    - Dispatches plaintext & HTML diagnostics via SMTP                    |
|    - Delivery failure is non-fatal to incident persistence               |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
| 3. PIPELINE HALT & AUDIT STATUS                                          |
|    - Updates `pipeline_runs.status = 'FAILED'`                           |
|    - Halts trusted data promotion                                        |
|    - Raises AirflowFailException marking DAG task as failed              |
+--------------------------------------------------------------------------+
                                     |
                          [Investigation & Remediation]
                                     v
+--------------------------------------------------------------------------+
| 4. RESOLUTION WORKFLOW                                                   |
|    - Engineer reviews audit trail and applies source/rule fixes          |
|    - Updates `incidents.status = 'RESOLVED'`                             |
|    - Populates `resolution_timestamp` and `resolution_notes`             |
+--------------------------------------------------------------------------+
```

---

## 2. Incident Schema

The `incidents` table in PostgreSQL (`sql/schema.sql`) models all governance and diagnostic attributes. Non-applicable or unprovided metrics remain `NULL` without synthetic value invention.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `incident_id` | `BIGSERIAL` | `PRIMARY KEY` | Unique serial identifier for the incident |
| `run_id` | `UUID` | `NOT NULL, REFERENCES pipeline_runs(run_id) ON DELETE CASCADE, UNIQUE` | Pipeline execution run ID (primary lineage key) |
| `severity` | `VARCHAR(50)` | `NOT NULL` | Incident severity: `CRITICAL`, `ERROR`, or `WARNING` |
| `status` | `VARCHAR(50)` | `NOT NULL, DEFAULT 'OPEN'` | Lifecycle state: `OPEN`, `ACKNOWLEDGED`, `RESOLVED` |
| `failure_type` | `VARCHAR(100)` | `NOT NULL` | Classification (e.g. `DATA_INTEGRITY_FAILURE`, `SCHEMA_VALIDATION_FAILURE`) |
| `source_table` | `VARCHAR(100)` | `NULLABLE` | Primary affected source worksheet / table |
| `check_id` | `VARCHAR(50)` | `NULLABLE` | Primary failing check identifier (e.g. `SCH-02`, `NUM-01`) |
| `check_name` | `VARCHAR(255)` | `NULLABLE` | Concise descriptive name of the primary failing check |
| `expected_value` | `TEXT` | `NULLABLE` | Expected value or constraint expression (`NULL` if unprovided) |
| `observed_value` | `TEXT` | `NULLABLE` | Observed actual value (`NULL` if unprovided) |
| `difference` | `NUMERIC(24, 12)`| `NULLABLE` | Numeric deviation or gap (`NULL` if non-numeric/unprovided) |
| `affected_record_count` | `INTEGER` | `NOT NULL, DEFAULT 0` | Total affected records across failures |
| `title` | `VARCHAR(255)` | `NOT NULL` | Concise incident summary title |
| `description` | `TEXT` | `NOT NULL` | Diagnostic description and action taken |
| `triggering_failures` | `JSONB` | `NULLABLE` | Complete structured array of all underlying failure objects |
| `detection_timestamp` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Timestamp when failure was detected |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL, DEFAULT NOW()` | Creation timestamp (synced with detection) |
| `resolution_timestamp` | `TIMESTAMPTZ` | `NULLABLE` | Timestamp when marked resolved (`NULL` while OPEN) |
| `resolved_at` | `TIMESTAMPTZ` | `NULLABLE` | Resolution timestamp alias |
| `resolution_notes` | `TEXT` | `NULLABLE` | Remediation description and root-cause analysis notes |
| `alert_sent` | `BOOLEAN` | `NOT NULL, DEFAULT FALSE` | Whether email notification was dispatched |
| `alert_sent_at` | `TIMESTAMPTZ` | `NULLABLE` | Timestamp of email dispatch |

---

## 3. Severity Semantics & Epistemic Boundaries

### Severity Hierarchy
When multiple validation failures occur within a single run, the incident takes the highest severity among all failing checks:
$$\text{CRITICAL} > \text{ERROR} > \text{WARNING}$$

- **CRITICAL:** Fundamental schema violations (missing worksheets, missing required columns, corrupted headers), structural flaws, or duplicate primary keys.
- **ERROR:** Mathematical cross-foot check failures (`REC-V01..08`), out-of-range negative values, non-numeric data types in numeric movement cells.
- **WARNING:** Non-critical data domain deviations or minor advisory issues.

### Strict Governance Boundary (Advisory vs. Blocking)
The system maintains a strict epistemic boundary:
1. **Year-over-Year Statistical Differences:**  
   A finding of `STATISTICALLY_DIFFERENT` (e.g. from a two-sample Kolmogorov-Smirnov test or Population Stability Index) indicates a distributional shift between annual snapshots under test assumptions. It **does NOT** represent data corruption, a pipeline defect, or an economic cause, and **never generates a blocking incident or alert**.
2. **`OTHER TERRITORY` Unresolved Reconciliation:**  
   The `REC-DO06` finding where inward movement contains ₹3,030.56 crore not reflected in outward trade is recorded as an advisory `UNRESOLVED` audit (Severity: `WARNING`). It reflects published source data and **does NOT generate a blocking incident or alert**.
3. **Blocking Incidents Only:**  
   Only hard data-integrity failures (`status == 'FAIL'` and `severity in ('CRITICAL', 'ERROR')`) enter the incident and email alerting workflow.

---

## 4. Aggregation Policy

When a pipeline run fails multiple validation rules:
1. **Single Incident Per Failed Run:**  
   The system does not flood databases or inboxes with separate incidents for each individual failed cell or check. Exactly **one** aggregated incident record is created per execution run.
2. **Primary Metric Extraction:**  
   Top-level diagnostic columns (`source_table`, `check_id`, `check_name`, `expected_value`, `observed_value`, `difference`) are extracted from the highest-severity failure (prioritizing `CRITICAL` over `ERROR`).
3. **Cumulative Metrics:**  
   `affected_record_count` sums the affected records across all underlying failures.
4. **Complete Underlying Lineage:**  
   The `triggering_failures` JSONB column stores the complete list of all failing checks, ensuring forensic visibility into every individual error.

---

## 5. Idempotency Behavior

Airflow tasks may retry due to infrastructure transient errors. The incident creation mechanism is completely idempotent:

1. **Identity Preservation:**  
   Before creating an incident, `IncidentManager.record_incident_in_db` queries:
   ```sql
   SELECT incident_id, alert_sent, detection_timestamp FROM incidents WHERE run_id = %s;
   ```
2. **No Duplicate Records:**  
   If an incident already exists for `run_id`, the existing record is preserved. Its `incident_id` and initial `detection_timestamp` remain immutable. The unique constraint `CONSTRAINT uq_incidents_run_id UNIQUE (run_id)` guarantees database-level integrity.
3. **No Duplicate Alerts:**  
   If `incident.alert_sent == True`, the email notifier logs `SKIPPED_DUPLICATE` and aborts email dispatch, preventing inbox spamming during task retries.

---

## 6. Email Notification Flow

Email notifications are dispatched by `src.notifications.email_service.EmailAlertNotifier`.

### Trigger Rules
- **Dispatched:** ONLY when a blocking data-integrity incident is created.
- **Suppressed:** Successful runs, normal statistical shifts, advisory reconciliation observations, informational validation checks.

### Subject Format
```
[EWAYBILL PIPELINE] <SEVERITY> - Run <run_id>
```
*Example:* `[EWAYBILL PIPELINE] CRITICAL - Run 3f4a9b2c-8d1e-4f5a-9a3b-2c8d1e4f5a9b`

### Body Content
Every notification delivers full failure diagnostics in both Plaintext and HTML formats:
- Pipeline Run ID
- Incident ID
- Severity (`CRITICAL` / `ERROR`)
- Failure Type
- Affected Source Table
- Check ID & Descriptive Name
- Expected Value & Observed Value
- Numerical Difference (if applicable)
- Affected Record Count
- Detection Timestamp
- Action Taken (Trusted promotion halted)
- Tabular breakdown of underlying failures (for multi-failure incidents)

---

## 7. Configuration

All notification parameters are dynamically loaded from environment variables via `src.notifications.config.NotificationConfig`:

| Environment Variable | Default | Purpose |
| :--- | :--- | :--- |
| `ALERT_EMAIL_ENABLED` | `false` | Global feature flag (`true`/`false`) to enable/disable SMTP dispatch |
| `SMTP_HOST` | `localhost` | SMTP relay server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | `None` | Authentication username for SMTP relay |
| `SMTP_PASSWORD` | `None` | Authentication password for SMTP relay |
| `SMTP_USE_TLS` | `true` | Whether to initiate STARTTLS encryption |
| `ALERT_SENDER_EMAIL` | `pipeline-alerts@example.com` | `From:` address on outgoing alerts |
| `ALERT_RECIPIENT_EMAILS` | `data-reliability-team@example.com`| Comma-separated list of recipient email addresses |

A template file [`.env.example`](file:///c:/Users/Saksham/OneDrive/Desktop/ewaybill-data-reliability/.env.example) provides safe placeholders.

---

## 8. Secret Handling & Security

1. **Version Control Protection:**  
   `.env` and `*.env` files are explicitly excluded via `.gitignore`.
2. **String Representation Masking:**  
   `NotificationConfig.__repr__` masks the `smtp_password` field as `********`. Passing config objects to logs or debug statements cannot leak credentials.
3. **Sanitized Exception Logging:**  
   SMTP connection exceptions catch transport errors and format sanitized strings without exposing username/password details.
4. **Payload Security:**  
   Database incident tables and markdown report files never store SMTP configuration, credentials, or keys.

---

## 9. Notification Failure Behavior

The pipeline implements an **authoritative persistence vs. secondary delivery** policy:

$$\text{Incident Persistence} = \textbf{Authoritative} \quad\gg\quad \text{Email Notification} = \textbf{Secondary}$$

### Deterministic Failure Policy
If email delivery fails (e.g. SMTP server unreachable, network timeout, authentication error):
1. **Incident Is NOT Rolled Back:**  
   The incident remains authoritatively committed to the PostgreSQL `incidents` table and written to `docs/incidents/`.
2. **Failure Is Logged:**  
   A diagnostic error is logged with the transport error message.
3. **Pipeline Failure Cause:**  
   The Airflow task still fails and halts trusted loading, but the failure is caused by the underlying **data integrity violation**, not the email delivery glitch.
4. **Lineage Preservation:**  
   `alert_sent` remains `FALSE`, allowing retry or manual notification dispatch once network/SMTP connectivity is restored.

---

## 10. Local Testing Procedure

### 1. Automated Test Suite
To verify incident management and email alerting without an external SMTP server:
```bash
# Run incident and notification tests
pytest -v tests/test_incidents.py tests/test_notifications.py

# Run full project suite (111 tests)
pytest -v
```

### 2. Mock Transport Validation
Tests utilize `smtp_sender_callable` to capture generated `email.message.EmailMessage` objects in-memory, verifying subject lines, headers, recipient lists, and plaintext/HTML body contents without sending live network packets.

### 3. Local Docker Testing (Optional)
To test with a local SMTP catcher (e.g. MailHog or Mailpit):
```bash
# Set environment variables
export ALERT_EMAIL_ENABLED=true
export SMTP_HOST=localhost
export SMTP_PORT=1025
export SMTP_USE_TLS=false
```

---

## 11. Limitations

1. **Single Notification Channel:**  
   Phase 9 intentionally implements Email notifications only. Slack, PagerDuty, and webhooks are omitted per project scope.
2. **Basic SMTP Authentication:**  
   The current service supports standard SMTP username/password with TLS. OAuth2/SSO-based email relays (e.g. Google Workspace XOAUTH2) are not implemented.
3. **Incident Management UI:**  
   Incidents are inspected via PostgreSQL queries or markdown audit logs in `docs/incidents/`. An interactive triage UI is deferred to future dashboard phases.
