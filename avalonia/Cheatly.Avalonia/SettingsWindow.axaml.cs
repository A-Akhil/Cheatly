using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;
using Cheatly.Avalonia.Models;
using Cheatly.Avalonia.Services;

namespace Cheatly.Avalonia;

public partial class SettingsWindow : Window
{
    private readonly AppSettings _settings;
    private readonly BackendClient _backendClient;
    private readonly WebSocketSuggestionClient _webSocketClient;
    private readonly CancellationTokenSource _cancellation;
    private readonly ObservableCollection<string> _documents = new();

    private OverlayWindow? _overlayWindow;
    private WindowsSpeechService? _windowsSpeech;
    private LoopbackSpeechService? _loopbackSpeech;
    private bool _isConnected;
    private bool _apiKeyVisible;
    private bool _isApplyingBackendConfig;
    private bool _isConnecting;
    private CancellationTokenSource? _syncDebounce;

    private static readonly Dictionary<string, string[]> ProviderModels = new()
    {
        ["openai"] = new[] { "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo" },
        ["anthropic"] = new[] { "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022" },
        ["gemini"] = new[] { "gemini/gemini-pro", "gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash" },
        ["azure"] = new[] { "azure/gpt-4", "azure/gpt-4-turbo", "azure/gpt-35-turbo" },
        ["custom"] = new[] { "custom-model" }
    };

    public SettingsWindow()
    {
        InitializeComponent();

        _settings = new AppSettings();
        _backendClient = new BackendClient(_settings.BackendBaseUrl);
        _webSocketClient = new WebSocketSuggestionClient(_settings.BackendWebSocketUrl);
        _cancellation = new CancellationTokenSource();

        DocumentsList.ItemsSource = _documents;
        ProviderCombo.SelectedIndex = 0;

        _webSocketClient.FullPayloadReceived += OnFullPayloadReceived;
        _webSocketClient.StatusChanged += OnStatusChanged;
        _webSocketClient.ConnectionStateChanged += OnConnectionStateChanged;
        _webSocketClient.TranscriptReceived += OnTranscriptReceived;

        Closed += OnWindowClosed;

        Loaded += async (_, _) => await AutoConnectAsync();

        _ = RefreshAudioStatusAsync();
        _ = LoadDocuments();
    }

    private void OnProviderChanged(object? sender, SelectionChangedEventArgs e)
    {
        if (_isApplyingBackendConfig)
            return;

        if (ProviderCombo.SelectedItem is ComboBoxItem item && item.Tag is string provider)
        {
            _ = RefreshModelsForProviderAsync(provider, selectedModel: null);

            bool needsApiKey = provider != "ollama";
            ApiKeyInput.IsEnabled = needsApiKey;
            ApiKeyInput.Watermark = needsApiKey ? "Enter your API key..." : "Not required for local models";

            bool showApiBase = provider == "azure" || provider == "custom" || provider == "ollama";
            ApiBasePanel.IsVisible = showApiBase;
            if (provider == "ollama")
            {
                if (string.IsNullOrWhiteSpace(ApiBaseInput.Text))
                {
                    ApiBaseInput.Text = "http://127.0.0.1:11434";
                }
            }

            TriggerSyncIfConnected();
        }
    }

    private void OnAnySelectionChanged(object? sender, SelectionChangedEventArgs e)
    {
        TriggerSyncIfConnected();
    }

    private async void OnApiBaseChanged(object? sender, RoutedEventArgs e)
    {
        if (_isApplyingBackendConfig)
            return;

        if (ProviderCombo.SelectedItem is ComboBoxItem item &&
            string.Equals(item.Tag?.ToString(), "ollama", StringComparison.OrdinalIgnoreCase))
        {
            await RefreshModelsForProviderAsync("ollama", GetSelectedModel());
        }

        TriggerSyncIfConnected();
    }

    private void OnAnyPresetChecked(object? sender, RoutedEventArgs e)
    {
        TriggerSyncIfConnected();
    }

