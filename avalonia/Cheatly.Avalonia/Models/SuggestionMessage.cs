using System.Text.Json.Serialization;

namespace Cheatly.Avalonia.Models;

public sealed class SuggestionMessage
{
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;

    [JsonPropertyName("payload")]
    public SuggestionPayload? Payload { get; set; }
}

public sealed class SuggestionPayload
{
    [JsonPropertyName("output")]
    public List<string> Output { get; set; } = new();

    [JsonPropertyName("turn_id")]
    public string? TurnId { get; set; }

    [JsonPropertyName("mode")]
    public string? Mode { get; set; }

    [JsonPropertyName("revision")]
    public int? Revision { get; set; }

    public bool IsPrefetch => Mode == "prefetch";
    public bool IsFinal => Mode == "final";
}
