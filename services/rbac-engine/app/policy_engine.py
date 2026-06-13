"""
RBAC Policy Engine — role-based access control for RAG document retrieval.

Enterprise Security Model:
  - Documents have metadata: {category, sensitivity, allowed_roles}
  - Users have a role: admin | lawyer | doctor | engineer | analyst | viewer
  - Policy: document accessible if user.role in document.allowed_roles
  - Admin has access to everything

Role Hierarchy:
  admin > lawyer, doctor, engineer > analyst > viewer
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role Definitions
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    ADMIN = "admin"
    LAWYER = "lawyer"
    DOCTOR = "doctor"
    ENGINEER = "engineer"
    ANALYST = "analyst"
    VIEWER = "viewer"


class DocumentSensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    """Represents an authenticated user making a RAG query."""
    user_id: str
    role: UserRole
    tenant_id: str
    email: Optional[str] = None
    additional_permissions: List[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Metadata attached to each document in the knowledge base."""
    document_id: str
    category: str                    # e.g. "legal", "medical", "engineering"
    sensitivity: DocumentSensitivity
    allowed_roles: List[UserRole]    # Roles permitted to access this document
    owner_id: Optional[str] = None
    tenant_id: Optional[str] = None


class AccessDecision(BaseModel):
    """Result of a policy check."""
    allowed: bool
    document_id: str
    user_id: str
    user_role: UserRole
    reason: str
    required_roles: List[UserRole]


# ---------------------------------------------------------------------------
# Default Policy Configuration
# ---------------------------------------------------------------------------

DEFAULT_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    UserRole.ADMIN: ["*"],                          # All categories
    UserRole.LAWYER: ["legal", "contracts", "compliance", "public"],
    UserRole.DOCTOR: ["medical", "clinical", "research", "public"],
    UserRole.ENGINEER: ["engineering", "technical", "code", "architecture", "public"],
    UserRole.ANALYST: ["reports", "analytics", "public"],
    UserRole.VIEWER: ["public"],
}

# Sensitivity access matrix: role → max sensitivity level accessible
SENSITIVITY_ACCESS: Dict[UserRole, Set[DocumentSensitivity]] = {
    UserRole.ADMIN: {
        DocumentSensitivity.PUBLIC,
        DocumentSensitivity.INTERNAL,
        DocumentSensitivity.CONFIDENTIAL,
        DocumentSensitivity.RESTRICTED,
    },
    UserRole.LAWYER: {
        DocumentSensitivity.PUBLIC,
        DocumentSensitivity.INTERNAL,
        DocumentSensitivity.CONFIDENTIAL,
    },
    UserRole.DOCTOR: {
        DocumentSensitivity.PUBLIC,
        DocumentSensitivity.INTERNAL,
        DocumentSensitivity.CONFIDENTIAL,
    },
    UserRole.ENGINEER: {
        DocumentSensitivity.PUBLIC,
        DocumentSensitivity.INTERNAL,
        DocumentSensitivity.CONFIDENTIAL,
    },
    UserRole.ANALYST: {
        DocumentSensitivity.PUBLIC,
        DocumentSensitivity.INTERNAL,
    },
    UserRole.VIEWER: {
        DocumentSensitivity.PUBLIC,
    },
}


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

class PolicyEngine:
    """
    Enterprise RBAC policy engine for document-level access control.

    Implements a deny-by-default policy: access is granted only if:
      1. User role is in document.allowed_roles, OR user is admin
      2. User has access to the document's sensitivity level
      3. (Optional) Same tenant_id if multi-tenant isolation is enabled

    Usage:
        engine = PolicyEngine(multi_tenant=True)
        decision = engine.check_access(user, document_metadata)
        if decision.allowed:
            # proceed with retrieval
    """

    def __init__(self, multi_tenant: bool = True):
        self.multi_tenant = multi_tenant

    def check_access(
        self,
        user: UserContext,
        document: DocumentMetadata,
    ) -> AccessDecision:
        """
        Evaluates whether a user can access a document.

        Args:
            user: The authenticated user context.
            document: The document's access metadata.

        Returns:
            AccessDecision with allowed=True/False and reason.
        """
        # 1. Admin has unrestricted access
        if user.role == UserRole.ADMIN:
            return AccessDecision(
                allowed=True,
                document_id=document.document_id,
                user_id=user.user_id,
                user_role=user.role,
                reason="Admin role: unrestricted access",
                required_roles=document.allowed_roles,
            )

        # 2. Multi-tenant isolation
        if self.multi_tenant and document.tenant_id and user.tenant_id != document.tenant_id:
            reason = f"Tenant mismatch: user={user.tenant_id}, doc={document.tenant_id}"
            logger.warning(f"[RBAC] DENIED (tenant): user={user.user_id}, doc={document.document_id}")
            return AccessDecision(
                allowed=False,
                document_id=document.document_id,
                user_id=user.user_id,
                user_role=user.role,
                reason=reason,
                required_roles=document.allowed_roles,
            )

        # 3. Check role-level access (document must explicitly allow this role)
        if user.role not in document.allowed_roles:
            reason = (
                f"Role '{user.role}' not in document allowed_roles: "
                f"{[r.value for r in document.allowed_roles]}"
            )
            logger.info(f"[RBAC] DENIED (role): user={user.user_id}, doc={document.document_id}")
            return AccessDecision(
                allowed=False,
                document_id=document.document_id,
                user_id=user.user_id,
                user_role=user.role,
                reason=reason,
                required_roles=document.allowed_roles,
            )

        # 4. Check sensitivity level
        accessible_sensitivities = SENSITIVITY_ACCESS.get(user.role, set())
        if document.sensitivity not in accessible_sensitivities:
            reason = (
                f"Role '{user.role}' cannot access '{document.sensitivity}' sensitivity. "
                f"Max allowed: {[s.value for s in accessible_sensitivities]}"
            )
            logger.info(f"[RBAC] DENIED (sensitivity): user={user.user_id}, doc={document.document_id}")
            return AccessDecision(
                allowed=False,
                document_id=document.document_id,
                user_id=user.user_id,
                user_role=user.role,
                reason=reason,
                required_roles=document.allowed_roles,
            )

        # All checks passed
        logger.debug(f"[RBAC] ALLOWED: user={user.user_id}, doc={document.document_id}")
        return AccessDecision(
            allowed=True,
            document_id=document.document_id,
            user_id=user.user_id,
            user_role=user.role,
            reason=f"Role '{user.role}' has access to '{document.category}' ({document.sensitivity})",
            required_roles=document.allowed_roles,
        )

    def filter_documents(
        self,
        user: UserContext,
        documents: List[DocumentMetadata],
    ) -> List[DocumentMetadata]:
        """
        Filters a list of documents to only those the user can access.

        Args:
            user: The authenticated user.
            documents: List of documents to filter.

        Returns:
            Subset of documents the user is permitted to access.
        """
        accessible = []
        denied_count = 0
        for doc in documents:
            decision = self.check_access(user, doc)
            if decision.allowed:
                accessible.append(doc)
            else:
                denied_count += 1

        logger.info(
            f"[RBAC] filter_documents: user={user.user_id} role={user.role} | "
            f"accessible={len(accessible)}/{len(documents)}, denied={denied_count}"
        )
        return accessible

    def get_allowed_categories(self, role: UserRole) -> List[str]:
        """Returns the document categories a role can access."""
        if role == UserRole.ADMIN:
            return ["*"]
        return DEFAULT_ROLE_PERMISSIONS.get(role, [])
