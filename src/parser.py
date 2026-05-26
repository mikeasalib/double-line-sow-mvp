"""
SOW parser using Gemini API.
Extracts structured deliverables, milestones, constraints, and context from raw SOW text.
"""
import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from google import genai


@dataclass
class ClientContext:
    organization_name: str = ""
    user_count: int = 0
    current_platform: str = ""
    target_services: list[str] = field(default_factory=list)
    industry: str = ""
    data_volume: str = ""
    timeline_weeks: int = 0
    is_federal: bool = False
    compliance_requirements: list[str] = field(default_factory=list)


@dataclass
class Deliverable:
    id: str = ""
    name: str = ""
    description: str = ""
    phase: str = ""
    category: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class ScopeExclusion:
    description: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class ParsedSOW:
    client_context: ClientContext = field(default_factory=ClientContext)
    deliverables: list[Deliverable] = field(default_factory=list)
    exclusions: list[ScopeExclusion] = field(default_factory=list)
    milestones: list[dict] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    pricing: Optional[str] = None
    team_structure: list[dict] = field(default_factory=list)
    raw_response: str = ""


SYSTEM_PROMPT = """You are a senior project manager at a cloud technology consulting firm specializing in Google Cloud, Google Workspace, AWS, and enterprise platform deployments.
You are analyzing a Statement of Work (SOW) to extract structured information for project planning.

Return ONLY valid JSON with no markdown formatting, no backticks, no preamble. The JSON must follow this exact schema:

{
  "client_context": {
    "organization_name": "string",
    "user_count": integer,
    "current_platform": "string (e.g., 'Microsoft 365', 'On-premises Exchange')",
    "target_services": ["Google Workspace", "GCP", etc.],
    "industry": "string",
    "data_volume": "string (e.g., '1.8 TB')",
    "timeline_weeks": integer,
    "is_federal": boolean,
    "compliance_requirements": ["FedRAMP", "HIPAA", etc. or empty list]
  },
  "deliverables": [
    {
      "id": "D-001",
      "name": "short name",
      "description": "what must be delivered",
      "phase": "Discovery|Planning|Build|Migration|Testing|Cutover|Hypercare",
      "category": "Google Workspace|GCP Infrastructure|Data & Analytics|Security & Compliance|Chrome & Endpoint|Federal Compliance",
      "keywords": ["relevant", "search", "terms"]
    }
  ],
  "exclusions": [
    {
      "description": "what is explicitly out of scope",
      "keywords": ["terms", "that", "should", "not", "match"]
    }
  ],
  "milestones": [
    {
      "name": "milestone name",
      "target": "Week X or date",
      "phase": "phase name"
    }
  ],
  "assumptions": ["list of project assumptions"],
  "pricing": "total price if stated, null otherwise",
  "team_structure": [
    {
      "role": "role title",
      "source": "Consulting Firm|Client",
      "allocation": "percentage or description"
    }
  ]
}

Rules:
- Extract EVERY distinct deliverable mentioned in the SOW, no matter how small.
- Each deliverable should map to a single category. If a deliverable spans categories, split it.
- Keywords should be concrete technical terms, not generic words. These will be used to match against a task catalog.
- is_federal should be true if the SOW mentions any government agency, FedRAMP, NIST, ATO, FISMA, or federal contracting terms.
- If information is not stated in the SOW, use reasonable defaults or null. Do not invent information.
- Phase assignments should reflect a typical Google Cloud engagement lifecycle.
- BREVITY: Keep every description field under 80 characters — one tight phrase, no full sentences.
- BREVITY: Limit each keywords array to 4 items maximum.
- BREVITY: Limit assumptions to the 8 most important items.
- BREVITY: Limit team_structure to actual named roles only.
- Return pure minified JSON — no indentation, no extra whitespace.
"""


def parse_sow(sow_text: str) -> ParsedSOW:
    """
    Send SOW text to Gemini API and parse the structured response.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Analyze this Statement of Work and extract the structured information:\n\n{sow_text}",
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=8192,
        ),
    )

    raw = response.text

    # Clean potential markdown fencing
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Strip trailing commas before } or ] (Claude occasionally emits these)
    cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Claude returned invalid JSON: {e}\n\nRaw response:\n{raw[:500]}")

    # Build dataclasses from parsed JSON
    result = ParsedSOW(raw_response=raw)

    ctx = data.get("client_context", {})
    result.client_context = ClientContext(
        organization_name=ctx.get("organization_name", ""),
        user_count=ctx.get("user_count", 0),
        current_platform=ctx.get("current_platform", ""),
        target_services=ctx.get("target_services", []),
        industry=ctx.get("industry", ""),
        data_volume=ctx.get("data_volume", ""),
        timeline_weeks=ctx.get("timeline_weeks", 0),
        is_federal=ctx.get("is_federal", False),
        compliance_requirements=ctx.get("compliance_requirements", []),
    )

    for d in data.get("deliverables", []):
        result.deliverables.append(Deliverable(
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            phase=d.get("phase", ""),
            category=d.get("category", ""),
            keywords=d.get("keywords", []),
        ))

    for ex in data.get("exclusions", []):
        result.exclusions.append(ScopeExclusion(
            description=ex.get("description", ""),
            keywords=ex.get("keywords", []),
        ))

    result.milestones = data.get("milestones", [])
    result.assumptions = data.get("assumptions", [])
    result.pricing = data.get("pricing")
    result.team_structure = data.get("team_structure", [])

    return result


def parsed_sow_to_dict(parsed: ParsedSOW) -> dict:
    """Convert ParsedSOW to a serializable dictionary."""
    return {
        "client_context": asdict(parsed.client_context),
        "deliverables": [asdict(d) for d in parsed.deliverables],
        "exclusions": [asdict(e) for e in parsed.exclusions],
        "milestones": parsed.milestones,
        "assumptions": parsed.assumptions,
        "pricing": parsed.pricing,
        "team_structure": parsed.team_structure,
    }
