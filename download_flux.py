# download_flux.py として保存して実行
from huggingface_hub import hf_hub_download

# FLUX.1 Schnell GGUF量子化版（約9GB）
hf_hub_download(
    repo_id="city96/FLUX.1-schnell-gguf",
    filename="flux1-schnell-Q8_0.gguf",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\unet"
)

# VAE
hf_hub_download(
    repo_id="black-forest-labs/FLUX.1-schnell",
    filename="ae.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\vae"
)

# CLIPテキストエンコーダ
hf_hub_download(
    repo_id="comfyanonymous/flux_text_encoders",
    filename="clip_l.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\clip"
)
hf_hub_download(
    repo_id="comfyanonymous/flux_text_encoders",
    filename="t5xxl_fp8_e4m3fn.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\clip"
)

print("ダウンロード完了")