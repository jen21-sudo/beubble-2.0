import base64
import json
import os
import re
from mimetypes import guess_type
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

class UniversalAgent:

    def __init__(self):
        # Qwen Cloud API Configuration (DashScope)
        api_key = os.getenv("DASHSCOPE_API_KEY")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        
        # Strict assignment according to the real capabilities of your models
        self.default_text_model = "qwen3.7-plus"                 # The strongest in textual logic / JSON
        self.default_cam_model = "qwen3.7-plus"  # Ultra-fast for short queries
        self.default_vision_model = "qwen3.7-plus" # The only one in your list that handles vision

    def _encode_image_to_base64(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"The image cannot be found at the indicated path: {image_path}")

        mime_type, _ = guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        
        return f"data:{mime_type};base64,{encoded_string}"

    def _raw_llm_call(self, prompt: str, model: str = None) -> str:
        target_model = model if model else self.default_text_model
        
        response = self.client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _raw_llm_call_string(self, prompt: str, model: str = None) -> str:
        target_model = model if model else self.default_text_model
        
        response = self.client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content

    def execute_cam_crisis_call(self, prompt: str, model: str = None) -> str:
        """Executes a quick call with Qwen3 Omni Flash Realtime."""
        target_model = model if model else self.default_cam_model
        
        response = self.client.chat.completions.create(
            model=target_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip()

    def execute_vision(self, prompt: str, image_path: str, response_json: bool = False, model: str = None) -> str | dict:
        """Analyzes an image by forcing the Qwen3 Omni model (The only one capable of vision)."""
        # Security: If the user tries to pass a pure text model (14b), we force Omni
        target_model = model if model else self.default_vision_model
        if "14b-instruct" in target_model:
            print("Warning: qwen2.5-14b-instruct does not support vision. Replacing with Qwen3-Omni.")
            target_model = self.default_vision_model

        base64_image = self._encode_image_to_base64(image_path)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image
                        }
                    }
                ]
            }
        ]

        kwargs = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.2
        }

        if response_json:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        raw_text = response.choices[0].message.content.strip()

        if response_json:
            return self._parse_json_safely(raw_text)
        return raw_text

    def _parse_json_safely(self, raw_text: str) -> dict:
        raw_text = re.sub(r"^```json\s*", "", raw_text, flags=re.IGNORECASE)
        raw_text = re.sub(r"^```\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()

        match = re.search(r"(\{.*\})", raw_text, re.DOTALL)
        json_string = match.group(1) if match else raw_text

        try:
            return json.loads(json_string)
        except json.JSONDecodeError:
            try:
                fixed_string = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_string)
                return json.loads(fixed_string)
            except Exception:
                print(f"Critical JSON structure error. Content: {raw_text}")
                return {"error": "Defective JSON formatting", "raw_content": raw_text}

    def execute(self, prompt: str, model: str = None) -> dict:
        raw_text = self._raw_llm_call(prompt, model=model).strip()
        return self._parse_json_safely(raw_text)

    def execute_string(self, prompt: str, model: str = None) -> str:
        return self._raw_llm_call_string(prompt, model=model).strip()

    def execute_markdown(self, prompt: str, model: str = None) -> str:
        raw_text = self._raw_llm_call_string(prompt, model=model).strip()
        raw_text = re.sub(r"```[\s\S]*?```", "", raw_text)
        raw_text = re.sub(r"`([^`]+)`", r"\1", raw_text)
        raw_text = re.sub(r"\*\*([^*]+)\*\*", r"\1", raw_text)
        raw_text = re.sub(r"\*([^*]+)\*", r"\1", raw_text)
        raw_text = re.sub(r"^#+\s+", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"^\s*[-*+]\s+", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"^\s*\d+\.\s+", "", raw_text, flags=re.MULTILINE)
        raw_text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", raw_text)
        return raw_text.strip()


if __name__ == "__main__":
    agent = UniversalAgent()
    print("Text extraction test (Qwen2.5-14b)...")
    test_prompt = 'Return a JSON with the key "status" equal to "ready"'
    print(agent.execute(test_prompt))