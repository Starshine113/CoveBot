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

    @commands.group(aliases=["sb", "star"], help="Starboard settings")
    @commands.has_permissions(manage_guild=True)
    async def starboard(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid subcommand provided.")

    @starboard.command(help="Get the current starboard settings.")
    async def get(self, ctx):
        channel = ctx.message.guild.get_channel(self.settings[1])
        limit = self.settings[2]
        emoji = self.settings[3]
        await ctx.send(
            f"The current starboard channel is <#{channel.id}>.\nThe current emoji for the starboard is {emoji}.\nA message needs {limit} stars to get on <#{channel.id}>."
        )

    @starboard.command(help="Set the channel where starboard messages are sent.")
    async def channel(self, ctx, channel: discord.TextChannel):
        await self.conn.set_starboard_channel(channel.id)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard channel set to {channel.mention}.")
        self.logger.log(
            logging.INFO, f"Set starboard channel to #{channel.name} ({channel.id})"
        )

    @starboard.command(help="Set the emoji the starboard module will look for.")
    async def emoji(self, ctx, arg: str):
        await self.conn.set_starboard_emoji(arg)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard emoji set to {arg}.")
        self.logger.log(logging.INFO, f"Set starboard emoji to {arg}")

    @starboard.command(help="Set the emoji limit for messages to get on the starboard.")
    async def limit(self, ctx, limit: int):
        await self.conn.set_starboard_limit(limit)
        self.settings = await self.conn.get_starboard_settings()
        await ctx.send(f"✅ Starboard limit set to {limit}.")
        self.logger.log(logging.INFO, f"Set starboard limit to {limit}")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        await self.conn.delete_starboard_entry(payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if (
            payload.guild_id == self.bot_config["guild"]["guild_id"]
            and str(payload.emoji) == self.settings[3]
            and not payload.channel_id == self.settings[1]
            and await self.conn.channel_not_blacklisted(payload.channel_id)
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild = self.bot.get_guild(payload.guild_id)
        if guild.id == self.bot_config["guild"]["guild_id"]:
            channel = guild.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            member = guild.get_member(payload.user_id)
            if (
                str(payload.emoji) == self.settings[3]
                and not payload.channel_id == self.settings[3]
                and await self.conn.channel_not_blacklisted(payload.channel_id)
            ):
                if message.author == member:
                    pass
                else:
                    for reaction in message.reactions:
                        if str(reaction.emoji) == self.settings[3]:
                            if reaction.count < self.settings[2]:
                                await self.delete_starboard_message(message, guild)
                            else:
                                await self.create_or_edit_starboard_message(
                                    message, guild, reaction.count
                                )

    async def delete_starboard_message(
        self, message: discord.Message, guild: discord.Guild
    ):
        starboard_channel = guild.get_channel(self.settings[1])
        starboard = await self.conn.get_starboard_message(message.id)
        if starboard:
            starboard_message = await starboard_channel.fetch_message(starboard[1])
            await starboard_message.delete()
            await self.conn.delete_starboard_entry(message.id)

    async def create_or_edit_starboard_message(
        self, message: discord.Message, guild: discord.Guild, count: int
    ):
        starboard_channel = guild.get_channel(self.settings[1])
        starboard_text = f"**{count}** {self.settings[3]} <#{message.channel.id}>"
        starboard_embed = discord.Embed(
            description=message.content,
            colour=discord.Colour(0xF8E71C),
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
            self.logger.log(
                logging.INFO, f"Updated starboard message {starboard_message.id}"
            )
        else:
            starboard_message = await starboard_channel.send(
                content=starboard_text, embed=starboard_embed
            )
            await self.conn.set_starboard_message(message.id, starboard_message.id)
            self.logger.log(logging.INFO, f"Created starboard message for {message.id}")

    @starboard.group(aliases=["bl"], help="Manage the channel blacklist.")
    @commands.has_permissions(manage_guild=True)
    async def blacklist(self, ctx):
        if ctx.invoked_subcommand is None:
            blacklist = await self.conn.get_blacklist()
            blacklist_message = ""
            for channel in blacklist:
                blacklist_message += "<#" + str(channel) + ">\n"
            if blacklist_message == "":
                blacklist_message = "No channels are blacklisted.\n(Use `{}starboard blacklist add` to disable commands in a given channel)".format(
                    ctx.prefix
                )
            else:
                blacklist_message += "\nTo remove channels from the blacklist, use `{}starboard blacklist remove`.".format(
                    ctx.prefix
                )
            embed = discord.Embed(
                title="Starboard blacklist",
                description=blacklist_message,
            )
            await ctx.send(embed=embed)

    @blacklist.command(help="Add channel(s) to the blacklist.")
    async def add(self, ctx, *args):
        current_blacklist = await self.conn.get_blacklist()
        channels = await self.get_channel_ids(args)
        message = ""
        for channel in channels:
            if not channel in current_blacklist:
                await self.conn.add_to_blacklist(channel)
                message += "✅ Channel <#" + str(channel) + "> added to the blacklist.\n"
            else:
                message += (
                    "⚠ Channel <#"
                    + str(channel)
                    + "> is already on the blacklist. Use `"
                    + ctx.prefix
                    + "starboard blacklist remove` to remove it from the blacklist.\n"
                )
        await ctx.send(message)

    @blacklist.command(help="Remove channel(s) from the blacklist.")
    async def remove(self, ctx, *args):
        current_blacklist = await self.conn.get_blacklist()
        channels = await self.get_channel_ids(args)
        message = ""
        for channel in channels:
            if channel in current_blacklist:
                await self.conn.remove_from_blacklist(channel)
                message += (
                    "✅ Channel <#" + str(channel) + "> removed from the blacklist.\n"
                )
            else:
                message += (
                    "⚠ Channel <#"
                    + str(channel)
                    + "> is not blacklisted. Use `"
                    + ctx.prefix
                    + "starboard blacklist add` to add it to the blacklist.\n"
                )
        await ctx.send(message)

    async def get_channel_ids(self, args):
        channels = []
        for item in args:
            m = re.search(r"<#(?P<ID>\d{3,25})>", item)
            channel = m.group("ID")
            channels.append(int(channel))
        return channels
