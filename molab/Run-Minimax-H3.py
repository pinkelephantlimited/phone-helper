import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Run-Minimax-H3 — MiniMax H3, all three workflows

    One notebook to run **MiniMax H3**, the open-sourced (2026) general-purpose
    omni-modal video model, and generate **video + native stereo audio** from a
    text prompt, first/last keyframes, or an ordered mix of image, video and
    audio references.

    - **Model:** [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3)
      (MiniMax H3 Community License)
    - **Workflows:** `t2va` (text → video + audio), `fl2va` (first/last
      keyframe → video + audio), `ref2va` (omni-references → video + audio).
      Video and audio come out of the **same denoising loop** — no separate
      vocoder, no `negative_prompt`, no `guidance_scale` (the weights are
      guidance-distilled).
    - **Runtime:** molab with a **96 GB VRAM** GPU.

    ## How to run

    1. Open this notebook in molab.
    2. **Attach a GPU** (96 GB VRAM) via the notebook header specs button.
    3. Run cells **top to bottom**. The first run downloads ~125 GB of weights
       (allow 30–60 min); later runs reuse the cache, so re-runs are fast.
    4. Pick a **workflow** in Config, run **Load model**, then **Generate** and
       watch the video render inline. Save it from the **Download** cell.

    > MiniMax H3 needs both ~62 GB transformer partitions and the Qwen3-VL
    > conditioner at **int8** to fit one card. This notebook is built for the
    > molab 96 GB Blackwell node — a free / low-RAM runtime will not work.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Check compute

    Confirm the GPU is attached and usable.
    """)
    return


@app.cell
def _(mo):
    import torch

    print("torch:", torch.__version__)
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
        print("VRAM (GB):", round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1))
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    mo.md(f"**Device:** `{DEVICE}`")
    return DEVICE, torch


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Install the open-source MiniMax-H3 integration

    MiniMax-H3 is **not in a diffusers release yet**, so we install diffusers
    from the maintained pull request that adds it (`av` is PyAV, used to decode
    video/audio references).
    """)
    return


@app.cell
def _(mo):
    import subprocess, sys
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-qU",
        "git+https://github.com/huggingface/diffusers.git@refs/pull/14355/head",
        "transformers", "accelerate", "torchao", "safetensors",
        "imageio", "imageio-ffmpeg", "av",
    ], check=True)
    import importlib, diffusers
    importlib.reload(diffusers)
    mo.md(f"**diffusers:** `{diffusers.__version__}`")
    return


@app.cell
def _():
    from diffusers import MiniMaxH3Transformer3DModel, ModularPipeline, TorchAoConfig
    from transformers import Qwen3VLForConditionalGeneration
    from transformers import TorchAoConfig as TransformersTorchAoConfig
    from torchao.quantization import Int8WeightOnlyConfig
    from diffusers.utils import load_image
    from diffusers.utils.export_utils import encode_video
    from diffusers.modular_pipelines.minimax_h3 import MiniMaxH3ImageReference
    from diffusers.modular_pipelines.minimax_h3 import MiniMaxH3VideoReference
    from diffusers.modular_pipelines.minimax_h3 import MiniMaxH3AudioReference

    print("imports OK")
    return (MiniMaxH3Transformer3DModel, ModularPipeline, TorchAoConfig,
            Qwen3VLForConditionalGeneration, TransformersTorchAoConfig,
            Int8WeightOnlyConfig, load_image, encode_video,
            MiniMaxH3ImageReference, MiniMaxH3VideoReference, MiniMaxH3AudioReference)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Hardware guard

    Quick sanity check so we stop early on a small runtime instead of waiting
    for a multi-GB download that will fail. Uses a `mo.callout` (the correct
    marimo API).
    """)
    return


@app.cell
def _(mo, torch):
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else 0
    if vram_gb < 80:
        mo.callout(
            f"Only {vram_gb:.0f} GB VRAM detected. Run-Minimax-H3 loads both "
            "transformer partitions plus the Qwen3-VL conditioner, which takes "
            "~90 GB of VRAM at int8. Attach the 96 GB GPU in the runtime "
            "specs, then re-run this cell.",
            kind="warn",
        )
    else:
        mo.callout(f"GPU OK — {vram_gb:.0f} GB VRAM. Ready to load the model.", kind="success")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Config

    **Workflow:**
    - `t2va` — text → video + audio (prompt only).
    - `fl2va` — text + a *first* keyframe and/or *last* keyframe (URLs below).
    - `ref2va` — text + up to **9 images / 3 videos / 3 audio clips** as
      references (URLs below). Order matters! The model labels them
      `"<Picture 1>"`, `"<Video 1>"`, `"<Audio 1>"` in the prompt.

    **Frames:** MiniMax-H3 runs at **24 fps**, snaps `num_frames` up to the VAE
    grid `17*n + 5`, and allows **5–15 seconds** (`124`–`365` frames).

    **Canvas:** a multiple of 32. Smaller is much faster — `544×960` runs
    ~2.3× faster per step than the trained `768p` short edge. For `fl2va`
    the canvas follows the first keyframe's aspect ratio.
    """)
    return


