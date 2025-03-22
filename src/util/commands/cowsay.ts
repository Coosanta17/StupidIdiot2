import { exec } from "child_process";
import { AutocompleteFocusedOption, AutocompleteInteraction, InteractionReplyOptions } from "discord.js";

export const choices =  [
    "apt", "bud-frogs", "bunny", "calvin", "cheese", "cock", "cow", "cower", "daemon",
    "default", "dragon", "dragon-and-cow", "duck", "elephant", "elephant-in-snake",
    "eyes", "flaming-sheep", "fox", "ghostbusters", "gnu", "hellokitty", "kangaroo",
    "kiss", "koala", "kosh", "luke-koala", "mech-and-cow", "milk", "moofasa", "moose",
    "pony", "pony-smaller", "ren", "sheep", "skeleton", "snowman", "stegosaurus",
    "stimpy", "suse", "three-eyes", "turkey", "turtle", "tux", "unipony", 
    "unipony-smaller", "vader", "vader-koala", "www"
];

export function autocompleteCowType(interaction: AutocompleteInteraction) {
    const focusedValue = interaction.options.getFocused();
    const filtered = choices.filter(choice => choice.startsWith(focusedValue)).slice(0, 25);
    return filtered.map(choice => ({ name: choice, value: choice }));
}

function runCommandWithOutput(command: string): Promise<{content: string | null, status: 'success' | 'error' | 'stderr'}> {
    console.debug(`Executing console command: ${command}`);

    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                console.error(`Error: ${error.message}`);
                reject({ content: null, status: 'error' });
            } else if (stderr) {
                console.error(`Stderr: ${stderr}`);
                reject({ content: null, status: 'stderr' });
            } else {
                resolve({ content: stdout.trim(), status: 'success' });
            }
        });
    });
}

export async function runConsoleCommand(command: string): Promise<InteractionReplyOptions> {
    const result: {content: string | null, status: 'success' | 'error' | 'stderr'} = await runCommandWithOutput(command)

    if (result.status === 'error') {
        return { content: 'There was an error executing the command.', ephemeral: true };
    } else if (result.status === 'stderr') {
        return { content: 'There was an error with the command on the server.', ephemeral: true };
    } else {
        return { content: `\`\`\`\n ${result.content}\n\`\`\``, ephemeral: false };
    }
}