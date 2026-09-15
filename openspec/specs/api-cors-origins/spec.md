# api-cors-origins Specification

## Purpose

Allow Streamlit Cloud, Hugging Face Spaces, and local Streamlit browsers without unmatched origin globs.

## Requirements

### Requirement: Subdomain origins allowed

HTTPS Origins on Streamlit Cloud and Hugging Face Spaces subdomains MUST be allowed by a subdomain-matching mechanism. Literal globs such as `https://*.streamlit.app` MUST NOT be that mechanism. Credentialed CORS MUST stay enabled.

#### Scenario: Streamlit Cloud

- GIVEN an HTTPS Streamlit Cloud app Origin
- WHEN the browser sends a CORS request
- THEN that Origin is permitted

#### Scenario: Hugging Face Spaces

- GIVEN an HTTPS Hugging Face Space Origin
- WHEN the browser sends a CORS request
- THEN that Origin is permitted

#### Scenario: No glob matching

- GIVEN API CORS config
- WHEN origins are evaluated
- THEN matching MUST NOT rely on glob strings like `https://*.streamlit.app`

### Requirement: Local Streamlit exact

The API MUST allow exact `http://localhost:8501` and `http://127.0.0.1:8501`.

#### Scenario: Localhost

- GIVEN Origin `http://localhost:8501`
- WHEN a CORS request is sent
- THEN that Origin is permitted

#### Scenario: Loopback

- GIVEN Origin `http://127.0.0.1:8501`
- WHEN a CORS request is sent
- THEN that Origin is permitted
