import marimo

__generated_with = "0.23.16"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Pink Elephant TXT2VID — MiniMax H3 Text-to-Video

    One notebook to run **MiniMax H3**, the open-sourced (2026) general-purpose
    omni-modal video model, and generate **video + native stereo audio** from a
    text prompt.

    - **Model:** [MiniMaxAI/MiniMax-H3](https://huggingface.co/MiniMaxAI/MiniMax-H3)
      (MiniMax H3 Community License)
    - **Task:** `t2va` — Text → Video + Audio (24 fps, 5–15 s, 768p short edge,
      native stereo sound). The model generates the video and its own soundtrack
      together in one denoising loop.
    - **Runtime:** molab with a **96 GB VRAM** GPU.

    ## How to run

    1. Open this notebook in molab.
    2. **Attach a GPU** (96 GB VRAM) via the notebook header specs button.
    3. Run cells **top to bottom**. The first run downloads ~65 GB of weights
       (allow 15–40 min); later runs reuse the cache, so re-runs are fast.
    4. Set your prompt in **Config**, run **Load model**, then **Generate** and
       watch the video render inline. Save it from the **Download** cell.

    > MiniMax H3 needs ~62 GB of *quantized* weights. On a 96 GB card everything
    > fits on the accelerator. A free / low-RAM runtime will not work — this
    > notebook is built for the molab 96 GB Blackwell node.
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
    from the maintained pull request that adds it.
    """)
    return


@app.cell
def _(mo):
    import subprocess, sys
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-qU",
        "git+https://github.com/huggingface/diffusers.git@refs/pull/14355/head",
        "transformers", "accelerate", "torchao", "safetensors",
        "imageio", "imageio-ffmpeg",
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
    from diffusers.utils.export_utils import encode_video

    print("imports OK")
    return MiniMaxH3Transformer3DModel, ModularPipeline, TorchAoConfig, Qwen3VLForConditionalGeneration, TransformersTorchAoConfig, Int8WeightOnlyConfig, encode_video


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
    if vram_gb < 60:
        mo.callout(
            f"Only {vram_gb:.0f} GB VRAM detected. MiniMax H3 needs ~62 GB of "
            "quantized weights plus activations. Attach the 96 GB GPU in the "
            "runtime specs, then re-run this cell.",
            kind="warn",
        )
    else:
        mo.callout(f"GPU OK — {vram_gb:.0f} GB VRAM. Ready to load the model.", kind="success")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Config

    Set your prompt and generation parameters.

    **Frames:** MiniMax-H3 runs at **24 fps**, snaps `num_frames` up to the VAE
    grid `17*n + 5`, and allows **5–15 seconds** (`124`–`365` frames). `124` ≈ 5.2s.

    **Canvas:** only a multiple of 32 is allowed. A smaller canvas is much
    faster per step — `544×960` runs ~2.3× faster than the trained `768p` short
    edge.
    """)
    return


@app.cell
def _(mo):
    PROMPT = mo.ui.text(
        label="Prompt",
        value="A red fox trotting through a snowy pine forest, snow crunching underfoot",
    )
    NUM_FRAMES = mo.ui.number(124, 365, 124, step=17, label="frames (24 fps; 124–365)")
    HEIGHT = mo.ui.number(288, 768, 544, step=32, label="height")
    WIDTH = mo.ui.number(512, 1344, 960, step=32, label="width")
    STEPS = mo.ui.number(15, 60, 30, step=1, label="denoising steps")
    SEED = mo.ui.number(0, 2**31 - 1, 42, step=1, label="seed")
    mo.vstack([PROMPT, NUM_FRAMES, HEIGHT, WIDTH, STEPS, SEED]).callout()
    return HEIGHT, NUM_FRAMES, PROMPT, SEED, STEPS, WIDTH


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Load the model (int8, on-card)

    Both big components (the 61.7 GB transformer and the 62.1 GB Qwen3-VL
    conditioner) are loaded as **int8 weight-only quantized** — this brings
    them down to ~62 GB combined so they fit on a 96 GB card. We then freeze
    the weights (`requires_grad_(False)`) and move everything to the GPU.

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
        text_encoder=Qwen3VLForConditionalGeneration.from_pretrained(
            MODEL_ID, subfolder="text_encoder", dtype=torch.bfloat16,
            quantization_config=TransformersTorchAoConfig(Int8WeightOnlyConfig(version=2), modules_to_not_convert=NO_CONVERT_TEXT),
        ),
    )
    pipe.load_components(workflow="t2va", dtype=torch.bfloat16)

    pipe.transformer.requires_grad_(False)
    pipe.text_encoder.requires_grad_(False)

    if torch.cuda.is_available():
        pipe.transformer.to("cuda")
        pipe.text_encoder.to("cuda")
        pipe.vae.to("cuda")
        pipe.audio_vae.to("cuda")

    mo.callout("Model loaded and moved to GPU.", kind="success")
    return pipe


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Generate

    This is the slow step (a 30-step 544×960 clip takes roughly 2–5 min on a
    96 GB Blackwell). The model returns the video frames **and** its own stereo
    soundtrack together. We wrap generation so any error prints clearly instead
    of crashing the notebook.
    """)
    return


@app.cell
def _(HEIGHT, NUM_FRAMES, PROMPT, SEED, STEPS, WIDTH, mo, pipe, torch):
    import torch as T

    try:
        with torch.inference_mode():
            generator = T.Generator().manual_seed(int(SEED.value))
            results = pipe(
                prompt=str(PROMPT.value),
                num_frames=int(NUM_FRAMES.value),
                height=int(HEIGHT.value),
                width=int(WIDTH.value),
                num_inference_steps=int(STEPS.value),
                generator=generator,
                output=["videos", "audio", "sampling_rate"],
            )
        n_frames = len(results["videos"][0])
        mo.callout(
            f"Generated {n_frames} frames (~{n_frames/24:.1f}s) at 24 fps, "
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
    OUT_MP4 = "pinkelephant-txt2vid.mp4"
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
        filename="pinkelephant-txt2vid.mp4",
        label="Download TXT2VID mp4",
    )
    return


if __name__ == "__main__":
    app.run()
