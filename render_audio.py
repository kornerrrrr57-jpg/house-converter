"""
render_audio.py  —  PERSON B owns this file (works with Person C).

Turns a `song` dict into a MIDI file, then uses FluidSynth to make a WAV
you can play in the browser. Also renders the raw uploaded MIDI ("original").
"""

import os
import glob
import subprocess
import pretty_midi


def find_soundfont():
    """Locate the .sf2 soundfont. Set the SOUNDFONT env var to override,
    otherwise it grabs the first .sf2 it finds in this folder."""
    override = os.environ.get("SOUNDFONT")
    if override and os.path.exists(override):
        return override
    matches = glob.glob("*.sf2") + glob.glob(os.path.expanduser("~/house-converter/*.sf2"))
    if matches:
        return matches[0]
    raise FileNotFoundError(
        "No .sf2 soundfont found. Put your soundfont (e.g. GeneralUser-GS.sf2) "
        "in this folder, or set the SOUNDFONT environment variable."
    )


def _song_to_pm(song, bpm):
    """Build a pretty_midi object from the shared song dict."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    melody = pretty_midi.Instrument(program=81)              # 81 = synth lead
    bass = pretty_midi.Instrument(program=38)                # 38 = synth bass
    drums = pretty_midi.Instrument(program=0, is_drum=True)  # channel 9 drums

    sec_per_beat = 60.0 / bpm
    for n in song["notes"]:
        note = pretty_midi.Note(
            velocity=int(n["velocity"]),
            pitch=int(n["pitch"]),
            start=n["start"] * sec_per_beat,
            end=(n["start"] + n["duration"]) * sec_per_beat,
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
    subprocess.run(
        ["fluidsynth", "-ni", find_soundfont(), midi_path, "-F", wav_path, "-r", "44100"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return wav_path


def render(song, wav_path, bpm=124):
    """Render a transformed song dict to a WAV file."""
    midi_path = wav_path.rsplit(".", 1)[0] + ".mid"
    _song_to_pm(song, bpm).write(midi_path)
    return _fluidsynth_to_wav(midi_path, wav_path)


def render_original(midi_path, wav_path):
    """Render the raw uploaded MIDI straight to WAV (keeps its own sound/tempo)."""
    return _fluidsynth_to_wav(midi_path, wav_path)
