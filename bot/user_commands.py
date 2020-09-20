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

import logging
import re
import discord
from discord.ext import commands


class UserCommands(commands.Cog):
    def __init__(self, bot, conn, logger):
        self.bot = bot
        self.conn = conn
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded commands cog")
        print("Loaded commands cog")

    @commands.command(help="Enlarge any custom emoji.")
    @commands.cooldown(1, 3, commands.BucketType.channel)
    async def enlarge(self, ctx, emoji_str: str):
        match = re.search(r"<(a)?:\w+:(\d+)>", emoji_str)
        if match:
            animated = match.group(1)
            emoji_id = match.group(2)
            extension = ".png"
            if animated:
                extension = ".gif"
            emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}{extension}"
            await ctx.send(emoji_url)

    @commands.command(help="Show the bot's latency.")
    @commands.cooldown(1, 3, commands.BucketType.channel)
    async def ping(self, ctx):
        await ctx.send("Pong! Latency: {}ms".format(round(self.bot.latency * 1000, 2)))
