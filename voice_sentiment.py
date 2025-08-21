"""
Simple Voice Sentiment Analysis System
Wav2Vec 2.0 + BERT Pipeline
"""

import torch
import librosa
import numpy as np
from transformers import (
    Wav2Vec2ForCTC, 
    Wav2Vec2Tokenizer, 
    pipeline
)
import pandas as pd
import os

class VoiceSentimentAnalyzer:
    """Simple Pipeline: Audio → Transcription → Sentiment Analysis"""
    
    def __init__(self):
        print("Loading models...")
        
        # ASR Model (Speech-to-Text)
        self.asr_tokenizer = Wav2Vec2Tokenizer.from_pretrained("facebook/wav2vec2-large-960h-lv60-self")
        self.asr_model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-large-960h-lv60-self")
        
        # Sentiment Model
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment"
        )
        
        print("Models loaded!")
    
    def audio_to_text(self, audio_path):
        """Convert audio to text"""
        # Load and preprocess audio
        audio, sr = librosa.load(audio_path, sr=16000)
        
        # Transcription with Wav2Vec2
        input_values = self.asr_tokenizer(audio, return_tensors="pt", sampling_rate=16000).input_values
        
        with torch.no_grad():
            logits = self.asr_model(input_values).logits
        
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.asr_tokenizer.decode(predicted_ids[0])
        
        return transcription.strip()
    
    def text_to_sentiment(self, text):
        """Analyze sentiment of the text"""
        if not text:
            return {"sentiment": "NEUTRAL", "score": 0.0}
        
        result = self.sentiment_analyzer(text)[0]
        
        # Convert labels to simple format
        label_map = {
            "1 star": "NEGATIVE", "2 stars": "NEGATIVE",
            "3 stars": "NEUTRAL", 
            "4 stars": "POSITIVE", "5 stars": "POSITIVE"
        }
        
        sentiment = label_map.get(result['label'], result['label'])
        
        return {
            "sentiment": sentiment,
            "score": result['score']
        }
    
    def classify_satisfaction(self, sentiment, score):
        """Classify customer satisfaction"""
        if sentiment == "POSITIVE" and score > 0.7:
            return "Satisfied"
        elif sentiment == "NEGATIVE" and score > 0.7:
            return "Dissatisfied"
        else:
            return "Neutral"
    
    def analyze_call(self, audio_path):
        """Complete pipeline: Audio → Sentiment → Classification"""
        print(f"Analyzing: {audio_path}")
        
        # 1. Audio → Text
        transcription = self.audio_to_text(audio_path)
        print(f"Transcription: {transcription}")
        
        # 2. Text → Sentiment
        sentiment_result = self.text_to_sentiment(transcription)
        print(f"Sentiment: {sentiment_result['sentiment']} (score: {sentiment_result['score']:.2f})")
        
        # 3. Satisfaction classification
        satisfaction = self.classify_satisfaction(sentiment_result['sentiment'], sentiment_result['score'])
        print(f"Satisfaction: {satisfaction}")
        
        return {
            "file": os.path.basename(audio_path),
            "transcription": transcription,
            "sentiment": sentiment_result['sentiment'],
            "score": sentiment_result['score'],
            "satisfaction": satisfaction
        }
    
    def analyze_batch(self, audio_folder):
        """Analyze a folder of calls"""
        results = []
        
        for filename in os.listdir(audio_folder):
            if filename.endswith(('.wav', '.mp3', '.m4a')):
                audio_path = os.path.join(audio_folder, filename)
                result = self.analyze_call(audio_path)
                results.append(result)
                print("-" * 50)
        
        # Save to CSV
        df = pd.DataFrame(results)
        df.to_csv("analysis_results.csv", index=False)
        print(f"Results saved: analysis_results.csv")
        
        # Quick statistics
        print("\nSTATISTICS:")
        print(f"Total calls: {len(results)}")
        sentiment_counts = df['sentiment'].value_counts()
        for sentiment, count in sentiment_counts.items():
            print(f"{sentiment}: {count}")
        
        return df