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
import typing
from datetime import datetime

import discord
from discord.ext import commands


class Notes(commands.Cog):
    def __init__(self, bot, conn, logger):
        self.bot = bot
        self.conn = conn
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded notes cog")
        print("Loaded notes cog")

    @commands.command(name="setnote", help="Add a note for a user.")
    @commands.has_permissions(manage_messages=True)
    async def set_note(
        self,
        ctx,
        member: typing.Union[discord.Member, discord.User],
        *,
        reason: str,
    ):
        current_notes = await self.conn.list_notes(member.id)
        if len(current_notes) >= 25:  # embeds have a maximum of 25 fields
            await ctx.send(
                "This user has too many notes! A user can have up to 25 notes at any given time."
            )
        elif (
            len(reason) > 200
        ):  # 200 characters to make sure we don't hit the 6000-character limit
            await ctx.send(
                f"Note too long! A note can be up to 200 characters, this note is {len(reason)} characters."
            )
        else:
            await self.conn.add_note(member.id, ctx.author.id, reason)
            await ctx.send(f"✅ Note taken.\n**Note:** {reason}")
            self.logger.log(logging.INFO, "Added note")

    @set_note.error
    async def set_note_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}setnote <user: Member> <reason: str>```\nError: missing required parameter `{error.param.name}`"
            )

    @commands.command(name="delnote", help="Delete a note by ID.")
    @commands.has_permissions(manage_messages=True)
    async def del_note(self, ctx, note: int):
        await self.conn.del_note(note)
        await ctx.send(f"✅ Deleted note #{note}.")
        self.logger.log(logging.INFO, "Deleted note")

    @del_note.error
    async def del_note_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}delnote <note: int>```\nError: missing required argument `{error.param.name}`"
            )

    @commands.command(help="List all notes for a user.")
    @commands.has_permissions(manage_messages=True)
    async def notes(
        self,
        ctx,
        member: typing.Optional[typing.Union[discord.Member, discord.User]] = None,
    ):
        if not member:
            member = ctx.author
        notes = await self.conn.list_notes(member.id)
        embed = discord.Embed(
            timestamp=datetime.utcnow(),
            title="Notes",
            colour=discord.Colour(0x404ADD),
        )
        embed.set_author(name=str(member), icon_url=str(member.avatar_url))
        embed.set_footer(text=f"ID: {member.id}", icon_url=str(ctx.me.avatar_url))
        if notes:
            for note in notes:
                user = ctx.guild.get_member(note[2])
                embed.add_field(
                    name=f"#{note[0]} ({str(user)})",
                    value=f"{note[3]}",
                    inline=False,
                )
        else:
            embed.add_field(name="No notes", value="There are no notes for this user.")
        await ctx.send(embed=embed)
