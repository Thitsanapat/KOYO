# GitHub Publication Guide

Publish only the generated `github-public/KOYO-Beacon-Decoder` directory. Do
not initialize or push the private workspace root: it contains local-only
material, and an existing Git history can preserve files even after deletion.

## Pre-Push Check

1. Confirm there are no OGG, WAV, KISS, raw data, unapproved office source
   documents, or local Grafana/InfluxDB runtime files. The allowlisted
   `KOYO_Real_Results.xlsx` evidence workbook is expected.
2. Search text files for private hostnames, credentials, source-document names,
   byte offsets, and unapproved telemetry mappings.
3. Open the final PDF and presentation once from the public directory.
4. Confirm the repository visibility and access policy with the project owner.
5. Review `THIRD_PARTY_NOTICES.md`. The bundled GPL text applies only where a
   file identifies itself as GPL-covered; it does not grant rights over
   mission documents or the rest of the project.

## Existing Remote Warning

The repository previously published at `Thitsanapat/KOYO` contains confidential
document references, byte-offset mappings, personal contact information, raw
frame archives, and unrelated SCION-X research in its Git history. Deleting
those files in a later commit is not sufficient.

Before making the sanitized release public:

1. Make the existing repository private or temporarily disable access.
2. Preserve the private working repository locally as internal evidence.
3. Replace the remote branch with the clean, unrelated history created from
   this directory only.
4. Remove every old branch, tag, release, pull-request ref, Actions artifact,
   and fork that can retain the former objects.
5. Contact GitHub Support to purge cached views and unreachable sensitive
   objects after the rewrite.

History replacement is destructive for the remote and requires explicit owner
approval. Do not run a force push as part of an ordinary update.

## Initialize and Push

Run these commands from `github-public/KOYO-Beacon-Decoder` only:

```powershell
git init
git add .
git status
git commit -m "Publish KOYO beacon decoder evidence"
git branch -M main
git remote add origin <NEW_OR_EMPTY_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Review `git status` before committing. The generated public directory is built
from an explicit allowlist, but the final publication decision remains with the
project owner.
