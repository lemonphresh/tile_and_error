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

user_team_cooldowns = {}  # key: (user_id, team_id), value: last use timestamp
COOLDOWN_DURATION = 20 * 60  # 20 minutes in seconds

def register_commands(bot: commands.Bot):

    @bot.command(name="select")
    async def select_tile(ctx, coord_str: str):
        now = time.time()  # get current time in seconds
        author_id = ctx.author.id
        team = get_user_team(author_id)

        if not team:
            await ctx.send("❌ You are not part of any team.")
            return

        cooldown_key = (author_id, team.id)
        # clean up expired cooldowns
        expired_keys = [key for key, ts in user_team_cooldowns.items() if now - ts > COOLDOWN_DURATION]
        for key in expired_keys:
            del user_team_cooldowns[key]
        
        # check if user is on cooldown
        last_used = user_team_cooldowns.get(cooldown_key)
        if last_used and now - last_used < COOLDOWN_DURATION:
            # remaining = int((COOLDOWN_DURATION - (now - last_used)) / 60)
            await ctx.send(f"Your team just picked a tile already! Get to grinding!")
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
        user_team_cooldowns[cooldown_key] = now

        await ctx.send(format_tile_reveal_message(tile, ctx.author.display_name))

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

    @bot.command(name="commands")
    async def list_commands(ctx):
        help_text = """
📜 **Available Commands**

`!select A,2` — Reveal the tile at the specified coordinate  
`!board` — View your team's current board progress
`!team` — Tag and show your team members  
`!moves` — Show move history  
`!commands` — Show this command list
`!list_teams` - Show list of all teams and their members  

Admin-only commands:

`!undo_move [team_id]` — Undo last move for that team
"""
        await ctx.send(help_text)

    @bot.command(name="moves")
    async def view_moves(ctx):
        team = get_user_team(ctx.author.id)
        if not team:
            await ctx.send("❌ You are not part of any team.")
            return

        team_moves = [m for m in data.move_log if m.team_id == team.id]
        if not team_moves:
            await ctx.send("🕳️ No moves made yet.")
            return

        moves_text = "\n".join(
            [f"{m.timestamp} — <@{m.discord_id}> revealed {m.coord[0]}{m.coord[1]}" for m in team_moves]
        )
        await ctx.send(f"📜 **Move History for Your Team:**\n\n{moves_text}")

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