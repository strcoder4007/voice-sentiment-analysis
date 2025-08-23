import os
import torch
import librosa
from transformers import AutoModel, AutoProcessor

model_id = "mlx-community/Voxtral-Mini-3B-2507-bf16"
device = "mps" if torch.backends.mps.is_available() else "cpu"

processor = AutoProcessor.from_pretrained(model_id)
model = AutoModelForAudioClassification.from_pretrained(model_id).to(device)

def analyze_audio_file(file_path: str):
    audio, sr = librosa.load(file_path, sr=16000)
    inputs = processor.feature_extractor(audio, sampling_rate=sr, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs


def analyze_directory(audio_dir: str):
    results = {}
    for file in os.listdir(audio_dir):
        if file.endswith((".mp3", ".wav", ".m4a")):
            path = os.path.join(audio_dir, file)
            results[file] = analyze_audio_file(path)
    return results

if __name__ == "__main__":
    audio_dir = "audios"
    results = analyze_directory(audio_dir)
    for file, sentiment in results.items():
        print(f"{file}: {sentiment}")
