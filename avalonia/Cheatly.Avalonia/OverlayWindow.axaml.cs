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
            ConnectionIndicator.Fill = new SolidColorBrush(Color.Parse(color));
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

    private void OnCloseClicked(object? sender, RoutedEventArgs e)
    {
        _viewModel.ClearSession();
        SessionStopped?.Invoke();
        Close();
    }

    private void OnBackClicked(object? sender, RoutedEventArgs e)
    {
        _viewModel.ClearSession();
        SessionStopped?.Invoke();
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
