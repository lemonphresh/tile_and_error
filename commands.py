import discord
from discord.ext import commands
import config
import data
from data import (
    get_user_team,
    get_tile,
    format_tile_reveal_message,
    render_board_view,
    MoveLog,
    save_move_log,
)
from datetime import datetime
import time
import json
from pathlib import Path

user_team_cooldowns = {}  # key: (user_id, team_id), value: last use timestamp
COOLDOWN_DURATION = 20 * 60  # 20 minutes in seconds

def register_commands(bot: commands.Bot):

    @bot.command(name="select")
    async def select_tile(ctx, coord_str: str):
        now = time.time()  # get current time in seconds
        author_id = ctx.author.id
        team = get_user_team(author_id)
        refs_role = discord.utils.get(ctx.guild.roles, name="refs")
        if refs_role:
            role_mention = refs_role.mention
        else:
            role_mention = "@refs"  # fallback in case role not found

        if not team:
            await ctx.send("❌ You are not part of any team.")
            return

        # Clean up expired cooldowns
        expired_keys = [key for key, ts in user_team_cooldowns.items() if now - ts > COOLDOWN_DURATION]
        for key in expired_keys:
            del user_team_cooldowns[key]

        # Check if ANY user in the team is still on cooldown
        team_on_cooldown = any(
            now - ts < COOLDOWN_DURATION
            for (uid, tid), ts in user_team_cooldowns.items()
            if tid == team.id
        )

        if team_on_cooldown:
            await ctx.send("⏳ Your team has picked a tile already! Get to grinding!")
            return

        # parsing coordinate
        try:
            row_letter, col_number = coord_str.split(",")
            coord = (row_letter.strip().upper(), int(col_number.strip()))
        except Exception:
            await ctx.send("❌ Invalid format. Use: `!select A,2`.")
            return

        tile = get_tile(team.board, coord)
        if not tile:
            await ctx.send("❌ Invalid tile coordinates.")
            return

        if tile.revealed:
            await ctx.send(f"⚠️ Tile {coord[0]}{coord[1]} has already been revealed!")
            return

        tile.revealed = True
        data.move_log.append(
            MoveLog(
                team_id=team.id,
                discord_id=ctx.author.id,
                coord=coord,
                timestamp=datetime.utcnow().isoformat()
            )
        )
        
        save_move_log()

        # update cooldown
        user_team_cooldowns[(author_id, team.id)] = now

        await ctx.send(f"{format_tile_reveal_message(tile, ctx.author.display_name)}\n\n|| {role_mention} ||")

    @bot.command(name="tile_leaderboard")
    async def leaderboard(ctx):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        score_map = {
            1: 1,  # KC tile
            2: 2,  # Unique
            3: 3,  # Raid/NM
            "bomb": 4  # Bomb
        }

        leaderboard = []

        for team in data.teams:
            data.apply_move_log_to_board(team)  # sync revealed tiles

            score = 0
            bomb_count = 0

            for row in team.board:
                for tile in row:
                    if tile.revealed:
                        score += score_map.get(tile.tile_type, 0)
                        if tile.tile_type == "bomb":
                            bomb_count += 1

            leaderboard.append((team.id, score, bomb_count))

        leaderboard.sort(key=lambda x: x[1], reverse=True)

        if not leaderboard:
            await ctx.send("📊 No scores to show yet!")
            return

        lines = ["🏆 **Team Leaderboard:**"]
        for rank, (team_id, score, bomb_count) in enumerate(leaderboard, start=1):
            bomb_suffix = "💣" if bomb_count else ""
            lines.append(f"{rank}. Team {team_id}: **{score} points** ({bomb_count} bombs) {bomb_suffix}")

        await ctx.send("\n".join(lines))

    

    @bot.command(name="all_boards")
    async def all_boards(ctx):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        if not data.teams:
            await ctx.send("ℹ️ No teams have been created yet.")
            return

        for team in data.teams:
            data.apply_move_log_to_board(team)
            board_view = render_board_view(team.board, team.id)
            await ctx.send(f"🧩 **Team {team.id} Board:**\n```\n{board_view}\n```")

    @bot.command(name="board")
    async def view_board(ctx):
        team = get_user_team(ctx.author.id)
        if not team:
            await ctx.send("❌ You are not part of any team.")
            return
        
        board_view = render_board_view(team.board, team.id)
        await ctx.send(f"🧩 Here is your current board:\n```\n{board_view}\n```")

    @bot.command(name="team")
    async def show_team(ctx):
        team = get_user_team(ctx.author.id)
        if not team:
            await ctx.send("❌ You are not part of any team.")
            return

        member_list = "\n".join([f"- {member.rsn} (<@{member.discord_id}>)" for member in team.members])
        await ctx.send(f"👥 **Your Team Members:**\n\n{member_list}")

    @bot.command(name="tilecommands")
    async def list_commands(ctx):
        help_text = """
📜 **Available Commands**

`!select A,2` — Reveal the tile at the specified coordinate  
`!board` — View your team's current board progress
`!team` — Tag and show your team members  
`!moves` — Show move history  
`!tilecommands` — Show this command list
`!list_teams` - Show list of all teams and their members  

Admin-only commands:

`!undo_move [team_id]` — Undo last move for that team
"""
        await ctx.send(help_text)

    @bot.command(name="cooldowns")
    async def check_cooldowns(ctx):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        now = time.time()
        lines = []

        # collect cooldown info by team
        cooldowns_by_team = {}
        for (user_id, team_id), timestamp in user_team_cooldowns.items():
            remaining = int(COOLDOWN_DURATION - (now - timestamp))
            if remaining > 0:
                cooldowns_by_team.setdefault(team_id, []).append((user_id, remaining))

        if not cooldowns_by_team:
            await ctx.send("✅ No teams are currently on cooldown.")
            return

        for team_id, entries in cooldowns_by_team.items():
            lines.append(f"🕒 **Team {team_id}**:")
            for user_id, remaining in entries:
                minutes = remaining // 60
                seconds = remaining % 60
                lines.append(f"  <@{user_id}> — {minutes}m {seconds}s remaining")

        await ctx.send("\n".join(lines))

    @bot.command(name="reset_cooldown")
    async def reset_cooldown(ctx, team_id: int):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        affected = 0
        keys_to_remove = [key for key in user_team_cooldowns if key[1] == team_id]
        for key in keys_to_remove:
            del user_team_cooldowns[key]
            affected += 1

        if affected == 0:
            await ctx.send(f"ℹ️ No active cooldowns found for team {team_id}.")
        else:
            await ctx.send(f"✅ Reset cooldowns for team {team_id} (cleared {affected} entr{'y' if affected == 1 else 'ies'}).")

    @bot.command(name="completed_board")
    async def reveal_base_board(ctx):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You do not have permission to use this command.")
            return

        tile_path = Path("tiles.json")
        if not tile_path.exists():
            await ctx.send("❌ Could not find `tiles.json`.")
            return

        with open(tile_path, "r") as f:
            tile_data = json.load(f)

        # build a dummy team board from tile data
        dummy_board = data.create_board_template_from_json(tile_data)

        # reveal all tiles
        for row in dummy_board:
            for tile in row:
                tile.revealed = True

        board_text = render_board_view(dummy_board, team_id=0)
        await ctx.send(f"🧩 **Base Board (All Tiles Revealed):**\n```\n{board_text}\n```")


    @bot.command(name="moves")
    async def view_moves(ctx, team_id: int = None):        
        if team_id:
            # only allow if the user is an admin
            if ctx.author.id not in config.ADMIN_IDS:
                await ctx.send("❌ You do not have permission to view other teams' moves.")
                return

            # look up the team by ID
            team = next((t for t in data.teams if t.id == team_id), None)
            if not team:
                await ctx.send("❌ Could not find a team with that ID.")
                return
        else:
            # no team ID passed; check if the user is part of a team
            team = get_user_team(ctx.author.id)
            if not team:
                await ctx.send("❌ You are not part of any team.")
                return

        team_moves = [m for m in data.move_log if m.team_id == team.id]
        if not team_moves:
            await ctx.send(f"🕳️ No moves made yet for Team `{team.id}`.")
            return

        moves_text = "\n".join(
            [f"{m.timestamp} — <@{m.discord_id}> revealed {m.coord[0]}{m.coord[1]}" for m in team_moves]
        )
        await ctx.send(f"📜 **Move History for Team `{team.id}`:**\n\n{moves_text}")

    @bot.command(name="undo_move")
    async def undo_move(ctx, team_id: int):
        if ctx.author.id not in config.ADMIN_IDS:
            await ctx.send("❌ You don't have permission to use this command.")
            return

        team_moves = [m for m in data.move_log if m.team_id == team_id]
        if not team_moves:
            await ctx.send(f"❌ No moves found for team {team_id}.")
            return

        last_move = team_moves[-1]
        team = next((t for t in data.teams if t.id == team_id), None)

        if not team:
            await ctx.send(f"❌ No team found with ID {team_id}.")
            return

        tile = get_tile(team.board, last_move.coord)
        if tile:
            tile.revealed = False
            data.move_log.remove(last_move)
            save_move_log()
            await ctx.send(f"✅ Move undone for team {team_id} — {last_move.coord[0]}{last_move.coord[1]}")

            board_view = render_board_view(team.board, team.id)
            await ctx.send(f"🧩 Updated board:\n```\n{board_view}\n```")
        else:
            await ctx.send("❌ Could not find the tile to undo.")

    @bot.command(name="current_tile")
    async def current_tile(ctx):
        author_id = ctx.author.id
        team = get_user_team(author_id)

        if not team:
            await ctx.send("❌ You are not part of any team.")
            return
        
        data.apply_move_log_to_board(team)

        # get all moves for the team, sorted by timestamp
        team_moves = [m for m in data.move_log if m.team_id == team.id]
        if not team_moves:
            await ctx.send("ℹ️ Your team hasn't revealed any tiles yet.")
            return

        last_move = team_moves[-1]
        tile = get_tile(team.board, last_move.coord)
        print(tile)
        if tile and tile.revealed:
            await ctx.send(
                f"🧩 Your team's most recently revealed tile is **{last_move.coord[0]}{last_move.coord[1]}**:\n\n"
                f"{format_tile_reveal_message(tile, ctx.author.display_name)}"
            )
        else:
            await ctx.send("⚠️ Could not find the last revealed tile.")


    @bot.command(name="list_teams")
    async def list_teams(ctx):
        if not data.teams:
            await ctx.send("ℹ️ No teams have been created yet.")
            return

        message = "**📋 Team Roster:**\n"

        for team in data.teams:
            message += f"\n**Team {team.id}**:\n"

            if not team.members:
                message += "  — No members\n"
                continue

            for member in team.members:
                try:
                    message += f"  • {member.rsn}\n"
                except Exception:
                    message += f"  • Unknown user (<@{member.discord_id}>)\n"

        await ctx.send(message)

    @bot.command(name="hole")
    async def hole(ctx):
        message = "Oh, are you seeking hole?\n\n"
        message += "Here are some holes:\n"
        message += "1. 🕳️\n"

        await ctx.send(message)


## FUNNY STUFF NOW

    # @bot.command(name="buttlid")
    # async def buttlid(ctx):
    #     file_path = "buttlid.png"  

    #     try:
    #         with open(file_path, "rb") as f:
    #             picture = discord.File(f)
    #             await ctx.send(file=picture)
    #     except FileNotFoundError:
    #         await ctx.send("❌ Could not find the image file.")
