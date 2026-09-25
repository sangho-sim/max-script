// RAQuad: 여러 오브젝트를 하나로 합쳐 흐름에 맞는 쿼드 메쉬로 다시 만드는 엔진 (스캔 → 합친 메쉬)
//
//  1) 복셀 합치기   : 모든 삼각형까지의 거리(좁은 띠)를 격자에 기록하고 바깥에서 채워 들어가
//                     겹치거나 열린(판) 오브젝트도 하나의 닫힌 껍질로 만듦 (거리 r 만큼 부푼 면)
//  2) 서피스 넷     : 껍질을 고른 쿼드 격자 메쉬로 (방향장 계산용 바탕)
//  3) 방향장/위치장 : Instant Meshes 방식 4-RoSy 방향장 + 격자 위치장 (여러 단계 계층으로 빠르게 수렴)
//                     날카로운 모서리(꺾인 엣지·열린 경계)는 방향과 격자선을 모서리에 고정
//  4) 추출          : 격자점이 같은 버텍스는 합치고, 한 칸 차이는 엣지로 → 면 찾기 → 쿼드 위주 메쉬
//  5) 정리          : 삼각형 짝 → 쿼드, (선택) 한 번 나눠 전부 쿼드, 원래 표면에 붙이며 이완,
//                     모서리 버텍스는 모서리 선 위로
//
// MaxScript 에서:  q = asm.CreateInstance "RAQuad"; q.AddMesh xyz tris; q.Run edge angle flags maxVox
//                  → q.OutVerts (x,y,z...) / q.OutCounts (면마다 버텍스 수) / q.OutIdx (0 기반)
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Text;
using System.Threading.Tasks;

public struct RV
{
	public double X, Y, Z;
	public RV(double x, double y, double z) { X = x; Y = y; Z = z; }
	public static RV operator +(RV a, RV b) { return new RV(a.X + b.X, a.Y + b.Y, a.Z + b.Z); }
	public static RV operator -(RV a, RV b) { return new RV(a.X - b.X, a.Y - b.Y, a.Z - b.Z); }
	public static RV operator -(RV a) { return new RV(-a.X, -a.Y, -a.Z); }
	public static RV operator *(RV a, double s) { return new RV(a.X * s, a.Y * s, a.Z * s); }
	public static RV operator *(double s, RV a) { return new RV(a.X * s, a.Y * s, a.Z * s); }
	public static RV operator /(RV a, double s) { return new RV(a.X / s, a.Y / s, a.Z / s); }
	public double Dot(RV b) { return X * b.X + Y * b.Y + Z * b.Z; }
	public RV Cross(RV b) { return new RV(Y * b.Z - Z * b.Y, Z * b.X - X * b.Z, X * b.Y - Y * b.X); }
	public double Len2 { get { return X * X + Y * Y + Z * Z; } }
	public double Len { get { return Math.Sqrt(X * X + Y * Y + Z * Z); } }
	public RV Norm() { double l = Len; return l > 1e-30 ? this / l : new RV(0, 0, 0); }
	public static readonly RV Zero = new RV(0, 0, 0);
}

// (a<<32|b) 꼴 키는 기본 해시가 a^b 라 충돌이 심함 → 섞어서 해시
public sealed class LongKey : IEqualityComparer<long>
{
	public static readonly LongKey I = new LongKey();
	public bool Equals(long a, long b) { return a == b; }
	public int GetHashCode(long x)
	{
		ulong z = (ulong)x * 0x9E3779B97F4A7C15UL;
		z = (z ^ (z >> 31)) * 0xBF58476D1CE4E5B9UL;
		return (int)(z ^ (z >> 32));
	}
}

public class RAQuad
{
	// ---------------------------------------------------------------- 입력
	readonly List<double> inXYZ = new List<double>();
	readonly List<int> inTri = new List<int>();
	readonly List<int> inTriObj = new List<int>();
	int objCount;

	// ---------------------------------------------------------------- 출력
	public float[] OutVerts = new float[0];
	public int[] OutCounts = new int[0];
	public int[] OutIdx = new int[0];
	public string Log = "";
	public int OutQuads, OutTris, OutOthers;

	// ---------------------------------------------------------------- 설정
	public double VoxelRatio = 0.4;      // 칸 크기 = 엣지 길이 × 이 값
	public double Dilate = 0.6;          // 껍질 부풀림 = 칸 크기 × 이 값 (얇은 판/틈 메우기)
	public int OrientIters = 12;
	public int PosIters = 12;
	public int RelaxIters = 6;
	public double MinCreaseLen = 1.5;
	public bool SnapToCrease = false;    // 모서리 버텍스를 가장 가까운 날카로운 엣지로 (두꺼운 모서리용)    // 이 길이(엣지 길이 배수)보다 짧은 모서리 선은 무시

	// flags
	public const int F_PureQuad = 1;     // 한 번 나눠서 전부 쿼드
	public const int F_Sharp = 2;        // 모서리 살리기
	public const int F_KeepBack = 4;     // 두께 없는 판의 뒷면도 남김
	public const int F_Serial = 8;       // 병렬 처리 끔 (디버그)

	public void Clear()
	{
		inXYZ.Clear(); inTri.Clear(); inTriObj.Clear(); objCount = 0;
	}

	// xyz: 월드 좌표 (x,y,z 반복), tris: 0 기반 삼각형 인덱스
	public int AddMesh(float[] xyz, int[] tris)
	{
		int baseV = inXYZ.Count / 3;
		for (int i = 0; i < xyz.Length; i++) inXYZ.Add(xyz[i]);
		for (int i = 0; i + 2 < tris.Length; i += 3)
		{
			int a = tris[i], b = tris[i + 1], c = tris[i + 2];
			if (a == b || b == c || a == c) continue;
			inTri.Add(a + baseV); inTri.Add(b + baseV); inTri.Add(c + baseV);
			inTriObj.Add(objCount);
		}
		return objCount++;
	}

	public int AddMeshD(double[] xyz, int[] tris)
	{
		float[] f = new float[xyz.Length];
		for (int i = 0; i < f.Length; i++) f[i] = (float)xyz[i];
		return AddMesh(f, tris);
	}

	// ================================================================ 공용 데이터
	RV[] P;           // 입력 버텍스
	int[] T;          // 입력 삼각형 (3개씩)
	RV[] TN;          // 삼각형 법선
	byte[] triSharp;  // 삼각형 엣지(0:ab 1:bc 2:ca)가 날카로운지 비트
	bool[] triOpen;   // 열린(판) 오브젝트의 삼각형
	int nT;

	double L, h, r;
	int nx, ny, nz;
	RV g0;
	float[] D;        // 가장 가까운 삼각형까지 거리 (띠 밖은 큰 값)
	int[] NT;         // 가장 가까운 삼각형
	byte[] outside;   // 바깥에서 채워진 칸
	bool parallel = true;

	StringBuilder log;
	Stopwatch sw;
	void Note(string s) { log.AppendFormat("{0,6:0.00}s  {1}\n", sw.Elapsed.TotalSeconds, s); }

	// ================================================================ 실행
	// edge: 목표 엣지 길이, sharpDeg: 이 각도 이상 꺾인 엣지를 모서리로, maxVox: 최대 복셀 수
	public string Run(double edge, double sharpDeg, int flags, int maxVox)
	{
		log = new StringBuilder();
		sw = Stopwatch.StartNew();
		parallel = (flags & F_Serial) == 0;
		OutVerts = new float[0]; OutCounts = new int[0]; OutIdx = new int[0];
		try
		{
			if (inTri.Count == 0) return "입력 메쉬가 없습니다";
			bool pure = (flags & F_PureQuad) != 0;
			L = edge;
			Prepare(sharpDeg, (flags & F_Sharp) != 0);
			Note(string.Format("입력: 오브젝트 {0}  삼각형 {1}", objCount, nT));
			h = L * VoxelRatio;
			if (!BuildGrid(maxVox <= 0 ? 24000000 : maxVox)) return "격자를 만들 수 없습니다";
			Note(string.Format("격자 {0}x{1}x{2} (칸 {3:0.####})", nx, ny, nz, h));
			ComputeDistance();
			Note("거리장");
			FloodOutside();
			Note("바깥 채우기");
			BuildSurfaceNet();
			Note(string.Format("서피스 넷: 버텍스 {0}  면 {1}", snV.Length, snQ.Length / 4));
			if (snV.Length < 8) return "표면을 찾지 못했습니다 (엣지 길이가 너무 큽니다)";
			D = null; outside = null; // NT 는 투영에 계속 사용
			TagFeatures((flags & F_Sharp) != 0, sharpDeg);
			Note(string.Format("모서리 버텍스 {0}", CountTagged()));
			double scale = L;
			BuildHierarchy();
			Note(string.Format("계층 {0}단계", lv.Count));
			SolveOrientation();
			Note("방향장");
			SolvePosition(scale);
			Note("위치장");
			ExtractMesh(scale);
			Note(string.Format("추출: 버텍스 {0}  면 {1}", mV.Count, mF.Count));
			CleanupMesh();
			if (pure) { MakePureQuads(); CompactVerts(); }
			RemoveSheetBacks((flags & F_KeepBack) == 0);
			Relax();
			Note("이완/투영");
			WriteOutput();
			Note(string.Format("결과: 쿼드 {0}  삼각형 {1}  기타 {2}", OutQuads, OutTris, OutOthers));
			Log = log.ToString();
			return "OK";
		}
		catch (Exception ex)
		{
			Log = log.ToString() + "\n" + ex.ToString();
			return "오류: " + ex.Message;
		}
	}

	void For(int n, Action<int> body)
	{
		if (parallel && n > 1) Parallel.For(0, n, body);
		else for (int i = 0; i < n; i++) body(i);
	}

