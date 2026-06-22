using System.Text.Json.Serialization;

namespace Cheatly.Avalonia.Models;

public sealed class TranscriptRequest
{
    [JsonPropertyName("text")]
    public string Text { get; set; } = string.Empty;
}
