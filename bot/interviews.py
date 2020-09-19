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
import logging
import uuid
import discord
from discord.ext import commands


class Interviews(commands.Cog):
    def __init__(self, bot, conn, config, logger):
        self.bot = bot
        self.conn = conn
        self.bot_config = config
        self.logger = logger

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if (
            isinstance(error, commands.CommandOnCooldown)
            or isinstance(error, commands.CheckFailure)
            or isinstance(error, commands.CheckAnyFailure)
        ):
            pass
        elif isinstance(error, commands.CommandNotFound):
            await ctx.send("Command not found!")
        else:  # for debugging purposes, probably very insecure for production
            error_id = str(uuid.uuid4())
            self.logger.log(
                logging.WARN, "Internal error occurred ({}): {}".format(error_id, error)
            )
            await ctx.send(
                "❌ Internal error occurred! Please join the support server and send the developer this ID: `{}`".format(
                    error_id
                )
            )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            self.logger.log(
                logging.INFO,
                f"A new member joined {member.guild.name}: {member.name}#{member.discriminator} ({member.id})",
            )
            await member.add_roles(
                member.guild.get_role(self.bot_config["guild"]["gatekeeper_role"]),
                reason="Interview: add gatekeeper role",
            )
            if not await self.conn.get_interview(member.id):
                await self.create_interview_channel(member, member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            self.logger.log(
                logging.INFO,
                f"A member left {member.guild.name}: {member.name}#{member.discriminator} ({member.id})",
            )
            interview = await self.conn.get_interview(member.id)
            if interview:
                channel_id = interview[1]
                channel = member.guild.get_channel(channel_id)
                await channel.send(
                    f"{member.name} left {member.guild.name} before finishing their interview."
                )
                await self.queue_channel_deletion(channel, member, False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        interview = await self.conn.get_interview_from_channel(payload.channel_id)
        if interview:
            if (
                payload.user_id == interview[0]
                and payload.message_id == interview[3]
                and str(payload.emoji) == "👍"
            ):
                channel = payload.member.guild.get_channel(payload.channel_id)
                await self.send_next_question(
                    interview,
                    channel,
                )
                message = await channel.fetch_message(interview[3])
                await message.remove_reaction("👍", payload.member)

    async def send_next_question(self, interview, channel: discord.TextChannel):
        questions = self.bot_config["guild"]["interview_questions"]
        if interview[2] < len(questions):
            self.logger.log(
                logging.INFO,
                f"Sent question {interview[2]} to #{channel.name} ({channel.id})",
            )
            await channel.send(questions[interview[2]])
            await self.conn.increment_question(interview[2] + 1, channel.id)

    async def send_welcome_message(
        self, member: discord.Member, channel: discord.TextChannel
    ):
        await asyncio.sleep(1)
        embed = discord.Embed(
            title="Welcome",
            colour=discord.Colour(0x7ED321),
            description=f"Welcome to {member.guild.name}, {member.mention}!\nTo start your interview, or have the bot send the next question of the interview, react to this message with 👍.",
        )
        message = await channel.send(f"Welcome, {member.mention}!", embed=embed)
        await message.add_reaction("👍")
        await message.pin()
        self.logger.log(
            logging.INFO, f"Sent welcome message to #{channel.name} ({channel.id})"
        )
        return message

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
        welcome_message = await self.send_welcome_message(member, channel)
        await self.conn.create_interview(member.id, channel.id, welcome_message.id)
        self.logger.log(
            logging.INFO, f"Created welcome channel #{channel.name} ({channel.id})"
        )
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
            message = f"Added the gatekeeper role to {member.mention}."
            if not await self.conn.get_interview(member.id):
                channel = await self.create_interview_channel(member, member.guild)
                message += f"\nCreated interview channel {channel.mention}."
            await ctx.send(message)

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
            welcome_channel = member.guild.get_channel(
                self.bot_config["guild"]["welcome_channel"]
            )
            await welcome_channel.send(
                self.bot_config["guild"]["welcome_message"].format(
                    guild=member.guild.name, mention=member.mention
                )
            )
            self.logger.log(
                logging.INFO,
                f"Welcomed user {member.name}#{member.discriminator} ({member.id}) in #{welcome_channel.name} ({welcome_channel.id})",
            )
            await self.queue_channel_deletion(ctx.message.channel, member, False)

    @interview.command()
    async def deny(self, ctx):
        interview = await self.conn.get_interview_from_channel(ctx.message.channel.id)
        if interview:
            member = ctx.message.author.guild.get_member(interview[0])
            await ctx.send(
                f"We're really sorry, {member.mention}, but we do not think you are a good fit for {member.guild.name} at this time."
            )
            await self.queue_channel_deletion(ctx.message.channel, member, True)
            await asyncio.sleep(150)

    async def queue_channel_deletion(
        self, channel: discord.TextChannel, member: discord.Member, kick: bool
    ):
        self.logger.log(
            logging.INFO,
            f"Deleting channel #{channel.name} ({channel.id}) in five minutes",
        )
        archive_message = await channel.send("Archiving channel in five minutes.")
        await self.conn.delete_interview_entry(channel.id)
        await asyncio.sleep(60)
        await archive_message.edit(content="Archiving channel in four minutes.")
        if kick:
            await member.send(
                f"We're really sorry, {member.mention}, but we do not think you are a good fit for {member.guild.name} at this time.\nYou were automatically kicked."
            )
            await asyncio.sleep(5)
            await member.kick(reason="Interview: automatic kick after being denied.")
        await asyncio.sleep(60)
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
        self.logger.log(logging.INFO, f"Deleting #{channel.name} ({channel.id})")
        await channel.delete(reason="Interview: automatic deletion")