	// ================================================================ 1. 입력 준비 / 날카로운 엣지
	void Prepare(double sharpDeg, bool sharp)
	{
		int nv = inXYZ.Count / 3;
		P = new RV[nv];
		for (int i = 0; i < nv; i++) P[i] = new RV(inXYZ[i * 3], inXYZ[i * 3 + 1], inXYZ[i * 3 + 2]);
		nT = inTri.Count / 3;
		T = inTri.ToArray();
		TN = new RV[nT];
		for (int t = 0; t < nT; t++)
			TN[t] = (P[T[t * 3 + 1]] - P[T[t * 3]]).Cross(P[T[t * 3 + 2]] - P[T[t * 3]]).Norm();
		triSharp = new byte[nT];
		triOpen = new bool[nT];

		// 엣지 → 면 (오브젝트마다 버텍스가 따로라 섞이지 않음)
		var edgeFaces = new Dictionary<long, int>(nT * 2, LongKey.I);   // 첫 면*4 + 엣지 번호, 두 번째부터는 별도
		var second = new Dictionary<long, int>(LongKey.I);
		var many = new HashSet<long>(LongKey.I);
		for (int t = 0; t < nT; t++)
			for (int k = 0; k < 3; k++)
			{
				int a = T[t * 3 + k], b = T[t * 3 + (k + 1) % 3];
				long key = a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a;
				int prev;
				if (!edgeFaces.TryGetValue(key, out prev)) edgeFaces[key] = t * 4 + k;
				else if (!second.ContainsKey(key)) second[key] = t * 4 + k;
				else many.Add(key);
			}
		var objOpen = new bool[objCount];
		double cosT = Math.Cos(sharpDeg * Math.PI / 180.0);
		// 날카로운 엣지 목록 (선 길이 필터용)
		var sEdges = new List<int>(); // t*4+k
		foreach (var kv in edgeFaces)
		{
			int t0 = kv.Value >> 2, k0 = kv.Value & 3;
			int s;
			bool isSharp = false;
			if (!second.TryGetValue(kv.Key, out s))
			{
				objOpen[inTriObj[t0]] = true;
				isSharp = true; // 열린 경계
			}
			else if (many.Contains(kv.Key)) isSharp = true;
			else
			{
				int t1 = s >> 2;
				double c = TN[t0].Dot(TN[t1]);
				if (c < cosT)
				{
					// 볼록한 모서리만 (안으로 파인 홈은 부푼 껍질에 묻힘)
					int opp = T[t1 * 3 + ((s & 3) + 2) % 3];
					double side = (P[opp] - P[T[t0 * 3 + k0]]).Dot(TN[t0]);
					if (side < 0) isSharp = true;
				}
				if (isSharp) sEdges.Add(s);
			}
			if (isSharp) sEdges.Add(kv.Value);
		}
		for (int t = 0; t < nT; t++) triOpen[t] = objOpen[inTriObj[t]];
		if (!sharp) return;

		// 모서리 선을 이어 짧은 것은 버림 (작은 장식의 잔 모서리가 흐름을 흐트리지 않게)
		var uf = new UF(nv);
		foreach (int e in sEdges)
		{
			int t = e >> 2, k = e & 3;
			uf.Union(T[t * 3 + k], T[t * 3 + (k + 1) % 3]);
		}
		var len = new Dictionary<int, double>();
		foreach (int e in sEdges)
		{
			int t = e >> 2, k = e & 3;
			int a = T[t * 3 + k], b = T[t * 3 + (k + 1) % 3];
			int root = uf.Find(a);
			double l0;
			len.TryGetValue(root, out l0);
			len[root] = l0 + (P[a] - P[b]).Len * 0.5; // 양쪽 면에서 두 번 더해짐
		}
		double minLen = MinCreaseLen * L;
		foreach (int e in sEdges)
		{
			int t = e >> 2, k = e & 3;
			int a = T[t * 3 + k];
			if (len[uf.Find(a)] >= minLen) triSharp[t] |= (byte)(1 << k);
		}
	}

	class UF
	{
		int[] p;
		public UF(int n) { p = new int[n]; for (int i = 0; i < n; i++) p[i] = i; }
		public int Find(int x) { while (p[x] != x) { p[x] = p[p[x]]; x = p[x]; } return x; }
		public void Union(int a, int b) { a = Find(a); b = Find(b); if (a != b) p[a] = b; }
	}

	// ================================================================ 2. 격자 / 거리장
	bool BuildGrid(int maxVox)
	{
		RV mn = new RV(1e300, 1e300, 1e300), mx = new RV(-1e300, -1e300, -1e300);
		foreach (int vi in T)
		{
			RV p = P[vi];
			mn = new RV(Math.Min(mn.X, p.X), Math.Min(mn.Y, p.Y), Math.Min(mn.Z, p.Z));
			mx = new RV(Math.Max(mx.X, p.X), Math.Max(mx.Y, p.Y), Math.Max(mx.Z, p.Z));
		}
		for (int tries = 0; tries < 60; tries++)
		{
			r = h * Dilate;
			double pad = r + h * 3;
			g0 = mn - new RV(pad, pad, pad);
			RV ext = mx - mn + new RV(pad * 2, pad * 2, pad * 2);
			nx = (int)Math.Ceiling(ext.X / h) + 1;
			ny = (int)Math.Ceiling(ext.Y / h) + 1;
			nz = (int)Math.Ceiling(ext.Z / h) + 1;
			if ((double)nx * ny * nz <= maxVox) break;
			double f = Math.Pow((double)nx * ny * nz / maxVox, 1.0 / 3.0) * 1.02;
			h *= f;
		}
		if ((double)nx * ny * nz > maxVox) return false;
		if (h > L * VoxelRatio * 1.001)
			Note(string.Format("  (복셀 수 제한으로 칸을 {0:0.####} 로 키움 — 엣지 길이를 키우면 더 정확)", h));
		return true;
	}

	int Idx(int i, int j, int k) { return i + nx * (j + ny * k); }

	void ComputeDistance()
	{
		int N = nx * ny * nz;
		D = new float[N];
		NT = new int[N];
		double band = r + h * 1.75;
		float big = (float)(band * 4);
		for (int i = 0; i < N; i++) { D[i] = big; NT[i] = -1; }
		// z 방향 조각마다 삼각형을 모아 병렬 처리 (조각끼리 칸이 겹치지 않음)
		int slab = 4;
		int nSlab = (nz + slab - 1) / slab;
		var lists = new List<int>[nSlab];
		for (int s = 0; s < nSlab; s++) lists[s] = new List<int>();
		for (int t = 0; t < nT; t++)
		{
			double z0 = Math.Min(P[T[t * 3]].Z, Math.Min(P[T[t * 3 + 1]].Z, P[T[t * 3 + 2]].Z)) - band;
			double z1 = Math.Max(P[T[t * 3]].Z, Math.Max(P[T[t * 3 + 1]].Z, P[T[t * 3 + 2]].Z)) + band;
			int k0 = Math.Max(0, (int)Math.Ceiling((z0 - g0.Z) / h));
			int k1 = Math.Min(nz - 1, (int)Math.Floor((z1 - g0.Z) / h));
			if (k1 < k0) continue;
			for (int s = k0 / slab; s <= k1 / slab; s++) lists[s].Add(t);
		}
		double band2 = band * band;
		For(nSlab, s =>
		{
			int ks = s * slab, ke = Math.Min(nz - 1, ks + slab - 1);
			foreach (int t in lists[s])
			{
				RV a = P[T[t * 3]], b = P[T[t * 3 + 1]], c = P[T[t * 3 + 2]];
				double x0 = Math.Min(a.X, Math.Min(b.X, c.X)) - band, x1 = Math.Max(a.X, Math.Max(b.X, c.X)) + band;
				double y0 = Math.Min(a.Y, Math.Min(b.Y, c.Y)) - band, y1 = Math.Max(a.Y, Math.Max(b.Y, c.Y)) + band;
				double z0 = Math.Min(a.Z, Math.Min(b.Z, c.Z)) - band, z1 = Math.Max(a.Z, Math.Max(b.Z, c.Z)) + band;
				int i0 = Math.Max(0, (int)Math.Ceiling((x0 - g0.X) / h)), i1 = Math.Min(nx - 1, (int)Math.Floor((x1 - g0.X) / h));
				int j0 = Math.Max(0, (int)Math.Ceiling((y0 - g0.Y) / h)), j1 = Math.Min(ny - 1, (int)Math.Floor((y1 - g0.Y) / h));
				int k0 = Math.Max(ks, (int)Math.Ceiling((z0 - g0.Z) / h)), k1 = Math.Min(ke, (int)Math.Floor((z1 - g0.Z) / h));
				RV n = TN[t];
				for (int k = k0; k <= k1; k++)
					for (int j = j0; j <= j1; j++)
					{
						int row = nx * (j + ny * k);
						for (int i = i0; i <= i1; i++)
						{
							RV p = new RV(g0.X + i * h, g0.Y + j * h, g0.Z + k * h);
							// 평면까지 거리로 먼저 거름
							double pd = (p - a).Dot(n);
							if (pd * pd >= band2) continue;
							int reg;
							RV q = ClosestOnTri(p, a, b, c, out reg);
							double d2 = (p - q).Len2;
							if (d2 < band2)
							{
								float d = (float)Math.Sqrt(d2);
								if (d < D[row + i]) { D[row + i] = d; NT[row + i] = t; }
							}
						}
					}
			}
		});
	}

	// 삼각형 위 가장 가까운 점 (Ericson). reg: 0 면, 1..3 버텍스 a,b,c, 4 ab, 5 bc, 6 ca
	static RV ClosestOnTri(RV p, RV a, RV b, RV c, out int reg)
	{
		RV ab = b - a, ac = c - a, ap = p - a;
		double d1 = ab.Dot(ap), d2 = ac.Dot(ap);
		if (d1 <= 0 && d2 <= 0) { reg = 1; return a; }
		RV bp = p - b;
		double d3 = ab.Dot(bp), d4 = ac.Dot(bp);
		if (d3 >= 0 && d4 <= d3) { reg = 2; return b; }
		double vc = d1 * d4 - d3 * d2;
		if (vc <= 0 && d1 >= 0 && d3 <= 0) { double v = d1 / (d1 - d3); reg = 4; return a + ab * v; }
		RV cp = p - c;
		double d5 = ab.Dot(cp), d6 = ac.Dot(cp);
		if (d6 >= 0 && d5 <= d6) { reg = 3; return c; }
		double vb = d5 * d2 - d1 * d6;
		if (vb <= 0 && d2 >= 0 && d6 <= 0) { double w = d2 / (d2 - d6); reg = 6; return a + ac * w; }
		double va = d3 * d6 - d5 * d4;
		if (va <= 0 && (d4 - d3) >= 0 && (d5 - d6) >= 0)
		{
			double w = (d4 - d3) / ((d4 - d3) + (d5 - d6)); reg = 5; return b + (c - b) * w;
		}
		double den = 1.0 / (va + vb + vc);
		double vv = vb * den, ww = vc * den;
		reg = 0;
		return a + ab * vv + ac * ww;
	}

