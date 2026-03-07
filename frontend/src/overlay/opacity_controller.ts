// Controls the transparency level of the overlay window.
//
// Responsibilities:
// - Read the opacity value from settings_store.ts
// - Apply the opacity value to the Tauri window using the window API
// - Expose setOpacity(value: number) for the settings panel to call
// - Clamp opacity between a minimum visible value and 1.0
// - Persist opacity changes to settings_store.ts
