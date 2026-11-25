// 설치 프로그램 다시 만들기: 원래 RetopoAnnotate_Setup.exe 에 들어 있는 리소스(스크립트·DLL·README)를
// 저장소의 새 파일로 바꿔 넣음. 설치 로직은 그대로.
//   mono Repack.exe <원래 Setup.exe> <새 Setup.exe> 이름=파일 ...
using System;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

static class Repack
{
	static int Main(string[] args)
	{
		var asm = AssemblyDefinition.ReadAssembly(args[0]);
		var mod = asm.MainModule;
		for (int i = 2; i < args.Length; i++)
		{
			int eq = args[i].IndexOf('=');
			string name = args[i].Substring(0, eq), file = args[i].Substring(eq + 1);
			var old = mod.Resources.OfType<EmbeddedResource>().FirstOrDefault(r => r.Name == name);
			if (old == null) { Console.WriteLine("리소스 없음: " + name); return 1; }
			int idx = mod.Resources.IndexOf(old);
			mod.Resources[idx] = new EmbeddedResource(name, old.Attributes, File.ReadAllBytes(file));
			Console.WriteLine("{0}: {1} → {2} bytes", name, old.GetResourceData().Length, new FileInfo(file).Length);
		}
		// 번들 버전 표시 1.5.0 → 1.6.0
		foreach (var t in mod.Types)
			foreach (var m in t.Methods.Where(m => m.HasBody))
				foreach (var ins in m.Body.Instructions)
					if (ins.OpCode == OpCodes.Ldstr && ((string)ins.Operand).Contains("1.5.0"))
						ins.Operand = ((string)ins.Operand).Replace("1.5.0", "1.6.0");
		asm.Write(args[1]);
		return 0;
	}
}