	void FloodOutside()
	{
		int N = nx * ny * nz;
		outside = new byte[N];
		var q = new Queue<int>();
		float rf = (float)r;
		Action<int> seed = id => { if (outside[id] == 0 && D[id] >= rf) { outside[id] = 1; q.Enqueue(id); } };
		for (int k = 0; k < nz; k++)
			for (int j = 0; j < ny; j++)
			{
				seed(Idx(0, j, k)); seed(Idx(nx - 1, j, k));
			}
		for (int k = 0; k < nz; k++)
			for (int i = 0; i < nx; i++)
			{
				seed(Idx(i, 0, k)); seed(Idx(i, ny - 1, k));
			}
		for (int j = 0; j < ny; j++)
			for (int i = 0; i < nx; i++)
			{
				seed(Idx(i, j, 0)); seed(Idx(i, j, nz - 1));
			}
		int sy = nx, sz = nx * ny;
		while (q.Count > 0)
		{
			int id = q.Dequeue();
			int i = id % nx, j = (id / nx) % ny, k = id / sz;
			if (i > 0) seed(id - 1);
			if (i < nx - 1) seed(id + 1);
			if (j > 0) seed(id - sy);
			if (j < ny - 1) seed(id + sy);
			if (k > 0) seed(id - sz);
			if (k < nz - 1) seed(id + sz);
		}
	}

	// 부푼 껍질의 부호 있는 값 (바깥 +, 안 -)
	float Fv(int id)
	{
		float d = D[id] - (float)r;
		if (outside[id] != 0) return d;
		return d < 0 ? d : (float)(-0.05 * h);
	}

	// ================================================================ 3. 서피스 넷
	RV[] snV; RV[] snN; int[] snQ;

	void BuildSurfaceNet()
	{
		var cellVert = new Dictionary<int, int>();
		var verts = new List<RV>();
		int sy = nx, sz = nx * ny;
		int[] co = { 0, 1, sy, sy + 1, sz, sz + 1, sz + sy, sz + sy + 1 };
		int[,] ed = { { 0, 1 }, { 2, 3 }, { 4, 5 }, { 6, 7 }, { 0, 2 }, { 1, 3 }, { 4, 6 }, { 5, 7 }, { 0, 4 }, { 1, 5 }, { 2, 6 }, { 3, 7 } };
		RV[] cp = new RV[8];
		for (int c = 0; c < 8; c++) cp[c] = new RV(c & 1, (c >> 1) & 1, (c >> 2) & 1);
		// 칸마다 병렬로 버텍스 계산 → 조각별 목록
		int nSlab = nz - 1;
		var sl = new List<KeyValuePair<int, RV>>[nSlab];
		For(nSlab, k =>
		{
			var list = new List<KeyValuePair<int, RV>>();
			float[] f = new float[8];
			for (int j = 0; j < ny - 1; j++)
				for (int i = 0; i < nx - 1; i++)
				{
					int id = i + nx * (j + ny * k);
					int neg = 0;
					for (int c = 0; c < 8; c++) { f[c] = Fv(id + co[c]); if (f[c] < 0) neg++; }
					if (neg == 0 || neg == 8) continue;
					RV s = RV.Zero; int cnt = 0;
					for (int e = 0; e < 12; e++)
					{
						float a = f[ed[e, 0]], b = f[ed[e, 1]];
						if ((a < 0) == (b < 0)) continue;
						double tt = a / (a - b);
						s = s + cp[ed[e, 0]] + (cp[ed[e, 1]] - cp[ed[e, 0]]) * tt;
						cnt++;
					}
					s = s / cnt;
					list.Add(new KeyValuePair<int, RV>(id, new RV(g0.X + (i + s.X) * h, g0.Y + (j + s.Y) * h, g0.Z + (k + s.Z) * h)));
				}
			sl[k] = list;
		});
		foreach (var list in sl)
			foreach (var kv in list) { cellVert[kv.Key] = verts.Count; verts.Add(kv.Value); }
		// 부호가 바뀌는 격자 엣지마다 쿼드
		var quads = new List<int>();
		for (int k = 1; k < nz - 1; k++)
			for (int j = 1; j < ny - 1; j++)
				for (int i = 1; i < nx - 1; i++)
				{
					int id = i + nx * (j + ny * k);
					float f0 = Fv(id);
					bool in0 = f0 < 0;
					// x 방향 엣지 (i,j,k)-(i+1,j,k): 칸 (i,j-1..j,k-1..k)
					if (i < nx - 1 && (Fv(id + 1) < 0) != in0)
						AddQuad(quads, cellVert, id, id - sy, id - sy - sz, id - sz, in0);
					if (j < ny - 1 && (Fv(id + sy) < 0) != in0)
						AddQuad(quads, cellVert, id, id - sz, id - sz - 1, id - 1, in0);
					if (k < nz - 1 && (Fv(id + sz) < 0) != in0)
						AddQuad(quads, cellVert, id, id - 1, id - 1 - sy, id - sy, in0);
				}
		snV = verts.ToArray();
		snQ = quads.ToArray();
		// 법선: 가장 가까운 원래 표면에서 바깥쪽 (없으면 면 법선 평균)
		int n = snV.Length;
		snN = new RV[n];
		var fn = new RV[n];
		for (int q = 0; q < snQ.Length; q += 4)
		{
			RV a = snV[snQ[q]], b = snV[snQ[q + 1]], c = snV[snQ[q + 2]], d = snV[snQ[q + 3]];
			RV nn = (c - a).Cross(d - b);
			for (int m = 0; m < 4; m++) fn[snQ[q + m]] = fn[snQ[q + m]] + nn;
		}
		For(n, v =>
		{
			RV fnv = fn[v].Norm();
			int t; RV cpt; int reg;
			if (Nearest(snV[v], out t, out cpt, out reg))
			{
				RV d = snV[v] - cpt;
				if (d.Len > r * 0.3 && d.Dot(fnv) > 0) { snN[v] = (d.Norm() + fnv).Norm(); return; }
			}
			snN[v] = fnv;
		});
	}

	void AddQuad(List<int> quads, Dictionary<int, int> cv, int c0, int c1, int c2, int c3, bool flip)
	{
		int a, b, c, d;
		if (!cv.TryGetValue(c0, out a) || !cv.TryGetValue(c1, out b) || !cv.TryGetValue(c2, out c) || !cv.TryGetValue(c3, out d)) return;
		if (flip) { quads.Add(a); quads.Add(b); quads.Add(c); quads.Add(d); }
		else { quads.Add(d); quads.Add(c); quads.Add(b); quads.Add(a); }
	}

	// 점에서 가장 가까운 원래 표면 (주변 칸에 기록된 가까운 삼각형들 중)
	bool Nearest(RV p, out int bestT, out RV bestP, out int bestReg)
	{
		bestT = -1; bestP = p; bestReg = 0;
		int ci = (int)Math.Round((p.X - g0.X) / h), cj = (int)Math.Round((p.Y - g0.Y) / h), ck = (int)Math.Round((p.Z - g0.Z) / h);
		double best = double.MaxValue;
		for (int rad = 1; rad <= 3; rad++)
		{
			for (int dk = -rad; dk <= rad; dk++)
				for (int dj = -rad; dj <= rad; dj++)
					for (int di = -rad; di <= rad; di++)
					{
						if (rad > 1 && Math.Abs(di) < rad && Math.Abs(dj) < rad && Math.Abs(dk) < rad) continue;
						int i = ci + di, j = cj + dj, k = ck + dk;
						if (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) continue;
						int t = NT[Idx(i, j, k)];
						if (t < 0 || t == bestT) continue;
						int reg;
						RV q = ClosestOnTri(p, P[T[t * 3]], P[T[t * 3 + 1]], P[T[t * 3 + 2]], out reg);
						double d2 = (p - q).Len2;
						if (d2 < best) { best = d2; bestT = t; bestP = q; bestReg = reg; }
					}
			if (bestT >= 0) break;
		}
		return bestT >= 0;
	}

	// ================================================================ 모서리 표시
	// ctag: 0 없음, 1 모서리 선(방향 cdir, 선 위 점 cpos), 2 꼭짓점(cpos)
	byte[] ctag; RV[] cdir; RV[] cpos; RV[] cpt;

	int CountTagged() { int c = 0; foreach (byte b in ctag) if (b != 0) c++; return c; }

	// 삼각형 엣지 k 가 날카로운지
	bool SharpEdge(int t, int k) { return (triSharp[t] & (1 << k)) != 0; }

	void TagFeatures(bool sharp, double sharpDeg)
	{
		int n = snV.Length;
		ctag = new byte[n]; cdir = new RV[n]; cpos = new RV[n]; cpt = new RV[n];
		if (!sharp) return;
		double near = h * 0.35;
		For(n, v =>
		{
			int t; RV q; int reg;
			if (!Nearest(snV[v], out t, out q, out reg)) return;
			// 가장 가까운 점이 날카로운 엣지 위 / 가까이 있으면 모서리 버텍스
			int bestK = -1; double bestD = near;
			for (int k = 0; k < 3; k++)
			{
				if (!SharpEdge(t, k)) continue;
				RV a = P[T[t * 3 + k]], b = P[T[t * 3 + (k + 1) % 3]];
				double d = SegDist(q, a, b);
				if (d < bestD) { bestD = d; bestK = k; }
			}
			if (bestK < 0) return;
			RV ea = P[T[t * 3 + bestK]], eb = P[T[t * 3 + (bestK + 1) % 3]];
			RV dir = (eb - ea).Norm();
			RV nrm = snN[v];
			RV td = dir - nrm * dir.Dot(nrm);
			if (td.Len < 0.3) return; // 모서리가 법선 방향 (구석) → 무시
			ctag[v] = 1;
			cdir[v] = td.Norm();
			RV cp = ClosestOnSeg(q, ea, eb);
			// 껍질(탄젠트 평면) 위로 옮긴 모서리 점
			cpos[v] = cp + nrm * (snV[v] - cp).Dot(nrm);
		});
		BuildSnAdj();
		// 엣지 길이 규모에서 선처럼 이어지고 방향이 고른 모서리만 (잔 장식이 뭉친 곳은 버림)
		int rings = Math.Max(2, (int)Math.Round(0.7 * L / h));
		double shellCos = Math.Cos(Math.Min(sharpDeg, 80) * Math.PI / 180.0);
		var keep = new bool[n];
		For(n, v =>
		{
			if (ctag[v] == 0) return;
			var ring = Ring(v, rings);
			int tagged = 0;
			double xx = 0, yy = 0, zz = 0, xy = 0, xz = 0, yz = 0;
			foreach (int w in ring)
			{
				if (ctag[w] == 0) continue;
				tagged++;
				RV d = cdir[w];
				xx += d.X * d.X; yy += d.Y * d.Y; zz += d.Z * d.Z; xy += d.X * d.Y; xz += d.X * d.Z; yz += d.Y * d.Z;
			}
			double frac = (double)tagged / ring.Count;
			// 합친 껍질 자체가 그 자리에서 꺾여야 함 (겹친 판 사이의 작은 턱은 무시)
			double minDot = 1;
			foreach (int w in ring) minDot = Math.Min(minDot, snN[v].Dot(snN[w]));
			if (minDot > shellCos) return;
			// 가장 큰 고유값 (거듭제곱법) / 전체 → 방향이 고른 정도
			RV e = cdir[v];
			for (int it = 0; it < 8; it++)
			{
				e = new RV(xx * e.X + xy * e.Y + xz * e.Z, xy * e.X + yy * e.Y + yz * e.Z, xz * e.X + yz * e.Y + zz * e.Z).Norm();
			}
			RV me = new RV(xx * e.X + xy * e.Y + xz * e.Z, xy * e.X + yy * e.Y + yz * e.Z, xz * e.X + yz * e.Y + zz * e.Z);
			double coh = me.Len / Math.Max(1e-12, xx + yy + zz);
			keep[v] = frac < 0.6 && coh > 0.8;
		});
		for (int v = 0; v < n; v++) if (!keep[v]) ctag[v] = 0;
		// 꼭짓점: 모서리 선이 크게 꺾이는 곳에서 가장 가까운 버텍스
		FindCorners();
		foreach (RV c in corners)
		{
			// 가까운 버텍스 (꼭짓점 수가 적어 전체에서 찾음), 주변에 살아남은 모서리 버텍스가 있어야 함
			int best = -1; double bd = (r + h * 1.5) * (r + h * 1.5);
			int support = 0; double sr2 = (L * 0.6) * (L * 0.6);
			for (int v = 0; v < n; v++)
			{
				double d2 = (snV[v] - c).Len2;
				if (d2 < bd) { bd = d2; best = v; }
				if (d2 < sr2 && ctag[v] == 1) support++;
			}
			if (best < 0 || support < 3) continue;
			ctag[best] = 2;
			cpt[best] = c;
			RV nn = snN[best];
			cpos[best] = c + nn * (snV[best] - c).Dot(nn);
		}
		// 외톨이 모서리 버텍스 (이웃에 모서리가 없음) 는 잡음
		var lone = new bool[n];
		for (int v = 0; v < n; v++)
		{
			if (ctag[v] != 1) continue;
			bool any = false;
			for (int e = snAdjS[v]; e < snAdjS[v + 1]; e++) if (ctag[snAdj[e]] != 0) { any = true; break; }
			if (!any) lone[v] = true;
		}
		for (int v = 0; v < n; v++) if (lone[v]) ctag[v] = 0;
	}

