"""
Voice Agent State Machine — manages multi-turn customer support conversations.

States:
  IDLE → LISTENING → TRANSCRIBING → CLASSIFYING → PROCESSING → RESPONDING → IDLE
                                                              ↓
                                                          ESCALATING (human handoff)

Conversation Flow:
  handle_question → classify_intent → extract_entities → call_api → generate_response
  → check_clarification → (loop or close)

Escalation: if confidence < 0.7 OR user says "agent"/"human"/"supervisor"
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ESCALATION_KEYWORDS = {"agent", "human", "supervisor", "manager", "person", "representative", "escalate"}
ESCALATION_CONFIDENCE_THRESHOLD = 0.7
MAX_TURNS = 10


# ---------------------------------------------------------------------------
# State Models
# ---------------------------------------------------------------------------

class ConversationState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    CLASSIFYING = "classifying"
    PROCESSING = "processing"
    RESPONDING = "responding"
    WAITING_CLARIFICATION = "waiting_clarification"
    ESCALATING = "escalating"
    CLOSED = "closed"


class Turn(BaseModel):
    """A single turn in the conversation."""
    turn_id: int
    user_text: str
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    entities: Optional[Dict[str, Any]] = None
    bot_response: str = ""
    state: ConversationState = ConversationState.PROCESSING
    latency_ms: int = 0


class ConversationContext(BaseModel):
    """Full conversation context across all turns."""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    state: ConversationState = ConversationState.IDLE
    turns: List[Turn] = Field(default_factory=list)

    # Accumulated understanding
    intent: Optional[str] = None
    entities: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, str]] = Field(default_factory=list)

    # Escalation tracking
    escalated: bool = False
    escalation_reason: Optional[str] = None

    # Metrics
    total_latency_ms: int = 0
    resolved: bool = False
    csat_score: Optional[float] = None

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    @property
    def last_turn(self) -> Optional[Turn]:
        return self.turns[-1] if self.turns else None


# ---------------------------------------------------------------------------
# Response Generation
# ---------------------------------------------------------------------------

INTENT_RESPONSE_TEMPLATES = {
    "ordering": {
        "with_product": "I'd be happy to help you with placing an order for {product}. "
                         "Let me check our current inventory and pricing for you.",
        "without_product": "I can help you place an order. Could you tell me which product "
                            "you're interested in?",
    },
    "tracking": {
        "with_order": "Let me check the status of order {order_id} for you. "
                       "I'll pull up the latest tracking information.",
        "without_order": "I can help you track your order. "
                          "Could you provide your order number?",
    },
    "refund": {
        "with_order": "I'll initiate a refund review for order {order_id}. "
                       "This typically takes 3-5 business days to process.",
        "without_order": "I can help process your refund. "
                          "Could you provide your order number or the item you'd like to return?",
    },
    "complaint": {
        "default": "I sincerely apologize for the experience you've had. "
                   "Your feedback is very important to us. "
                   "Could you please share more details about what went wrong so I can help resolve this?",
    },
}


def _generate_response_from_template(
    intent: str,
    entities: Dict[str, Any],
) -> str:
    """Generate a response using pre-defined templates (fast, no LLM needed)."""
    templates = INTENT_RESPONSE_TEMPLATES.get(intent, {})
    order_id = entities.get("order_id")
    product = entities.get("product")

    if intent == "ordering":
        tpl_key = "with_product" if product else "without_product"
        return templates.get(tpl_key, "I can help with your order.").format(product=product or "")
    elif intent == "tracking":
        tpl_key = "with_order" if order_id else "without_order"
        return templates.get(tpl_key, "I can help track your order.").format(order_id=order_id or "")
    elif intent == "refund":
        tpl_key = "with_order" if order_id else "without_order"
        return templates.get(tpl_key, "I can help with your refund.").format(order_id=order_id or "")
    else:
        return templates.get("default", "I'm here to help. Could you please tell me more?")


async def _generate_response_llm(
    user_text: str,
    intent: str,
    entities: Dict[str, Any],
    history: List[Dict[str, str]],
) -> str:
    """Generate a contextual response using LLM (Ollama/OpenAI)."""
    system_prompt = (
        "You are a helpful customer support agent. "
        "Be empathetic, concise (2-3 sentences max), and professional. "
        "If you need more information, ask one specific question. "
        "Do not make up order details or make promises you cannot keep."
    )

    history_text = "\n".join([
        f"Customer: {t['user']}\nAgent: {t['bot']}"
        for t in history[-3:]  # Last 3 turns for context
    ])

    user_prompt = (
        f"Customer intent: {intent}\n"
        f"Extracted entities: {entities}\n\n"
        f"Conversation history:\n{history_text}\n\n"
        f"Customer's latest message: {user_text}\n\n"
        f"Respond as a customer support agent:"
    )

    # Try Ollama
    try:
        import httpx
        response = await httpx.AsyncClient().post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>",
                "stream": False,
                "options": {"temperature": 0.3, "num_ctx": 2048, "num_predict": 256},
            },
            timeout=10.0,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
    except Exception as e:
        logger.warning(f"Ollama response generation failed: {e}")

    # Try OpenAI
    if OPENAI_API_KEY:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
            completion = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=256,
                temperature=0.3,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"OpenAI response generation failed: {e}")

    # Fallback to template
    return _generate_response_from_template(intent, entities)


def _should_escalate(user_text: str, intent_confidence: float) -> Optional[str]:
    """
    Determine if escalation to a human agent is needed.

    Returns escalation reason string if escalation needed, else None.
    """
    text_lower = user_text.lower()

    # Explicit request for human
    if any(kw in text_lower for kw in ESCALATION_KEYWORDS):
        return "Customer explicitly requested human agent"

    # Low classifier confidence
    if intent_confidence < ESCALATION_CONFIDENCE_THRESHOLD:
        return f"Low intent confidence ({intent_confidence:.0%}) — routing to human for safety"

    return None


# ---------------------------------------------------------------------------
# Voice State Machine
# ---------------------------------------------------------------------------

class VoiceStateMachine:
    """
    Multi-turn voice conversation manager.

    Tracks conversation state, accumulated entities, intent history,
    and manages the escalation flow.

    Usage:
        sm = VoiceStateMachine()
        ctx = sm.new_session()
        response_text, ctx = await sm.handle_turn(ctx, transcribed_text, intent_result, entities)
    """

    def new_session(self) -> ConversationContext:
        """Create a new conversation context."""
        ctx = ConversationContext()
        ctx.state = ConversationState.IDLE
        logger.info(f"[StateMachine] New session: {ctx.session_id}")
        return ctx

    async def handle_turn(
        self,
        ctx: ConversationContext,
        user_text: str,
        intent: str,
        intent_confidence: float,
        entities: Dict[str, Any],
    ) -> tuple[str, ConversationContext]:
        """
        Process one turn of the conversation.

        Args:
            ctx: Current conversation context.
            user_text: Transcribed user text.
            intent: Classified intent.
            intent_confidence: Intent classification confidence (0-1).
            entities: Extracted entities dict.

        Returns:
            (response_text, updated_context)
        """
        start = time.time()
        ctx.state = ConversationState.PROCESSING

        # Check turn limit
        if ctx.turn_count >= MAX_TURNS:
            ctx.state = ConversationState.ESCALATING
            ctx.escalated = True
            ctx.escalation_reason = f"Maximum conversation turns ({MAX_TURNS}) reached"
            return (
                "I'm going to connect you with a senior support specialist who can better assist you. "
                "Please hold for one moment.",
                ctx
            )

        # Update accumulated context
        ctx.intent = intent
        ctx.entities.update({k: v for k, v in entities.items() if v is not None})

        # Check for escalation
        escalation_reason = _should_escalate(user_text, intent_confidence)
        if escalation_reason:
            ctx.state = ConversationState.ESCALATING
            ctx.escalated = True
            ctx.escalation_reason = escalation_reason
            logger.info(f"[StateMachine] Escalating: {escalation_reason}")
            response_text = (
                "I want to make sure you get the best possible assistance. "
                "Let me connect you with one of our specialist agents who can help you further. "
                "Please hold for just a moment."
            )
        else:
            # Generate response
            response_text = await _generate_response_llm(
                user_text=user_text,
                intent=intent,
                entities=ctx.entities,
                history=ctx.history,
            )
            ctx.state = ConversationState.RESPONDING

        # Check if clarification is needed
        needs_clarification = (
            intent == "tracking" and not ctx.entities.get("order_id") and
            ctx.turn_count < 2
        )
        if needs_clarification and not ctx.escalated:
            ctx.state = ConversationState.WAITING_CLARIFICATION

        # Record turn
        elapsed_ms = int((time.time() - start) * 1000)
        turn = Turn(
            turn_id=ctx.turn_count + 1,
            user_text=user_text,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities,
            bot_response=response_text,
            state=ctx.state,
            latency_ms=elapsed_ms,
        )
        ctx.turns.append(turn)
        ctx.history.append({"user": user_text, "bot": response_text})
        ctx.total_latency_ms += elapsed_ms

        if not ctx.escalated:
            ctx.state = ConversationState.IDLE

        logger.info(
            f"[StateMachine] Turn {ctx.turn_count}: "
            f"intent={intent} ({intent_confidence:.0%}), "
            f"state={ctx.state.value}, "
            f"latency={elapsed_ms}ms"
        )

        return response_text, ctx

    def is_resolved(self, ctx: ConversationContext) -> bool:
        """Estimate if the conversation was resolved (heuristic)."""
        if ctx.escalated:
            return False
        if ctx.turn_count == 0:
            return False
        # Check if last response contained resolution signals
        last = ctx.last_turn
        if last:
            resolution_signals = ["thank you", "is there anything else", "glad I could",
                                   "resolved", "completed", "processed"]
            return any(sig in last.bot_response.lower() for sig in resolution_signals)
        return False
