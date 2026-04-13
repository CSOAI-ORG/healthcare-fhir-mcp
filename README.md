# Healthcare FHIR MCP Server

FHIR R4 (Fast Healthcare Interoperability Resources) MCP server for healthcare AI applications. Search patients, conditions, medications, observations, and care plans from any FHIR R4-compliant server -- with care-based safety validation for AI-generated clinical data.

Built by [MEOK AI Labs](https://meok.ai) -- the team behind MEOK AI OS and the Sovereign Temple care membrane framework.

## Why this exists

Healthcare AI needs structured access to clinical data, but existing tools lack safety guardrails for AI-generated content. This server validates AI-created observations against physiological safety ranges before they reach the health record. Inspired by MEOK's care membrane framework, it prevents AI from recording impossible vital signs like a heart rate of 500 bpm or a body temperature of 90 degrees Celsius.

## Tools

| Tool | Description |
|------|-------------|
| `search_patients` | Search patients by name, DOB, or identifier |
| `get_patient` | Get full patient demographics and contact info |
| `search_conditions` | Find diagnoses/conditions for a patient |
| `search_medications` | Find active medication requests/prescriptions |
| `search_observations` | Find lab results, vital signs, social history |
| `create_observation` | Record a new observation with safety validation |
| `get_care_plan` | Retrieve active care plans and activities |
| `validate_resource` | Validate any FHIR resource against R4 spec + safety checks |

## Installation

```bash
pip install mcp requests
```

## Configuration

Set the `FHIR_SERVER_URL` environment variable to your FHIR R4 server endpoint.

| Variable | Default | Description |
|----------|---------|-------------|
| `FHIR_SERVER_URL` | (required) | FHIR R4 base URL (e.g., `https://hapi.fhir.org/baseR4`) |
| `FHIR_AUTH_TOKEN` | (optional) | Bearer token for authenticated FHIR servers |

### Public test servers

For development and testing, you can use these public FHIR R4 servers:

- **HAPI FHIR**: `https://hapi.fhir.org/baseR4`
- **SMART Health IT**: `https://r4.smarthealthit.org`

## Usage

### Run the server

```bash
FHIR_SERVER_URL=https://hapi.fhir.org/baseR4 python server.py
```

### Claude Desktop config

Add to `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "healthcare-fhir": {
      "command": "python",
      "args": ["/path/to/healthcare-fhir-mcp/server.py"],
      "env": {
        "FHIR_SERVER_URL": "https://hapi.fhir.org/baseR4"
      }
    }
  }
}
```

### Example calls

**Search patients:**
```
Tool: search_patients
Input: {"name": "Smith", "count": 5}
Output: {"total": 142, "patients": [{"id": "123", "name": "John Smith", "birthDate": "1980-03-15", ...}]}
```

**Get conditions:**
```
Tool: search_conditions
Input: {"patient_id": "123", "clinical_status": "active"}
Output: {"total": 3, "conditions": [{"display": "Type 2 diabetes", "code": "44054006", ...}]}
```

**Create observation with safety validation:**
```
Tool: create_observation
Input: {"patient_id": "123", "loinc_code": "8867-4", "display_name": "Heart rate", "value": 72, "unit": "bpm"}
Output: {"created": true, "id": "456", "validation": {"valid": true, "safety_check": "passed"}}
```

**Rejected unsafe observation:**
```
Tool: create_observation
Input: {"patient_id": "123", "loinc_code": "8867-4", "display_name": "Heart rate", "value": 500, "unit": "bpm"}
Output: {"created": false, "validation": {"valid": false, "errors": ["SAFETY: Heart rate value 500 is outside safe range (30-220 bpm)"]}}
```

## Care-Based Safety Validation

The care membrane validates AI-generated clinical observations against known physiological ranges:

| Vital Sign | LOINC Code | Safe Range | Unit |
|-----------|------------|------------|------|
| Heart rate | 8867-4 | 30-220 | bpm |
| Body temperature | 8310-5 | 30-45 | Cel |
| Systolic BP | 8480-6 | 50-300 | mmHg |
| Diastolic BP | 8462-4 | 20-200 | mmHg |
| Respiratory rate | 9279-1 | 4-60 | /min |
| Oxygen saturation | 2708-6 | 50-100 | % |
| Body weight | 29463-7 | 0.5-500 | kg |
| Body height | 8302-2 | 30-280 | cm |
| BMI | 39156-5 | 5-100 | kg/m2 |
| Glucose | 2339-0 | 10-1000 | mg/dL |

Values outside these ranges are rejected with a descriptive error. AI-generated observations are also flagged if they use `final` status (which should be reserved for clinician-verified data).

## Security Considerations

- **PHI handling**: This server connects to FHIR servers that may contain Protected Health Information (PHI). Ensure your deployment complies with HIPAA, GDPR, or applicable regulations.
- **Authentication**: Use `FHIR_AUTH_TOKEN` for production FHIR servers. Never use public test servers with real patient data.
- **Transport security**: Always use HTTPS for FHIR server URLs in production.
- **AI-generated data**: All observations created through `create_observation` are validated against safety ranges and default to `preliminary` status. AI should never set `final` status on clinical data.
- **Audit**: Consider enabling your FHIR server's audit logging (AuditEvent resource) for compliance.
- **Access control**: The MCP server inherits the permissions of the FHIR auth token. Use the principle of least privilege.
- **Rate limiting**: Built-in rate limiting prevents abuse. Free tier allows 100 calls/day; Pro tier allows 10,000 calls/day.

## FHIR R4 Resources Supported

- Patient
- Condition
- MedicationRequest
- Observation
- CarePlan

Additional resource types can be queried through the `validate_resource` tool for structural validation.

## Pricing

| Tier | Limit | Price |
|------|-------|-------|
| Free | 100 calls/day | $0 |
| Pro | 10,000 calls/day + priority | $15/mo |
| Enterprise | Custom + SLA + BAA | Contact us |

Enterprise tier includes a Business Associate Agreement (BAA) for HIPAA-covered entities.

## License

MIT
