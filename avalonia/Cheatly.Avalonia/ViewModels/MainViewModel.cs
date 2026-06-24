using System.Collections.ObjectModel;
using Cheatly.Avalonia.Models;
using Cheatly.Avalonia.Services;

namespace Cheatly.Avalonia.ViewModels;

public sealed class MainViewModel : IAsyncDisposable
{
    private readonly AppSettings _settings;
    private readonly BackendClient _backendClient;
    private readonly WebSocketSuggestionClient _webSocketClient;
    private readonly CancellationTokenSource _cancellation;
    private readonly SynchronizationContext? _uiContext;

    public ObservableCollection<string> TranscriptItems { get; } = new();
    public ObservableCollection<string> OutputItems { get; } = new();

    public event Action<string>? BackendStatusChanged;

    public string BackendStatus { get; private set; } = "Disconnected";

    public MainViewModel()
    {
        _uiContext = SynchronizationContext.Current;
        _settings = new AppSettings();
        _backendClient = new BackendClient(_settings.BackendBaseUrl);
        _webSocketClient = new WebSocketSuggestionClient(_settings.BackendWebSocketUrl);
        _webSocketClient.SuggestionsReceived += OnSuggestionsReceived;
        _webSocketClient.StatusChanged += OnStatusChanged;
        _cancellation = new CancellationTokenSource();
    }

    public async Task AutoConnectAsync()
    {
        SetStatus("Waiting for Backend...");
        while (!_cancellation.IsCancellationRequested)
        {
            var isHealthy = await _backendClient.CheckHealthAsync(_cancellation.Token);
            if (isHealthy)
            {
                _ = Task.Run(async () => await _webSocketClient.ConnectAndListenAsync(_cancellation.Token));
                SetStatus("Connected");
                break;
            }
            SetStatus("Waiting for Backend...");
            try { await Task.Delay(2000, _cancellation.Token); } catch { break; }
        }
    }

    public async Task ConnectAsync()
    {
        var isHealthy = await _backendClient.CheckHealthAsync(_cancellation.Token);
        if (!isHealthy)
        {
            SetStatus("Backend Unreachable");
            return;
        }

        _ = Task.Run(async () => await _webSocketClient.ConnectAndListenAsync(_cancellation.Token));
        SetStatus("Connected");
    }

    public async Task SendTranscriptAsync(string text)
    {
        RunOnUiThread(() => TranscriptItems.Add(text));
        var ok = await _backendClient.SendTranscriptAsync(text, _cancellation.Token);
        if (!ok)
        {
            RunOnUiThread(() => OutputItems.Add("Failed to send transcript to backend"));
        }
    }

    public async Task StartTranscriptionAsync()
    {
        var ok = await _backendClient.StartTranscriptionAsync(_cancellation.Token);
        SetStatus(ok ? "Transcription Running" : "Failed to start transcription");
    }

    public async Task StopTranscriptionAsync()
    {
        var ok = await _backendClient.StopTranscriptionAsync(_cancellation.Token);
        SetStatus(ok ? "Connected" : "Failed to stop transcription");
    }

    public async Task ResetSessionAsync()
    {
        var ok = await _backendClient.ResetSessionAsync(_cancellation.Token);
        if (ok)
        {
            RunOnUiThread(() =>
            {
                TranscriptItems.Clear();
                OutputItems.Clear();
            });
            SetStatus("Session Reset");
            return;
        }

        SetStatus("Failed to reset session");
    }

    private void OnSuggestionsReceived(List<string> suggestions)
    {
        RunOnUiThread(() =>
        {
            OutputItems.Clear();
            foreach (var item in suggestions)
            {
                OutputItems.Add(item);
            }
        });
    }

    private void OnStatusChanged(string status)
    {
        SetStatus(status);
    }

    private void SetStatus(string status)
    {
        BackendStatus = status;
        BackendStatusChanged?.Invoke(status);
    }

    private void RunOnUiThread(Action action)
    {
        if (_uiContext is null)
        {
            action();
            return;
        }

        _uiContext.Post(_ => action(), null);
    }

    public async ValueTask DisposeAsync()
    {
        _cancellation.Cancel();
        await _webSocketClient.DisposeAsync();
        _cancellation.Dispose();
    }
}
