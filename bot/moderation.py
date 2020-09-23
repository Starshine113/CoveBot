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
import discord
from discord.ext import commands, tasks


time_match = re.compile(
    r"((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?"
)


def none_to_zero(arg):
    if arg is None:
        return 0
    else:
        return arg


def get_timedelta_from_string(time_string: str) -> datetime.timedelta:
    result = time_match.match(time_string)
    time = [
        result.group("weeks"),
        result.group("days"),
        result.group("hours"),
        result.group("minutes"),
    ]
    time = [int(none_to_zero(y)) for y in time]

    time_obj = datetime.timedelta(
        weeks=time[0], days=time[1], hours=time[2], minutes=time[3]
    )
    return time_obj


class Duration(commands.Converter):
    async def convert(self, ctx, argument):
        return get_timedelta_from_string(argument)


class Moderation(commands.Cog):
    def __init__(self, bot, conn, bot_config, logger):
        self.bot = bot
        self.conn = conn
        self.bot_config = bot_config
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded moderation cog")
        print("Loaded moderation cog")
        self.do_pending_actions.start()

    def cog_unload(self):
        self.do_pending_actions.cancel()

    @tasks.loop(seconds=30.0)
    async def do_pending_actions(self):
        pass

    @commands.command()
    async def time(
        self,
        ctx,
        member: discord.Member,
        duration: Duration,
        *,
        reason: typing.Optional[str] = None,
    ):
        await ctx.send(
            f"{ctx.author} muted {member} for {duration}. Reason: **{reason}**"
        )

    # @commands.command(help="Mute a user for the specified duration.")
    async def mute(
        self,
        ctx,
        member: discord.Member,
        duration: Duration,
        *,
        reason: typing.Optional[str] = None,
    ):
        if not reason:
            reason = "None"
        expire_time = datetime.datetime.utcnow() + duration
        self.conn.set_pending_action(
            member.id,
            "mute",
            self.bot_config["moderation"]["mute_role"],
            expire_time,
        )
        await member.add_roles(
            ctx.guild.get_role(self.bot_config["moderation"]["mute_role"])
        )
        self.conn.add_to_mod_logs(member.id, ctx.author.id, "mute", reason)
        await ctx.send(
            f"**{ctx.author}** muted **{member}** for {duration}. Reason: {reason}"
        )

    # @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}mute <user: Member> <duration: Duration> <reason: str>```\nError: missing required parameter `{error.param.name}`"
            )

    def make_log_embed(
        self, member: discord.Member, action_type: str, reason: str = "None"
    ):
        pass

    @commands.command(help="Lock a channel", aliases=["lock", "ld"])
    @commands.has_permissions(manage_guild=True)
    async def lockdown(self, ctx, channel: typing.Optional[discord.TextChannel] = None):
        if not channel:
            channel = ctx.message.channel
        overwrites = channel.overwrites
        overwrites[ctx.guild.default_role].update(send_messages=False)
        overwrites[self.bot.user] = discord.PermissionOverwrite(send_messages=True)
        await channel.edit(overwrites=overwrites)
        await ctx.send(f"✅ Locked down <#{channel.id}>.")

    @commands.command(help="Unlock a channel", aliases=["unlock", "uld"])
    @commands.has_permissions(manage_guild=True)
    async def unlockdown(
        self, ctx, channel: typing.Optional[discord.TextChannel] = None
    ):
        if not channel:
            channel = ctx.message.channel
        overwrites = channel.overwrites
        overwrites[ctx.guild.default_role].update(send_messages=None)
        overwrites[self.bot.user] = discord.PermissionOverwrite(send_messages=None)
        await channel.edit(overwrites=overwrites)
        await ctx.send(f"✅ Unlocked <#{channel.id}>.")

    @commands.command(help="Set a channel's slowmode")
    @commands.has_permissions(manage_messages=True)
    async def slowmode(
        self, ctx, delay: int, channel: typing.Optional[discord.TextChannel] = None
    ):
        if not channel:
            channel = ctx.message.channel
        if delay > 21600 or delay < 0:
            ctx.send(
                "```{ctx.prefix}slowmode <delay: int> [channel: TextChannel]```\nError: `delay` must be between 0 and 21600 seconds."
            )
        else:
            await channel.edit(slowmode_delay=delay)
            await ctx.send(
                f"✅ Set the slowmode for <#{channel.id}> to {delay} seconds."
            )
