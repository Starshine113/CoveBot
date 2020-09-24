# CoveBotn't

CoveBotn't is a general moderation bot for the Cove.

- Interview gatekeeper system
- Notes
- Starboard
- Some user commands
- Highlights

## Requirements

- PostgreSQL (tested down to 9.5)
- Python 3.6+
- The requirements listed in `requirements.txt`

## Installation

1. Create a venv
2. Install the requirements with `pip install -r requirements.txt`
3. Fill in the configuration file
5. Run the bot with `main.py`

## Usage

(All examples here assume a prefix of `--`)

### Starboard

Set a starboard channel with `--starboard channel <channel>`, set a star emoji with `--sb emoji <emoji>` (default: ⭐), and a limit with `--sb limit <limit>`.

Channels can be blacklisted with `--sb blacklist add`, and removed from the blacklist with `--sb blacklist remove`. Use `--sb blacklist` to view the current blacklist.

## Interviews

Set *all* IDs in `config.toml` and put at least one question in `guild.interview_questions`. Approve members with `--interview approve` in their interview channel, deny them with `--interview deny`.

## Notes

Set a note on a user with `--setnote <user> <note>`, delete a note with `--delnote <id>`, and list all notes for a user with `--notes <user>`.

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