@app.cell
def _(mo):
    TASK = mo.ui.dropdown(
        options=["t2va", "fl2va", "ref2va"],
        value="t2va",
        label="Workflow",
    )
    PROMPT = mo.ui.text(
        label="Prompt",
        value="A red fox trotting through a snowy pine forest, snow crunching underfoot",
    )
    NUM_FRAMES = mo.ui.number(124, 365, 124, step=17, label="frames (24 fps; 124–365)")
    HEIGHT = mo.ui.number(288, 768, 544, step=32, label="height")
    WIDTH = mo.ui.number(512, 1344, 960, step=32, label="width")
    STEPS = mo.ui.number(15, 60, 30, step=1, label="denoising steps")
    SEED = mo.ui.number(0, 2**31 - 1, 42, step=1, label="seed")

    FIRST_URL = mo.ui.text(label="fl2va: first keyframe image URL (optional)", value="")
    LAST_URL = mo.ui.text(label="fl2va: last keyframe image URL (optional)", value="")
    REF_IMG_URL = mo.ui.text(label="ref2va: reference image URL (optional)", value="")
    REF_VID_URL = mo.ui.text(label="ref2va: reference video URL (optional)", value="")
    REF_AUD_URL = mo.ui.text(label="ref2va: reference audio URL (optional)", value="")

    mo.vstack([
        mo.md("**Task**"),
        TASK,
        PROMPT,
        NUM_FRAMES,
        HEIGHT,
        WIDTH,
        STEPS,
        SEED,
        mo.md("**Keyframes (fl2va)**"),
        FIRST_URL,
        LAST_URL,
        mo.md("**References (ref2va)**"),
        REF_IMG_URL,
        REF_VID_URL,
        REF_AUD_URL,
    ]).callout()
    return (TASK, PROMPT, NUM_FRAMES, HEIGHT, WIDTH, STEPS, SEED,
            FIRST_URL, LAST_URL, REF_IMG_URL, REF_VID_URL, REF_AUD_URL)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Load the model (int8, on-card)

    MiniMax H3 ships as **two checkpoint partitions** that share everything
    except the transformer (`transformer/` for `t2va`+`fl2va`,
    `transformer_ref/` for `ref2va`). They are the same ~61.7 GB transformer
    architecture, so we load **both** as **int8 weight-only** — that, plus the
    int8 Qwen3-VL conditioner, hugs the edge of a 96 GB card while still
    fitting together with the VAE. We freeze weights and move everything to the
    GPU. Loading both partitions is what lets one pipeline serve all three
    workflows.

    First run downloads the weights; watch the progress bar.
    """)
    return


@app.cell
def _(
    MiniMaxH3Transformer3DModel,
    ModularPipeline,
    Qwen3VLForConditionalGeneration,
    TorchAoConfig,
    TransformersTorchAoConfig,
    Int8WeightOnlyConfig,
    mo,
    torch,
):
    MODEL_ID = "MiniMaxAI/MiniMax-H3"
    NO_CONVERT = [
        "proj_in", "audio_proj_in", "context_embedder", "time_embedder", "time_proj",
        "token_refiner", "norm_out", "proj_out", "audio_proj_out",
    ]
    NO_CONVERT_TEXT = [
        "model.visual", "model.language_model.embed_tokens", "model.language_model.norm", "lm_head",
    ]

    pipe = ModularPipeline.from_pretrained(MODEL_ID)
    pipe.update_components(
        transformer=MiniMaxH3Transformer3DModel.from_pretrained(
            MODEL_ID, subfolder="transformer", dtype=torch.bfloat16,
            quantization_config=TorchAoConfig(Int8WeightOnlyConfig(version=2), modules_to_not_convert=NO_CONVERT),
            low_cpu_mem_usage=False,
        ),
        transformer_ref=MiniMaxH3Transformer3DModel.from_pretrained(
            MODEL_ID, subfolder="transformer_ref", dtype=torch.bfloat16,
            quantization_config=TorchAoConfig(Int8WeightOnlyConfig(version=2), modules_to_not_convert=NO_CONVERT),
            low_cpu_mem_usage=False,
        ),
        text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(
            MODEL_ID, subfolder="text_encoder", dtype=torch.bfloat16,
            quantization_config=TransformersTorchAoConfig(Int8WeightOnlyConfig(version=2), modules_to_not_convert=NO_CONVERT_TEXT),
        ),
    )
    pipe.load_components(workflow="t2va", dtype=torch.bfloat16)
    pipe.load_components(workflow="ref2va", dtype=torch.bfloat16)

    pipe.transformer.requires_grad_(False)
    pipe.transformer_ref.requires_grad_(False)
    pipe.text_encoder.requires_grad_(False)

    if torch.cuda.is_available():
        pipe.transformer.to("cuda")
        pipe.transformer_ref.to("cuda")
        pipe.text_encoder.to("cuda")
        pipe.vae.to("cuda")
        pipe.audio_vae.to("cuda")

    mo.callout("Model loaded and moved to GPU — all three workflows ready.", kind="success")
    return pipe


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Generate

    The slow step (a 30-step 544×960 clip takes roughly 2–5 min on a 96 GB
    Blackwell). The model returns the video frames **and** its own stereo
    soundtrack together. The call picks the workflow from its inputs:
    `image`/`last_image` → `fl2va`, `references` → `ref2va`, otherwise `t2va`.

    For `ref2va`, media URLs are decoded with each reference class's
    `from_file`, which brings the media's own frame rate / sample rate along —
    so a video reference is conditioned on at the right speed.
    """)
    return


