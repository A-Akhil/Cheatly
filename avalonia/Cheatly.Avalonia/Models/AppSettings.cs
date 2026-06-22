namespace Cheatly.Avalonia.Models;

public sealed class AppSettings
{
    public string BackendBaseUrl { get; set; } = "http://127.0.0.1:8765";
    public string BackendWebSocketUrl { get; set; } = "ws://127.0.0.1:8765/ws/suggestions";
}
