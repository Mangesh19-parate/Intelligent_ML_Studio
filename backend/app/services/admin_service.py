from datetime import datetime, timezone
from uuid import UUID as PyUUID, uuid4
from typing import Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.role import Role
from app.models.permission import Permission
from app.models.user_permission_override import UserPermissionOverride
from app.models.deployment_gate import DeploymentGate
from app.models.prediction_log import PredictionLog
from app.models.deployment import Deployment
from app.core.security import get_password_hash
from app.config.contract import (
    ALGORITHM_SET,
    METRICS,
    PRIMARY_METRIC_DEFAULTS,
    FEATURE_SELECTION_DEFAULTS,
    TaskType,
)
from app.schemas.admin import (
    UserAdminResponse,
    PermissionOverrideDetail,
    UserCreateRequest,
    UserUpdateRequest,
    PermissionOverrideRequest,
    AlgorithmCatalogItem,
    MetricCatalogItem,
    FeatureSelectionCatalog,
    AuditLogItem,
)


class AdminService:
    """
    Service layer for Admin Operations (Day 6).
    Handles:
    1. User Directory & Role administration.
    2. Granular per-user Permission Overrides (specifically DEPLOY override).
    3. Algorithm, Metric, and Feature Selection Catalogs.
    4. Multi-entity Unified System Audit Trail.
    """

    def __init__(self, db: Session):
        self.db = db

    def _compute_effective_permissions(self, user: User) -> list[str]:
        effective: set[str] = set()
        if user.role and user.role.permissions:
            for p in user.role.permissions:
                key = p.permission_key if hasattr(p, "permission_key") else str(p)
                effective.add(key)
        
        if hasattr(user, "permission_overrides") and user.permission_overrides:
            for override in user.permission_overrides:
                if override.is_granted:
                    effective.add(override.permission_key)
                else:
                    effective.discard(override.permission_key)
        
        return sorted(list(effective))

    def _serialize_user(self, user: User) -> UserAdminResponse:
        overrides = [
            PermissionOverrideDetail(
                permission_key=o.permission_key,
                is_granted=o.is_granted,
                created_at=o.created_at,
            )
            for o in (user.permission_overrides or [])
        ]
        return UserAdminResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role_name=user.role.role_name if user.role else "VIEWER",
            role_id=user.role_id,
            is_active=user.is_active,
            created_at=user.created_at,
            effective_permissions=self._compute_effective_permissions(user),
            permission_overrides=overrides,
        )

    def list_users(self) -> list[UserAdminResponse]:
        users = self.db.query(User).order_by(User.created_at.asc()).all()
        return [self._serialize_user(u) for u in users]

    def create_user(self, payload: UserCreateRequest) -> UserAdminResponse:
        existing = self.db.query(User).filter(User.email == payload.email.lower().strip()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User with email '{payload.email}' already exists"
            )

        role = self.db.query(Role).filter(Role.role_name == payload.role_name.upper().strip()).first()
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role '{payload.role_name}' does not exist"
            )

        new_user = User(
            id=uuid4(),
            full_name=payload.full_name.strip(),
            email=payload.email.lower().strip(),
            password_hash=get_password_hash(payload.password),
            role_id=role.id,
            is_active=True,
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        return self._serialize_user(new_user)

    def update_user(self, user_id: PyUUID | str, payload: UserUpdateRequest) -> UserAdminResponse:
        uid = PyUUID(str(user_id)) if not isinstance(user_id, PyUUID) else user_id
        user = self.db.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()

        if payload.is_active is not None:
            user.is_active = payload.is_active

        if payload.role_name is not None:
            role = self.db.query(Role).filter(Role.role_name == payload.role_name.upper().strip()).first()
            if not role:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{payload.role_name}' not found")
            user.role_id = role.id

        self.db.commit()
        self.db.refresh(user)
        return self._serialize_user(user)

    def set_permission_override(
        self,
        user_id: PyUUID | str,
        payload: PermissionOverrideRequest
    ) -> UserAdminResponse:
        """
        Sets or updates a granular permission override for a user.
        E.g. granting DEPLOY override to an ML_ENGINEER or VIEWER,
        or revoking DEPLOY from a DEPLOYMENT_MANAGER.
        """
        uid = PyUUID(str(user_id)) if not isinstance(user_id, PyUUID) else user_id
        user = self.db.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        perm_key = payload.permission_key.upper().strip()

        # Check existing override
        override = (
            self.db.query(UserPermissionOverride)
            .filter(
                UserPermissionOverride.user_id == uid,
                UserPermissionOverride.permission_key == perm_key
            )
            .first()
        )

        if override:
            override.is_granted = payload.is_granted
        else:
            override = UserPermissionOverride(
                id=uuid4(),
                user_id=uid,
                permission_key=perm_key,
                is_granted=payload.is_granted,
            )
            self.db.add(override)

        self.db.commit()
        self.db.refresh(user)
        return self._serialize_user(user)

    def delete_permission_override(
        self,
        user_id: PyUUID | str,
        permission_key: str
    ) -> UserAdminResponse:
        """
        Removes an override so the user reverts to their role's baseline permission.
        """
        uid = PyUUID(str(user_id)) if not isinstance(user_id, PyUUID) else user_id
        user = self.db.query(User).filter(User.id == uid).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        perm_key = permission_key.upper().strip()
        override = (
            self.db.query(UserPermissionOverride)
            .filter(
                UserPermissionOverride.user_id == uid,
                UserPermissionOverride.permission_key == perm_key
            )
            .first()
        )

        if override:
            self.db.delete(override)
            self.db.commit()
            self.db.refresh(user)

        return self._serialize_user(user)

    def get_algorithm_catalog(self) -> list[AlgorithmCatalogItem]:
        items: list[AlgorithmCatalogItem] = []
        for algo_id, meta in ALGORITHM_SET.items():
            items.append(
                AlgorithmCatalogItem(
                    id=meta.id,
                    display_name=meta.display_name,
                    task_type=meta.task_type.value,
                    is_baseline=meta.is_baseline,
                    sklearn_class=meta.sklearn_class,
                    description=meta.description,
                )
            )
        return items

    def get_metric_catalog(self) -> list[MetricCatalogItem]:
        items: list[MetricCatalogItem] = []
        for task_type, metrics_map in METRICS.items():
            default_metric = PRIMARY_METRIC_DEFAULTS.get(task_type)
            for m_key, m_info in metrics_map.items():
                items.append(
                    MetricCatalogItem(
                        id=m_key,
                        display_name=m_info["display_name"],
                        task_type=task_type.value,
                        direction=m_info["direction"].value if m_info["direction"] else None,
                        is_primary_candidate=m_info["is_primary_candidate"],
                        is_default=(m_key == default_metric),
                    )
                )
        return items

    def get_feature_selection_catalog(self) -> FeatureSelectionCatalog:
        return FeatureSelectionCatalog(
            strategy=FEATURE_SELECTION_DEFAULTS["strategy"],
            alpha=FEATURE_SELECTION_DEFAULTS["alpha"],
            k_min=FEATURE_SELECTION_DEFAULTS["k_min"],
            k_max=FEATURE_SELECTION_DEFAULTS["k_max"],
            min_applied_methods=FEATURE_SELECTION_DEFAULTS["min_applied_methods"],
            active_methods=FEATURE_SELECTION_DEFAULTS["active_methods"],
            deferred_methods=FEATURE_SELECTION_DEFAULTS["deferred_methods"],
        )

    def get_audit_logs(
        self,
        event_type: Optional[str] = None,
        limit: int = 100,
        search: Optional[str] = None
    ) -> list[AuditLogItem]:
        """
        Aggregates multi-table system governance audit events.
        """
        events: list[AuditLogItem] = []

        # 1. Gate evaluations & approvals
        gates = (
            self.db.query(DeploymentGate)
            .order_by(DeploymentGate.evaluated_at.desc())
            .limit(limit)
            .all()
        )
        for g in gates:
            status_val = "PASSED" if g.gate_passed else "BLOCKED"
            events.append(
                AuditLogItem(
                    id=str(g.id),
                    event_type="GATE_EVALUATION",
                    timestamp=g.evaluated_at or datetime.now(timezone.utc),
                    actor=str(g.approved_by) if g.approved_by else "SYSTEM_AUTOMATION",
                    target_id=str(g.model_id),
                    status=status_val,
                    summary=f"Deployment Gate evaluation for Model {str(g.model_id)[:8]}: {status_val}",
                    details={
                        "model_id": str(g.model_id),
                        "gate_passed": g.gate_passed,
                        "approved_by": str(g.approved_by) if g.approved_by else None,
                        "conditions": {
                            "locked_test_evaluated": g.locked_test_evaluated,
                            "schema_locked": g.schema_locked,
                            "artifact_verified": g.artifact_verified,
                            "lineage_complete": g.lineage_complete,
                            "performance_threshold_passed": g.performance_threshold_passed,
                            "user_approved": g.user_approved,
                        },
                    },
                )
            )

        # 2. Prediction logs
        pred_logs = (
            self.db.query(PredictionLog)
            .order_by(PredictionLog.requested_at.desc())
            .limit(limit)
            .all()
        )
        for p in pred_logs:
            events.append(
                AuditLogItem(
                    id=str(p.id),
                    event_type="INFERENCE_REQUEST" if p.status == "SUCCESS" else "VALIDATION_FAILURE",
                    timestamp=p.requested_at or datetime.now(timezone.utc),
                    actor="INFERENCE_CLIENT",
                    target_id=str(p.deployment_id),
                    status=p.status,
                    summary=f"Inference request on Deployment {str(p.deployment_id)[:8]} ({p.latency_ms}ms, {p.payload_mode})",
                    details={
                        "request_id": str(p.request_id),
                        "deployment_id": str(p.deployment_id),
                        "payload_mode": p.payload_mode,
                        "schema_hash": p.schema_hash,
                        "latency_ms": p.latency_ms,
                        "explanation_requested": p.explanation_requested,
                        "explanation_latency_ms": p.explanation_latency_ms,
                        "status": p.status,
                    },
                )
            )

        # 3. User permission overrides
        overrides = (
            self.db.query(UserPermissionOverride)
            .order_by(UserPermissionOverride.created_at.desc())
            .limit(limit)
            .all()
        )
        for o in overrides:
            action = "GRANT" if o.is_granted else "REVOKE"
            events.append(
                AuditLogItem(
                    id=str(o.id),
                    event_type="PERMISSION_OVERRIDE",
                    timestamp=o.created_at or datetime.now(timezone.utc),
                    actor="ADMIN_ACTION",
                    target_id=str(o.user_id),
                    status=action,
                    summary=f"Permission {o.permission_key} {action}ed for User {str(o.user_id)[:8]}",
                    details={
                        "user_id": str(o.user_id),
                        "permission_key": o.permission_key,
                        "is_granted": o.is_granted,
                    },
                )
            )

        # Sort all aggregated events by timestamp descending
        events.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply filtering
        if event_type:
            event_type_upper = event_type.upper().strip()
            events = [e for e in events if e.event_type == event_type_upper]

        if search:
            s = search.lower().strip()
            events = [e for e in events if s in e.summary.lower() or s in e.status.lower() or s in str(e.target_id).lower()]

        return events[:limit]
