from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_code_dict_query_service
from app.services import CodeDictOption, CodeDictQueryService

router = APIRouter(prefix="/code-dicts")


class CodeDictOptionResponse(BaseModel):
    code: int
    name: str
    category: str


@router.get("", response_model=list[CodeDictOptionResponse])
def list_code_dict_options(
    category: str = Query(...),
    service: CodeDictQueryService = Depends(get_code_dict_query_service),
) -> list[CodeDictOptionResponse]:
    try:
        result = service.list_options(category)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [_serialize_option(item) for item in result]


def _serialize_option(option: CodeDictOption) -> CodeDictOptionResponse:
    return CodeDictOptionResponse(code=option.code, name=option.name, category=option.category)