	static double SegDist(RV p, RV a, RV b) { return (p - ClosestOnSeg(p, a, b)).Len; }
	static RV ClosestOnSeg(RV p, RV a, RV b)
	{
		RV ab = b - a;
		double l2 = ab.Len2;
		if (l2 < 1e-30) return a;
		double t = Math.Max(0, Math.Min(1, (p - a).Dot(ab) / l2));
		return a + ab * t;
	}

	// 입력의 날카로운 엣지 선에서 엣지 길이 규모로 크게 꺾이는 점 (날개 끝 같은 곳)
	List<RV> corners = new List<RV>();
	void FindCorners()
	{
		corners.Clear();
		var nbr = new Dictionary<int, List<int>>();
		for (int t = 0; t < nT; t++)
		{
			if (triSharp[t] == 0) continue;
			for (int k = 0; k < 3; k++)
			{
				if (!SharpEdge(t, k)) continue;
				int a = T[t * 3 + k], b = T[t * 3 + (k + 1) % 3];
				List<int> la, lb;
				if (!nbr.TryGetValue(a, out la)) nbr[a] = la = new List<int>();
				if (!nbr.TryGetValue(b, out lb)) nbr[b] = lb = new List<int>();
				if (!la.Contains(b)) la.Add(b);
				if (!lb.Contains(a)) lb.Add(a);
			}
		}
		double reach = L * 0.45;
		var cand = new List<KeyValuePair<double, int>>();
		foreach (var kv in nbr)
		{
			int v = kv.Key;
			var l = kv.Value;
			if (l.Count >= 3) { cand.Add(new KeyValuePair<double, int>(-2, v)); continue; }
			if (l.Count != 2) continue;
			RV a = Walk(nbr, v, l[0], reach), b = Walk(nbr, v, l[1], reach);
			RV da = a - P[v], db = b - P[v];
			if (da.Len < reach * 0.5 || db.Len < reach * 0.5) continue;
			double c = da.Norm().Dot(db.Norm());  // -1 곧음, 1 완전히 접힘
			if (c > -0.45) cand.Add(new KeyValuePair<double, int>(-c, v));
		}
		// 가장 뾰족한 것부터, 가까운 후보는 하나만
		cand.Sort((x, y) => x.Key.CompareTo(y.Key));
		double sep = L * 0.8;
		foreach (var c in cand)
		{
			RV p = P[c.Value];
			bool close = false;
			foreach (RV q in corners) if ((q - p).Len < sep) { close = true; break; }
			if (!close) corners.Add(p);
		}
	}

	// 모서리 선을 따라 거리 len 만큼 간 점
	RV Walk(Dictionary<int, List<int>> nbr, int from, int to, double len)
	{
		int prev = from, cur = to;
		double acc = (P[to] - P[from]).Len;
		int guard = 0;
		while (acc < len && guard++ < 10000)
		{
			var l = nbr[cur];
			if (l.Count != 2) break;
			int nxt = l[0] == prev ? l[1] : l[0];
			double sl = (P[nxt] - P[cur]).Len;
			if (acc + sl > len)
			{
				return P[cur] + (P[nxt] - P[cur]) * ((len - acc) / Math.Max(sl, 1e-12));
			}
			acc += sl; prev = cur; cur = nxt;
		}
		return P[cur];
	}

	// k 고리 안의 버텍스
	List<int> Ring(int v, int k)
	{
		var res = new List<int> { v };
		var seen = new HashSet<int> { v };
		int s = 0;
		for (int ring = 0; ring < k; ring++)
		{
			int e0 = res.Count;
			for (int i = s; i < e0; i++)
			{
				int a = res[i];
				for (int e = snAdjS[a]; e < snAdjS[a + 1]; e++)
					if (seen.Add(snAdj[e])) res.Add(snAdj[e]);
			}
			s = e0;
		}
		return res;
	}

	int[] snAdjS, snAdj;
	void BuildSnAdj()
	{
		if (snAdjS != null) return;
		int n = snV.Length;
		var lists = new List<int>[n];
		for (int i = 0; i < n; i++) lists[i] = new List<int>(4);
		for (int q = 0; q < snQ.Length; q += 4)
			for (int m = 0; m < 4; m++)
			{
				int a = snQ[q + m], b = snQ[q + (m + 1) % 4];
				if (a == b) continue;
				if (!lists[a].Contains(b)) lists[a].Add(b);
				if (!lists[b].Contains(a)) lists[b].Add(a);
			}
		snAdjS = new int[n + 1];
		for (int i = 0; i < n; i++) snAdjS[i + 1] = snAdjS[i] + lists[i].Count;
		snAdj = new int[snAdjS[n]];
		for (int i = 0; i < n; i++) lists[i].CopyTo(snAdj, snAdjS[i]);
	}

	// ================================================================ 4. 계층 (Instant Meshes)
	class Level
	{
		public int n;
		public RV[] V, N, Q, O, CQ, CO;
		public double[] A;
		public byte[] C;
		public int[] adjS, adj;
		public int[] up;          // 한 단계 위(성긴 단계) 버텍스
		public List<int[]> colors;
	}
	List<Level> lv = new List<Level>();

	void BuildHierarchy()
	{
		BuildSnAdj();
		int n = snV.Length;
		var l0 = new Level { n = n, V = snV, N = snN, A = new double[n], C = ctag, CQ = cdir, CO = cpos, adjS = snAdjS, adj = snAdj };
		for (int q = 0; q < snQ.Length; q += 4)
		{
			RV a = snV[snQ[q]], b = snV[snQ[q + 1]], c = snV[snQ[q + 2]], d = snV[snQ[q + 3]];
			double ar = (c - a).Cross(d - b).Len * 0.5;
			for (int m = 0; m < 4; m++) l0.A[snQ[q + m]] += ar * 0.25;
		}
		for (int i = 0; i < n; i++) if (l0.A[i] <= 0) l0.A[i] = h * h * 0.25;
		lv.Clear();
		lv.Add(l0);
		while (lv[lv.Count - 1].n > 64 && lv.Count < 30)
		{
			var c = Coarsen(lv[lv.Count - 1]);
			if (c.n > lv[lv.Count - 1].n * 0.85) break;
			lv.Add(c);
		}
		foreach (var l in lv) l.colors = ColorGraph(l);
	}

	Level Coarsen(Level f)
	{
		int n = f.n;
		// 이웃 쌍 점수: 법선이 비슷하고 면적이 비슷할수록 먼저 합침
		var pairs = new List<KeyValuePair<double, long>>(f.adj.Length / 2);
		for (int i = 0; i < n; i++)
			for (int e = f.adjS[i]; e < f.adjS[i + 1]; e++)
			{
				int j = f.adj[e];
				if (j <= i) continue;
				double dp = f.N[i].Dot(f.N[j]);
				double ratio = Math.Max(f.A[i] / f.A[j], f.A[j] / f.A[i]);
				// 모서리 버텍스와 일반 버텍스는 되도록 합치지 않음
				double pen = (f.C[i] != 0) != (f.C[j] != 0) ? 0.5 : 1.0;
				pairs.Add(new KeyValuePair<double, long>(-dp / ratio * pen, ((long)i << 32) | (uint)j));
			}
		pairs.Sort((x, y) => x.Key.CompareTo(y.Key));
		var up = new int[n];
		for (int i = 0; i < n; i++) up[i] = -1;
		int m = 0;
		var members = new List<int>(n);
		var cl = new List<int[]>();
		foreach (var pr in pairs)
		{
			int i = (int)(pr.Value >> 32), j = (int)(pr.Value & 0xffffffff);
			if (up[i] >= 0 || up[j] >= 0) continue;
			if (f.N[i].Dot(f.N[j]) < 0) continue;
			up[i] = up[j] = m++;
			cl.Add(new[] { i, j });
		}
		for (int i = 0; i < n; i++) if (up[i] < 0) { up[i] = m++; cl.Add(new[] { i }); }
		var c = new Level { n = m, V = new RV[m], N = new RV[m], A = new double[m], C = new byte[m], CQ = new RV[m], CO = new RV[m] };
		for (int k = 0; k < m; k++)
		{
			RV v = RV.Zero, nn = RV.Zero; double a = 0;
			int best = -1;
			foreach (int i in cl[k])
			{
				v = v + f.V[i] * f.A[i]; nn = nn + f.N[i] * f.A[i]; a += f.A[i];
				if (f.C[i] != 0 && (best < 0 || f.C[i] > f.C[best])) best = i;
			}
			c.V[k] = v / a; c.N[k] = nn.Norm(); c.A[k] = a;
			if (c.N[k].Len2 == 0) c.N[k] = f.N[cl[k][0]];
			if (best >= 0)
			{
				c.C[k] = f.C[best];
				RV d = f.CQ[best] - c.N[k] * f.CQ[best].Dot(c.N[k]);
				c.CQ[k] = d.Norm();
				c.CO[k] = f.CO[best];
				if (c.C[k] == 1 && c.CQ[k].Len2 == 0) c.C[k] = 0;
			}
		}
		// 성긴 단계 이웃
		var lists = new HashSet<int>[m];
		for (int k = 0; k < m; k++) lists[k] = new HashSet<int>();
		for (int i = 0; i < n; i++)
			for (int e = f.adjS[i]; e < f.adjS[i + 1]; e++)
			{
				int a = up[i], b = up[f.adj[e]];
				if (a != b) { lists[a].Add(b); lists[b].Add(a); }
			}
		c.adjS = new int[m + 1];
		for (int k = 0; k < m; k++) c.adjS[k + 1] = c.adjS[k] + lists[k].Count;
		c.adj = new int[c.adjS[m]];
		for (int k = 0; k < m; k++) lists[k].CopyTo(c.adj, c.adjS[k]);
		f.up = up;
		return c;
	}

