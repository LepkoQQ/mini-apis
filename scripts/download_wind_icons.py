from pathlib import Path
import requests
import os

ICON_BASE = "https://vreme.arso.gov.si/app/common/images/svg/graf/"
ICON_EXT = ".svg"

ff_icons = [
    "light",
    "mod",
    "heavy",
]
dd_icons = [
    "N",
    "NE",
    "E",
    "SE",
    "S",
    "SW",
    "W",
    "NW",
]

ICONS = [f"{ff}{dd}" for ff in ff_icons for dd in dd_icons]

OUT_DIR = Path(__file__).parent.parent / "mini-apis" / "api" / "weather" / "icons" / "wind"


def main():
    print(f"Output directory: {OUT_DIR}")
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Downloading {len(ICONS)} icons...")
    for icon in ICONS:
        url = f"{ICON_BASE}{icon}{ICON_EXT}"
        print(f"Downloading {url}...")
        response = requests.get(url, allow_redirects=False)
        if response.status_code == 200:
            with open(f"{OUT_DIR}/{icon}.svg", "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download {url}: {response.status_code}")


if __name__ == "__main__":
    main()
