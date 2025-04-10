from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import ClassVar

DATA_DIRECTORY = "../data/unprocessed/"
MAX_CONVERSATION_LENGTH = 20
ONE_HOUR = 3600000

@dataclass
class Message:
    role: str
    context: str
    content: str

@dataclass
class MessageContext:
    replied_user: str | None
    replied_message_id: int | None
    id: int = -1

    def format(self) -> str:
        string = f"Message id {self.id}."
        if self.replied_user is not None:
            if self.replied_message_id is not None:
                string += f" Replying to message id {self.replied_message_id} by {self.replied_user}."
            else:
                string += f" Replying to an unknown message by {self.replied_user}."

        return string

@dataclass
class RawMessage:
    author_id: str
    content: str
    message_id: str
    timestamp: int
    replied_message_id: str | None
    replied_user_id: str | None

    author: str | None = None
    context: MessageContext = field(default_factory=lambda: MessageContext(None, None))

    def format(self) -> str:
        return Message(self.author if self.author is not None else self.author_id, self.context.format(), self.content).__str__()
    
@dataclass
class Prompt:
    instruction: str
    messages: list[RawMessage]
    
    _next_user_number: int = 1
    _user_id_map: dict[str, str] = field(default_factory=dict)

    _next_message_id: int = 1
    _message_id_map: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        for message in self.messages:
            if message.author is not None:
                print("error: iterating over messages that have already been processed")
                continue

            # Set author username
            if message.author_id in self._user_id_map:
                message.author = self._user_id_map[message.author_id]
            else:
                message.author = f"User {self._next_user_number}"
                self._next_message_id += 1
                self._user_id_map[message.author_id] = message.author

            # Set message context
            message.context.id = self._next_message_id
            self._next_message_id += 1
            self._message_id_map[message.message_id] = message.context.id

            # Set replied message ids in context
            if message.replied_message_id is not None:
                if message.replied_message_id in self._message_id_map:
                    message.context.replied_message_id = self._message_id_map[message.replied_message_id]

                if message.replied_user_id in self._user_id_map:
                    message.context.replied_user = self._user_id_map[message.replied_user_id]

    def format(self):
        formatted_messages: list[str] = []
        for raw_message in self.messages:
            formatted_messages.append(raw_message.format())

        return {
            "instruction": self.instruction,
            "messages": formatted_messages
        }



def load_message_data(directory_path) -> list[dict[str, str]]:
    messages: list = []

    if not os.path.exists(directory_path):
        print(f"Directory \'{directory_path}\' not found.")
        return messages
    
    for filename in os.listdir(directory_path):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(directory_path, filename)
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data: dict = json.load(file)
                if isinstance(data, list):
                    messages.extend(data)
                    print(f"Loaded {filename} with {len(data)} messages")
        except Exception as e:
            print(f"Error loading {filename}, {type(e).__name__} - {e}")

    return messages

def process_messages_into_conversations(data: list) -> list[Prompt]:
    prompts: list[Prompt] = []
    raw_messages: list[RawMessage] = []
    start_index: int = 0

    def process_conversation_segment(start_index: int, end_index: int):
        conversation_length = end_index - start_index
        
        if conversation_length <= 0:
            return

        # Full conversation prompt
        if conversation_length != 1:
            formatted_full_messages = [msg for msg in raw_messages[start_index:end_index]]
            user = raw_messages[end_index - 1].author
            
            instruction = f"You are {user} engaging in a conversation on Discord."
            prompts.append(Prompt(instruction, formatted_full_messages))
        
        # First message only (conversation starter)
        first_message = [raw_messages[start_index]]
        first_instruction = f"You are {raw_messages[start_index].author} starting a conversation on Discord."
        prompts.append(Prompt(first_instruction, first_message))

        # Half conversation
        if conversation_length > 10:
            half_length = conversation_length // 2
            half_end_index = start_index + half_length
            formatted_half_messages = [msg for msg in raw_messages[start_index:half_end_index]]
            half_user = raw_messages[half_end_index - 1].author
            half_instruction = f"You are {half_user} engaging in a conversation on Discord."
            prompts.append(Prompt(half_instruction, formatted_half_messages))

    total_length = len(data)

    for i, message in enumerate(data):
        raw_message = dict_to_raw_message(message)
        
        if str(raw_message.content).strip() == "":
            continue
            
        raw_messages.append(raw_message)
        
        if len(raw_messages) > 1 and (
            raw_message.timestamp - raw_messages[-2].timestamp >= ONE_HOUR or 
            len(raw_messages) - start_index > MAX_CONVERSATION_LENGTH
        ):

            process_conversation_segment(start_index, len(raw_messages) - 1)
            
            start_index = len(raw_messages) - 1
        
        # Debug
        print(f"Processed {i+1} messages out of {total_length}")
    
    # Process the final conversation
    if len(raw_messages) > start_index:
        process_conversation_segment(start_index, len(raw_messages))
        
    return prompts

#TODO: fix message and user ids - this is from the saving stuff
def save_prompts_to_jsonl(prompts: list[Prompt]) -> None:
    output_path = "../data/processed/prompts.jsonl"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as file:
        for prompt in prompts:
            prompt_string = prompt.format()
            file.write(json.dumps(prompt_string) + "\n")
            pass

    print(f"Saved {len(prompts)} prompts to {output_path}")

def dict_to_raw_message(message: dict) -> RawMessage:
    required_fields = ["authorId", "content", "id", "createdTimestamp"]
    for field in required_fields:
        if field not in message:
            raise ValueError(f"Missing required field: {field}")
    
    replied_message_id = None
    if message.get("reference") is not None:
        replied_message_id = message["reference"].get("messageId")
    
    replied_user_id = None
    if message.get("mentions") is not None:
        replied_user_id = message["mentions"].get("repliedUser")
    
    return RawMessage(
        message["authorId"],
        message["content"], 
        message["id"], 
        message["createdTimestamp"],
        replied_message_id,
        replied_user_id
    )

def main():
    messages = load_message_data(DATA_DIRECTORY)
    if not messages:
        print("No messages found to process.")
        return
        
    prompts = process_messages_into_conversations(messages)
    save_prompts_to_jsonl(prompts)
    print(f"Processing complete: {len(prompts)} prompts generated.")

if __name__ == "__main__":
    main()
