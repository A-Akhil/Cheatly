using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using Cheatly.Avalonia.Models;

namespace Cheatly.Avalonia.ViewModels;

public sealed class OverlayViewModel : INotifyPropertyChanged
{
    private string _transcript = string.Empty;
    private string _committedTranscript = string.Empty;
    private string _liveHypothesis = string.Empty;
    private string _inputText = string.Empty;
    private string _modeIndicator = "Ready";
    private bool _isDraft;
    private bool _isConnected;
    private string _currentTurnId = string.Empty;

    private readonly Dictionary<string, TurnState> _turnStates = new();

    public event PropertyChangedEventHandler? PropertyChanged;

    public ObservableCollection<string> Suggestions { get; } = new();

    public string Transcript
    {
        get => _transcript;
        set => SetField(ref _transcript, value);
    }

    public string InputText
    {
        get => _inputText;
        set => SetField(ref _inputText, value);
    }

    public string ModeIndicator
    {
        get => _modeIndicator;
        set => SetField(ref _modeIndicator, value);
    }

    public bool IsDraft
    {
        get => _isDraft;
        set
        {
            if (SetField(ref _isDraft, value))
            {
                OnPropertyChanged(nameof(ModeColor));
            }
        }
    }

    public bool IsConnected
    {
        get => _isConnected;
        set
        {
            if (SetField(ref _isConnected, value))
            {
                OnPropertyChanged(nameof(ConnectionColor));
            }
        }
    }

    public string ModeColor => IsDraft ? "#FFA500" : "#4CAF50";
    public string ConnectionColor => IsConnected ? "#4CAF50" : "#FF6B6B";

    public void UpdateFromPayload(SuggestionPayload payload)
    {
        if (payload.TurnId == null)
        {
            ApplySuggestions(payload.Output, payload.IsPrefetch);
            return;
        }

        var turnId = payload.TurnId;
        _currentTurnId = turnId;

        if (!_turnStates.TryGetValue(turnId, out var state))
        {
            state = new TurnState();
            _turnStates[turnId] = state;
        }

        if (payload.IsFinal)
        {
            state.HasFinal = true;
            state.FinalSuggestions = payload.Output;
            state.FinalRevision = payload.Revision ?? 0;
        }
        else if (payload.IsPrefetch && !state.HasFinal)
        {
            state.PrefetchSuggestions = payload.Output;
            state.PrefetchRevision = payload.Revision ?? 0;
        }

        if (state.HasFinal)
        {
            ApplySuggestions(state.FinalSuggestions, false);
        }
        else
        {
            ApplySuggestions(state.PrefetchSuggestions, true);
        }

        CleanupOldTurns(turnId);
    }

    private void ApplySuggestions(List<string> suggestions, bool isDraft)
    {
        IsDraft = isDraft;
        ModeIndicator = isDraft ? "Draft" : "Final";

        Suggestions.Clear();
        foreach (var suggestion in suggestions)
        {
            Suggestions.Add(suggestion);
        }
    }

    private void CleanupOldTurns(string currentTurnId)
    {
        var keysToRemove = _turnStates.Keys
            .Where(k => k != currentTurnId && _turnStates[k].HasFinal)
            .ToList();

        foreach (var key in keysToRemove)
        {
            _turnStates.Remove(key);
        }

        if (_turnStates.Count > 10)
        {
            var oldest = _turnStates.Keys.Take(_turnStates.Count - 10).ToList();
            foreach (var key in oldest)
            {
                _turnStates.Remove(key);
            }
        }
    }

    /// <summary>
    /// Called for every live hypothesis. Replaces the in-progress line (not appended).
    /// </summary>
    public void SetLiveHypothesis(string text)
    {
        _liveHypothesis = text ?? string.Empty;
        RebuildTranscript();
    }

    /// <summary>
    /// Called when the speech engine finalizes a phrase. Commits it permanently.
    /// </summary>
    public void CommitTranscript(string text)
    {
        if (string.IsNullOrWhiteSpace(text))
            return;

        // Commit the final text
        if (!string.IsNullOrEmpty(_committedTranscript))
            _committedTranscript += " " + text;
        else
            _committedTranscript = text;

        // Trim if too long
        const int maxLength = 500;
        if (_committedTranscript.Length > maxLength)
        {
            var trimPoint = _committedTranscript.IndexOf(' ', _committedTranscript.Length - maxLength);
            if (trimPoint > 0)
                _committedTranscript = "..." + _committedTranscript.Substring(trimPoint + 1);
        }

        // Clear the live hypothesis since it's now committed
        _liveHypothesis = string.Empty;
        RebuildTranscript();
    }

    /// <summary>
    /// Rebuilds the visible Transcript from committed + live hypothesis.
    /// </summary>
    private void RebuildTranscript()
    {
        if (string.IsNullOrEmpty(_liveHypothesis))
            Transcript = _committedTranscript;
        else if (string.IsNullOrEmpty(_committedTranscript))
            Transcript = _liveHypothesis;
        else
            Transcript = _committedTranscript + " " + _liveHypothesis;
    }

    /// <summary>Legacy wrapper kept for compatibility.</summary>
    public void AppendTranscript(string text) => CommitTranscript(text);

    public void ClearSession()
    {
        Transcript = string.Empty;
        InputText = string.Empty;
        Suggestions.Clear();
        _turnStates.Clear();
        _currentTurnId = string.Empty;
        ModeIndicator = "Ready";
        IsDraft = false;
    }

    private bool SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
            return false;
        field = value;
        OnPropertyChanged(propertyName);
        return true;
    }

    private void OnPropertyChanged([CallerMemberName] string? propertyName = null)
    {
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }

    private sealed class TurnState
    {
        public List<string> PrefetchSuggestions { get; set; } = new();
        public List<string> FinalSuggestions { get; set; } = new();
        public int PrefetchRevision { get; set; }
        public int FinalRevision { get; set; }
        public bool HasFinal { get; set; }
    }
}