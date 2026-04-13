#!/usr/bin/env python3
"""
Healthcare FHIR MCP Server
============================
FHIR R4 (Fast Healthcare Interoperability Resources) MCP server for healthcare AI.
Connects to any FHIR R4-compliant server to search patients, conditions, medications,
observations, and care plans with care-based safety validation.

Built by MEOK AI Labs.

Install: pip install mcp requests
Run:     FHIR_SERVER_URL=https://hapi.fhir.org/baseR4 python server.py
"""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from collections import defaultdict
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
FHIR_SERVER_URL = os.environ.get("FHIR_SERVER_URL", "").rstrip("/")
FHIR_AUTH_TOKEN = os.environ.get("FHIR_AUTH_TOKEN", "")  # Optional Bearer token

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
FREE_DAILY_LIMIT = 100
PRO_DAILY_LIMIT = 10_000
_usage: dict[str, list[datetime]] = defaultdict(list)


def _check_rate_limit(caller: str = "anonymous", tier: str = "free") -> Optional[str]:
    """Returns error string if rate-limited, else None."""
    limit = PRO_DAILY_LIMIT if tier == "pro" else FREE_DAILY_LIMIT
    now = datetime.now()
    cutoff = now - timedelta(days=1)
    _usage[caller] = [t for t in _usage[caller] if t > cutoff]
    if len(_usage[caller]) >= limit:
        return f"Rate limit reached ({limit}/day). Upgrade to Pro: https://meok.ai/mcp/healthcare-fhir/pro"
    _usage[caller].append(now)
    return None


# ---------------------------------------------------------------------------
# FHIR HTTP helpers
# ---------------------------------------------------------------------------
def _fhir_headers() -> dict:
    """Return standard FHIR request headers."""
    headers = {
        "Accept": "application/fhir+json",
        "Content-Type": "application/fhir+json",
    }
    if FHIR_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {FHIR_AUTH_TOKEN}"
    return headers


def _fhir_get(path: str, params: dict = None) -> dict:
    """Execute a GET request against the FHIR server."""
    if not FHIR_SERVER_URL:
        raise ValueError(
            "FHIR_SERVER_URL environment variable is required. "
            "Example: https://hapi.fhir.org/baseR4"
        )
    import requests
    url = f"{FHIR_SERVER_URL}/{path}"
    response = requests.get(url, headers=_fhir_headers(), params=params or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def _fhir_post(path: str, data: dict) -> dict:
    """Execute a POST request against the FHIR server."""
    if not FHIR_SERVER_URL:
        raise ValueError("FHIR_SERVER_URL environment variable is required.")
    import requests
    url = f"{FHIR_SERVER_URL}/{path}"
    response = requests.post(url, headers=_fhir_headers(), json=data, timeout=30)
    response.raise_for_status()
    return response.json()


def _extract_entries(bundle: dict) -> list[dict]:
    """Extract resource entries from a FHIR Bundle."""
    entries = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        entries.append(resource)
    return entries


# ---------------------------------------------------------------------------
# Care-based validation — inspired by MEOK care membrane
# ---------------------------------------------------------------------------
# Safety thresholds for clinical data created by AI
VITAL_SIGN_RANGES = {
    # LOINC code: (min_safe, max_safe, unit, display_name)
    "8867-4": (30, 220, "bpm", "Heart rate"),
    "8310-5": (30.0, 45.0, "Cel", "Body temperature"),
    "8480-6": (50, 300, "mmHg", "Systolic blood pressure"),
    "8462-4": (20, 200, "mmHg", "Diastolic blood pressure"),
    "9279-1": (4, 60, "/min", "Respiratory rate"),
    "2708-6": (50, 100, "%", "Oxygen saturation"),
    "29463-7": (0.5, 500, "kg", "Body weight"),
    "8302-2": (30, 280, "cm", "Body height"),
    "39156-5": (5, 100, "kg/m2", "BMI"),
    "2339-0": (10, 1000, "mg/dL", "Glucose"),
}


def _validate_observation_safety(resource: dict) -> dict:
    """Validate that an AI-generated observation falls within safe clinical ranges.
    Returns validation result with pass/fail and any warnings."""
    warnings = []
    errors = []

    # Check resource type
    if resource.get("resourceType") != "Observation":
        errors.append("resourceType must be 'Observation'")

    # Check required fields
    if not resource.get("status"):
        errors.append("Missing required field: status")
    if not resource.get("code"):
        errors.append("Missing required field: code")
    if not resource.get("subject"):
        warnings.append("Missing subject reference -- observation not linked to a patient")

    # Validate value against known vital sign ranges
    value_quantity = resource.get("valueQuantity", {})
    codings = resource.get("code", {}).get("coding", [])

    for coding in codings:
        loinc_code = coding.get("code", "")
        if loinc_code in VITAL_SIGN_RANGES:
            min_safe, max_safe, expected_unit, display = VITAL_SIGN_RANGES[loinc_code]
            value = value_quantity.get("value")

            if value is not None:
                if value < min_safe or value > max_safe:
                    errors.append(
                        f"SAFETY: {display} value {value} is outside safe range "
                        f"({min_safe}-{max_safe} {expected_unit}). "
                        f"AI-generated clinical values must be within physiological limits."
                    )
                unit = value_quantity.get("unit", "")
                if expected_unit and unit and unit != expected_unit:
                    warnings.append(
                        f"Unit mismatch for {display}: got '{unit}', expected '{expected_unit}'"
                    )

    # Check for prohibited statuses from AI
    status = resource.get("status", "")
    if status == "final":
        warnings.append(
            "Status 'final' should only be set by authorized clinicians. "
            "AI-generated observations should use 'preliminary' status."
        )

    passed = len(errors) == 0
    return {
        "valid": passed,
        "errors": errors,
        "warnings": warnings,
        "safety_check": "passed" if passed else "failed",
        "care_membrane_note": (
            "This validation is inspired by MEOK AI Labs' care membrane framework. "
            "AI-generated clinical data undergoes safety range checks to prevent "
            "physiologically impossible values from entering health records."
        ),
    }


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Healthcare FHIR MCP",
    instructions=(
        "FHIR R4 healthcare data server with care-based safety validation. "
        "Connects to any FHIR R4-compliant server. Requires FHIR_SERVER_URL env var. "
        "AI-generated clinical data is validated against physiological safety ranges."
    ),
)


