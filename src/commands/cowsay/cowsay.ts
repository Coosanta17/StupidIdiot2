import { AutocompleteInteraction, ChatInputApplicationCommandData, ChatInputCommandInteraction, CommandInteraction, SlashCommandBuilder } from "discord.js";

import { autocompleteCowType, runConsoleCommand } from "../../util/commands/cowsay";

export default {
    data: new SlashCommandBuilder()
        .setName('cowsay')
        .setDescription("Shows the available commands.")

        .addStringOption(option =>
            option
                .setName('content')
                .setDescription("What the cow will say.")
                .setRequired(true)
                .setMaxLength(1_000))

        .addStringOption(option =>
            option
                .setName('cow_type')
                .setDescription("The type of cow to use. (use `/cowlist` to see all options)")
                .setRequired(false)
                .setAutocomplete(true)),

    async autocomplete(interaction: AutocompleteInteraction) {
        await interaction.respond(
            autocompleteCowType(interaction),
        );
    },
    async execute(interaction: ChatInputCommandInteraction) {

        const content: string | null = interaction.options.getString('content');
        const cowType: string = interaction.options.getString('cow_type') || "default";

        const command = (cowType === "default" || cowType === "cow") ? `cowsay "${content}"` : `cowsay -f ${cowType} "${content}"`;
        
        const replyMessage = await runConsoleCommand(command);
        await interaction.reply(replyMessage);
    },
}
