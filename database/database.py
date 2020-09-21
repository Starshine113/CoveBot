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


DATABASE_VERSION = 9


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

    # starboard functions

    async def get_starboard_settings(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM starboard")
                return await cur.fetchone()

    async def set_starboard_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE starboard SET channel = %s WHERE id = 1", (channel_id,)
                )

    async def set_starboard_emoji(self, emoji: str):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE starboard SET emoji = %s WHERE id = 1", (emoji,)
                )

    async def set_starboard_limit(self, limit: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "UPDATE starboard SET star_limit = %s WHERE id = 1", (limit,)
                )

    async def get_starboard_message(self, message_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT * FROM starboard_messages WHERE message_id = %s",
                    (message_id,),
                )
                return await cur.fetchone()

    async def set_starboard_message(self, message_id: int, starboard_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO starboard_messages (message_id, starboard_id) VALUES (%s, %s)",
                    (message_id, starboard_id),
                )

    async def delete_starboard_entry(self, message_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM starboard_messages WHERE message_id = %s OR starboard_id = %s",
                    (message_id, message_id),
                )

    # note functions

    async def add_note(self, user_id: int, added_by: int, note: str):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO notes (user_id, set_by, reason) VALUES (%s, %s, %s)",
                    (user_id, added_by, note),
                )

    async def del_note(self, note_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM notes WHERE id = %s", (note_id,))

    async def list_notes(self, user_id: int):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT * FROM notes WHERE user_id = %s", (user_id,))
                return await cur.fetchall()

    # blacklist functions

    async def add_to_blacklist(self, channel):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO blacklisted_channels (channel_id) VALUES (%s)",
                    (channel,),
                )

    async def remove_from_blacklist(self, channel):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM blacklisted_channels WHERE channel_id = %s",
                    (int(channel),),
                )

    async def get_blacklist(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT channel_id FROM blacklisted_channels")
                channels = await cur.fetchall()
                channel_list = []
                for channel in channels:
                    channel_list.append(channel[0])

                return channel_list

    async def channel_not_blacklisted(self, channel_id: int):
        blacklist = await self.get_blacklist()
        return channel_id not in blacklist

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
