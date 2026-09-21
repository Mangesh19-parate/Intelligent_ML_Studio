from uuid import UUID as PyUUID
from sqlalchemy.orm import Session
from app.models.feature_importance_score import FeatureImportanceScore
from app.repositories.base import BaseRepository

class FeatureImportanceRepository(BaseRepository[FeatureImportanceScore]):
    def __init__(self, db: Session):
        super().__init__(FeatureImportanceScore, db)

    def get_by_project(self, project_id: PyUUID | str) -> list[FeatureImportanceScore]:
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass
        return (
            self.db.query(FeatureImportanceScore)
            .filter(FeatureImportanceScore.project_id == project_id)
            .order_by(FeatureImportanceScore.avg_rank_score.desc())
            .all()
        )

    def upsert_scores(
        self,
        project_id: PyUUID | str,
        scores: dict[str, float],
        default_selected: bool = True,
    ) -> list[FeatureImportanceScore]:
        """
        Upserts aggregated feature importance scores for a project.
        """
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass

        existing = {
            f.column_name: f
            for f in self.db.query(FeatureImportanceScore)
            .filter(FeatureImportanceScore.project_id == project_id)
            .all()
        }

        # Keep track of columns present in new scores
        incoming_cols = set(scores.keys())

        # Remove columns no longer present in incoming scores (if schema changed)
        for col, item in existing.items():
            if col not in incoming_cols:
                self.db.delete(item)

        results = []
        for col_name, score in scores.items():
            if col_name in existing:
                item = existing[col_name]
                item.avg_rank_score = round(score, 4)
                # Keep existing selection or set default if needed
                self.db.add(item)
                results.append(item)
            else:
                item = FeatureImportanceScore(
                    project_id=project_id,
                    column_name=col_name,
                    avg_rank_score=round(score, 4),
                    is_selected=default_selected,
                )
                self.db.add(item)
                results.append(item)

        self.db.commit()
        for r in results:
            self.db.refresh(r)

        return sorted(results, key=lambda x: x.avg_rank_score, reverse=True)

    def update_selection(
        self,
        project_id: PyUUID | str,
        threshold: float | None = None,
        selected_columns: list[str] | None = None,
    ) -> list[FeatureImportanceScore]:
        """
        Updates is_selected flag based on threshold or explicit list of selected column names.
        """
        if isinstance(project_id, str):
            try:
                project_id = PyUUID(project_id)
            except Exception:
                pass

        items = self.get_by_project(project_id)
        for item in items:
            if selected_columns is not None:
                item.is_selected = item.column_name in selected_columns
            elif threshold is not None:
                item.is_selected = float(item.avg_rank_score) >= float(threshold)
            self.db.add(item)

        self.db.commit()
        for item in items:
            self.db.refresh(item)

        return sorted(items, key=lambda x: x.avg_rank_score, reverse=True)
