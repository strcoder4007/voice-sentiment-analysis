#!/usr/bin/env python3
"""
Gradio Interface for Voice Sentiment Analysis
Wav2Vec 2.0 + BERT Pipeline
"""

import gradio as gr
import pandas as pd
import os
from utils import custom_css
from voice_sentiment import VoiceSentimentAnalyzer

# Initialize model (once)
print("Loading models...")
analyzer = VoiceSentimentAnalyzer()
print("Models ready!")

def analyze_audio_file(audio_file):
    """Analyze an uploaded audio file"""
    if audio_file is None:
        return "No audio file provided", "", "", ""
    
    try:
        # Analyze the call
        result = analyzer.analyze_call(audio_file)
        
        # Format results
        transcription = result['transcription']
        sentiment = result['sentiment']
        score = f"{result['score']:.2f}"
        satisfaction = result['satisfaction']
        
        # Emoji based on sentiment
        emoji_map = {
            "POSITIVE": "😊",
            "NEGATIVE": "😠", 
            "NEUTRAL": "😐"
        }
        emoji = emoji_map.get(sentiment, "❓")
        
        status = f"Analysis completed {emoji}"
        
        return status, transcription, sentiment, score, satisfaction
        
    except Exception as e:
        error_msg = f"Analysis error: {str(e)}"
        return error_msg, "", "", "", ""

def analyze_batch_files(files):
    """Analyze multiple audio files"""
    if not files:
        return "No files provided", None
    
    try:
        results = []
        
        for file in files:
            result = analyzer.analyze_call(file.name)
            results.append({
                "File": os.path.basename(file.name),
                "Transcription": result['transcription'][:100] + "..." if len(result['transcription']) > 100 else result['transcription'],
                "Sentiment": result['sentiment'],
                "Score": round(result['score'], 2),
                "Satisfaction": result['satisfaction']
            })
        
        # Create DataFrame for display
        df = pd.DataFrame(results)
        csv_filename = "analysis_results.csv"

        print(f"Saving {len(df)} rows to CSV...")
        df.to_csv(csv_filename, index=False)
        print(f"CSV saved successfully")  # 

        # Verify CSV was created and has content
        if os.path.exists(csv_filename):  # ← NEW DEBUG BLOCK
            file_size = os.path.getsize(csv_filename)
            print(f"CSV file exists, size: {file_size} bytes")
        else:
            print("CSV file was not created!")

        
        # Statistics
        total = len(results)
        positive = len([r for r in results if r['Sentiment'] == 'POSITIVE'])
        negative = len([r for r in results if r['Sentiment'] == 'NEGATIVE'])
        neutral = len([r for r in results if r['Sentiment'] == 'NEUTRAL'])
        
        stats = f"""📊 Statistics:
• Total: {total} calls
• Positive: {positive} ({positive/total*100:.1f}%)
• Negative: {negative} ({negative/total*100:.1f}%)
• Neutral: {neutral} ({neutral/total*100:.1f}%)"""
        
        return stats, df
        
    except Exception as e:
        error_msg = f"Analysis error: {str(e)}"
        return error_msg, None

# Gradio Interface
with gr.Blocks(title="Voice Sentiment Analysis", theme=gr.themes.Soft(), css=custom_css) as app:
    
    gr.Markdown("""
    # Voice Sentiment Analysis System
    ### Wav2Vec 2.0 + BERT Pipeline
    
    Automatically analyze customer call sentiment and classify satisfaction.
    """)
    
    with gr.Tabs():
        
        # Tab 1: Single file analysis
        with gr.Tab("Single File"):
            gr.Markdown("### Analyze one voice call")
            
            with gr.Row():
                with gr.Column():
                    audio_input = gr.Audio(
                        type="filepath",
                        label="Upload your audio file"
                    )
                    
                    analyze_btn = gr.Button(
                        "Analyze", 
                        variant="primary",
                        size="lg"
                    )
                
                with gr.Column():
                    status_output = gr.Textbox(
                        label="📊 Status",
                        interactive=False
                    )
                    
                    transcription_output = gr.Textbox(
                        label="📝 Transcription",
                        lines=3,
                        interactive=False
                    )
                    
                    with gr.Row():
                        sentiment_output = gr.Textbox(
                            label="🎭 Sentiment",
                            interactive=False
                        )
                        score_output = gr.Textbox(
                            label="🎯 Confidence Score",
                            interactive=False
                        )
                    
                    satisfaction_output = gr.Textbox(
                        label="😊 Customer Satisfaction",
                        interactive=False
                    )
        
        # Tab 2: Multiple files analysis
        with gr.Tab("Multiple Files"):
            gr.Markdown("### Analyze multiple calls in batch")
            
            files_input = gr.File(
                file_count="multiple",
                file_types=[".wav", ".mp3", ".m4a"],
                label="Upload your audio files"
            )
            
            batch_analyze_btn = gr.Button(
                "Analyze All", 
                variant="primary",
                size="lg"
            )
            
            batch_status = gr.Textbox(
                label="Statistics",
                lines=6,
                interactive=False
            )
            
            results_table = gr.Dataframe(
                label="Detailed Results",
                interactive=False
            )
    
    # Tab 3: Information
    with gr.Tab("Information"):
        gr.Markdown("""
        ### How it works?
        
        **3-step pipeline:**
        1. **Audio → Text**: Transcription with Wav2Vec 2.0
        2. **Text → Sentiment**: Analysis with multilingual BERT  
        3. **Classification**: Customer satisfaction (Satisfied/Dissatisfied/Neutral)
        
        ### Supported formats
        - WAV (recommended)
        - MP3
        - M4A
        
        ### Classifications
        - **😊 Satisfied**: Positive sentiment with high confidence
        - **😠 Dissatisfied**: Negative sentiment with high confidence
        - **😐 Neutral**: Neutral sentiment or low confidence
        
        ### Tips
        - Clear audio quality recommended
        - Optimal duration: 10 seconds to 2 minutes
        - Avoid excessive background noise
        """)
    
    # Event connections
    analyze_btn.click(
        fn=analyze_audio_file,
        inputs=[audio_input],
        outputs=[status_output, transcription_output, sentiment_output, score_output, satisfaction_output]
    )
    
    batch_analyze_btn.click(
        fn=analyze_batch_files,
        inputs=[files_input],
        outputs=[batch_status, results_table]
    )

# Launch the application
if __name__ == "__main__":
    app.launch(
        share=True,  # Creates a public link
        server_name="0.0.0.0",  # Accessible from other machines
        server_port=7860
    )