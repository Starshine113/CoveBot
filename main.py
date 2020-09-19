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
from bot import interviews


config_file = Path("config.toml")

if not config_file.is_file():
    raise FileNotFoundError(
        "Config file not found! Try using the sample config in config.sample.toml"
    )

bot_config = tomlkit.parse(config_file.read_text())

if os.environ.get("COVEBOT_DATABASE"):
    bot_config["db"]["database_url"] = os.environ.get("COVEBOT_DATABASE")


logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

description = "General-purpose moderation bot for the Cove"

bot = commands.AutoShardedBot(
    command_prefix=commands.when_mentioned_or(*bot_config["bot"]["prefixes"]),
    description=description,
    case_insensitive=True,
)


@bot.event
async def on_ready():
    print("Logged in as")
    print(bot.user.name)
    print(bot.user.id)
    print("------")

    logger.log(logging.INFO, f"Logged in as {bot.user.name} ({bot.user.id})")

    activity = "{}help".format(bot_config["bot"]["prefixes"][0])

    await bot.change_presence(activity=discord.Game(name=activity))

    conn = await botdb.init_dbconn(bot_config["db"]["database_url"])

    bot.add_cog(interviews.Interviews(bot, conn, bot_config, logger))

    logger.log(logging.INFO, f"Bot ready")


bot.run(bot_config["bot"]["token"])
