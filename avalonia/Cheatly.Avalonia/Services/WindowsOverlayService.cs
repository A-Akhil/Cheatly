using System;
using System.Runtime.InteropServices;

namespace Cheatly.Avalonia.Services;

public static class WindowsOverlayService
{
    private const uint WDA_EXCLUDEFROMCAPTURE = 0x00000011;

    [DllImport("user32.dll")]
    private static extern bool SetWindowDisplayAffinity(IntPtr hwnd, uint dwAffinity);

    [DllImport("user32.dll")]
    private static extern uint GetWindowDisplayAffinity(IntPtr hwnd, out uint dwAffinity);

    public static bool SetCaptureExclusion(IntPtr hwnd, bool enabled)
    {
        if (hwnd == IntPtr.Zero)
            return false;

        uint affinity = enabled ? WDA_EXCLUDEFROMCAPTURE : 0;
        return SetWindowDisplayAffinity(hwnd, affinity);
    }

    public static bool IsCaptureExclusionEnabled(IntPtr hwnd)
    {
        if (hwnd == IntPtr.Zero)
            return false;

        GetWindowDisplayAffinity(hwnd, out uint affinity);
        return affinity == WDA_EXCLUDEFROMCAPTURE;
    }

    public static bool IsSupported()
    {
        return RuntimeInformation.IsOSPlatform(OSPlatform.Windows) &&
               Environment.OSVersion.Version >= new Version(10, 0, 18362);
    }
}
