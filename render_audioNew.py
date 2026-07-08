"""
render_audio.py  —  PERSON B owns this file (works with Person C).

Turns a `song` dict into a MIDI file, then uses FluidSynth to make a WAV
you can play in the browser. Also renders the raw uploaded MIDI ("original").

Quick sanity check without Flask involved at all:
    python3 render_audio.py
This renders one held middle-C note to smoke_test.wav so you can confirm
FluidSynth + your soundfont are working before wiring anything else up.
"""
import os
import glob
import subprocess
import pretty_midi

# FluidSynth's default synth gain can clip when kick + bass + melody +
# hats all hit around the same instant. 0.6 is a safe starting point;
# raise it if the render sounds too quiet once you've heard it for real.
SYNTH_GAIN = "0.6"

# Guard against FluidSynth hanging on a broken MIDI/soundfont combo --
# without this, a stuck render call could hang a Flask request forever.
RENDER_TIMEOUT_SECONDS = 60


def find_soundfont():
    """
    Locate the .sf2 soundfont. Set the SOUNDFONT env var to override.
    Otherwise search, in order:
      1. This script's own folder (works regardless of Flask's cwd)
      2. The current working directory
      3. ~/house-converter/
    """
    override = os.environ.get("SOUNDFONT")
    if override:
        if os.path.exists(override):
            return override
        raise FileNotFoundError(f"SOUNDFONT env var set to '{override}' but that file doesn't exist.")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [script_dir, os.getcwd(), os.path.expanduser("~/house-converter")]

    for d in search_dirs:
        matches = glob.glob(os.path.join(d, "*.sf2"))
        if matches:
            return matches[0]

    raise FileNotFoundError(
        "No .sf2 soundfont found. Put your soundfont (e.g. GeneralUser-GS.sf2) "
        f"in one of: {search_dirs}, or set the SOUNDFONT environment variable."
    )


def _clamp7bit(value, default=64):
    """Clamp a value into valid MIDI 0-127 range. Defensive: a bug upstream
    in transform.py (or a weird uploaded MIDI) should never crash rendering."""
    try:
        value = int(round(value))
    except (TypeError, ValueError):
        return default
    return max(0, min(127, value))


def _song_to_pm(song, bpm):
    """Build a pretty_midi object from the shared song dict."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    melody = pretty_midi.Instrument(program=81)              # 81 = synth lead
    bass = pretty_midi.Instrument(program=38)                # 38 = synth bass
    drums = pretty_midi.Instrument(program=0, is_drum=True)  # channel 9 drums

    sec_per_beat = 60.0 / bpm
    for n in song["notes"]:
        start = n["start"] * sec_per_beat
        end = (n["start"] + n["duration"]) * sec_per_beat
        if end <= start:
            end = start + 0.05  # guard against zero/negative-length notes

        note = pretty_midi.Note(
            velocity=_clamp7bit(n["velocity"], default=90),
            pitch=_clamp7bit(n["pitch"], default=60),
            start=start,
            end=end,
        )
        if n["track"] == 99:
            drums.notes.append(note)
        elif n["track"] == 98:
            bass.notes.append(note)
        else:
            melody.notes.append(note)

    pm.instruments.extend([melody, bass, drums])
    return pm


def _fluidsynth_to_wav(midi_path, wav_path):
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    out_dir = os.path.dirname(os.path.abspath(wav_path))
    os.makedirs(out_dir, exist_ok=True)

    soundfont = find_soundfont()
    cmd = [
        "fluidsynth", "-ni",
        "-g", SYNTH_GAIN,
        soundfont,
        midi_path,
        "-F", wav_path,
        "-r", "44100",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=RENDER_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        _remove_if_exists(wav_path)
        raise RuntimeError(
            f"FluidSynth timed out after {RENDER_TIMEOUT_SECONDS}s rendering {midi_path}. "
            "Check for an unusually long/dense MIDI file, or a hung fluidsynth process."
        )

    if result.returncode != 0:
        _remove_if_exists(wav_path)
        raise RuntimeError(
            "FluidSynth failed to render audio.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        _remove_if_exists(wav_path)
        raise RuntimeError(
            f"FluidSynth reported success but no audio was written to {wav_path}"
        )

    return wav_path


def _remove_if_exists(path):
    """Clean up a partial/broken output file so Flask never serves a
    zero-byte or corrupt WAV to the browser."""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass  # best-effort cleanup; don't let this mask the real error


def render(song, wav_path, bpm=124):
    """Render a transformed song dict to a WAV file."""
    if not song.get("notes"):
        raise ValueError("Cannot render a song with no notes.")

    midi_path = wav_path.rsplit(".", 1)[0] + ".mid"
    _song_to_pm(song, bpm).write(midi_path)
    return _fluidsynth_to_wav(midi_path, wav_path)


def render_original(midi_path, wav_path):
    """Render the raw uploaded MIDI straight to WAV (keeps its own sound/tempo)."""
    return _fluidsynth_to_wav(midi_path, wav_path)


if __name__ == "__main__":
    # Standalone smoke test: confirms FluidSynth + your soundfont work
    # at all, with zero dependency on Flask, Person A, or Person C.
    test_song = {
        "notes": [
            {"pitch": 60, "start": 0, "duration": 2, "velocity": 100, "track": 0},
        ],
        "tempo": 124,
        "key": "C",
        "time_sig": (4, 4),
    }
    try:
        out = render(test_song, "smoke_test.wav")
        print(f"Success! Wrote {out} -- play it to confirm you hear a note.")
    except Exception as e:
        print(f"Smoke test failed: {e}")
