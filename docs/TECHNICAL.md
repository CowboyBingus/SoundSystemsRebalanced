# Sound Systems Rebalanced: technical notes

Steam build 25480438 (EXE 1.8.46015.0, Wwise 2024.1.9). Offsets below are for that build; the mod checks both
module hashes and does nothing on any other build.

The mod was developed as Mission Music Fix (v1.0: the volume fix; v1.1: the silent-music fix), neither released.
The live tests below ran on those builds; Sound Systems Rebalanced v1.0 renames the mod (title, module
`mods/cowboybingus/sound_systems_rebalanced`, log `SoundSystemsRebalanced.log`) and changes no behavior. Its music
bank archive is byte for byte the one tested.

## The cause

All mission music runs through one Wwise bus, `music` (`0xEDF036D6`; its chain is `0xC8D298AC` > `0x068D30DE` >
`music` > `0xB03E4E37` > `0xE534A105` > master). That bus has a state attenuation in the init bank: when the
global state group `environment_shiphub_room` (`0xEC643124`) is `shiphub_view` (`0x08EEC31C`), its bus volume is
-6 dB. The other values are `shiphub_deck`, `shiphub_hangar`, `shiphub_armory` and `shiphub_alcove`; none of them
changes the music bus.

Only five Wwise events set that group: `set_state_shiphub_view`, `_deck`, `_armory`, `_hangar` and `_alcove`
(bank `env_ship`). The Super Destroyer's level fires them from trigger volumes as the player moves between rooms.
No game code and no other event sets it, so when a mission starts the group keeps the last room the player was
in. In missions it reaches only the music bus (its other users are ship ambience, ship crew foley and a ship
voice/cutscene bus).

The names come from the FNV-1 hashes Wwise uses: the ship level's own strings (`set_state_shiphub_view`,
`ShipHub_View`, ...) hash to the event and state ids above.

### Measurements

- Static: every music bank and the init bank's global settings were parsed; the `music` bus's state chunk holds
  the -6 dB entry; the five events are the only setters.
