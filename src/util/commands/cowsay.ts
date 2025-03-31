import { exec, ExecException } from "child_process";
import { AutocompleteFocusedOption, AutocompleteInteraction, InteractionReplyOptions } from "discord.js";

export const choices = [
    "apt", "bud-frogs", "bunny", "calvin", "cheese", "cock", "cow", "cower", "daemon",
    "default", "dragon", "dragon-and-cow", "duck", "elephant", "elephant-in-snake",
    "eyes", "flaming-sheep", "fox", "ghostbusters", "gnu", "hellokitty", "kangaroo",
    "kiss", "koala", "kosh", "luke-koala", "mech-and-cow", "milk", "moofasa", "moose",
    "pony", "pony-smaller", "random", "ren", "sheep", "skeleton", "snowman", "stegosaurus",
    "stimpy", "suse", "three-eyes", "turkey", "turtle", "tux", "unipony",
    "unipony-smaller", "vader", "vader-koala", "www"
];

export function autocompleteCowType(interaction: AutocompleteInteraction) {
    const focusedValue = interaction.options.getFocused();
    const filtered = choices.filter(choice => choice.startsWith(focusedValue)).slice(0, 25);
    return filtered.map(choice => ({ name: choice, value: choice }));
}

function runCommandWithOutput(command: string): Promise<{ content: string | null, status: 'success' | 'error' | 'stderr' }> {
    console.debug(`Executing console command: ${command}`);

    return new Promise((resolve) => {
        exec(command, (error: ExecException | null, stdout: string, stderr: string) => {
            if (error) {
                console.error(`Error: ${error.message}`);
                resolve({ content: error.message, status: 'error' });
            } else if (stderr) {
                console.error(`Stderr: ${stderr}`);
                resolve({ content: stderr, status: 'stderr' });
            } else {
                resolve({ content: stdout.trim(), status: 'success' });
            }
        });
    });
}

export async function runConsoleCommand(command: string): Promise<InteractionReplyOptions> {
    const result: { content: string | null, status: 'success' | 'error' | 'stderr' } = await runCommandWithOutput(command)

    // TODO: ephemeral deprecated - use tags
    if (result.status === 'error') {
        return { content: `There was an error executing the command. ${result.content}`, ephemeral: true };
    } else if (result.status === 'stderr') {
        return { content: `There was an error with the command on the server. ${result.content}`, ephemeral: true };
    } else {
        return { content: `\`\`\`\n ${result.content}\n\`\`\``, ephemeral: false };
    }
}

export function buildCowsayCommand(cowType: string, content?: string): string {
    if (cowType === "default" || cowType === "cow") {
        return content ? `cowsay "${content}"` : `fortune | cowsay`;
    } else if (cowType === "random") {
        let randomType: string;
        do {
            randomType = choices[Math.floor(Math.random() * choices.length)];
        } while (randomType === "random");

        return content
            ? `cowsay -f ${randomType} "${content}"`
            : `fortune | cowsay -f ${randomType}`;
    } else {
        return content
            ? `cowsay -f ${cowType} "${content}"`
            : `fortune | cowsay -f ${cowType}`;
    }
}