# Decodes a KOYO SatNOGS WAV locally via gr_satellites.
#
# clk_bw defaults to 0.15 here, not gr_satellites' own default of 0.06 - the
# default clock-recovery bandwidth is too narrow to track through the full
# 263-byte KOYO frame (it would sync on the AX.25 header correctly, then lose
# lock partway through, producing truncated/malformed captures). Verified
# 2026-07-30: with clk_bw=0.15 against obs 14526577's audio, this produces a
# 263-byte frame that is an exact byte-for-byte match against SatNOGS' own
# server-side decoded frame for the same observation - see
# data/koyo/observations/14526577/sweep/dev3000_clk0.15.kiss.
#
# Default ObsId here must be an observation with real SatNOGS demoddata to
# compare against (frames_hex/<obsid>.txt) - 14586261 has none and is not a
# valid test case; use 14526577 or 14468821.
param(
    [string]$ObsId = "14526577",
    [string]$Config = "koyo_gr_satellites.yml",
    [string]$Variant = "normal",
    [double]$ClkBw = 0.15
)

$ErrorActionPreference = "Stop"

$Root = Join-Path "data\koyo\observations" $ObsId
$Wav = Join-Path $Root "obs_$ObsId.wav"
$Kiss = Join-Path $Root "$Variant.kiss"
$Conda = Join-Path $env:USERPROFILE "radioconda\Scripts\conda.exe"

if (!(Test-Path $Conda)) {
    throw "radioconda not found at $Conda"
}
if (!(Test-Path $Wav)) {
    throw "WAV not found at $Wav"
}

$Args = @(
    "run", "-n", "base",
    "gr_satellites", $Config,
    "--satcfg",
    "--wavfile", $Wav,
    "--samp_rate", "48000",
    "--clk_bw", $ClkBw,
    "--hexdump",
    "--kiss_out", $Kiss
)

switch ($Variant) {
    "invert" { $Args += @("--input_gain", "-1") }
    "nodc" { $Args += "--disable_dc_block" }
    "invert_nodc" { $Args += @("--input_gain", "-1", "--disable_dc_block") }
}

& $Conda @Args
Write-Host "KISS output: $Kiss"
