import * as fs from 'fs';
import * as path from 'path';

const DATA_DIRECTORY = "./data/unprocessed/";
const MAX_CONVERSATION_LENGTH = 20;
const ONE_HOUR = 3600000;

class Message {
    private role: string;
    private context: string;
    private content: string;

    public constructor(role: string, context: string, content: string) {
        this.role = role;
        this.context = context;
        this.content = content;
    }

    public toJSON() {
        return {
            role: this.role,
            context: this.context,
            content: this.content
        };
    }
}

class User {
    private id: string;
    private name: string | undefined;

    public constructor(id: string) {
        this.id = id;
    }

    setName(name: string): void {
        if (this.name) return;
        this.name = name;
    }

    getName(): string | undefined {
        return this.name;
    }
}

class RawMessage {
    private readonly authorId: string
    private readonly content: string
    private readonly discordMessageId: string
    private readonly timeStamp: number
    private repliedMessageId?: string
    private repliedUserId?: string
    private context: MessageContext | undefined

    public constructor(authorId: string, content: string, discordMessageId: string, timeStamp: number, repliedUserId?: string, repliedMessageId?: string) {
        this.authorId = authorId;
        this.content = content;
        this.discordMessageId = discordMessageId;
        this.timeStamp = timeStamp;
        this.repliedUserId = repliedUserId;
        this.repliedMessageId = repliedMessageId;
    }

    public getAuthorId(): string {
        return this.authorId;
    }

    public getContent(): string {
        return this.content;
    }

    public getDiscordMessageId(): string {
        return this.discordMessageId;
    }

    public getTimeStamp(): number {
        return this.timeStamp;
    }

    public getRepliedMessageId(): string | undefined {
        return this.repliedMessageId;
    }

    public setRepliedMessageId(repliedMessageId: string): void {
        this.repliedMessageId = repliedMessageId;
    }

    public getRepliedUserId(): string | undefined {
        return this.repliedUserId;
    }

    public setRepliedUserId(repliedUserId: string): void {
        this.repliedUserId = repliedUserId;
    }

    public getContext(): MessageContext | undefined {
        return this.context;
    }

    public setContext(context: MessageContext): void {
        // Defensive copy - not an inefficiency
        this.context = new MessageContext(
            context.getId(),
            context.getRepliedMessageId(),
            context.getRepliedUser()
        );
    }
}

class MessageContext {
    private readonly id: number;
    private readonly repliedMessageId?: number;
    private readonly repliedUserId?: number;

    public constructor(id: number, repliedMessageId?: number, repliedUserId?: number) {
        this.id = id;
        this.repliedMessageId = repliedMessageId;
        this.repliedUserId = repliedUserId;
    }

    public toString(): string {
        let string: string = "";
        string += `Message ID ${this.id}.`;

        if (this.repliedMessageId || this.repliedUserId) {
            string += `\nReplying to`;

            if (this.repliedMessageId) {
                string += ` message ID ${this.repliedMessageId}`;
            } else {
                string += " an unknown message";
            }

            string += " by";

            if (this.repliedUserId) {
                string += ` ${toUsername(this.repliedUserId)}`;
            } else {
                string += " an unknown user";
            }
        }

        return string;
    }

    public getId(): number {
        return this.id;
    }

    public getRepliedMessageId(): number | undefined {
        return this.repliedMessageId;
    }

    public getRepliedUser(): number | undefined {
        return this.repliedUserId;
    }
}

class Prompt {
    private instruction: string;
    private readonly messages: ReadonlyArray<RawMessage>;

    private nextUserNumber: number = 1;
    private userIdMap: Map<string, number> = new Map<string, number>();

    private nextMessageNumber: number = 1;
    private messageIdMap: Map<string, number> = new Map<string, number>();

    public constructor(messages: Array<RawMessage>) {
        this.messages = [...messages];

        let userId: number;
        this.messages.forEach((message) => {
            if (this.userIdMap.has(message.getAuthorId())) {
                userId = this.userIdMap.get(message.getAuthorId())!;
            } else {
                userId = this.newUserId();
                this.userIdMap.set(message.getAuthorId(), userId);
            }

            if (!message.getContext()) {
                this.initialiseMessageContext(message);
            }
        });

        const lastMessageUsername = toUsername(this.userIdMap.get(messages.at(-1)!.getAuthorId())!);
        let instructionBuilder = `You are ${lastMessageUsername} `;
        if (messages.length === 1) {
            instructionBuilder += "starting";
        } else {
            instructionBuilder += "engaging in";
        }
        instructionBuilder += " a conversation on Discord";

        this.instruction = instructionBuilder;
    }

