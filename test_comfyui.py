# test_comfyui.py
import requests
import json
import time

COMFYUI_URL = "http://localhost:8188"

workflow = {
    "1": {
    "class_type": "UnetLoaderGGUF",
    "inputs": {
        "unet_name": "flux1-schnell-Q8_0.gguf"
    }
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
        "inputs": {
            "vae_name": "ae.safetensors"
        }
    },
    "4": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "AI technology, neural network visualization, futuristic blue gradient, ultra high quality, 4K",
            "clip": ["2", 0]
        }
    },
    "5": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "blurry, low quality, text, watermark",
            "clip": ["2", 0]
        }
    },
    "6": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "width": 1280,
            "height": 720,
            "batch_size": 1
        }
    },
    "7": {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["4", 0],
            "negative": ["5", 0],
            "latent_image": ["6", 0],
            "seed": 42,
            "steps": 4,
            "cfg": 1.0,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1.0
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["7", 0],
            "vae": ["3", 0]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["8", 0],
            "filename_prefix": "test_flux"
        }
    }
}

print("テスト画像生成中...")
res = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow})
print(f"ステータス: {res.status_code}")

if res.status_code == 200:
    prompt_id = res.json()["prompt_id"]
    print(f"prompt_id: {prompt_id}")
    print("完了待機中...")

    for i in range(120):
        time.sleep(1)
        history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}").json()
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_id, output in outputs.items():
                if "images" in output:
                    filename = output["images"][0]["filename"]
                    print(f"✅ 生成成功: {filename}")
                    print(f"確認: http://localhost:8188/view?filename={filename}&type=output")
            break
        if i % 10 == 0:
            print(f"待機中... {i}秒")
else:
    print(f"エラー: {res.text}")