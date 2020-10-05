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
import io
import json
import logging
import math
import re
import typing
import discord
from discord.ext import commands


class Tickets(commands.Cog):
    def __init__(self, bot, conn, ticket_settings, bot_config, logger):
        self.bot = bot
        self.conn = conn
        self.ticket_settings = ticket_settings
        self.bot_config = bot_config
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded tickets cog")
        print("Loaded tickets cog")

    # management commands
    @commands.group(help="Manage tickets.", aliases=["ticket"])
    async def tickets(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.help(ctx)

    @tickets.command()
    async def help(self, ctx):
        embed = discord.Embed(colour=discord.Colour(0x404ADD), title="Tickets help")
        embed.add_field(
            name="User commands",
            value=f"`{ctx.prefix}tickets help`: show help.\nReact to the message in <#{self.ticket_settings[1]}> to open a modmail ticket.",
            inline=False,
        )
        embed.add_field(
            name="Ticket management commands",
            value=f"`{ctx.prefix}tickets close`: closes the current ticket.\n`{ctx.prefix}tickets save`: saves a transcript for the current ticket.\n`{ctx.prefix}tickets delete`: deletes the current ticket channel.",
            inline=False,
        )
        embed.add_field(
            name="User management commands",
            value=f"`{ctx.prefix}tickets add <member: discord.Member>`: adds a member to the current ticket.\n`{ctx.prefix}tickets remove <member: discord.Member>`: remove a member from the current ticket.",
            inline=False,
        )
        await ctx.send(embed=embed)

    @tickets.group()
    @commands.has_permissions(manage_guild=True)
    async def config(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Current tickets config", colour=discord.Colour(0x404ADD)
            )
            embed.description = f"Watching in channel <#{self.ticket_settings[1]}> (ID: {self.ticket_settings[1]})\nTo message ID {self.ticket_settings[2]}\nFor the reaction {self.ticket_settings[3]}"
            embed.add_field(name="Welcome message", value=self.ticket_settings[4])
            await ctx.send(embed=embed)

    @config.command(name="set-message")
    async def set_message(self, ctx, message: discord.Message):
        await self.conn.set_ticket_channel(message.channel.id)
        await self.conn.set_ticket_message(message.id)
        self.ticket_settings = await self.conn.get_ticket_settings()
        await ctx.send(
            embed=discord.Embed(
                description=f"Now listening for reacts on message ID {self.ticket_settings[2]} in <#{self.ticket_settings[1]}>."
            )
        )

    @config.command(name="send")
    async def send_and_set(self, ctx, channel: discord.TextChannel = None):
        if not channel:
            channel = ctx.message.channel
        embed = discord.Embed(colour=discord.Colour(0x2EA7C8))
        embed.title = "Modmail"
        embed.description = f"React to this message with {self.ticket_settings[3]} to open a new modmail ticket."
        message = await channel.send(embed=embed)
        await message.add_reaction(self.ticket_settings[3])
        await self.set_message(ctx, message)

    @tickets.command(aliases=["reopen"])
    @commands.has_permissions(manage_messages=True)
    async def close(self, ctx):
        ticket = await self.conn.get_ticket(ctx.channel.id)
        if not ticket:
            await ctx.send(
                embed=discord.Embed(
                    description="This is not a ticket.", colour=discord.Colour(15158332)
                )
            )
            return True

    @tickets.command()
    @commands.has_permissions(manage_messages=True)
    async def add(self, ctx, members: commands.Greedy[discord.Member]):
        ticket = await self.conn.get_ticket(ctx.channel.id)
        if not ticket:
            await ctx.send(
                embed=discord.Embed(
                    description="This is not a ticket.", colour=discord.Colour(15158332)
                )
            )
            return True
        overwrites = ctx.message.channel.overwrites
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)
        await ctx.message.channel.edit(overwrites=overwrites)
        await ctx.send(
            embed=discord.Embed(
                description=f"Added {len(members)} users to this ticket.",
                colour=discord.Colour(0x2EA7C8),
            )
        )

    @tickets.command()
    @commands.has_permissions(manage_messages=True)
    async def remove(self, ctx, members: commands.Greedy[discord.Member]):
        ticket = await self.conn.get_ticket(ctx.channel.id)
        if not ticket:
            await ctx.send(
                embed=discord.Embed(
                    description="This is not a ticket.", colour=discord.Colour(15158332)
                )
            )
            return True
        overwrites = ctx.message.channel.overwrites
        for member in members:
            overwrites[member] = discord.PermissionOverwrite(read_messages=None)
        await ctx.message.channel.edit(overwrites=overwrites)
        await ctx.send(
            embed=discord.Embed(
                description=f"Removed {len(members)} users from this ticket.",
                colour=discord.Colour(0x2EA7C8),
            )
        )

    @tickets.command()
    @commands.has_permissions(manage_guild=True)
    async def archive(self, ctx):
        # ticket check goes here
        await ctx.trigger_typing()
        json_out = {
            "packVersion": 3,
            "timestamp": str(datetime.datetime.utcnow()),
            "messages": [],
            "channel": {
                "id": ctx.channel.id,
                "guild_id": ctx.guild.id,
                "name": ctx.channel.name,
                "topic": ctx.channel.topic,
                "type": 0,
                "nsfw": ctx.channel.is_nsfw(),
                "rate_limit_per_user": ctx.channel.slowmode_delay,
            },
        }
        history = await ctx.channel.history(limit=100).flatten()
        for message in history:
            message_json = {
                "id": message.id,
                "channel_id": message.channel.id,
                "content": message.stripped_content,
                "timestamp": str(message.created_at),
                "tts": message.tts,
                "pinned": message.pinned,
                "mention_everyone": message.mention_everyone,
                "author": {
                    "id": message.author.id,
                    "username": message.author.name,
                    "avatar": message.author.avatar,
                    "discriminator": message.author.discriminator,
                    "bot": message.author.bot,
                },
                "embeds": [],
                "attachments": [],
                "type": 0,
                "flags": 0,
            }
            if message.attachments:
                for attachment in message.attachments:
                    attachment_json = {
                        "id": attachment.id,
                        "url": attachment.url,
                        "proxy_url": attachment.proxy_url,
                        "filename": attachment.filename,
                    }
                    message_json["attachments"].append(attachment_json)
            if message.embeds:
                for embed in message.embeds:
                    embed_json = {
                        "title": embed.title,
                        "description": embed.description,
                    }
                    embed_json["footer"] = {
                        "text": embed.footer.text,
                        "icon_url": embed.footer.icon_url,
                    }
                    message_json["embeds"].append(embed_json)
            json_out["messages"].append(message_json)
        export_string = json.dumps(json_out, indent=2)
        export_file = io.BytesIO(bytes(export_string, "utf-8"))
        await ctx.send(
            content="Here you go!",
            file=discord.File(
                export_file,
                filename=f"export-{ctx.channel.name}-{str(datetime.datetime.utcnow())}.json",
            ),
        )
