## fe2: Frontier: Elite 2 savegame decoder, parser and encoder.

This is a simple command line to decrypt and reencrypt samegames from fe2 the Atari and Amiga version.
It also works with [Final Frontier, the linux 64bits port of the game](https://github.com/lee-b/final-frontier) or [glfrontier for DOS/Windows](https://github.com/pcercuei/glfrontier).

Tested on Python 3.8 but should be broadly compatible across 3.x.
As a dependency it only needs [click](https://click.palletsprojects.com/en/7.x/).
An easy way to install it is to use pip.

```bash
$ pip install click
```

To use it:

```bash
$ ./fe2.py --help

Usage: fe2.py [OPTIONS] SRCFILE [DSTFILE]

Options:
  -d, --decrypt  Decrypt the savegame to clear binary.
  -e, --encrypt  Encrypt back a savegame.
  -i, --inspect  Inspect a decrypted savegame.
  -t, --testdec  Test the decryption with a ground truth from amiSGE.
  -T, --testenc  Test the encryption with a ground truth from amiSGE.
  --help         Show this message and exit.
```

The savegames are saved by default in the `/savs` subdirectory.

Example of an inspection after decryption:

```
./fe2.py -i samples/MAGNUM.raw 
Player:
  Date: 3211-08-04
  Money: ¢1451413.8
  Federal Rank: Sergeant-Major with 334 points
  Imperial Title: Outsider with 0 points
  Elite rating: Dangerous with 1470 kills
  Ship ID: 6a
  Selected target ID: 6a
  Cargo Space: 26t [0x83d0]
  Fuel: 10t

Game Objects:
id 67:
  type: Kind Of Ship In Hyperspace
  designation: ZP-736
  speed: 0.4 m.s⁻¹

id 69:
  type: Kind Of Ship In Hyperspace
  designation: TW-960
  near: Star/Planet Lucifer
  speed: 0.2 m.s⁻¹
  forward acceleration: 4905 m.s⁻²
  reverse acceleration: 63356 m.s⁻²
  equipment:
    - Scanner
    - Normal ECM
    - Atmospheric Shielding
  drive type: Hyperdrive Class 3
  guns:
    - front:161
    - back:0
    - top:0

 vvvv This is your own ship vvvv ------------------------
id 6a:
  type: Kind Of Ship In Hyperspace
  designation: UW-677
  near: Star/Planet Lucifer
  speed: 0.6 m.s⁻¹
  forward acceleration: 11990 m.s⁻²
  reverse acceleration: 61721 m.s⁻²
  equipment:
    - Scanner
    - Autopilot
    - Radar Mapper
    - Naval ECM
    - Hyperspace Cloud Analyser
    - Energy Bomb
    - Energy Booster Unit
    - Atmospheric Shielding
  drive type: Military Class 3
  guns:
    - front:170
    - back:0

id 6b:
  type: Unknown 75
  designation: XI-353
  near: Unknown 17 Sirius, Sirius B
  forward acceleration: 7630 m.s⁻²
  reverse acceleration: 62266 m.s⁻²
  equipment:
    - Scanner
    - Atmospheric Shielding
  drive type: Hyperdrive Class 2
  guns:
    - front:136

id 6c:
  type: Active ship in current system
  designation: UG-384
  near: Unknown 17 Sirius, Sirius B
  speed: 1.5 m.s⁻¹
  forward acceleration: 407 m.s⁻²
  reverse acceleration: 5952 m.s⁻²
  equipment:
    - Cargo Bay Life Support
  guns:
    - front:0
    [...]
 ```
