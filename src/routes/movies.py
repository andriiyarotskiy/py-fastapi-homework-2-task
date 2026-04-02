from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db, MovieModel
from database.models import GenreModel, ActorModel, LanguageModel, CountryModel
from routes.helpers import get_or_create_many, get_or_create_country
from schemas.movies import (
    MovieListResponseSchema,
    MovieDetailSchema,
    MovieCreateSchema,
    MovieUpdateSchema,
)

router = APIRouter(prefix="/movies")


@router.get("/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, MovieListResponseSchema]:
    result = await db.execute(
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    movies = result.scalars().all()
    if not movies:
        raise HTTPException(status_code=404, detail="No movies found.")
    total_items = await db.scalar(select(func.count(MovieModel.id)))
    total_pages = (total_items + per_page - 1) // per_page
    prev_page = None
    if page > 1:
        prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}"
    next_page = None
    if page < total_pages:
        next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}"
    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_items": total_items,
        "total_pages": total_pages,
    }


@router.post("/", status_code=201, response_model=MovieDetailSchema)
async def create_movie(
    payload: MovieCreateSchema, db: AsyncSession = Depends(get_db)
) -> MovieModel:
    async with db.begin():
        # duplicate check
        result = await db.execute(
            select(MovieModel).filter(
                MovieModel.name == payload.name,
                MovieModel.date == payload.date,
            )
        )
        existing_movie = result.scalar_one_or_none()
        if existing_movie:
            raise HTTPException(
                status_code=409,
                detail=f"A movie with the name '{payload.name}' and release date '{payload.date}' already exists.",
            )
        # create/link related entities (assume these return ORM objects attached to `db`)
        genres = await get_or_create_many(db, GenreModel, payload.genres or [])
        actors = await get_or_create_many(db, ActorModel, payload.actors or [])
        languages = await get_or_create_many(db, LanguageModel, payload.languages or [])
        country = None
        if payload.country:
            country = await get_or_create_country(db, payload.country)
        # create movie and set relations
        movie = MovieModel(
            name=payload.name,
            date=payload.date,
            score=payload.score,
            overview=payload.overview,
            status=payload.status,
            budget=payload.budget,
            revenue=payload.revenue,
            country=country,
        )
        movie.genres = genres
        movie.actors = actors
        movie.languages = languages
        db.add(movie)
        # IMPORTANT: ensure DB INSERTs are flushed and ORM attributes (including relationships)
        # are loaded while session/transaction is still open.
        await db.flush()  # push INSERTs, populate movie.id
        # Option A: explicit refresh of movie and its relationships
        await db.refresh(
            movie, ["country", "genres", "actors", "languages"]
        )  # refresh scalar attributes
        # await db.refresh(movie, ["country", "genres", "actors", "languages"])
    return movie


@router.get("/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> MovieModel:
    result = await db.execute(
        select(MovieModel)
        .options(
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
            selectinload(MovieModel.country),
        )
        .where(MovieModel.id == movie_id)
    )

    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )
    return movie


@router.delete("/{movie_id}/", status_code=204)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )
    await db.delete(movie)
    await db.commit()
    return None


@router.patch("/{movie_id}/", status_code=200)
async def update_movie(
    movie_id: int, payload: MovieUpdateSchema, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(MovieModel).where(MovieModel.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=404, detail="Movie with the given ID was not found."
        )

    movie_data = payload.model_dump(exclude_unset=True)
    for key, value in movie_data.items():
        setattr(movie, key, value)
    await db.commit()
    return {"detail": "Movie updated successfully."}
