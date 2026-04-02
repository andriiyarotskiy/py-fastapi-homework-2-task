from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from database.models import CountryModel


async def get_or_create_country(db: AsyncSession, code: str) -> CountryModel:
    result = await db.execute(select(CountryModel).filter(CountryModel.code == code))
    country = result.scalar_one_or_none()
    if country:
        return country
    country = CountryModel(
        code=code, name=None
    )  # name can be searched by code if there is a map
    db.add(country)
    await db.flush()  # to get the id to the commit
    return country


async def get_or_create_many(session: AsyncSession, Model, names: list[str]):
    names = list({n.strip() for n in names if n})  # Unique clean names
    if not names:
        return []
    # 1) We get existing
    q = select(Model).where(Model.name.in_(names))
    result = await session.execute(q)
    existing = {obj.name: obj for obj in result.scalars().all()}
    # 2) Identify the missing ones and create them as a batch
    missing = [n for n in names if n not in existing]
    new_objs = []
    if missing:
        for name in missing:
            new_objs.append(Model(name=name))
        session.add_all(new_objs)
        try:
            await session.flush()  # to get id (and prepare INSERT)
        except IntegrityError:
            # possible race - someone created an entry between select and insert
            await session.rollback()
            # We re-receive all
            q = select(Model).where(Model.name.in_(names))
            result = await session.execute(q)
            existing = {obj.name: obj for obj in result.scalars().all()}
            return list(existing.values())
        # Add new ones to existing map
        for obj in new_objs:
            existing[obj.name] = obj
    return list(existing.values())
