import subprocess
img = "/marimo/multilingual_ds/images/en/en-00000-0000000000.jpg"
import glob
imgs = glob.glob("/marimo/multilingual_ds/images/en/*.jpg")
img = imgs[0]
print("test image:", img)
cmd = [
    "bash", "-c",
    "cd /marimo/models && timeout 280 /marimo/llama.cpp/build/bin/llama-cli "
    "-m phone-helper-3b-q4_k_m.gguf "
    "-mmproj phone-helper-3b-q4_k_m.f16-mmproj.gguf "
    "-p 'Describe this image. What is in it and any dates or prices?' "
    "--image " + img + " -n 60 --no-display-prompt 2>&1 | tail -30",
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=295)
print(r.stdout[-2600:])