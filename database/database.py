#!/usr/bin/env python3

# CoveBot: Discord bot for a simple interview gatekeeper
# Copyright (C) 2020 Starshine113 (Starshine System)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import psycopg2
import aiopg


DATABASE_VERSION = 5


async def init_dbconn(database_url):
    dbconn = DatabaseConn(database_url)
    await dbconn._init()
    return dbconn


class DatabaseConn:
    def __init__(self, database_url):
        self.database_url = database_url

    async def _init(self):
        self.pool = await aiopg.create_pool(self.database_url)
        await self.init_db_if_not_initialised()
        await self.update_db()

    async def create_interview(
        self, user_id: int, channel_id: int, welcome_message_id: int
    ):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO interviews (user_id, channel_id, welcome_message) VALUES (%s, %s, %s)",
                    (user_id, channel_id, welcome_message_id),
                )

    async def get_interview(self, user_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM interviews WHERE user_id = %s",
                    (user_id,),
                )
                return await cur.fetchone()

    async def get_interview_from_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM interviews WHERE channel_id = %s",
                    (channel_id,),
                )
                return await cur.fetchone()

    async def delete_interview_entry(self, user_or_channel_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM interviews WHERE channel_id = %s OR user_id = %s",
                    (user_or_channel_id, user_or_channel_id),
                )

    async def increment_question(self, question: int, channel_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE interviews SET current_question = %s WHERE channel_id = %s",
                    (question, channel_id),
                )

    # database initialisation functions

    async def init_db_if_not_initialised(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'info')"
                )
                exists = await cur.fetchone()
                if not exists[0]:
                    await self.init_db()

    async def init_db(self):
        sql_file = open("database/migrations/1.sql", "r")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql_file.read())

    async def update_db(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT schema_version FROM info")
                schema = await cur.fetchone()
                schema_version = schema[0]
                while schema_version < DATABASE_VERSION:
                    schema_version += 1
                    sql_file = open(f"database/migrations/{schema_version}.sql", "r")
                    await cur.execute(sql_file.read())
