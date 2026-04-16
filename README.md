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
