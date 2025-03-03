import json
import time
import torch
import google.generativeai as genai
from openai import OpenAI
from pydantic import BaseModel
from typing import Optional, List
from transformers import AutoTokenizer, PreTrainedTokenizer
from fire import Fire


class DummyImport:
    LLM = None
    SamplingParams = None


try:
    import vllm
    from vllm.lora.request import LoRARequest
except ImportError:
    print("vLLM not installed")
    vllm = DummyImport()
    LoRARequest = lambda *args: args


class EvalModel(BaseModel, arbitrary_types_allowed=True):
    path_model: str
    temperature: float = 0.0

    def run(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIModel(EvalModel):
    path_model: str = "openai_key.json"
    engine: str = "o1-preview"
    timeout: int = 1200
    client: Optional[OpenAI] = None

    def load(self):
        with open(self.path_model) as f:
            info = json.load(f)
            self.client = OpenAI(api_key=info["api_key"], timeout=self.timeout)

    def make_messages(self, prompt: str) -> List[dict]:
        return [{"role": "user", "content": prompt}]

    def run(self, prompt: str) -> str:
        self.load()

        while True:
            try:
                response = self.client.chat.completions.create(
                    model=self.engine,
                    messages=self.make_messages(prompt),
                )
                output = response.choices[0].message.content
                break
            except Exception as e:
                print(e)
                time.sleep(5)
                continue
        return output


class OpenAIGPT4Model(OpenAIModel):
    engine: str = "gpt-4o"


class OpenAIGPT3Model(OpenAIModel):
    engine: str = "gpt-3.5-turbo"


class GeminiFlashThinkingModel(EvalModel):
    path_model: str = "gemini_key.json"
    engine: str = "gemini-2.0-flash-thinking-exp-01-21"
    timeout: int = 600
    model: Optional[genai.GenerativeModel] = None

    def load(self):
        with open(self.path_model) as f:
            info = json.load(f)
            api_key = info["api_key"]
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(self.engine)

    def run(self, prompt: str) -> str:
        self.load()

        while True:
            try:
                response = self.model.generate_content(prompt)
                break
            except Exception as e:
                print(e)
                time.sleep(5)
                continue
        
        try:
            output = response.text
        except Exception as e:
            output = ""

        return output


class GeminiFlashModel(GeminiFlashThinkingModel):
    engine: str = "gemini-2.0-flash-exp"


class VLLMModel(EvalModel):
    path_lora: str = ""
    model: vllm.LLM = None
    quantization: Optional[str] = None
    tokenizer: Optional[PreTrainedTokenizer] = None
    tensor_parallel_size: Optional[int] = None
    max_output_length: int = 512
    stopping_words: Optional[List[str]] = None

    def load(self):
        if self.model is None:
            available_gpus = torch.cuda.device_count()
            if available_gpus == 0:
                raise EnvironmentError("No GPUs detected.")

            if self.tensor_parallel_size is None:
                self.tensor_parallel_size = available_gpus
                print(f"tensor_parallel_size not set. Using all available GPUs: {self.tensor_parallel_size}")
            else:
                if self.tensor_parallel_size > available_gpus:
                    raise ValueError(
                        f"tensor_parallel_size ({self.tensor_parallel_size}) exceeds the number of available GPUs ({available_gpus})."
                    )
                print(f"Using tensor_parallel_size: {self.tensor_parallel_size} out of {available_gpus} available GPUs.")

            self.model = vllm.LLM(
                model=self.path_model,
                trust_remote_code=True,
                quantization=self.quantization,
                enable_lora=self.path_lora != "",
                tensor_parallel_size=self.tensor_parallel_size,
            )

        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(self.path_model)

    def format_prompt(self, prompt: str) -> str:
        self.load()
        prompt = prompt.rstrip(" ")
        return prompt

    def make_kwargs(self, do_sample: bool, **kwargs) -> dict:
        if self.stopping_words:
            kwargs.update(stop=self.stopping_words)
        params = vllm.SamplingParams(
            temperature=0.5 if do_sample else 0.0,
            max_tokens=self.max_output_length,
            **kwargs
        )
        outputs = dict(sampling_params=params, use_tqdm=False)
        if self.path_lora:
            outputs.update(lora_request=LoRARequest("lora", 1, self.path_lora))
        return outputs

    def run(self, prompt: str) -> str:
        prompt = self.format_prompt(prompt)
        outputs = self.model.generate([prompt], **self.make_kwargs(do_sample=False))
        pred = outputs[0].outputs[0].text
        pred = pred.split("<|endoftext|>")[0]
        return pred


def select_model(model_name: str, **kwargs) -> EvalModel:
    model_map = dict(
        o1=OpenAIModel,
        gpt_4o=OpenAIGPT4Model,
        gpt_35_turbo=OpenAIGPT3Model,
        gemini_flash=GeminiFlashModel,
        gemini_flash_thinking=GeminiFlashThinkingModel,
        qwen=VLLMModel,
    )
    model_class = model_map.get(model_name)
    if model_class is None:
        raise ValueError(f"{model_name}. Choose from {list(model_map.keys())}")
    return model_class(**kwargs)


def test_model(
    prompt: str = "What are the rules for Sudoku?",
    model_name: str = "gemini_flash_thinking",
    **kwargs,
):
    model = select_model(model_name, **kwargs)
    print(locals())
    print(model.run(prompt))


if __name__ == "__main__":
    Fire()