@mcp.tool()
def search_patients(name: str = "", birthdate: str = "", identifier: str = "", count: int = 20) -> dict:
    """Search for patients on the FHIR server by name, date of birth, or identifier.
    Date format: YYYY-MM-DD. Identifier format depends on the system (e.g., MRN, SSN)."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        params: dict[str, Any] = {"_count": min(count, 100)}
        if name:
            params["name"] = name
        if birthdate:
            params["birthdate"] = birthdate
        if identifier:
            params["identifier"] = identifier

        bundle = _fhir_get("Patient", params)
        patients = []
        for resource in _extract_entries(bundle):
            names = resource.get("name", [{}])
            display_name = ""
            if names:
                given = " ".join(names[0].get("given", []))
                family = names[0].get("family", "")
                display_name = f"{given} {family}".strip()

            patients.append({
                "id": resource.get("id"),
                "name": display_name,
                "birthDate": resource.get("birthDate"),
                "gender": resource.get("gender"),
                "identifier": [
                    {"system": i.get("system"), "value": i.get("value")}
                    for i in resource.get("identifier", [])[:3]
                ],
            })

        return {
            "total": bundle.get("total", len(patients)),
            "patients": patients,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_patient(patient_id: str) -> dict:
    """Get a full patient record by FHIR resource ID. Returns demographics,
    identifiers, contact info, and other patient details."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        resource = _fhir_get(f"Patient/{patient_id}")

        names = resource.get("name", [{}])
        display_name = ""
        if names:
            given = " ".join(names[0].get("given", []))
            family = names[0].get("family", "")
            display_name = f"{given} {family}".strip()

        telecoms = [
            {"system": t.get("system"), "value": t.get("value"), "use": t.get("use")}
            for t in resource.get("telecom", [])
        ]

        addresses = []
        for addr in resource.get("address", []):
            addresses.append({
                "use": addr.get("use"),
                "city": addr.get("city"),
                "state": addr.get("state"),
                "postalCode": addr.get("postalCode"),
                "country": addr.get("country"),
            })

        return {
            "id": resource.get("id"),
            "name": display_name,
            "birthDate": resource.get("birthDate"),
            "gender": resource.get("gender"),
            "active": resource.get("active"),
            "identifier": [
                {"system": i.get("system"), "value": i.get("value")}
                for i in resource.get("identifier", [])
            ],
            "telecom": telecoms,
            "address": addresses,
            "maritalStatus": resource.get("maritalStatus", {}).get("text"),
            "communication": [
                {"language": c.get("language", {}).get("text")}
                for c in resource.get("communication", [])
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_conditions(patient_id: str, clinical_status: str = "active", count: int = 50) -> dict:
    """Find diagnoses and conditions for a patient. Clinical status can be
    'active', 'recurrence', 'relapse', 'inactive', 'remission', or 'resolved'."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": min(count, 100),
        }
        if clinical_status:
            params["clinical-status"] = clinical_status

        bundle = _fhir_get("Condition", params)
        conditions = []
        for resource in _extract_entries(bundle):
            code = resource.get("code", {})
            display = code.get("text", "")
            if not display:
                codings = code.get("coding", [])
                if codings:
                    display = codings[0].get("display", codings[0].get("code", ""))

            conditions.append({
                "id": resource.get("id"),
                "display": display,
                "code": code.get("coding", [{}])[0].get("code") if code.get("coding") else None,
                "system": code.get("coding", [{}])[0].get("system") if code.get("coding") else None,
                "clinicalStatus": resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", ""),
                "verificationStatus": resource.get("verificationStatus", {}).get("coding", [{}])[0].get("code", ""),
                "onsetDateTime": resource.get("onsetDateTime"),
                "recordedDate": resource.get("recordedDate"),
                "severity": resource.get("severity", {}).get("text"),
            })

        return {
            "patient_id": patient_id,
            "total": bundle.get("total", len(conditions)),
            "conditions": conditions,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_medications(patient_id: str, status: str = "active", count: int = 50) -> dict:
    """Find medication requests (prescriptions) for a patient. Status can be
    'active', 'on-hold', 'cancelled', 'completed', 'stopped', 'draft'."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": min(count, 100),
        }
        if status:
            params["status"] = status

        bundle = _fhir_get("MedicationRequest", params)
        medications = []
        for resource in _extract_entries(bundle):
            med_code = resource.get("medicationCodeableConcept", {})
            display = med_code.get("text", "")
            if not display:
                codings = med_code.get("coding", [])
                if codings:
                    display = codings[0].get("display", "")

            dosage_instructions = []
            for dosage in resource.get("dosageInstruction", []):
                dosage_instructions.append(dosage.get("text", str(dosage.get("timing", ""))))

            medications.append({
                "id": resource.get("id"),
                "medication": display,
                "status": resource.get("status"),
                "intent": resource.get("intent"),
                "authoredOn": resource.get("authoredOn"),
                "dosageInstructions": dosage_instructions,
                "requester": resource.get("requester", {}).get("display"),
            })

        return {
            "patient_id": patient_id,
            "total": bundle.get("total", len(medications)),
            "medications": medications,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def search_observations(patient_id: str, category: str = "", code: str = "", count: int = 50) -> dict:
    """Find lab results, vital signs, and other observations for a patient.
    Category can be 'vital-signs', 'laboratory', 'social-history', 'imaging'.
    Code is a LOINC code (e.g., '8867-4' for heart rate)."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": min(count, 100),
            "_sort": "-date",
        }
        if category:
            params["category"] = category
        if code:
            params["code"] = code

        bundle = _fhir_get("Observation", params)
        observations = []
        for resource in _extract_entries(bundle):
            obs_code = resource.get("code", {})
            display = obs_code.get("text", "")
            if not display:
                codings = obs_code.get("coding", [])
                if codings:
                    display = codings[0].get("display", codings[0].get("code", ""))

            # Extract value
            value = None
            unit = None
            if "valueQuantity" in resource:
                vq = resource["valueQuantity"]
                value = vq.get("value")
                unit = vq.get("unit", vq.get("code", ""))
            elif "valueString" in resource:
                value = resource["valueString"]
            elif "valueCodeableConcept" in resource:
                value = resource["valueCodeableConcept"].get("text")

            observations.append({
                "id": resource.get("id"),
                "display": display,
                "value": value,
                "unit": unit,
                "status": resource.get("status"),
                "effectiveDateTime": resource.get("effectiveDateTime"),
                "issued": resource.get("issued"),
                "category": [
                    cat.get("coding", [{}])[0].get("code", "")
                    for cat in resource.get("category", [])
                ],
            })

        return {
            "patient_id": patient_id,
            "total": bundle.get("total", len(observations)),
            "observations": observations,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def create_observation(
    patient_id: str,
    loinc_code: str,
    display_name: str,
    value: float,
    unit: str,
    status: str = "preliminary",
) -> dict:
    """Record a new observation (vital sign, lab result) for a patient.
    Includes care-based safety validation -- AI-generated values are checked
    against physiological ranges before submission.

    Status should be 'preliminary' for AI-generated data (not 'final').
    Common LOINC codes: 8867-4 (heart rate), 8310-5 (temperature),
    8480-6 (systolic BP), 2708-6 (SpO2), 29463-7 (weight)."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    resource = {
        "resourceType": "Observation",
        "status": status,
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": loinc_code,
                    "display": display_name,
                }
            ],
            "text": display_name,
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
        },
        "effectiveDateTime": datetime.now(tz=timezone.utc).isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }

    # Care-based safety validation
    validation = _validate_observation_safety(resource)
    if not validation["valid"]:
        return {
            "created": False,
            "validation": validation,
            "message": "Observation rejected by care membrane safety check. Fix errors before retrying.",
        }

    try:
        result = _fhir_post("Observation", resource)
        return {
            "created": True,
            "id": result.get("id"),
            "validation": validation,
            "resource": {
                "resourceType": "Observation",
                "id": result.get("id"),
                "status": status,
                "code": display_name,
                "value": value,
                "unit": unit,
                "patient": patient_id,
            },
        }
    except Exception as e:
        return {"error": str(e), "validation": validation}


