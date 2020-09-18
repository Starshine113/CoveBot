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

import asyncio
from datetime import datetime
import io
import discord
from discord.ext import commands


class Interviews(commands.Cog):
    def __init__(self, bot, conn, config):
        self.bot = bot
        self.conn = conn
        self.bot_config = config

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            await member.add_roles(
                member.guild.get_role(self.bot_config["guild"]["gatekeeper_role"]),
                reason="Interview: add gatekeeper role",
            )
            if not await self.conn.get_interview(member.id):
                channel = await self.create_interview_channel(member, member.guild)
                await self.send_welcome_message(member, channel)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            interview = await self.conn.get_interview(member.id)
            if interview:
                channel_id = interview[1]
                channel = member.guild.get_channel(channel_id)
                await channel.send(
                    f"{member.name} left {member.guild.name} before finishing their interview."
                )
                await self.queue_channel_deletion(channel, member)

    async def send_welcome_message(
        self, member: discord.Member, channel: discord.TextChannel
    ):
        await asyncio.sleep(1)
        await channel.send(
            f"Thanks for checking out our server, {member.mention}! Please answer these questions, and a moderator will approve you. If you have any questions, feel free to mention `@Mods` and we'll try to answer!\n> 1. How did you find this server?\n> 2. What are your pronouns?\n> 3. Have you read and agree to the rules?"
        )

    async def create_interview_channel(self, member, guild):
        channel_name = "{}-{}-interview".format(member.name, member.discriminator)
        overwrites = {
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                read_message_history=True,
            ),
        }
        for role in self.bot_config["guild"]["mod_roles"]:
            overwrites[guild.get_role(role)] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True, add_reactions=True
            )
        for role in self.bot_config["guild"]["helper_roles"]:
            overwrites[guild.get_role(role)] = discord.PermissionOverwrite(
                read_messages=True, manage_messages=False
            )
        if self.bot_config["guild"]["everyone_can_see_interviews"]:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                send_messages=False, add_reactions=False
            )
            overwrites[
                guild.get_role(self.bot_config["guild"]["hide_interview_role"])
            ] = discord.PermissionOverwrite(read_messages=False)
        else:
            overwrites[guild.default_role] = discord.PermissionOverwrite(
                read_messages=False
            )
        channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            category=guild.get_channel(self.bot_config["guild"]["interview_category"]),
            reason="Interview: automatic interview channel creation",
        )
        await self.conn.create_interview(member.id, channel.id)
        return channel

    @commands.group(aliases=["in"])
    @commands.has_permissions(manage_guild=True)
    async def interview(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid subcommand provided.")

    @interview.command()
    async def create(self, ctx, member: discord.Member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            await member.add_roles(
                member.guild.get_role(self.bot_config["guild"]["gatekeeper_role"]),
                reason="Interview: add gatekeeper role",
            )
            if not await self.conn.get_interview(member.id):
                await self.create_interview_channel(member, member.guild)

    @interview.command()
    async def approve(self, ctx):
        interview = await self.conn.get_interview_from_channel(ctx.message.channel.id)
        if interview:
            member = ctx.message.author.guild.get_member(interview[0])
            await member.add_roles(
                ctx.message.author.guild.get_role(
                    self.bot_config["guild"]["member_role"]
                ),
                reason="Interview: approved",
            )
            await member.remove_roles(
                ctx.message.author.guild.get_role(
                    self.bot_config["guild"]["gatekeeper_role"]
                ),
                reason="Interview: approved",
            )
            await ctx.send(f"Welcome to the server, {member.mention}!")
            await self.queue_channel_deletion(ctx.message.channel, member)

    @interview.command()
    async def deny(self, ctx):
        interview = await self.conn.get_interview_from_channel(ctx.message.channel.id)
        if interview:
            member = ctx.message.author.guild.get_member(interview[0])
            await ctx.send(
                f"We're really sorry, {member.mention}, but we do not think you are a good fit for {member.guild.name} at this time."
            )
            await self.queue_channel_deletion(ctx.message.channel, member)
            await asyncio.sleep(150)

    async def queue_channel_deletion(
        self, channel: discord.TextChannel, member: discord.Member
    ):
        archive_message = await channel.send("Archiving channel in five minutes.")
        await asyncio.sleep(60)
        await archive_message.edit(content="Archiving channel in four minutes.")
        await member.send(
            f"We're really sorry, {member.mention}, but we do not think you are a good fit for {member.guild.name} at this time.\nYou were automatically kicked."
        )
        await asyncio.sleep(60)
        await member.kick(reason="Interview: automatic kick after being denied.")
        await archive_message.edit(content="Archiving channel in three minutes.")
        await asyncio.sleep(60)
        await archive_message.edit(content="Archiving channel in two minutes.")
        await asyncio.sleep(60)
        await archive_message.edit(content="Archiving channel in one minute.")
        await asyncio.sleep(60)
        await channel.send("Archiving channel!")
        await asyncio.sleep(5)
        log_channel = channel.guild.get_channel(
            self.bot_config["guild"]["interview_log_channel"]
        )
        messages = await channel.history(limit=200, oldest_first=True).flatten()
        message_log = f"Message log for #{channel.name} ({channel.id}):\n==============================\n\n"
        for message in messages:
            message_log += f"{message.created_at.strftime('%Y-%m-%d %H:%M:%S')}: {message.author.name}#{message.author.discriminator} ({message.author.id}): {message.clean_content}\n\n"
        message_file = io.BytesIO(bytes(message_log, "utf-8"))
        await log_channel.send(
            f"Message log for #{channel.name} ({channel.id})",
            file=discord.File(message_file, filename="message_log.txt"),
        )
        await self.conn.delete_interview_entry(channel.id)
        await channel.delete(reason="Interview: automatic deletion")
