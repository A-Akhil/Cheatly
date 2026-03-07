// HTTP client for making REST API calls to the backend.
//
// Responsibilities:
// - Provide typed wrappers around fetch for each backend REST endpoint
// - Implement getSettings(), postSettings(data), getModels(), postSessionReset()
// - Handle HTTP errors and return structured error objects to callers
// - Read the backend base URL from runtime configuration
// - Used by settings_panel.tsx and any component needing non-streaming data
