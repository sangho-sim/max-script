// Geo Node Prompt 설치 프로그램 (GeoNodePrompt_Setup.exe)
//
//   GeoNodePrompt_Setup.exe        창을 띄워 Blender 버전을 골라 설치/제거
//   GeoNodePrompt_Setup.exe /S     지원되는 모든 Blender 버전에 자동 설치 + 활성화
//   GeoNodePrompt_Setup.exe /U     모든 버전에서 자동 제거
//
// 애드온은 exe 안의 geo_node_prompt.zip 리소스로 들어 있고, 아래 위치로 풀림:
//   %APPDATA%\Blender Foundation\Blender\<버전>\scripts\addons\geo_node_prompt
// 빌드: geo_node_prompt_installer/build.sh
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;

static class Core
{
	public const string AddonName = "geo_node_prompt";
	public static readonly Version MinVersion = new Version(4, 0);  // bl_info["blender"] 와 맞춤
	const string Marker = "GEO_NODE_PROMPT_ENABLED";

	// Blender 안에서 실행할 코드: 애드온 켜고 환경설정 저장
	static readonly string EnableExpr =
		"import bpy, addon_utils;" +
		"bpy.ops.preferences.addon_enable(module='" + AddonName + "');" +
		"bpy.ops.wm.save_userpref();" +
		"print('" + Marker + "' if addon_utils.check('" + AddonName + "')[1] else 'GEO_NODE_PROMPT_FAILED')";

	public class BlenderVersion
	{
		public Version Ver; public string Name; public string Dir;
		public bool Supported { get { return Ver >= MinVersion; } }
	}

	public static string ConfigRoot()
	{
		string appdata = Environment.GetEnvironmentVariable("APPDATA");
		if (string.IsNullOrEmpty(appdata))
			appdata = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
		return Path.Combine(appdata, "Blender Foundation", "Blender");
	}

	public static Version ParseVersion(string name)
	{
		var m = Regex.Match(name, @"^(\d+)\.(\d+)$");
		return m.Success ? new Version(int.Parse(m.Groups[1].Value), int.Parse(m.Groups[2].Value)) : null;
	}

	/// 설치된(한 번이라도 실행된) Blender 버전 폴더, 최신 버전부터
	public static List<BlenderVersion> FindVersions()
	{
		var found = new List<BlenderVersion>();
		string root = ConfigRoot();
		if (Directory.Exists(root))
			foreach (string dir in Directory.GetDirectories(root))
			{
				string name = Path.GetFileName(dir);
				Version v = ParseVersion(name);
				if (v != null) found.Add(new BlenderVersion { Ver = v, Name = name, Dir = dir });
			}
		return found.OrderByDescending(b => b.Ver).ToList();
	}

	public static string AddonDir(string versionDir)
	{
		return Path.Combine(versionDir, "scripts", "addons", AddonName);
	}

	public static bool IsInstalled(string versionDir)
	{
		return File.Exists(Path.Combine(AddonDir(versionDir), "__init__.py"));
	}

	/// 기존 설치를 지우고 exe 안의 애드온을 새로 풀어 넣음
	public static string Install(string versionDir)
	{
		string dest = AddonDir(versionDir);
		if (Directory.Exists(dest)) Directory.Delete(dest, true);
		string addons = Path.GetDirectoryName(dest);
		Directory.CreateDirectory(addons);
		using (Stream s = typeof(Core).Assembly.GetManifestResourceStream("geo_node_prompt.zip"))
		using (var zip = new ZipArchive(s, ZipArchiveMode.Read))
			foreach (ZipArchiveEntry e in zip.Entries)
			{
				if (e.FullName.EndsWith("/")) continue;
				string path = Path.Combine(addons, e.FullName.Replace('/', Path.DirectorySeparatorChar));
				Directory.CreateDirectory(Path.GetDirectoryName(path));
				using (Stream src = e.Open())
				using (FileStream dst = File.Create(path))
					src.CopyTo(dst);
			}
		return dest;
	}

