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

import datetime
import logging
import re
import subprocess
import typing

from cachetools import TTLCache
import discord
from discord.ext import commands


class HelpCommand(commands.Cog):
    def __init__(self, bot, conn, bot_config, logger):
        self.bot = bot
        self.conn = conn
        self.bot_config = bot_config
        self.logger = logger

    @commands.command(name="addroles")
    @commands.has_permissions(manage_roles=True)
    async def add_roles(self, ctx, roles: commands.Greedy[discord.Role]):
        message = ""
        current_whitelisted_roles = await self.conn.fetch_roles()
        for role in roles:
            if role.id in current_whitelisted_roles:
                message += f"Role `{role.name}` is already whitelisted.\n"
            else:
                await self.conn.add_role(role.id)
                message += f"Whitelisted `{role.name}`.\n"
        embed = discord.Embed(
            colour=discord.Colour(0x4A90E2),
            description=message,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(
            name=f"{ctx.author} added some roles", icon_url=str(ctx.author.avatar_url)
        )
        embed.set_footer(text=f"Invoking user ID: {ctx.author.id}")
        await ctx.send(embed=embed)