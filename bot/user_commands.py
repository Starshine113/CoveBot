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
from discord.ext import commands


class UserCommands(commands.Cog):
    def __init__(self, bot, conn, logger):
        self.bot = bot
        self.conn = conn
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded commands cog")
        print("Loaded commands cog")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_perms)
            await ctx.send(
                f"❌ **Error:** You are missing the required permissions to run this command.\nRequired permissions: `{perms}`"
            )

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

    # this should be part of the help command eventually but we're l a z y and can't be bothered to figure that out yet
    @commands.command(help="Show some info about the bot.")
    @commands.cooldown(1, 3, commands.BucketType.channel)
    async def about(self, ctx):
        embed = discord.Embed(
            title="About CoveBotn't",
            colour=discord.Colour(0xF8E71C),
            description="CoveBotn't is a general purpose custom bot for the Cove. It currently handles the starboard and moderation notes.",
        )
        embed.set_footer(
            text="Created by Starshine System (Starshine ☀✨#5000) | CoveBotn't v0.5"
        )
        embed.add_field(
            name="Source code",
            value="The source code can be found [here](https://github.com/Starshine113/CoveBot/).",
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(help="Say something in a channel", aliases=["say"])
    @commands.has_permissions(manage_guild=True)
    async def echo(
        self, ctx, channel: typing.Optional[discord.TextChannel], *, args=None
    ):
        if ctx.message.attachments:
            attachments = []
            for attachment in ctx.message.attachments:
                attachments.append(await attachment.to_file())
        else:
            attachments = None
        if channel:
            await channel.send(
                content=args,
                files=attachments,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
            )
        else:
            await ctx.send(
                content=args,
                files=attachments,
                allowed_mentions=discord.AllowedMentions(
                    everyone=False, users=False, roles=False
                ),
            )

    @commands.command(help="Get information about a user", aliases=["i", "profile"])
    @commands.cooldown(1, 1, commands.BucketType.channel)
    async def info(
        self,
        ctx,
        *,
        member: typing.Optional[typing.Union[discord.Member, discord.User]] = None,
    ):
        if not member:
            member = ctx.author

        embed = discord.Embed(
            description=f"User data for {member.mention}:",
            colour=discord.Colour(0xF8E71C),
        )
        embed.set_author(name=str(member), icon_url=str(member.avatar_url))
        embed.set_thumbnail(url=str(member.avatar_url))
        embed.set_footer(text=f"User ID: {member.id}")
        if isinstance(member, discord.Member):
            embed.add_field(
                name="Highest Rank", value=str(member.top_role), inline=True
            )
        if isinstance(member, discord.Member):
            if member.status is discord.Status.online:
                status = "online"
            elif member.status is discord.Status.idle:
                status = "idle"
            elif member.status is discord.Status.do_not_disturb:
                status = "do not disturb"
            elif member.status is discord.Status.offline:
                status = "offline"
            elif isinstance(member.status, str):
                status = member.status
            if status is not None:
                embed.add_field(name="Status", value=status, inline=True)

        embed.add_field(name="Username", value=str(member), inline=True)
        if isinstance(member, discord.Member):
            embed.add_field(name="Nickname", value=member.display_name, inline=True)

        created_delta = datetime.datetime.utcnow() - member.created_at
        created_string = f"{member.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC ({created_delta.days} days ago)"

        embed.add_field(name="Created", value=created_string, inline=True)
        if isinstance(member, discord.Member):
            joined_delta = datetime.datetime.utcnow() - member.joined_at
            joined_string = f"{member.joined_at.strftime('%Y-%m-%d %H:%M:%S')} UTC ({joined_delta.days} days ago)"
            embed.add_field(name="Joined", value=joined_string, inline=True)

        if isinstance(member, discord.Member):
            roles = []
            for role in member.roles[1:]:
                roles.append(role.mention)
            roles.reverse()
            roles_string = " ".join(roles)
            if len(roles_string) >= 1000:
                roles_string = "Too many to list"
            embed.add_field(
                name=f"Roles ({len(roles)})", value=roles_string, inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(
        name="roleinfo", help="Get information about a role", aliases=["role-info"]
    )
    @commands.cooldown(1, 1, commands.BucketType.channel)
    async def role_info(self, ctx, *, role: typing.Optional[discord.Role] = None):
        if not role:
            role = ctx.guild.default_role
        embed = discord.Embed(
            title=f"Role info: {role.name}",
            colour=role.colour,
            description=f"`<@&{role.id}>`",
            timestamp=role.created_at,
        )
        embed.set_footer(text="Created at")
        embed.add_field(name="Name", value=role.name, inline=False)
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Position", value=role.position, inline=True)
        embed.add_field(name="Hoisted", value=role.hoist, inline=True)
        embed.add_field(name="Mentionable", value=str(role.mentionable), inline=True)
        embed.add_field(name="Colour", value=str(role.colour), inline=True)
        embed.add_field(name="Members", value=str(len(role.members)), inline=True)
        embed.add_field(
            name="Created",
            value=f"{role.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            inline=True,
        )

        await ctx.send(embed=embed)

    @commands.command(name="setstatus")
    @commands.is_owner()
    async def set_status(self, ctx, *, args: str):
        await self.bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Game(name=args),
        )
        await ctx.send("Changed presence")
