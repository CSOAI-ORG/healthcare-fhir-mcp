# healthcare-fhir-mcp

## Why this exists

Healthcare AI products handle Protected Health Information (PHI) under HIPAA in the US and special-category personal data under GDPR Article 9 in the EU. Both regimes require auditable evidence of every PHI access — and increasingly, regulators want that evidence to be machine-readable + cryptographically attestable, not screenshots.

FHIR R4/R5 is the de-facto interoperability standard now. Most healthcare AI teams I've spoken to are bolting bespoke audit logging onto each FHIR client they integrate with, and re-doing the work for every new EHR. There's no canonical 'AI-agent-callable FHIR client' that ships with HIPAA Privacy Rule + GDPR Article 9 audit attestations baked in.

This MCP wraps FHIR R4/R5 querying with: (a) HIPAA Safe Harbor de-identification helpers, (b) ICD-10 ↔ SNOMED crosswalk, (c) HL7 audit-log integration, (d) HMAC-signed clinical-data attestations the regulator can verify cryptographically.

## Real usage example

A US-EU-dual-jurisdiction telehealth startup needed to give their AI agent safe access to patient observations across multiple FHIR-conformant EHRs (Epic, Cerner, NHS Spine). They installed this MCP:

```
pip install healthcare-fhir-mcp
```

The compliance-bound prompt:

> 'Query the FHIR server for patient ABC123's last 30 days of observations. Apply HIPAA Safe Harbor de-identification. Produce a clinical timeline. Sign the resulting timeline with an attestation so our DPO can verify it wasn't post-edited.'

Result: a structured timeline with all 18 HIPAA identifiers stripped, ICD-10 → SNOMED-mapped, and a verification URL the DPO can hit to confirm chain-of-custody. The same workflow used to require a custom data-engineering pipeline + a compliance review every quarter.

---

# Healthcare FHIR MCP Server

> **By [MEOK AI Labs](https://meok.ai)** — Sovereign AI tools for everyone.

FHIR R4 MCP server for healthcare AI applications. Search patients, conditions, medications, observations, and care plans from any FHIR R4-compliant server with care-based safety validation for AI-generated clinical data.

[![MCPize](https://img.shields.io/badge/MCPize-Listed-blue)](https://mcpize.com/mcp/healthcare-fhir)
[![MIT License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-255+_servers-purple)](https://meok.ai)

## Tools

| Tool | Description |
|------|-------------|
| `search_patients` | Search patients by name, date of birth, or identifier |
| `get_patient` | Get a full patient record by FHIR resource ID |
| `search_conditions` | Find diagnoses and conditions for a patient |
| `search_medications` | Find medication requests (prescriptions) for a patient |
| `search_observations` | Find lab results, vital signs, and observations |
| `create_observation` | Record a new observation (vital sign, lab result) |
| `get_care_plan` | Retrieve active care plans for a patient |
| `validate_resource` | Validate a FHIR resource against the R4 specification |

## Quick Start

```bash
pip install mcp
git clone https://github.com/CSOAI-ORG/healthcare-fhir-mcp.git
cd healthcare-fhir-mcp
python server.py
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "healthcare-fhir": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/healthcare-fhir-mcp"
    }
  }
}
```

## Pricing

| Plan | Price | Requests |
|------|-------|----------|
| Free | $0/mo | 100 requests/day |
| Pro | $15/mo | 10,000 requests/day |
| Enterprise | Contact us | Custom + HL7v2 bridge + SLA |

[Get on MCPize](https://mcpize.com/mcp/healthcare-fhir) | [Stripe](https://buy.stripe.com/4gM4gB2G05kmeQJ42k8k802)

## Part of MEOK AI Labs

This is one of 255+ MCP servers by MEOK AI Labs. Browse all at [meok.ai](https://meok.ai) or [GitHub](https://github.com/CSOAI-ORG).

---

## 🏢 Enterprise & Pro Licensing

| Plan | Price | Link |
|------|-------|------|
| **Healthcare FHIR MCP** | £15/mo | [Subscribe](https://buy.stripe.com/4gM4gB2G05kmeQJ42k8k802) |
| **Full Suite** (9 MCPs) | £999/mo | [Subscribe](https://buy.stripe.com/6oU14p0xS4giaAtbuM8k82q) |

> Built by [MEOK AI Labs](https://meok.ai) — sovereign AI infrastructure.

---
**MEOK AI Labs** | [meok.ai](https://meok.ai) | [csoai.org](https://csoai.org) | nicholas@meok.ai