	static List<int[]> ColorGraph(Level l)
	{
		var col = new int[l.n];
		for (int i = 0; i < l.n; i++) col[i] = -1;
		int maxC = 0;
		var used = new List<bool>();
		for (int i = 0; i < l.n; i++)
		{
			used.Clear();
			for (int e = l.adjS[i]; e < l.adjS[i + 1]; e++)
			{
				int c = col[l.adj[e]];
				if (c < 0) continue;
				while (used.Count <= c) used.Add(false);
				used[c] = true;
			}
			int k = 0;
			while (k < used.Count && used[k]) k++;
			col[i] = k;
			if (k + 1 > maxC) maxC = k + 1;
		}
		var groups = new List<int>[maxC];
		for (int c = 0; c < maxC; c++) groups[c] = new List<int>();
		for (int i = 0; i < l.n; i++) groups[col[i]].Add(i);
		var res = new List<int[]>();
		foreach (var g in groups) res.Add(g.ToArray());
		return res;
	}

	// ---------------------------------------------------------------- 4-RoSy 방향장
	static void CompatOrient(RV q0, RV n0, RV q1, RV n1, out RV a, out RV b)
	{
		RV t0 = n0.Cross(q0), t1 = n1.Cross(q1);
		double s00 = q0.Dot(q1), s01 = q0.Dot(t1), s10 = t0.Dot(q1), s11 = t0.Dot(t1);
		double best = Math.Abs(s00); a = q0; b = q1; double dp = s00;
		if (Math.Abs(s01) > best) { best = Math.Abs(s01); a = q0; b = t1; dp = s01; }
		if (Math.Abs(s10) > best) { best = Math.Abs(s10); a = t0; b = q1; dp = s10; }
		if (Math.Abs(s11) > best) { best = Math.Abs(s11); a = t0; b = t1; dp = s11; }
		if (dp < 0) b = -b;
	}

	static void CompatOrientIndex(RV q0, RV n0, RV q1, RV n1, out int ia, out int ib)
	{
		RV t0 = n0.Cross(q0), t1 = n1.Cross(q1);
		double[] s = { q0.Dot(q1), q0.Dot(t1), t0.Dot(q1), t0.Dot(t1) };
		int best = 0;
		for (int k = 1; k < 4; k++) if (Math.Abs(s[k]) > Math.Abs(s[best])) best = k;
		ia = best >> 1; ib = best & 1;
		if (s[best] < 0) ib += 2;
	}

	void SolveOrientation()
	{
		var rnd = new Random(1234);
		var top = lv[lv.Count - 1];
		top.Q = new RV[top.n];
		for (int i = 0; i < top.n; i++)
		{
			RV n = top.N[i];
			RV q = new RV(rnd.NextDouble() - 0.5, rnd.NextDouble() - 0.5, rnd.NextDouble() - 0.5);
			q = q - n * q.Dot(n);
			if (q.Len2 < 1e-12) q = Perp(n);
			top.Q[i] = q.Norm();
		}
		for (int li = lv.Count - 1; li >= 0; li--)
		{
			var l = lv[li];
			if (li < lv.Count - 1)
			{
				var c = lv[li + 1];
				l.Q = new RV[l.n];
				for (int i = 0; i < l.n; i++)
				{
					RV q = c.Q[l.up[i]];
					RV n = l.N[i];
					q = q - n * q.Dot(n);
					if (q.Len2 < 1e-12) q = Perp(n);
					l.Q[i] = q.Norm();
				}
			}
			ApplyOrientConstraints(l);
			int iters = li == 0 ? OrientIters : OrientIters + 4;
			for (int it = 0; it < iters; it++)
				foreach (var grp in l.colors)
				{
					var g = grp;
					For(g.Length, gi =>
					{
						int i = g[gi];
						if (l.C[i] != 0) return;
						RV n = l.N[i];
						RV sum = l.Q[i];
						double ws = 0;
						for (int e = l.adjS[i]; e < l.adjS[i + 1]; e++)
						{
							int j = l.adj[e];
							double w = 1;
							RV a, b;
							CompatOrient(sum, n, l.Q[j], l.N[j], out a, out b);
							sum = a * ws + b * w;
							sum = sum - n * n.Dot(sum);
							double len = sum.Len;
							if (len > 1e-20) sum = sum / len;
							ws += w;
						}
						if (ws > 0 && sum.Len2 > 0) l.Q[i] = sum;
					});
				}
		}
	}

	void ApplyOrientConstraints(Level l)
	{
		for (int i = 0; i < l.n; i++)
		{
			if (l.C[i] == 1) l.Q[i] = l.CQ[i];
		}
		// 꼭짓점: 이웃 모서리 방향 중 하나를 따름 (다음 반복에서 자유롭게 두지 않음)
		for (int i = 0; i < l.n; i++)
		{
			if (l.C[i] != 2) continue;
			for (int e = l.adjS[i]; e < l.adjS[i + 1]; e++)
			{
				int j = l.adj[e];
				if (l.C[j] == 1) { RV q = l.CQ[j] - l.N[i] * l.CQ[j].Dot(l.N[i]); if (q.Len2 > 1e-12) { l.Q[i] = q.Norm(); break; } }
			}
		}
	}

	static RV Perp(RV n)
	{
		RV a = Math.Abs(n.X) < 0.9 ? new RV(1, 0, 0) : new RV(0, 1, 0);
		return (a - n * a.Dot(n)).Norm();
	}

	// ---------------------------------------------------------------- 위치장
	static RV MiddlePoint(RV p0, RV n0, RV p1, RV n1)
	{
		double n0p0 = n0.Dot(p0), n0p1 = n0.Dot(p1), n1p0 = n1.Dot(p0), n1p1 = n1.Dot(p1), n0n1 = n0.Dot(n1);
		double denom = 1.0 / (1.0 - n0n1 * n0n1 + 1e-4);
		double l0 = 2 * (n0p1 - n0p0 - n0n1 * (n1p0 - n1p1)) * denom;
		double l1 = 2 * (n1p0 - n1p1 - n0n1 * (n0p1 - n0p0)) * denom;
		return (p0 + p1) * 0.5 - (n0 * l0 + n1 * l1) * 0.25;
	}

	static RV PosFloor(RV o, RV q, RV n, RV p, double s, double inv, out int fi, out int fj)
	{
		RV t = n.Cross(q), d = p - o;
		fi = (int)Math.Floor(q.Dot(d) * inv); fj = (int)Math.Floor(t.Dot(d) * inv);
		return o + q * (fi * s) + t * (fj * s);
	}

	static RV PosRound(RV o, RV q, RV n, RV p, double s, double inv)
	{
		RV t = n.Cross(q), d = p - o;
		return o + q * (Math.Round(q.Dot(d) * inv) * s) + t * (Math.Round(t.Dot(d) * inv) * s);
	}

	static void CompatPos(RV p0, RV n0, RV q0, RV o0, RV p1, RV n1, RV q1, RV o1, double s, double inv,
		out RV ra, out RV rb, out int ai, out int aj, out int bi, out int bj, out double err)
	{
		RV t0 = n0.Cross(q0), t1 = n1.Cross(q1);
		RV mid = MiddlePoint(p0, n0, p1, n1);
		int fi0, fj0, fi1, fj1;
		RV o0p = PosFloor(o0, q0, n0, mid, s, inv, out fi0, out fj0);
		RV o1p = PosFloor(o1, q1, n1, mid, s, inv, out fi1, out fj1);
		double best = double.MaxValue; int bi0 = 0, bj0 = 0;
		RV qs0 = q0 * s, ts0 = t0 * s, qs1 = q1 * s, ts1 = t1 * s;
		for (int i = 0; i < 4; i++)
		{
			RV a = o0p + qs0 * (i & 1) + ts0 * ((i & 2) >> 1);
			for (int j = 0; j < 4; j++)
			{
				RV b = o1p + qs1 * (j & 1) + ts1 * ((j & 2) >> 1);
				double c = (a - b).Len2;
				if (c < best) { best = c; bi0 = i; bj0 = j; }
			}
		}
		ra = o0p + qs0 * (bi0 & 1) + ts0 * ((bi0 & 2) >> 1);
		rb = o1p + qs1 * (bj0 & 1) + ts1 * ((bj0 & 2) >> 1);
		ai = fi0 + (bi0 & 1); aj = fj0 + ((bi0 & 2) >> 1);
		bi = fi1 + (bj0 & 1); bj = fj1 + ((bj0 & 2) >> 1);
		err = best;
	}

