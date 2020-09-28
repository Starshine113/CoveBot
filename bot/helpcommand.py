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
        self.current_revision = subprocess.run(
            ["git", "log", "-1", "--format=%h"], stdout=subprocess.PIPE
        ).stdout.decode("utf-8")
        if not self.current_revision:
            self.current_revision = "UNKNOWN"

        self.help_cache = TTLCache(maxsize=1000, ttl=300)
        self.help_embeds = self.help_embeds()
        self.bot.remove_command("help")

        self.logger.log(logging.INFO, "Loaded help cog")
        print("Loaded help cog")

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx):
        if ctx.guild:
            await self.send_help(ctx.message.author, ctx.author)
            await ctx.send("📬 Check your DMs!")
        else:
            await self.send_help(ctx, ctx.author)
        await ctx.message.add_reaction("✅")

    # send help messages
    async def send_help(self, channel, user: discord.User):
        message = await channel.send(embed=self.help_embeds[0])
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")
        self.help_cache[user.id] = [message.id, 0]

    # listen for reacts/edit the message
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id in self.help_cache:
            if self.help_cache[payload.user_id][0] == payload.message_id:
                if str(payload.emoji) == "⬅️":
                    user = self.bot.get_user(payload.user_id)
                    message = await user.fetch_message(payload.message_id)
                    page = self.help_cache[payload.user_id][1]
                    if page > 0:
                        await message.edit(embed=self.help_embeds[page - 1])
                        self.help_cache[user.id] = [message.id, page - 1]
                if str(payload.emoji) == "➡️":
                    user = self.bot.get_user(payload.user_id)
                    message = await user.fetch_message(payload.message_id)
                    page = self.help_cache[payload.user_id][1]
                    if page < len(self.help_embeds) - 1:
                        await message.edit(embed=self.help_embeds[page + 1])
                        self.help_cache[user.id] = [message.id, page + 1]

    # help embeds
    def help_embeds(self):
        common_footer = f"Created by Starshine System (Starshine ☀✨#5000) | CoveBotn't v0.{self.conn.get_version()}-{self.current_revision}"
        help_embeds = []

        embed0 = discord.Embed(colour=discord.Colour(0x4A90E2), title="CoveBotn't help")
        embed0.description = (
            "CoveBotn't is a general purpose custom bot for the Cove. "
            "It currently handles the gatekeeper, starboard, mod notes, some moderator actions, and highlights.\n"
            "Use ⬅️ ➡️ to navigate between pages️."
        )
        embed0.set_footer(text=common_footer)
        help_embeds.append(embed0)

        if self.bot_config["cogs"]["enable_user_commands"]:
            embed1 = discord.Embed(
                colour=discord.Colour(0x4A90E2), title="User commands"
            )
            embed1.description = (
                "`avatar [user: User]`: show your or another user's avatar\n"
                "`echo [channel: TextChannel] [message: str]`: make the bot say something (requires manage server)\n"
                "`embed [channel: TextChannel] <colour: str> <message: str>`: create an embed (requires manage messages in the target channel)\n"
                "`enlarge <emoji: str>`: enlarge any *custom* emoji\n"
                "`info [user: User]`: get information about yourself or another user\n"
                "`ping`: show the bot's latency\n"
                "`roleinfo [role: Role]`: get info about a role"
            )
            embed1.set_footer(text=common_footer)
            help_embeds.append(embed1)
        if self.bot_config["cogs"]["enable_highlights"]:
            embed2 = discord.Embed(colour=discord.Colour(0x4A90E2), title="Highlights")
            embed2.description = (
                "Highlights DM you when the phrase(s) you highlighted are mentioned in chat.\n"
                "There's a 5-minute cooldown after sending a message, and a 1-minute cooldown between highlights.\n\n"
                "`highlight [list]`: show your current highlights\n"
                "`highlight add <phrase: str>`: add a phrase to your highlights\n"
                "`highlight remove <phrase: str>`: remove a phrase from your highlights"
            )
            embed2.set_footer(text=common_footer)
            help_embeds.append(embed2)
        if self.bot_config["cogs"]["enable_starboard"]:
            embed3 = discord.Embed(
                colour=discord.Colour(0x4A90E2), title="Starboard commands"
            )
            embed3.description = (
                "**All commands here require the `Manage Server` permission to use.**\n\n"
                "`starboard get`: get the current starboard settings\n"
                "`starboard channel <channel: TextChannel>`: set the channel used for the starboard\n"
                "`starboard emoji <emoji: str>`: set the emoji (default or custom) used for the starboard\n"
                "`starboard limit <limit: int>`: set the number of emoji needed to get a message on the starboard\n"
                "`starboard blacklist`: show the current channel blacklist\n"
                "`starboard blacklist add <channels: ...TextChannel>`: add channels to the blacklist\n"
                "`starboard blacklist remove <channels: ...TextChannel>`: remove channels from the blacklist"
            )
            embed3.set_footer(text=common_footer)
            help_embeds.append(embed3)
        if self.bot_config["cogs"]["enable_moderation"]:
            embed4 = discord.Embed(
                colour=discord.Colour(0x4A90E2), title="Moderation commands"
            )
            embed4.description = (
                "`hardmute <user: Member> <duration: Duration> [reason: str]`: hardmute a user for the specified duration\n"
                "`lockdown [channel: TextChannel]`: lock a channel, so no users can send messages in the channel\n"
                "`massban <users: ...User> [reason: str]`: mass ban users, with an optional reason\n"
                "`modlogs <user: User> [page: int]`: show the moderation logs for a user\n"
                "`mute <user: Member> <duration: Duration> [reason: str]`: mute a user for the specified duration\n"
                "`slowmode <delay: int> [channel: TextChannel]`: set the slowmode for a channel\n"
                "`unban <user: User> [reason: str]`: unban the specified user, with an optional reason\n"
                "`unlockdown [channel: TextChannel]`: unlock a channel\n"
                "`unmute <user: Member> [reason: str]`: unmute a user, with an optional reason\n"
                "`warn <user: Member> <reason: str>`: warn a user"
            )
            embed4.set_footer(text=common_footer)
            help_embeds.append(embed4)
        if self.bot_config["cogs"]["enable_simple_gatekeeper"]:
            embed5 = discord.Embed(
                colour=discord.Colour(0x4A90E2), title="Gatekeeper commands"
            )
            embed5.description = (
                "**These commands require `Manage Server` to use.\n\n**"
                "`approve <user: Member>`: approve a user"
            )
            embed5.set_footer(text=common_footer)
            help_embeds.append(embed5)
        elif self.bot_config["cogs"]["enable_advanced_gatekeeper"]:
            embed5 = discord.Embed(
                colour=discord.Colour(0x4A90E2), title="Gatekeeper commands"
            )
            embed5.description = (
                "**These commands require `Manage Server` to use.\n\n**"
                "`interview approve`: approve a user\n"
                "`interview deny`: deny a user"
            )
            embed5.set_footer(text=common_footer)
            help_embeds.append(embed5)
        if self.bot_config["cogs"]["enable_notes"]:
            embed6 = discord.Embed(colour=discord.Colour(0x4A90E2), title="Notes")
            embed6.description = (
                "**These commands require `Manage Messages` to use.\n\n**"
                "`setnote <user: Member> <reason: str>`: set a note for a user\n"
                "`delnote <id: int>`: deny a user\n"
                "`notes [user: Member]`: show notes for yourself or another user"
            )
            embed6.set_footer(text=common_footer)
            help_embeds.append(embed6)

        return help_embeds
