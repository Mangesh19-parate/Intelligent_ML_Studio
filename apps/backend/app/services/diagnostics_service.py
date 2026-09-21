from uuid import UUID
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.dataset import Dataset
from app.models.recommendation import Recommendation
from app.repositories.project_repository import ProjectRepository
from app.repositories.dataset_repository import DatasetRepository

class DiagnosticsService:
    """
    Diagnostics & Recommendations Service (SRS §2.16).
    Generates structured, traceable recommendations with all five mandatory fields:
    finding, evidence, recommended_action, risk_note, confidence.
    """

    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.dataset_repo = DatasetRepository(db)

    def generate_dqi_recommendations(
        self,
        dataset_id: UUID | str,
        column_stats: dict,
        dqi_report: dict,
        duplicate_count: int,
        total_rows: int
    ) -> list[dict]:
        dataset = self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        project_id = dataset.project_id

        # 1. Clear existing recommendations for this project to ensure idempotency
        self.db.query(Recommendation).filter(Recommendation.project_id == project_id).delete()

        sub_scores = dqi_report.get("sub_scores", {})
        recommendations_to_add: list[Recommendation] = []
        now = datetime.now(timezone.utc)

        # 2. Check Missingness Score & per-column missing values
        missing_score = sub_scores.get("missingness")
        for col_name, stats in column_stats.items():
            missing_pct = stats.get("missing_pct", 0.0)
            missing_cnt = stats.get("missing_count", 0)
            if missing_pct > 0:
                col_type = stats.get("type", "unknown")
                skew = stats.get("skew")
                if col_type == "numeric":
                    if skew is not None and abs(skew) > 1.0:
                        evidence_str = f"Distribution is skewed (skewness={skew:.2f}) across {total_rows} development rows."
                        action_str = f"Apply median imputation for `{col_name}` during Day 4 transformation."
                        risk_str = "Median imputation may attenuate feature variance if missingness is high."
                        conf_str = "HIGH" if missing_pct > 20 else "MEDIUM"
                    else:
                        skew_val = skew if skew is not None else 0.0
                        evidence_str = f"Distribution is approximately symmetric (skewness={skew_val:.2f}) across {total_rows} development rows."
                        action_str = f"Apply mean or KNN imputation for `{col_name}` during Day 4 transformation."
                        risk_str = "Mean imputation reduces variance and underestimates uncertainty."
                        conf_str = "HIGH" if missing_pct > 20 else "MEDIUM"
                elif col_type == "categorical":
                    evidence_str = f"Categorical column with {stats.get('unique_count', 0)} unique levels."
                    action_str = f"Impute missing values in `{col_name}` with mode or a distinct 'Missing' category."
                    risk_str = "Mode imputation may artificially inflate the most frequent category frequency."
                    conf_str = "HIGH"
                else:
                    evidence_str = f"Datetime or text feature with {missing_cnt} missing entries."
                    action_str = f"Forward-fill or drop missing rows for `{col_name}` in transformation stage."
                    risk_str = "Row dropping reduces total sample size available for training."
                    conf_str = "MEDIUM"

                recommendations_to_add.append(
                    Recommendation(
                        project_id=project_id,
                        finding=f"{missing_pct:.1f}% ({missing_cnt} cells) missing in `{col_name}`",
                        evidence=evidence_str,
                        recommended_action=action_str,
                        risk_note=risk_str,
                        confidence=conf_str,
                        status="SUGGESTED",
                        created_at=now
                    )
                )

        # 3. Check Duplicate Rate Score
        dup_score = sub_scores.get("duplicate_rate", 100.0)
        if duplicate_count > 0:
            dup_pct = (duplicate_count / total_rows * 100.0) if total_rows > 0 else 0.0
            recommendations_to_add.append(
                Recommendation(
                    project_id=project_id,
                    finding=f"Identified {duplicate_count} exact duplicate rows ({dup_pct:.1f}% of Development partition)",
                    evidence=f"Duplicate Rate Score is {dup_score:.1f}/100 across {total_rows} development rows.",
                    recommended_action="Execute automated deduplication to retain single distinct records on Day 4.",
                    risk_note="Ensure duplicate rows are not legitimate repeated transaction logs before removing.",
                    confidence="HIGH",
                    status="SUGGESTED",
                    created_at=now
                )
            )

        # 4. Check Outlier Prevalence
        outlier_score = sub_scores.get("outlier_prevalence")
        if outlier_score is not None and outlier_score < 100.0:
            for col_name, stats in column_stats.items():
                if stats.get("type") == "numeric":
                    outlier_cnt = stats.get("outlier_count", 0)
                    outlier_pct = stats.get("outlier_pct", 0.0)
                    if outlier_cnt > 0:
                        q25 = stats.get("q25")
                        q75 = stats.get("q75")
                        recommendations_to_add.append(
                            Recommendation(
                                project_id=project_id,
                                finding=f"{outlier_pct:.1f}% ({outlier_cnt} values) detected as IQR outliers in `{col_name}`",
                                evidence=f"IQR range is [{q25:.2f} to {q75:.2f}] with skew={stats.get('skew', 0.0):.2f}.",
                                recommended_action=f"Apply RobustScaler or 1.5*IQR winsorization to `{col_name}` on Day 4.",
                                risk_note="Clipping genuine extreme events can impair predictive power if outliers are non-spurious.",
                                confidence="MEDIUM",
                                status="SUGGESTED",
                                created_at=now
                            )
                        )

        # 5. Check Type Consistency / Mixed Dtypes
        type_score = sub_scores.get("type_consistency", 100.0)
        for col_name, stats in column_stats.items():
            if stats.get("is_mixed_type", False):
                recommendations_to_add.append(
                    Recommendation(
                        project_id=project_id,
                        finding=f"Mixed or ambiguous data types detected in `{col_name}`",
                        evidence=f"Column contains mixed representations (e.g. numeric strings with alphabetic entries).",
                        recommended_action=f"Apply explicit schema casting and text cleaning to `{col_name}` during Day 4 transformation.",
                        risk_note="Forced casting might coerce invalid entries to null/NaN if unhandled.",
                        confidence="HIGH",
                        status="SUGGESTED",
                        created_at=now
                    )
                )

        # Persist all recommendations
        if recommendations_to_add:
            self.db.add_all(recommendations_to_add)
            self.db.commit()

        # Format return list
        result = []
        for r in recommendations_to_add:
            result.append({
                "id": str(r.id),
                "project_id": str(r.project_id),
                "finding": r.finding,
                "evidence": r.evidence,
                "recommended_action": r.recommended_action,
                "risk_note": r.risk_note,
                "confidence": r.confidence,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        return result
