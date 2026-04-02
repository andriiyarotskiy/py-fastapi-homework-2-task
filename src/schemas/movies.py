import datetime
from typing import List, Optional

from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field, PositiveFloat, create_model

from database.models import MovieStatusEnum


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: datetime.date
    score: float
    overview: str


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: str | None = None
    next_page: str | None = None
    total_pages: int
    total_items: int


class MovieBaseSchema(BaseModel):
    name: str = Field(max_length=255)
    date: datetime.date = Field(lt=datetime.date.today() + relativedelta(years=1))
    score: PositiveFloat = Field(le=100, description="0..100")
    overview: str
    status: MovieStatusEnum
    budget: PositiveFloat
    revenue: PositiveFloat


class GenreReadSchema(BaseModel):
    id: int
    name: str


class ActorReadSchema(BaseModel):
    id: int
    name: str


class LanguageReadSchema(BaseModel):
    id: int
    name: str


class CountryReadSchema(BaseModel):
    id: int
    code: str
    name: str | None


class MovieDetailSchema(MovieBaseSchema):
    id: int
    name: str = Field(max_length=255)
    country: CountryReadSchema
    genres: List[GenreReadSchema]
    actors: List[ActorReadSchema]
    languages: List[LanguageReadSchema]


class MovieCreateSchema(MovieBaseSchema):
    country: str
    genres: List[str]
    actors: List[str]
    languages: List[str]


def make_optional(model):
    fields = {}
    for name, field in model.model_fields.items():
        fields[name] = (Optional[field.annotation], None)
    return create_model(model.__name__, **fields)


UpdateSchema = make_optional(MovieBaseSchema)


class MovieUpdateSchema(UpdateSchema):
    pass
