# KOYO GitHub Publication Audit

Audit date: 2026-08-31

This is a private handoff report. Do not add it to the public repository.

## Remote Finding

Repository: `https://github.com/Thitsanapat/KOYO.git`

- Visibility: public
- Default branch: `master`
- Remote head before cleanup: `9929224247117e6e145ab4ce753e64f781e11342`
- Reachable history: 14 commits
- Branches: 1
- Tags: 0
- Releases: 0
- Forks reported by GitHub: 0
- Pull requests: 0
- Actions runs: 1, with no artifact; run `30982490796` references an old commit

The existing history is not suitable for publication. It contains confidential
source-document references, derived telemetry byte mappings, personal contact
information, raw frame archives, local service configuration, and unrelated
SCION-X research. A normal deletion commit would leave all of this reachable.

## Clean Release

Clean repository directory:

`github-public/KOYO-Beacon-Decoder`

- Branch: `main`
- Root commit: `281b44759aad613b86e3e92d3ea797a5ff1a04cf`
- Reachable commits: 1
- Files: 21
- Public audit: PASS
- Manifest SHA256: `D37D68CA3DBD66D7572BB76D4704801C49F45AB97991A965E3A5AF415BFF6385`
- ZIP SHA256: `FC25751F6462A2596DC87CAA1302A92BDEB2AE023EAD283DF8F743A4F4FEC87A`
- Commit email: GitHub noreply address
- Byte-identical duplicate files: none

The clean release excludes confidential documents, raw OGG/WAV/KISS and frame
files, the mapping-bearing decoder, private dashboard source, local databases,
credentials, private paths, and Git history from the working repository.

## Required Response

1. Make the existing GitHub repository private immediately while cleanup is in
   progress.
2. Keep the private workspace root and its `.git` directory off public remotes.
3. Prefer publishing the clean repository to a new private repository first,
   reviewing it on GitHub, and only then changing that new repository to public.
4. If the existing URL must be reused, replace `master` with the clean root
   commit only after explicit owner approval. This is a destructive force push.
5. Delete the old Actions run and check issues, discussions, wiki, Pages, caches,
   and collaborators for copied material.
6. Contact GitHub Support after the rewrite and request removal of cached views
   and unreachable sensitive objects. Explain that confidential mission-derived
   mappings and personal information were published in the old history.
7. Rotate any credential that was ever real or reused outside local development.
8. Ask any known clone holder to delete or re-clone the old repository.

## Prepared Push Commands

Run only from `github-public/KOYO-Beacon-Decoder` after authenticating and after
the remote publication decision is approved.

For a new repository, create it as private first:

```powershell
gh auth login
gh repo create Thitsanapat/KOYO-Beacon-Decoder --private --source . --remote publish --push
```

For the existing repository, the owner-approved destructive replacement would
be:

```powershell
git remote set-url --push origin https://github.com/Thitsanapat/KOYO.git
git push --force origin main:master
```

The prepared clean repository currently has a deliberately disabled push URL
to prevent an ordinary push from adding `main` while leaving the unsafe
`master` history online. Do not enable it until the owner approves the history
replacement. Do not run the force push from the private workspace root.

## Legal Boundary

This audit is a technical risk-reduction review, not legal advice. Public data
availability does not override confidentiality, copyright, contractual terms,
privacy obligations, export controls, spectrum rules, or an employer or
university publication policy. Obtain written approval from the project owner
for any telemetry interpretation or mission material whose publication rights
are uncertain.