	void SolvePosition(double scale)
	{
		double inv = 1.0 / scale;
		var top = lv[lv.Count - 1];
		top.O = new RV[top.n];
		for (int i = 0; i < top.n; i++) top.O[i] = top.V[i];
		for (int li = lv.Count - 1; li >= 0; li--)
		{
			var l = lv[li];
			if (li < lv.Count - 1)
			{
				var c = lv[li + 1];
				l.O = new RV[l.n];
				for (int i = 0; i < l.n; i++)
				{
					RV o = c.O[l.up[i]];
					o = o - l.N[i] * l.N[i].Dot(o - l.V[i]);
					l.O[i] = o;
				}
			}
			for (int i = 0; i < l.n; i++) l.O[i] = ConstrainPos(l, i, PosRound(l.O[i], l.Q[i], l.N[i], l.V[i], scale, inv), scale, inv);
			int iters = li == 0 ? PosIters : PosIters + 4;
			for (int it = 0; it < iters; it++)
				foreach (var grp in l.colors)
				{
					var g = grp;
					For(g.Length, gi =>
					{
						int i = g[gi];
						RV n = l.N[i], v = l.V[i], q = l.Q[i];
						RV sum = l.O[i];
						double ws = 0;
						for (int e = l.adjS[i]; e < l.adjS[i + 1]; e++)
						{
							int j = l.adj[e];
							double w = 1;
							RV a, b; int x0, y0, x1, y1; double err;
							CompatPos(v, n, q, sum, l.V[j], l.N[j], l.Q[j], l.O[j], scale, inv, out a, out b, out x0, out y0, out x1, out y1, out err);
							sum = a * ws + b * w;
							ws += w;
							if (ws > 1e-20) sum = sum / ws;
							sum = sum - n * n.Dot(sum - v);
						}
						if (ws > 0) l.O[i] = ConstrainPos(l, i, PosRound(sum, q, n, v, scale, inv), scale, inv);
					});
				}
		}
	}

	RV ConstrainPos(Level l, int i, RV o, double s, double inv)
	{
		if (l.C[i] == 0) return o;
		RV n = l.N[i], q = l.Q[i], cp = l.CO[i];
		cp = cp - n * n.Dot(cp - l.V[i]);
		if (l.C[i] == 2)
		{
			// 꼭짓점: 격자점을 꼭짓점에
			return cp;
		}
		// 모서리 선: 방향 q 의 격자선이 모서리 점을 지나도록
		RV t = n.Cross(q);
		o = o - t * t.Dot(o - cp);
		return o;
	}

	// ================================================================ 5. 추출
	List<RV> mV = new List<RV>();
	List<RV> mN = new List<RV>();
	List<byte> mC = new List<byte>();      // 모서리 (1 선, 2 꼭짓점)
	List<RV> mCP = new List<RV>();         // 꼭짓점 위치
	List<int[]> mF = new List<int[]>();

	void ExtractMesh(double scale)
	{
		var l = lv[0];
		int n = l.n;
		double inv = 1.0 / scale;
		var uf = new UF(n);
		var edges = new List<long>();
		for (int i = 0; i < n; i++)
			for (int e = l.adjS[i]; e < l.adjS[i + 1]; e++)
			{
				int j = l.adj[e];
				if (j <= i) continue;
				int ra, rb;
				CompatOrientIndex(l.Q[i], l.N[i], l.Q[j], l.N[j], out ra, out rb);
				RV a, b; int x0, y0, x1, y1; double err;
				CompatPos(l.V[i], l.N[i], l.Q[i], l.O[i], l.V[j], l.N[j], l.Q[j], l.O[j], scale, inv, out a, out b, out x0, out y0, out x1, out y1, out err);
				// j 틀의 정수 좌표를 i 틀로 회전: q_j = rot_i(ra - rb)
				int k = ((ra - rb) % 4 + 4) % 4;
				int u = x1, w = y1;
				for (int s = 0; s < k; s++) { int tmp = u; u = -w; w = tmp; }
				int dx = x0 - u, dy = y0 - w;
				int ad = Math.Abs(dx) + Math.Abs(dy);
				if (ad == 0) uf.Union(i, j);
				else if (ad == 1) edges.Add(((long)i << 32) | (uint)j);
			}
		// 합친 버텍스
		var id = new int[n];
		for (int i = 0; i < n; i++) id[i] = -1;
		mV.Clear(); mN.Clear(); mC.Clear(); mCP.Clear(); mF.Clear();
		var wsum = new List<double>();
		for (int i = 0; i < n; i++)
		{
			int rt = uf.Find(i);
			if (id[rt] < 0) { id[rt] = mV.Count; mV.Add(RV.Zero); mN.Add(RV.Zero); mC.Add(0); mCP.Add(RV.Zero); wsum.Add(0); }
			int m = id[rt];
			id[i] = m;
			mV[m] = mV[m] + l.O[i] * l.A[i];
			mN[m] = mN[m] + l.N[i] * l.A[i];
			wsum[m] += l.A[i];
			if (l.C[i] > mC[m]) mC[m] = l.C[i];
			if (l.C[i] == 2) mCP[m] = cpt[i];
		}
		for (int m = 0; m < mV.Count; m++) { mV[m] = mV[m] / wsum[m]; mN[m] = mN[m].Norm(); }
		// 엣지
		var adj = new List<HashSet<int>>();
		for (int m = 0; m < mV.Count; m++) adj.Add(new HashSet<int>());
		foreach (long e in edges)
		{
			int a = id[(int)(e >> 32)], b = id[(int)(e & 0xffffffff)];
			if (a == b) continue;
			adj[a].Add(b); adj[b].Add(a);
		}
		// 너무 긴 엣지 제거 (다른 면이나 반대편으로 건너간 연결)
		for (int a = 0; a < mV.Count; a++)
		{
			var rm = new List<int>();
			foreach (int b in adj[a])
				if ((mV[a] - mV[b]).Len > scale * 1.9 || mN[a].Dot(mN[b]) < -0.2) rm.Add(b);
			foreach (int b in rm) { adj[a].Remove(b); adj[b].Remove(a); }
		}
		madj = adj;
		TraceFaces();
	}

	List<HashSet<int>> madj;

	// 버텍스마다 이웃을 탄젠트 평면에서 각도 순으로 정렬해 면을 따라감
	void TraceFaces()
	{
		int n = mV.Count;
		var order = new int[n][];
		for (int v = 0; v < n; v++)
		{
			RV nn = mN[v];
			RV ax = Perp(nn), ay = nn.Cross(ax);
			var nb = new List<int>(madj[v]);
			var ang = new double[nb.Count];
			for (int k = 0; k < nb.Count; k++)
			{
				RV d = mV[nb[k]] - mV[v];
				ang[k] = Math.Atan2(d.Dot(ay), d.Dot(ax));
			}
			var arr = nb.ToArray();
			Array.Sort(ang, arr);
			order[v] = arr;
		}
		// 반엣지 방문 표시
		var visited = new HashSet<long>(LongKey.I);
		mF.Clear();
		for (int v = 0; v < n; v++)
			foreach (int w0 in order[v])
			{
				long key0 = ((long)v << 32) | (uint)w0;
				if (visited.Contains(key0)) continue;
				var face = new List<int>();
				int a = v, b = w0;
				bool ok = true;
				while (true)
				{
					long key = ((long)a << 32) | (uint)b;
					if (visited.Contains(key)) { ok = key == key0; break; }
					visited.Add(key);
					face.Add(a);
					if (face.Count > 24) { ok = false; break; }
					// b 에서 a 다음(시계 방향으로 한 칸 전) 이웃
					int[] ob = order[b];
					int ix = Array.IndexOf(ob, a);
					int c = ob[(ix - 1 + ob.Length) % ob.Length];
					a = b; b = c;
				}
				if (ok && face.Count >= 3) mF.Add(face.ToArray());
			}
	}

	// ================================================================ 6. 정리
	void CleanupMesh()
	{
		// 가장 큰 면(외곽 루프 역할) 을 거름: 버텍스 8개 초과인 면은 구멍으로 보고 나중에 채움
		var faces = new List<int[]>();
		int big = 0;
		foreach (var f in mF)
		{
			if (f.Length > 8) { big++; faces.Add(f); continue; }
			faces.Add(f);
		}
		mF = faces;
		// 방향 확인: 면 법선이 버텍스 법선과 반대면 전부 뒤집기
		double agree = 0;
		foreach (var f in mF) agree += FaceNormal(f).Dot(mN[f[0]]);
		if (agree < 0) foreach (var f in mF) Array.Reverse(f);
		RemoveValence2();
		FillHoles();
		MergeTriangles();
		CompactVerts();
	}

	// ---------------------------------------------------------------- 구멍 채우기
	// 한 면에만 붙은 엣지들을 이어 루프를 만들고 n각형으로 막음 (나중에 쿼드로 나눔)
	void FillHoles()
	{
		var next = new Dictionary<int, List<int>>();
		var ec = EdgeFaceCount();
		foreach (var f in mF)
			for (int k = 0; k < f.Length; k++)
			{
				int a = f[k], b = f[(k + 1) % f.Length];
				if (ec[EKey(a, b)] != 1) continue;
				// 구멍 쪽에서 보면 b→a 방향
				List<int> l;
				if (!next.TryGetValue(b, out l)) next[b] = l = new List<int>();
				l.Add(a);
			}
		var used = new HashSet<long>(LongKey.I);
		int filled = 0;
		foreach (var kv in next)
			foreach (int first in kv.Value)
			{
				int s = kv.Key;
				if (used.Contains(EKey(s, first))) continue;
				var loop = new List<int> { s };
				int cur = first, prev = s;
				bool ok = false;
				used.Add(EKey(s, first));
				while (loop.Count < 64)
				{
					if (cur == s) { ok = true; break; }
					loop.Add(cur);
					List<int> l;
					if (!next.TryGetValue(cur, out l)) break;
					int pick = -1;
					foreach (int w in l) if (!used.Contains(EKey(cur, w))) { pick = w; break; }
					if (pick < 0) break;
					used.Add(EKey(cur, pick));
					prev = cur; cur = pick;
				}
				if (!ok || loop.Count < 3) continue;
				// 루프에 같은 버텍스가 두 번 나오면 막지 않음
				if (new HashSet<int>(loop).Count != loop.Count) continue;
				mF.Add(loop.ToArray());
				filled++;
			}
		if (filled > 0) Note(string.Format("구멍 {0}개 채움", filled));
	}

	Dictionary<long, int> EdgeFaceCount()
	{
		var ec = new Dictionary<long, int>(LongKey.I);
		foreach (var f in mF)
			for (int k = 0; k < f.Length; k++)
			{
				long key = EKey(f[k], f[(k + 1) % f.Length]);
				int c; ec.TryGetValue(key, out c); ec[key] = c + 1;
			}
		return ec;
	}

