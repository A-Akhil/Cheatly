using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using Cheatly.Avalonia.Models;

namespace Cheatly.Avalonia.Services;

public sealed class WebSocketSuggestionClient : IAsyncDisposable
{
    private readonly string _wsUrl;
    private ClientWebSocket? _socket;
    private CancellationTokenSource? _reconnectCts;
    private bool _disposed;
    private bool _shouldReconnect = true;
    private bool _connectLoopRunning;

    private const int MaxReconnectAttempts = 10;
    private const int BaseReconnectDelayMs = 1000;
    private const int MaxReconnectDelayMs = 30000;
    private const int HeartbeatIntervalMs = 30000;

    public event Action<List<string>>? SuggestionsReceived;
    public event Action<SuggestionPayload>? FullPayloadReceived;
    public event Action<string>? StatusChanged;
    public event Action<bool>? ConnectionStateChanged;
    public event Action<string>? TranscriptReceived;

    public bool IsConnected => _socket?.State == WebSocketState.Open;

    public WebSocketSuggestionClient(string wsUrl)
    {
        _wsUrl = wsUrl;
    }

    public async Task ConnectAndListenAsync(CancellationToken cancellationToken)
    {
        if (_connectLoopRunning)
            return;

        _connectLoopRunning = true;
        _reconnectCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        _shouldReconnect = true;
        try
        {
            await ConnectWithRetryAsync(_reconnectCts.Token);
        }
        finally
        {
            _connectLoopRunning = false;
        }
    }

    private async Task ConnectWithRetryAsync(CancellationToken cancellationToken)
    {
        int attempt = 0;

        while (!cancellationToken.IsCancellationRequested && _shouldReconnect)
        {
            try
            {
                _socket?.Dispose();
                _socket = new ClientWebSocket();

                StatusChanged?.Invoke($"Connecting... (attempt {attempt + 1})");
                await _socket.ConnectAsync(new Uri(_wsUrl), cancellationToken);

                StatusChanged?.Invoke("Connected");
                ConnectionStateChanged?.Invoke(true);
                attempt = 0;

                _ = Task.Run(() => HeartbeatLoopAsync(cancellationToken), cancellationToken);
                await ReceiveLoopAsync(cancellationToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (Exception ex)
            {
                attempt++;
                ConnectionStateChanged?.Invoke(false);

                if (attempt >= MaxReconnectAttempts)
                {
                    StatusChanged?.Invoke($"Connection failed after {MaxReconnectAttempts} attempts");
                    break;
                }

                int delay = Math.Min(BaseReconnectDelayMs * (1 << attempt), MaxReconnectDelayMs);
                StatusChanged?.Invoke($"Reconnecting in {delay / 1000}s... ({ex.Message})");

                try
                {
                    await Task.Delay(delay, cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    break;
                }
            }
        }

        StatusChanged?.Invoke("Disconnected");
        ConnectionStateChanged?.Invoke(false);
    }

    private async Task ReceiveLoopAsync(CancellationToken cancellationToken)
    {
        var buffer = new byte[16 * 1024];
        var messageBuffer = new List<byte>();

        while (!cancellationToken.IsCancellationRequested && _socket?.State == WebSocketState.Open)
        {
            try
            {
                var result = await _socket.ReceiveAsync(buffer, cancellationToken);

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    StatusChanged?.Invoke("Server closed connection");
                    return;
                }

                messageBuffer.AddRange(buffer.Take(result.Count));

                if (result.EndOfMessage)
                {
                    var message = Encoding.UTF8.GetString(messageBuffer.ToArray());
                    messageBuffer.Clear();
                    ProcessMessage(message);
                }
            }
            catch (WebSocketException)
            {
                return;
            }
            catch (OperationCanceledException)
            {
                return;
            }
        }
    }

    private void ProcessMessage(string message)
    {
        try
        {
            using var doc = JsonDocument.Parse(message);
            var root = doc.RootElement;

            if (!root.TryGetProperty("type", out var typeElement))
                return;

            var msgType = typeElement.GetString();

            if (msgType == "pong")
                return;

            if (msgType == "transcript" && root.TryGetProperty("payload", out var transcriptPayload))
            {
                if (transcriptPayload.TryGetProperty("text", out var textEl))
                {
                    var text = textEl.GetString();
                    if (!string.IsNullOrWhiteSpace(text))
                        TranscriptReceived?.Invoke(text);
                }
                return;
            }

            if (msgType == "suggestions" && root.TryGetProperty("payload", out var payloadElement))
            {
                var payload = new SuggestionPayload
                {
                    Output = new List<string>()
                };

                if (payloadElement.TryGetProperty("output", out var outputArray))
                {
                    foreach (var item in outputArray.EnumerateArray())
                    {
                        var text = item.GetString();
                        if (text != null)
                            payload.Output.Add(text);
                    }
                }

                if (payloadElement.TryGetProperty("turn_id", out var turnId))
                    payload.TurnId = turnId.GetString();

                if (payloadElement.TryGetProperty("mode", out var mode))
                    payload.Mode = mode.GetString();

                if (payloadElement.TryGetProperty("revision", out var rev))
                    payload.Revision = rev.GetInt32();

                CheatlyLog.Info($"[WebSocket] Received {payload.Output.Count} suggestions for TurnID='{payload.TurnId}' Mode='{payload.Mode}'");

                FullPayloadReceived?.Invoke(payload);
                SuggestionsReceived?.Invoke(payload.Output);
            }
        }
        catch
        {
        }
    }

    private async Task HeartbeatLoopAsync(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested && _socket?.State == WebSocketState.Open)
        {
            try
            {
                await Task.Delay(HeartbeatIntervalMs, cancellationToken);

                if (_socket?.State == WebSocketState.Open)
                {
                    var pingMessage = Encoding.UTF8.GetBytes("{\"type\":\"ping\"}");
                    await _socket.SendAsync(pingMessage, WebSocketMessageType.Text, true, cancellationToken);
                }
            }
            catch
            {
                break;
            }
        }
    }

    public async Task SendAsync(string message, CancellationToken cancellationToken = default)
    {
        if (_socket?.State != WebSocketState.Open)
            return;

        var bytes = Encoding.UTF8.GetBytes(message);
        await _socket.SendAsync(bytes, WebSocketMessageType.Text, true, cancellationToken);
    }

    public void StopReconnecting()
    {
        _shouldReconnect = false;
        _reconnectCts?.Cancel();
    }

    public async ValueTask DisposeAsync()
    {
        if (_disposed)
            return;

        _disposed = true;
        _shouldReconnect = false;
        _reconnectCts?.Cancel();

        if (_socket?.State == WebSocketState.Open)
        {
            try
            {
                await _socket.CloseAsync(
                    WebSocketCloseStatus.NormalClosure,
                    "Closing",
                    CancellationToken.None
                );
            }
            catch
            {
            }
        }

        _socket?.Dispose();
        _reconnectCts?.Dispose();
    }
}
