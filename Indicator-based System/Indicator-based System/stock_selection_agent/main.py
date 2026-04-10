import os
import colorama
from colorama import Fore, Style
from stock_selection_agent.agent.core import StockSelectionAgent

colorama.init()

def run_chat_loop(agent):
    print(f"{Fore.GREEN}Agent initialized successfully.{Style.RESET_ALL}")
    print("Type 'exit' or 'quit' to end.")
    print("Type '/clear' to start new conversation.")
    print(f"{Fore.CYAN}Agent: {agent.intro_message()}{Style.RESET_ALL}")

    while True:
        try:
            user_input = input(f"\n{Fore.GREEN}You: {Style.RESET_ALL}").strip()
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit']:
                print("Thank you for using Stock Selection Agent. Goodbye!")
                break
            if user_input.lower() == '/clear':
                agent.clear_history()
                print(f"{Fore.YELLOW}History cleared.{Style.RESET_ALL}")
                continue

            agent.run(user_input)

        except (KeyboardInterrupt, EOFError):
            print("\nThank you for using Stock Selection Agent. Goodbye!")
            os._exit(0)
        except Exception as e:
            print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")

def main():
    print(f"{Fore.GREEN}Welcome to Stock-Selection-Agent!{Style.RESET_ALL}")
    print("Initializing...")
    agent = StockSelectionAgent()
    run_chat_loop(agent)

if __name__ == "__main__":
    main()