	// ---------------------------------------------------------------- 전부 쿼드로
	// 홀수 면(삼각형·오각형…)끼리 쿼드 띠를 따라 이어 그 길의 엣지에 중점을 넣으면 모든 면이 짝수 → 쿼드로 나눔
	void MakePureQuads()
	{
		int nf = mF.Count;
		var edgeFaces = new Dictionary<long, int[]>(LongKey.I);
		for (int fi = 0; fi < nf; fi++)
		{
			var f = mF[fi];
			for (int k = 0; k < f.Length; k++)
			{
				long key = EKey(f[k], f[(k + 1) % f.Length]);
				int[] l;
				if (!edgeFaces.TryGetValue(key, out l)) edgeFaces[key] = new[] { fi, -1, 0 };
				else if (l[1] < 0) l[1] = fi;
				else l[2] = 1; // 세 면 이상 (비다양체): 지나가지 않음
			}
		}
		var odd = new List<int>();
		for (int fi = 0; fi < nf; fi++) if ((mF[fi].Length & 1) == 1) odd.Add(fi);
		var split = new HashSet<long>(LongKey.I);
		var matched = new bool[nf];
		var prevF = new int[nf];
		var prevE = new long[nf];
		var mark = new int[nf];
		int stamp = 0, paired = 0, toBoundary = 0;
		foreach (int start in odd)
		{
			if (matched[start]) continue;
			// 가장 가까운 짝 없는 홀수 면(또는 열린 경계)까지 BFS
			stamp++;
			var q = new Queue<int>();
			q.Enqueue(start); mark[start] = stamp; prevF[start] = -1;
			int goal = -1; long goalEdge = -1;
			while (q.Count > 0 && goal < 0)
			{
				int f = q.Dequeue();
				var fv = mF[f];
				for (int k = 0; k < fv.Length && goal < 0; k++)
				{
					long key = EKey(fv[k], fv[(k + 1) % fv.Length]);
					var ef = edgeFaces[key];
					if (ef[2] != 0) continue;
					int g = ef[0] == f ? ef[1] : ef[0];
					if (g < 0)
					{
						// 열린 경계에서 끝남 (구멍 쪽에 버텍스 하나 늘어남)
						if (f != start || true) { goal = f; goalEdge = key; }
						continue;
					}
					if (mark[g] == stamp) continue;
					mark[g] = stamp; prevF[g] = f; prevE[g] = key;
					if ((mF[g].Length & 1) == 1 && !matched[g]) { goal = g; goalEdge = -1; break; }
					q.Enqueue(g);
				}
			}
			if (goal < 0) continue;
			matched[start] = true;
			if (goalEdge >= 0)
			{
				Toggle(split, goalEdge);
				toBoundary++;
			}
			else { matched[goal] = true; paired++; }
			for (int f = goal; f != start; f = prevF[f]) Toggle(split, prevE[f]);
		}
		// 중점 넣기
		var mid = new Dictionary<long, int>(LongKey.I);
		foreach (long key in split)
		{
			int a = (int)(key >> 32), b = (int)(key & 0xffffffff);
			mid[key] = mV.Count;
			mV.Add((mV[a] + mV[b]) * 0.5);
			mN.Add((mN[a] + mN[b]).Norm());
			mC.Add((byte)(mC[a] != 0 && mC[b] != 0 ? 1 : 0));
			mCP.Add(RV.Zero);
		}
		var res = new List<int[]>();
		int leftOdd = 0;
		foreach (var f in mF)
		{
			var nfv = new List<int>();
			for (int k = 0; k < f.Length; k++)
			{
				nfv.Add(f[k]);
				int m;
				if (mid.TryGetValue(EKey(f[k], f[(k + 1) % f.Length]), out m)) nfv.Add(m);
			}
			if ((nfv.Count & 1) == 1) { leftOdd++; res.Add(nfv.ToArray()); continue; }
			SplitEven(nfv, res);
		}
		mF = res;
		Note(string.Format("쿼드로: 홀수 면 {0}쌍 이음, 경계로 {1}, 남은 홀수 면 {2}", paired, toBoundary, leftOdd));
	}

	static void Toggle(HashSet<long> s, long key) { if (!s.Remove(key)) s.Add(key); }

	// 짝수 다각형을 쿼드로 (가장 반듯한 대각선으로 반씩 나눔)
	void SplitEven(List<int> poly, List<int[]> outF)
	{
		int n = poly.Count;
		if (n == 4) { outF.Add(poly.ToArray()); return; }
		if (n < 4) { outF.Add(poly.ToArray()); return; }
		double best = double.MaxValue; int bi = -1, bj = -1;
		RV nrm = FaceNormal(poly.ToArray()).Norm();
		double per = 0;
		for (int k = 0; k < n; k++) per += (mV[poly[k]] - mV[poly[(k + 1) % n]]).Len;
		for (int i = 0; i < n; i++)
			for (int d = 3; d <= n / 2; d += 2)
			{
				int j = (i + d) % n;
				// 대각선이 다각형 밖으로 나가지 않는지 (양 끝 각도) 대략 확인 + 짧을수록, 반반에 가까울수록 좋음
				RV a = mV[poly[i]], b = mV[poly[j]];
				double len = (a - b).Len;
				double bal = Math.Abs(n - 2 * d);
				double pen = 0;
				if (!DiagInside(poly, i, j, nrm)) pen += 1e6;
				double score = len / per + bal * 0.05 + pen;
				if (score < best) { best = score; bi = i; bj = j; }
			}
		var p1 = new List<int>(); var p2 = new List<int>();
		for (int k = bi; ; k = (k + 1) % n) { p1.Add(poly[k]); if (k == bj) break; }
		for (int k = bj; ; k = (k + 1) % n) { p2.Add(poly[k]); if (k == bi) break; }
		SplitEven(p1, outF);
		SplitEven(p2, outF);
	}

	bool DiagInside(List<int> poly, int i, int j, RV nrm)
	{
		int n = poly.Count;
		RV a = mV[poly[i]], b = mV[poly[j]];
		RV d = b - a;
		// i 에서의 안쪽 각 사이로 가는지
		RV prev = mV[poly[(i - 1 + n) % n]] - a, next = mV[poly[(i + 1) % n]] - a;
		return InWedge(prev, next, d, nrm) && InWedge(mV[poly[(j - 1 + n) % n]] - b, mV[poly[(j + 1) % n]] - b, -d, nrm);
	}

	static bool InWedge(RV prev, RV next, RV d, RV n)
	{
		// next 에서 반시계로 prev 까지의 각 안에 d 가 있는지 (법선 n 기준)
		double an = Math.Atan2(n.Dot(next.Cross(d)), next.Dot(d));
		double ap = Math.Atan2(n.Dot(next.Cross(prev)), next.Dot(prev));
		if (an < 0) an += 2 * Math.PI;
		if (ap < 0) ap += 2 * Math.PI;
		return an > 0.05 && an < ap - 0.05;
	}

	RV FaceNormal(int[] f)
	{
		RV s = RV.Zero;
		RV c = RV.Zero;
		foreach (int v in f) c = c + mV[v];
		c = c / f.Length;
		for (int k = 0; k < f.Length; k++) s = s + (mV[f[k]] - c).Cross(mV[f[(k + 1) % f.Length]] - c);
		return s;
	}

	// 두 면 사이 직선 위에만 있는 버텍스(엣지 2개) 제거
	void RemoveValence2()
	{
		var vf = VertFaceCount();
		var drop = new bool[mV.Count];
		for (int v = 0; v < mV.Count; v++) if (vf[v] == 2 && mC[v] != 2) drop[v] = true;
		// 이웃 수(면 둘레 기준)가 2 인지 확인
		var nb = new List<HashSet<int>>();
		for (int v = 0; v < mV.Count; v++) nb.Add(new HashSet<int>());
		foreach (var f in mF)
			for (int k = 0; k < f.Length; k++) { nb[f[k]].Add(f[(k + 1) % f.Length]); nb[f[(k + 1) % f.Length]].Add(f[k]); }
		for (int v = 0; v < mV.Count; v++) if (nb[v].Count != 2) drop[v] = false;
		var res = new List<int[]>();
		foreach (var f in mF)
		{
			var nf = new List<int>();
			foreach (int v in f) if (!drop[v]) nf.Add(v);
			if (nf.Count >= 3) res.Add(nf.ToArray());
		}
		mF = res;
	}

	int[] VertFaceCount()
	{
		var c = new int[mV.Count];
		foreach (var f in mF) foreach (int v in f) c[v]++;
		return c;
	}

	// 붙어 있는 삼각형 두 개를 반듯한 쿼드로
	void MergeTriangles()
	{
		var edgeFace = new Dictionary<long, List<int>>(LongKey.I);
		for (int fi = 0; fi < mF.Count; fi++)
		{
			var f = mF[fi];
			if (f.Length != 3) continue;
			for (int k = 0; k < 3; k++)
			{
				long key = EKey(f[k], f[(k + 1) % 3]);
				List<int> lst;
				if (!edgeFace.TryGetValue(key, out lst)) edgeFace[key] = lst = new List<int>();
				lst.Add(fi);
			}
		}
		var cands = new List<KeyValuePair<double, long>>();
		foreach (var kv in edgeFace)
		{
			if (kv.Value.Count != 2) continue;
			int f0 = kv.Value[0], f1 = kv.Value[1];
			int[] q = QuadOf(mF[f0], mF[f1], kv.Key);
			if (q == null) continue;
			double qual = QuadQuality(q);
			// 모서리 선 위의 엣지는 지우지 않음
			int a = (int)(kv.Key >> 32), b = (int)(kv.Key & 0xffffffff);
			if (mC[a] != 0 && mC[b] != 0) qual *= 0.3;
			if (qual > 0.35) cands.Add(new KeyValuePair<double, long>(-qual, ((long)f0 << 32) | (uint)f1));
		}
		cands.Sort((x, y) => x.Key.CompareTo(y.Key));
		var used = new bool[mF.Count];
		var add = new List<int[]>();
		foreach (var c in cands)
		{
			int f0 = (int)(c.Value >> 32), f1 = (int)(c.Value & 0xffffffff);
			if (used[f0] || used[f1]) continue;
			// 공유 엣지 찾기
			long key = SharedEdge(mF[f0], mF[f1]);
			if (key < 0) continue;
			int[] q = QuadOf(mF[f0], mF[f1], key);
			if (q == null) continue;
			used[f0] = used[f1] = true;
			add.Add(q);
		}
		var res = new List<int[]>();
		for (int i = 0; i < mF.Count; i++) if (!used[i]) res.Add(mF[i]);
		res.AddRange(add);
		mF = res;
	}

	static long EKey(int a, int b) { return a < b ? ((long)a << 32) | (uint)b : ((long)b << 32) | (uint)a; }

	static long SharedEdge(int[] f0, int[] f1)
	{
		for (int k = 0; k < f0.Length; k++)
		{
			int a = f0[k], b = f0[(k + 1) % f0.Length];
			for (int m = 0; m < f1.Length; m++)
				if (f1[m] == b && f1[(m + 1) % f1.Length] == a) return EKey(a, b);
		}
		return -1;
	}

