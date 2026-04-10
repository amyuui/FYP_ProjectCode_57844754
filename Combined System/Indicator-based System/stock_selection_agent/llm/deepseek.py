from openai import OpenAI
from stock_selection_agent.config import Config

class _LLMObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def _to_jsonable(self, value):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, list):
            return [self._to_jsonable(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_jsonable(item) for key, item in value.items()}
        return value

    def model_dump(self):
        return {key: self._to_jsonable(value) for key, value in self.__dict__.items()}

    def to_dict(self):
        return self.model_dump()

class DeepSeekClient:
    def __init__(self):
        Config.validate()
        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL
        )
        self.model = Config.DEEPSEEK_MODEL

    def _serialize_message(self, msg):
        if isinstance(msg, dict):
            return msg
        if hasattr(msg, 'model_dump'):
            try:
                return msg.model_dump()
            except:
                return msg
        if hasattr(msg, 'to_dict'):
            return msg.to_dict()
        return msg

    def chat(self, messages, tools=None, tool_choice=None, stream=False):
        sanitized_messages = [self._serialize_message(msg) for msg in messages]

        params = {
            "model": self.model,
            "messages": sanitized_messages,
            "stream": stream
        }
        
        if tools:
            params["tools"] = tools
        if tool_choice:
            params["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**params)
        if stream:
            return self._handle_stream(response)
        return response.choices[0].message

    def _handle_stream(self, response_stream):
        collected_content = []
        collected_tool_calls = {}

        for chunk in response_stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if delta.content:
                content_chunk = delta.content
                collected_content.append(content_chunk)
                yield {"type": "content", "content": content_chunk}

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    index = tc.index

                    yield {
                        "type": "tool_call_chunk",
                        "index": index,
                        "id": tc.id if tc.id else None,
                        "name": tc.function.name if tc.function and tc.function.name else None,
                        "arguments": tc.function.arguments if tc.function and tc.function.arguments else None
                    }

                    if index not in collected_tool_calls:
                        collected_tool_calls[index] = {"id": "", "name": "", "arguments": ""}

                    if tc.id:
                        collected_tool_calls[index]["id"] += tc.id
                    if tc.function:
                        if tc.function.name:
                            collected_tool_calls[index]["name"] += tc.function.name
                        if tc.function.arguments:
                            collected_tool_calls[index]["arguments"] += tc.function.arguments

        final_content = "".join(collected_content) if collected_content else None

        final_tool_calls = []
        if collected_tool_calls:
            sorted_indices = sorted(collected_tool_calls.keys())
            for index in sorted_indices:
                tc_data = collected_tool_calls[index]
                final_tool_calls.append(
                    _LLMObject(
                        id=tc_data["id"],
                        type="function",
                        function=_LLMObject(
                            name=tc_data["name"],
                            arguments=tc_data["arguments"]
                        )
                    )
                )
        
        final_message = _LLMObject(
            role="assistant",
            content=final_content,
            tool_calls=final_tool_calls if final_tool_calls else None
        )

        yield {"type": "response", "response": final_message}
