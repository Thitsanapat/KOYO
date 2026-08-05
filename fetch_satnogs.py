#!/usr/bin/env python3
"""
Download everything SatNOGS has for KOYO (and optionally SCION-X).

Usage:
    pip install requests
    python3 fetch_satnogs.py            # KOYO only, frames + metadata
    python3 fetch_satnogs.py --audio    # also download .ogg audio (big!)
    python3 fetch_satnogs.py --sat scionx --audio

Output tree:
    data/koyo/frames/<obsid>_<n>.bin     raw demodulated frames (binary)
    data/koyo/frames_hex/<obsid>.txt     same frames as hex text, one per line
    data/koyo/audio/<obsid>.ogg          audio recordings
    data/koyo/waterfall/<obsid>.png      waterfall images
    data/koyo/observations.json          full API metadata
    data/koyo/index.csv                  obsid, start, station, status, n_frames
"""

import argparse
import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
import random
import sys
import time
from urllib.parse import urlencode

import requests

NETWORK = "https://network.satnogs.org/api"

SATS = {
    # norad_cat_id is a *temporary* ID for freshly-launched CubeSats and SatNOGS
    # has been observed to reassign it: satellite__norad_cat_id=98273 returned
    # observations for a different satellite (PEARL-1B, norad 98330) on
    # 2026-07-30. sat_id is SatNOGS' permanent identifier and does not move, so
    # every fetched observation is checked against it (and against tle0) before
    # anything is saved - see filter_observations_for_satellite().
    "koyo":   {"norad": 98273, "name": "KOYO", "sat_id": "YZNT-7399-1272-5956-2962"},
    "scionx": {"norad": 98266, "name": "SCION-X", "sat_id": None},
}

HEADERS = {"User-Agent": "NCU-KOYO-internship/1.0"}


def retry_after_seconds(response):
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=timezone.utc)
    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())


def polite_get(url, label, timeout=60, max_retries=8):
    """GET with SatNOGS-friendly retry behavior for 429 and transient errors."""
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeout)
            if response.status_code not in (429, 500, 502, 503, 504):
                response.raise_for_status()
                return response

            retry_after = retry_after_seconds(response)
            wait = retry_after if retry_after is not None else min(90.0, 2.0 ** attempt)
            wait += random.uniform(0.0, 0.5)
            last_error = requests.HTTPError(
                f"{response.status_code} for {label}", response=response
            )
        except requests.RequestException as exc:
            wait = min(90.0, 2.0 ** attempt) + random.uniform(0.0, 0.5)
            last_error = exc

        if attempt >= max_retries:
            break
        print(f"    ! {label}: {last_error}; waiting {wait:.1f}s before retry {attempt + 1}/{max_retries}")
        time.sleep(wait)

    raise last_error


def get_observations(sat, status="good", max_pages=60, api_delay=1.0, max_retries=8):
    """Page through the observations API for one satellite.

    Prefer filtering by sat_id: it is SatNOGS' permanent per-satellite
    identifier. satellite__norad_cat_id was found on 2026-07-30 to silently
    match nothing useful (norad_cat_id is temporary/reassignable for
    newly-launched CubeSats) - it returned unrelated recent observations
    across many satellites instead of raising an error. Bare sat_id=<id> does
    filter correctly; satellite__sat_id=<id> does not.
    """
    if sat["sat_id"]:
        params = {"sat_id": sat["sat_id"], "format": "json"}
    else:
        params = {"satellite__norad_cat_id": sat["norad"], "format": "json"}
    if status and status != "all":
        params["status"] = status
    obs, url = [], f"{NETWORK}/observations/?{urlencode(params)}"
    for page in range(max_pages):
        r = polite_get(url, f"observations page {page + 1}", timeout=60, max_retries=max_retries)
        batch = r.json()
        if not batch:
            break
        obs.extend(batch)
        print(f"  page {page + 1}: +{len(batch)} observations (total {len(obs)})")
        # SatNOGS paginates via the Link header
        nxt = r.links.get("next", {}).get("url")
        if not nxt:
            break
        url = nxt
        time.sleep(api_delay)
    return obs


