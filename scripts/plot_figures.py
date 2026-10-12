#!/usr/bin/env python3
"""Plot retained cadence theorem values, without rerunning the validation suite."""
from pathlib import Path
import argparse
import csv
import os
import shutil
import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt, font_manager
from matplotlib.ticker import NullLocator

ROOT = Path(__file__).resolve().parents[1]


def configure_fonts():
    directory = Path(os.environ.get("FIGURE_FONT_DIR", os.environ.get("WINDIR", "")))
    if not os.environ.get("FIGURE_FONT_DIR"):
        directory /= "Fonts"
    candidates = [directory / "times.ttf", directory / "timesi.ttf"]
    if all(p.is_file() for p in candidates):
        for p in candidates:
            font_manager.fontManager.addfont(str(p))
        family = font_manager.FontProperties(fname=str(candidates[0])).get_name()
    else:
        # STIX is bundled with Matplotlib and is a Times-compatible serif fallback.
        family = "STIXGeneral"
    plt.rcParams.update({"font.family": family, "font.size": 9.963,
                         "mathtext.fontset": "custom", "mathtext.rm": family,
                         "mathtext.it": family + ":style=italic",
                         "mathtext.bf": family, "mathtext.fallback": None,
                         "pdf.fonttype": 42, "ps.fonttype": 42,
                         "pdf.use14corefonts": False, "text.usetex": False,
                         "axes.linewidth": .5, "xtick.major.width": .5,
                         "ytick.major.width": .5, "xtick.major.size": 3.5,
                         "ytick.major.size": 3.5})
    print("Font:", family)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "figures")
    parser.add_argument("--paper-dir", type=Path, default=ROOT.parent / "paper" / "figures")
    args = parser.parse_args()
    with (ROOT / "results/pinned/cadence.csv").open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    slots = [int(r["slots"]) for r in rows]
    moving = [int(r["moving_pins"]) for r in rows]
    fixed = [int(r["fixed_pins"]) for r in rows]
    assert moving == [min(2*t, 2*((t+1)//2)+3, 8) for t in slots]
    assert fixed == [min(2*t, 5) for t in slots]
    configure_fonts()
    fig = plt.figure(figsize=(393.0143 / 72, 152.6701 / 72))
    ax = fig.add_axes([26.0 / 393.0143, 27.43 / 152.6701,
                       366.3 / 393.0143, 124.54 / 152.6701])
    ax.plot(slots, moving, "-o", color="black", linewidth=.8, markersize=3.6,
            label="Changing offline identities")
    ax.plot(slots, fixed, "--s", color="black", linewidth=.8, markersize=3.6,
            label="One fixed offline set")
    ax.set(xlim=(.7, 12.3), ylim=(0, 9), xlabel=r"Number of slots $T$",
           ylabel="Temporal capacity")
    ax.set_xticks([1, 2, 4, 6, 8, 10, 12])
    ax.set_yticks([0, 2, 4, 5, 6, 7, 8])
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.tick_params(direction="in", top=True, right=True, pad=4)
    ax.legend(loc="lower right", frameon=False, fontsize=9.963,
              handlelength=1.5, handletextpad=.4, borderpad=.2, labelspacing=.2)
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "cadence.pdf"
    fig.savefig(path, metadata={"Creator": None, "Producer": None,
                                "CreationDate": None, "ModDate": None})
    plt.close(fig)
    if args.paper_dir.is_dir():
        shutil.copyfile(path, args.paper_dir / path.name)
    print("Rendered cadence: 12 unchanged theorem rows")


if __name__ == "__main__":
    main()
