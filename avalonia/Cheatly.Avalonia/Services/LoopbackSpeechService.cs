using System.Collections.Concurrent;
using System.Globalization;
using System.Speech.AudioFormat;
using System.Speech.Recognition;
using System.Text;
using NAudio.Wave;

namespace Cheatly.Avalonia.Services;

public sealed class LoopbackSpeechService : IAsyncDisposable
{
    private WasapiLoopbackCapture? _capture;
    private SpeechRecognitionEngine? _engine;
    private AudioPipeStream? _pipe;
    private IWaveProvider? _resampler;
    private BufferedWaveProvider? _inputBuffer;
    private int _chunksReceived;
    private int _recognitionCount;

    private CancellationTokenSource? _silenceCts;
    private readonly StringBuilder _accumulated = new();
    private readonly object _accLock = new();
    private const int SilenceThresholdMs = 1500;

    public event Action<string>? FragmentReady;
    public event Action<string>? FinalTranscriptReady;
    public event Action<string>? ErrorOccurred;

    public bool IsRunning { get; private set; }

    public Task<bool> StartAsync()
    {
        CheatlyLog.Info("StartAsync called");
        try
        {
            // ── Step 1: WASAPI loopback capture ────────────────────────────────
            _capture = new WasapiLoopbackCapture();
            CheatlyLog.Info($"WasapiLoopbackCapture created: format={_capture.WaveFormat}");

            _inputBuffer = new BufferedWaveProvider(_capture.WaveFormat)
            {
                BufferDuration = TimeSpan.FromSeconds(3),
                DiscardOnBufferOverflow = true
            };

            // ── Step 2: Resample to 16kHz 16-bit mono ──────────────────────────
            var targetFormat = new WaveFormat(16000, 16, 1);
            _resampler = new MediaFoundationResampler(_inputBuffer, targetFormat)
            {
                ResamplerQuality = 60
            };
            CheatlyLog.Info($"MediaFoundationResampler: {_capture.WaveFormat} → {targetFormat}");

            // ── Step 3: Pipe bridge ─────────────────────────────────────────────
            _pipe = new AudioPipeStream();

            _chunksReceived = 0;
            _recognitionCount = 0;
            _capture.DataAvailable += (_, e) =>
            {
                _inputBuffer!.AddSamples(e.Buffer, 0, e.BytesRecorded);

                var buf = new byte[4096];
                int read;
                int drained = 0;
                while ((read = _resampler!.Read(buf, 0, buf.Length)) > 0)
                {
                    _pipe!.Write(buf, 0, read);
                    drained += read;
                }

                _chunksReceived++;
                if (_chunksReceived <= 5 || _chunksReceived % 50 == 0)
                    CheatlyLog.Info($"Loopback chunks={_chunksReceived} last_drain={drained}B pipe_ok=true");
            };

            // ── Step 4: System.Speech recognition ──────────────────────────────
            _engine = new SpeechRecognitionEngine(new CultureInfo("en-US"));
            CheatlyLog.Info("SpeechRecognitionEngine created with en-US");

            _engine.LoadGrammar(new DictationGrammar());
            CheatlyLog.Info("DictationGrammar loaded");

            _engine.SpeechRecognized       += OnSpeechRecognized;
            _engine.SpeechDetected         += (_, _) => CheatlyLog.Info("Speech DETECTED in loopback audio");
            _engine.SpeechHypothesized     += (_, e) => CheatlyLog.Info($"Hypothesis: '{e.Result.Text}'");
            _engine.RecognizeCompleted     += OnRecognizeCompleted;
            _engine.SpeechRecognitionRejected += (_, e) =>
                CheatlyLog.Warn($"Speech REJECTED (confidence too low): '{e.Result.Text}'");

            _engine.SetInputToAudioStream(
                _pipe,
                new SpeechAudioFormatInfo(16000, AudioBitsPerSample.Sixteen, AudioChannel.Mono)
            );
            CheatlyLog.Info("SetInputToAudioStream configured (16kHz 16-bit mono)");

            _engine.RecognizeAsync(RecognizeMode.Multiple);
            CheatlyLog.Info("RecognizeAsync(Multiple) started");

            _capture.StartRecording();
            CheatlyLog.Info("WASAPI loopback capture started -- listening for system audio");

            // Watchdog: warn if data flows but no recognition fires after 15 seconds
            _ = Task.Run(async () =>
            {
                await Task.Delay(15000);
                if (IsRunning && _recognitionCount == 0)
                {
                    CheatlyLog.Warn($"Loopback watchdog: {_chunksReceived} audio chunks received but 0 recognitions after 15s. System.Speech may not handle loopback audio well on this system.");
                }
            });

            IsRunning = true;
            return Task.FromResult(true);
        }
        catch (Exception ex)
        {
            CheatlyLog.Error(ex, "StartAsync failed");
            ErrorOccurred?.Invoke($"Loopback STT failed: {ex.Message}");
            Cleanup();
            return Task.FromResult(false);
        }
    }