def filter_observations_for_satellite(obs, sat):
    """Defensively drop observations that don't actually belong to `sat`.

    sat_id is SatNOGS' permanent per-satellite identifier and is the only
    field trusted as a hard requirement here. norad_cat_id and tle0 (the
    display name) are both known to drift for newly-launched CubeSats - e.g.
    KOYO's tle0 read "KOYO" on one date and "0 OBJECT AZ" (a generic
    placeholder) on another, same sat_id both times - so they are logged for
    visibility but never used to reject an observation.

    If sat_id isn't known for this satellite (see SATS), falls back to
    norad_cat_id as a best-effort (weaker) check and says so loudly.
    """
    kept, dropped = [], []
    for o in obs:
        if sat["sat_id"]:
            ok = o.get("sat_id") == sat["sat_id"]
        else:
            ok = o.get("norad_cat_id") == sat["norad"]
        (kept if ok else dropped).append(o)
    if not sat["sat_id"]:
        print(f"  ! WARNING: no known sat_id for {sat['name']} - filtering by norad_cat_id only, "
              f"which is known to be unreliable for newly-launched CubeSats. Double check results.")
    if dropped:
        print(f"  ! dropped {len(dropped)} observation(s) that did not match {sat['name']} "
              f"(norad {sat['norad']}, sat_id {sat['sat_id']}):")
        for o in dropped[:10]:
            print(f"      obs {o.get('id')}: tle0={o.get('tle0')!r} norad_cat_id={o.get('norad_cat_id')} sat_id={o.get('sat_id')}")
        if len(dropped) > 10:
            print(f"      ... and {len(dropped) - 10} more")
    return kept


def get_observation(obs_id, max_retries=8):
    r = polite_get(
        f"{NETWORK}/observations/{obs_id}/?format=json",
        f"observation {obs_id}",
        timeout=60,
        max_retries=max_retries,
    )
    return r.json()


def download(url, path, label, download_delay=0.5, max_retries=8):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return False
    try:
        r = polite_get(url, label, timeout=120, max_retries=max_retries)
    except Exception as e:
        print(f"    ! {label} failed: {e}")
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(r.content)
    time.sleep(download_delay)
    return True


