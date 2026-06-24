using System.Text;
using Windows.Media.SpeechRecognition;

namespace Cheatly.Avalonia.Services;

/// <summary>
/// Wraps Windows.Media.SpeechRecognition for real-time mic transcription.
/// ~200ms latency. Replaces Whisper for microphone input.
/// </summary>
public sealed class WindowsSpeechService : IAsyncDisposable
{
    private SpeechRecognizer? _recognizer;
    private CancellationTokenSource? _silenceCts;
    private readonly StringBuilder _accumulated = new();
    private readonly object _lock = new();
    private string? _lastResultText;

    private const int SilenceThresholdMs = 1500;

    public event Action<string>? FragmentReady;
    public event Action<string>? FinalTranscriptReady;
    public event Action<string>? ErrorOccurred;

    public bool IsRunning { get; private set; }

    /// <summary>
    /// Checks if Windows Online Speech Recognition is enabled and we have mic permissions.
    /// If not, automatically opens the correct Windows Settings page.
    /// </summary>
    public static async Task<bool> CheckPermissionsAsync()
    {
        try
        {
            using var recognizer = new SpeechRecognizer();
            var result = await recognizer.CompileConstraintsAsync().AsTask();
            return result.Status == SpeechRecognitionResultStatus.Success;
        }
        catch (Exception ex)
        {
            if (ex.HResult == unchecked((int)0x80045509) || ex.HResult == unchecked((int)0x80045508))
            {
                try
                {
                    System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo
                    {
                        FileName = "ms-settings:privacy-speech",
                        UseShellExecute = true
                    });
                }
                catch { /* Ignore if ms-settings fails to launch */ }
            }
            return false;
        }
    }

    public async Task<bool> StartAsync()
    {
        CheatlyLog.Info("StartAsync called");
        if (IsRunning) { CheatlyLog.Warn("Already running"); return true; }

        try
        {
            // Try en-US, fall back to system language
            SpeechRecognizer recognizer;
            try
            {
                var enUS = new Windows.Globalization.Language("en-US");
                recognizer = new SpeechRecognizer(enUS);
                CheatlyLog.Info("SpeechRecognizer created with en-US");
            }
            catch (Exception ex)
            {
                CheatlyLog.Warn($"en-US failed ({ex.Message}), using system default");
                recognizer = new SpeechRecognizer();
            }

            _recognizer = recognizer;

            // Force the OS to finalize phrases quickly when the user pauses
            _recognizer.Timeouts.EndSilenceTimeout = TimeSpan.FromMilliseconds(500);

            CheatlyLog.Info("Compiling constraints (free dictation)...");
            var compileResult = await _recognizer.CompileConstraintsAsync().AsTask();
            CheatlyLog.Info($"CompileConstraints status = {compileResult.Status}");

            if (compileResult.Status != SpeechRecognitionResultStatus.Success)
            {
                var msg = $"Grammar compilation failed: {compileResult.Status}";
                CheatlyLog.Error(msg);
                ErrorOccurred?.Invoke(msg);
                _recognizer.Dispose();
                _recognizer = null;
                return false;
            }

            _recognizer.StateChanged += (s, e) => CheatlyLog.Info($"Windows Mic State: {e.State}");
            _recognizer.HypothesisGenerated += OnHypothesisGenerated;
            _recognizer.ContinuousRecognitionSession.ResultGenerated += OnResultGenerated;
            _recognizer.ContinuousRecognitionSession.Completed += OnSessionCompleted;

            CheatlyLog.Info("Starting continuous recognition session...");
            await _recognizer.ContinuousRecognitionSession.StartAsync().AsTask();

            IsRunning = true;
            CheatlyLog.Info("Windows STT is RUNNING — listening for mic speech");
            return true;
        }
        catch (Exception ex)
        {
            var hint = ex.HResult == unchecked((int)0x80045509)
                ? " → Go to Windows Settings → Privacy → Speech → enable Online Speech Recognition"
                : ex.HResult == unchecked((int)0x80045508)
                ? " → Microphone permission denied. Check Settings → Privacy → Microphone"
                : string.Empty;

            CheatlyLog.Error(ex, $"StartAsync failed{hint}");
            var msg = $"Windows STT failed (0x{ex.HResult:X8}): {ex.Message}{hint}";
            ErrorOccurred?.Invoke(msg);
            _recognizer?.Dispose();
            _recognizer = null;
            return false;
        }
    }

    private void OnResultGenerated(
        SpeechContinuousRecognitionSession session,
        SpeechContinuousRecognitionResultGeneratedEventArgs args)
    {
        var result = args.Result;
        CheatlyLog.Info($"OnResultGenerated confidence={result.Confidence} text={repr(result.Text)}");

        if (result.Confidence == SpeechRecognitionConfidence.Rejected)
        {
            CheatlyLog.Warn("Result rejected (too low confidence)");
            return;
        }

        var text = result.Text?.Trim();
        if (string.IsNullOrWhiteSpace(text))
        {
            CheatlyLog.Warn("Result text is empty/whitespace");
            return;
        }

        lock (_lock)
        {
            if (text == _lastResultText)
            {
                CheatlyLog.Warn($"Ignoring duplicate SAPI result: {repr(text)}");
                return;
            }
            _lastResultText = text;

            CheatlyLog.Info($"Result accepted (accumulating for final): {repr(text)}");

            if (_accumulated.Length > 0) _accumulated.Append(' ');
            _accumulated.Append(text);
        }

        var cts = new CancellationTokenSource();
        var old = Interlocked.Exchange(ref _silenceCts, cts);
        old?.Cancel();
        old?.Dispose();

        Task.Delay(SilenceThresholdMs, cts.Token).ContinueWith(t =>
        {
            if (t.IsCanceled) return;

            string final;
            lock (_lock)
            {
                final = _accumulated.ToString().Trim();
                _accumulated.Clear();
                _lastResultText = null;
            }

            if (!string.IsNullOrWhiteSpace(final))
            {
                CheatlyLog.Info($"Silence detected — firing FinalTranscript: {repr(final)}");
                FinalTranscriptReady?.Invoke(final);
            }
        }, TaskScheduler.Default);
    }

    private void OnHypothesisGenerated(SpeechRecognizer sender, SpeechRecognitionHypothesisGeneratedEventArgs args)
    {
        var text = args.Hypothesis.Text;
        FragmentReady?.Invoke(text);

        // Reset silence timer so we don't fire FinalTranscript while user is still talking.
        // Do NOT start a new FinalTranscript timer here -- only OnResultGenerated should
        // trigger final sends, since hypotheses don't append to _accumulated.
        var cts = new CancellationTokenSource();
        var old = Interlocked.Exchange(ref _silenceCts, cts);
        old?.Cancel();
        old?.Dispose();
    }

    private void OnSessionCompleted(
        SpeechContinuousRecognitionSession session,
        SpeechContinuousRecognitionCompletedEventArgs args)
    {
        CheatlyLog.Info($"Session completed: status={args.Status}");
        if (!IsRunning) return;

        if (args.Status == SpeechRecognitionResultStatus.Success
            || args.Status == SpeechRecognitionResultStatus.TimeoutExceeded
            || args.Status == SpeechRecognitionResultStatus.UserCanceled)
        {
            _ = Task.Run(async () =>
            {
                if (args.Status == SpeechRecognitionResultStatus.UserCanceled)
                {
                    CheatlyLog.Warn("Session UserCanceled -- restarting after short delay...");
                    await Task.Delay(500);
                }
                else
                {
                    CheatlyLog.Info("Session completed naturally. Restarting to keep listening...");
                }

                try 
                { 
                    CheatlyLog.Info("Recreating SpeechRecognizer to avoid corruption...");
                    await StopAsync();
                    await StartAsync();
                    CheatlyLog.Info("Restarted successfully.");
                }
                catch (Exception ex) { CheatlyLog.Error(ex, "Failed to restart mic session"); }
            });
            return;
        }

        var msg = $"STT session ended: {args.Status}";
        CheatlyLog.Error(msg);
        ErrorOccurred?.Invoke(msg);
        IsRunning = false;
    }

    public async Task StopAsync()
    {
        CheatlyLog.Info("StopAsync called");
        if (!IsRunning || _recognizer == null) return;
        IsRunning = false;

        try
        {
            var oldCts = Interlocked.Exchange(ref _silenceCts, null);
            oldCts?.Cancel();
            oldCts?.Dispose();

            _recognizer.HypothesisGenerated -= OnHypothesisGenerated;
            _recognizer.ContinuousRecognitionSession.ResultGenerated -= OnResultGenerated;
            _recognizer.ContinuousRecognitionSession.Completed -= OnSessionCompleted;

            await _recognizer.ContinuousRecognitionSession.StopAsync().AsTask();
            CheatlyLog.Info("Windows STT stopped");
        }
        catch (Exception ex) 
        { 
            // Ignore COMException if the session was already cancelled/completed (0x80131509)
            if (ex.HResult != unchecked((int)0x80131509))
                CheatlyLog.Error(ex, "StopAsync"); 
        }
        finally
        {
            _recognizer.Dispose();
            _recognizer = null;
        }
    }

    public async ValueTask DisposeAsync() => await StopAsync();

    private static string repr(string? s) =>
        s == null ? "<null>" : $"'{(s.Length > 60 ? s[..60] + "…" : s)}'";
}
