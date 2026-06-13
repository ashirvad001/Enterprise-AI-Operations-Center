"""
Entity Extractor — extracts structured entities from customer support transcripts.

Entities:
  - order_id: Order numbers (e.g., "ORD-12345", "#12345", "order 12345")
  - date: Dates mentioned (e.g., "last Tuesday", "March 15th", "yesterday")
  - product: Product names or descriptions
  - amount: Monetary amounts ("$49.99", "49 dollars")
  - tracking_number: Shipping tracking codes

Uses: spaCy NER + regex patterns for robust extraction
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

try:
    import spacy
    _SPACY_AVAILABLE = True
    try:
        _NLP = spacy.load("en_core_web_sm")
        logger.info("spaCy en_core_web_sm loaded")
    except OSError:
        _NLP = None
        logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")
except ImportError:
    _SPACY_AVAILABLE = False
    _NLP = None
    logger.warning("spaCy not installed. Using regex-only entity extraction.")

# ---------------------------------------------------------------------------
# Regex Patterns
# ---------------------------------------------------------------------------

ORDER_ID_PATTERNS = [
    r"\b(?:order|ord)[\s#\-]*([A-Z0-9]{4,12})\b",
    r"#([A-Z0-9]{4,12})\b",
    r"\border[\s#]*(\d{4,10})\b",
    r"\b([A-Z]{2,4}-\d{4,8})\b",          # e.g. ORD-12345, TRK-987654
]

TRACKING_PATTERNS = [
    r"\b([0-9]{12,22})\b",                # FedEx/UPS numeric
    r"\b([A-Z]{2}\d{9}[A-Z]{2})\b",       # USPS format
    r"\b(1Z[A-Z0-9]{16})\b",              # UPS format
]

AMOUNT_PATTERNS = [
    r"\$\s*(\d+(?:\.\d{1,2})?)",
    r"(\d+(?:\.\d{1,2})?)\s*(?:dollar|dollars|USD)",
]

RELATIVE_DATE_MAP = {
    "yesterday": -1,
    "today": 0,
    "tomorrow": 1,
    "last week": -7,
    "last month": -30,
    "last tuesday": -2,   # approximate
    "last monday": -3,
    "this week": 0,
}


# ---------------------------------------------------------------------------
# Entity Models
# ---------------------------------------------------------------------------

class ExtractedEntities(BaseModel):
    """Structured entities extracted from a support transcript."""
    order_ids: List[str] = Field(default_factory=list)
    tracking_numbers: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    amounts: List[str] = Field(default_factory=list)
    persons: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    raw_entities: List[Dict[str, str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Regex Extraction
# ---------------------------------------------------------------------------

def _extract_with_regex(text: str) -> Dict[str, List[str]]:
    """Extract entities using regex patterns (always available)."""
    results: Dict[str, List[str]] = {
        "order_ids": [],
        "tracking_numbers": [],
        "amounts": [],
        "dates": [],
    }

    # Order IDs
    for pattern in ORDER_ID_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["order_ids"].extend(matches)

    # Tracking numbers (only if not already captured as order IDs)
    existing_ids = set(results["order_ids"])
    for pattern in TRACKING_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        new = [m for m in matches if m not in existing_ids]
        results["tracking_numbers"].extend(new)

    # Amounts
    for pattern in AMOUNT_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        results["amounts"].extend([f"${m}" for m in matches])

    # Relative dates
    text_lower = text.lower()
    for phrase, delta in RELATIVE_DATE_MAP.items():
        if phrase in text_lower:
            date = (datetime.now() + timedelta(days=delta)).strftime("%Y-%m-%d")
            results["dates"].append(f"{phrase} ({date})")

    # Deduplicate
    for key in results:
        results[key] = list(dict.fromkeys(results[key]))

    return results


# ---------------------------------------------------------------------------
# spaCy NER Extraction
# ---------------------------------------------------------------------------

def _extract_with_spacy(text: str) -> Dict[str, List[str]]:
    """Extract named entities using spaCy NER."""
    if _NLP is None:
        return {}

    try:
        doc = _NLP(text)
        results: Dict[str, List[str]] = {
            "persons": [],
            "locations": [],
            "organizations": [],
            "dates": [],
            "products": [],
            "raw_entities": [],
        }

        for ent in doc.ents:
            raw = {"text": ent.text, "label": ent.label_, "start": ent.start_char, "end": ent.end_char}
            results["raw_entities"].append(raw)

            if ent.label_ == "PERSON":
                results["persons"].append(ent.text)
            elif ent.label_ in ("GPE", "LOC", "FAC"):
                results["locations"].append(ent.text)
            elif ent.label_ == "ORG":
                results["organizations"].append(ent.text)
            elif ent.label_ == "DATE":
                results["dates"].append(ent.text)
            elif ent.label_ == "PRODUCT":
                results["products"].append(ent.text)

        return results
    except Exception as e:
        logger.warning(f"spaCy extraction failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# Entity Extractor Service
# ---------------------------------------------------------------------------

class EntityExtractor:
    """
    Extracts structured entities from customer support transcripts.

    Usage:
        extractor = EntityExtractor()
        entities = extractor.extract("My order #12345 hasn't arrived yet")
        print(entities.order_ids)  # ['12345']
    """

    def extract(self, text: str, intent: Optional[str] = None) -> ExtractedEntities:
        """
        Extract entities from transcribed text.

        Args:
            text: Transcribed customer query.
            intent: Optional intent context (helps prioritize extraction).

        Returns:
            ExtractedEntities with all found entities.
        """
        if not text:
            return ExtractedEntities()

        # 1. Regex extraction (always runs)
        regex_results = _extract_with_regex(text)

        # 2. spaCy NER (if available)
        spacy_results = _extract_with_spacy(text) if _SPACY_AVAILABLE else {}

        # 3. Merge results
        entities = ExtractedEntities(
            order_ids=regex_results.get("order_ids", []),
            tracking_numbers=regex_results.get("tracking_numbers", []),
            amounts=regex_results.get("amounts", []),
            dates=list(dict.fromkeys(
                regex_results.get("dates", []) + spacy_results.get("dates", [])
            )),
            products=spacy_results.get("products", []),
            persons=spacy_results.get("persons", []),
            locations=spacy_results.get("locations", []),
            organizations=spacy_results.get("organizations", []),
            raw_entities=spacy_results.get("raw_entities", []),
        )

        logger.info(
            f"[EntityExtractor] Extracted: "
            f"orders={entities.order_ids}, "
            f"tracking={entities.tracking_numbers}, "
            f"amounts={entities.amounts}, "
            f"dates={entities.dates[:2]}"
        )
        return entities

    def to_crm_payload(self, entities: ExtractedEntities, intent: str) -> Dict[str, Any]:
        """
        Formats entities into a CRM/order API lookup payload.

        Args:
            entities: Extracted entities.
            intent: Classified intent.

        Returns:
            Dict ready to pass to CRM/order API.
        """
        return {
            "intent": intent,
            "order_id": entities.order_ids[0] if entities.order_ids else None,
            "tracking_number": entities.tracking_numbers[0] if entities.tracking_numbers else None,
            "amount": entities.amounts[0] if entities.amounts else None,
            "date_mentioned": entities.dates[0] if entities.dates else None,
            "product": entities.products[0] if entities.products else None,
            "customer_name": entities.persons[0] if entities.persons else None,
        }
