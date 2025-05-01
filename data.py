from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Union, Tuple, Literal, Optional

move_log: List[MoveLog] = []
# global team list to be populated from file data
teams: List[Team] = []

# --- move log structure ---
@dataclass
class MoveLog:
    team_id: int
    discord_id: int
    coord: tuple[str, int]
    timestamp: str

    def to_dict(self):
        return {
            "team_id": self.team_id,
            "discord_id": self.discord_id,
            "coord": list(self.coord),  # convert tuple to list for JSON
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            team_id=data["team_id"],
            discord_id=data["discord_id"],
            coord=data["coord"],
            timestamp=data["timestamp"]
        )

# --- team member structure ---
@dataclass
class Member:
    rsn: str
    discord_id: int  


# --- tile structure ---
TileType = Union[Literal[1], Literal[2], Literal[3], Literal["bomb"]] # either 1, 2, 3 or "bomb"
Coordinates = Tuple[str, int]  # e.g., ("A", 1)


@dataclass
class Tile:
    coordinates: Coordinates
    tile_type: TileType
    drop_source: str
    drop: str
    alternative_drop: str
    count: int
    notes: str
    description: str
    revealed: bool = False


# --- team structure ---
@dataclass
class Team:
    id: int
    members: List[Member]
    board: List[List[Tile]] = field(default_factory=list)  # 7x7 grid
    
move_log_file = Path("move_log.json")

def save_move_log(filename=move_log_file):
    with open(filename, "w") as f:
        json.dump([ml.to_dict() for ml in move_log], f, indent=2)

def load_move_log(filename=move_log_file):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            return [MoveLog.from_dict(m) for m in data]
    except FileNotFoundError:
        return []

def get_user_team(discord_id: int) -> Optional[Team]:
    for team in teams:
        if any(member.discord_id == discord_id for member in team.members):
            return team
    return None

def get_tile(board: List[List[Tile]], coord: tuple[str, int]) -> Optional[Tile]:
    row_letter, col_number = coord
    row_index = ord(row_letter.upper()) - ord("A")
    col_index = col_number - 1

    if 0 <= row_index < 7 and 0 <= col_index < 7:
        return board[row_index][col_index]
    return None

def create_board_template_from_json(json_data: List[dict]) -> List[List[Tile]]:
    layout = []
    for row_index in range(7):
        row_letter = chr(ord('A') + row_index)
        row = []
        for col_index in range(7):
            # find the tile data for this coordinate (row, col)
            tile_data = next((tile for tile in json_data if tile['coordinates'] == [row_letter, col_index + 1]), None)
            if tile_data:
                tile = Tile(
                    coordinates=tile_data['coordinates'],
                    tile_type=tile_data['tile_type'],
                    drop_source=tile_data['drop_source'],
                    drop=tile_data['drop'],
                    alternative_drop=tile_data['alternative_drop'],
                    count=tile_data['count'],
                    notes=tile_data['notes'],
                    description=tile_data['description'],
                    revealed=tile_data['revealed'],
                )
            else:
                # if no specific tile data is found, create a default tile
                tile = Tile(
                    coordinates=[row_letter, col_index + 1],
                    tile_type=1,
                    drop_source="General Graardor",
                    drop="Bandos Chestplate",
                    alternative_drop="",
                    count=1,
                    notes="",
                    description="Kill count or unique item drop",
                    revealed=False,
                )
            row.append(tile)
        layout.append(row)
    return layout

def load_dummy_data_from_json(file_path: str) -> None:
    global teams
    """
    loads the dummy data from a JSON file and creates teams with boards.

    args:
        file_path (str): Path to the JSON file containing tile data.

    returns:
        List[Team]: A list of teams with boards.
    """
    with open(file_path, 'r') as f:
        tile_data = json.load(f)

    teams = [
        Team(
            id=1,
            members=[
                Member(rsn="WhipMaster", discord_id=5678901234),
                Member(rsn="DharokTank", discord_id=6789012345),
            ],
            board=create_board_template_from_json(tile_data)
        ),
    ]

    print("Teams loaded:")
    for team in teams:
        print(f"Team {team.id}: {[member.rsn for member in team.members]}")


