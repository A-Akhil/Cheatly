import { transcriptStore } from "../state/transcript_store";

export const transcriptBuffer = {
	push(text: string): void {
		transcriptStore.appendSegment(text);
	},

	clear(): void {
		transcriptStore.clearTranscript();
	}
};
