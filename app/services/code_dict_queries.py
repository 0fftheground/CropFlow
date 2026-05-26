from __future__ import annotations

from dataclasses import dataclass

from app.repositories import CodeDictRepository


@dataclass(slots=True)
class CodeDictOption:
    code: int
    name: str
    category: str


class CodeDictQueryService:
    def __init__(self, code_dict_repository: CodeDictRepository) -> None:
        self.code_dict_repository = code_dict_repository

    def list_options(self, category: str) -> list[CodeDictOption]:
        if not category.strip():
            raise ValueError("Code dict category is required.")
        return [
            CodeDictOption(
                code=item.code,
                name=item.code_name,
                category=item.category,
            )
            for item in self.code_dict_repository.list_active_by_category(category.strip())
        ]
