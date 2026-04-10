import inspect
from datetime import datetime
from types import SimpleNamespace
from colorama import Fore, Style
from stock_selection_agent.agent.prompts import SYSTEM_PROMPT
from stock_selection_agent.llm.deepseek import DeepSeekClient
from stock_selection_agent.tools.yfinance import execute_tool_call
from stock_selection_agent.tools.schema import TOOLS_SCHEMA


FORCED_TOOL_RULES = [
    ("generate_investment_report", ["report", "structured report", "investment recommendation", "investment advice"]),
    ("recommend_momentum_stocks_by_news", ["momentum stock", "momentum stocks", "find momentum", "momentum analysis", "momentum"]),
    ("run_backtest", ["backtest", "backtesting", "strategy test"]),
    ("evaluate_buy_signal", ["buy", "entry", "position", "bottom"]),
]

class StockSelectionAgent:
    def __init__(self):
        self.llm = DeepSeekClient()
        self.history = []
        self._time_checked_this_turn = False
        self._init_history()

    def _get_system_content(self):
        now = datetime.now().astimezone()
        runtime_time = (
            f"\nRuntime local datetime: {now.strftime('%Y-%m-%d %H:%M:%S')} ({str(now.tzinfo)}).\n"
        )
        return SYSTEM_PROMPT + runtime_time

    def _init_history(self):
        self.history = [{"role": "system", "content": self._get_system_content()}]

    def intro_message(self):
        return (
            "Hello, I'm your stock selection and backtesting assistant.\n" 
            "I fetch data from Yahoo Finance and use momentum strategy with fuzzy logic to select and backtest stocks.\n"
            "You may ask for investment advice, request for backtesting, or query stock data.\n"
            "Example 1: What is the current price of AAPL?\n"
            "Example 2: Backtest on AAPL for 1 year.\n"
            "Example 3: Is it a good time to buy AAPL now?\n"
            "Example 4: Provide some stocks with high momentum.\n"
            "Example 5: Generate investment advice for AAPL.\n"
        )

    def _to_dict(self, message):
        if isinstance(message, dict):
            return message
        if hasattr(message, 'model_dump'):
            return message.model_dump()
        if hasattr(message, 'to_dict'):
            return message.to_dict()
        return {
            "role": getattr(message, "role", "assistant"),
            "content": getattr(message, "content", ""),
            "tool_calls": getattr(message, "tool_calls", None)
        }

    def clear_history(self):
        """Clear conversation history (keep system prompt)."""
        self._init_history()

    def _detect_forced_tool(self, user_input):
        text = (user_input or "").lower()
        for tool_name, keywords in FORCED_TOOL_RULES:
            if any(keyword in text for keyword in keywords):
                return tool_name
        return None

    def _refresh_system_prompt(self):
        if self.history and self.history[0].get('role') == 'system':
            self.history[0]['content'] = self._get_system_content()
        else:
            self.history.insert(0, {"role": "system", "content": self._get_system_content()})

    def _resolve_tool_choice(self, step, forced_tool):
        if step == 1 and not self._time_checked_this_turn:
            return {"type": "function", "function": {"name": "get_current_time"}}
        if step == 2 and forced_tool:
            return {"type": "function", "function": {"name": forced_tool}}
        return "auto"

    def _consume_stream_response(self, response):
        full_content = ""
        message = None
        try:
            for chunk in response:
                chunk_type = chunk.get("type")
                if chunk_type == 'content':
                    content = chunk.get("content", "")
                    if content:
                        full_content += content
                        yield {"type": "content", "content": content}
                elif chunk_type == 'tool_call_chunk':
                    yield chunk
                elif chunk_type == 'response':
                    message = chunk.get("response")
            return message, False
        except KeyboardInterrupt:
            yield {"type": "error", "content": "Interrupted by user"}
            if full_content:
                message = SimpleNamespace(role="assistant", content=full_content, tool_calls=None)
                self.history.append(self._to_dict(message))
            return message, True

    def _execute_tool_calls(self, message):
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            arguments = tool_call.function.arguments
            call_id = tool_call.id

            if function_name == "get_current_time":
                self._time_checked_this_turn = True

            yield {"type": "tool_call", "tool_name": function_name, "args": arguments}

            try:
                tool_result = execute_tool_call(function_name, arguments)
            except Exception as e:
                tool_result = f"Error executing tool: {e}"

            yield {"type": "tool_result", "tool_name": function_name, "result": str(tool_result)}
            self.history.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": str(tool_result)
            })

    def stream_chat(self, user_input):
        if not self.llm:
            yield {"type": "error", "content": "LLM not initialized. Please check configuration."}
            return

        self._refresh_system_prompt()
        self._time_checked_this_turn = False
        self.history.append({"role": "user", "content": user_input})

        step = 0
        forced_tool = self._detect_forced_tool(user_input)
        try:
            while True:
                step += 1

                try:
                    tool_choice_value = self._resolve_tool_choice(step, forced_tool)
                    response = self.llm.chat(self.history, tools=TOOLS_SCHEMA, tool_choice=tool_choice_value, stream=True)

                    message = None

                    if inspect.isgenerator(response):
                        message, stream_interrupted = yield from self._consume_stream_response(response)
                        if stream_interrupted:
                            return
                    else:
                        message = response
                        if message.content:
                            yield {"type": "content", "content": message.content}

                except Exception as e:
                    err_msg = f"Error: {str(e)}"
                    yield {"type": "error", "content": err_msg}
                    return

                if not message:
                    return

                if not message.tool_calls:
                    answer = message.content if message.content else ""
                    self.history.append(self._to_dict(message))
                    yield {"type": "answer", "content": answer}
                    return

                self.history.append(self._to_dict(message))
                yield from self._execute_tool_calls(message)

        except KeyboardInterrupt:
            yield {"type": "error", "content": "Interrupted by user"}
            return

    def run(self, user_input):

        print(f"{Fore.CYAN}Agent: {Style.RESET_ALL}")

        generator = self.stream_chat(user_input)

        final_answer = ""
        has_streamed_content = False

        try:
            for event in generator:
                event_type = event['type']

                if event_type == 'content':
                    content = event['content']
                    print(content, end="", flush=True)
                    has_streamed_content = True

                elif event_type == 'tool_call':
                    if has_streamed_content:
                        print()
                        has_streamed_content = False
                    print(Style.RESET_ALL, end="", flush=True)

                    name = event['tool_name']
                    args = event['args']
                    print(f"\n{Fore.CYAN}Calling Tool: {name} with args: {args}{Style.RESET_ALL}")

                elif event_type == 'tool_result':
                    result = event['result']
                    display_result = result[:200] + "..." if len(result) > 200 else result
                    print(f"{Fore.BLUE}Tool Result: {display_result}{Style.RESET_ALL}")

                elif event_type == 'error':
                    if has_streamed_content:
                        print()
                    print(f"\n{Fore.RED}Error: {event['content']}{Style.RESET_ALL}")
                    return event['content']

                elif event_type == 'answer':
                    final_answer = event['content']

            if has_streamed_content:
                print()
            print(Style.RESET_ALL)
            return final_answer

        except KeyboardInterrupt:
            if has_streamed_content:
                print()
            print(f"\n{Fore.YELLOW}[Interrupted by user]{Style.RESET_ALL}")
            return ""
