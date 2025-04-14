import os
import pandas as pd # type: ignore
from typing import TypedDict, List
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import get_peft_model, LoraConfig, TaskType
import torch
from accelerate import infer_auto_device_map, init_empty_weights # type: ignore

os.environ["CUDA_VISIBLE_DEVICES"] = "0" 
MODEL_PATH = "./models/Mistral-7B-v0.3/"
QUANTIZE = False

with init_empty_weights():
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, trust_remote_code=True)

device_map = infer_auto_device_map(model, max_memory={0: "4GiB", "cpu": "14GiB"})

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

# # Debug
# for conversation in conversations[0:10]:
#     print(conversation.to_prompt_format())
#     print("-" * 40)


tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)

if torch.cuda.is_available():
    print(f"CUDA available: {torch.cuda.get_device_name(0)}")
    print(f"CUDA version: {torch.version.cuda}")
    
    try:
        print("Attempting 4-bit quantization...")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )
        
        print("Loading model...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            quantization_config=quantization_config,
            torch_dtype=torch.float16,
            device_map=device_map,
            trust_remote_code=True
        )
        print("Successfully loaded model with 4-bit quantization")
    except Exception as e:
        print(f"4-bit quantization failed: {e}")
        
        try:
            print("Attempting half precision (no quantization)...")
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_PATH,
                torch_dtype=torch.float16,
                device_map=device_map,
                trust_remote_code=True
            )
            print("Successfully loaded model in half precision")
        except Exception as e2:
            print(f"Half precision failed: {e2}")
            
            user_input = input("Do you want to fall back to CPU mode? (y/n): ").strip().lower()
            if user_input == 'y':
                print("Falling back to CPU mode...")
                model = AutoModelForCausalLM.from_pretrained(
                    MODEL_PATH,
                    device_map="cpu",
                    trust_remote_code=True
                )
                print("Model loaded on CPU (this will be slow)")
            else:
                print("Operation cancelled.")
                exit()
else:
    print("No CUDA device found.")
    user_input = input("Do you want to use CPU mode? (y/n): ").strip().lower()
    if user_input == 'y':
        print("Using CPU mode (this will be slow)...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="cpu",
            trust_remote_code=True
        )
    else:
        print("Operation cancelled.")
        exit()

lora_config = LoraConfig(
    r=8,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
