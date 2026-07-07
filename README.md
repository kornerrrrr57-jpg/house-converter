# MIDI → House Converter

Upload a MIDI file → keep the melody → 124 BPM → add house drums + bass → hear both versions.

## Setup (each teammate does this once)

```
pip install music21 pretty_midi flask
# install FluidSynth:  mac -> brew install fluidsynth
```

Put a soundfont (`.sf2`, e.g. GeneralUser GS) in this folder.

## Run

```
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Files / who owns what

| File              | Owner     | Job                                             |
|-------------------|-----------|-------------------------------------------------|
| `analysis.py`     | Person A  | `parse_midi(path) -> song`                      |
| `transform.py`    | Person B  | `to_house(song) -> song`                        |
| `render_audio.py` | Person B  | `render(song, wav)` + `render_original(...)`    |
| `app.py`          | Person C  | the Flask website that connects everything      |

## Shared data format — DO NOT change after we split up

```python
note = {
    "pitch": 60,       # MIDI note number, 60 = middle C
    "start": 0.0,      # start time IN BEATS (not seconds)
    "duration": 1.0,   # length IN BEATS
    "velocity": 90,    # loudness 0-127
    "track": 0,        # source track. 99 = drums, 98 = bass (used by renderer)
}
song = {
    "notes": [],           # list of note dicts
    "tempo": 120,          # original BPM
    "key": "C",
    "time_sig": (4, 4),
}
```

## House drum pattern (one 4-beat bar)

- Kick (36): beats 0, 1, 2, 3
- Clap (39): beats 1, 3
- Hat (42): beats 0.5, 1.5, 2.5, 3.5
- Target tempo: 124 BPM