    private void TriggerSyncIfConnected()
    {
        if (!_isConnected || _isApplyingBackendConfig)
            return;

        // Debounce: coalesce rapid-fire ComboBox/RadioButton change events into a single sync
        _syncDebounce?.Cancel();
        _syncDebounce?.Dispose();
        var cts = new CancellationTokenSource();
        _syncDebounce = cts;
        _ = Task.Delay(300, cts.Token).ContinueWith(t =>
        {
            if (!t.IsCanceled)
                Dispatcher.UIThread.Post(() => _ = SyncSettings());
        }, TaskScheduler.Default);
    }

    private void OnToggleKeyVisibility(object? sender, RoutedEventArgs e)
    {
        _apiKeyVisible = !_apiKeyVisible;
        ApiKeyInput.PasswordChar = _apiKeyVisible ? '\0' : '*';
        ShowKeyButton.Content = _apiKeyVisible ? "Hide" : "Show";
    }

    private async Task AutoConnectAsync()
    {
        // Pre-warm the mic in the background while waiting for connection
        _windowsSpeech = new WindowsSpeechService();
        _ = _windowsSpeech.InitializeAsync();

        StatusText.Text = "Waiting for Backend...";
        StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(global::Avalonia.Media.Color.Parse("#FFA500"));
        ConnectButton.IsEnabled = false;

        while (!_cancellation.IsCancellationRequested)
        {
            var isHealthy = await _backendClient.CheckHealthAsync(_cancellation.Token);
            if (isHealthy)
            {
                OnConnectClicked(null, new RoutedEventArgs());
                break;
            }
            try { await Task.Delay(2000, _cancellation.Token); } catch { break; }
        }
    }

    private async void OnConnectClicked(object? sender, RoutedEventArgs e)
    {
        if (_isConnecting)
            return;

        if (_webSocketClient.IsConnected)
        {
            StatusText.Text = "Connected";
            return;
        }

        _isConnecting = true;
        ConnectButton.IsEnabled = false;
        StatusText.Text = "Connecting...";

        try
        {
            var isHealthy = await _backendClient.CheckHealthAsync(_cancellation.Token);
            if (!isHealthy)
            {
                StatusText.Text = "Backend Unreachable";
                StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                    global::Avalonia.Media.Color.Parse("#FF6B6B"));
                return;
            }

            _ = Task.Run(async () => await _webSocketClient.ConnectAndListenAsync(_cancellation.Token));

            await LoadSettingsFromBackend();
            await RefreshAudioStatusAsync();

            _isConnected = true;
            StatusText.Text = "Connected";
            StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                global::Avalonia.Media.Color.Parse("#4CAF50"));

