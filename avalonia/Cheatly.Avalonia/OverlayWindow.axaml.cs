using System;
using System.Collections.Generic;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Shapes;
using Avalonia.Input;
using Avalonia.Interactivity;
using Avalonia.Media;
using Avalonia.Threading;
using Cheatly.Avalonia.Models;
using Cheatly.Avalonia.Services;
using Cheatly.Avalonia.ViewModels;

namespace Cheatly.Avalonia;

public partial class OverlayWindow : Window
{
    private readonly OverlayViewModel _viewModel;
    private readonly bool _enableCaptureExclusion;
    private readonly DispatcherTimer _timer;
    private int _secondsElapsed;

    public event Action? SessionStopped;
    public event Action<string>? ForceSendRequested;

    public OverlayViewModel ViewModel => _viewModel;

    public OverlayWindow() : this(true)
    {
    }

    public OverlayWindow(bool enableCaptureExclusion)
    {
        InitializeComponent();

        _enableCaptureExclusion = enableCaptureExclusion;
        _viewModel = new OverlayViewModel();
        DataContext = _viewModel;
        SuggestionsList.ItemsSource = _viewModel.Suggestions;

        _viewModel.PropertyChanged += OnViewModelPropertyChanged;

        Opened += OnWindowOpened;
        Closed += OnWindowClosed;

        _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(1) };
        _timer.Tick += (s, e) => 
        {
            _secondsElapsed++;
            var mins = _secondsElapsed / 60;
            var secs = _secondsElapsed % 60;
            var timerText = this.FindControl<TextBlock>("TimerText");
            if (timerText != null)
            {
                timerText.Text = $"{mins:D2}:{secs:D2}";
            }
        };
    }

    private void OnWindowClosed(object? sender, EventArgs e)
    {
        _timer.Stop();
        SessionStopped?.Invoke();
    }

    private void OnViewModelPropertyChanged(object? sender, System.ComponentModel.PropertyChangedEventArgs e)
    {
        if (e.PropertyName == nameof(OverlayViewModel.IsConnected))
        {
            UpdateConnectionIndicator();
        }
        else if (e.PropertyName == nameof(OverlayViewModel.IsDraft))
        {
            UpdateModeIndicator();
        }
    }

    private void UpdateConnectionIndicator()
    {
        Dispatcher.UIThread.Post(() =>
        {
            var color = _viewModel.IsConnected ? "#4CAF50" : "#FF6B6B";
            var brush = new SolidColorBrush(Color.Parse(color));
            
            var indicator = this.FindControl<Border>("ConnectionIndicator");
            if (indicator != null)
            {
                indicator.Background = brush;
            }
        });
    }

    private void UpdateModeIndicator()
    {
        Dispatcher.UIThread.Post(() =>
        {
            ModeIndicator.Text = _viewModel.ModeIndicator;
            var color = _viewModel.IsDraft ? "#FFA500" : "#4CAF50";
            ModeIndicator.Foreground = new SolidColorBrush(Color.Parse(color));
        });
    }

    private void OnWindowOpened(object? sender, EventArgs e)
    {
        if (_enableCaptureExclusion)
        {
            ApplyCaptureExclusion();
        }
        PositionTopRight();
        UpdateConnectionIndicator();
        _timer.Start();
    }

    private void ApplyCaptureExclusion()
    {
        if (!WindowsOverlayService.IsSupported())
            return;

        var handle = TryGetPlatformHandle()?.Handle ?? IntPtr.Zero;
        if (handle != IntPtr.Zero)
        {
            WindowsOverlayService.SetCaptureExclusion(handle, true);
        }
    }

    private void PositionTopRight()
    {
        var screen = Screens.Primary;
        if (screen == null) return;

        var workArea = screen.WorkingArea;
        Position = new PixelPoint(
            workArea.X + workArea.Width - (int)Width - 20,
            workArea.Y + 20
        );
    }

    private void OnHeaderPointerPressed(object? sender, PointerPressedEventArgs e)
    {
        if (e.GetCurrentPoint(this).Properties.IsLeftButtonPressed)
        {
            BeginMoveDrag(e);
        }
    }

    private void OnBackClicked(object? sender, RoutedEventArgs e)
    {
        _viewModel.ClearSession();
        Close();
    }

    private void OnSendClicked(object? sender, RoutedEventArgs e)
    {
        var userInput = _viewModel.InputText?.Trim();
        var transcript = _viewModel.Transcript ?? "";

        var textToSend = string.IsNullOrEmpty(userInput)
            ? transcript
            : $"{transcript}\n\n[User context]: {userInput}";

        if (!string.IsNullOrWhiteSpace(textToSend))
        {
            ForceSendRequested?.Invoke(textToSend);
            _viewModel.InputText = "";
        }
    }

    public void UpdateFromPayload(SuggestionPayload payload)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _viewModel.UpdateFromPayload(payload);
            AutoScrollSuggestions();
        });
    }

    public void UpdateTranscript(string text)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _viewModel.CommitTranscript(text);
            AutoScrollTranscript();
        });
    }

    /// <summary>Live hypothesis — replaces the in-progress text, doesn't append.</summary>
    public void SetLiveHypothesis(string text)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _viewModel.SetLiveHypothesis(text);
            AutoScrollTranscript();
        });
    }

    public void UpdateSuggestions(List<string> suggestions, string mode)
    {
        Dispatcher.UIThread.Post(() =>
        {
            var payload = new SuggestionPayload
            {
                Output = suggestions,
                Mode = mode
            };
            _viewModel.UpdateFromPayload(payload);
        });
    }

    public void SetConnectionState(bool connected)
    {
        Dispatcher.UIThread.Post(() =>
        {
            _viewModel.IsConnected = connected;
        });
    }

    public void ClearSuggestions()
    {
        Dispatcher.UIThread.Post(() =>
        {
            _viewModel.ClearSession();
        });
    }

    private void AutoScrollTranscript()
    {
        var sv = this.FindControl<ScrollViewer>("TranscriptScroller");
        sv?.ScrollToEnd();
    }

    private void AutoScrollSuggestions()
    {
        var sv = this.FindControl<ScrollViewer>("SuggestionsScroller");
        sv?.ScrollToEnd();
    }
}
