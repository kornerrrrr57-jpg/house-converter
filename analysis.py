"""
analysis.py  —  PERSON A owns this file.

Right now this is a SIMPLE working version so the website runs today.
Person A: replace/improve the melody detection and key finding.
The only rule: parse_midi() must return the shared `song` dict format.
"""

import pretty_midi


def parse_midi(path):
    """Read a MIDI file and return the shared `song` dict.

    song = {
        "notes": [ {pitch, start, duration, velocity, track}, ... ],  # times in BEATS
        "tempo": 120,
        "key": "C",
        "time_sig": (4, 4),
    }
    """
    pm = pretty_midi.PrettyMIDI(path)

    # --- original tempo (default 120 if the file doesn't say) ---
    tempo = 120.0
    try:
        _, tempi = pm.get_tempo_changes()
        if len(tempi) > 0:
            tempo = float(tempi[0])
    except Exception:
        pass
    beats_per_second = tempo / 60.0

    # --- collect notes, converting seconds -> beats, skipping drum tracks ---
    notes = []
    for track_index, inst in enumerate(pm.instruments):
        if inst.is_drum:
            continue  # ignore existing percussion
        for n in inst.notes:
            notes.append({
                "pitch": n.pitch,
                "start": n.start * beats_per_second,
                "duration": (n.end - n.start) * beats_per_second,
                "velocity": n.velocity,
                "track": track_index,
            })
    notes.sort(key=lambda x: x["start"])

    # --- time signature (default 4/4) ---
    time_sig = (4, 4)
    if pm.time_signature_changes:
        ts = pm.time_signature_changes[0]
        time_sig = (ts.numerator, ts.denominator)

    # --- key guess (simple placeholder — Person A can use music21 to improve) ---
    key = "C"

    return {
        "notes": notes,
        "tempo": round(tempo),
        "key": key,
        "time_sig": time_sig,
    }
