// 테스트: mono RAQuadTest.exe out.obj edge sharpDeg flags in1.obj in2.obj ...
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Diagnostics;
using System.Linq;

static class RAQuadTest
{
	static int Main(string[] args)
	{
		CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
		System.Threading.Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture;
		string outPath = args[0];
		double edge = double.Parse(args[1]);
		double sharp = double.Parse(args[2]);
		int flags = int.Parse(args[3]);
		var q = new RAQuad();
		foreach (System.Collections.DictionaryEntry de in Environment.GetEnvironmentVariables())
		{
			string k = (string)de.Key;
			if (!k.StartsWith("RAQ_")) continue;
			var fi = typeof(RAQuad).GetField(k.Substring(4));
			if (fi == null) { Console.WriteLine("no field " + k); continue; }
			fi.SetValue(q, Convert.ChangeType(de.Value, fi.FieldType, CultureInfo.InvariantCulture));
			Console.WriteLine("set {0} = {1}", fi.Name, de.Value);
		}
		var sw = Stopwatch.StartNew();
		for (int a = 4; a < args.Length; a++)
		{
			var v = new List<float>(); var t = new List<int>();
			foreach (var line in File.ReadLines(args[a]))
			{
				if (line.StartsWith("v "))
				{
					var p = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
					v.Add(float.Parse(p[1])); v.Add(float.Parse(p[2])); v.Add(float.Parse(p[3]));
				}
				else if (line.StartsWith("f "))
				{
					var p = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
					var ids = new int[p.Length - 1];
					for (int i = 1; i < p.Length; i++) ids[i - 1] = int.Parse(p[i].Split('/')[0]) - 1;
					for (int i = 1; i + 1 < ids.Length; i++) { t.Add(ids[0]); t.Add(ids[i]); t.Add(ids[i + 1]); }
				}
			}
			q.AddMesh(v.ToArray(), t.ToArray());
		}
		Console.WriteLine("load {0:0.00}s", sw.Elapsed.TotalSeconds);
		// GUIDES=파일: 줄마다 "x y z nx ny nz", 빈 줄로 선 구분
		string gf = Environment.GetEnvironmentVariable("GUIDES");
		if (gf != null)
		{
			var pts = new List<float>(); var nrm = new List<float>();
			foreach (var line in File.ReadAllLines(gf).Concat(new[] { "" }))
			{
				var p = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
				if (p.Length < 6) { if (pts.Count > 0) q.AddGuide(pts.ToArray(), nrm.ToArray()); pts.Clear(); nrm.Clear(); continue; }
				for (int i = 0; i < 3; i++) pts.Add(float.Parse(p[i]));
				for (int i = 3; i < 6; i++) nrm.Add(float.Parse(p[i]));
			}
		}
		string res = q.Run(edge, sharp, flags, 0);
		Console.Write(q.Log);
		// 같은 엔진으로 면 수만 바꿔 다시 (Max 의 +/− 와 같음)
		string rerun = Environment.GetEnvironmentVariable("RERUN");
		if (rerun != null)
			foreach (var tf in rerun.Split(','))
			{
				q.TargetFaces = int.Parse(tf);
				var sw2 = Stopwatch.StartNew();
				res = q.Run(edge, sharp, flags, 0);
				Console.WriteLine("rerun target {0}: {1}  faces {2}  {3:0.00}s", tf, res, q.OutCounts.Length, sw2.Elapsed.TotalSeconds);
			}
		Console.WriteLine(res);
		using (var w = new StreamWriter(outPath))
		{
			for (int i = 0; i < q.OutVerts.Length; i += 3) w.WriteLine("v {0} {1} {2}", q.OutVerts[i], q.OutVerts[i + 1], q.OutVerts[i + 2]);
			int o = 0;
			foreach (int c in q.OutCounts)
			{
				w.Write("f");
				for (int k = 0; k < c; k++) w.Write(" " + (q.OutIdx[o++] + 1));
				w.WriteLine();
			}
		}
		if (Environment.GetEnvironmentVariable("SNOUT") != null)
		{
			var sv = q.DebugSurfaceNet(); var sq = q.DebugSurfaceNetQuads(); var tg = q.DebugTags();
			using (var w = new StreamWriter(Environment.GetEnvironmentVariable("SNOUT")))
			{
				for (int i = 0; i < sv.Length; i += 3) w.WriteLine("v {0} {1} {2} {3}", sv[i], sv[i + 1], sv[i + 2], tg[i / 3]);
				for (int i = 0; i < sq.Length; i += 4) w.WriteLine("f {0} {1} {2} {3}", sq[i] + 1, sq[i + 1] + 1, sq[i + 2] + 1, sq[i + 3] + 1);
			}
		}
		return res == "OK" ? 0 : 1;
	}
}
