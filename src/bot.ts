import { Client, ActivityType, Interaction, ChatInputCommandInteraction, AutocompleteInteraction } from "discord.js";
import "dotenv/config";

import { deployCommands, deployCommandsAll } from "./util/commands/deploy";
import { config } from "./config";
import { commands } from "./commands/export";

// temporary
deployCommandsAll();

const client = new Client({
    intents: ["Guilds", "GuildMessages", "DirectMessages"],
});

client.on("ready", () => {
    if (!client.user) throw "What the fuck just happened!? (Client user is null)";
    client.user.setActivity("Cow Simulator", { type: ActivityType.Playing });
    console.log(`Logged in as \"${client.user.tag}\"`);
});

client.on("guildCreate", async (guild) => {
    await deployCommands({ guildId: guild.id });
});

client.on("interactionCreate", async (interaction) => {
    // "Why the nesting?" you might ask. Well, typescript panics when I un-nest this.
    if ((interaction.isChatInputCommand() || interaction.isAutocomplete()) && interaction.commandName in commands) {
        const command = commands[interaction.commandName as keyof typeof commands];

        if (!command) return;

        if (interaction.isAutocomplete()) {
            if ("autocomplete" in command && typeof command.autocomplete === "function") {
                try {
                    await command.autocomplete(interaction);
                } catch (error) {
                    console.error(error);
                }
            }
        } else if (interaction.isChatInputCommand()) {
            try {
                await command.execute(interaction);
            } catch (error) {
                console.error(error);
                const errorMessage = error instanceof Error 
                    ? `Error: ${error.message}` 
                    : "An unexpected error occurred!";
                    
                if (interaction.replied || interaction.deferred) {
                    await interaction.followUp({ 
                        content: `There was an error while executing this command!\n${errorMessage}`, 
                        ephemeral: true 
                    });
                } else {
                    await interaction.reply({ 
                        content: `There was an error while executing this command!\n${errorMessage}`, 
                        ephemeral: true 
                    });
                }
            }
        }
    }
});

client.login(config.TOKEN);
