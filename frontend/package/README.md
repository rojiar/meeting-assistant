# Audio ML Notebooks — Run Package

Four demo notebooks with presentation PDFs. Everything here runs from Hugging Face on first use (models + datasets download automatically).

## Contents

| Folder | Notebook | PDF | Topic |
|--------|----------|-----|-------|
| `acoustic-scene-analysis/` | `acoustic_scene_analysis.ipynb` | `acoustic-scene-analysis.pdf` | BEATs, WavLM, HuBERT scene classification |
| `audio-foundation-models/` | `acoustic_scene_classification.ipynb` | `acoustic-scene-classification.pdf` | WavLM linear probe demo |
| `speech_enhancement/` | `speech_enhancement.ipynb` | `speech-enhancement.pdf` | CNN spectral masking + MetricGAN+ |
| `edge-cloud-hearing/` | `edge_cloud_audio_processing.ipynb` | `edge-cloud-audio-processing.pdf` | Edge–cloud hearing-aid prototype |

## Setup

Python 3.10+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook
```

Open any `.ipynb` and run cells **top to bottom**.

## Internet required (first run)

Each notebook downloads from the [Hugging Face Hub](https://huggingface.co/):

- **Models** — e.g. WavLM, HuBERT, MetricGAN+
- **Datasets** — e.g. TUT2017, LibriSpeech dummy set
- **BEATs code** — auto-downloaded into `beats_src/` if missing (also included in this zip)

Cached files go to `~/.cache/huggingface/`. SpeechBrain saves MetricGAN+ under `speech_enhancement/pretrained_models/`.

## Hardware

- All notebooks run on **CPU** (tested).
- GPU optional — set automatically when CUDA is available.
- Speech enhancement training: ~2–3 min on CPU. WavLM embedding passes: ~1 min for 80 clips.

## Optional: Hugging Face token

Downloads work without a token. For faster limits, set:

```bash
export HF_TOKEN=your_token_here
```
