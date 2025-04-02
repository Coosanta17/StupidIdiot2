import fetchAll from "discord-fetch-all/src/functions/fetchMessages";
import { Message, Guild, GuildChannel, TextChannel } from "discord.js";
import * as fs from 'fs';

import { client } from "./bot";

export async function downloadAllMessages() {
    console.log("Starting download of messages from all guilds...");
    
    const guilds = Array.from(client.guilds.cache.keys());
    console.log(`Found ${guilds.length} guilds to process`);
    
    try {
        await Promise.all(
            guilds.map(guildId => downloadGuildMessages(guildId))
        );
        console.log("Successfully downloaded messages from all guilds");
    } catch (error) {
        console.error("Error downloading messages from guilds:", error);
    }
}

export async function downloadGuildMessages(guildId: string) {
    console.log(`downloading messages of guild ${guildId}`);
    const guild: Guild | undefined = client.guilds.cache.get(guildId);

    if (!guild) {
        console.error(`Guild with ID ${guildId} not found.`);
        return;
    }

    const channels: GuildChannel[] = Array.from(guild.channels.cache.values());
    const textChannels = channels.filter(channel => channel instanceof TextChannel);
    
    try {
        await Promise.all(textChannels.map(async (channel) => {
            if (channel instanceof TextChannel) {
                const messages = await downloadChannelMessages(channel);
                await storeChannelMessages(messages, guild.name, channel.name);
            }
        }));
        console.log(`Successfully downloaded all messages from guild ${guildId}`);
    } catch (error) {
        console.error(`Error downloading messages from guild ${guildId}:`, error);
    }
}

async function downloadChannelMessages(channel: TextChannel): Promise<Message[]> {
    return await fetchAll(channel, {
        reverseArray: true,
        userOnly: true,
        botOnly: false,
        pinnedOnly: false,
    });
}

async function storeChannelMessages(messages: Message[], guild: string, channel: string): Promise<void> {
    const guildMessageFolder = `./data/${guild}/messages/`;
    const filePath = `${guildMessageFolder}/${channel}.json`;
    
    try {
        await fs.promises.mkdir(guildMessageFolder, { recursive: true });
        await fs.promises.writeFile(filePath, JSON.stringify(messages, null, 2));
        console.log(`Successfully stored messages for channel ${channel}`);
    } catch (error) {
        console.error(`Failed to store messages for channel ${channel}:`, error);
        throw error;
    }
}
