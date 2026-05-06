from huggingface_hub import hf_hub_download

TOKEN = "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"  # ← ここに貼り付け

print("VAEダウンロード中...")
hf_hub_download(
    repo_id="black-forest-labs/FLUX.1-schnell",
    filename="ae.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\vae",
    token=TOKEN
)
print("VAE完了")

print("CLIP Lダウンロード中...")
hf_hub_download(
    repo_id="comfyanonymous/flux_text_encoders",
    filename="clip_l.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\clip",
    token=TOKEN
)
print("CLIP L完了")

print("T5 XXLダウンロード中...")
hf_hub_download(
    repo_id="comfyanonymous/flux_text_encoders",
    filename="t5xxl_fp8_e4m3fn.safetensors",
    local_dir=r"C:\Users\info\Desktop\dev\tools\ComfyUI\models\clip",
    token=TOKEN
)
print("T5 XXL完了")

print("全ダウンロード完了")