	public static bool Uninstall(string versionDir)
	{
		string dest = AddonDir(versionDir);
		if (!Directory.Exists(dest)) return false;
		Directory.Delete(dest, true);
		return true;
	}

	/// 해당 버전의 blender.exe 를 일반적인 설치 위치에서 찾음
	public static string FindBlenderExe(string versionName)
	{
		var bases = new List<string>();
		foreach (string var in new[] { "ProgramFiles", "ProgramW6432", "ProgramFiles(x86)" })
		{
			string b = Environment.GetEnvironmentVariable(var);
			if (!string.IsNullOrEmpty(b)) bases.Add(b);
		}
		string local = Environment.GetEnvironmentVariable("LOCALAPPDATA");
		if (!string.IsNullOrEmpty(local)) bases.Add(Path.Combine(local, "Programs"));  // 사용자 단위 설치
		foreach (string b in bases)
		{
			string exe = Path.Combine(b, "Blender Foundation", "Blender " + versionName, "blender.exe");
			if (File.Exists(exe)) return exe;
		}
		return null;
	}

	/// Blender 를 백그라운드로 잠깐 실행해 애드온을 켜고 환경설정 저장
	public static bool Enable(string blenderExe)
	{
		try
		{
			var psi = new ProcessStartInfo(blenderExe,
				"--background --python-expr \"" + EnableExpr + "\"")
			{
				UseShellExecute = false, CreateNoWindow = true,
				RedirectStandardOutput = true, RedirectStandardError = true,
			};
			using (Process p = Process.Start(psi))
			{
				p.ErrorDataReceived += (o, e) => { };
				p.BeginErrorReadLine();
				string output = p.StandardOutput.ReadToEnd();
				if (!p.WaitForExit(180000)) { try { p.Kill(); } catch { } return false; }
				return output.Contains(Marker);
			}
		}
		catch (Exception) { return false; }
	}
}

class SetupForm : Form
{
	const string Title = "Geo Node Prompt 설치";
	readonly CheckedListBox list = new CheckedListBox { Width = 460, Height = 110, CheckOnClick = true };
	readonly CheckBox enableBox = new CheckBox
	{
		Text = "설치 후 애드온 자동 활성화 (Blender 를 잠깐 백그라운드로 실행)",
		Checked = true, AutoSize = true,
	};
	readonly Label status = new Label { AutoSize = false, Width = 460, Height = 48 };
	readonly Button installBtn = new Button { Text = "설치", Width = 90 };
	readonly Button uninstallBtn = new Button { Text = "제거", Width = 90 };
	readonly List<Core.BlenderVersion> items = new List<Core.BlenderVersion>();

