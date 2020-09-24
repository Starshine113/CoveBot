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
import typing
import asyncio
from cachetools import TTLCache
import discord
from discord import Embed
from discord.ext import commands


class Highlights(commands.Cog):
    def __init__(self, bot, conn, logger):
        self.bot = bot
        self.conn = conn
        self.logger = logger
        self.send_expiration = TTLCache(maxsize=1000, ttl=300)
        self.hl_expiration = TTLCache(maxsize=1000, ttl=60)
        self.logger.log(logging.INFO, "Loaded highlights cog")
        print("Loaded highlights cog")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return True
        if not message.guild:
            return True
        self.send_expiration[message.author.id] = True
        highlights = await self.conn.get_all_highlights()
        for highlight in highlights:
            if highlight[1] in self.hl_expiration:
                pass
            elif highlight[1] in self.send_expiration:
                pass
            else:
                member = message.guild.get_member(highlight[1])
                perms = message.channel.permissions_for(member)
                if perms.read_messages:
                    if (  # VERY naive matching, TODO fix this
                        re.search(
                            r"\A" + re.escape(highlight[2]) + r"s?\Z",
                            message.content,
                            re.M | re.I,
                        )
                        or re.search(
                            r"\A" + re.escape(highlight[2]) + r"s?\W",
                            message.content,
                            re.M | re.I,
                        )
                        or re.search(
                            r"\W" + re.escape(highlight[2]) + r"s?\Z",
                            message.content,
                            re.M | re.I,
                        )
                        or re.search(
                            r"\W" + re.escape(highlight[2]) + r"s?\W",
                            message.content,
                            re.M | re.I,
                        )
                    ):
                        await asyncio.sleep(1)
                        hl_message, embed = await self.create_message(
                            message, highlight[2]
                        )
                        await member.send(content=hl_message, embed=embed)
                        self.hl_expiration[highlight[1]] = True

    async def create_message(self, message: discord.Message, word: str):
        hl_message: str = f"In **{message.guild.name}** <#{message.channel.id}>, you were mentioned with the highlight word {word}"
        history = await message.channel.history(limit=5).flatten()
        history.reverse()
        embed_desc = ""
        for message in history:
            embed_desc += f"**[{message.created_at.strftime('%H:%M:%S')}] {message.author.display_name}:** {message.content}\n"
        embed_desc = embed_desc[:2000]
        embed: Embed = discord.Embed(
            title=word,
            description=embed_desc,
            colour=discord.Colour(0xF8E71C),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text="Triggered")
        embed.add_field(
            name="Source message",
            value=f"[Jump to](https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id})",
        )
        return hl_message, embed

    @commands.group(help="Manage your highlights", aliases=["hl"])
    async def highlight(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.list(ctx)

    @highlight.command()
    async def list(self, ctx):
        highlights = await self.conn.get_highlights_for_user(ctx.author.id)
        if highlights:
            highlight_list = ""
            for highlight in highlights:
                highlight_list += f"{highlight[2]}\n"
        else:
            highlight_list = "You are not tracking any words."
        embed = discord.Embed(
            title="You're currently tracking the following words",
            description=highlight_list,
            colour=discord.Colour(0xF8E71C),
        )
        await ctx.send(embed=embed)

    @highlight.command()
    async def add(self, ctx, *, word: str):
        highlights = await self.conn.get_highlights_for_user(ctx.author.id)
        if highlights:
            if len(highlights) >= 20:
                await ctx.send("You have reached the limit of 20 highlights.")
                return True
        if len(word) > 50:
            await ctx.send("Your highlight is too long (maximum 50 characters).")
        elif len(word) < 2:
            await ctx.send("Your highlight is too short (minimum 2 characters).")
        else:
            await self.conn.add_highlight(ctx.author.id, word)
            embed = discord.Embed(
                description=f'Added "{word}" to your highlights.',
                colour=discord.Colour(0xF8E71C),
            )
            await ctx.send(embed=embed)

    @highlight.command()
    async def remove(self, ctx, *, word: str):
        current_highlights = await self.conn.get_highlights_for_user(ctx.author.id)
        matched = None
        for highlight in current_highlights:
            if word == highlight["word"]:
                matched = word
        if matched:
            await self.conn.remove_highlight(ctx.author.id, word)
            embed = discord.Embed(
                description=f'Removed "{word}" from your highlighted words.',
                colour=discord.Colour(0xF8E71C),
            )
            await ctx.send(embed=embed)
