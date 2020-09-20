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


class Starboard(commands.Cog):
    def __init__(self, bot, conn, settings, bot_config, logger):
        self.bot = bot
        self.conn = conn
        self.settings = settings
        self.bot_config = bot_config
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded starboard cog")
        print("Loaded starboard cog")

    @commands.group(aliases=["sb", "star"])
    @commands.has_permissions(manage_guild=True)
    async def starboard(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid subcommand provided.")

    @starboard.command()
    async def get(self, ctx):
        channel = ctx.message.guild.get_channel(self.settings[1])
        limit = self.settings[2]
        emoji = self.settings[3]
        await ctx.send(
            f"The current starboard channel is <#{channel.id}>.\nThe current emoji for the starboard is {emoji}.\nA message needs {limit} stars to get on <#{channel.id}>."
        )

    @starboard.command()
    async def channel(self, ctx, channel: discord.TextChannel):
        await self.conn.set_starboard_channel(channel.id)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard channel set to {channel.mention}.")

    @starboard.command()
    async def emoji(self, ctx, arg: str):
        await self.conn.set_starboard_emoji(arg)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard emoji set to {arg}.")

    @starboard.command()
    async def limit(self, ctx, limit: int):
        await self.conn.set_starboard_limit(limit)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard limit set to {limit}.")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        await self.conn.delete_starboard_entry(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if (
            payload.guild_id == self.bot_config["guild"]["guild_id"]
            and str(payload.emoji) == self.settings[3]
            and not payload.channel_id == self.settings[1]
        ):
            member = payload.member
            channel = member.guild.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.author == member:
                await message.remove_reaction(self.settings[3], member)
            else:
                for reaction in message.reactions:
                    if str(reaction.emoji) == self.settings[3]:
                        if reaction.count >= self.settings[2]:
                            await self.create_or_edit_starboard_message(
                                message, member.guild, reaction.count
                            )

    async def create_or_edit_starboard_message(
        self, message: discord.Member, guild: discord.Guild, count: int
    ):
        starboard_channel = guild.get_channel(self.settings[1])
        starboard_text = f"{count} {self.settings[3]} <#{message.channel.id}>"
        starboard_embed = discord.Embed(
            description=message.content,
            timestamp=message.created_at,
        )
        starboard_embed.set_author(
            name=message.author.display_name, icon_url=str(message.author.avatar_url)
        )
        starboard_embed.add_field(
            name="Source",
            value=f"[Jump to message](https://discordapp.com/channels/{message.guild.id}/{message.channel.id}/{message.id})",
        )
        starboard_embed.set_footer(text=f"{message.id}")
        if message.attachments:
            attachment_url = message.attachments[0].url
            if re.search(r"\.(png|jpg|jpeg|gif|webp)$", attachment_url) is not None:
                starboard_embed.set_image(url=attachment_url)
        starboard = await self.conn.get_starboard_message(message.id)
        if starboard:
            starboard_message = await starboard_channel.fetch_message(starboard[1])
            await starboard_message.edit(content=starboard_text, embed=starboard_embed)
        else:
            starboard_message = await starboard_channel.send(
                content=starboard_text, embed=starboard_embed
            )
            await self.conn.set_starboard_message(message.id, starboard_message.id)
