to run the bot, you'll need a discord token.

touch .env in the root, add DISCORD_TOKEN variable in there.

grab your discord id and add it to the ADMIN_IDS variable in config.py (and whoever else's you might want as an admin)

add data to the `teams` declaration in `load_dummy_data_from_json`.

edit the tiles.json however you like.

run `python bot.py` in your console. voila
