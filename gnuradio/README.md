# KOYO GNU Radio flowgraph

`koyo_audio_rx.grc` is the editable GNU Radio Companion version of the local
audio receive chain. It uses the GNU Radio and gr-satellites installation in
`%USERPROFILE%\radioconda`.

Compile it from the repository root:

```powershell
& "$env:USERPROFILE\radioconda\Scripts\grcc.exe" -o .\gnuradio\generated .\gnuradio\koyo_audio_rx.grc
```

Run the generated flowgraph against the default validation WAV:

```powershell
& "$env:USERPROFILE\radioconda\python.exe" .\gnuradio\generated\koyo_audio_rx.py
```

The default input is SatNOGS observation `14526577`. Its generated KISS output
contains one valid 263-byte frame that matches the observation control exactly.
Edit the `audio_file` and `kiss_file` variables in GNU Radio Companion for a
different prepared WAV.
