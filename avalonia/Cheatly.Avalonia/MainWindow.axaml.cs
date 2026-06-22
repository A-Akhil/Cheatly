using Cheatly.Avalonia.ViewModels;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Threading;

namespace Cheatly.Avalonia;

public partial class MainWindow : Window
{
    private readonly MainViewModel _viewModel;

    public MainWindow()
    {
        InitializeComponent();
        _viewModel = new MainViewModel();

        TranscriptList.ItemsSource = _viewModel.TranscriptItems;
        OutputList.ItemsSource = _viewModel.OutputItems;
        BackendStatusText.Text = _viewModel.BackendStatus;
        _viewModel.BackendStatusChanged += OnBackendStatusChanged;

        Closed += async (_, _) => await _viewModel.DisposeAsync();
    }

    private async void OnConnectClicked(object? sender, RoutedEventArgs e)
    {
        await _viewModel.ConnectAsync();
    }

    private async void OnStartTranscriptionClicked(object? sender, RoutedEventArgs e)
    {
        await _viewModel.StartTranscriptionAsync();
    }

    private async void OnStopTranscriptionClicked(object? sender, RoutedEventArgs e)
    {
        await _viewModel.StopTranscriptionAsync();
    }

    private async void OnResetSessionClicked(object? sender, RoutedEventArgs e)
    {
        await _viewModel.ResetSessionAsync();
    }

    private async void OnSendTranscriptClicked(object? sender, RoutedEventArgs e)
    {
        var text = TranscriptInputBox.Text;
        if (string.IsNullOrWhiteSpace(text))
        {
            return;
        }

        TranscriptInputBox.Text = string.Empty;
        await _viewModel.SendTranscriptAsync(text);
    }

    private void OnBackendStatusChanged(string status)
    {
        Dispatcher.UIThread.Post(() => BackendStatusText.Text = status);
    }
}
