import requests
import json

prompt = "AI technology, neural network visualization, futuristic blue gradient, ultra high quality 4K"
negative = "blurry, low quality, text, watermark, human face"
article_id = 1

workflow = {
    "1": {
        "class_type": "UnetLoaderGGUF",
        "inputs": {"unet_name": "flux1-schnell-Q8_0.gguf"}
    },
    "2": {
        "class_type": "DualCLIPLoader",
        "inputs": {
            "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
            "clip_name2": "clip_l.safetensors",
            "type": "flux",
            "device": "default"
        }
    },
    "3": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "ae.safetensors"}
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt, "clip": ["2", 0]}
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": ["2", 0]}
    },
    "6": {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": 1280, "height": 720, "batch_size": 1}
    },
    "7": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["4", 0],
            "negative": ["5", 0],
            "latent_image": ["6", 0],
            "seed": article_id,
            "steps": 4,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {"samples": ["7", 0], "vae": ["3", 0]}
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {"images": ["8", 0], "filename_prefix": f"article_{article_id}"}
    }
}

res = requests.post("http://localhost:8188/prompt", json={"prompt": workflow})
print(f"ステータス: {res.status_code}")
print(f"レスポンス: {json.dumps(res.json(), indent=2, ensure_ascii=False)}")