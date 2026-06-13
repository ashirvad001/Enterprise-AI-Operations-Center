"""
RBAC Metadata Filter — translates RBAC policy decisions into vector DB query filters.

At query time, before executing vector similarity search, this module builds
a WHERE filter that restricts results to documents the user is permitted to see.

Supports:
  - pgvector (PostgreSQL WHERE clause via SQLAlchemy)
  - Weaviate (GraphQL where filter)
  - In-memory filter (for testing / mock mode)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .policy_engine import UserContext, UserRole, DocumentSensitivity, SENSITIVITY_ACCESS

logger = logging.getLogger(__name__)


class MetadataFilter:
    """
    Builds vector-DB-specific filter expressions based on RBAC policy.

    Usage:
        filter_builder = MetadataFilter()
        pg_filter = filter_builder.build_pgvector_filter(user)
        weaviate_filter = filter_builder.build_weaviate_filter(user)
    """

    def build_pgvector_filter(self, user: UserContext) -> Dict[str, Any]:
        """
        Builds a SQLAlchemy-compatible filter dict for pgvector queries.

        The RAG retriever applies this as a WHERE clause:
            SELECT ... FROM chunks c JOIN documents d ON ...
            WHERE d.category = ANY(:allowed_categories)
            AND d.sensitivity = ANY(:allowed_sensitivities)
            AND d.tenant_id = :tenant_id

        Returns:
            Dict with filter parameters.
        """
        if user.role == UserRole.ADMIN:
            # Admin: no restrictions
            return {
                "allowed_categories": None,       # None = no filter
                "allowed_sensitivities": None,
                "tenant_id": user.tenant_id,
            }

        # Get accessible sensitivities for this role
        accessible_sensitivities = [
            s.value for s in SENSITIVITY_ACCESS.get(user.role, set())
        ]

        # Get accessible categories (None means "all of this sensitivity")
        from .policy_engine import DEFAULT_ROLE_PERMISSIONS
        allowed_categories = DEFAULT_ROLE_PERMISSIONS.get(user.role, ["public"])

        return {
            "allowed_categories": allowed_categories,
            "allowed_sensitivities": accessible_sensitivities,
            "tenant_id": user.tenant_id,
            "user_role": user.role.value,
        }

    def build_weaviate_filter(self, user: UserContext) -> Dict[str, Any]:
        """
        Builds a Weaviate GraphQL where filter for hybrid search.

        Weaviate filter format:
        {
            "operator": "And",
            "operands": [
                {"path": ["category"], "operator": "ContainsAny", "valueString": [...categories]},
                {"path": ["sensitivity"], "operator": "ContainsAny", "valueString": [...]},
                {"path": ["tenantId"], "operator": "Equal", "valueString": "..."}
            ]
        }

        Returns:
            Weaviate-compatible where filter dict.
        """
        if user.role == UserRole.ADMIN:
            # Admin: only tenant filter
            return {
                "path": ["tenantId"],
                "operator": "Equal",
                "valueString": user.tenant_id,
            }

        from .policy_engine import DEFAULT_ROLE_PERMISSIONS
        allowed_categories = DEFAULT_ROLE_PERMISSIONS.get(user.role, ["public"])
        accessible_sensitivities = [
            s.value for s in SENSITIVITY_ACCESS.get(user.role, set())
        ]

        operands = [
            {
                "path": ["tenantId"],
                "operator": "Equal",
                "valueString": user.tenant_id,
            }
        ]

        # Add category filter (skip if admin wildcard)
        if "*" not in allowed_categories:
            operands.append({
                "path": ["category"],
                "operator": "ContainsAny",
                "valueTextArray": allowed_categories,
            })

        # Add sensitivity filter
        if accessible_sensitivities:
            operands.append({
                "path": ["sensitivity"],
                "operator": "ContainsAny",
                "valueTextArray": accessible_sensitivities,
            })

        return {
            "operator": "And",
            "operands": operands,
        }

    def filter_in_memory(
        self,
        user: UserContext,
        documents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Applies RBAC filtering to an in-memory list of documents.

        Each document dict must have:
          - 'category': str
          - 'sensitivity': str
          - 'allowed_roles': list[str]
          - 'tenant_id': str (optional)

        Used in mock/testing mode and as a post-retrieval safety net.
        """
        if user.role == UserRole.ADMIN:
            return documents

        from .policy_engine import DEFAULT_ROLE_PERMISSIONS
        allowed_categories = set(DEFAULT_ROLE_PERMISSIONS.get(user.role, ["public"]))
        accessible_sensitivities = {
            s.value for s in SENSITIVITY_ACCESS.get(user.role, set())
        }

        filtered = []
        for doc in documents:
            # Tenant check
            doc_tenant = doc.get("tenant_id")
            if doc_tenant and doc_tenant != user.tenant_id:
                continue

            # Role check
            doc_roles = doc.get("allowed_roles", [])
            if doc_roles and user.role.value not in doc_roles and "admin" not in doc_roles:
                continue

            # Category check
            doc_category = doc.get("category", "public")
            if "*" not in allowed_categories and doc_category not in allowed_categories:
                continue

            # Sensitivity check
            doc_sensitivity = doc.get("sensitivity", "public")
            if doc_sensitivity not in accessible_sensitivities:
                continue

            filtered.append(doc)

        logger.info(
            f"[MetadataFilter] in-memory: {len(filtered)}/{len(documents)} docs "
            f"accessible for role={user.role.value}"
        )
        return filtered
