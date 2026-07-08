"""
transform.py  —  PERSON B owns this file.

to_house(song) -> song  is the only contract the rest of the team depends on.

Special track numbers used by the renderer:
    track = 99  -> drums (played on MIDI channel 9)
    track = 98  -> bassline
    anything else -> melody / original notes

Day 2 improvements in this version:
  - Bassline now follows a chord "root" (the pitch that's sounding the
    longest during each beat), instead of just whatever is lowest at
    the instant the beat starts.
  - Quantization is now a *pull* toward the grid rather than a hard
    snap, so some of the original expressive timing survives.
  - Velocities are rebalanced so drums don't bury the melody and quiet
    melody notes don't disappear.
  - Bass pitch is clamped to a sane register and durations/overlaps are
    kept in check.
"""

TARGET_BPM = 124

# How hard we pull notes toward the quantize grid: 1.0 = hard snap,
# 0.0 = no quantization at all. 0.85 keeps the house feel tight while
# preserving a little of the original human timing.
QUANTIZE_STRENGTH = 0.85

# Bass register bounds (MIDI pitch). Roughly E1–B2.
BASS_LOW = 28
BASS_HIGH = 47

MIN_MELODY_VELOCITY = 60   # don't let melody notes go inaudibly quiet
MIN_DURATION = 0.1         # guard against zero/negative durations


def to_house(song):
    # copy the melody notes so we don't modify Person A's data
    notes = [dict(n) for n in song["notes"]]

    # keep an unquantized copy for bass/chord lookups -- we want the
    # bassline to follow what was actually played, not the quantized grid
    original_notes = [dict(n) for n in song["notes"]]

    # 1) QUANTIZE (soft): pull each start toward the nearest quarter-beat
    #    instead of snapping it exactly, so some expressive timing survives.
    for n in notes:
        grid_start = round(n["start"] * 4) / 4
        n["start"] = n["start"] + (grid_start - n["start"]) * QUANTIZE_STRENGTH
        n["duration"] = max(n["duration"], MIN_DURATION)

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
        for beat in (0.5, 1.5, 2.5, 3.5):               # offbeat hats
            notes.append(_drum(42, base + beat, 70, dur=0.25))

    # 3) BASSLINE: one note per beat, following the chord root
    bass_notes = _build_bassline(original_notes, bars)
    notes.extend(bass_notes)

    # 4) BALANCE VOLUMES: keep melody audible, keep drums from
    #    overpowering everything, keep bass supportive but not competing
    _balance_velocities(notes)

    return {
        "notes": notes,
        "tempo": TARGET_BPM,
        "key": song["key"],
        "time_sig": song["time_sig"],
    }


def _drum(pitch, start, velocity, dur=0.5):
    return {"pitch": pitch, "start": start, "duration": dur,
            "velocity": velocity, "track": 99}


def _build_bassline(melody, bars):
    """
    One bass note per beat. For each beat, find the chord "root" --
    the pitch that's sounding for the largest share of that beat -- and
    drop it into the bass register. If nothing is sounding (a rest),
    hold the previous root instead of jumping to an unrelated note.
    """
    bass_notes = []
    last_root = None

    for bar in range(bars):
        for beat in (0, 1, 2, 3):
            beat_start = bar * 4 + beat
            beat_end = beat_start + 1

            root = _find_chord_root(melody, beat_start, beat_end)
            if root is None:
                root = last_root
            if root is None:
                continue  # nothing has played yet -- skip, don't guess

            last_root = root
            bass_pitch = _to_bass_register(root)

            bass_notes.append({
                "pitch": bass_pitch,
                "start": beat_start,
                "duration": 0.85,   # leaves a small gap so beats don't overlap
                "velocity": 100,    # rebalanced later in _balance_velocities
                "track": 98,
            })

    return bass_notes


def _find_chord_root(melody, beat_start, beat_end):
    """
    Look at every melody note overlapping [beat_start, beat_end) and
    weight each pitch by how much of the beat it covers. The pitch with
    the most coverage wins (ties broken by picking the lower pitch,
    since chord roots tend to sit underneath).
    """
    weights = {}
    for n in melody:
        n_start = n["start"]
        n_end = n["start"] + n["duration"]
        overlap = min(n_end, beat_end) - max(n_start, beat_start)
        if overlap > 0:
            weights[n["pitch"]] = weights.get(n["pitch"], 0) + overlap

    if not weights:
        return None

    max_weight = max(weights.values())
    candidates = [p for p, w in weights.items() if w == max_weight]
    return min(candidates)


def _to_bass_register(pitch):
    """Drop/raise a pitch by octaves until it sits in [BASS_LOW, BASS_HIGH]."""
    while pitch > BASS_HIGH:
        pitch -= 12
    while pitch < BASS_LOW:
        pitch += 12
    return pitch


def _balance_velocities(notes):
    """
    Rebalance loudness across melody / bass / drums so nothing gets
    buried and nothing gets lost:
      - melody notes below a floor get bumped up
      - drums get rescaled relative to the melody's average volume
      - bass sits just under the melody so it supports without competing
    """
    melody_notes = [n for n in notes if n["track"] not in (98, 99)]
    avg_melody_vel = (
        sum(n["velocity"] for n in melody_notes) / len(melody_notes)
        if melody_notes else 90
    )

    for n in melody_notes:
        if n["velocity"] < MIN_MELODY_VELOCITY:
            n["velocity"] = MIN_MELODY_VELOCITY

    # Rescale drums around the melody's average, but keep the relative
    # accents (kick louder than hats) by scaling rather than overwriting.
    drum_target = _clamp(int(avg_melody_vel * 1.4), 95, 127)
    for n in notes:
        if n["track"] == 99:
            n["velocity"] = _clamp(int(n["velocity"] * (drum_target / 110)), 60, 120)

    bass_target = _clamp(int(avg_melody_vel * 0.9), 55, 105)
    for n in notes:
        if n["track"] == 98:
            n["velocity"] = bass_target


def _clamp(value, low, high):
    return max(low, min(high, value))
