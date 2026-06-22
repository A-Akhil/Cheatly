"""Check CPU feature support - ctranslate2 requires specific SIMD instructions"""
import ctypes
import struct
import os

def check_cpuid():
    """Check basic CPU features via a quick test"""
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        flags = info.get('flags', [])
        print("CPU flags:", sorted(flags))
        for feat in ['sse', 'sse2', 'sse3', 'ssse3', 'sse4_1', 'sse4_2', 'avx', 'avx2', 'fma']:
            present = feat in flags
            print(f"  {feat}: {'YES' if present else 'NO'}")
    except ImportError:
        print("cpuinfo not installed, trying alternative check")

    # Alternative: try loading ctranslate2 shared lib and see what happens
    import ctranslate2
    print(f"\nctranslate2 version: {ctranslate2.__version__}")

    # Check the DLLs that ctranslate2 ships
    ct2_dir = os.path.dirname(ctranslate2.__file__)
    print(f"ctranslate2 dir: {ct2_dir}")
    dlls = [f for f in os.listdir(ct2_dir) if f.endswith('.dll') or f.endswith('.pyd')]
    print(f"DLLs: {dlls}")

    # Check if we can at least call simple ctranslate2 functions
    print(f"\nCPU compute types: {sorted(ctranslate2.get_supported_compute_types('cpu'))}")

    # Try creating a simpler model type if available
    print("\nAvailable model types:", [x for x in dir(ctranslate2.models) if not x.startswith('_')])

check_cpuid()
