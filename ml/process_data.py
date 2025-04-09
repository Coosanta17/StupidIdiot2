from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import ClassVar

DATA_DIRECTORY = "../data/unprocessed/"
MAX_CONVERSATION_LENGTH = 20
ONE_HOUR = 3600000

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
class MessageContext:
    replied_user_id: str | None
    replied_message_discord_id: str | None
    id: int = -1

    _next_id: ClassVar[int] = 1
    _id_map: ClassVar[dict[str, int]] = {}

    def __post_init__(self):
        self.replied_message_id = None
        self.replied_username = None
        
        if self.replied_user_id is not None:
            if self.replied_user_id in User._user_id_map:
                self.replied_username = User(self.replied_user_id).name
            else:
                self.replied_username = self.replied_user_id

        if self.replied_message_discord_id is not None:
            if self.replied_message_discord_id in MessageContext._id_map:
                self.replied_message_id = MessageContext._id_map[self.replied_message_discord_id]
        
        if self.id == -1:
            self.id = MessageContext._next_id
            MessageContext._next_id += 1
            
            if self.replied_message_discord_id is not None:
                MessageContext._id_map[self.replied_message_discord_id] = self.id

    def formatted(self) -> str:
        string: str = f"Message id {self.id}."
        if self.replied_message_id is not None and self.replied_username is not None:
            string += f" Replying to message id {self.replied_message_id} by {self.replied_username}."
        elif self.replied_message_id is None and self.replied_username is not None:
            string += f" Replying to an unknown message by {self.replied_username}."

        return string

    @classmethod
    def reset_message_counter(cls):
        cls._next_id = 1
        cls._id_map = {}
        print("reset message counter")

@dataclass
class RawMessage:
    author_id: str
    content: str
    message_id: str
    timestamp: int
    replied_message_id: str | None
    replied_user_id: str | None

    context: MessageContext = field(default_factory=lambda: MessageContext(None, None))
    
    def __post_init__(self):
        self.author = User(self.author_id)
        self.replied_user = User(self.replied_user_id) if self.replied_user_id is not None else None

    def format_message(self) -> Message:
        if self.author.name is None:
            raise Exception("User name is Null")
    
        if self.replied_user is not None or self.replied_message_id is not None:
            context = MessageContext(self.replied_user.id if self.replied_user is not None else None, self.replied_message_id)
        else: 
            context = MessageContext(None, None)
        return Message(self.author.name, context.formatted(), self.content)
    
@dataclass
class Prompt:
    instruction: str
    messages: list[Message]

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
            
        User.reset_user_counter()
        MessageContext.reset_message_counter()

        # Full conversation prompt
        if conversation_length != 1:
            formatted_full_messages = [msg.format_message() for msg in raw_messages[start_index:end_index]]
            user = raw_messages[end_index - 1].author
            
            instruction = f"You are {user.name} engaging in a conversation on Discord."
            prompts.append(Prompt(instruction, formatted_full_messages))
        
        User.reset_user_counter()
        MessageContext.reset_message_counter()
        
        # First message only (conversation starter)
        first_message = [raw_messages[start_index].format_message()]
        first_instruction = f"You are {raw_messages[start_index].author.name} starting a conversation on Discord."
        prompts.append(Prompt(first_instruction, first_message))
        
        User.reset_user_counter()
        MessageContext.reset_message_counter()

        # Half conversation
        if conversation_length > 10:
            half_length = conversation_length // 2
            half_end_index = start_index + half_length
            formatted_half_messages = [msg.format_message() for msg in raw_messages[start_index:half_end_index]]
            half_user = raw_messages[half_end_index - 1].author
            half_instruction = f"You are {half_user.name} engaging in a conversation on Discord."
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

            prompt_dict = {
                "instruction": prompt.instruction,
                "messages": [{"role": msg.role, "context": msg.context, "content": msg.content} for msg in prompt.messages]
            }

            file.write(json.dumps(prompt_dict) + "\n")

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
