from pydantic import BaseModel, Field


class HookInput(BaseModel):
    code: str = Field(default="", max_length=80)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=30000)
    hookType: str = Field(default="", max_length=120)
    product: str = Field(default="", max_length=200)
    audience: str = Field(default="", max_length=200)
    scene: str = Field(default="", max_length=200)
    referenceMaterial: str = Field(default="", max_length=10000)
    notes: str = Field(default="", max_length=10000)
    status: str = Field(default="待筛选", max_length=40)
    isExample: bool = False
    createdAt: str = Field(default="", max_length=40)
    version: int | None = Field(default=None, ge=1)


class ProductEntryInput(BaseModel):
    hookId: str = Field(min_length=1, max_length=80)
    code: str = Field(default="", max_length=80)
    title: str = Field(min_length=1, max_length=300)
    entryType: str = Field(default="", max_length=120)
    entryTime: str = Field(default="", max_length=80)
    transitionLogic: str = Field(default="", max_length=30000)
    sellingPoints: str = Field(default="", max_length=30000)
    visualDescription: str = Field(default="", max_length=30000)
    product: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=10000)
    status: str = Field(default="待筛选", max_length=40)
    isExample: bool = False
    createdAt: str = Field(default="", max_length=40)
    version: int | None = Field(default=None, ge=1)
