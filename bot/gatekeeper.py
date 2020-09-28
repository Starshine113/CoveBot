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
from datetime import datetime

import discord
from discord.ext import commands


class SimpleGatekeeper(commands.Cog):
    def __init__(self, bot, conn, config, logger):
        self.bot = bot
        self.conn = conn
        self.bot_config = config
        self.logger = logger
        self.logger.log(logging.INFO, "Loaded simple gatekeeper cog")
        print("Loaded simple gatekeeper cog")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == self.bot_config["guild"]["guild_id"]:
            self.logger.log(
                logging.INFO,
                f"A new member joined {member.guild.name}: {member.name}#{member.discriminator} ({member.id})",
            )
            await member.add_roles(
                member.guild.get_role(self.bot_config["gatekeeper"]["gatekeeper_role"]),
                reason="Interview: add gatekeeper role",
            )
            await self.send_gatekeeper_message(member)

    async def send_gatekeeper_message(self, member: discord.Member):
        gatekeeper_channel = member.guild.get_channel(
            self.bot_config["gatekeeper"]["simple"]["gatekeeper_channel"]
        )
        await gatekeeper_channel.send(
            self.bot_config["gatekeeper"]["simple"]["message"].format(
                mention=member.mention
            )
        )

    @commands.command(help="Approve a user.")
    @commands.has_permissions(manage_guild=True)
    async def approve(self, ctx, member: discord.Member):
        await member.add_roles(
            ctx.message.author.guild.get_role(
                self.bot_config["gatekeeper"]["member_role"]
            ),
            reason="Gatekeeper: approved",
        )
        await member.remove_roles(
            ctx.message.author.guild.get_role(
                self.bot_config["gatekeeper"]["gatekeeper_role"]
            ),
            ctx.message.author.guild.get_role(
                self.bot_config["gatekeeper"]["simple"]["gatekeeper2_role"]
            ),
            reason="Gatekeeper: approved",
        )
        welcome_channel = member.guild.get_channel(
            self.bot_config["gatekeeper"]["welcome_channel"]
        )
        await welcome_channel.send(
            self.bot_config["gatekeeper"]["welcome_message"].format(
                guild=member.guild.name, mention=member.mention
            )
        )
        await ctx.send(
            f"User **{str(member)}** has been approved by **{str(ctx.author)}**."
        )
        self.logger.log(
            logging.INFO,
            f"Welcomed user {member.name}#{member.discriminator} ({member.id}) in #{welcome_channel.name} ({welcome_channel.id})",
        )
