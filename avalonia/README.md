# Cheatly Avalonia client

This directory contains the C# desktop UI built with Avalonia.

## Scope

- UI stack: Avalonia
- Backend: Python FastAPI service in [backend/main.py](../backend/main.py)
- Runtime targets: Linux and Windows

## Structure

- [Cheatly.Avalonia.sln](Cheatly.Avalonia.sln)
- [Cheatly.Avalonia](Cheatly.Avalonia)
  - [Program.cs](Cheatly.Avalonia/Program.cs)
  - [App.axaml](Cheatly.Avalonia/App.axaml)
  - [MainWindow.axaml](Cheatly.Avalonia/MainWindow.axaml)
  - [Services/BackendClient.cs](Cheatly.Avalonia/Services/BackendClient.cs)
  - [Services/WebSocketSuggestionClient.cs](Cheatly.Avalonia/Services/WebSocketSuggestionClient.cs)
  - [ViewModels/MainViewModel.cs](Cheatly.Avalonia/ViewModels/MainViewModel.cs)

## Run flow

1. Start backend server from project root:

python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

2. Run the Avalonia app:

dotnet run --project avalonia/Cheatly.Avalonia/Cheatly.Avalonia.csproj

Default backend endpoints:
- `http://127.0.0.1:8000`
- `ws://127.0.0.1:8000/ws`
