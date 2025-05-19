from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Union, Tuple, Literal, Optional
import random

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
                
            ],
            board=create_board_template_from_json(tile_data)
        ),
        
        # Team(
        #     id=5,
        #     members=[
        #         Member(rsn='test user 1', discord_id=),
        #         Member(rsn='test user 2', discord_id=)
        #     ],
        #     board=create_board_template_from_json(tile_data)
        # ),
    ]

    print("Teams loaded:")
    for team in teams:
        print(f"Team {team.id}: {[member.rsn for member in team.members]}")

import random

def format_tile_reveal_message(tile: Tile, display_name: str) -> str:
    coord = f"{tile.coordinates[0]}{tile.coordinates[1]}"
    
    # shared helpers
    alt = f" **OR {tile.alternative_drop}**" if getattr(tile, "alternative_drop", None) else ""
    note_line = f"\n📝 **Note:** {tile.notes}" if getattr(tile, "notes", None) else ""
    plural = "s" if getattr(tile, "count", 1) > 1 else ""

    if tile.tile_type == 1:  # kill count tiles
        variants = [
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. There, you encounter an army of {tile.drop_source}s! "
            f"It seems the only way past is by ~~holding hands with~~ banding together with your team and brutally eliminating **{tile.count}** of them. "
            f"Good luck, team! May RNGesus be with you.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You step into tile {coord}, only to be ambushed by a swarm of {tile.drop_source}s. "
            f"They hiss in unison: 'Only the strongest may pass... after slaying **{tile.count}** of us!'\n\n"
            f"Guess that means it's time for carnage. Good luck, team.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A battered sign creaks in the wind at tile {coord}. It reads:\n"
            f"“⚔️ **Warning: {tile.drop_source} Territory Ahead! Trespassers Will Be Slain or I Guess Maybe You Need to Slay {tile.count} of Us First.**”\n\n"
            f"What a strange challenge. Fortunately, your team is built different. Get to it!\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid OR have killed this boss at any point during this competition, log out to update WOM and, take a screenshot of your starting KC in the collection log before you start.\n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You descend into a cavern echoing with monstrous shrieks. You've stumbled upon a camp of {tile.drop_source}s — and they're not thrilled to see visitors.\n\n"
            f"To survive, you must cut down **{tile.count}** of the beasts. Or tenderly kiss them. No, probably just kill them. (Maybe both?)\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid OR have killed this boss at any point during this competition, log out to update WOM and, take a screenshot of your starting KC in the collection log before you start.\n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

             f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"As your team crosses into tile {coord}, a piercing shriek cuts through the air. "
            f"Suddenly, **{tile.count}** furious {tile.drop_source}s descend from the sky like divebombing pigeons on a bread truck, or Healsha when hole pics are around. "
            f"Time to swat 'em down. Good luck!\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You set foot on tile {coord} and immediately step in something… squishy. "
            f"A pack of **{tile.count}** {tile.drop_source}s erupts from the muck and rushes toward your group with wild abandon. "
            f"Defend yourself!\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"Tile {coord} is eerily quiet... until the ground cracks open beneath your feet, and **{tile.count}** {tile.drop_source}s climb out grinning. "
            f"One of them whispers, 'We have been *waiting* for you.'\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"As you step into tile {coord}, you get goosebumps as you feel something lingering around you. "
            f"Moments later, **{tile.count}** {tile.drop_source}s spawn around with loud POP, POP, POPs. "
            f"Get to slaying!\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You hear battle music start to play... and then spot **{tile.count}** {tile.drop_source}s doing synchronized squats ahead. Look at those peaches!\n\n"
            f"Intimidating. But nothing a little bloodshed won't solve. Move out! Clap 'em!\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A foul stench wafts across tile {coord}. You know it before you see it: "
            f"**{tile.count}** {tile.drop_source}s camped out, ripping ass and sharpening blades. "
            f"Time to clean house.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"The sky dims as a huge shadow sweeps over tile {coord}. "
            f"Turns out it's just a giant pile of **{tile.count}** {tile.drop_source}s stacked in a trench coat. "
            f"You know what must be done.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You trip and fall face-first into tile {coord}, only to look up and see **{tile.count}** {tile.drop_source}s grinning down at you. "
            f"They hand you a sword. How polite.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A nearby sign reads: 'Danger ahead: **{tile.drop_source}s** crossing.' You scoff. "
            f"Then **{tile.count}** of them round the corner, eyes glowing, blades drawn.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You barely set foot on tile {coord} before a trumpet sounds. "
            f"Out marches a parade of **{tile.count}** {tile.drop_source}s in perfect formation. "
            f"Too bad this isn't a celebration — it's a deathmatch.\n\n"
            f"📖 **READ THIS:** If you have *less than 5 KC* of this boss or raid, take a screenshot of your starting KC in the collection log before you start. If you have killed this boss at any point during this competition, EVERYONE must log out to update WOM and then please provide a starting screenshot of the team's WOM overview of that boss/raid's KC data. \n\n"
            f"Otherwise, track your team's KC progress by filtering to see **{tile.drop_source} KC** in WOM.",
        ]
        return random.choice(variants)

    elif tile.tile_type == 2:  # collection tiles
        variants = [
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. You encounter a stinky little troll blocking your path… "
            f"looks a lot like Healsha with a pair of glasses and a mustache on. Curious.\n\n"
            f"The wretched creature demands **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source} to be delivered to him before he will let you pass. \n\n"
            f"What a greedy little bastard! Good luck, team!\n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A dusty merchant at tile {coord} eyes you warily. 'I won't let you pass unless you bring me **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}!' he grumbles. \n\n"
            f"Apparently loot is currency now. Good luck getting that trade to go through. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You stumble upon a floating treasure chest sealed shut. An inscription reads: "
            f"'Within me, a key. To unlock me, however, you must bring me **{tile.count} {tile.drop}{plural}**{alt} looted from {tile.drop_source}.'\n\n"
            f"You swear the voice came from inside the box... creepy. \n\n"
            f"In the distance, you see a magical gate sealed shut. We're gonna need that key... Good luck, team! \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A spectral banker blocks the path at tile {coord}. He clutches a dusty ledger and mutters,\n"
            f"“No one passes without presenting **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}....”\n\n"
            f"You suppose it wouldn't hurt bolstering your bank value a bit in the process. Good luck looting, team!\n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode.\n"
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A talking, shirtless frog sits smugly at tile {coord}, croaking:\n"
            f"“No entry unless you bring me **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}!”\n\n"
            f"You're about to ask why it was specified that he was shirtless, but then he does a fancy little dance, charming you into doing whatever he wants without question. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode.\n"
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

             f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You arrive at tile {coord} and find a sentient cabbage blocking your path. "
            f"It squeaks, 'No passage without **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}!' before rolling slightly closer... menacingly.\n\n"
            f"You didn't think cabbages could be menacing. You were wrong. Good luck. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A cloaked figure looms over tile {coord}. It rasps, 'You want to pass? Bring me **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}, or rot like the others...'\n\n"
            f"A pile of bones lies ominously beside it. Best not join them. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A massive bouncer blocks tile {coord}, arms folded. 'No entry,' he grunts, unless you are carrying **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}.'\n\n"
            f"He's wearing some sick-ass reflective sunglasses and has huge, gorgeous biceps. You blush. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"At tile {coord}, you encounter a haunted vending machine. "
            f"The display flashes: 'Insert **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source} to continue.'\n\n"
            f"You're not sure where the slot is, or if it accepts noted items. Either way, good luck, team. I'm sure you'll find the hole. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A dramatic cutscene begins as you enter tile {coord}. A booming narrator shouts:\n"
            f"'ONLY THE WORTHY WHO COLLECT **{tile.count} {tile.drop.upper()}{plural.upper()}**{alt.upper()} FROM {tile.drop_source.upper()} SHALL PROCEED!'\n\n"
            f"You try to skip the cutscene but there's no button. Guess you're stuck doing the task. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You discover a giant rubber duck sitting in the middle of tile {coord}. It honks loudly and spits out a note: "
            f"'Quack. Bring **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}. Or else.'\n\n"
            f"You have no idea what 'or else' means coming from this fella, but you're not about to take any chances. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"Tile {coord} reveals a snooty alchemist holding a golden chalice. 'Ah yes,' he sniffs. "
            f"'My potion requires **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}. Be quick about it!'\n\n"
            f"You consider throwing the chalice at him, but that won't get the drops. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A tiny raccoon in a crown is sitting at tile {coord}. He squeaks, 'Prove your worth! Fetch me **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}!' "
            f"Then he throws a peanut at your head.\n\n"
            f"You catch it in your mouth to assert dominance, but quickly realize that chewing on an unshelled peanut isn't pleasant. Better get to work. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You step into tile {coord} and are greeted by a statue that springs to life. 'Halt!' it cries. "
            f"'Bring forth **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}, or remain frozen in time!'\n\n"
            f"Suddenly, 'If I Could Turn Back Time' by Cher starts playing in the distance. Perfect jam to get some drops to. Head out! \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You trip over a magical scroll on tile {coord}. It unfurls itself and reads aloud:\n"
            f"'Retrieve **{tile.count} {tile.drop}{plural}**{alt} from {tile.drop_source}, or suffer mild embarrassment.'\n\n"
            f"Mild embarrassment? Unacceptable. Go get the drops. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",
        ]
        return random.choice(variants)

    elif tile.tile_type == 3:  # unique item tiles
        variants = [
            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You venture forth to tile {coord}. Before you lies a vast pit... A booming voice echoes out from it, "
            f"rattling your chest and shaking the trees around you:\n\n"
            f"“**I DEMAND A UNIQUE FROM {tile.drop_source.upper()} TO BE PLACED BEFORE MY HOLE. "
            f"BRING IT TO ME AND I SHALL ERECT A BRIDGE FOR YOU TO BE ABLE TO SAFELY TRAVERSE MY HOLE.**”\n\n"
            f"The voice sounds a little bit like Healsha's. That figures, what with the 'hole' and 'erect' descriptors. Well, best be getting to it. \n\n"
            f"Good luck, team!\n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A glowing rift blocks the path at tile {coord}, pulsing with energy like that you've seen from {tile.drop_source}. "
            f"An otherworldly whisper seeps into your mind:\n\n"
            f"“**FEED ME A UNIQUE FROM {tile.drop_source.upper()} AND I SHALL OPEN THE WAY.**”\n\n"
            f"It smells like Clodsire droppings around here... You'll need that unique, team. It is too stinky to stay here. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode. "
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A majestic shrine hums with arcane energy. An ancient voice declares:\n"
            f"“ONLY A **UNIQUE ITEM** FROM {tile.drop_source.upper()} SHALL SATISFY THE ALMIGHTY GODS, WHO WILL THEN BENEVOLENTLY ALLOW YOU TO LIVE AND CONTINUE YOUR JOURNEY.”\n\n"
            f"Weird how the gods always demand the rarest stuff. Good luck, team!\n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode.\n"
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",

            f"🎉 `{display_name}` revealed tile **{coord}**.\n\n"
            f"The air crackles with static. A disembodied voice coming from seemingly everywhere around you whispers:\n"
            f"“You wish to proceed? Then, stinky butts, you must offer a **unique** stolen from {tile.drop_source}.”\n\n"
            f"You've been warned. May the RNG gods smile upon you. \n\n{note_line}\n\n"
            f"📖 **READ THIS:** Drops must be visible in your chat box with the event passcode.\n"
            f"Be sure to turn your loot threshold down so you can see the drops, if necessary.",
        ]
        return random.choice(variants)

    elif tile.tile_type == "bomb":
        note_line = f"\n📖 **READ THIS:** {tile.notes}" if getattr(tile, "notes", None) else ""

        variants = [
            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"Oho! Well, well, would you look at that. You've stumbled across one of the bombs that Healsha has scattered throughout the world! "
            f"It's up to you to defuse it. Upon further inspection, Healsha left some instructions on how to do just that… That's uncharacteristically kind. \n\n"
            f"The instructions read:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A pulsing red glow emanates from tile {coord}... it's one of Healsha's infamous bombs! "
            f"A sticky note (literally, it's sticky... hm...) is taped to it: \n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"Damn. Alright. Get to it, team.\n\n{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You spot a crate with blinking lights and duct tape that reads: “DO NOT TOUCH.”\n"
            f"You touch it.\n\n"
            f"A note flutters out:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"Classic Healsha. Handle with care. \n\n{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A suspicious humming noise leads you to a moss-covered barrel... with an LED countdown.\n\n"
            f"Someone (you know who) scribbled instructions on the side:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"You've got this. Probably. \n\n{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"You find a glowing orb surrounded by runes, crackling with wild energy. Tied to it with twine is a crude, slightly damp label:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"Looks like Healsha's handiwork. Smells like Healsha's handiwork. \n\n{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"The earth shakes slightly as you arrive. A half-buried, rune-etched sphere pulses ominously in the dirt.\n"
            f"A charred scroll nearby reads:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"Defuse it. Or... run? Nah, defuse it. \n\n{note_line}",

            f"💣 `{display_name}` revealed tile **{coord}**.\n\n"
            f"A chirping, mechanical sound draws you to tile {coord}. You lift a rock and find a blinking gnome hat.\n"
            f"Attached to it is a sticky note:\n\n"
            f"“**{tile.drop}** — *{tile.description}*”\n\n"
            f"What the hell is this man building? Good luck. \n\n{note_line}",
        ]
        return random.choice(variants)

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

    # filter the move_log to get moves for the given team
    team_moves = [move for move in move_log if move.team_id == team_id]

    # set the revealed status of tiles based on the move log
    revealed_coords = set((move.coord[0], move.coord[1]) for move in team_moves)

    output = ["    1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣"]  # column headers using number emojis

    for row_index, row in enumerate(board):
        row_label = chr(ord("A") + row_index)
        row_str = f"{row_label}  "  # row label
        for tile in row:
            coord = (tile.coordinates[0], tile.coordinates[1])

            if coord in revealed_coords:
                tile.revealed = True  # set the tile as revealed if it's in the move log

            if not tile.revealed:
                row_str += emoji_map["unrevealed"]
            else:
                row_str += emoji_map[tile.tile_type]
                total_score += score_map[tile.tile_type]
        output.append(row_str)

    output.append(f"\n🏆 ** Total Team Points: {total_score} **")

    return "\n".join(output)

def apply_move_log_to_board(team):
    # reset all tiles
    for row in team.board:
        for tile in row:
            tile.revealed = False

    # apply moves relevant to this team
    for move in move_log:
        if move.team_id == team.id:
            tile = get_tile(team.board, move.coord)
            if tile:
                tile.revealed = True