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
import os
from pathlib import Path
import discord
from discord.ext import commands
import tomlkit
from database import database as botdb
from bot import (
    interviews,
    starboard,
    user_commands,
    notes,
    gatekeeper,
    moderation,
    highlight,
)


config_file = Path("config.toml")

if not config_file.is_file():
    raise FileNotFoundError(
        "Config file not found! Try using the sample config in config.sample.toml"
    )

bot_config = tomlkit.parse(config_file.read_text())

if os.environ.get("COVEBOT_DATABASE"):
    bot_config["bot"]["database_url"] = os.environ.get("COVEBOT_DATABASE")


logger = logging.getLogger("discord")
logger.setLevel(bot_config["bot"]["logging_level"])
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

description = "General-purpose moderation bot for the Cove"

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(*bot_config["bot"]["prefixes"]),
    description=description,
    case_insensitive=True,
    allowed_mentions=discord.AllowedMentions(everyone=False, users=False, roles=False),
)


@bot.event
async def on_connect():
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Game(name="Starting... (please wait)"),
    )


@bot.event
async def on_disconnect():
    for cog in bot.cogs:
        bot.remove_cog(cog[0])


@bot.event
async def on_ready():
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print("------")

    logger.log(logging.INFO, f"Logged in as {bot.user.name} ({bot.user.id})")

    activity = "{}help".format(bot_config["bot"]["prefixes"][0])

    conn = await botdb.init_dbconn(bot_config["bot"]["database_url"])

    if bot_config["cogs"]["enable_user_commands"]:
        bot.add_cog(user_commands.UserCommands(bot, conn, logger))
    if bot_config["cogs"]["enable_advanced_gatekeeper"]:
        bot.add_cog(interviews.Interviews(bot, conn, bot_config, logger))
    elif bot_config["cogs"]["enable_simple_gatekeeper"]:
        bot.add_cog(gatekeeper.SimpleGatekeeper(bot, conn, bot_config, logger))
    if bot_config["cogs"]["enable_notes"]:
        bot.add_cog(notes.Notes(bot, conn, logger))
    if bot_config["cogs"]["enable_moderation"]:
        bot.add_cog(moderation.Moderation(bot, conn, bot_config, logger))
    if bot_config["cogs"]["enable_starboard"]:
        bot.add_cog(
            starboard.Starboard(
                bot, conn, await conn.get_starboard_settings(), bot_config, logger
            )
        )
    if bot_config["cogs"]["enable_highlights"]:
        bot.add_cog(highlight.Highlights(bot, conn, logger))
    logger.log(logging.INFO, f"Bot ready")

    await bot.change_presence(
        status=discord.Status.online, activity=discord.Game(name=activity)
    )


bot.run(bot_config["bot"]["token"])
