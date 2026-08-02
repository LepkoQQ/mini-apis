from pathlib import Path
import requests
import os

ICON_BASE = "https://vreme.arso.gov.si/app/common/images/svg/weather/"
ICON_EXT = ".svg"

nn_icons = [
    "clear",  # jasno
    # "mostClear",  # pretežno jasno
    # "slightCloudy",  # rahlo oblačno
    "partCloudy",  # delno oblačno
    # "modCloudy",  # zmerno oblačno
    "prevCloudy",  # pretežno oblačno
    "overcast",  # oblačno
    "FG",  # megla
]

rr_decodeText = [
    "light",
    "mod",
    "heavy",
]

wwsyn_icons = [
    "FG",  # megla
    "DZ",  # rosenje
    "FZDZ",  # rosenje, ki zmrzuje
    "RA",  # dež
    "FZRA",  # dež, ki zmrzuje
    "RASN",  # dež s snegom
    "SN",  # sneg
    "SHRA",  # ploha dežja
    "SHRASN",  # ploha dežja s snegom
    "SHSN",  # snežna ploha
    "SHGR",  # ploha sodre
    "TS",  # nevihta
    "TSRA",  # nevihta z dežjem
    "TSRASN",  # nevihta z dežjem in snegom
    "TSSN",  # nevihta s sneženjem
    "TSGR",  # nevihta s točo
]

tod = [
    "day",
    "night",
]

# Example: prevCloudy_lightRA_day.svg
ICONS = []
for icon in nn_icons:
    for t in tod:
        icon_name = f"{icon}_{t}"
        ICONS.append(icon_name)
    if icon == "clear":
        continue
    for ww in wwsyn_icons:
        for rr in rr_decodeText:
            for t in tod:
                icon_name = f"{icon}_{rr}{ww}_{t}"
                ICONS.append(icon_name)


OUT_DIR = (
    Path(__file__).parent.parent
    / "mini-apis"
    / "api"
    / "weather"
    / "static"
    / "icons"
    / "weather"
)


def main():
    print(f"Output directory: {OUT_DIR}")
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Downloading {len(ICONS)} icons...")
    for icon in ICONS:
        url = f"{ICON_BASE}{icon}{ICON_EXT}"
        response = requests.get(url, allow_redirects=False)
        if response.status_code == 200:
            if not response.content.startswith(b"<?xml"):
                print(f"  > Invalid: {url}")
                continue
            with open(f"{OUT_DIR}/{icon}.svg", "wb") as f:
                f.write(response.content)
            print(f"Downloaded: {url}")
        else:
            print(f"Failed to download {url}: {response.status_code}")


if __name__ == "__main__":
    main()