            await SyncSettings();
            await LoadDocuments();
        }
        finally
        {
            _isConnecting = false;
            ConnectButton.IsEnabled = true;
        }
    }

    private async Task RefreshAudioStatusAsync()
    {
        var isHealthy = await _backendClient.CheckHealthAsync(_cancellation.Token);
        if (!isHealthy)
        {
            AudioStatusText.Text = "Backend unreachable";
            AudioStatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                global::Avalonia.Media.Color.Parse("#FF6B6B"));
            return;
        }

        var (micCount, loopbackCount) = await _backendClient.GetAudioDeviceCountsAsync(_cancellation.Token);
        AudioStatusText.Text = $"Microphones: {micCount}, Loopback devices: {loopbackCount}";
        AudioStatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
            global::Avalonia.Media.Color.Parse("#4CAF50"));
    }

    private async void OnStartSessionClicked(object? sender, RoutedEventArgs e)
    {
        if (!_isConnected)
        {
            StatusText.Text = "Connect to backend first";
            return;
        }

        await SyncSettings();

        // Show overlay instantly
        bool enableCaptureExclusion = CaptureExclusionToggle.IsChecked == true;
        _overlayWindow = new OverlayWindow(enableCaptureExclusion);
        _overlayWindow.SessionStopped += OnOverlaySessionStopped;
        _overlayWindow.ForceSendRequested += OnForceSendRequested;
        _overlayWindow.SetConnectionState(true);
        _overlayWindow.Show();
        Hide();

        // ── Start Audio Services in Background ────────────────────────────────────
        _ = Task.Run(async () =>
        {
            CheatlyLog.Info("Starting WindowsSpeechService (mic)...");
            if (_windowsSpeech == null)
            {
                _windowsSpeech = new WindowsSpeechService();
            }
            _windowsSpeech.FragmentReady     += OnSpeechFragment;
            _windowsSpeech.FinalTranscriptReady += OnSpeechFinal;
            _windowsSpeech.ErrorOccurred     += OnSpeechError;
            var micStarted = await _windowsSpeech.StartAsync();
            CheatlyLog.Info($"WindowsSpeechService started={micStarted}");
            if (!micStarted)
            {
                Dispatcher.UIThread.Post(() =>
                {
                    _windowsSpeech = null;
                    StatusText.Text = "Enable Online Speech Recognition in Windows Settings";
                    StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(global::Avalonia.Media.Color.Parse("#FF6B6B"));
                    
                    try
                    {
                        System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                        {
                            FileName = "ms-settings:privacy-speech",
                            UseShellExecute = true
                        });
                    }
                    catch { }
                });
            }

            CheatlyLog.Info("Starting LoopbackSpeechService (system audio)...");
            _loopbackSpeech = new LoopbackSpeechService();
            _loopbackSpeech.FragmentReady       += OnLoopbackFragment;
            _loopbackSpeech.FinalTranscriptReady += OnSpeechFinal;
            _loopbackSpeech.ErrorOccurred       += OnSpeechError;
            var loopStarted = await _loopbackSpeech.StartAsync();
            CheatlyLog.Info($"LoopbackSpeechService started={loopStarted}");
            if (!loopStarted) _loopbackSpeech = null;

            CheatlyLog.Info($"Session started — log file: {CheatlyLog.LogFilePath}");
        });
    }

    private async void OnOverlaySessionStopped()
    {
        // Stop mic STT
        if (_windowsSpeech != null)
        {
            _windowsSpeech.FragmentReady        -= OnSpeechFragment;
            _windowsSpeech.FinalTranscriptReady -= OnSpeechFinal;
            _windowsSpeech.ErrorOccurred        -= OnSpeechError;
            await _windowsSpeech.StopAsync();
            await _windowsSpeech.DisposeAsync();
            _windowsSpeech = null;
        }

        // Stop loopback STT
        if (_loopbackSpeech != null)
        {
            _loopbackSpeech.FragmentReady        -= OnLoopbackFragment;
            _loopbackSpeech.FinalTranscriptReady -= OnSpeechFinal;
            _loopbackSpeech.ErrorOccurred        -= OnSpeechError;
            await _loopbackSpeech.StopAsync();
            await _loopbackSpeech.DisposeAsync();
            _loopbackSpeech = null;
        }

        _overlayWindow = null;
        Dispatcher.UIThread.Post(() => Show());

        // Pre-warm the mic again for the next session
        _windowsSpeech = new WindowsSpeechService();
        _ = _windowsSpeech.InitializeAsync();
    }

    // ── Speech Recognition handlers ───────────────────────────────────────────

    private void OnSpeechFragment(string text)
    {
        CheatlyLog.Info($"[UI] Mic hypothesis -> SetLiveHypothesis: '{text}'");
        Dispatcher.UIThread.Post(() => _overlayWindow?.SetLiveHypothesis(text));
    }

    private void OnLoopbackFragment(string text)
    {
        CheatlyLog.Info($"[UI] Loopback fragment -> SetLiveHypothesis: '{text}'");
        Dispatcher.UIThread.Post(() => _overlayWindow?.SetLiveHypothesis(text));
    }

    private async void OnSpeechFinal(string text)
    {
        // Commit the finalized phrase to the UI transcript permanently
        CheatlyLog.Info($"[UI] Final transcript -> CommitTranscript: '{text}'");
        Dispatcher.UIThread.Post(() => _overlayWindow?.UpdateTranscript(text));

        // After 1.5s silence -> auto-send to LLM pipeline
        await _backendClient.SendTranscriptAsync(text, _cancellation.Token);
    }

    private void OnSpeechError(string error)
    {
        Dispatcher.UIThread.Post(() =>
        {
            StatusText.Text = $"STT: {error}";
            StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                global::Avalonia.Media.Color.Parse("#FFA500"));
        });
    }

    private async void OnForceSendRequested(string text)
    {
        await _backendClient.SendTranscriptAsync(text, _cancellation.Token);
    }

    private void OnFullPayloadReceived(SuggestionPayload payload)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _overlayWindow?.UpdateFromPayload(payload);
        });
    }

    private void OnTranscriptReceived(string text)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _overlayWindow?.UpdateTranscript(text);
        });
    }

    private void OnConnectionStateChanged(bool connected)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _isConnected = connected;
            _overlayWindow?.SetConnectionState(connected);
        });
    }

    private void OnStatusChanged(string status)
    {
        Dispatcher.UIThread.Post(() =>
        {
            if (status.Contains("Disconnected") || status.Contains("Error") || status.Contains("failed"))
            {
                _isConnected = false;
                StatusText.Text = status;
                StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                    global::Avalonia.Media.Color.Parse("#FF6B6B"));
            }
            else if (status.Contains("Connected"))
            {
                _isConnected = true;
                StatusText.Text = status;
                StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                    global::Avalonia.Media.Color.Parse("#4CAF50"));
            }
            else
            {
                StatusText.Text = status;
                StatusText.Foreground = new global::Avalonia.Media.SolidColorBrush(
                    global::Avalonia.Media.Color.Parse("#FFA500"));
            }
        });
    }

    private string GetSelectedModel()
    {
        if (ModelCombo.SelectedItem is ComboBoxItem item)
        {
            return item.Content?.ToString() ?? "";
        }
        return "";
    }

    private string GetSelectedProvider()
    {
        if (ProviderCombo.SelectedItem is ComboBoxItem item && item.Tag is string tag)
        {
            return tag;
        }

        return "openai";
    }

    private string GetSelectedFallbackModel()
    {
        if (FallbackProviderCombo.SelectedItem is ComboBoxItem providerItem && 
            providerItem.Tag?.ToString() == "none")
        {
            return "";
        }
        
        if (FallbackModelCombo.SelectedItem is ComboBoxItem item)
        {
            return item.Content?.ToString() ?? "";
        }
        return "ollama/llama3";
    }

    private async Task SyncSettings()
    {
        var preset = "balanced";
        if (PresetFast.IsChecked == true) preset = "fast";
        else if (PresetAccurate.IsChecked == true) preset = "accurate";

        var provider = GetSelectedProvider();
        var model = GetSelectedModel();
        var fallbackModel = GetSelectedFallbackModel();
        var apiKey = ApiKeyInput.Text ?? "";
        var apiBase = ApiBaseInput.Text ?? "";

        var modelProvider = new Dictionary<string, object>
        {
            ["provider"] = provider,
        };

        if (!string.IsNullOrWhiteSpace(model))
        {
            modelProvider["model"] = model;
        }

        if (!string.IsNullOrEmpty(fallbackModel))
        {
            modelProvider["fallback_model"] = fallbackModel;
        }
        if (!string.IsNullOrEmpty(apiKey))
        {
            modelProvider["api_key"] = apiKey;
        }
        if (!string.IsNullOrEmpty(apiBase))
        {
            modelProvider["api_base"] = apiBase;
        }

        var settings = new Dictionary<string, object>
        {
            ["model_provider"] = modelProvider,
            ["trigger"] = new Dictionary<string, object>
            {
                ["preset"] = preset
            }
        };

        await _backendClient.UpdateSettingsAsync(settings, _cancellation.Token);
    }

    private async Task LoadSettingsFromBackend()
    {
        var json = await _backendClient.GetSettingsJsonAsync(_cancellation.Token);
        if (string.IsNullOrWhiteSpace(json))
            return;

        string selectedProvider = "openai";
        string? selectedModel = null;

        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;

            _isApplyingBackendConfig = true;

            if (root.TryGetProperty("model_provider", out var mp))
            {
                if (mp.TryGetProperty("provider", out var providerEl))
                {
                    selectedProvider = providerEl.GetString() ?? "openai";
                    SelectComboBoxByTag(ProviderCombo, selectedProvider);
                }

                if (mp.TryGetProperty("model", out var modelEl))
                {
                    selectedModel = modelEl.GetString();
                }

                if (mp.TryGetProperty("fallback_model", out var fallbackModelEl))
                {
                    SelectComboBoxByContent(FallbackModelCombo, fallbackModelEl.GetString());
                }

                if (mp.TryGetProperty("api_base", out var apiBaseEl))
                {
                    ApiBaseInput.Text = apiBaseEl.GetString() ?? string.Empty;
                }
            }

            if (root.TryGetProperty("trigger", out var trigger) &&
                trigger.TryGetProperty("preset", out var presetEl))
            {
                var preset = (presetEl.GetString() ?? "balanced").ToLowerInvariant();
                PresetFast.IsChecked = preset == "fast";
                PresetBalanced.IsChecked = preset == "balanced";
                PresetAccurate.IsChecked = preset == "accurate";
            }
        }
        catch
        {
        }
        finally
        {
            // Do NOT reset _isApplyingBackendConfig here -- keep it true
            // until RefreshModelsForProviderAsync completes below, to prevent
            // model ComboBox changes from triggering redundant POST /settings.
        }

        await RefreshModelsForProviderAsync(selectedProvider, selectedModel);
        _isApplyingBackendConfig = false;
    }

    private async Task RefreshModelsForProviderAsync(string provider, string? selectedModel)
    {
        List<string> models;
        if (string.Equals(provider, "ollama", StringComparison.OrdinalIgnoreCase))
        {
            var apiBase = ApiBaseInput.Text?.Trim();
            models = await _backendClient.GetOllamaModelsAsync(apiBase, _cancellation.Token);
            if (models.Count == 0 && !string.IsNullOrWhiteSpace(selectedModel))
            {
                models = new List<string> { selectedModel };
            }
        }
        else if (ProviderModels.TryGetValue(provider, out var staticModels))
        {
            models = new List<string>(staticModels);
        }
        else
        {
            models = new List<string>();
        }

        ApplyModelItems(models, selectedModel);
    }

    private void ApplyModelItems(List<string> models, string? selectedModel)
    {
        ModelCombo.Items.Clear();

        foreach (var model in models)
        {
            ModelCombo.Items.Add(new ComboBoxItem { Content = model });
        }

        if (!string.IsNullOrWhiteSpace(selectedModel) && SelectComboBoxByContent(ModelCombo, selectedModel))
        {
            return;
        }

        if (ModelCombo.Items.Count > 0)
        {
            ModelCombo.SelectedIndex = 0;
        }
    }

    private static bool SelectComboBoxByTag(ComboBox comboBox, string? tag)
    {
        if (string.IsNullOrWhiteSpace(tag))
            return false;

        foreach (var item in comboBox.Items)
        {
            if (item is ComboBoxItem cbItem &&
                string.Equals(cbItem.Tag?.ToString(), tag, StringComparison.OrdinalIgnoreCase))
            {
                comboBox.SelectedItem = cbItem;
                return true;
            }
        }

        return false;
    }

    private static bool SelectComboBoxByContent(ComboBox comboBox, string? content)
    {
        if (string.IsNullOrWhiteSpace(content))
            return false;

        foreach (var item in comboBox.Items)
        {
            if (item is ComboBoxItem cbItem &&
                string.Equals(cbItem.Content?.ToString(), content, StringComparison.OrdinalIgnoreCase))
            {
                comboBox.SelectedItem = cbItem;
                return true;
            }
        }

        return false;
    }

    private async Task LoadDocuments()
    {
        try
        {
            var docs = await _backendClient.GetRagDocumentsAsync(_cancellation.Token);
            Dispatcher.UIThread.Post(() =>
            {
                _documents.Clear();
                foreach (var doc in docs)
                {
                    _documents.Add(doc);
                }
            });
        }
        catch
        {
        }
    }

    private async void OnAddDocumentClicked(object? sender, RoutedEventArgs e)
    {
        var files = await StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = "Select Document",
            AllowMultiple = false,
            FileTypeFilter = new[]
            {
                new FilePickerFileType("Text Files") { Patterns = new[] { "*.txt", "*.md", "*.json" } }
            }
        });

        if (files.Count > 0)
        {
            var file = files[0];
            await using var stream = await file.OpenReadAsync();
            using var reader = new System.IO.StreamReader(stream);
            var text = await reader.ReadToEndAsync();
            var fileName = file.Name;

            await _backendClient.AddRagTextAsync(fileName, text, _cancellation.Token);
            await LoadDocuments();
        }
    }

    private async void OnWindowClosed(object? sender, EventArgs e)
    {
        _webSocketClient.StopReconnecting();
        _cancellation.Cancel();
        await _webSocketClient.DisposeAsync();
    }
}
