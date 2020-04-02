## fe2: Frontier: Elite 2 savegames encoder - decoder.

This is a simple command line to decrypt and reencrypt samegames from fe2 the Atari and Amiga version.
It also works with [Final Frontier, the linux 64bits port of the game](https://github.com/lee-b/final-frontier) or [glfrontier for DOS/Windows](https://github.com/pcercuei/glfrontier)

Tested on Python 3.8 but should be broadly compatible across 3.x.
As a dependency it only needs [click](https://click.palletsprojects.com/en/7.x/).
An easy way to install it is to use pip.
```bash
$ pip install click
```

To use it:

```bash
$ ./fe2.py --help
Usage: fe2.py [OPTIONS] SRCFILE DSTFILE

Options:
  -d, --decrypt  Decrypt the savegame to clear binary.
  -e, --encrypt  Encrypt back a savegame.
  --help         Show this message and exit
```

The savegames are saved by default in the `/savs` subdirectory.