	static int[] QuadOf(int[] t0, int[] t1, long key)
	{
		int a = (int)(key >> 32), b = (int)(key & 0xffffffff);
		// t0 에서 a→b 또는 b→a 순서 찾아 반대쪽 버텍스를 끼움
		for (int k = 0; k < 3; k++)
		{
			int x = t0[k], y = t0[(k + 1) % 3], z = t0[(k + 2) % 3];
			if ((x == a && y == b) || (x == b && y == a))
			{
				int o = -1;
				for (int m = 0; m < 3; m++) if (t1[m] != a && t1[m] != b) o = t1[m];
				if (o < 0 || o == z) return null;
				// t1 은 y→x 방향이어야 함
				bool okDir = false;
				for (int m = 0; m < 3; m++) if (t1[m] == y && t1[(m + 1) % 3] == x) okDir = true;
				if (!okDir) return null;
				return new[] { x, o, y, z };
			}
		}
		return null;
	}

	double QuadQuality(int[] q)
	{
		// 네 각이 90도에 가까울수록 1
		double worst = 1;
		RV n = FaceNormal(q).Norm();
		for (int k = 0; k < 4; k++)
		{
			RV a = mV[q[(k + 3) % 4]] - mV[q[k]], b = mV[q[(k + 1) % 4]] - mV[q[k]];
			double la = a.Len, lb = b.Len;
			if (la < 1e-12 || lb < 1e-12) return 0;
			double c = a.Dot(b) / (la * lb);
			if (a.Cross(b).Dot(n) > 0) return 0; // 오목 (방향 반대)
			worst = Math.Min(worst, 1 - Math.Abs(c));
		}
		return worst;
	}

	void CompactVerts()
	{
		var used = new int[mV.Count];
		for (int i = 0; i < used.Length; i++) used[i] = -1;
		var nV = new List<RV>(); var nN = new List<RV>(); var nC = new List<byte>(); var nCP = new List<RV>();
		foreach (var f in mF)
			for (int k = 0; k < f.Length; k++)
			{
				int v = f[k];
				if (used[v] < 0) { used[v] = nV.Count; nV.Add(mV[v]); nN.Add(mN[v]); nC.Add(mC[v]); nCP.Add(mCP[v]); }
				f[k] = used[v];
			}
		mV = nV; mN = nN; mC = nC; mCP = nCP;
	}

	// 한 번 나누기: n각형 → 쿼드 n개 (전부 쿼드)
	void Subdivide()
	{
		var ev = new Dictionary<long, int>(LongKey.I);
		var faces = new List<int[]>();
		int n0 = mV.Count;
		foreach (var f in mF)
		{
			RV c = RV.Zero, cn = RV.Zero;
			foreach (int v in f) { c = c + mV[v]; cn = cn + mN[v]; }
			int ci = mV.Count;
			mV.Add(c / f.Length); mN.Add(cn.Norm()); mC.Add(0); mCP.Add(RV.Zero);
			var mids = new int[f.Length];
			for (int k = 0; k < f.Length; k++)
			{
				int a = f[k], b = f[(k + 1) % f.Length];
				long key = EKey(a, b);
				int m;
				if (!ev.TryGetValue(key, out m))
				{
					m = mV.Count;
					mV.Add((mV[a] + mV[b]) * 0.5);
					mN.Add((mN[a] + mN[b]).Norm());
					mC.Add((byte)(mC[a] != 0 && mC[b] != 0 ? 1 : 0));
					mCP.Add(RV.Zero);
					ev[key] = m;
				}
				mids[k] = m;
			}
			for (int k = 0; k < f.Length; k++)
				faces.Add(new[] { f[k], mids[k], ci, mids[(k - 1 + f.Length) % f.Length] });
		}
		mF = faces;
	}

	// 두께 없는 판(열린 오브젝트) 뒷면 지우기: 가장 가까운 판 삼각형이 반대쪽을 보고 있는 면
	void RemoveSheetBacks(bool enable)
	{
		if (!enable) return;
		bool any = false;
		foreach (bool b in triOpen) if (b) { any = true; break; }
		if (!any) return;
		int nv = mV.Count;
		var back = new sbyte[nv];
		For(nv, v =>
		{
			int t; RV q; int reg;
			if (!Nearest(mV[v], out t, out q, out reg)) return;
			if (!triOpen[t]) return;
			RV d = mV[v] - q;
			double dl = d.Len;
			if (dl < r * 0.25) return;
			double s = d.Dot(TN[t]) / dl;
			if (reg == 0) back[v] = (sbyte)(s < -0.5 ? 1 : -1);
		});
		var res = new List<int[]>();
		int removed = 0;
		foreach (var f in mF)
		{
			int b = 0, fr = 0;
			foreach (int v in f) { if (back[v] > 0) b++; else if (back[v] < 0) fr++; }
			if (b > 0 && b * 2 >= f.Length && fr == 0) { removed++; continue; }
			res.Add(f);
		}
		// 판 뒷면 전체가 남은 면보다 많으면 (법선이 반대인 오브젝트) 지우지 않음
		if (removed > 0 && removed < mF.Count / 2)
		{
			mF = res;
			CompactVerts();
			Note(string.Format("두께 없는 판 뒷면 {0}면 지움", removed));
		}
	}

	// 원래 표면에 붙이며 고르게. 모서리 버텍스는 모서리 선으로
	void Relax()
	{
		int n = mV.Count;
		var nb = new List<int>[n];
		for (int v = 0; v < n; v++) nb[v] = new List<int>(4);
		var boundary = new bool[n];
		var ec = new Dictionary<long, int>(LongKey.I);
		foreach (var f in mF)
			for (int k = 0; k < f.Length; k++)
			{
				int a = f[k], b = f[(k + 1) % f.Length];
				if (!nb[a].Contains(b)) nb[a].Add(b);
				if (!nb[b].Contains(a)) nb[b].Add(a);
				long key = EKey(a, b);
				int c; ec.TryGetValue(key, out c); ec[key] = c + 1;
			}
		foreach (var kv in ec)
			if (kv.Value == 1) { boundary[(int)(kv.Key >> 32)] = true; boundary[(int)(kv.Key & 0xffffffff)] = true; }
		var pos = mV.ToArray();
		var nrm = mN.ToArray();
		var feat = new byte[n];     // 투영 결과 모서리 위
		// 처음 투영: 모서리 버텍스는 가까운 날카로운 엣지로
		For(n, v => { pos[v] = Project(pos[v], mC[v], out nrm[v], out feat[v]); if (mC[v] == 2) pos[v] = mCP[v]; });
		var np = new RV[n];
		for (int it = 0; it < RelaxIters; it++)
		{
			For(n, v =>
			{
				if (mC[v] == 2 || boundary[v]) { np[v] = pos[v]; return; }
				RV s = RV.Zero; int c = 0;
				if (mC[v] == 1)
				{
					// 모서리 선을 따라서만: 모서리 이웃 둘의 평균
					foreach (int w in nb[v]) if (mC[w] != 0) { s = s + pos[w]; c++; }
					if (c != 2) { np[v] = pos[v]; return; }
				}
				else
					foreach (int w in nb[v]) { s = s + pos[w]; c++; }
				if (c == 0) { np[v] = pos[v]; return; }
				RV d = s / c - pos[v];
				if (mC[v] == 0) d = d - nrm[v] * d.Dot(nrm[v]);
				np[v] = pos[v] + d * 0.5;
			});
			For(n, v => { pos[v] = mC[v] == 2 ? mCP[v] : Project(np[v], mC[v], out nrm[v], out feat[v]); });
		}
		for (int v = 0; v < n; v++) mV[v] = pos[v];
	}

	// 가장 가까운 원래 표면으로. c != 0 이면 가까운 날카로운 엣지 위로
	RV Project(RV p, byte c, out RV nrm, out byte onFeat)
	{
		nrm = RV.Zero; onFeat = 0;
		int t; RV q; int reg;
		if (!Nearest(p, out t, out q, out reg)) return p;
		nrm = TN[t];
		if (c == 0 || !SnapToCrease) return q;
		// 주변에서 가장 가까운 날카로운 엣지
		double best = double.MaxValue; RV bq = q;
		int ci = (int)Math.Round((p.X - g0.X) / h), cj = (int)Math.Round((p.Y - g0.Y) / h), ck = (int)Math.Round((p.Z - g0.Z) / h);
		int rad = Math.Max(2, (int)Math.Ceiling(L * 0.5 / h));
		var seen = new HashSet<int>();
		for (int dk = -rad; dk <= rad; dk++)
			for (int dj = -rad; dj <= rad; dj++)
				for (int di = -rad; di <= rad; di++)
				{
					int i = ci + di, j = cj + dj, k = ck + dk;
					if (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) continue;
					int tt = NT[Idx(i, j, k)];
					if (tt < 0 || triSharp[tt] == 0 || !seen.Add(tt)) continue;
					for (int e = 0; e < 3; e++)
					{
						if (!SharpEdge(tt, e)) continue;
						RV a = P[T[tt * 3 + e]], b = P[T[tt * 3 + (e + 1) % 3]];
						RV cp = ClosestOnSeg(p, a, b);
						double d2 = (cp - p).Len2;
						if (d2 < best) { best = d2; bq = cp; }
					}
				}
		if (best < (L * 0.6) * (L * 0.6)) { onFeat = 1; return bq; }
		return q;
	}

	void WriteOutput()
	{
		OutVerts = new float[mV.Count * 3];
		for (int i = 0; i < mV.Count; i++)
		{
			OutVerts[i * 3] = (float)mV[i].X; OutVerts[i * 3 + 1] = (float)mV[i].Y; OutVerts[i * 3 + 2] = (float)mV[i].Z;
		}
		OutCounts = new int[mF.Count];
		int tot = 0;
		OutQuads = OutTris = OutOthers = 0;
		for (int i = 0; i < mF.Count; i++)
		{
			OutCounts[i] = mF[i].Length; tot += mF[i].Length;
			if (mF[i].Length == 4) OutQuads++; else if (mF[i].Length == 3) OutTris++; else OutOthers++;
		}
		OutIdx = new int[tot];
		int o = 0;
		foreach (var f in mF) foreach (int v in f) OutIdx[o++] = v;
	}

	// ---------------------------------------------------------------- 테스트/디버그용
	public float[] DebugSurfaceNet()
	{
		var res = new float[snV.Length * 3];
		for (int i = 0; i < snV.Length; i++) { res[i * 3] = (float)snV[i].X; res[i * 3 + 1] = (float)snV[i].Y; res[i * 3 + 2] = (float)snV[i].Z; }
		return res;
	}
	public int[] DebugSurfaceNetQuads() { return snQ; }
	public byte[] DebugTags() { return ctag; }
}
