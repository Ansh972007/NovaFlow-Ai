from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class UnifiedResponse(BaseModel, Generic[T]):
    status_code: int = 200
    status_message: str = "SUCCESS"
    data: Optional[T] = None


def ok(data: Any = None, message: str = "SUCCESS") -> dict:
    return {"status_code": 200, "status_message": message, "data": data}


def fail(code: int, message: str, data: Any = None) -> dict:
    return {"status_code": code, "status_message": message, "data": data}


class UserLogin(BaseModel):
    user_name: str
    password: str


class UserCreate(BaseModel):
    user_name: str
    password: str


class AssistantCreate(BaseModel):
    name: str = Field(max_length=50)
    prompt: str = Field(min_length=20, max_length=4000)
    logo: str = ""


class AssistantUpdate(BaseModel):
    id: str
    name: Optional[str] = ""
    desc: Optional[str] = ""
    prompt: Optional[str] = ""


class AssistantKnowledgeUpdate(BaseModel):
    assistant_id: str
    knowledge_ids: List[int] = Field(default_factory=list)


class KnowledgeCreate(BaseModel):
    name: str
    description: str = ""
    model: Optional[str] = None
    type: int = 0


class ProcessFiles(BaseModel):
    knowledge_id: int
    file_list: List[dict]
    chunk_size: int = 1000
    chunk_overlap: int = 100


class WorkflowCreate(BaseModel):
    name: str = Field(max_length=80)
    desc: str = ""
    template_id: str = "rag"


class WorkflowUpdate(BaseModel):
    id: str
    name: Optional[str] = None
    desc: Optional[str] = None
    graph: Optional[dict] = None


class WorkflowRunRequest(BaseModel):
    workflow_id: str
    input: str = Field(min_length=1, max_length=4000)
