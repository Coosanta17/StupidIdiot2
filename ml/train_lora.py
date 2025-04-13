import pandas as pd # type: ignore
from typing import TypedDict, List
import json

MODEL_DIRECTORY = "./models/Mistral-7B-v0.3/"

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

df = pd.read_json('../data/processed/prompts.jsonl', lines=True)
data = df.to_dict('records')

conversations: List[Conversation] = []

for prompt in data:
    conversation = Conversation()

    for message in prompt["context"]:
        conversation.append(Message(role=message["role"], content=f"{message["context"]}\nMessage content: {message["content"]}"))

    conversation.append(Message(role="system", content=prompt["instruction"]))

    conversation.append(Message(role=f"User {prompt["responseUser"]}", content=prompt["response"]))

    conversations.append(conversation)

for conversation in conversations[0:10]:
    print(json.dumps(conversation.to_chat_format(), indent=2))
    print("-" * 40)