- Live, in an Automaton mission with only the loader and an audio probe installed: switching the state between
  `shiphub_view` and `shiphub_hangar` every 40 s (through Wwise's SetState) moved the `music` bus against its
  input bus between -5.07 dB and +0.93 dB in all eight windows: a 6.00 dB step.
- Real play: one session showed both levels, a mission joined and launched from the host's hangar at 0 dB and
  the next mission launched from the war-table area at -6 dB.

## What the mod does

- Every 0.25 s of game time (frame times added up, no clock call) it reads the game state, a `u32` at
  `[game.dll + 0x3326340] + 0xAC21C`: 1 splash, 2 title, 5 preparing the ship, 3 ship, 6 preparing a mission
  (loading), 4 mission. Hellpod Drop Hold and Better Lobby Management read the same value. Joining a mission in
  progress also passes through 6 and 4.
- When the state enters 6 or 4 from any other value (or is 6 or 4 at the first read), it calls the engine's Lua
  binding `stingray.Wwise.set_state('environment_shiphub_room', 'shiphub_view')` once and logs one line. Setting
  the value a war-table launch already left is a no-op in Wwise.
- The game object's pointer (`[game.dll + 0x3326340]`) is read once and kept while the state reads back as a
  number up to 64; otherwise it is read again at the next check.

Nothing is written to game memory, and no game or Wwise function is called directly.

## Cost

| Path | Per frame | In-game cost |
| --- | --- | --- |
| most frames | adds the frame time, no call | no system call |
| every 0.25 s | 1 `ReadProcessMemory` (4 bytes) | about 1-2 us |
| first check, or after an implausible value | 1 more `ReadProcessMemory` (8 bytes) | about 1-2 us |
| mission start | 1 `stingray.Wwise.set_state`, 1 log line | unmeasured in game |

No page queries, no allocation per frame (two small buffers made at load; tested at 0 bytes per frame, compiled
and interpreted, in the game's `lua51.dll`), and no C types per frame.

## Silent music on unmapped biomes

### The cause

- Music tracks of type switch choose a sub-track by the global Wwise state `ENVIRONMENT_Planet_Biome`
  (`0x42FF4D50`, a state group).
- All 48 such tracks list the same 9 values, one per sub-track: arctic, forest, forest_snow, grassland, None
  (`0x2CA33BDB`), `0xD513EAAE`, rocky, sandy, savanna. Their default switch is None.
- The game has 14 biomes (its planet database, read live). Seven are not listed: swamp, deciduous, coniferous,
  desert, oasis, bug_hiveworld and rift_active.
- The music plugin keeps only the sub-tracks whose value equals the state and falls back to nothing. The default
  is used only while the state was never set. So on those biomes the track plays silence until the music moves
  to another segment.
- Every music segment of the start-intensity playlist is a single such track. That playlist starts at each drop
  and respawn, after 40 s of designed silence, so the music stays silent until the intensity changes.
- Four of the five biome-keyed music switches (`0x116C7F93`, `0x3C28B5C6`, `0x1AC07560` = Automaton drop music,
  `0x2546F4AC`) have no wildcard branch either. The fifth, `0x20D39FFE`, has one.

Live, Automaton front with test tunes and an audio probe:

- Swamp: the start playlist ran ~150 s and ~170 s with no voice and no signal on the music bus.
- Grassland: the same playlist played its first segment at 46-52 s and a second at ~97 s.

### The patch

`scripts/biome_patch.py` writes a patched copy of the `music_init` sound bank (wwise_bank
`content/audio/music_init`) into `Music/` of the release:

- Each of the 48 biome tracks gets 7 sub-tracks, one per missing biome. Each is a copy of the None sub-track's
  clip (same source, trims and duration), and the biome's id is added to the association list. The None
  sub-track is one clip without automation on all 48 tracks.
- Each of the 4 switches gets a wildcard node (key 0) as the root's first child, pointing to the None branch.
  That also covers biomes added later; the tracks need a rebuild for those.
- `music_init` loads at boot, and Wwise keeps the first-loaded copy of an object, so its copies are the ones the
  game uses:
  - It already defines 24 of the tracks and `0x116C7F93`.
  - The other 24 tracks and 3 switches exist only in the four mission banks, byte-identical in all four. They
    are copied into `music_init` with the same edits.
  - The mission banks (25 MB each, and what music-replacement mods ship) are not touched.
  - The mission banks' segments link the tracks defined at boot the way a bank links children loaded before
    their parents.
  - The copied switches keep their decision trees but list **no children**, because their branches exist only
    in the mission banks.
    - In vanilla, every `music_init` container lists only children `music_init` defines.
    - A first build that kept the copied switches' child lists silenced all music, ship included, because the
      bank no longer loaded.
    - The music root already reaches the mission-only themes the same way, through its tree alone.
- Nothing else changes: every other object and chunk is byte-identical, and objects keep their order. The bank
  grows from 486,764 to 520,220 bytes, with no new media.
- The build refuses unless `music_init` and the four mission banks match the SHA-256 of build 25480438.
- Changing the biome state at runtime instead was rejected because the state is global. Non-music objects in 7
  other banks read it, with values of their own on swamp, deciduous and rift_active.

### Cost

No code runs, so there is no per-frame path and nothing in the LuaJIT code cache. Two one-off costs are
unmeasured in game: the boot load of 33.4 KB more bank data, and the extra Wwise objects in memory. On an
unmapped biome the plugin compares 16 associations instead of 9 when a track starts or the biome changes, on the
audio thread. Only the matching sub-track plays.

### Tests

`tests/test_biome_patch.py` (14 tests) checks the patched bank against the extracted vanilla banks. It parses whole
objects with `scripts/wwise_bank.py`, not the builder's layout readers; that reader matches the research parser on
all 13,273 music objects of the five banks:

- every object parses to its end;
- every other object and chunk is unchanged;
- every container lists only children `music_init` defines (the first build's failure);
- the copied objects are the mission banks' own;
- the build guard refuses other banks;
- every biome track has 16 sub-tracks, and the new clips equal the None clip;
- all 14 game biomes, None and `0xD513EAAE` play on every track;
- mapped biomes are unchanged;
- the switches resolve every biome, unmapped ones to the None branch;
- the patch archive reads back.

The reported case is pinned:

- Automaton start playlist `0x3B401453` on swamp: all 8 biome tracks are silent in vanilla and play the None clip
  patched.
- Drop-music switch `0x1AC07560`: no branch in vanilla, the None branch patched.
- Grassland is unchanged.

Live, 2026-10-16: solo Automaton missions at difficulty 1, loader + audio probe + this build, vanilla music,
capture `fix-2`.

- **Ship:** the music plays.
- **Swamp, planet 205:**
  - Drop-music switch `0x1AC07560` takes the None branch: track `0x27D6B7BB` plays 63-64 s, music input peaks
    -20 to -23 dBFS. Vanilla on the same planet: no branch, no drop track.
  - Then the start playlist ran alone for 72 s (two earlier tries were combat from the landing on). Silent intro,
    then track `0x2204F4A8` from 46 s at -45 to -34 dBFS. Vanilla: no start-playlist voice for ~150 s.
- **Grassland, planet 157 (regression):**
  - Drop music 64 s on the same branch.
  - Start playlist track `0x19E20F5B` from 50 s, as in the vanilla controls (46-52 s).
- The volume fix logged 4 mission starts. The game reached the ship and quit without a crash dump.

## Tests

`tests/test_mod.lua` runs the real Bingus Shared Runtime against a synthetic game object in the test process's
memory, with an exact call budget per scenario (`tests/frame_budget.lua`): first read, ship idle, mission start
and no repeat, the next mission, a stale or not yet created game object, a missing frame time, no garbage or C
types per frame, the install refusals (wrong build, no loader, no engine binding), and a guarded update with a
failing update below it. `tests/test_entry.lua` runs the assembled entry twice outside the game. Both run in
LuaJIT and in the game's `lua51.dll` (`tests/game_lua.py`).
