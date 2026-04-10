import os
import sys
from src.utils.config import DEEPSEEK_API_KEY
from src.app.momentum_app import MomentumEventAnalyzerApp

if __name__ == "__main__":
    # Example Usage
    api_key = DEEPSEEK_API_KEY
    if not api_key and "DEEPSEEK_API_KEY" in os.environ:
        api_key = os.environ["DEEPSEEK_API_KEY"]
        
    if not api_key:
        print("Error: DEEPSEEK_API_KEY not found in config or environment variables.")
        exit(1)
        
    app = MomentumEventAnalyzerApp(api_key)
    
    print("Momentum Event Analyzer")
    print("------------------------------------------")
    
    # Allow user input or use default for testing
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        print(f"\nProcessing query: '{user_query}'...")
        app.handle_natural_language_query(user_query)
    else:
        while True:
            try:
                user_query = input("\nHow can I help you? (e.g., 'Recommend 5 momentum stocks', 'Analyze Tesla', 'What is momentum trading?'): ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ['exit', 'quit']:
                    break
                print(f"\nProcessing query: '{user_query}'...")
                app.handle_natural_language_query(user_query)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"An error occurred: {e}")
