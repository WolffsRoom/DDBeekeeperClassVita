<p align="center">
  <img src="assets/darkest_dungeon_logo.png" width="420" alt="Darkest Dungeon">
</p>

# The Beekeeper Class — Darkest Dungeon PS Vita

Unofficial PS Vita port of **The Beekeeper Class** by [Nick Noir](https://nick-noir.itch.io/darkest-dungeon-beekeeper) for **Darkest Dungeon 1.17**.

This project provides a Windows patcher that converts the original PC class mod to Vita-compatible assets and merges it into the user's own `content_patch_13.psarc` for use with **rePatch**.

> No Darkest Dungeon game files or original Beekeeper assets are distributed by this repository. You must provide legally obtained copies of both.

<p align="center">
  <img src="assets/ClassModBeekeeper.png" width="640" alt="The Beekeeper Class">
</p>

## Status

| Component | Status |
| --- | --- |
| Beekeeper class / Stage Coach | ✅ Working |
| Combat data and animations | ✅ Working |
| Vita GXT textures | ✅ Working |
| Vita localization | ✅ Working |
| Multilanguage support | ✅ Implemented |
| Custom Beekeeper audio | 🧪 Experimental — real Vita validation in progress |
| PSARC rebuild / rePatch output | ✅ Working |

Tested primarily with the US Vita release:

```text
Darkest Dungeon 1.17
Title ID: PCSE00919
```

## How it works

Darkest Dungeon Vita does not load the PC mod directly. The patcher adapts the class to the formats and layout expected by the Vita version:

```text
Original Vita content_patch_13.psarc
                +
Original Beekeeper PC mod
                ↓
Extract Vita archive
                ↓
Merge Beekeeper into the content root
                ↓
PNG → Vita GXT textures
.loc2/XML → Vita legacy localization
Manifest regeneration
                ↓
Rebuild + verify PSARC
                ↓
rePatch/PCSE00919/
```

Texture conversion follows rules derived from official Vita content, especially the Shieldbreaker DLC. Images are resized to Vita-appropriate dimensions and converted to swizzled GXT using BC1 or BC3 depending on the asset type and alpha requirements.

The patcher also converts the Beekeeper localization to the older format used by the Vita release and can generate the supported language files from the original translation data.

## Patcher

The Windows build is standalone and does **not** require Python.

1. Download the latest `DDBeekeeperClassVita.exe` release.
2. Select your original Vita `content_patch_13.psarc`.
3. Select the original Beekeeper mod ZIP or folder.
4. Choose an output directory.
5. Click **Build rePatch**.
6. Copy the generated `rePatch` folder to the root of `ux0:`.

Expected output:

```text
rePatch/
└── PCSE00919/
    ├── content_patch_13.psarc
    └── audio/
        └── ...
```

The patcher also contains an optional **Force Beekeeper in Stage Coach** setting intended only for debugging. It is disabled by default.

## Development history

The first attempts treated Beekeeper as an additional DLC under `dlc/beekeeper_class`. The Vita accepted the modified PSARC and Stage Coach roster, but the custom class itself was not discovered, leaving the Stage Coach empty.

Comparing the PC mod layout with official Vita content showed that an arbitrary DLC directory was the wrong approach. Beekeeper was then integrated directly into the archive root (`heroes`, `effects`, `raid`, `shared`, `upgrades`, etc.). This allowed the Vita build to discover and instantiate the custom hero correctly.

The next major problem was asset compatibility. Official Vita textures use GXT data even when their filenames still end in `.png`. By comparing Beekeeper assets against the official Shieldbreaker Vita files, the project reproduced the Vita resize, BC1/BC3 and metadata rules and converted the full class texture set.

Localization required another Vita-specific conversion: the PC mod uses modern `.loc2` files, while the Vita build expects the older localization format. A legacy conversion pipeline was added and the class text now loads correctly on hardware.

Custom audio is the current experimental area. Vita FMOD banks use a different sample encoding than the original PC Beekeeper bank. The current test pipeline rebuilds the bank using the Vita-compatible **FADPCM** format and integrates its load order and GUID overrides. Real-hardware validation is still in progress.

## Building from source

Requirements:

- Windows 10/11;
- Python 3.13+;
- dependencies from `requirements.txt`;
- authorized Vita SDK copies of `psp2gxt.exe` and `psp2psarc.exe` placed in `tools/`.

Run the source GUI or build the standalone executable with:

```text
Build_EXE.bat
```

Sony SDK binaries are intentionally excluded from the repository.

## Credits

- **The Beekeeper Class:** [Nick Noir](https://nick-noir.itch.io/darkest-dungeon-beekeeper)
- **PS Vita port / patcher:** [WolffsRoom](https://github.com/WolffsRoom)
- **Darkest Dungeon:** Red Hook Studios

This is an unofficial fan project and is not affiliated with or endorsed by Red Hook Studios, Sony Interactive Entertainment, or Nick Noir.
