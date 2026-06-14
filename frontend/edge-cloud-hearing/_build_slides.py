from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parent
NB = ROOT / "edge_cloud_audio_processing.ipynb"
OUT = ROOT / "edge-cloud-audio-processing-slides.html"

nb = nbformat.read(NB, as_version=4)


def img_from_cell(idx):
    cell = nb.cells[idx]
    for o in cell.get("outputs", []):
        png = o.get("data", {}).get("image/png")
        if png:
            return "data:image/png;base64," + png.replace("\n", "")
    return None


IMG_CM = img_from_cell(18)

CSS = """
  @page { size: 1280px 720px; margin: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  :root{
    --bg:#0f1226; --bg2:#171a35; --ink:#eef1ff; --muted:#a8b0d8;
    --accent:#6ee7d7; --accent2:#7c8cff; --card:#1d2142; --line:#2c3160;
    --good:#4ade80; --warn:#fbbf24;
  }
  html,body{ font-family:"Segoe UI",Roboto,Helvetica,Arial,sans-serif; color:var(--ink); }
  .slide{
    position:relative; width:1280px; height:720px; overflow:hidden;
    background:linear-gradient(135deg,var(--bg) 0%,var(--bg2) 100%);
    padding:64px 72px; page-break-after:always; display:flex; flex-direction:column;
  }
  .slide:last-child{ page-break-after:auto; }
  .kicker{ color:var(--accent); font-weight:700; letter-spacing:.16em; text-transform:uppercase; font-size:15px; }
  h1{ font-size:54px; line-height:1.08; font-weight:800; letter-spacing:-.5px; }
  h2{ font-size:38px; font-weight:800; letter-spacing:-.3px; margin-bottom:6px; }
  .sub{ color:var(--muted); font-size:20px; margin-top:14px; }
  p,li{ font-size:21px; line-height:1.5; color:#dfe3ff; }
  .muted{ color:var(--muted); }
  .accent{ color:var(--accent); }
  .accent2{ color:var(--accent2); }
  .footer{ position:absolute; left:72px; right:72px; bottom:28px; display:flex; justify-content:space-between;
           font-size:13px; color:#7a83b8; border-top:1px solid var(--line); padding-top:10px; }
  .grid{ display:grid; gap:18px; margin-top:26px; }
  .g2{ grid-template-columns:1fr 1fr; } .g3{ grid-template-columns:repeat(3,1fr); } .g4{ grid-template-columns:repeat(4,1fr); }
  .card{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 22px; }
  .card h3{ font-size:22px; margin-bottom:8px; }
  .emoji{ font-size:30px; }
  table{ width:100%; border-collapse:collapse; margin-top:22px; font-size:20px; }
  th,td{ text-align:left; padding:14px 16px; border-bottom:1px solid var(--line); }
  th{ color:var(--accent); font-size:15px; letter-spacing:.08em; text-transform:uppercase; }
  tr td:first-child{ font-weight:700; }
  .pipe{ display:flex; align-items:center; gap:14px; margin-top:40px; flex-wrap:wrap; }
  .box{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px; text-align:center; flex:1; }
  .box .t{ font-weight:800; font-size:20px; } .box .d{ color:var(--muted); font-size:15px; margin-top:6px; }
  .arrow{ color:var(--accent); font-size:34px; font-weight:800; }
  .pill{ display:inline-block; background:rgba(110,231,215,.12); color:var(--accent);
         border:1px solid rgba(110,231,215,.4); border-radius:999px; padding:6px 16px; font-size:16px; font-weight:700; }
  .center{ justify-content:center; align-items:center; text-align:center; }
  ul{ margin-top:18px; padding-left:26px; } li{ margin:10px 0; }
  code{ background:#0c0f22; border:1px solid var(--line); border-radius:8px; padding:2px 8px; font-size:18px; color:var(--accent); }
  .codeblock{ background:#0a0d1e; border:1px solid var(--line); border-radius:14px; padding:20px 24px;
              font-family:"Cascadia Code",Consolas,monospace; font-size:18px; color:#cdd3ff; margin-top:18px; white-space:pre; line-height:1.6; }
  .hl{ color:var(--good); font-weight:800; }
  .imgwrap{ background:#fff; border-radius:14px; padding:14px; margin-top:10px; display:flex; justify-content:center; }
  .imgwrap img{ max-width:100%; max-height:250px; }
  .tier-ha{ border-color:rgba(251,191,36,.5); }
  .tier-ph{ border-color:rgba(124,140,255,.6); }
  .tier-cl{ border-color:rgba(110,231,215,.6); }
"""

