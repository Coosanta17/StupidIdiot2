import { SlashCommandBuilder, EmbedBuilder, CommandInteraction } from "discord.js";

import { choices } from "../../util/commands/cowsay";

export default {
    data: new SlashCommandBuilder()
        .setName("cowlist")
        .setDescription("Shows the available cowsay types."),
    async execute(interaction: CommandInteraction) {
        const randomChoice = choices[Math.floor(Math.random() * choices.length)];
        const response = new EmbedBuilder()
            .setColor(0x969696)
            .setTitle("Available Cow Types:")
            .setDescription(choices.join(", "))
            .addFields(
                { name: "Example usage", value: `\`/cowsay 'Hello world!' ${randomChoice}\`` },
            );

        interaction.reply({ embeds: [response] })
    }
}