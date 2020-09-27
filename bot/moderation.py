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
import math
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
        guild = self.bot.get_guild(self.bot_config["guild"]["guild_id"])
        actions = await self.conn.get_pending_actions()
        for action in actions:
            if action[4] < datetime.datetime.utcnow():
                member = guild.get_member(action[5])
                if action[1] == "mute" or action[1] == "hardmute":
                    await self.unmute_inner(member, action[2], action[3])
                    await self.conn.add_to_mod_logs(
                        member.id, self.bot.user.id, "unmute", "Automatic unmute"
                    )
                    await self.make_log_embed(
                        member,
                        "unmuted",
                        guild.get_member(self.bot.user.id),
                        "Automatic unmute",
                    )
                    await self.conn.delete_pending_action(action[0])

    @commands.command(help="Warn a user.")
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        if member.id == self.bot.user.id:
            await ctx.send("But why? <:meowsob:759071377562009620>")
            return True
        await ctx.trigger_typing()
        await self.conn.add_to_mod_logs(member.id, ctx.author.id, "warn", reason)
        await member.send(f"You were warned in {ctx.guild.name}. Reason: {reason}")
        await self.make_log_embed(member, "warned", ctx.author, reason)
        await ctx.send(f"Warned **{member}**.")

    @commands.command(help="Mute a user for the specified duration.")
    @commands.has_permissions(manage_messages=True)
    async def mute(
        self,
        ctx,
        member: discord.Member,
        duration: Duration,
        *,
        reason: typing.Optional[str] = None,
    ):
        mute_role = ctx.guild.get_role(self.bot_config["moderation"]["mute_role"])
        if member.top_role.position >= ctx.author.top_role.position:
            await ctx.send("You are not high enough in the role hierarchy to do that.")
            return True
        if mute_role in member.roles:
            await ctx.send(f"{member} is already muted.")
            return True
        await ctx.trigger_typing()
        if not reason:
            reason = "None"
        expire_time = datetime.datetime.utcnow() + duration
        await self.conn.set_pending_action(
            member.id,
            "mute",
            [mute_role.id],
            None,
            expire_time,
        )
        await member.add_roles(mute_role)
        await self.conn.add_to_mod_logs(member.id, ctx.author.id, "mute", reason)
        await ctx.send(
            f"**{ctx.message.author}** muted **{member}** for {duration}. Reason: {reason}"
        )
        await member.send(
            f"You were muted in {ctx.guild.name} for {duration}. Reason: {reason}"
        )
        await self.make_log_embed(member, "muted", ctx.author, reason)

    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}mute <user: Member> <duration: Duration> [reason: str]```\nError: missing required parameter `{error.param.name}`"
            )

    @commands.command(help="Hardmute a user for the specified duration.")
    @commands.has_permissions(kick_members=True)
    async def hardmute(
        self,
        ctx,
        member: discord.Member,
        duration: Duration,
        *,
        reason: typing.Optional[str] = None,
    ):
        mute_role = ctx.guild.get_role(self.bot_config["moderation"]["mute_role"])
        if member.top_role.position >= ctx.author.top_role.position:
            await ctx.send("You are not high enough in the role hierarchy to do that.")
            return True
        bot_user = ctx.guild.get_member(self.bot.user.id)
        if member.top_role.position >= bot_user.top_role.position:
            await ctx.send("I am not high enough in the role hierachy to do that.")
            return True
        if mute_role in member.roles:
            await ctx.send(f"{member} is already muted.")
            return True
        await ctx.trigger_typing()
        if not reason:
            reason = "None"
        roles_to_add = []
        all_roles = member.roles[1:]
        for role in all_roles:
            roles_to_add.append(role.id)
        await member.remove_roles(*all_roles, atomic=False)
        expire_time = datetime.datetime.utcnow() + duration
        await self.conn.set_pending_action(
            member.id,
            "hardmute",
            [mute_role.id],
            roles_to_add,
            expire_time,
        )
        await member.add_roles(mute_role, atomic=False)
        await self.conn.add_to_mod_logs(member.id, ctx.author.id, "hardmute", reason)
        await ctx.send(
            f"**{ctx.message.author}** hardmuted **{member}** for {duration}. Reason: {reason}"
        )
        await member.send(
            f"You were hardmuted in {ctx.guild.name} for {duration}. Reason: {reason}"
        )
        await self.make_log_embed(member, "hardmuted", ctx.author, reason)

    @mute.error
    async def hardmute_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}hardmute <user: Member> <duration: Duration> [reason: str]```\nError: missing required parameter `{error.param.name}`"
            )

    @commands.command(help="Unmute a user.")
    @commands.has_permissions(manage_messages=True)
    async def unmute(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: typing.Optional[str] = None,
    ):
        mute_role = ctx.guild.get_role(self.bot_config["moderation"]["mute_role"])
        if not mute_role in member.roles:
            await ctx.send("That member is not muted.")
            return True
        if member.top_role.position >= ctx.author.top_role.position:
            await ctx.send("You are not high enough in the role hierarchy to do that.")
            return True
        await ctx.trigger_typing()
        if not reason:
            reason = "None"
        db_entry = await self.conn.get_mute(member.id)
        await self.unmute_inner(member, db_entry[2], db_entry[3])
        await self.conn.add_to_mod_logs(member.id, ctx.author.id, "unmute", reason)
        await self.conn.delete_pending_action(db_entry[0])
        await self.make_log_embed(member, "unmuted", ctx.author, reason)
        await ctx.send(f"Unmuted **{member}**.")

    async def unmute_inner(
        self, member: discord.Member, remove_roles=None, add_roles=None
    ):
        if remove_roles:
            remove = []
            for role in remove_roles:
                remove.append(member.guild.get_role(role))
        else:
            remove = None
        if add_roles:
            add = []
            for role in add_roles:
                add.append(member.guild.get_role(role))
        else:
            add = None
        if remove:
            await member.remove_roles(*remove, atomic=False)
        if add:
            await member.add_roles(*add, atomic=False)

    async def make_log_embed(
        self,
        member: discord.Member,
        action_type: str,
        mod: discord.Member,
        reason: str = "None",
    ):
        guild = self.bot.get_guild(self.bot_config["guild"]["guild_id"])
        log_channel = guild.get_channel(self.bot_config["moderation"]["mod_log"])
        embed = discord.Embed(
            title=f"{action_type.title()} {member}",
            colour=discord.Colour(0x404ADD),
            description=f"**{mod}** {action_type} **{member}**.\nReason: **{reason}**",
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_footer(text=f"User ID: {member.id} | Moderator ID: {mod.id}")
        await log_channel.send(embed=embed)

    @commands.command(help="Lock a channel", aliases=["lock", "ld"])
    @commands.has_permissions(manage_guild=True)
    async def lockdown(self, ctx, channel: typing.Optional[discord.TextChannel] = None):
        if not channel:
            channel = ctx.message.channel
        await ctx.trigger_typing()
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
        await ctx.trigger_typing()
        if delay > 21600 or delay < 0:
            ctx.send(
                f"```{ctx.prefix}slowmode <delay: int> [channel: TextChannel]```\nError: `delay` must be between 0 and 21600 seconds."
            )
        else:
            await channel.edit(slowmode_delay=delay)
            await ctx.send(
                f"✅ Set the slowmode for <#{channel.id}> to {delay} seconds."
            )

    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}slowmode <delay: int> [channel: TextChannel]```\nError: missing required parameter `{error.param.name}`"
            )

    @commands.command(help="Show a user's moderation logs.")
    @commands.has_permissions(manage_messages=True)
    async def modlogs(
        self,
        ctx,
        user: discord.User,
        page: typing.Optional[int] = 1,
    ):
        await ctx.trigger_typing()
        mod_logs = await self.conn.get_logs_for_user(user.id)
        mod_logs.reverse()
        minimum = (page - 1) * 10
        maximum = page * 10
        if len(mod_logs) < minimum:
            await ctx.send("That page doesn't exist.")
            return True
        if len(mod_logs) <= maximum:
            maximum = len(mod_logs)
        mod_log_page = mod_logs[minimum:maximum]
        embed = discord.Embed(
            colour=discord.Colour(0x404ADD),
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_author(name=str(user), icon_url=str(user.avatar_url))
        embed.set_footer(text=f"User ID: {user.id}")
        for log_entry in mod_log_page:
            embed = await self.add_log_entry(embed, log_entry)
        if mod_logs:
            embed.title = f"Page {page}/{math.ceil(len(mod_logs) / 10)}"
        else:
            embed.description = "There are no moderation logs for this user."
        await ctx.send(embed=embed)

    @modlogs.error
    async def modlogs_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"```{ctx.prefix}modlogs <user: User> [page: int]```\nError: missing required parameter `{error.param.name}`"
            )

    async def add_log_entry(
        self,
        embed: discord.Embed,
        entry: list,
    ) -> discord.Embed:
        mod = self.bot.get_user((entry[2]))
        embed.add_field(
            name=f"Case #{entry[0]}: {entry[3]}",
            value=f"By **{mod}** ({entry[2]})\nReason: **{entry[4]}**\nTime: {entry[5].strftime('%Y-%m-%d %H:%M:%S')} UTC",
            inline=False,
        )
        return embed

    @commands.command(help="Mass-ban users with an optional reason.")
    @commands.has_permissions(ban_members=True, manage_guild=True)
    async def massban(self, ctx, users: commands.Greedy[discord.User]):
        await ctx.trigger_typing()
        for user in users:
            await ctx.guild.ban(user, reason=f"Massban by {str(ctx.author)}")
        await ctx.send(f"Banned {len(users)} users.")

    @commands.command(help="Unban a user with an optional reason.")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user: discord.User, *, reason: str = "None"):
        await ctx.trigger_typing()
        await ctx.guild.unban(
            user, reason=f"Unbanned by {str(ctx.author)} reason: {reason}"
        )
        await ctx.send(f"Unbanned **{str(user)}**.")

    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, discord.HTTPException):
            await ctx.send("That user is not banned.")
