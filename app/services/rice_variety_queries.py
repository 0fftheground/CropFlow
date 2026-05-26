from __future__ import annotations

from dataclasses import dataclass

from app.repositories import RiceVarietyRepository


@dataclass(slots=True)
class RiceVarietyOption:
    id: int
    name: str
    culti_type_code: int | None
    sub_type_code: int | None


class RiceVarietyQueryService:
    def __init__(self, rice_variety_repository: RiceVarietyRepository) -> None:
        self.rice_variety_repository = rice_variety_repository

    def search(self, query: str | None, *, limit: int = 20) -> list[RiceVarietyOption]:
        if limit < 1 or limit > 100:
            raise ValueError("Rice variety search limit must be between 1 and 100.")
        return [
            RiceVarietyOption(
                id=item.id,
                name=item.name,
                culti_type_code=item.culti_type_code,
                sub_type_code=item.sub_type_code,
            )
            for item in self.rice_variety_repository.search_by_name(query, limit=limit)
        ]