def load_observations(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sat", default="koyo", choices=SATS.keys())
    ap.add_argument("--obs-id", help="download a single observation by SatNOGS observation id")
    ap.add_argument("--status", default="good", help="SatNOGS observation status to fetch; use 'all' to omit this filter")
    ap.add_argument("--audio", action="store_true", help="download .ogg audio too")
    ap.add_argument("--waterfall", action="store_true", help="download waterfall PNGs too")
    ap.add_argument("--refresh-observations", action="store_true", help="ignore cached observations.json and fetch a fresh API list")
    ap.add_argument("--metadata-only", action="store_true", help="write observations.json/index.csv without downloading frames/audio/waterfalls")
    ap.add_argument("--max-pages", type=int, default=60, help="maximum observation-list pages to fetch when refreshing")
    ap.add_argument("--max-observations", type=int, default=0, help="limit how many observations are processed after listing")
    ap.add_argument("--api-delay", type=float, default=1.0, help="seconds to wait between observation-list pages")
    ap.add_argument("--download-delay", type=float, default=0.5, help="seconds to wait after each downloaded file")
    ap.add_argument("--max-retries", type=int, default=8, help="retries for 429 and transient HTTP errors")
    args = ap.parse_args()

    sat = SATS[args.sat]
    root = os.path.join("data", args.sat)
    os.makedirs(root, exist_ok=True)
    cache_suffix = args.status if args.status != "all" else "all"
    observations_path = os.path.join(root, f"observations_{cache_suffix}.json")

    print(f"=== {sat['name']} (NORAD {sat['norad']}) ===")
    if args.obs_id:
        print(f"Fetching observation {args.obs_id}...")
        obs = [get_observation(args.obs_id, max_retries=args.max_retries)]
        checked = filter_observations_for_satellite(obs, sat)
        if not checked:
            print(f"  ! WARNING: obs {args.obs_id} does not match {sat['name']} - keeping it anyway "
                  f"since it was explicitly requested by --obs-id, but do not trust it as {sat['name']} data.")
    else:
        if os.path.exists(observations_path) and not args.refresh_observations:
            print(f"Using cached observation list: {observations_path}")
            obs = load_observations(observations_path)
        else:
            print("Fetching observation list...")
            obs = get_observations(
                sat,
                status=args.status,
                max_pages=args.max_pages,
                api_delay=args.api_delay,
                max_retries=args.max_retries,
            )
        obs = filter_observations_for_satellite(obs, sat)
    if args.max_observations > 0:
        obs = obs[:args.max_observations]
    print(f"Total observations: {len(obs)}\n")

    with open(observations_path, "w", encoding="utf-8") as f:
        json.dump(obs, f, indent=2)

    rows = []
    n_frames = n_audio = n_wf = 0

    for i, o in enumerate(obs, 1):
        oid = o["id"]
        demod = o.get("demoddata") or []
        prefix = f"[{i}/{len(obs)}] obs {oid}"

        # ---- frames ----
        hex_lines = []
        if not args.metadata_only:
            for j, d in enumerate(demod):
                url = d.get("payload_demod")
                if not url:
                    continue
                path = os.path.join(root, "frames", f"{oid}_{j:03d}.bin")
                download(
                    url,
                    path,
                    f"frame {oid}_{j}",
                    download_delay=args.download_delay,
                    max_retries=args.max_retries,
                )
                if os.path.exists(path):
                    n_frames += 1
                    with open(path, "rb") as f:
                        hex_lines.append(f.read().hex())

        if hex_lines:
            os.makedirs(os.path.join(root, "frames_hex"), exist_ok=True)
            with open(os.path.join(root, "frames_hex", f"{oid}.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(hex_lines) + "\n")

        # ---- audio ----
        if args.audio and o.get("payload") and not args.metadata_only:
            audio_path = os.path.join(root, "audio", f"{oid}.ogg")
            download(
                o["payload"],
                audio_path,
                f"audio {oid}",
                download_delay=args.download_delay,
                max_retries=args.max_retries,
            )
            if os.path.exists(audio_path):
                n_audio += 1

        # ---- waterfall ----
        if args.waterfall and o.get("waterfall") and not args.metadata_only:
            waterfall_path = os.path.join(root, "waterfall", f"{oid}.png")
            download(
                o["waterfall"],
                waterfall_path,
                f"wf {oid}",
                download_delay=args.download_delay,
                max_retries=args.max_retries,
            )
            if os.path.exists(waterfall_path):
                n_wf += 1

        rows.append({
            "obs_id": oid,
            "start": o.get("start"),
            "end": o.get("end"),
            "station": o.get("station_name"),
            "status": o.get("status"),
            "transmitter_mode": o.get("transmitter_mode"),
            "n_frames": len(hex_lines) if not args.metadata_only else len(demod),
            "has_audio": bool(o.get("payload")),
        })

        if i % 20 == 0 or i == len(obs):
            print(f"{prefix}  frames so far: {n_frames}")

    with open(os.path.join(root, "index.csv"), "w", newline="", encoding="utf-8") as f:
        if rows:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    good = sum(1 for r in rows if r["status"] == "good")
    with_frames = sum(1 for r in rows if r["n_frames"] > 0)

    print(f"""
=== DONE ===
observations   : {len(rows)}  ({good} good, {with_frames} with frames)
frames saved   : {n_frames}
audio saved    : {n_audio}
waterfalls     : {n_wf}
output         : {os.path.abspath(root)}

Next: all frames as hex are in {root}/frames_hex/  -- feed those into the decoder.
""")


if __name__ == "__main__":
    sys.exit(main())
