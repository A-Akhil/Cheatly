import React from "react";
import { useSuggestionStore } from "../state/suggestion_store";
import { SuggestionRenderer } from "./suggestion_renderer";

export function SuggestionPanel(): JSX.Element {
	const { suggestions, loading } = useSuggestionStore();

	return (
		<section>
			<h3 style={{ margin: "0 0 8px 0", fontSize: 14 }}>Output</h3>
			{loading ? <div style={{ fontSize: 12 }}>Generating...</div> : null}
			<ul style={{ margin: 0, paddingLeft: 20, fontSize: 13 }}>
				{suggestions.length === 0 && !loading ? <li>No output yet.</li> : null}
				{suggestions.map((item, index) => (
					<SuggestionRenderer key={`${index}-${item}`} text={item} />
				))}
			</ul>
		</section>
	);
}
