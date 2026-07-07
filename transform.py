"""
transform.py  —  PERSON B owns this file.

Right now this is a SIMPLE working version so the website runs today.
Person B: improve the bassline (follow chord roots), balance volumes, etc.
The only rule: to_house() takes a `song` dict and returns a `song` dict.

Special track numbers used by the renderer:
    track = 99  -> drums (played on MIDI channel 9)
    track = 98  -> bassline
    anything else -> melody / original notes
"""

TARGET_BPM = 124


def to_house(song):
    # copy the melody notes so we don't modify Person A's data
    notes = [dict(n) for n in song["notes"]]

    # 1) QUANTIZE: snap every start to the nearest quarter-beat (tight house grid)
    for n in notes:
        n["start"] = round(n["start"] * 4) / 4

    # how many 4-beat bars long is the song?
    if notes:
        end_beat = max(n["start"] + n["duration"] for n in notes)
    else:
        end_beat = 4
    bars = int(end_beat // 4) + 1

    # 2) DRUMS: four-on-the-floor kick, clap on 2 & 4, offbeat hats
    for bar in range(bars):
        base = bar * 4
        for beat in (0, 1, 2, 3):                      # kick every beat
            notes.append(_drum(36, base + beat, 110))
        for beat in (1, 3):                            # clap on 2 and 4
            notes.append(_drum(39, base + beat, 95))
        for beat in (0.5, 1.5, 2.5, 3.5):              # offbeat hats
            notes.append(_drum(42, base + beat, 70, dur=0.25))

    # 3) BASSLINE: one note per beat, from the lowest note sounding then
    melody = [n for n in song["notes"]]  # use un-quantized originals for pitch lookup
    for bar in range(bars):
        for beat in (0, 1, 2, 3):
            b = bar * 4 + beat
            pitch = _bass_pitch(melody, b)
            notes.append({
                "pitch": pitch, "start": b, "duration": 0.9,
                "velocity": 100, "track": 98,
            })

    return {
        "notes": notes,
        "tempo": TARGET_BPM,
        "key": song["key"],
        "time_sig": song["time_sig"],
    }


def _drum(pitch, start, velocity, dur=0.5):
    return {"pitch": pitch, "start": start, "duration": dur,
            "velocity": velocity, "track": 99}


def _bass_pitch(notes, beat):
    """Pick a bass note for this beat: lowest note sounding, dropped to bass range."""
    sounding = [n["pitch"] for n in notes
                if n["start"] <= beat < n["start"] + max(n["duration"], 0.1)]
    if sounding:
        pitch = min(sounding)
    elif notes:
        pitch = min(notes, key=lambda n: abs(n["start"] - beat))["pitch"]
    else:
        pitch = 48
    while pitch > 48:      # bring it down into a bassy octave
        pitch -= 12
    return pitch
