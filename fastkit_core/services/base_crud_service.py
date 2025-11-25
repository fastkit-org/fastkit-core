from typing import Generic, TypeVar, List, Optional, Any
from fastkit_core.database import Repository

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseCrudService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

    def __init__(self, repository: Repository):
        self.repository = repository

    def find(self, id: Any) -> Optional[ModelType]:
        return self.repository.get(id)

    def get_all(self) -> List[ModelType]:
        return self.repository.get_all()

    def filter(
            self,
            _limit: int | None = None,
            _offset: int | None = None,
            _order_by: str | None = None,
            **filters
    )-> List[ModelType]:
        return self.repository.filter(_limit=_limit, _offset=_offset, _order_by=_order_by, **filters)

    def paginate(
            self,
            page: int = 1,
            per_page: int = 20,
            **filters
    ) -> tuple[list[ModelType], dict[str, Any]]:
        return self.repository.paginate(page=page, per_page=per_page, **filters)

    def exists(self, **filters) -> bool:
        return self.repository.exists(**filters)

    def create(self, data: CreateSchemaType) -> ModelType:
        return self.repository.create(data=data.dict(), commit=True)

    def create_many(self, data: list[CreateSchemaType]) -> list[ModelType]:
        return self.repository.create_many(data_list=[item.dict() for item in data], commit=True)

    def update(self, id: Any, data: UpdateSchemaType) -> ModelType | None:
        return self.repository.update(id=id, data=data.dict(), commit=True)

    def update_many(
            self,
            filters: dict[str, Any],
            data: UpdateSchemaType
    ) -> int:
        return self.repository.update_many(filters=filters, data=data.dict(), commit=True)

    def delete(self, id: Any, force: bool = False) -> bool:
        return self.repository.delete(id=id, commit=True, force=force)

    def delete_many(self, filters: dict[str, Any]) -> int:
        return self.repository.delete_many(filters=filters, commit=True)
