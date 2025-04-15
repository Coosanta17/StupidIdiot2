import pandas as pd # type: ignore
import json
from typing import TypedDict, List

END_OF_TEXT_TOKEN = "<|end_of_text|>"

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

def format_conversations():
    print("Formatting data to conversation")
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
    return conversations_jsonl

if __name__ == '__main__':
    format_conversations()
