# Artwork

Files: [banner](banner.png) (1300×372, the Nexus mod-page header size) · [square cover](thumbnail.png) (1254×1254, shown by Arsenal and HD2MM).

Drawn in code with Claude Opus 5.5 (Pillow and NumPy); no image generator was used. `source/` re-renders both PNGs pixel for pixel:

```
cd source
python art.py
```

- Same system as the Bingus Shared Loader, Mod Bindings Menu and Vanilla Plus Megapack art (`artlib.py` and `style.py` are byte-identical copies): Franklin Gothic Heavy for the title, Bahnschrift SemiBold (width 87) for everything else, ground `#121110`, cream `#f0e8d6`, yellow `#fdd00c`.
- The hero is a mission's music as a volume strip from the drop through landing to the fight, with no silent stretch, its loudest bars just under a dashed yellow ceiling they never cross. The banner names both fixes on one line above the strip ("same music volume when you join", "music on every planet"); the cover says them in its side text, in the same order. The bars come from a fixed seed, not from a recording.
- On Nexus the lower left of the header sits under the page's title and stats, so everything that must read is above y≈200.
- The PNGs carry no metadata chunks.
