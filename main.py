#!/usr/bin/env python3
"""
Main script for voice sentiment analysis
"""

from voice_sentiment import VoiceSentimentAnalyzer
import os

def main():
    """Main function"""
    print("VOICE SENTIMENT ANALYSIS SYSTEM")
    print("="*50)
    
    # Initialize the system
    analyzer = VoiceSentimentAnalyzer()
    
    # Simple menu
    while True:
        print("\nOptions:")
        print("1. Analyze an audio file")
        print("2. Analyze a folder of calls")
        print("3. Exit")
        
        choice = input("\nYour choice (1-3): ").strip()
        
        if choice == "1":
            # Single file analysis
            file_path = input("Audio file path: ").strip()
            
            if os.path.exists(file_path):
                try:
                    result = analyzer.analyze_call(file_path)
                    print("\nAnalysis completed!")
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print("File not found!")
        
        elif choice == "2":
            # Folder analysis
            folder_path = input("Folder path: ").strip()
            
            if os.path.exists(folder_path):
                try:
                    results = analyzer.analyze_batch(folder_path)
                    print(f"\n{len(results)} files analyzed!")
                except Exception as e:
                    print(f"Error: {e}")
            else:
                print("Folder not found!")
        
        elif choice == "3":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice!")

if __name__ == "__main__":
    main()