def format_tile_reveal_message(tile: Tile, display_name: str) -> str:
    coord = f"{tile.coordinates[0]}{tile.coordinates[1]}"
    
    if tile.tile_type == 1:
        return (
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. There, you encounter an army of {tile.drop_source}s! "
            f"It seems the only way past is by banding together with your team and brutally eliminating **{tile.count}** of them. "
            f"Good luck, team! May RNGesus be with you.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. \n\n"
            f"Otherwise, track your team’s KC progress by filtering to see **{tile.drop_source} KC** in WOM."
        )

    elif tile.tile_type == 2:
        alt = f" **OR {tile.alternative_drop}**" if tile.alternative_drop else ""
        note_line = f"\n📝 **Note:** {tile.notes}" if tile.notes else ""
        plural = "s" if tile.count > 1 else ""
        return (
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. You encounter a stinky little troll blocking your path… "
            f"looks a lot like Healsha with a pair of glasses and a mustache on. Curious.\n\n"
            f"The wretched creature demands **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source} to be delivered to him before he will let you pass. \n\n"
            f"What a greedy little bastard! Good luck, team!{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary."
        )

    elif tile.tile_type == 3:
        note_line = f"\n📝 **Note:** {tile.notes}" if tile.notes else ""
        return (
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. Before you lies a vast pit... A booming voice echoes out from it, "
            f"rattling your chest and shaking the trees around you:\n\n"
            f"“**I DEMAND A UNIQUE FROM {tile.drop_source.upper()} TO BE PLACED BEFORE MY HOLE. "
            f"BRING IT TO ME AND I SHALL ERECT A BRIDGE FOR YOU TO BE ABLE TO SAFELY TRAVERSE MY HOLE.**”\n\n"
            f"The voice sounds a little bit like Healsha’s. How is he everywhere?? Well, best be getting to it. \n\n"
            f"Good luck, team!{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary."
        )

    elif tile.tile_type == "bomb":
        note_line = f"\n📖 **READ THIS:** {tile.notes}" if tile.notes else ""
        return (
            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"Oho! Well, well, would you look at that. You’ve stumbled across one of the bombs that Healsha has scattered throughout the world! "
            f"It’s up to you to defuse it. Upon further inspection, Healsha left some instructions on how to do just that… That’s uncharacteristically kind. \n\n"
            f"The instructions read:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"{note_line}"
        )
    else:
        return f"🎉 `{display_name}` revealed tile **{coord}**. (Unrecognized tile type: {tile.tile_type})"

def render_board_view(board: List[List[Tile]], team_id: int) -> str:
    """
    Returns a formatted string of the bingo board using emojis.
    Includes row (A–G) and column (1–7) headers for reference.
    Takes into account the moves in the move_log to determine revealed tiles.
    """
    emoji_map = {
        1: " 1️⃣",
        2: " 2️⃣",
        3: " 3️⃣",
        "bomb": " 💣",
        "unrevealed": " ⬜",
    }

    score_map = {
        1: 1,
        2: 2,
        3: 3,
        "bomb": 4,
    }

    total_score = 0

    # Filter the move_log to get moves for the given team
    team_moves = [move for move in move_log if move.team_id == team_id]

    # Set the revealed status of tiles based on the move log
    revealed_coords = set((move.coord[0], move.coord[1]) for move in team_moves)

    output = ["    1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣"]  # column headers using number emojis

    for row_index, row in enumerate(board):
        row_label = chr(ord("A") + row_index)
        row_str = f"{row_label}  "  # row label
        for tile in row:
            coord = (tile.coordinates[0], tile.coordinates[1])

            if coord in revealed_coords:
                tile.revealed = True  # Set the tile as revealed if it's in the move log

            if not tile.revealed:
                row_str += emoji_map["unrevealed"]
            else:
                row_str += emoji_map[tile.tile_type]
                total_score += score_map[tile.tile_type]
        output.append(row_str)

    output.append(f"\n🏆 ** Total Team Points: {total_score} **")

    return "\n".join(output)

def apply_move_log_to_board(team):
    # Reset all tiles
    for row in team.board:
        for tile in row:
            tile.revealed = False

    # Apply moves relevant to this team
    for move in move_log:
        if move.team_id == team.id:
            tile = get_tile(team.board, move.coord)
            if tile:
                tile.revealed = True