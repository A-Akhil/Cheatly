using System.Runtime.CompilerServices;

namespace Cheatly.Avalonia.Services;

/// <summary>
/// Simple logger: writes to console (visible in dotnet run) + a .log file side-by-side with the exe.
/// </summary>
public static class CheatlyLog
{
    private static readonly string LogPath = Path.Combine(
        AppContext.BaseDirectory, "cheatly_debug.log");

    private static readonly object _lock = new();

    static CheatlyLog()
    {
        // Clear old log on startup
        try { File.AppendAllText(LogPath, $"\n=== Cheatly Debug Log {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===\n"); }
        catch { }
    }

    public static void Info(string msg, [CallerMemberName] string caller = "")
        => Write("INFO ", caller, msg);

    public static void Warn(string msg, [CallerMemberName] string caller = "")
        => Write("WARN ", caller, msg);

    public static void Error(string msg, [CallerMemberName] string caller = "")
        => Write("ERROR", caller, msg);

    public static void Error(Exception ex, string context, [CallerMemberName] string caller = "")
        => Write("ERROR", caller, $"{context}: [{ex.GetType().Name}] {ex.Message}\n  HResult=0x{ex.HResult:X8}\n  {ex.StackTrace?.Split('\n').FirstOrDefault()}");

    private static void Write(string level, string caller, string msg)
    {
        var line = $"[{DateTime.Now:HH:mm:ss.fff}] {level} [{caller}] {msg}";
        lock (_lock)
        {
            // Always write to console — visible in 'dotnet run'
            Console.WriteLine(line);

            // Also write to file
            try { File.AppendAllText(LogPath, line + "\n"); }
            catch { }
        }
    }

    public static string LogFilePath => LogPath;
}