@app.cell
def _(HEIGHT, NUM_FRAMES, PROMPT, SEED, STEPS, TASK, FIRST_URL, LAST_URL,
      REF_IMG_URL, REF_VID_URL, REF_AUD_URL, load_image,
      MiniMaxH3ImageReference, MiniMaxH3VideoReference, MiniMaxH3AudioReference,
      pipe, torch, mo):
    try:
        kwargs = dict(
            prompt=str(PROMPT.value),
            num_frames=int(NUM_FRAMES.value),
            height=int(HEIGHT.value),
            width=int(WIDTH.value),
            num_inference_steps=int(STEPS.value),
            generator=torch.Generator().manual_seed(int(SEED.value)),
            output=["videos", "audio", "sampling_rate"],
        )
        task = str(TASK.value)

        if task == "fl2va":
            if FIRST_URL.value.strip():
                kwargs["image"] = load_image(FIRST_URL.value.strip())
            if LAST_URL.value.strip():
                kwargs["last_image"] = load_image(LAST_URL.value.strip())

        if task == "ref2va":
            refs = []
            if REF_IMG_URL.value.strip():
                refs.append(MiniMaxH3ImageReference.from_file(REF_IMG_URL.value.strip()))
            if REF_VID_URL.value.strip():
                refs.append(MiniMaxH3VideoReference.from_file(REF_VID_URL.value.strip()))
            if REF_AUD_URL.value.strip():
                refs.append(MiniMaxH3AudioReference.from_file(REF_AUD_URL.value.strip()))
            if refs:
                kwargs["references"] = refs
            else:
                task = "t2va"  # nothing to condition on — fall back to text only

        with torch.inference_mode():
            results = pipe(**kwargs)
        n_frames = len(results["videos"][0])
        mo.callout(
            f"[{task}] Generated {n_frames} frames (~{n_frames/24:.1f}s) at 24 fps, "
            f"audio at {results['sampling_rate']} Hz.",
            kind="success",
        )
    except Exception as e:
        mo.callout(f"Generation failed: {e}", kind="danger")
        raise
    return results


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Encode to MP4 (video + audio)

    Mux the frames and the synthesized soundtrack into a single `.mp4`.
    """)
    return


@app.cell
def _(encode_video, mo, results):
    OUT_MP4 = "minimax-h3.mp4"
    encode_video(
        results["videos"][0],
        fps=24,
        output_path=OUT_MP4,
        audio=results["audio"][0],
        audio_sample_rate=results["sampling_rate"],
    )
    mo.video(OUT_MP4)
    return OUT_MP4


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 8. Download

    A `mo.download` button for the generated MP4.
    """)
    return


@app.cell
def _(OUT_MP4, mo):
    import io

    with open(OUT_MP4, "rb") as f:
        data = f.read()
    mo.download(
        io.BytesIO(data),
        filename="minimax-h3.mp4",
        label="Download-minimax-h3 mp4",
    )
    return


if __name__ == "__main__":
    app.run()