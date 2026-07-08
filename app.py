"""
app.py  —  PERSON C owns this file.

The website. Run it with:   python app.py
Then open the address it prints (http://127.0.0.1:5000) in your browser.

Flow:  upload .mid  ->  parse_midi()  ->  to_house()  ->  render()  ->  play both
"""

import os
import uuid
from flask import Flask, request, render_template_string, url_for

from analysis import parse_midi        # Person A
from transformNew import to_house         # Person B
from render_audioNew import render, render_original  # Person B

app = Flask(__name__)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)   # Flask serves WAVs from here


PAGE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIDI &rarr; House Converter</title>
<style>
  :root{
    --bg:#15121f; --panel:#1e1930; --line:#332b4d;
    --ink:#ece8f7; --muted:#9a90bd; --amber:#ffb347; --violet:#a97bff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:radial-gradient(circle at 50% -10%,#241d3a,#15121f 60%);
       color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
  .wrap{max-width:680px;margin:0 auto;padding:48px 20px 80px}
  .eyebrow{letter-spacing:.35em;text-transform:uppercase;font-size:.7rem;color:var(--muted)}
  h1{font-size:2.4rem;margin:.2em 0 .1em;line-height:1.05}
  h1 span{color:var(--amber)}
  .sub{color:var(--muted);margin-bottom:32px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:16px;
        padding:24px;margin-bottom:24px}
  input[type=file]{color:var(--muted);width:100%;margin-bottom:16px}
  button{background:var(--amber);color:#241d3a;border:0;border-radius:10px;
         padding:12px 22px;font-size:1rem;font-weight:700;cursor:pointer}
  button:hover{filter:brightness(1.08)}
  .players{display:grid;gap:18px}
  .player h3{margin:0 0 8px;font-size:.95rem}
  .player h3 small{color:var(--muted);font-weight:400}
  audio{width:100%}
  .tag{display:inline-block;font-size:.7rem;padding:2px 8px;border-radius:20px;margin-left:6px}
  .tag.orig{background:#2a2340;color:var(--muted)}
  .tag.house{background:var(--violet);color:#15121f}
  table{width:100%;border-collapse:collapse;font-size:.92rem}
  td{padding:8px 0;border-bottom:1px solid var(--line);color:var(--muted)}
  td.v{color:var(--ink);text-align:right;font-weight:600}
  .warn{background:#3a2a12;border:1px solid var(--amber);color:#ffd9a0;
        padding:12px 14px;border-radius:10px;margin-bottom:20px;font-size:.9rem}
  .err{background:#3a1220;border:1px solid #ff6b6b;color:#ffb3b3;
       padding:12px 14px;border-radius:10px;font-size:.9rem}
  .converting{display:none;margin-top:14px;color:var(--amber);font-size:.92rem;
              align-items:center;gap:10px}
  .converting.show{display:flex}
  .spinner{width:16px;height:16px;border:3px solid var(--line);
           border-top-color:var(--amber);border-radius:50%;
           display:inline-block;animation:spin .8s linear infinite}
  @keyframes spin{to{transform:rotate(360deg)}}
  .cplayer{display:flex;align-items:center;gap:14px;margin-top:6px}
  .playbtn{width:52px;height:52px;border-radius:50%;background:var(--violet);
           color:#15121f;font-size:1.1rem;border:0;cursor:pointer;flex:0 0 auto;
           display:flex;align-items:center;justify-content:center;padding:0;line-height:1}
  .playbtn:hover{filter:brightness(1.1)}
  .playbtn.playing{background:var(--amber)}
  .eq{display:flex;align-items:flex-end;gap:3px;height:26px;width:34px;flex:0 0 auto}
  .eq span{width:5px;height:6px;background:var(--muted);border-radius:2px}
  .eq.on span{background:var(--amber);animation:bounce .9s ease-in-out infinite}
  .eq.on span:nth-child(2){animation-delay:.15s}
  .eq.on span:nth-child(3){animation-delay:.30s}
  .eq.on span:nth-child(4){animation-delay:.45s}
  .eq.on span:nth-child(5){animation-delay:.60s}
  @keyframes bounce{0%,100%{height:6px}50%{height:24px}}
  .pbar{flex:1 1 auto;height:8px;background:var(--line);border-radius:6px;
        cursor:pointer;position:relative}
  .pfill{height:100%;width:0;background:var(--violet);border-radius:6px}
  .ptime{flex:0 0 auto;color:var(--muted);font-size:.8rem;min-width:40px;text-align:right}
  .foot{color:var(--muted);font-size:.8rem;margin-top:30px;text-align:center}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Computing in the Arts</div>
  <h1>MIDI &rarr; <span>House</span></h1>
  <p class="sub">Upload a MIDI file. We keep the melody, lock it to 124&nbsp;BPM,
     and add a four-on-the-floor house beat.</p>

  <div class="card">
    <form method="post" enctype="multipart/form-data" onsubmit="showConverting()">
      <input type="file" name="midi" accept=".mid,.midi" required>
      <button type="submit" id="convertBtn">Convert to House</button>
    </form>
    <div id="converting" class="converting">
      <span class="spinner"></span> Converting&hellip; this takes a few seconds.
    </div>
  </div>

  {% if error %}<div class="err">{{ error }}</div>{% endif %}

  {% if result %}
    {% if result.warning %}<div class="warn">&#9888; {{ result.warning }}</div>{% endif %}

    <div class="card players">
      <div class="player">
        <h3>Original <span class="tag orig">as uploaded</span></h3>
        <audio controls src="{{ result.original_url }}"></audio>
      </div>
      <div class="player">
        <h3>House Version <span class="tag house">124 BPM</span></h3>
        <audio id="houseAudio" src="{{ result.converted_url }}" preload="metadata"></audio>
        <div class="cplayer">
          <button type="button" id="playBtn" class="playbtn" aria-label="Play">&#9654;</button>
          <div class="eq" id="eq"><span></span><span></span><span></span><span></span><span></span></div>
          <div class="pbar" id="pbar"><div class="pfill" id="pfill"></div></div>
          <div class="ptime" id="ptime">0:00</div>
        </div>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-top:0">What changed</h3>
      <table>
        <tr><td>Detected key</td><td class="v">{{ result.key }}</td></tr>
        <tr><td>Original tempo</td><td class="v">{{ result.orig_tempo }} BPM</td></tr>
        <tr><td>New tempo</td><td class="v">{{ result.new_tempo }} BPM</td></tr>
        <tr><td>Time signature</td><td class="v">{{ result.time_sig }}</td></tr>
        <tr><td>Melody notes kept</td><td class="v">{{ result.num_notes }}</td></tr>
        <tr><td>Drums added</td><td class="v">Kick + clap + hats</td></tr>
        <tr><td>Bassline added</td><td class="v">Yes</td></tr>
        <tr><td>Quantization</td><td class="v">Quarter-beat grid</td></tr>
      </table>
    </div>
  {% endif %}

  <div class="foot">Rule-based converter &middot; symbolic MIDI in, house out</div>
</div>
<script>
  function showConverting(){
    document.getElementById('converting').classList.add('show');
    var b = document.getElementById('convertBtn');
    b.disabled = true;
    b.textContent = 'Working\u2026';
  }

  (function(){
    var a = document.getElementById('houseAudio');
    if(!a) return;  // no converted track on the page yet
    var btn = document.getElementById('playBtn');
    var eq = document.getElementById('eq');
    var pbar = document.getElementById('pbar');
    var pfill = document.getElementById('pfill');
    var ptime = document.getElementById('ptime');

    function fmt(t){
      if(isNaN(t) || t === Infinity) return '0:00';
      var m = Math.floor(t/60), s = Math.floor(t%60);
      return m + ':' + (s < 10 ? '0' : '') + s;
    }

    btn.addEventListener('click', function(){
      if(a.paused){ a.play(); } else { a.pause(); }
    });
    a.addEventListener('play', function(){
      btn.textContent = '\u23F8';           // pause icon
      btn.classList.add('playing');
      eq.classList.add('on');
    });
    a.addEventListener('pause', function(){
      btn.textContent = '\u25B6';           // play icon
      btn.classList.remove('playing');
      eq.classList.remove('on');
    });
    a.addEventListener('ended', function(){
      btn.textContent = '\u25B6';
      btn.classList.remove('playing');
      eq.classList.remove('on');
      pfill.style.width = '0%';
    });
    a.addEventListener('timeupdate', function(){
      if(a.duration){
        pfill.style.width = (a.currentTime / a.duration * 100) + '%';
        ptime.textContent = fmt(a.currentTime);
      }
    });
    a.addEventListener('loadedmetadata', function(){
      ptime.textContent = fmt(a.duration);
    });
    pbar.addEventListener('click', function(e){
      var rect = pbar.getBoundingClientRect();
      var ratio = (e.clientX - rect.left) / rect.width;
      if(a.duration){ a.currentTime = ratio * a.duration; }
    });
  })();
</script>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    error = None

    if request.method == "POST":
        f = request.files.get("midi")
        if not f or f.filename == "":
            error = "Please choose a .mid file first."
        else:
            try:
                token = uuid.uuid4().hex[:8]
                in_path = os.path.join(UPLOAD_DIR, token + ".mid")
                f.save(in_path)

                # render the original as-is
                orig_wav = os.path.join("static", token + "_original.wav")
                render_original(in_path, orig_wav)

                # analyze -> transform -> render
                song = parse_midi(in_path)
                house = to_house(song)
                conv_wav = os.path.join("static", token + "_converted.wav")
                render(house, conv_wav)

                not_44 = song["time_sig"] != (4, 4)
                result = {
                    "original_url": url_for("static", filename=os.path.basename(orig_wav)),
                    "converted_url": url_for("static", filename=os.path.basename(conv_wav)),
                    "key": song["key"],
                    "orig_tempo": song["tempo"],
                    "new_tempo": 124,
                    "time_sig": "%d/%d" % song["time_sig"],
                    "num_notes": len(song["notes"]),
                    "warning": ("This converter works best with 4/4 music. "
                                "Other time signatures may sound unusual.") if not_44 else None,
                }
            except Exception as e:
                error = "Something went wrong: %s" % e

    return render_template_string(PAGE, result=result, error=error)


if __name__ == "__main__":
    app.run(debug=True, port=5001)