SLIDES = """
<!-- 1. TITLE -->
<section class="slide center">
  <div class="kicker">Project 3 &middot; Distributed AI for Hearing Devices</div>
  <h1 style="margin-top:18px; max-width:1000px;">Edge-Cloud Audio<br><span class="accent">Processing Framework</span></h1>
  <p class="sub" style="max-width:820px;">A software prototype: hearing aid &rarr; smartphone &rarr; cloud &mdash;
     lightweight edge features, deep on-device inference, cloud model updates.</p>
  <div style="margin-top:34px;"><span class="pill">Feature extract &rarr; WavLM &rarr; classify &rarr; cloud update</span></div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>1</span></div>
</section>

<!-- 2. WHY -->
<section class="slide">
  <div class="kicker">Motivation</div>
  <h2>Why split across three devices?</h2>
  <p class="sub">Hearing aids have strict power and compute limits. Phones have more capacity. The cloud can improve models over time.</p>
  <div class="grid g3" style="margin-top:28px;">
    <div class="card tier-ha"><div class="emoji">&#129467;</div><h3 class="accent" style="color:var(--warn)">Hearing aid</h3><p class="muted">Tiny battery, DSP only &mdash; extract compact audio features, not full neural nets.</p></div>
    <div class="card tier-ph"><div class="emoji">&#128241;</div><h3 class="accent2">Smartphone</h3><p class="muted">Runs the heavy encoder (WavLM) and a small classifier head near the user.</p></div>
    <div class="card tier-cl"><div class="emoji">&#9729;</div><h3 class="accent">Cloud</h3><p class="muted">Aggregates feedback from many users and pushes an updated classifier back.</p></div>
  </div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>2</span></div>
</section>

<!-- 3. ARCHITECTURE -->
<section class="slide">
  <div class="kicker">Architecture</div>
  <h2>Three-tier pipeline</h2>
  <div class="pipe">
    <div class="box tier-ha"><div class="t" style="color:var(--warn)">Hearing Aid</div><div class="d">log-mel summary<br>80 floats</div></div>
    <div class="arrow">&rarr;</div>
    <div class="box tier-ph"><div class="t accent2">Smartphone</div><div class="d">WavLM embedding<br>+ classifier</div></div>
    <div class="arrow">&rarr;</div>
    <div class="box"><div class="t">Scene label</div><div class="d">Restaurant, Street,<br>Office, Car</div></div>
  </div>
  <div class="pipe" style="margin-top:24px;">
    <div class="box tier-ph"><div class="t accent2">Phones upload</div><div class="d">embeddings + labels</div></div>
    <div class="arrow">&uarr;</div>
    <div class="box tier-cl"><div class="t accent">Cloud</div><div class="d">retrain classifier</div></div>
    <div class="arrow">&darr;</div>
    <div class="box tier-ph"><div class="t accent2">Model update</div><div class="d">new weights to phones</div></div>
  </div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>3</span></div>
</section>

<!-- 4. HEARING AID -->
<section class="slide">
  <div class="kicker">Tier 1 &mdash; Hearing Aid</div>
  <h2>Lightweight feature extraction</h2>
  <p class="sub">No neural network on the device. We compute a log-mel spectrogram and send a tiny summary over Bluetooth.</p>
  <div class="grid g2" style="margin-top:24px;">
    <div class="card">
      <h3 class="accent">What it computes</h3>
      <ul>
        <li>40 mel bands &times; mean energy</li>
        <li>40 mel bands &times; standard deviation</li>
        <li>Total: <span class="hl">80 floats</span> per clip</li>
      </ul>
    </div>
    <div class="card">
      <h3 class="accent">Why it matters</h3>
      <ul>
        <li>Raw 10 s audio &asymp; 160 000 samples</li>
        <li>Edge packet &asymp; <span class="hl">2000&times; smaller</span></li>
        <li>Good for telemetry &amp; bandwidth checks</li>
      </ul>
    </div>
  </div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>4</span></div>
</section>

<!-- 5. SMARTPHONE -->
<section class="slide">
  <div class="kicker">Tier 2 &mdash; Smartphone</div>
  <h2>Deep model inference with WavLM</h2>
  <table>
    <tr><th>What</th><th>Details</th></tr>
    <tr><td>Encoder</td><td><code>microsoft/wavlm-base-plus</code> (frozen, from Hugging Face)</td></tr>
    <tr><td>Input</td><td>16&nbsp;kHz mono waveform (up to 10 s)</td></tr>
    <tr><td>Embedding</td><td>Mean-pool frame outputs &rarr; 768-dim vector</td></tr>
    <tr><td>Head</td><td>Logistic regression (trainable on phone, updatable from cloud)</td></tr>
  </table>
  <p style="margin-top:28px;" class="muted">The expensive encoder runs once per clip; only the tiny classifier head changes when the cloud pushes an update.</p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>5</span></div>
</section>

<!-- 6. CLOUD -->
<section class="slide">
  <div class="kicker">Tier 3 &mdash; Cloud</div>
  <h2>Aggregate feedback and push updates</h2>
  <ol style="margin-top:24px; padding-left:28px; font-size:21px; color:#dfe3ff; line-height:1.7;">
    <li>Each phone only experiences <b>some</b> scenes, so alone it has blind spots.</li>
    <li>Phones upload compact <b>(embedding, label)</b> pairs &mdash; never raw audio.</li>
    <li>Cloud merges the partial views (demo: two phones) and retrains the shared head.</li>
    <li>The stronger classifier is pushed back to every phone (version bump).</li>
  </ol>
  <p style="margin-top:28px;"><span class="hl">Prototype only:</span> production would add encryption, federated learning, and signed OTA updates.</p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>6</span></div>
</section>

<!-- 7. TASK -->
<section class="slide">
  <div class="kicker">Demo Task</div>
  <h2>Acoustic scene classification</h2>
  <p class="sub">Predict the environment around the wearer so the hearing aid can switch noise-reduction profiles.</p>
  <div class="grid g4">
    <div class="card"><div class="emoji">&#127869;</div><h3>Restaurant</h3><p class="muted">cafe chatter</p></div>
    <div class="card"><div class="emoji">&#128739;</div><h3>Street</h3><p class="muted">traffic, crowds</p></div>
    <div class="card"><div class="emoji">&#128187;</div><h3>Office</h3><p class="muted">keyboards, talk</p></div>
    <div class="card"><div class="emoji">&#128663;</div><h3>Car</h3><p class="muted">engine, road</p></div>
  </div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>7</span></div>
</section>

<!-- 8. DATA -->
<section class="slide">
  <div class="kicker">Hugging Face Hub</div>
  <h2>Model and dataset</h2>
  <div class="grid g2" style="margin-top:24px;">
    <div class="card">
      <h3 class="accent2">Model</h3>
      <p><code>microsoft/wavlm-base-plus</code></p>
      <p class="muted" style="margin-top:10px;">Loaded with <code>transformers</code>. Frozen encoder for embeddings.</p>
    </div>
    <div class="card">
      <h3 class="accent">Dataset</h3>
      <p><code>MahiA/TUT2017</code></p>
      <p class="muted" style="margin-top:10px;">TUT Acoustic Scenes 2017 mirror. Demo downloads ~20 clips per scene (~80 total).</p>
    </div>
  </div>
  <p style="margin-top:28px;">Label mapping: Restaurant &larr; <code>cafe/restaurant</code>, Street &larr; <code>city_center</code>, Office &larr; <code>office</code>, Car &larr; <code>car</code></p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>8</span></div>
</section>

<!-- 9. NOTEBOOK STEPS -->
<section class="slide">
  <div class="kicker">The Notebook</div>
  <h2>Ten clear steps</h2>
  <div class="grid g5" style="grid-template-columns:repeat(5,1fr); margin-top:22px;">
    <div class="card"><h3 class="accent2">1</h3><p class="muted">Install deps</p></div>
    <div class="card"><h3 class="accent2">2</h3><p class="muted">Configure</p></div>
    <div class="card"><h3 class="accent2">3</h3><p class="muted">Load HF data</p></div>
    <div class="card"><h3 class="accent2">4</h3><p class="muted">Hearing-aid features</p></div>
    <div class="card"><h3 class="accent2">5</h3><p class="muted">Load WavLM</p></div>
    <div class="card"><h3 class="accent2">6</h3><p class="muted">Extract embeddings</p></div>
    <div class="card"><h3 class="accent2">7</h3><p class="muted">Phone classifier</p></div>
    <div class="card"><h3 class="accent2">8</h3><p class="muted">Cloud retrain</p></div>
    <div class="card"><h3 class="accent2">9</h3><p class="muted">Apply update</p></div>
    <div class="card"><h3 class="accent2">10</h3><p class="muted">End-to-end demo</p></div>
  </div>
  <p style="margin-top:24px;">Notebook: <code>edge_cloud_audio_processing.ipynb</code></p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>9</span></div>
</section>

<!-- 10. RESULTS -->
<section class="slide">
  <div class="kicker">Results</div>
  <h2>Cloud aggregation fixes each phone's blind spots</h2>
  <div class="grid g3" style="margin-top:16px;">
    <div class="card"><h3 style="color:var(--warn)">One phone alone</h3><p class="hl" style="font-size:40px; margin-top:6px; color:var(--warn)">50%</p><p class="muted">only saw 2 of 4 scenes</p></div>
    <div class="card"><h3 class="accent">After cloud update</h3><p class="hl" style="font-size:40px; margin-top:6px;">100%</p><p class="muted">all 4 scenes covered</p></div>
    <div class="card"><h3 class="accent">Edge bandwidth</h3><p class="hl" style="font-size:40px; margin-top:6px;">2000&times;</p><p class="muted">packet vs raw audio</p></div>
  </div>
  __IMG_BLOCK__
  <p style="margin-top:10px;" class="muted">Left: phone-A alone fails on scenes it never recorded. Right: the cloud-updated head gets every scene.</p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>10</span></div>
</section>

<!-- 11. INFERENCE -->
<section class="slide">
  <div class="kicker">End-to-End</div>
  <h2>One clip through the full pipeline</h2>
  <div class="codeblock">wav  &rarr; hearing_aid_features(wav)   # 80-float edge packet
wav  &rarr; smartphone_embed(wav)       # 768-dim WavLM vector
emb  &rarr; phone_clf.predict(emb)      # scene + confidence

True scene : Restaurant
Predicted  : Restaurant
Edge packet: 80 floats</div>
  <p style="margin-top:24px;" class="muted">If the prediction is wrong, the phone would upload the embedding; the cloud includes it in the next update cycle.</p>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>11</span></div>
</section>

<!-- 12. TAKEAWAYS -->
<section class="slide">
  <div class="kicker">Takeaways</div>
  <h2>What this prototype shows</h2>
  <ul>
    <li><span class="accent">Edge-cloud split</span> lets hearing aids stay low-power while phones run deep models.</li>
    <li>Devices see <span class="accent">partial views</span>; the cloud combines them into a model better than any phone alone (50% &rarr; 100%).</li>
    <li>The <span class="accent">cloud only updates the small head</span> &mdash; cheap to retrain and easy to deploy.</li>
    <li>Both <span class="accent">model and dataset</span> come from the Hugging Face Hub.</li>
  </ul>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>12</span></div>
</section>

<!-- 13. EXTENSIONS -->
<section class="slide">
  <div class="kicker">Extensions</div>
  <h2>How to go further</h2>
  <div class="grid g2" style="margin-top:20px;">
    <div class="card"><h3 class="accent">Speech enhancement</h3><p class="muted">Replace scene classification with a denoising model (e.g. MetricGAN+) on the phone tier.</p></div>
    <div class="card"><h3 class="accent">Federated learning</h3><p class="muted">Train on-device without uploading raw audio &mdash; only gradients or embeddings.</p></div>
    <div class="card"><h3 class="accent">Real DSP</h3><p class="muted">Port the hearing-aid front-end to an embedded DSP chip instead of librosa.</p></div>
    <div class="card"><h3 class="accent">More scenes</h3><p class="muted">Use the full TUT2017 dataset (15 classes) for a richer environment model.</p></div>
  </div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>13</span></div>
</section>

<!-- 14. THANK YOU -->
<section class="slide center">
  <div class="kicker">Thank you</div>
  <h1 style="margin-top:14px;">Questions?</h1>
  <p class="sub" style="max-width:800px;">
    Notebook: <code>edge_cloud_audio_processing.ipynb</code><br>
    Slides: <code>edge-cloud-audio-processing.pdf</code><br>
    Model: <code>microsoft/wavlm-base-plus</code> &middot; Data: <code>MahiA/TUT2017</code>
  </p>
  <div style="margin-top:30px;"><span class="pill">Run the notebook top to bottom</span></div>
  <div class="footer"><span>Edge-Cloud Audio Processing</span><span>14</span></div>
</section>
"""

img_block = ""
if IMG_CM:
    img_block = (
        '<div class="imgwrap" style="margin-top:18px;">'
        f'<img src="{IMG_CM}" alt="Confusion matrices before and after cloud update">'
        "</div>"
    )

SLIDES = SLIDES.replace("__IMG_BLOCK__", img_block)

html = (
    '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    "<title>Edge-Cloud Audio Processing Framework</title>\n<style>"
    + CSS
    + "</style>\n</head>\n<body>\n"
    + SLIDES
    + "\n</body>\n</html>\n"
)

with open(OUT, "w") as f:
    f.write(html)
print("wrote", OUT, "(", len(html), "bytes )")
