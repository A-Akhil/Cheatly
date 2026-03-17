import React from "react";

type Props = {
	text: string;
};

export function SuggestionRenderer({ text }: Props): JSX.Element {
	return React.createElement(
		"li",
		{
			style: {
				marginBottom: 8,
				lineHeight: 1.4,
				cursor: "pointer"
			},
			onClick: () => navigator.clipboard?.writeText(text),
			title: "Click to copy"
		},
		text
	);
}
