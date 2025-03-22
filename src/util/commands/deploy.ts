import { REST, Routes } from "discord.js";
import { config } from "../../config";
import { commands } from "../../commands/export";

const commandsData = Object.values(commands).map((command) => command.data);

const rest = new REST({ version: "10" }).setToken(config.TOKEN);

type DeployCommandsProps = {
    guildId: string;
};

export async function deployCommands({ guildId }: DeployCommandsProps) {
    try {
        console.log("Started refreshing application (/) commands.");

        await rest.put(
            Routes.applicationGuildCommands(config.CLIENT_ID, guildId),
            {
                body: commandsData,
            }
        );

        console.log("Successfully reloaded application (/) commands.");
    } catch (error) {
        console.error(error);
    }
}

export async function deployCommandsAll() {
    try {
        console.log("Started refreshing application (/) commands.");

        await rest.put(
            Routes.applicationCommands(config.CLIENT_ID),
            {
                body: commandsData,
            }
        );

        console.log("Successfully reloaded application (/) commands.");
    } catch (error) {
        console.error(error);
    }
}
