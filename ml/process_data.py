import json
import os
from dataclasses import dataclass
from typing import ClassVar
from __future__ import annotations # I shouldn't need to import this but it's broken otherwise

@dataclass
class User:
    id: str
    name: str | None = None
    
    _next_user_number: ClassVar[int] = 1
    _user_id_map: ClassVar[dict[str, str]] = {}
    
    def __post_init__(self):
        if self.name is None:
            self.create_name()

    def create_name(self):
        if self.id in User._user_id_map:
            self.name = User._user_id_map[self.id]
        else:
            self.name = f"User {User._next_user_number}"
            User._user_id_map[self.id] = self.name
            User._next_user_number += 1
    
    @classmethod
    def reset_user_counter(cls):
        cls._next_user_number = 1
        cls._user_id_map = {}

@dataclass
class Message:
    role: str
    context: str
    content: str

@dataclass
class RawMessage:
    author_id: str
    content: str
    message_id: str
    timestamp: int
    replied_message_id: str | None
    replied_user_id: str | None

    context: MessageContext | None = None
    
    def __post_init__(self):
        self.author = User(self.author_id)
        self.replied_user = User(self.replied_user_id) if self.replied_user_id is not None else None

    def format_message(self) -> Message:
        if self.author.name is None:
            raise Exception("User name is Null")
        
        if self.replied_user is not None and self.replied_message_id is not None:
            context = MessageContext(self.replied_user, None)
        else:
            context = MessageContext(None, None)

        return Message(self.author.name, context.formatted(), self.content)
    
@dataclass
class MessageContext:
    replied_user_id: str | None
    replied_message: RawMessage | None
    id: int = -1

    _next_id: ClassVar[int] = 1
    _id_map: ClassVar[dict[str, int]] = {}

    def __post_init__(self):
        self.replied_username: str = User(self.replied_user_id).name if self.replied_user_id in User._user_id_map else self.replied_user_id
        if self.id == -1:
            self.id = MessageContext._next_id
            MessageContext._next_id += 1

    def formatted(self) -> str:
        string: str = f"Message id {self.id}."
        if self.replied_message is not None and self.replied_username is not None and self.replied_message.context is not None:
            string += f" Replying to message id {self.replied_message.context.id} by {self.replied_username}."
        elif self.replied_message is None and self.replied_username is not None:
            string += f" Replying to an unknown message by {self.replied_username}."

        return string

    @classmethod
    def reset_message_counter(cls):
        cls._next_id = 1

@dataclass
class Prompt:
    instruction: str
    messages: list[Message]

DATA_DIRECTORY: str = "../data/unprocessed/"

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
            with open(file_path, "r") as file:
                data: dict = json.load(file)
                messages.append(data)
                print(f"Loaded {filename}")
        except Exception as e:
            print(f"Error loading {filename}, {type(e).__name__} - {e}")

    return messages

def process_messages_into_conversations(data: list) -> list[Prompt]:
    prompts: list[Prompt] = []

    start_index: int = 0
    current_index: int = -1

    for message in data:
        current_index += 1
        raw_messages: list[RawMessage] = []
        raw_message: RawMessage = dict_to_raw_message(message)

        if str(raw_message.content).strip() == "":
            continue

        if current_index == 0:
            raw_messages.append(raw_message)
            continue
        
        if raw_message.timestamp - raw_messages[current_index - 1].timestamp >= 3600000 or current_index - start_index >= 20: # 1 hour difference
            user: User = raw_messages[current_index - 1].author

            formatted_messages = [msg.format_message() for msg in raw_messages[start_index:current_index - 1]]

            instruction: str

            if current_index > start_index:
                instruction = f"You are {user.name} engaging in a conversation on Discord."
            elif current_index == start_index:
                instruction = f"You are {user.name} starting a conversation on Discord."
            
            prompt = Prompt(instruction, formatted_messages)
            prompts.append(prompt)

            User.reset_user_counter()
            MessageContext.reset_message_counter()
            start_index = current_index

        raw_messages.append(raw_message)
    return prompts

def save_prompts_to_jsonl(prompts: list[Prompt]) -> None:
    output_path = "../data/processed/prompts.jsonl"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as file:
        for prompt in prompts:

            prompt_dict = {
                "instruction": prompt.instruction,
                "messages": [{"role": msg.role, "content": msg.content} for msg in prompt.messages]
            }

            file.write(json.dumps(prompt_dict) + "\n")

    print(f"Saved {len(prompts)} prompts to {output_path}")

def dict_to_raw_message(message: dict) -> RawMessage:
    return RawMessage(
        message["authorId"],
        message["content"], 
        message["id"], 
        message["createdTimestamp"],
        message["reference"]["messageId"] if message["reference"] is not None else None,
        message["mentions"]["repliedUser"]
    )

messages: list = load_message_data(DATA_DIRECTORY)
