from unsloth import FastLanguageModel # type: ignore
import os
from typing import TypedDict, List
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, DataCollatorForLanguageModeling, Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType
import torch
from peft import prepare_model_for_kbit_training, LoraConfig, get_peft_model
from datasets import load_dataset # type: ignore
from data_formatter import format_conversations, END_OF_TEXT_TOKEN

torch.backends.cudnn.benchmark = True

# Constants can stay at module level
MODEL_PATH = "./models/Llama-3.2-3B/"


def setup_model_and_tokenizer():
    max_seq_length = 1024

    print("Loading model with Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name = MODEL_PATH,
        max_seq_length = max_seq_length,
        dtype = torch.float16,
        load_in_4bit = True,
        token = None,
        device_map = "auto",
    )

    tokenizer.pad_token = END_OF_TEXT_TOKEN

    # lora_config = LoraConfig(
    #     r = 8,
    #     lora_alpha = 16,
    #     target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    #     lora_dropout = 0.1,
    #     bias = "none",
    #     task_type = TaskType.CAUSAL_LM
    # )

    model = FastLanguageModel.get_peft_model(
        model,
        r = 8,
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha = 16,
        lora_dropout = 0.1,
        bias = "none",
        use_gradient_checkpointing = True,
        random_state = 42,
        use_rslora = False,
        loftq_config = None,
)
    model.print_trainable_parameters()

    return model, tokenizer

def train_model(conversations_jsonl, model, tokenizer):
    dataset = load_dataset("json", data_files=conversations_jsonl, split="train")

    MAX_LENGTH = 512

    def tokenize_fn(ex):
        tokens = tokenizer(
            ex["text"],
            truncation=True,
            max_length=MAX_LENGTH,
            padding="max_length",
        )

        tokens["labels"] = tokens["input_ids"].copy()
        return tokens

    tokenized = dataset.map(
        tokenize_fn,
        batched=True,
        remove_columns=["text"],
        num_proc=1,
    )

    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
        pad_to_multiple_of=8,
    )

    training_args = TrainingArguments(
        output_dir="./lora-finetuned",
        per_device_train_batch_size=16,
        gradient_accumulation_steps=6,
        num_train_epochs=3,
        learning_rate=1e-4,
        # deepspeed="ds_config.json",
        #fp16=True,
        bf16=True,
        logging_steps=10,
        save_steps=200,
        save_total_limit=3,
        optim="adamw_8bit",
        optim_args="offload_optimizer=True,offload_param=True",
        remove_unused_columns=False,
        dataloader_num_workers=0,
        dataloader_pin_memory=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model("./lora-finetuned")

def main():
    conversations_jsonl = format_conversations()
    
    model, tokenizer = setup_model_and_tokenizer()
    
    train_model(conversations_jsonl, model, tokenizer)

if __name__ == '__main__':
    main()
