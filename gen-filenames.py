# /// script
# requires-python = ">=3.9"
# dependencies = ["ollama"]
# ///

# Copyright 2026 Daniel ZM.
# SPDX-License-Identifier: AGPL-3.0-only
# License text: https://www.gnu.org/licenses/agpl-3.0.html

import argparse, importlib, logging, os, pathlib, re, subprocess, sys

try:
  ollama = importlib.import_module("ollama")
except ModuleNotFoundError as e:
  raise SystemExit("Run with `uv run --script gen-filenames.py` to install dependencies") from e

def main(
    src: pathlib.Path,
    *,
    do: bool = False,
    keep_exif_dates: bool = False,
) -> None:
    if not src.is_dir():
        raise SystemExit(f"Source folder does not exist or is not a directory: {src}")

    prompt = (
        "Beschreibe den Bildinhalt in 3 bis 5 deutschen Stichworten, "
        "nur Wörter mit Leerzeichen, keine Satzzeichen."
    )
    uml = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

    image_paths = [
        *src.rglob("*.jpg"),
        *src.rglob("*.jpeg"),
    ]
    for p in sorted(image_paths):
        r = ollama.chat(
            model="qwen3-vl:8b",
            messages=[{"role": "user", "content": prompt, "images": [str(p)]}],
        )
        content = r["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            logging.warning("No filename returned for %s; keeping its current name", p.name)
            continue

        words = content.lower().translate(uml)
        slug = re.sub(r"[^a-z0-9]+", "-", words).strip("-")[:60].strip("-")
        if not slug:
            logging.warning("No usable filename returned for %s; keeping its current name", p.name)
            continue

        new = p.with_name(f"{slug}{p.suffix}")
        print(f"{p.name} -> {new.name}")
        if new == p:
            if do and not keep_exif_dates:
                subprocess.run(
                    ["exiftool", "-P", "-overwrite_original", "-time:all=", str(p.resolve())],
                    check=True,
                )
            continue
        if new.exists():
            logging.warning("Target %s already exists; keeping %s unchanged", new.name, p.name)
            continue

        if do and not keep_exif_dates:
            subprocess.run(
                ["exiftool", "-P", "-overwrite_original", "-time:all=", str(p.resolve())],
                check=True,
            )
        if do:
            try:
                os.link(p, new)
            except FileExistsError:
                logging.warning("Target %s already exists; keeping %s unchanged", new.name, p.name)
                continue
            p.unlink()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=pathlib.Path, required=True, help="Folder containing images")
    parser.add_argument("--do", action="store_true", help="Apply renames and remove date metadata")
    parser.add_argument(
        "--keep-exif-dates",
        action="store_true",
        help="Keep embedded date/time metadata when applying changes",
    )
    args = parser.parse_args()
    main(args.src, do=args.do, keep_exif_dates=args.keep_exif_dates)
