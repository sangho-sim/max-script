// 키 입력 도우미 (RetopoAnnotate.ms 의 실행 중 컴파일 소스와 같은 코드)
using System; using System.Threading; using System.Runtime.InteropServices;
public class RAKeys {
 [DllImport("user32.dll")] static extern short GetAsyncKeyState(int k);
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern IntPtr GetAncestor(IntPtr h, uint f);
 [DllImport("user32.dll")] static extern IntPtr SetWindowsHookEx(int id, HookProc fn, IntPtr mod, uint tid);
 [DllImport("user32.dll")] static extern IntPtr CallNextHookEx(IntPtr h, int n, IntPtr w, IntPtr l);
 [DllImport("user32.dll")] static extern int GetMessage(out MSG m, IntPtr h, uint a, uint b);
 [DllImport("kernel32.dll")] static extern IntPtr GetModuleHandle(string n);
 public delegate IntPtr HookProc(int n, IntPtr w, IntPtr l);
 [StructLayout(LayoutKind.Sequential)] public struct MSG { public IntPtr hwnd; public uint message; public IntPtr wp; public IntPtr lp; public uint time; public int x; public int y; }
 [StructLayout(LayoutKind.Sequential)] public struct MSLL { public int x; public int y; public uint data; public uint flags; public uint time; public IntPtr extra; }
 volatile int pend; int wheel; int wheelS; public volatile bool Armed; long owner; Thread th; Thread th2; IntPtr hook; HookProc proc;
 static bool D(int k) { return (GetAsyncKeyState(k) & 0x8000) != 0; }
 bool Front() { return GetAncestor(GetForegroundWindow(), 3).ToInt64() == owner; }
 public void Start(long hwnd) { owner = hwnd; if (th != null) return;
  th = new Thread(Loop); th.IsBackground = true; th.Start();
  th2 = new Thread(HookLoop); th2.IsBackground = true; th2.Start(); }
 void Loop() { bool prev = false; while (true) {
  bool c = D(0x11), z = D(0x5A), y = D(0x59);
  bool fire = c && (z || y);
  if (fire && !prev && Front()) pend = (z && !D(0x10)) ? 1 : 2;
  prev = fire; Thread.Sleep(5); } }
 void HookLoop() { proc = new HookProc(OnMouse); hook = SetWindowsHookEx(14, proc, GetModuleHandle(null), 0);
  MSG m; while (GetMessage(out m, IntPtr.Zero, 0, 0) > 0) { } }
 IntPtr OnMouse(int n, IntPtr w, IntPtr l) {
  if (n >= 0 && w.ToInt64() == 0x020A && Armed && D(0x12) && Front()) {
   MSLL s = (MSLL)Marshal.PtrToStructure(l, typeof(MSLL));
   int d = (short)((s.data >> 16) & 0xffff);
   int st = d > 0 ? 1 : -1;
   lock (this) { if (D(0x10)) wheelS += st; else wheel += st; }
   return (IntPtr)1; }
  return CallNextHookEx(hook, n, w, l); }
 public int Take() { int p = pend; pend = 0; return p; }
 public int TakeWheel() { lock (this) { int p = wheel; wheel = 0; return p; } }
 public int TakeWheelShift() { lock (this) { int p = wheelS; wheelS = 0; return p; } }
}
