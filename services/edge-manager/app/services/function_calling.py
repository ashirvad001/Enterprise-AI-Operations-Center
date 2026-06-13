"""
Function Calling — structured JSON output enforcement for edge LLMs.

Wraps Ollama's /api/generate with JSON format enforcement to enable
structured function-calling-style outputs from models that don't natively
support OpenAI function calling.

Approach:
  1. Describe the expected JSON schema in the prompt
  2. Request JSON output via Ollama's `format: json` parameter
  3. Validate and parse the response with Pydantic
  4. Retry up to 3x on parse failure

Use cases:
  - Intent extraction: {"intent": "refund", "confidence": 0.92}
  - Entity extraction: {"order_id": "12345", "product": "laptop"}
  - RAG citation: {"claim": "...", "source": "doc_001", "page": 3}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


SCHEMA_PROMPT_TEMPLATE = """
You are a precise JSON extraction assistant. Extract information from the text and return ONLY a valid JSON object.

Expected JSON schema:
{schema}

Text to process:
{text}

Return ONLY the JSON object, no explanation, no markdown code blocks.
"""

RETRY_PROMPT_TEMPLATE = """
The previous response was invalid JSON. Try again.

Expected JSON schema:
{schema}

Text: {text}

Previous invalid response: {previous}

Return ONLY the valid JSON object:
"""


async def call_with_json_schema(
    runtime,
    text: str,
    schema: Dict[str, Any],
    schema_model: Type[T],
    max_retries: int = 3,
    temperature: float = 0.0,
) -> Optional[T]:
    """
    Call the Ollama runtime and enforce a JSON output schema.

    Args:
        runtime: OllamaRuntime instance.
        text: Input text to process.
        schema: JSON schema dict describing the expected output.
        schema_model: Pydantic model class to validate and parse the output.
        max_retries: Maximum retry attempts on parse failure.
        temperature: LLM temperature (0.0 for deterministic JSON).

    Returns:
        Validated Pydantic model instance, or None if all retries fail.
    """
    schema_str = json.dumps(schema, indent=2)
    prompt = SCHEMA_PROMPT_TEMPLATE.format(schema=schema_str, text=text)
    previous_response = ""

    for attempt in range(max_retries):
        if attempt > 0:
            prompt = RETRY_PROMPT_TEMPLATE.format(
                schema=schema_str,
                text=text,
                previous=previous_response[:500],
            )

        result = await runtime.generate(
            prompt=prompt,
            temperature=temperature,
            json_mode=True,  # Ollama format: json
            max_tokens=512,
        )

        if result.error:
            logger.warning(f"[FunctionCalling] Attempt {attempt+1}: generation failed: {result.error}")
            continue

        response_text = result.text.strip()
        previous_response = response_text

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        try:
            parsed_dict = json.loads(response_text)
            validated = schema_model.model_validate(parsed_dict)
            logger.info(f"[FunctionCalling] Success on attempt {attempt+1}")
            return validated
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(
                f"[FunctionCalling] Attempt {attempt+1} parse failed: {e}. "
                f"Response: {response_text[:200]}"
            )

    logger.error(f"[FunctionCalling] All {max_retries} attempts failed for schema {schema_model.__name__}")
    return None


# ---------------------------------------------------------------------------
# Pre-built Function Call Schemas
# ---------------------------------------------------------------------------

class IntentExtractionOutput(BaseModel):
    """Output schema for intent extraction function call."""
    intent: str
    confidence: float
    entities: Dict[str, Any] = {}


class CitationOutput(BaseModel):
    """Output schema for citation extraction function call."""
    claim: str
    source: str
    page: Optional[int] = None
    confidence: float


INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["ordering", "tracking", "refund", "complaint"],
            "description": "The primary customer intent"
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Confidence score from 0 to 1"
        },
        "entities": {
            "type": "object",
            "description": "Extracted entities like order_id, product, amount"
        }
    },
    "required": ["intent", "confidence"]
}

CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "claim": {"type": "string", "description": "The claim from the answer"},
        "source": {"type": "string", "description": "Source document ID or filename"},
        "page": {"type": "integer", "description": "Page number in source document"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["claim", "source", "confidence"]
}


async def extract_intent_structured(
    runtime,
    text: str,
) -> Optional[IntentExtractionOutput]:
    """Extract intent using structured JSON function calling."""
    return await call_with_json_schema(
        runtime=runtime,
        text=text,
        schema=INTENT_SCHEMA,
        schema_model=IntentExtractionOutput,
        temperature=0.0,
    )