@mcp.tool()
def get_care_plan(patient_id: str, status: str = "active", count: int = 20) -> dict:
    """Retrieve active care plans for a patient. Care plans describe the intended
    care activities, goals, and team members involved in a patient's treatment."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        params: dict[str, Any] = {
            "patient": patient_id,
            "_count": min(count, 50),
        }
        if status:
            params["status"] = status

        bundle = _fhir_get("CarePlan", params)
        care_plans = []
        for resource in _extract_entries(bundle):
            categories = []
            for cat in resource.get("category", []):
                text = cat.get("text", "")
                if not text and cat.get("coding"):
                    text = cat["coding"][0].get("display", "")
                categories.append(text)

            activities = []
            for activity in resource.get("activity", []):
                detail = activity.get("detail", {})
                act_code = detail.get("code", {})
                act_display = act_code.get("text", "")
                if not act_display and act_code.get("coding"):
                    act_display = act_code["coding"][0].get("display", "")
                activities.append({
                    "description": activity.get("detail", {}).get("description", act_display),
                    "status": detail.get("status"),
                })

            care_plans.append({
                "id": resource.get("id"),
                "status": resource.get("status"),
                "intent": resource.get("intent"),
                "title": resource.get("title"),
                "description": resource.get("description"),
                "categories": categories,
                "period": resource.get("period"),
                "activities": activities,
                "created": resource.get("created"),
            })

        return {
            "patient_id": patient_id,
            "total": bundle.get("total", len(care_plans)),
            "care_plans": care_plans,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def validate_resource(resource_json: str) -> dict:
    """Validate a FHIR resource against the R4 specification. Accepts a JSON string
    of the resource. Checks structure, required fields, and (for Observations)
    clinical safety ranges.

    This uses the FHIR server's $validate operation when available, plus local
    care-based safety checks for AI-generated clinical data."""
    err = _check_rate_limit()
    if err:
        return {"error": err}

    try:
        resource = json.loads(resource_json)
    except json.JSONDecodeError as e:
        return {"valid": False, "errors": [f"Invalid JSON: {str(e)}"]}

    resource_type = resource.get("resourceType")
    if not resource_type:
        return {"valid": False, "errors": ["Missing resourceType field"]}

    errors = []
    warnings = []

    # Local structural validation
    if resource_type == "Patient":
        if not resource.get("name"):
            warnings.append("Patient has no name field")
        if not resource.get("gender"):
            warnings.append("Patient has no gender field")

    elif resource_type == "Observation":
        safety = _validate_observation_safety(resource)
        errors.extend(safety["errors"])
        warnings.extend(safety["warnings"])

    elif resource_type == "Condition":
        if not resource.get("code"):
            errors.append("Condition requires a code field")
        if not resource.get("subject"):
            errors.append("Condition requires a subject reference")

    elif resource_type == "MedicationRequest":
        if not resource.get("medicationCodeableConcept") and not resource.get("medicationReference"):
            errors.append("MedicationRequest requires medication (CodeableConcept or Reference)")
        if not resource.get("subject"):
            errors.append("MedicationRequest requires a subject reference")

    # Try server-side $validate if available
    server_validation = None
    try:
        result = _fhir_post(f"{resource_type}/$validate", resource)
        issues = result.get("issue", [])
        for issue in issues:
            severity = issue.get("severity", "")
            msg = issue.get("diagnostics", issue.get("details", {}).get("text", ""))
            if severity in ("error", "fatal"):
                errors.append(f"Server: {msg}")
            elif severity == "warning":
                warnings.append(f"Server: {msg}")
        server_validation = "completed"
    except Exception:
        server_validation = "unavailable (local validation only)"

    return {
        "valid": len(errors) == 0,
        "resourceType": resource_type,
        "errors": errors,
        "warnings": warnings,
        "server_validation": server_validation,
    }


if __name__ == "__main__":
    mcp.run()
