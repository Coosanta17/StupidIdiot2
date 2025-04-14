import os
import pandas as pd # type: ignore
from typing import TypedDict, List
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import get_peft_model, LoraConfig, TaskType
import torch

os.environ["CUDA_VISIBLE_DEVICES"] = "0" 

MODEL_PATH = "./models/Mistral-7B-v0.3/"

class Message(TypedDict):
    role: str
    content: str

class Conversation:
    messages: List[Message]

    def __init__(self):
        self.messages = []

    def append(self, message: Message):
        self.messages.append(message)

    def to_chat_format(self) -> List[dict]:
        return [dict(message) for message in self.messages]
    
    def to_prompt_format(self) -> str:
        if not self.messages:
            print("Error: Empty conversation.")
            return ""
        
        context_messages = self.messages[:-1]
        response_message = self.messages[-1]
        
        result = "### Context:\n"
        for msg in context_messages:
            prefix = f"{msg['role']}: "
            result += f"{prefix}{msg['content']}\n"
        
        result += "\n### Response:\n"
        result += response_message["content"]
        
        return result

df = pd.read_json('../data/processed/prompts.jsonl', lines=True)
data = df.to_dict('records')

conversations: List[Conversation] = []

for prompt in data:
    conversation = Conversation()

    for message in prompt["context"]:
        role = message["role"]
        content = message["content"]
        message_id_info = message["context"]
        
        formatted_content = f"{message_id_info}\n{content}\n"
        conversation.append(Message(role=role, content=formatted_content))

    conversation.append(Message(role="system", content=prompt["instruction"]))

    conversation.append(Message(role=f"User {prompt['responseUser']}", content=prompt["response"]))

    conversations.append(conversation)

# Debug
for conversation in conversations[0:10]:
    print(conversation.to_prompt_format())
    print("-" * 40)


tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

try:
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=quantization_config,
        device_map="auto",
        trust_remote_code=True
    )
except RuntimeError:
    print("GPU quantization not available.")
    user_input = input("Do you want to fall back to CPU mode? (y/n): ").strip().lower()
    if user_input == 'y':
        print("Falling back to CPU mode...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="auto",
            trust_remote_code=True
        )
    else:
        print("Operation cancelled.")
        exit()

lora_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