	public SetupForm()
	{
		Text = Title;
		FormBorderStyle = FormBorderStyle.FixedDialog;
		MaximizeBox = false;
		StartPosition = FormStartPosition.CenterScreen;
		AutoScaleMode = AutoScaleMode.Font;
		Font = new Font("Malgun Gothic", 9f);
		AutoSize = true;
		AutoSizeMode = AutoSizeMode.GrowAndShrink;
		Padding = new Padding(10);

		var flow = new FlowLayoutPanel
		{
			FlowDirection = FlowDirection.TopDown, AutoSize = true, WrapContents = false, Dock = DockStyle.Fill,
		};
		flow.Controls.Add(new Label
		{
			Text = "Geo Node Prompt — 프롬프트로 지오메트리 노드 만들기",
			Font = new Font(Font, FontStyle.Bold), AutoSize = true,
		});
		flow.Controls.Add(new Label
		{
			Text = string.Format("설치할 Blender 버전을 체크하세요 (Blender {0} 이상)", Core.MinVersion),
			AutoSize = true, Margin = new Padding(3, 10, 3, 3),
		});
		flow.Controls.Add(list);
		var addBtn = new Button { Text = "다른 Blender 폴더 추가...", AutoSize = true };
		addBtn.Click += (s, e) => AddFolder();
		flow.Controls.Add(addBtn);
		enableBox.Margin = new Padding(3, 10, 3, 3);
		flow.Controls.Add(enableBox);
		flow.Controls.Add(status);

		var buttons = new FlowLayoutPanel { FlowDirection = FlowDirection.RightToLeft, Width = 460, Height = 34 };
		var closeBtn = new Button { Text = "닫기", Width = 90 };
		closeBtn.Click += (s, e) => Close();
		installBtn.Click += (s, e) => DoInstall();
		uninstallBtn.Click += (s, e) => DoUninstall();
		buttons.Controls.Add(closeBtn);
		buttons.Controls.Add(uninstallBtn);
		buttons.Controls.Add(installBtn);
		flow.Controls.Add(buttons);
		Controls.Add(flow);

		// 체크 못 하게: 지원 안 되는 버전
		list.ItemCheck += (s, e) =>
		{
			if (e.NewValue == CheckState.Checked && !items[e.Index].Supported) e.NewValue = CheckState.Unchecked;
		};
		bool first = true;
		foreach (var b in Core.FindVersions())
		{
			AddItem(b, b.Supported && first);
			if (b.Supported) first = false;
		}
		if (items.Count == 0)
			status.Text = "설치된 Blender 를 찾지 못했습니다. Blender 를 한 번 실행했다가 끈 뒤 다시 실행하거나,\n" +
			              "[다른 Blender 폴더 추가]로 직접 고르세요.";
	}

	void AddItem(Core.BlenderVersion b, bool check)
	{
		string label = "Blender " + b.Name;
		if (Core.IsInstalled(b.Dir)) label += "  (설치됨)";
		if (!b.Supported) label += "  (지원 안 됨)";
		items.Add(b);
		list.Items.Add(label, check);
	}

	void AddFolder()
	{
		using (var dlg = new FolderBrowserDialog
		{
			Description = @"Blender 버전 폴더 선택 (예: ...\Blender Foundation\Blender\4.2)",
			SelectedPath = Core.ConfigRoot(),
		})
		{
			if (dlg.ShowDialog(this) != DialogResult.OK) return;
			string name = Path.GetFileName(dlg.SelectedPath.TrimEnd('\\', '/'));
			Version v = Core.ParseVersion(name);
			if (v == null)
			{
				MessageBox.Show(this, "버전 이름(예: 4.2)으로 된 폴더를 골라 주세요.", Title);
				return;
			}
			AddItem(new Core.BlenderVersion { Ver = v, Name = name, Dir = dlg.SelectedPath }, true);
			status.Text = "";
		}
	}

	List<Core.BlenderVersion> Selected()
	{
		return list.CheckedIndices.Cast<int>().Select(i => items[i]).ToList();
	}

	void DoInstall()
	{
		var targets = Selected();
		if (targets.Count == 0) { MessageBox.Show(this, "설치할 Blender 버전을 하나 이상 체크하세요.", Title); return; }
		var jobs = new List<KeyValuePair<Core.BlenderVersion, string>>();
		foreach (var b in targets)
		{
			string exe = null;
			if (enableBox.Checked)
			{
				exe = Core.FindBlenderExe(b.Name);
				if (exe == null && MessageBox.Show(this,
					"Blender " + b.Name + " 의 blender.exe 를 찾지 못했습니다.\n직접 찾아서 자동 활성화할까요?\n" +
					"(아니요 = 파일만 복사, 활성화는 Blender 에서 직접)", Title, MessageBoxButtons.YesNo) == DialogResult.Yes)
					using (var dlg = new OpenFileDialog
					{
						Title = "Blender " + b.Name + " 의 blender.exe 선택",
						Filter = "blender.exe|blender.exe|실행 파일|*.exe",
					})
						if (dlg.ShowDialog(this) == DialogResult.OK) exe = dlg.FileName;
			}
			jobs.Add(new KeyValuePair<Core.BlenderVersion, string>(b, exe));
		}
		SetBusy(true);
		status.Text = "설치 중...";
		new Thread(() => InstallWorker(jobs)) { IsBackground = true }.Start();
	}

