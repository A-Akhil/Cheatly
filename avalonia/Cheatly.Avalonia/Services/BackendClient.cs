using System.Net.Http.Json;
using System.Text.Json;
using Cheatly.Avalonia.Models;

namespace Cheatly.Avalonia.Services;

public sealed class BackendClient
{
    private readonly HttpClient _http;

    public BackendClient(string baseUrl)
    {
        _http = new HttpClient
        {
            BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/")
        };
    }

    public async Task<bool> CheckHealthAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _http.GetAsync("health", cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<ModelInfo?> GetModelsAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync("models", cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            return null;
        }

        var json = await response.Content.ReadAsStringAsync(cancellationToken);
        using var doc = JsonDocument.Parse(json);
        var root = doc.RootElement;

        return new ModelInfo
        {
            Provider = root.TryGetProperty("provider", out var p) ? p.GetString() ?? "" : "",
            Model = root.TryGetProperty("model", out var m) ? m.GetString() ?? "" : "",
            FallbackModel = root.TryGetProperty("fallback_model", out var f) ? f.GetString() ?? "" : "",
        };
    }

    public async Task<string?> GetSettingsJsonAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _http.GetAsync("settings", cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return null;
            }

            return await response.Content.ReadAsStringAsync(cancellationToken);
        }
        catch
        {
            return null;
        }
    }

    public async Task<List<string>> GetOllamaModelsAsync(string? apiBase = null, CancellationToken cancellationToken = default)
    {
        try
        {
            var path = "providers/ollama/models";
            if (!string.IsNullOrWhiteSpace(apiBase))
            {
                path += $"?api_base={Uri.EscapeDataString(apiBase)}";
            }

            using var response = await _http.GetAsync(path, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return new List<string>();
            }

            var json = await response.Content.ReadAsStringAsync(cancellationToken);
            using var doc = JsonDocument.Parse(json);

            var models = new List<string>();
            if (doc.RootElement.TryGetProperty("models", out var modelsArray))
            {
                foreach (var item in modelsArray.EnumerateArray())
                {
                    var model = item.GetString();
                    if (!string.IsNullOrWhiteSpace(model))
                    {
                        models.Add(model);
                    }
                }
            }

            return models;
        }
        catch
        {
            return new List<string>();
        }
    }

    public async Task<bool> SendTranscriptAsync(string text, CancellationToken cancellationToken = default)
    {
        CheatlyLog.Info($"[BackendClient] POST /transcript/ingest -> Sending final transcript to backend: '{text}'");
        var payload = new TranscriptRequest { Text = text };
        using var response = await _http.PostAsJsonAsync("transcript/ingest", payload, cancellationToken);
        if (response.IsSuccessStatusCode)
            CheatlyLog.Info($"[BackendClient] POST /transcript/ingest -> Success");
        else
            CheatlyLog.Error($"[BackendClient] POST /transcript/ingest -> Failed with status {response.StatusCode}");
            
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> StartTranscriptionAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.PostAsync("transcription/start", content: null, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> StopTranscriptionAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.PostAsync("transcription/stop", content: null, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> ResetSessionAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.PostAsync("session/reset", content: null, cancellationToken);
        return response.IsSuccessStatusCode;
    }

    public async Task<bool> UpdateSettingsAsync(Dictionary<string, object> settings, CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _http.PostAsJsonAsync("settings", settings, cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<List<string>> GetRagDocumentsAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _http.GetAsync("rag/documents", cancellationToken);
            if (!response.IsSuccessStatusCode)
                return new List<string>();

            var json = await response.Content.ReadAsStringAsync(cancellationToken);
            using var doc = JsonDocument.Parse(json);

            var documents = new List<string>();
            if (doc.RootElement.TryGetProperty("documents", out var docsArray))
            {
                foreach (var item in docsArray.EnumerateArray())
                {
                    if (item.TryGetProperty("source_name", out var name))
                    {
                        documents.Add(name.GetString() ?? "Unknown");
                    }
                }
            }
            return documents;
        }
        catch
        {
            return new List<string>();
        }
    }

    public async Task<bool> AddRagTextAsync(string sourceName, string text, CancellationToken cancellationToken = default)
    {
        try
        {
            var payload = new { source_name = sourceName, text = text };
            using var response = await _http.PostAsJsonAsync("rag/documents/text", payload, cancellationToken);
            return response.IsSuccessStatusCode;
        }
        catch
        {
            return false;
        }
    }

    public async Task<(int MicCount, int LoopbackCount)> GetAudioDeviceCountsAsync(CancellationToken cancellationToken = default)
    {
        try
        {
            using var response = await _http.GetAsync("audio/devices", cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                return (0, 0);
            }

            var json = await response.Content.ReadAsStringAsync(cancellationToken);
            using var doc = JsonDocument.Parse(json);

            int micCount = 0;
            int loopbackCount = 0;

            if (doc.RootElement.TryGetProperty("microphones", out var micArray) && micArray.ValueKind == JsonValueKind.Array)
            {
                micCount = micArray.GetArrayLength();
            }

            if (doc.RootElement.TryGetProperty("loopback", out var loopbackArray) && loopbackArray.ValueKind == JsonValueKind.Array)
            {
                loopbackCount = loopbackArray.GetArrayLength();
            }

            return (micCount, loopbackCount);
        }
        catch
        {
            return (0, 0);
        }
    }
}
