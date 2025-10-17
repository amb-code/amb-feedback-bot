import asyncio

import click

from feedbackbot.core.db import get_engine, Base


@click.command(short_help='Create DB')
def create_db():
    click.echo('Creating the database')

    async def __inner():
        engine = get_engine()
        async with engine.begin() as con:
            await con.run_sync(Base.metadata.create_all)

    asyncio.run(__inner())


@click.command(short_help='Create DB')
def clean_db():
    click.echo('Cleaning the database')

    async def __inner():
        engine = get_engine()
        async with engine.begin() as con:
            for tbl in reversed(Base.metadata.sorted_tables):
                await con.execute(tbl.delete())

    asyncio.run(__inner())