	void InstallWorker(List<KeyValuePair<Core.BlenderVersion, string>> jobs)
	{
		var lines = new List<string>();
		bool manual = false;
		foreach (var job in jobs)
		{
			var b = job.Key;
			try { Core.Install(b.Dir); }
			catch (Exception ex)
			{
				lines.Add("Blender " + b.Name + ": 설치 실패 — " + ex.Message + " (Blender 를 끄고 다시 시도)");
				continue;
			}
			if (job.Value != null)
			{
				string name = b.Name;
				BeginInvoke((Action)(() => status.Text = "Blender " + name + " 에서 애드온 활성화 중..."));
				bool ok = Core.Enable(job.Value);
				lines.Add("Blender " + b.Name + ": 설치 + 활성화 " + (ok ? "완료" : "실패"));
				manual |= !ok;
			}
			else
			{
				lines.Add("Blender " + b.Name + ": 설치 완료");
				manual = true;
			}
		}
		string msg = string.Join("\n", lines);
		if (manual)
			msg += "\n\n활성화가 안 된 버전은 Blender 에서 편집 > 환경설정 > 애드온 → \"Geo Node Prompt\" 를 체크하세요.";
		msg += "\n\n★ Blender 가 켜져 있었다면 껐다가 다시 실행하세요.\n사용: 3D 뷰포트에서 N 키 → 사이드바 'Geo Prompt' 탭";
		BeginInvoke((Action)(() => Done(msg)));
	}

	void DoUninstall()
	{
		var targets = Selected();
		if (targets.Count == 0) { MessageBox.Show(this, "제거할 Blender 버전을 체크하세요.", Title); return; }
		var lines = new List<string>();
		foreach (var b in targets)
		{
			try { lines.Add("Blender " + b.Name + ": " + (Core.Uninstall(b.Dir) ? "제거 완료" : "설치되어 있지 않음")); }
			catch (Exception ex) { lines.Add("Blender " + b.Name + ": 제거 실패 — " + ex.Message + " (Blender 를 끄고 다시 시도)"); }
		}
		Done(string.Join("\n", lines));
	}

	void SetBusy(bool busy) { installBtn.Enabled = uninstallBtn.Enabled = !busy; }

	void Done(string msg)
	{
		SetBusy(false);
		status.Text = "";
		MessageBox.Show(this, msg, Title);
	}
}

static class Program
{
	static int RunSilent(bool uninstall)
	{
		int code = 0;
		foreach (var b in Core.FindVersions())
		{
			if (uninstall)
			{
				if (Core.Uninstall(b.Dir)) Console.WriteLine("제거: " + b.Name);
				continue;
			}
			if (!b.Supported) continue;
			Console.WriteLine("설치: " + Core.Install(b.Dir));
			string exe = Core.FindBlenderExe(b.Name);
			if (exe != null)
			{
				bool ok = Core.Enable(exe);
				Console.WriteLine("  활성화 " + (ok ? "완료" : "실패 (Blender 환경설정에서 직접 체크)"));
				if (!ok) code = 2;
			}
		}
		return code;
	}

	[STAThread]
	static int Main(string[] args)
	{
		var flags = new HashSet<string>(args.Select(a => a.ToUpperInvariant()));
		if (flags.Contains("/U")) return RunSilent(true);
		if (flags.Contains("/S")) return RunSilent(false);
		Application.EnableVisualStyles();
		Application.SetCompatibleTextRenderingDefault(false);
		Application.Run(new SetupForm());
		return 0;
	}
}