    public toString(): string {
        const historyRawMessages = this.messages.slice(0, -1);
        const historyMessages = new Array<Message>();
        historyRawMessages.forEach((message) => {
            let formattedContext: string;
            let formattedUsername: string;

            if (message.getContext()) {
                formattedContext = message.getContext()!.toString();
            } else {
                throw new Error(`Context for message undefined!`);
            }

            if (this.userIdMap.has(message.getAuthorId())) {
                formattedUsername = toUsername(this.userIdMap.get(message.getAuthorId())!);
            } else {
                throw new Error(`User ID ${message.getAuthorId()} not found in userIdMap`);
            }

            historyMessages.push(new Message(formattedUsername, formattedContext, message.getContent()));
        });

        const object = {
            instruction: this.instruction,
            context: historyMessages,
            response: this.messages.at(-1)!.getContent(),
            responseUser: this.userIdMap.get(this.messages.at(-1)!.getAuthorId())
        };

        return JSON.stringify(object);
    }

    private initialiseMessageContext(message: RawMessage) {
        const newId = this.newMessageId();

        this.messageIdMap.set(message.getDiscordMessageId(), newId);
        
        if (message.getRepliedUserId() && message.getRepliedMessageId()) {
            if (this.userIdMap.has(message.getRepliedUserId()!) && this.messageIdMap.has(message.getRepliedMessageId()!)) {
                message.setContext(new MessageContext(
                    newId,
                    this.messageIdMap.get(message.getRepliedMessageId()!)!,
                    this.userIdMap.get(message.getRepliedUserId()!)!
                ));
            } else if (this.userIdMap.has(message.getRepliedUserId()!)) {
                message.setContext(new MessageContext(
                    newId,
                    undefined,
                    this.userIdMap.get(message.getRepliedUserId()!)!
                ));
            } else {
                // console.warn("Reply message outside of scope found");
                message.setContext(new MessageContext(newId, undefined, undefined));
            }
        } else {
            message.setContext(new MessageContext(newId, undefined, undefined));
        }
    }

    private newMessageId(): number {
        return this.nextMessageNumber++;
    }

    private newUserId(): number {
        return this.nextUserNumber++;
    }
}

function toUsername(id: number): string {
    return `User ${id}`;
}

function loadMessageData(directoryPath: string): Array<RawMessage> {
    const messages: Array<RawMessage> = [];

    if (!fs.existsSync(directoryPath)) {
        console.log(`Directory '${directoryPath}' not found.`);
        return messages;
    }

    const files = fs.readdirSync(directoryPath);
    for (const filename of files) {
        if (!filename.endsWith('.json')) {
            continue;
        }

        const filePath = path.join(directoryPath, filename);

        try {
            const fileContent = fs.readFileSync(filePath, 'utf-8');
            const data = JSON.parse(fileContent);

            if (Array.isArray(data)) {
                const validMessages = data
                    .filter(msg => msg.content && !msg.system)
                    .map(msg => new RawMessage(
                        String(msg.authorId),
                        msg.content,
                        msg.id,
                        msg.createdTimestamp,
                        msg.mentions?.repliedUser || undefined,
                        msg.reference?.messageId || undefined
                    ));

                messages.push(...validMessages);
                console.log(`Loaded ${filename} with ${validMessages.length} valid messages`);
            }
        } catch (e) {
            console.log(`Error loading ${filename}, ${e instanceof Error ? e.name : 'Unknown'} - ${e instanceof Error ? e.message : e}`);
        }
    }

    return messages;
}

function generatePrompts(messages: RawMessage[]): Prompt[] {
    let startIndex = 0;
    let tempConversation: Array<RawMessage> = [];
    const prompts = new Array<Prompt>();

    for (let index = 0; index < messages.length; index++) {
        tempConversation.push(messages[index]);
        const conversationLength = index - startIndex;

        if (index === startIndex) {
            prompts.push(new Prompt(tempConversation));
            continue;
        }

        if (messages[index].getTimeStamp() - messages[index - 1].getTimeStamp() > ONE_HOUR) {
            addHalfPrompt(conversationLength);
            pushPrompt();
            continue;
        }

        if (conversationLength >= MAX_CONVERSATION_LENGTH) {
            addHalfPrompt(conversationLength);
            pushPrompt();
            continue;
        }

        function pushPrompt() {
            prompts.push(new Prompt(tempConversation));
            tempConversation = [];
            startIndex = index + 1;
        }
    }

    function addHalfPrompt(conversationLength: number) {
        if (conversationLength > 10) {
            const halfLength = Math.round(conversationLength / 2);
            const halfEndIndex = startIndex + halfLength;
            const halfMessages = messages.slice(startIndex, halfEndIndex);
            prompts.push(new Prompt(halfMessages));
        }
    }

    return prompts;
}

function savePromptsToJsonl(prompts: Prompt[]) {
    const outputDir = './data/processed';
    const outputFile = path.join(outputDir, 'prompts.jsonl');

    if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
    }

    let outputContent = '';
    prompts.forEach(prompt => {
        outputContent += prompt.toString() + '\n';
    });

    fs.writeFileSync(outputFile, outputContent);
    console.log(`Saved ${prompts.length} prompts to ${outputFile}`);
}

function main() {
    savePromptsToJsonl(generatePrompts(loadMessageData(DATA_DIRECTORY)));
}

main();
