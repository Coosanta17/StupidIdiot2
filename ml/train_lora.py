import os
import pandas as pd # type: ignore
from typing import TypedDict, List
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, DataCollatorForLanguageModeling, Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType
import torch
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model
from datasets import load_dataset # type: ignore

os.environ["CUDA_VISIBLE_DEVICES"] = "0" 

MODEL_PATH = "./models/Llama-3.2-3B/"
END_OF_TEXT_TOKEN = "<|end_of_text|>"

# with init_empty_weights():
#     model = AutoModelForCausalLM.from_pretrained(MODEL_PATH, trust_remote_code=True)

# device_map = infer_auto_device_map(model, max_memory={0: "4GiB", "cpu": "14GiB"})

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
        result += END_OF_TEXT_TOKEN
        
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

conversations_jsonl = './conversations_prompt_format.jsonl'

with open(conversations_jsonl, 'w', encoding='utf-8') as f:
    for conversation in conversations:
        json_obj = {"text": conversation.to_prompt_format()}
        f.write(json.dumps(json_obj) + '\n')

print(f"Wrote {len(conversations)} conversations to {conversations_jsonl}")

if torch.cuda.is_available():
    print(f"CUDA available: {torch.cuda.get_device_name(0)}")
    print(f"CUDA version: {torch.version.cuda}")
    
    print("Attempting 4-bit quantization...")
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        llm_int8_enable_fp32_cpu_offload=True
    )
    
    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=quantization_config,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )
    print("Successfully loaded model with 4-bit quantization")
else:
    user_input = input("CUDA is not available. Do you want to load on CPU? (Y/N): ")
    if user_input.strip().lower() == "y":
        print("Loading model on CPU (this might be slow)...")
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            device_map="cpu",
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )

        print("Model loaded on CPU")
    else:
        print("Cancelled")
        exit()

model = prepare_model_for_kbit_training(model)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
tokenizer.pad_token = END_OF_TEXT_TOKEN 

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_dropout=0.1,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

dataset = load_dataset("json", data_files=conversations_jsonl, split="train")

MAX_LENGTH = 1024

def tokenize_fn(ex):
    tokens = tokenizer(
        ex["text"],
        truncation=True,
        max_length=MAX_LENGTH,
        padding="max_length",
    )
    # For causal LM, labels = input_ids
    tokens["labels"] = tokens["input_ids"].copy()
    return tokens

tokenized = dataset.map(
    tokenize_fn,
    batched=True,
    remove_columns=["text"],
    num_proc=4,
)

data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False,
    pad_to_multiple_of=8,
)

training_args = TrainingArguments(
    output_dir="./lora-finetuned",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=8,
    num_train_epochs=6,
    learning_rate=1e-4,
    fp16=True,
    logging_steps=50,
    save_steps=200,
    save_total_limit=3,
    remove_unused_columns=False,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    data_collator=data_collator,
)

trainer.train()
trainer.save_model("./lora-finetuned")
