# Canon G2000 maintenance tool for Linux

A small PyQt6 window modelled on Canon's Windows "IJ Printer Assistant Tool",
for the Canon PIXMA G2000 series (G2200 etc.) on Linux. Canon never shipped a
maintenance utility for Linux, so this sends the maintenance commands from
Canon's Linux driver (`cnijfilter2`) through CUPS.

**Status: experimental.** Tested on a single G2000 over USB on CachyOS.
Not affiliated with or endorsed by Canon.

## What works

| Action | Status |
|---|---|
| Nozzle Check | Works |
| Cleaning | Command sent through the driver, untested on hardware |
| Print Head Alignment | Command sent through the driver, untested on hardware |
| View Printer Status / Information | Shows CUPS queue and USB info |
| Everything else in the Windows tool | Greyed out: no command is known for it on Linux |

The Linux driver has no `cnijfilter2` profile for the G2000 itself. This tool
uses the G3000 profile (`canong3000.ppd`) on a separate CUPS queue. That queue
only carries maintenance jobs. For normal printing keep using a regular queue
(for example the Gutenprint G2000 driver).

## Requirements

- `cnijfilter2` (AUR on Arch/CachyOS)
- Python 3 with PyQt6
- A CUPS queue named `G2000-canon` using `canong3000.ppd`

## Setup

```bash
paru -S cnijfilter2 python-pyqt6

# find your printer's Canon backend URI, then create the queue
lpinfo -v | grep cnijbe2
sudo lpadmin -p G2000-canon -E -v "<the cnijbe2:// URI from above>" -m canong3000.ppd

python3 canon-maintenance.py
```

To add it to your app menu, copy `canon-maintenance.desktop.example` to
`~/.local/share/applications/canon-maintenance.desktop` and set `Exec=` to the
full path of the script. Change `QUEUE` at the top of the script if you named
the queue differently.

## How it works

`cnijfilter2` builds printer commands as small XML documents (Canon's "IVEC"
format). The maintenance files in `/usr/share/cmdtocanonij3/` are CUPS command
files that the `cmdtocanonij3` filter turns into that XML. You can inspect the
bytes without a printer by running the filter on a command file and sending
the output to a file.

## Notes and risks

- The library also contains a firmware-update-mode command. This tool never
  sends it, and you shouldn't either.
- Cleaning uses ink. Run a nozzle check afterwards to see if it helped.
- Other Windows-tool functions (deep cleaning, ink flush, roller cleaning,
  power off, quiet mode and so on) may exist as further IVEC commands, but
  they are not documented. Contributions are welcome, particularly captured
  command traces from other models.

## License

MIT, see `LICENSE`.