    private void OnSpeechRecognized(object? sender, SpeechRecognizedEventArgs e)
    {
        _recognitionCount++;
        CheatlyLog.Info($"OnSpeechRecognized confidence={e.Result.Confidence:F2} text='{e.Result.Text}'");

        if (e.Result.Confidence < 0.45f)
        {
            CheatlyLog.Warn($"Rejected: confidence {e.Result.Confidence:F2} < 0.45 threshold");
            return;
        }

        var text = e.Result.Text?.Trim();
        if (string.IsNullOrWhiteSpace(text)) return;

        CheatlyLog.Info($"Loopback fragment accepted: '{text}'");
        FragmentReady?.Invoke($"[System] {text}");

        lock (_accLock)
        {
            if (_accumulated.Length > 0) _accumulated.Append(' ');
            _accumulated.Append(text);
        }

        _silenceCts?.Cancel();
        _silenceCts?.Dispose();
        var cts = new CancellationTokenSource();
        _silenceCts = cts;

        Task.Delay(SilenceThresholdMs, cts.Token).ContinueWith(t =>
        {
            if (t.IsCanceled) return;
            string final;
            lock (_accLock)
            {
                final = _accumulated.ToString().Trim();
                _accumulated.Clear();
            }
            if (!string.IsNullOrWhiteSpace(final))
            {
                CheatlyLog.Info($"Loopback final transcript: '{final}'");
                FinalTranscriptReady?.Invoke(final);
            }
        }, TaskScheduler.Default);
    }

    private void OnRecognizeCompleted(object? sender, RecognizeCompletedEventArgs e)
    {
        if (e.Error != null)
            CheatlyLog.Error(e.Error, "RecognizeCompleted with error");
        else
            CheatlyLog.Info($"RecognizeCompleted: cancelled={e.Cancelled}");
    }

    public Task StopAsync()
    {
        CheatlyLog.Info("StopAsync called");
        IsRunning = false;
        _silenceCts?.Cancel();
        Cleanup();
        return Task.CompletedTask;
    }

    private void Cleanup()
    {
        try { _capture?.StopRecording(); } catch { }
        try { _engine?.RecognizeAsyncStop(); } catch { }
        try { _pipe?.Complete(); } catch { }
        try { _capture?.Dispose(); } catch { }
        try { _engine?.Dispose(); } catch { }
        try { _pipe?.Dispose(); } catch { }
        _capture = null; _engine = null; _pipe = null;
        _resampler = null; _inputBuffer = null;
    }

    public async ValueTask DisposeAsync() { await StopAsync(); _silenceCts?.Dispose(); }
}

internal sealed class AudioPipeStream : Stream
{
    private readonly BlockingCollection<byte[]> _queue = new(64);
    private byte[] _current = Array.Empty<byte>();
    private int _pos;

    public override bool CanRead  => true;
    public override bool CanSeek  => true; // Fake it for System.Speech
    public override bool CanWrite => true;
    public override long Length   => long.MaxValue; // Prevent EOF detection
    
    private long _position;
    public override long Position 
    { 
        get => _position; 
        set => _position = value; 
    }

    public override void Write(byte[] buffer, int offset, int count)
    {
        if (_queue.IsAddingCompleted) return;
        var chunk = new byte[count];
        Buffer.BlockCopy(buffer, offset, chunk, 0, count);
        _queue.TryAdd(chunk, millisecondsTimeout: 5);
    }

    public override int Read(byte[] buffer, int offset, int count)
    {
        int written = 0;
        while (written < count)
        {
            if (_pos < _current.Length)
            {
                int toCopy = Math.Min(count - written, _current.Length - _pos);
                Buffer.BlockCopy(_current, _pos, buffer, offset + written, toCopy);
                _pos += toCopy;
                written += toCopy;
                _position += toCopy;
            }
            else
            {
                try { _current = _queue.Take(); _pos = 0; }
                catch (InvalidOperationException) { break; }
            }
        }
        return written;
    }

    public void Complete() => _queue.CompleteAdding();
    public override void Flush() { }
    public override long Seek(long offset, SeekOrigin origin) => _position;
    public override void SetLength(long value) { }
    protected override void Dispose(bool disposing) { if (disposing) _queue.Dispose(); base.Dispose(disposing); }
}
