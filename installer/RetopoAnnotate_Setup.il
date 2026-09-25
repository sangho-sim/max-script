.assembly extern mscorlib
{
  .ver 4:0:0:0
  .publickeytoken = (B7 7A 5C 56 19 34 E0 89 ) // .z\V.4..
}
.assembly extern System.Windows.Forms
{
  .ver 4:0:0:0
  .publickeytoken = (B7 7A 5C 56 19 34 E0 89 ) // .z\V.4..
}
.assembly extern System
{
  .ver 4:0:0:0
  .publickeytoken = (B7 7A 5C 56 19 34 E0 89 ) // .z\V.4..
}
.assembly extern System.Drawing
{
  .ver 4:0:0:0
  .publickeytoken = (B0 3F 5F 7F 11 D5 0A 3A ) // .?_....:
}
.assembly 'RetopoAnnotate_Setup'
{
  .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilationRelaxationsAttribute::'.ctor'(int32) =  (01 00 08 00 00 00 00 00 ) // ........

  .custom instance void class [mscorlib]System.Runtime.CompilerServices.RuntimeCompatibilityAttribute::'.ctor'() =  (
		01 00 01 00 54 02 16 57 72 61 70 4E 6F 6E 45 78   // ....T..WrapNonEx
		63 65 70 74 69 6F 6E 54 68 72 6F 77 73 01       ) // ceptionThrows.

  .custom instance void class [mscorlib]System.Reflection.AssemblyProductAttribute::'.ctor'(string) =  (
		01 00 0F 52 65 74 6F 70 6F 20 41 6E 6E 6F 74 61   // ...Retopo Annota
		74 65 00 00                                     ) // te..

  .custom instance void class [mscorlib]System.Reflection.AssemblyFileVersionAttribute::'.ctor'(string) =  (01 00 07 31 2E 35 2E 30 2E 30 00 00 ) // ...1.5.0.0..

  .custom instance void class [mscorlib]System.Reflection.AssemblyTitleAttribute::'.ctor'(string) =  (
		01 00 15 52 65 74 6F 70 6F 20 41 6E 6E 6F 74 61   // ...Retopo Annota
		74 65 20 53 65 74 75 70 00 00                   ) // te Setup..

  .hash algorithm 0x00008004
  .ver  1:5:0:0
}
.mresource public 'retopo_annotate.py'
{
}
.mresource public 'RetopoAnnotate.ms'
{
}
.mresource public 'RAKeys.dll'
{
}
.mresource public 'README.txt'
{
}
.module RetopoAnnotate_Setup.exe // GUID = {F10F3F1F-6BDD-486B-8B18-591631B981A6}


.namespace RetopoAnnotateSetup
{
  .class private auto ansi beforefieldinit Target
  	extends [mscorlib]System.Object
  {
    .field  public  string Kind
    .field  public  string Version
    .field  public  string Dir
    .field  public  string Exe
    .field  public  string Label

    // method line 1
    .method public virtual hidebysig 
           instance default string ToString ()  cil managed 
    {
        // Method begins at RVA 0x2050
	// Code size 7 (0x7)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldfld string RetopoAnnotateSetup.Target::Label
	IL_0006:  ret 
    } // end of method Target::ToString

    // method line 2
    .method public hidebysig specialname rtspecialname 
           instance default void '.ctor' ()  cil managed 
    {
        // Method begins at RVA 0x2058
	// Code size 7 (0x7)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  call instance void object::'.ctor'()
	IL_0006:  ret 
    } // end of method Target::.ctor

  } // end of class RetopoAnnotateSetup.Target
}

.namespace RetopoAnnotateSetup
{
  .class private auto ansi abstract sealed beforefieldinit Installer
  	extends [mscorlib]System.Object
  {
    .field public static literal  string BlenderFile = "retopo_annotate.py"
    .field public static literal  string MaxFile = "RetopoAnnotate.ms"
    .field public static literal  string MaxCleanupFile = "RetopoAnnotate_uninstall.ms"
    .field private static literal  string PackageXml = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n<ApplicationPackage SchemaVersion=\"1.0\" ProductType=\"Application\" AutodeskProduct=\"3ds Max\"\r\n    Name=\"Retopo Annotate\" Description=\"Annotation based retopology tools\" AppVersion=\"1.5.0\"\r\n    Author=\"RetopoAnnotate\" AppNameSpace=\"retopo.annotate\" ProductCode=\"*\"\r\n    UpgradeCode=\"{3b8f5d2a-6c41-4e7b-a9d0-1f2e3c4b5a69}\">\r\n  <CompanyDetails Name=\"RetopoAnnotate\" />\r\n  <RuntimeRequirements OS=\"Win64\" Platform=\"3ds Max\" SeriesMin=\"2020\" />\r\n  <Components Description=\"post-start-up scripts parts\">\r\n    <RuntimeRequirements OS=\"Win64\" Platform=\"3ds Max\" SeriesMin=\"2020\" />\r\n    <ComponentEntry AppName=\"RetopoAnnotate\" Version=\"1.5.0\" ModuleName=\"./Contents/RetopoAnnotate.ms\" />\r\n  </Components>\r\n</ApplicationPackage>\r\n"
    .field  public static  string TestRoot
    .field  private static  class [mscorlib]System.Predicate`1<int32> 'CS$<>9__CachedAnonymousMethodDelegate1'
    .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....


    // method line 3
    .method private static hidebysig specialname 
           default string get_AppData ()  cil managed 
    {
        // Method begins at RVA 0x2060
	// Code size 31 (0x1f)
	.maxstack 8
	IL_0000:  ldsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_0005:  brtrue.s IL_000f

	IL_0007:  ldc.i4.s 0x1a
	IL_0009:  call string class [mscorlib]System.Environment::GetFolderPath(valuetype [mscorlib]System.Environment/SpecialFolder)
	IL_000e:  ret 
	IL_000f:  ldsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_0014:  ldstr "AppData"
	IL_0019:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_001e:  ret 
    } // end of method Installer::get_AppData

    // method line 4
    .method private static hidebysig specialname 
           default string get_LocalAppData ()  cil managed 
    {
        // Method begins at RVA 0x2080
	// Code size 31 (0x1f)
	.maxstack 8
	IL_0000:  ldsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_0005:  brtrue.s IL_000f

	IL_0007:  ldc.i4.s 0x1c
	IL_0009:  call string class [mscorlib]System.Environment::GetFolderPath(valuetype [mscorlib]System.Environment/SpecialFolder)
	IL_000e:  ret 
	IL_000f:  ldsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_0014:  ldstr "LocalAppData"
	IL_0019:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_001e:  ret 
    } // end of method Installer::get_LocalAppData

    // method line 5
    .method private static hidebysig specialname 
           default string get_MaxUserRoot ()  cil managed 
    {
        // Method begins at RVA 0x20a0
	// Code size 21 (0x15)
	.maxstack 8
	IL_0000:  call string class RetopoAnnotateSetup.Installer::get_LocalAppData()
	IL_0005:  ldstr "Autodesk"
	IL_000a:  ldstr "3dsMax"
	IL_000f:  call string class [mscorlib]System.IO.Path::Combine(string, string, string)
	IL_0014:  ret 
    } // end of method Installer::get_MaxUserRoot

    // method line 6
    .method public static hidebysig specialname 
           default string get_BundleDir ()  cil managed 
    {
        // Method begins at RVA 0x20b6
	// Code size 26 (0x1a)
	.maxstack 8
	IL_0000:  call string class RetopoAnnotateSetup.Installer::get_AppData()
	IL_0005:  ldstr "Autodesk"
	IL_000a:  ldstr "ApplicationPlugins"
	IL_000f:  ldstr "RetopoAnnotate.bundle"
	IL_0014:  call string class [mscorlib]System.IO.Path::Combine(string, string, string, string)
	IL_0019:  ret 
    } // end of method Installer::get_BundleDir

    // method line 7
    .method private static hidebysig 
           default class [mscorlib]System.Collections.Generic.List`1<string> MaxStartupDirs ()  cil managed 
    {
        // Method begins at RVA 0x20d4
	// Code size 134 (0x86)
	.maxstack 4
	.locals init (
		class [mscorlib]System.Collections.Generic.List`1<string>	V_0,
		string	V_1,
		string	V_2,
		string[]	V_3,
		int32	V_4,
		string[]	V_5,
		int32	V_6)
	IL_0000:  newobj instance void class [mscorlib]System.Collections.Generic.List`1<string>::'.ctor'()
	IL_0005:  stloc.0 
	IL_0006:  call string class RetopoAnnotateSetup.Installer::get_MaxUserRoot()
	IL_000b:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_0010:  brtrue.s IL_0014

	IL_0012:  ldloc.0 
	IL_0013:  ret 
	IL_0014:  call string class RetopoAnnotateSetup.Installer::get_MaxUserRoot()
	IL_0019:  ldstr "20* - 64bit"
	IL_001e:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string, string)
	IL_0023:  stloc.3 
	IL_0024:  ldc.i4.0 
	IL_0025:  stloc.s 4
	IL_0027:  br.s IL_007d

	IL_0029:  ldloc.3 
	IL_002a:  ldloc.s 4
	IL_002c:  ldelem.ref 
	IL_002d:  stloc.1 
	IL_002e:  ldloc.1 
	IL_002f:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string)
	IL_0034:  stloc.s 5
	IL_0036:  ldc.i4.0 
	IL_0037:  stloc.s 6
	IL_0039:  br.s IL_006f

	IL_003b:  ldloc.s 5
	IL_003d:  ldloc.s 6
	IL_003f:  ldelem.ref 
	IL_0040:  stloc.2 
	IL_0041:  ldloc.2 
	IL_0042:  ldstr "scripts"
	IL_0047:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_004c:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_0051:  brfalse.s IL_0069

	IL_0053:  ldloc.0 
	IL_0054:  ldloc.2 
	IL_0055:  ldstr "scripts"
	IL_005a:  ldstr "startup"
	IL_005f:  call string class [mscorlib]System.IO.Path::Combine(string, string, string)
	IL_0064:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<string>::Add(!0)
	IL_0069:  ldloc.s 6
	IL_006b:  ldc.i4.1 
	IL_006c:  add 
	IL_006d:  stloc.s 6
	IL_006f:  ldloc.s 6
	IL_0071:  ldloc.s 5
	IL_0073:  ldlen 
	IL_0074:  conv.i4 
	IL_0075:  blt.s IL_003b

	IL_0077:  ldloc.s 4
	IL_0079:  ldc.i4.1 
	IL_007a:  add 
	IL_007b:  stloc.s 4
	IL_007d:  ldloc.s 4
	IL_007f:  ldloc.3 
	IL_0080:  ldlen 
	IL_0081:  conv.i4 
	IL_0082:  blt.s IL_0029

	IL_0084:  ldloc.0 
	IL_0085:  ret 
    } // end of method Installer::MaxStartupDirs

    // method line 8
    .method private static hidebysig specialname 
           default string get_ProgramFiles ()  cil managed 
    {
        // Method begins at RVA 0x2166
	// Code size 8 (0x8)
	.maxstack 8
	IL_0000:  ldc.i4.s 0x26
	IL_0002:  call string class [mscorlib]System.Environment::GetFolderPath(valuetype [mscorlib]System.Environment/SpecialFolder)
	IL_0007:  ret 
    } // end of method Installer::get_ProgramFiles

    // method line 9
    .method public static hidebysig 
           default unsigned int8[] Resource (string name)  cil managed 
    {
        // Method begins at RVA 0x2170
	// Code size 56 (0x38)
	.maxstack 2
	.locals init (
		class [mscorlib]System.IO.Stream	V_0,
		class [mscorlib]System.IO.MemoryStream	V_1,
		unsigned int8[]	V_2)
	IL_0000:  call class [mscorlib]System.Reflection.Assembly class [mscorlib]System.Reflection.Assembly::GetExecutingAssembly()
	IL_0005:  ldarg.0 
	IL_0006:  callvirt instance class [mscorlib]System.IO.Stream class [mscorlib]System.Reflection.Assembly::GetManifestResourceStream(string)
	IL_000b:  stloc.0 
	.try { // 1
	  IL_000c:  newobj instance void class [mscorlib]System.IO.MemoryStream::'.ctor'()
	  IL_0011:  stloc.1 
	  .try { // 0
	    IL_0012:  ldloc.0 
	    IL_0013:  ldloc.1 
	    IL_0014:  callvirt instance void class [mscorlib]System.IO.Stream::CopyTo(class [mscorlib]System.IO.Stream)
	    IL_0019:  ldloc.1 
	    IL_001a:  callvirt instance unsigned int8[] class [mscorlib]System.IO.MemoryStream::ToArray()
	    IL_001f:  stloc.2 
	    IL_0020:  leave.s IL_0036

	  } // end .try 0
	  finally  { // 0
	    IL_0022:  ldloc.1 
	    IL_0023:  brfalse.s IL_002b

	    IL_0025:  ldloc.1 
	    IL_0026:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	    IL_002b:  endfinally 
	  } // end handler 0
	} // end .try 1
	finally  { // 1
	  IL_002c:  ldloc.0 
	  IL_002d:  brfalse.s IL_0035

	  IL_002f:  ldloc.0 
	  IL_0030:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_0035:  endfinally 
	} // end handler 1
	IL_0036:  ldloc.2 
	IL_0037:  ret 
    } // end of method Installer::Resource

    // method line 10
    .method public static hidebysig 
           default class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> Detect ()  cil managed 
    {
        // Method begins at RVA 0x21dc
	// Code size 975 (0x3cf)
	.maxstack 5
	.locals init (
		class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>	V_0,
		class [System]System.Text.RegularExpressions.Regex	V_1,
		class [System]System.Collections.Generic.SortedDictionary`2<string, string>	V_2,
		string	V_3,
		string	V_4,
		string	V_5,
		string	V_6,
		string	V_7,
		string	V_8,
		string	V_9,
		string	V_10,
		valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>	V_11,
		class [mscorlib]System.Version	V_12,
		class RetopoAnnotateSetup.Target	V_13,
		class [System]System.Collections.Generic.SortedSet`1<int32>	V_14,
		class [System]System.Text.RegularExpressions.Regex	V_15,
		string	V_16,
		string	V_17,
		class [System]System.Text.RegularExpressions.Match	V_18,
		string	V_19,
		string	V_20,
		class [System]System.Text.RegularExpressions.Match	V_21,
		class [mscorlib]System.Collections.Generic.List`1<string>	V_22,
		int32	V_23,
		class RetopoAnnotateSetup.Target	V_24,
		string[]	V_25,
		int32	V_26,
		string[]	V_27,
		int32	V_28,
		string[]	V_29,
		int32	V_30,
		valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<string, string>	V_31,
		string[]	V_32,
		int32	V_33,
		string[]	V_34,
		int32	V_35,
		valuetype [System]System.Collections.Generic.SortedSet`1/Enumerator<int32>	V_36)
	IL_0000:  newobj instance void class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::'.ctor'()
	IL_0005:  stloc.0 
	IL_0006:  ldstr "^\\d+\\.\\d+$"
	IL_000b:  newobj instance void class [System]System.Text.RegularExpressions.Regex::'.ctor'(string)
	IL_0010:  stloc.1 
	IL_0011:  newobj instance void class [System]System.Collections.Generic.SortedDictionary`2<string, string>::'.ctor'()
	IL_0016:  stloc.2 
	IL_0017:  call string class RetopoAnnotateSetup.Installer::get_ProgramFiles()
	IL_001c:  ldstr "Blender Foundation"
	IL_0021:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_0026:  stloc.3 
	IL_0027:  ldloc.3 
	IL_0028:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_002d:  brfalse.s IL_00ad

	IL_002f:  ldloc.3 
	IL_0030:  ldstr "Blender *"
	IL_0035:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string, string)
	IL_003a:  stloc.s 25
	IL_003c:  ldc.i4.0 
	IL_003d:  stloc.s 26
	IL_003f:  br.s IL_00a5

	IL_0041:  ldloc.s 25
	IL_0043:  ldloc.s 26
	IL_0045:  ldelem.ref 
	IL_0046:  stloc.s 4
	IL_0048:  ldloc.s 4
	IL_004a:  ldstr "blender.exe"
	IL_004f:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_0054:  stloc.s 5
	IL_0056:  ldloc.s 5
	IL_0058:  call bool class [mscorlib]System.IO.File::Exists(string)
	IL_005d:  brfalse.s IL_009f

	IL_005f:  ldloc.s 4
	IL_0061:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string)
	IL_0066:  stloc.s 27
	IL_0068:  ldc.i4.0 
	IL_0069:  stloc.s 28
	IL_006b:  br.s IL_0097

	IL_006d:  ldloc.s 27
	IL_006f:  ldloc.s 28
	IL_0071:  ldelem.ref 
	IL_0072:  stloc.s 6
	IL_0074:  ldloc.s 6
	IL_0076:  call string class [mscorlib]System.IO.Path::GetFileName(string)
	IL_007b:  stloc.s 7
	IL_007d:  ldloc.1 
	IL_007e:  ldloc.s 7
	IL_0080:  callvirt instance bool class [System]System.Text.RegularExpressions.Regex::IsMatch(string)
	IL_0085:  brfalse.s IL_0091

	IL_0087:  ldloc.2 
	IL_0088:  ldloc.s 7
	IL_008a:  ldloc.s 5
	IL_008c:  callvirt instance void class [System]System.Collections.Generic.SortedDictionary`2<string, string>::set_Item(!0, !1)
	IL_0091:  ldloc.s 28
	IL_0093:  ldc.i4.1 
	IL_0094:  add 
	IL_0095:  stloc.s 28
	IL_0097:  ldloc.s 28
	IL_0099:  ldloc.s 27
	IL_009b:  ldlen 
	IL_009c:  conv.i4 
	IL_009d:  blt.s IL_006d

	IL_009f:  ldloc.s 26
	IL_00a1:  ldc.i4.1 
	IL_00a2:  add 
	IL_00a3:  stloc.s 26
	IL_00a5:  ldloc.s 26
	IL_00a7:  ldloc.s 25
	IL_00a9:  ldlen 
	IL_00aa:  conv.i4 
	IL_00ab:  blt.s IL_0041

	IL_00ad:  call string class RetopoAnnotateSetup.Installer::get_AppData()
	IL_00b2:  ldstr "Blender Foundation"
	IL_00b7:  ldstr "Blender"
	IL_00bc:  call string class [mscorlib]System.IO.Path::Combine(string, string, string)
	IL_00c1:  stloc.s 8
	IL_00c3:  ldloc.s 8
	IL_00c5:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_00ca:  brfalse.s IL_0115

	IL_00cc:  ldloc.s 8
	IL_00ce:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string)
	IL_00d3:  stloc.s 29
	IL_00d5:  ldc.i4.0 
	IL_00d6:  stloc.s 30
	IL_00d8:  br.s IL_010d

	IL_00da:  ldloc.s 29
	IL_00dc:  ldloc.s 30
	IL_00de:  ldelem.ref 
	IL_00df:  stloc.s 9
	IL_00e1:  ldloc.s 9
	IL_00e3:  call string class [mscorlib]System.IO.Path::GetFileName(string)
	IL_00e8:  stloc.s 10
	IL_00ea:  ldloc.1 
	IL_00eb:  ldloc.s 10
	IL_00ed:  callvirt instance bool class [System]System.Text.RegularExpressions.Regex::IsMatch(string)
	IL_00f2:  brfalse.s IL_0107

	IL_00f4:  ldloc.2 
	IL_00f5:  ldloc.s 10
	IL_00f7:  callvirt instance bool class [System]System.Collections.Generic.SortedDictionary`2<string, string>::ContainsKey(!0)
	IL_00fc:  brtrue.s IL_0107

	IL_00fe:  ldloc.2 
	IL_00ff:  ldloc.s 10
	IL_0101:  ldnull 
	IL_0102:  callvirt instance void class [System]System.Collections.Generic.SortedDictionary`2<string, string>::set_Item(!0, !1)
	IL_0107:  ldloc.s 30
	IL_0109:  ldc.i4.1 
	IL_010a:  add 
	IL_010b:  stloc.s 30
	IL_010d:  ldloc.s 30
	IL_010f:  ldloc.s 29
	IL_0111:  ldlen 
	IL_0112:  conv.i4 
	IL_0113:  blt.s IL_00da

	IL_0115:  ldloc.2 
	IL_0116:  callvirt instance valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<!0,!1> class [System]System.Collections.Generic.SortedDictionary`2<string, string>::GetEnumerator()
	IL_011b:  stloc.s 31
	.try { // 0
	  IL_011d:  br IL_01d1

	  IL_0122:  ldloca.s 31
	  IL_0124:  call instance valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<!0,!1> valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<string, string>::get_Current()
	  IL_0129:  stloc.s 11
	  IL_012b:  ldloca.s 11
	  IL_012d:  call instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Key()
	  IL_0132:  ldloca.s 12
	  IL_0134:  call bool class [mscorlib]System.Version::TryParse(string, [out] class [mscorlib]System.Version&)
	  IL_0139:  brfalse.s IL_014e

	  IL_013b:  ldloc.s 12
	  IL_013d:  ldc.i4.4 
	  IL_013e:  ldc.i4.2 
	  IL_013f:  newobj instance void class [mscorlib]System.Version::'.ctor'(int32, int32)
	  IL_0144:  call bool class [mscorlib]System.Version::op_LessThan(class [mscorlib]System.Version, class [mscorlib]System.Version)
	  IL_0149:  brtrue IL_01d1

	  IL_014e:  newobj instance void class RetopoAnnotateSetup.Target::'.ctor'()
	  IL_0153:  stloc.s 13
	  IL_0155:  ldloc.s 13
	  IL_0157:  ldstr "Blender"
	  IL_015c:  stfld string RetopoAnnotateSetup.Target::Kind
	  IL_0161:  ldloc.s 13
	  IL_0163:  ldloca.s 11
	  IL_0165:  call instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Key()
	  IL_016a:  stfld string RetopoAnnotateSetup.Target::Version
	  IL_016f:  ldloc.s 13
	  IL_0171:  ldloc.s 8
	  IL_0173:  ldloca.s 11
	  IL_0175:  call instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Key()
	  IL_017a:  ldstr "scripts"
	  IL_017f:  ldstr "addons"
	  IL_0184:  call string class [mscorlib]System.IO.Path::Combine(string, string, string, string)
	  IL_0189:  stfld string RetopoAnnotateSetup.Target::Dir
	  IL_018e:  ldloc.s 13
	  IL_0190:  ldloca.s 11
	  IL_0192:  call instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Value()
	  IL_0197:  stfld string RetopoAnnotateSetup.Target::Exe
	  IL_019c:  ldloc.s 13
	  IL_019e:  ldstr "Blender "
	  IL_01a3:  ldloca.s 11
	  IL_01a5:  call instance !0 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Key()
	  IL_01aa:  ldloca.s 11
	  IL_01ac:  call instance !1 valuetype [mscorlib]System.Collections.Generic.KeyValuePair`2<string, string>::get_Value()
	  IL_01b1:  brfalse.s IL_01ba

	  IL_01b3:  ldstr ""
	  IL_01b8:  br.s IL_01bf

	  IL_01ba:  ldstr bytearray (
	20 00 20 00 28 00 e4 c2 89 d5 20 00 0c d3 7c c7  //  . .(..... ...|.
	20 00 c6 c5 4c c7 3a 00 20 00 f5 bc ac c0 cc b9  //  ...L.:. .......
	29 00 01 )                                       // )..
	
	  IL_01bf:  call string string::Concat(string, string, string)
	  IL_01c4:  stfld string RetopoAnnotateSetup.Target::Label
	  IL_01c9:  ldloc.0 
	  IL_01ca:  ldloc.s 13
	  IL_01cc:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::Add(!0)
	  IL_01d1:  ldloca.s 31
	  IL_01d3:  call instance bool valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<string, string>::MoveNext()
	  IL_01d8:  brtrue IL_0122

	  IL_01dd:  leave.s IL_01ed

	} // end .try 0
	finally  { // 0
	  IL_01df:  ldloca.s 31
	  IL_01e1:  constrained. valuetype [System]System.Collections.Generic.SortedDictionary`2/Enumerator<string,string>
	  IL_01e7:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_01ec:  endfinally 
	} // end handler 0
	IL_01ed:  newobj instance void class [System]System.Collections.Generic.SortedSet`1<int32>::'.ctor'()
	IL_01f2:  stloc.s 14
	IL_01f4:  ldstr "(20\\d\\d)"
	IL_01f9:  newobj instance void class [System]System.Text.RegularExpressions.Regex::'.ctor'(string)
	IL_01fe:  stloc.s 15
	IL_0200:  call string class RetopoAnnotateSetup.Installer::get_MaxUserRoot()
	IL_0205:  stloc.s 16
	IL_0207:  ldloc.s 16
	IL_0209:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_020e:  brfalse.s IL_0270

	IL_0210:  ldloc.s 16
	IL_0212:  ldstr "20* - 64bit"
	IL_0217:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string, string)
	IL_021c:  stloc.s 32
	IL_021e:  ldc.i4.0 
	IL_021f:  stloc.s 33
	IL_0221:  br.s IL_0268

	IL_0223:  ldloc.s 32
	IL_0225:  ldloc.s 33
	IL_0227:  ldelem.ref 
	IL_0228:  stloc.s 17
	IL_022a:  ldloc.s 15
	IL_022c:  ldloc.s 17
	IL_022e:  call string class [mscorlib]System.IO.Path::GetFileName(string)
	IL_0233:  callvirt instance class [System]System.Text.RegularExpressions.Match class [System]System.Text.RegularExpressions.Regex::Match(string)
	IL_0238:  stloc.s 18
	IL_023a:  ldloc.s 18
	IL_023c:  callvirt instance bool class [System]System.Text.RegularExpressions.Group::get_Success()
	IL_0241:  brfalse.s IL_0262

	IL_0243:  ldloc.s 14
	IL_0245:  ldloc.s 18
	IL_0247:  callvirt instance class [System]System.Text.RegularExpressions.GroupCollection class [System]System.Text.RegularExpressions.Match::get_Groups()
	IL_024c:  ldc.i4.1 
	IL_024d:  callvirt instance class [System]System.Text.RegularExpressions.Group class [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
	IL_0252:  callvirt instance string class [System]System.Text.RegularExpressions.Capture::get_Value()
	IL_0257:  call int32 int32::Parse(string)
	IL_025c:  callvirt instance bool class [System]System.Collections.Generic.SortedSet`1<int32>::Add(!0)
	IL_0261:  pop 
	IL_0262:  ldloc.s 33
	IL_0264:  ldc.i4.1 
	IL_0265:  add 
	IL_0266:  stloc.s 33
	IL_0268:  ldloc.s 33
	IL_026a:  ldloc.s 32
	IL_026c:  ldlen 
	IL_026d:  conv.i4 
	IL_026e:  blt.s IL_0223

	IL_0270:  call string class RetopoAnnotateSetup.Installer::get_ProgramFiles()
	IL_0275:  ldstr "Autodesk"
	IL_027a:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_027f:  stloc.s 19
	IL_0281:  ldloc.s 19
	IL_0283:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	IL_0288:  brfalse.s IL_02fd

	IL_028a:  ldloc.s 19
	IL_028c:  ldstr "3ds Max 20*"
	IL_0291:  call string[] class [mscorlib]System.IO.Directory::GetDirectories(string, string)
	IL_0296:  stloc.s 34
	IL_0298:  ldc.i4.0 
	IL_0299:  stloc.s 35
	IL_029b:  br.s IL_02f5

	IL_029d:  ldloc.s 34
	IL_029f:  ldloc.s 35
	IL_02a1:  ldelem.ref 
	IL_02a2:  stloc.s 20
	IL_02a4:  ldloc.s 15
	IL_02a6:  ldloc.s 20
	IL_02a8:  call string class [mscorlib]System.IO.Path::GetFileName(string)
	IL_02ad:  callvirt instance class [System]System.Text.RegularExpressions.Match class [System]System.Text.RegularExpressions.Regex::Match(string)
	IL_02b2:  stloc.s 21
	IL_02b4:  ldloc.s 21
	IL_02b6:  callvirt instance bool class [System]System.Text.RegularExpressions.Group::get_Success()
	IL_02bb:  brfalse.s IL_02ef

	IL_02bd:  ldloc.s 20
	IL_02bf:  ldstr "3dsmax.exe"
	IL_02c4:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_02c9:  call bool class [mscorlib]System.IO.File::Exists(string)
	IL_02ce:  brfalse.s IL_02ef

	IL_02d0:  ldloc.s 14
	IL_02d2:  ldloc.s 21
	IL_02d4:  callvirt instance class [System]System.Text.RegularExpressions.GroupCollection class [System]System.Text.RegularExpressions.Match::get_Groups()
	IL_02d9:  ldc.i4.1 
	IL_02da:  callvirt instance class [System]System.Text.RegularExpressions.Group class [System]System.Text.RegularExpressions.GroupCollection::get_Item(int32)
	IL_02df:  callvirt instance string class [System]System.Text.RegularExpressions.Capture::get_Value()
	IL_02e4:  call int32 int32::Parse(string)
	IL_02e9:  callvirt instance bool class [System]System.Collections.Generic.SortedSet`1<int32>::Add(!0)
	IL_02ee:  pop 
	IL_02ef:  ldloc.s 35
	IL_02f1:  ldc.i4.1 
	IL_02f2:  add 
	IL_02f3:  stloc.s 35
	IL_02f5:  ldloc.s 35
	IL_02f7:  ldloc.s 34
	IL_02f9:  ldlen 
	IL_02fa:  conv.i4 
	IL_02fb:  blt.s IL_029d

	IL_02fd:  ldloc.s 14
	IL_02ff:  ldsfld class [mscorlib]System.Predicate`1<int32> RetopoAnnotateSetup.Installer::'CS$<>9__CachedAnonymousMethodDelegate1'
	IL_0304:  brtrue.s IL_0317

	IL_0306:  ldnull 
	IL_0307:  ldftn bool class RetopoAnnotateSetup.Installer::'<Detect>b__0'(int32)
	IL_030d:  newobj instance void class [mscorlib]System.Predicate`1<int32>::'.ctor'(object, native int)
	IL_0312:  stsfld class [mscorlib]System.Predicate`1<int32> RetopoAnnotateSetup.Installer::'CS$<>9__CachedAnonymousMethodDelegate1'
	IL_0317:  ldsfld class [mscorlib]System.Predicate`1<int32> RetopoAnnotateSetup.Installer::'CS$<>9__CachedAnonymousMethodDelegate1'
	IL_031c:  callvirt instance int32 class [System]System.Collections.Generic.SortedSet`1<int32>::RemoveWhere(class [mscorlib]System.Predicate`1<!0>)
	IL_0321:  pop 
	IL_0322:  ldloc.s 14
	IL_0324:  callvirt instance int32 class [System]System.Collections.Generic.SortedSet`1<int32>::get_Count()
	IL_0329:  ldc.i4.0 
	IL_032a:  ble IL_03cd

	IL_032f:  newobj instance void class [mscorlib]System.Collections.Generic.List`1<string>::'.ctor'()
	IL_0334:  stloc.s 22
	IL_0336:  ldloc.s 14
	IL_0338:  callvirt instance valuetype [System]System.Collections.Generic.SortedSet`1/Enumerator<!0> class [System]System.Collections.Generic.SortedSet`1<int32>::GetEnumerator()
	IL_033d:  stloc.s 36
	.try { // 1
	  IL_033f:  br.s IL_0358

	  IL_0341:  ldloca.s 36
	  IL_0343:  call instance !0 valuetype [System]System.Collections.Generic.SortedSet`1/Enumerator<int32>::get_Current()
	  IL_0348:  stloc.s 23
	  IL_034a:  ldloc.s 22
	  IL_034c:  ldloca.s 23
	  IL_034e:  call instance string int32::ToString()
	  IL_0353:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<string>::Add(!0)
	  IL_0358:  ldloca.s 36
	  IL_035a:  call instance bool valuetype [System]System.Collections.Generic.SortedSet`1/Enumerator<int32>::MoveNext()
	  IL_035f:  brtrue.s IL_0341

	  IL_0361:  leave.s IL_0371

	} // end .try 1
	finally  { // 1
	  IL_0363:  ldloca.s 36
	  IL_0365:  constrained. valuetype [System]System.Collections.Generic.SortedSet`1/Enumerator<int32>
	  IL_036b:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_0370:  endfinally 
	} // end handler 1
	IL_0371:  newobj instance void class RetopoAnnotateSetup.Target::'.ctor'()
	IL_0376:  stloc.s 24
	IL_0378:  ldloc.s 24
	IL_037a:  ldstr "3ds Max"
	IL_037f:  stfld string RetopoAnnotateSetup.Target::Kind
	IL_0384:  ldloc.s 24
	IL_0386:  ldstr ", "
	IL_038b:  ldloc.s 22
	IL_038d:  callvirt instance !0[] class [mscorlib]System.Collections.Generic.List`1<string>::ToArray()
	IL_0392:  call string string::Join(string, string[])
	IL_0397:  stfld string RetopoAnnotateSetup.Target::Version
	IL_039c:  ldloc.s 24
	IL_039e:  call string class RetopoAnnotateSetup.Installer::get_BundleDir()
	IL_03a3:  stfld string RetopoAnnotateSetup.Target::Dir
	IL_03a8:  ldloc.s 24
	IL_03aa:  ldstr bytearray (
	33 00 64 00 73 00 20 00 4d 00 61 00 78 00 20 00  // 3.d.s. .M.a.x. .
	32 00 30 00 32 00 30 00 20 00 74 c7 c1 c0 20 00  // 2.0.2.0. .t... .
	a8 ba e0 b4 20 00 84 bc 04 c8 20 00 28 00 1c bc  // .... ..... .(...
	ac ac 3a 00 20 00 01 )                           // ..:. ..
	
	IL_03af:  ldloc.s 24
	IL_03b1:  ldfld string RetopoAnnotateSetup.Target::Version
	IL_03b6:  ldstr ")"
	IL_03bb:  call string string::Concat(string, string, string)
	IL_03c0:  stfld string RetopoAnnotateSetup.Target::Label
	IL_03c5:  ldloc.0 
	IL_03c6:  ldloc.s 24
	IL_03c8:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::Add(!0)
	IL_03cd:  ldloc.0 
	IL_03ce:  ret 
    } // end of method Installer::Detect

    // method line 11
    .method private static hidebysig 
           default bool RunBlender (class RetopoAnnotateSetup.Target t, string action, class [mscorlib]System.Action`1<string> log)  cil managed 
    {
        // Method begins at RVA 0x25d4
	// Code size 443 (0x1bb)
	.maxstack 5
	.locals init (
		string	V_0,
		class [System]System.Diagnostics.ProcessStartInfo	V_1,
		string	V_2,
		class [System]System.Diagnostics.Process	V_3,
		string	V_4,
		bool	V_5,
		class [mscorlib]System.Exception	V_6,
		bool	V_7)
	IL_0000:  ldarg.0 
	IL_0001:  ldfld string RetopoAnnotateSetup.Target::Exe
	IL_0006:  brtrue.s IL_0015

	IL_0008:  ldarg.2 
	IL_0009:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 62 00 6c 00 65 00  //  . . ... .b.l.e.
	6e 00 64 00 65 00 72 00 2e 00 65 00 78 00 65 00  // n.d.e.r...e.x.e.
	20 00 7c b9 20 00 3e cc c0 c9 20 00 bb ba 74 d5  //  .|. .>... ...t.
	20 00 90 c7 d9 b3 20 00 5c d6 31 c1 54 d6 20 00  //  ..... .\.1.T. .
	dd c0 b5 b7 20 00 92 21 20 00 42 00 6c 00 65 00  // .... ..! .B.l.e.
	6e 00 64 00 65 00 72 00 20 00 58 d6 bd ac 24 c1  // n.d.e.r. .X...$.
	15 c8 20 00 3e 00 20 00 60 c5 dc b4 28 c6 d0 c5  // .. .>. .`...(...
	1c c1 20 00 27 00 52 00 65 00 74 00 6f 00 70 00  // .. .'.R.e.t.o.p.
	6f 00 20 00 41 00 6e 00 6e 00 6f 00 74 00 61 00  // o. .A.n.n.o.t.a.
	74 00 65 00 27 00 20 00 7c b9 20 00 1c cf fc c8  // t.e.'. .|. .....
	38 c1 94 c6 01 )                                 // 8....
	
	IL_000e:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	IL_0013:  ldc.i4.0 
	IL_0014:  ret 
	IL_0015:  call string class [mscorlib]System.IO.Path::GetTempPath()
	IL_001a:  ldstr "retopo_annotate_setup.py"
	IL_001f:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_0024:  stloc.0 
	IL_0025:  ldloc.0 
	IL_0026:  ldstr "import bpy, addon_utils, sys\nact = sys.argv[sys.argv.index('--') + 1]\ntry:\n    if act == 'enable':\n        addon_utils.enable('retopo_annotate', default_set=True, persistent=True)\n    else:\n        addon_utils.disable('retopo_annotate', default_set=True)\n    bpy.ops.wm.save_userpref()\n    print('RETOPO_SETUP_OK')\nexcept Exception as ex:\n    print('RETOPO_SETUP_FAIL', ex)\n"
	IL_002b:  ldc.i4.0 
	IL_002c:  newobj instance void class [mscorlib]System.Text.UTF8Encoding::'.ctor'(bool)
	IL_0031:  call void class [mscorlib]System.IO.File::WriteAllText(string, string, class [mscorlib]System.Text.Encoding)
	IL_0036:  ldarg.0 
	IL_0037:  ldfld string RetopoAnnotateSetup.Target::Exe
	IL_003c:  ldstr "-b --python \""
	IL_0041:  ldloc.0 
	IL_0042:  ldstr "\" -- "
	IL_0047:  ldarg.1 
	IL_0048:  call string string::Concat(string, string, string, string)
	IL_004d:  newobj instance void class [System]System.Diagnostics.ProcessStartInfo::'.ctor'(string, string)
	IL_0052:  stloc.1 
	IL_0053:  ldloc.1 
	IL_0054:  ldc.i4.0 
	IL_0055:  callvirt instance void class [System]System.Diagnostics.ProcessStartInfo::set_UseShellExecute(bool)
	IL_005a:  ldloc.1 
	IL_005b:  ldc.i4.1 
	IL_005c:  callvirt instance void class [System]System.Diagnostics.ProcessStartInfo::set_CreateNoWindow(bool)
	IL_0061:  ldloc.1 
	IL_0062:  ldc.i4.1 
	IL_0063:  callvirt instance void class [System]System.Diagnostics.ProcessStartInfo::set_RedirectStandardOutput(bool)
	IL_0068:  ldloc.1 
	IL_0069:  ldc.i4.1 
	IL_006a:  callvirt instance void class [System]System.Diagnostics.ProcessStartInfo::set_RedirectStandardError(bool)
	IL_006f:  ldloc.1 
	IL_0070:  call class [mscorlib]System.Text.Encoding class [mscorlib]System.Text.Encoding::get_UTF8()
	IL_0075:  callvirt instance void class [System]System.Diagnostics.ProcessStartInfo::set_StandardOutputEncoding(class [mscorlib]System.Text.Encoding)
	IL_007a:  ldsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_007f:  brfalse.s IL_00e3

	IL_0081:  call string class RetopoAnnotateSetup.Installer::get_AppData()
	IL_0086:  ldstr "Blender Foundation"
	IL_008b:  ldstr "Blender"
	IL_0090:  ldarg.0 
	IL_0091:  ldfld string RetopoAnnotateSetup.Target::Version
	IL_0096:  call string class [mscorlib]System.IO.Path::Combine(string, string, string, string)
	IL_009b:  stloc.2 
	IL_009c:  ldloc.1 
	IL_009d:  callvirt instance class [System]System.Collections.Specialized.StringDictionary class [System]System.Diagnostics.ProcessStartInfo::get_EnvironmentVariables()
	IL_00a2:  ldstr "BLENDER_USER_RESOURCES"
	IL_00a7:  ldloc.2 
	IL_00a8:  callvirt instance void class [System]System.Collections.Specialized.StringDictionary::set_Item(string, string)
	IL_00ad:  ldloc.1 
	IL_00ae:  callvirt instance class [System]System.Collections.Specialized.StringDictionary class [System]System.Diagnostics.ProcessStartInfo::get_EnvironmentVariables()
	IL_00b3:  ldstr "BLENDER_USER_CONFIG"
	IL_00b8:  ldloc.2 
	IL_00b9:  ldstr "config"
	IL_00be:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_00c3:  callvirt instance void class [System]System.Collections.Specialized.StringDictionary::set_Item(string, string)
	IL_00c8:  ldloc.1 
	IL_00c9:  callvirt instance class [System]System.Collections.Specialized.StringDictionary class [System]System.Diagnostics.ProcessStartInfo::get_EnvironmentVariables()
	IL_00ce:  ldstr "BLENDER_USER_SCRIPTS"
	IL_00d3:  ldloc.2 
	IL_00d4:  ldstr "scripts"
	IL_00d9:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_00de:  callvirt instance void class [System]System.Collections.Specialized.StringDictionary::set_Item(string, string)
	.try { // 3
	  .try { // 1
	    IL_00e3:  ldloc.1 
	    IL_00e4:  call class [System]System.Diagnostics.Process class [System]System.Diagnostics.Process::Start(class [System]System.Diagnostics.ProcessStartInfo)
	    IL_00e9:  stloc.3 
	    .try { // 0
	      IL_00ea:  ldloc.3 
	      IL_00eb:  callvirt instance class [mscorlib]System.IO.StreamReader class [System]System.Diagnostics.Process::get_StandardError()
	      IL_00f0:  callvirt instance class [mscorlib]System.Threading.Tasks.Task`1<string> class [mscorlib]System.IO.TextReader::ReadToEndAsync()
	      IL_00f5:  callvirt instance !0 class [mscorlib]System.Threading.Tasks.Task`1<string>::get_Result()
	      IL_00fa:  pop 
	      IL_00fb:  ldloc.3 
	      IL_00fc:  callvirt instance class [mscorlib]System.IO.StreamReader class [System]System.Diagnostics.Process::get_StandardOutput()
	      IL_0101:  callvirt instance string class [mscorlib]System.IO.TextReader::ReadToEnd()
	      IL_0106:  stloc.s 4
	      IL_0108:  ldloc.3 
	      IL_0109:  ldc.i4 180000
	      IL_010e:  callvirt instance bool class [System]System.Diagnostics.Process::WaitForExit(int32)
	      IL_0113:  pop 
	      IL_0114:  ldloc.s 4
	      IL_0116:  ldstr "RETOPO_SETUP_OK"
	      IL_011b:  callvirt instance bool string::Contains(string)
	      IL_0120:  stloc.s 5
	      IL_0122:  ldarg.2 
	      IL_0123:  ldloc.s 5
	      IL_0125:  brtrue.s IL_0151

	      IL_0127:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 60 c5 dc b4 28 c6  //  . . ... .`...(.
	20 00 90 c7 d9 b3 20 00 01 )                     //  ..... ..
	
	      IL_012c:  ldarg.1 
	      IL_012d:  ldstr "enable"
	      IL_0132:  call bool string::op_Equality(string, string)
	      IL_0137:  brtrue.s IL_0140

	      IL_0139:  ldstr bytearray (
	44 be 5c d6 31 c1 54 d6 01 )                     // D.\.1.T..
	
	      IL_013e:  br.s IL_0145

	      IL_0140:  ldstr bytearray (
	5c d6 31 c1 54 d6 01 )                           // \.1.T..
	
	      IL_0145:  ldstr bytearray (
	20 00 e4 c2 28 d3 20 00 28 00 42 00 6c 00 65 00  //  ...(. .(.B.l.e.
	6e 00 64 00 65 00 72 00 20 00 d0 c5 1c c1 20 00  // n.d.e.r. ..... .
	c1 c9 11 c8 20 00 1c cf fc c8 38 c1 94 c6 29 00  // .... .....8...).
	01 )                                             // .
	
	      IL_014a:  call string string::Concat(string, string, string)
	      IL_014f:  br.s IL_0179

	      IL_0151:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 60 c5 dc b4 28 c6  //  . . ... .`...(.
	20 00 01 )                                       //  ..
	
	      IL_0156:  ldarg.1 
	      IL_0157:  ldstr "enable"
	      IL_015c:  call bool string::op_Equality(string, string)
	      IL_0161:  brtrue.s IL_016a

	      IL_0163:  ldstr bytearray (
	44 be 5c d6 31 c1 54 d6 01 )                     // D.\.1.T..
	
	      IL_0168:  br.s IL_016f

	      IL_016a:  ldstr bytearray (
	5c d6 31 c1 54 d6 01 )                           // \.1.T..
	
	      IL_016f:  ldstr bytearray (
	20 00 44 c6 cc b8 01 )                           //  .D....
	
	      IL_0174:  call string string::Concat(string, string, string)
	      IL_0179:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	      IL_017e:  ldloc.s 5
	      IL_0180:  stloc.s 7
	      IL_0182:  leave.s IL_01b8

	    } // end .try 0
	    finally  { // 0
	      IL_0184:  ldloc.3 
	      IL_0185:  brfalse.s IL_018d

	      IL_0187:  ldloc.3 
	      IL_0188:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	      IL_018d:  endfinally 
	    } // end handler 0
	  } // end .try 1
	  catch class [mscorlib]System.Exception { // 1
	    IL_018e:  stloc.s 6
	    IL_0190:  ldarg.2 
	    IL_0191:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 42 00 6c 00 65 00  //  . . ... .B.l.e.
	6e 00 64 00 65 00 72 00 20 00 e4 c2 89 d5 20 00  // n.d.e.r. ..... .
	e4 c2 28 d3 3a 00 20 00 01 )                     // ..(.:. ..
	
	    IL_0196:  ldloc.s 6
	    IL_0198:  callvirt instance string class [mscorlib]System.Exception::get_Message()
	    IL_019d:  call string string::Concat(string, string)
	    IL_01a2:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	    IL_01a7:  ldc.i4.0 
	    IL_01a8:  stloc.s 7
	    IL_01aa:  leave.s IL_01b8

	  } // end handler 1
	} // end .try 3
	finally  { // 3
	  .try { // 2
	    IL_01ac:  ldloc.0 
	    IL_01ad:  call void class [mscorlib]System.IO.File::Delete(string)
	    IL_01b2:  leave.s IL_01b7

	  } // end .try 2
	  catch class [mscorlib]System.Object { // 2
	    IL_01b4:  pop 
	    IL_01b5:  leave.s IL_01b7

	  } // end handler 2
	  IL_01b7:  endfinally 
	} // end handler 3
	IL_01b8:  ldloc.s 7
	IL_01ba:  ret 
    } // end of method Installer::RunBlender

    // method line 12
    .method public static hidebysig 
           default bool Install (class RetopoAnnotateSetup.Target t, class [mscorlib]System.Action`1<string> log)  cil managed 
    {
        // Method begins at RVA 0x27d0
	// Code size 480 (0x1e0)
	.maxstack 5
	.locals init (
		string	V_0,
		string	V_1,
		string	V_2,
		string	V_3,
		class [mscorlib]System.Exception	V_4,
		bool	V_5,
		valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>	V_6,
		string[]	V_7,
		string[]	V_8,
		int32	V_9)
	.try { // 2
	  IL_0000:  ldarg.0 
	  IL_0001:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_0006:  call class [mscorlib]System.IO.DirectoryInfo class [mscorlib]System.IO.Directory::CreateDirectory(string)
	  IL_000b:  pop 
	  IL_000c:  ldarg.0 
	  IL_000d:  ldfld string RetopoAnnotateSetup.Target::Kind
	  IL_0012:  ldstr "Blender"
	  IL_0017:  call bool string::op_Equality(string, string)
	  IL_001c:  brfalse.s IL_0070

	  IL_001e:  ldarg.0 
	  IL_001f:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_0024:  ldstr "retopo_annotate.py"
	  IL_0029:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_002e:  ldstr "retopo_annotate.py"
	  IL_0033:  call unsigned int8[] class RetopoAnnotateSetup.Installer::Resource(string)
	  IL_0038:  call void class [mscorlib]System.IO.File::WriteAllBytes(string, unsigned int8[])
	  IL_003d:  ldarg.1 
	  IL_003e:  ldstr bytearray (
	14 27 20 00 01 )                                 // .' ..
	
	  IL_0043:  ldarg.0 
	  IL_0044:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0049:  ldstr bytearray (
	20 00 3a 00 20 00 60 c5 dc b4 28 c6 20 00 f5 bc  //  .:. .`...(. ...
	ac c0 20 00 92 21 20 00 01 )                     // .. ..! ..
	
	  IL_004e:  ldarg.0 
	  IL_004f:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_0054:  call string string::Concat(string, string, string, string)
	  IL_0059:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_005e:  ldarg.0 
	  IL_005f:  ldstr "enable"
	  IL_0064:  ldarg.1 
	  IL_0065:  call bool class RetopoAnnotateSetup.Installer::RunBlender(class RetopoAnnotateSetup.Target, string, class [mscorlib]System.Action`1<string>)
	  IL_006a:  pop 
	  IL_006b:  br IL_01af

	  IL_0070:  ldarg.0 
	  IL_0071:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_0076:  ldstr "Contents"
	  IL_007b:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_0080:  stloc.0 
	  IL_0081:  ldloc.0 
	  IL_0082:  call class [mscorlib]System.IO.DirectoryInfo class [mscorlib]System.IO.Directory::CreateDirectory(string)
	  IL_0087:  pop 
	  IL_0088:  ldarg.0 
	  IL_0089:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_008e:  ldstr "PackageContents.xml"
	  IL_0093:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_0098:  ldstr "<?xml version=\"1.0\" encoding=\"utf-8\"?>\r\n<ApplicationPackage SchemaVersion=\"1.0\" ProductType=\"Application\" AutodeskProduct=\"3ds Max\"\r\n    Name=\"Retopo Annotate\" Description=\"Annotation based retopology tools\" AppVersion=\"1.5.0\"\r\n    Author=\"RetopoAnnotate\" AppNameSpace=\"retopo.annotate\" ProductCode=\"*\"\r\n    UpgradeCode=\"{3b8f5d2a-6c41-4e7b-a9d0-1f2e3c4b5a69}\">\r\n  <CompanyDetails Name=\"RetopoAnnotate\" />\r\n  <RuntimeRequirements OS=\"Win64\" Platform=\"3ds Max\" SeriesMin=\"2020\" />\r\n  <Components Description=\"post-start-up scripts parts\">\r\n    <RuntimeRequirements OS=\"Win64\" Platform=\"3ds Max\" SeriesMin=\"2020\" />\r\n    <ComponentEntry AppName=\"RetopoAnnotate\" Version=\"1.5.0\" ModuleName=\"./Contents/RetopoAnnotate.ms\" />\r\n  </Components>\r\n</ApplicationPackage>\r\n"
	  IL_009d:  ldc.i4.0 
	  IL_009e:  newobj instance void class [mscorlib]System.Text.UTF8Encoding::'.ctor'(bool)
	  IL_00a3:  call void class [mscorlib]System.IO.File::WriteAllText(string, string, class [mscorlib]System.Text.Encoding)
	  IL_00a8:  ldloc.0 
	  IL_00a9:  ldstr "RetopoAnnotate.ms"
	  IL_00ae:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_00b3:  ldstr "RetopoAnnotate.ms"
	  IL_00b8:  call unsigned int8[] class RetopoAnnotateSetup.Installer::Resource(string)
	  IL_00bd:  call void class [mscorlib]System.IO.File::WriteAllBytes(string, unsigned int8[])
	  .try { // 0
	    IL_00c2:  ldloc.0 
	    IL_00c3:  ldstr "RAKeys.dll"
	    IL_00c8:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	    IL_00cd:  ldstr "RAKeys.dll"
	    IL_00d2:  call unsigned int8[] class RetopoAnnotateSetup.Installer::Resource(string)
	    IL_00d7:  call void class [mscorlib]System.IO.File::WriteAllBytes(string, unsigned int8[])
	    IL_00dc:  leave.s IL_00e1

	  } // end .try 0
	  catch class [mscorlib]System.IO.IOException { // 0
	    IL_00de:  pop 
	    IL_00df:  leave.s IL_00e1

	  } // end handler 0
	  IL_00e1:  ldloc.0 
	  IL_00e2:  ldstr "RetopoAnnotate.firstrun"
	  IL_00e7:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_00ec:  ldstr "1"
	  IL_00f1:  call void class [mscorlib]System.IO.File::WriteAllText(string, string)
	  IL_00f6:  call class [mscorlib]System.Collections.Generic.List`1<string> class RetopoAnnotateSetup.Installer::MaxStartupDirs()
	  IL_00fb:  callvirt instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<string>::GetEnumerator()
	  IL_0100:  stloc.s 6
	  .try { // 1
	    IL_0102:  br.s IL_016a

	    IL_0104:  ldloca.s 6
	    IL_0106:  call instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::get_Current()
	    IL_010b:  stloc.1 
	    IL_010c:  ldc.i4.2 
	    IL_010d:  newarr [mscorlib]System.String
	    IL_0112:  stloc.s 7
	    IL_0114:  ldloc.s 7
	    IL_0116:  ldc.i4.0 
	    IL_0117:  ldstr "RetopoAnnotate.ms"
	    IL_011c:  stelem.ref 
	    IL_011d:  ldloc.s 7
	    IL_011f:  ldc.i4.1 
	    IL_0120:  ldstr "RetopoAnnotate_uninstall.ms"
	    IL_0125:  stelem.ref 
	    IL_0126:  ldloc.s 7
	    IL_0128:  stloc.s 8
	    IL_012a:  ldc.i4.0 
	    IL_012b:  stloc.s 9
	    IL_012d:  br.s IL_0162

	    IL_012f:  ldloc.s 8
	    IL_0131:  ldloc.s 9
	    IL_0133:  ldelem.ref 
	    IL_0134:  stloc.2 
	    IL_0135:  ldloc.1 
	    IL_0136:  ldloc.2 
	    IL_0137:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	    IL_013c:  stloc.3 
	    IL_013d:  ldloc.3 
	    IL_013e:  call bool class [mscorlib]System.IO.File::Exists(string)
	    IL_0143:  brfalse.s IL_015c

	    IL_0145:  ldloc.3 
	    IL_0146:  call void class [mscorlib]System.IO.File::Delete(string)
	    IL_014b:  ldarg.1 
	    IL_014c:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 74 c7 04 c8 20 00  //  . . ... .t... .
	24 c1 58 ce f8 bc 20 00 15 c8 ac b9 3a 00 20 00  // $.X... .....:. .
	01 )                                             // .
	
	    IL_0151:  ldloc.3 
	    IL_0152:  call string string::Concat(string, string)
	    IL_0157:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	    IL_015c:  ldloc.s 9
	    IL_015e:  ldc.i4.1 
	    IL_015f:  add 
	    IL_0160:  stloc.s 9
	    IL_0162:  ldloc.s 9
	    IL_0164:  ldloc.s 8
	    IL_0166:  ldlen 
	    IL_0167:  conv.i4 
	    IL_0168:  blt.s IL_012f

	    IL_016a:  ldloca.s 6
	    IL_016c:  call instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::MoveNext()
	    IL_0171:  brtrue.s IL_0104

	    IL_0173:  leave.s IL_0183

	  } // end .try 1
	  finally  { // 1
	    IL_0175:  ldloca.s 6
	    IL_0177:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>
	    IL_017d:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	    IL_0182:  endfinally 
	  } // end handler 1
	  IL_0183:  ldarg.1 
	  IL_0184:  ldstr bytearray (
	14 27 20 00 01 )                                 // .' ..
	
	  IL_0189:  ldarg.0 
	  IL_018a:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_018f:  ldstr bytearray (
	20 00 3a 00 20 00 0c d5 ec b7 f8 ad 78 c7 20 00  //  .:. .......x. .
	88 bc e4 b4 20 00 24 c1 58 ce 20 00 92 21 20 00  // .... .$.X. ..! .
	01 )                                             // .
	
	  IL_0194:  ldarg.0 
	  IL_0195:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_019a:  call string string::Concat(string, string, string, string)
	  IL_019f:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_01a4:  ldarg.1 
	  IL_01a5:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 33 00 64 00 73 00  //  . . ... .3.d.s.
	20 00 4d 00 61 00 78 00 20 00 7c b9 20 00 e4 b2  //  .M.a.x. .|. ...
	dc c2 20 00 dc c2 91 c7 58 d5 74 ba 20 00 27 00  // .. .....X.t. .'.
	52 00 65 00 74 00 6f 00 70 00 6f 00 20 00 41 00  // R.e.t.o.p.o. .A.
	6e 00 6e 00 6f 00 74 00 61 00 74 00 65 00 27 00  // n.n.o.t.a.t.e.'.
	20 00 3d cc 74 c7 20 00 f4 c5 ac b9 e0 ac 20 00  //  .=.t. ....... .
	54 ba 74 b2 14 bc d0 c5 20 00 27 00 52 00 65 00  // T.t..... .'.R.e.
	74 00 6f 00 70 00 6f 00 27 00 20 00 00 ac 20 00  // t.o.p.o.'. ... .
	dd c0 41 ae c8 b2 e4 b2 01 )                     // ..A......
	
	  IL_01aa:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_01af:  ldc.i4.1 
	  IL_01b0:  stloc.s 5
	  IL_01b2:  leave.s IL_01dd

	} // end .try 2
	catch class [mscorlib]System.Exception { // 2
	  IL_01b4:  stloc.s 4
	  IL_01b6:  ldarg.1 
	  IL_01b7:  ldstr bytearray (
	18 27 20 00 01 )                                 // .' ..
	
	  IL_01bc:  ldarg.0 
	  IL_01bd:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_01c2:  ldstr bytearray (
	20 00 24 c1 58 ce 20 00 e4 c2 28 d3 3a 00 20 00  //  .$.X. ...(.:. .
	01 )                                             // .
	
	  IL_01c7:  ldloc.s 4
	  IL_01c9:  callvirt instance string class [mscorlib]System.Exception::get_Message()
	  IL_01ce:  call string string::Concat(string, string, string, string)
	  IL_01d3:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_01d8:  ldc.i4.0 
	  IL_01d9:  stloc.s 5
	  IL_01db:  leave.s IL_01dd

	} // end handler 2
	IL_01dd:  ldloc.s 5
	IL_01df:  ret 
    } // end of method Installer::Install

    // method line 13
    .method public static hidebysig 
           default bool Uninstall (class RetopoAnnotateSetup.Target t, class [mscorlib]System.Action`1<string> log)  cil managed 
    {
        // Method begins at RVA 0x2a08
	// Code size 614 (0x266)
	.maxstack 5
	.locals init (
		string	V_0,
		string	V_1,
		string	V_2,
		bool	V_3,
		string	V_4,
		string	V_5,
		string	V_6,
		string	V_7,
		string	V_8,
		class [mscorlib]System.Exception	V_9,
		bool	V_10,
		string[]	V_11,
		int32	V_12,
		string[]	V_13,
		int32	V_14,
		valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>	V_15,
		string[]	V_16,
		int32	V_17)
	.try { // 3
	  IL_0000:  ldarg.0 
	  IL_0001:  ldfld string RetopoAnnotateSetup.Target::Kind
	  IL_0006:  ldstr "Blender"
	  IL_000b:  call bool string::op_Equality(string, string)
	  IL_0010:  brfalse IL_00c6

	  IL_0015:  ldarg.0 
	  IL_0016:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_001b:  ldstr "retopo_annotate.py"
	  IL_0020:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_0025:  stloc.0 
	  IL_0026:  ldloc.0 
	  IL_0027:  call bool class [mscorlib]System.IO.File::Exists(string)
	  IL_002c:  brfalse.s IL_00a6

	  IL_002e:  ldarg.0 
	  IL_002f:  ldstr "disable"
	  IL_0034:  ldarg.1 
	  IL_0035:  call bool class RetopoAnnotateSetup.Installer::RunBlender(class RetopoAnnotateSetup.Target, string, class [mscorlib]System.Action`1<string>)
	  IL_003a:  pop 
	  IL_003b:  ldloc.0 
	  IL_003c:  call void class [mscorlib]System.IO.File::Delete(string)
	  IL_0041:  ldarg.0 
	  IL_0042:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_0047:  ldstr "__pycache__"
	  IL_004c:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	  IL_0051:  stloc.1 
	  IL_0052:  ldloc.1 
	  IL_0053:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	  IL_0058:  brfalse.s IL_0086

	  IL_005a:  ldloc.1 
	  IL_005b:  ldstr "retopo_annotate*.pyc"
	  IL_0060:  call string[] class [mscorlib]System.IO.Directory::GetFiles(string, string)
	  IL_0065:  stloc.s 11
	  IL_0067:  ldc.i4.0 
	  IL_0068:  stloc.s 12
	  IL_006a:  br.s IL_007e

	  IL_006c:  ldloc.s 11
	  IL_006e:  ldloc.s 12
	  IL_0070:  ldelem.ref 
	  IL_0071:  stloc.2 
	  IL_0072:  ldloc.2 
	  IL_0073:  call void class [mscorlib]System.IO.File::Delete(string)
	  IL_0078:  ldloc.s 12
	  IL_007a:  ldc.i4.1 
	  IL_007b:  add 
	  IL_007c:  stloc.s 12
	  IL_007e:  ldloc.s 12
	  IL_0080:  ldloc.s 11
	  IL_0082:  ldlen 
	  IL_0083:  conv.i4 
	  IL_0084:  blt.s IL_006c

	  IL_0086:  ldarg.1 
	  IL_0087:  ldstr bytearray (
	14 27 20 00 01 )                                 // .' ..
	
	  IL_008c:  ldarg.0 
	  IL_008d:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0092:  ldstr bytearray (
	20 00 3a 00 20 00 60 c5 dc b4 28 c6 20 00 1c c8  //  .:. .`...(. ...
	70 ac 01 )                                       // p..
	
	  IL_0097:  call string string::Concat(string, string, string)
	  IL_009c:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_00a1:  br IL_0235

	  IL_00a6:  ldarg.1 
	  IL_00a7:  ldstr bytearray (
	b7 00 20 00 01 )                                 // .. ..
	
	  IL_00ac:  ldarg.0 
	  IL_00ad:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_00b2:  ldstr bytearray (
	20 00 3a 00 20 00 24 c1 58 ce 18 b4 b4 c5 20 00  //  .:. .$.X..... .
	88 c7 c0 c9 20 00 4a c5 4c c7 01 )               // .... .J.L..
	
	  IL_00b7:  call string string::Concat(string, string, string)
	  IL_00bc:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_00c1:  br IL_0235

	  IL_00c6:  ldarg.0 
	  IL_00c7:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_00cc:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	  IL_00d1:  stloc.3 
	  IL_00d2:  ldloc.3 
	  IL_00d3:  brfalse.s IL_0135

	  .try { // 1
	    IL_00d5:  ldarg.0 
	    IL_00d6:  ldfld string RetopoAnnotateSetup.Target::Dir
	    IL_00db:  ldc.i4.1 
	    IL_00dc:  call void class [mscorlib]System.IO.Directory::Delete(string, bool)
	    IL_00e1:  leave.s IL_0135

	  } // end .try 1
	  catch class [mscorlib]System.Exception { // 1
	    IL_00e3:  pop 
	    IL_00e4:  ldarg.0 
	    IL_00e5:  ldfld string RetopoAnnotateSetup.Target::Dir
	    IL_00ea:  ldstr "*"
	    IL_00ef:  ldc.i4.1 
	    IL_00f0:  call string[] class [mscorlib]System.IO.Directory::GetFiles(string, string, valuetype [mscorlib]System.IO.SearchOption)
	    IL_00f5:  stloc.s 13
	    IL_00f7:  ldc.i4.0 
	    IL_00f8:  stloc.s 14
	    IL_00fa:  br.s IL_0115

	    IL_00fc:  ldloc.s 13
	    IL_00fe:  ldloc.s 14
	    IL_0100:  ldelem.ref 
	    IL_0101:  stloc.s 4
	    .try { // 0
	      IL_0103:  ldloc.s 4
	      IL_0105:  call void class [mscorlib]System.IO.File::Delete(string)
	      IL_010a:  leave.s IL_010f

	    } // end .try 0
	    catch class [mscorlib]System.Object { // 0
	      IL_010c:  pop 
	      IL_010d:  leave.s IL_010f

	    } // end handler 0
	    IL_010f:  ldloc.s 14
	    IL_0111:  ldc.i4.1 
	    IL_0112:  add 
	    IL_0113:  stloc.s 14
	    IL_0115:  ldloc.s 14
	    IL_0117:  ldloc.s 13
	    IL_0119:  ldlen 
	    IL_011a:  conv.i4 
	    IL_011b:  blt.s IL_00fc

	    IL_011d:  ldarg.1 
	    IL_011e:  ldstr bytearray (
	20 00 20 00 20 00 b7 00 20 00 33 00 64 00 73 00  //  . . ... .3.d.s.
	20 00 4d 00 61 00 78 00 20 00 00 ac 20 00 1c cf  //  .M.a.x. ... ...
	38 c8 20 00 88 c7 b4 c5 20 00 52 00 41 00 4b 00  // 8. ..... .R.A.K.
	65 00 79 00 73 00 2e 00 64 00 6c 00 6c 00 20 00  // e.y.s...d.l.l. .
	74 c7 20 00 a8 b0 58 c5 b5 c2 c8 b2 e4 b2 2e 00  // t. ...X.........
	20 00 4d 00 61 00 78 00 20 00 7c b9 20 00 48 b0  //  .M.a.x. .|. .H.
	20 00 a4 b4 20 00 5b 00 1c c8 70 ac 5d 00 7c b9  //  ... .[...p.].|.
	20 00 5c d5 20 00 88 bc 20 00 54 b3 20 00 04 b2  //  .\. ... .T. ...
	74 b9 38 c1 94 c6 3a 00 20 00 01 )               // t.8...:. ..
	
	    IL_0123:  ldarg.0 
	    IL_0124:  ldfld string RetopoAnnotateSetup.Target::Dir
	    IL_0129:  call string string::Concat(string, string)
	    IL_012e:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	    IL_0133:  leave.s IL_0135

	  } // end handler 1
	  IL_0135:  call class [mscorlib]System.Collections.Generic.List`1<string> class RetopoAnnotateSetup.Installer::MaxStartupDirs()
	  IL_013a:  callvirt instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<string>::GetEnumerator()
	  IL_013f:  stloc.s 15
	  .try { // 2
	    IL_0141:  br IL_01de

	    IL_0146:  ldloca.s 15
	    IL_0148:  call instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::get_Current()
	    IL_014d:  stloc.s 5
	    IL_014f:  ldloc.s 5
	    IL_0151:  ldstr "RetopoAnnotate.ms"
	    IL_0156:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	    IL_015b:  stloc.s 6
	    IL_015d:  ldloc.s 6
	    IL_015f:  call bool class [mscorlib]System.IO.File::Exists(string)
	    IL_0164:  brfalse.s IL_016f

	    IL_0166:  ldloc.s 6
	    IL_0168:  call void class [mscorlib]System.IO.File::Delete(string)
	    IL_016d:  ldc.i4.1 
	    IL_016e:  stloc.3 
	    IL_016f:  ldloc.3 
	    IL_0170:  brfalse.s IL_018e

	    IL_0172:  ldloc.s 5
	    IL_0174:  ldstr "RetopoAnnotate_uninstall.ms"
	    IL_0179:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	    IL_017e:  ldstr "try (local m = menuMan.findMenu \"Retopo\"; if m != undefined do (menuMan.unRegisterMenu m; menuMan.updateMenuBar())) catch ()\r\ntry (deleteFile (getThisScriptFilename())) catch ()\r\n"
	    IL_0183:  ldc.i4.1 
	    IL_0184:  newobj instance void class [mscorlib]System.Text.UTF8Encoding::'.ctor'(bool)
	    IL_0189:  call void class [mscorlib]System.IO.File::WriteAllText(string, string, class [mscorlib]System.Text.Encoding)
	    IL_018e:  ldloc.s 5
	    IL_0190:  call string class [mscorlib]System.IO.Path::GetDirectoryName(string)
	    IL_0195:  call string class [mscorlib]System.IO.Path::GetDirectoryName(string)
	    IL_019a:  ldstr "usermacros"
	    IL_019f:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	    IL_01a4:  stloc.s 7
	    IL_01a6:  ldloc.s 7
	    IL_01a8:  call bool class [mscorlib]System.IO.Directory::Exists(string)
	    IL_01ad:  brfalse.s IL_01de

	    IL_01af:  ldloc.s 7
	    IL_01b1:  ldstr "RetopoAnnotate-*.mcr"
	    IL_01b6:  call string[] class [mscorlib]System.IO.Directory::GetFiles(string, string)
	    IL_01bb:  stloc.s 16
	    IL_01bd:  ldc.i4.0 
	    IL_01be:  stloc.s 17
	    IL_01c0:  br.s IL_01d6

	    IL_01c2:  ldloc.s 16
	    IL_01c4:  ldloc.s 17
	    IL_01c6:  ldelem.ref 
	    IL_01c7:  stloc.s 8
	    IL_01c9:  ldloc.s 8
	    IL_01cb:  call void class [mscorlib]System.IO.File::Delete(string)
	    IL_01d0:  ldloc.s 17
	    IL_01d2:  ldc.i4.1 
	    IL_01d3:  add 
	    IL_01d4:  stloc.s 17
	    IL_01d6:  ldloc.s 17
	    IL_01d8:  ldloc.s 16
	    IL_01da:  ldlen 
	    IL_01db:  conv.i4 
	    IL_01dc:  blt.s IL_01c2

	    IL_01de:  ldloca.s 15
	    IL_01e0:  call instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>::MoveNext()
	    IL_01e5:  brtrue IL_0146

	    IL_01ea:  leave.s IL_01fa

	  } // end .try 2
	  finally  { // 2
	    IL_01ec:  ldloca.s 15
	    IL_01ee:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<string>
	    IL_01f4:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	    IL_01f9:  endfinally 
	  } // end handler 2
	  IL_01fa:  ldloc.3 
	  IL_01fb:  brfalse.s IL_021a

	  IL_01fd:  ldarg.1 
	  IL_01fe:  ldstr bytearray (
	14 27 20 00 01 )                                 // .' ..
	
	  IL_0203:  ldarg.0 
	  IL_0204:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0209:  ldstr bytearray (
	20 00 3a 00 20 00 1c c8 70 ac 20 00 28 00 e4 b2  //  .:. ...p. .(...
	4c c7 20 00 e4 c2 89 d5 20 00 4c b5 20 00 54 ba  // L. ..... .L. .T.
	74 b2 c4 b3 20 00 15 c8 ac b9 28 b4 29 00 01 )   // t... .....(.)..
	
	  IL_020e:  call string string::Concat(string, string, string)
	  IL_0213:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_0218:  br.s IL_0235

	  IL_021a:  ldarg.1 
	  IL_021b:  ldstr bytearray (
	b7 00 20 00 01 )                                 // .. ..
	
	  IL_0220:  ldarg.0 
	  IL_0221:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0226:  ldstr bytearray (
	20 00 3a 00 20 00 24 c1 58 ce 18 b4 b4 c5 20 00  //  .:. .$.X..... .
	88 c7 c0 c9 20 00 4a c5 4c c7 01 )               // .... .J.L..
	
	  IL_022b:  call string string::Concat(string, string, string)
	  IL_0230:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_0235:  ldc.i4.1 
	  IL_0236:  stloc.s 10
	  IL_0238:  leave.s IL_0263

	} // end .try 3
	catch class [mscorlib]System.Exception { // 3
	  IL_023a:  stloc.s 9
	  IL_023c:  ldarg.1 
	  IL_023d:  ldstr bytearray (
	18 27 20 00 01 )                                 // .' ..
	
	  IL_0242:  ldarg.0 
	  IL_0243:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0248:  ldstr bytearray (
	20 00 1c c8 70 ac 20 00 e4 c2 28 d3 3a 00 20 00  //  ...p. ...(.:. .
	01 )                                             // .
	
	  IL_024d:  ldloc.s 9
	  IL_024f:  callvirt instance string class [mscorlib]System.Exception::get_Message()
	  IL_0254:  call string string::Concat(string, string, string, string)
	  IL_0259:  callvirt instance void class [mscorlib]System.Action`1<string>::Invoke(!0)
	  IL_025e:  ldc.i4.0 
	  IL_025f:  stloc.s 10
	  IL_0261:  leave.s IL_0263

	} // end handler 3
	IL_0263:  ldloc.s 10
	IL_0265:  ret 
    } // end of method Installer::Uninstall

    // method line 14
    .method public static hidebysig 
           default bool IsInstalled (class RetopoAnnotateSetup.Target t)  cil managed 
    {
        // Method begins at RVA 0x2ce0
	// Code size 67 (0x43)
	.maxstack 3
	IL_0000:  ldarg.0 
	IL_0001:  ldfld string RetopoAnnotateSetup.Target::Kind
	IL_0006:  ldstr "Blender"
	IL_000b:  call bool string::op_Equality(string, string)
	IL_0010:  brtrue.s IL_002d

	IL_0012:  ldarg.0 
	IL_0013:  ldfld string RetopoAnnotateSetup.Target::Dir
	IL_0018:  ldstr "Contents"
	IL_001d:  ldstr "RetopoAnnotate.ms"
	IL_0022:  call string class [mscorlib]System.IO.Path::Combine(string, string, string)
	IL_0027:  call bool class [mscorlib]System.IO.File::Exists(string)
	IL_002c:  ret 
	IL_002d:  ldarg.0 
	IL_002e:  ldfld string RetopoAnnotateSetup.Target::Dir
	IL_0033:  ldstr "retopo_annotate.py"
	IL_0038:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_003d:  call bool class [mscorlib]System.IO.File::Exists(string)
	IL_0042:  ret 
    } // end of method Installer::IsInstalled

    // method line 15
    .method public static hidebysig 
           default string RunningApps ()  cil managed 
    {
        // Method begins at RVA 0x2d30
	// Code size 75 (0x4b)
	.maxstack 2
	.locals init (
		class [mscorlib]System.Collections.Generic.List`1<string>	V_0)
	IL_0000:  newobj instance void class [mscorlib]System.Collections.Generic.List`1<string>::'.ctor'()
	IL_0005:  stloc.0 
	IL_0006:  ldstr "blender"
	IL_000b:  call class [System]System.Diagnostics.Process[] class [System]System.Diagnostics.Process::GetProcessesByName(string)
	IL_0010:  ldlen 
	IL_0011:  conv.i4 
	IL_0012:  ldc.i4.0 
	IL_0013:  ble.s IL_0020

	IL_0015:  ldloc.0 
	IL_0016:  ldstr "Blender"
	IL_001b:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<string>::Add(!0)
	IL_0020:  ldstr "3dsmax"
	IL_0025:  call class [System]System.Diagnostics.Process[] class [System]System.Diagnostics.Process::GetProcessesByName(string)
	IL_002a:  ldlen 
	IL_002b:  conv.i4 
	IL_002c:  ldc.i4.0 
	IL_002d:  ble.s IL_003a

	IL_002f:  ldloc.0 
	IL_0030:  ldstr "3ds Max"
	IL_0035:  callvirt instance void class [mscorlib]System.Collections.Generic.List`1<string>::Add(!0)
	IL_003a:  ldstr ", "
	IL_003f:  ldloc.0 
	IL_0040:  callvirt instance !0[] class [mscorlib]System.Collections.Generic.List`1<string>::ToArray()
	IL_0045:  call string string::Join(string, string[])
	IL_004a:  ret 
    } // end of method Installer::RunningApps

    // method line 16
    .method private static hidebysig 
           default bool '<Detect>b__0' (int32 y)  cil managed 
    {
        .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x21d0
	// Code size 9 (0x9)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldc.i4 2020
	IL_0006:  clt 
	IL_0008:  ret 
    } // end of method Installer::<Detect>b__0

	.property string AppData ()
	{
		.get default string RetopoAnnotateSetup.Installer::get_AppData () 
	}
	.property string LocalAppData ()
	{
		.get default string RetopoAnnotateSetup.Installer::get_LocalAppData () 
	}
	.property string MaxUserRoot ()
	{
		.get default string RetopoAnnotateSetup.Installer::get_MaxUserRoot () 
	}
	.property string BundleDir ()
	{
		.get default string RetopoAnnotateSetup.Installer::get_BundleDir () 
	}
	.property string ProgramFiles ()
	{
		.get default string RetopoAnnotateSetup.Installer::get_ProgramFiles () 
	}
  } // end of class RetopoAnnotateSetup.Installer
}

.namespace RetopoAnnotateSetup
{
  .class private auto ansi beforefieldinit SetupForm
  	extends [System.Windows.Forms]System.Windows.Forms.Form
  {
    .field  private  class [System.Windows.Forms]System.Windows.Forms.CheckedListBox list
    .field  private  class [System.Windows.Forms]System.Windows.Forms.TextBox logBox
    .field  private  class [System.Windows.Forms]System.Windows.Forms.Button btnInstall
    .field  private  class [System.Windows.Forms]System.Windows.Forms.Button btnUninstall
    .field  private  class [System.Windows.Forms]System.Windows.Forms.Button btnGuide
    .field  private  class [System.Windows.Forms]System.Windows.Forms.Button btnClose
    .field  private  class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> targets

    // method line 17
    .method public hidebysig specialname rtspecialname 
           instance default void '.ctor' ()  cil managed 
    {
        // Method begins at RVA 0x2dac
	// Code size 1109 (0x455)
	.maxstack 5
	.locals init (
		class [System.Windows.Forms]System.Windows.Forms.Panel	V_0,
		class [System.Windows.Forms]System.Windows.Forms.Label	V_1,
		class [System.Windows.Forms]System.Windows.Forms.Label	V_2,
		class [System.Windows.Forms]System.Windows.Forms.Label	V_3,
		class RetopoAnnotateSetup.Target	V_4,
		class RetopoAnnotateSetup.Target	V_5,
		string	V_6,
		class [mscorlib]System.EventHandler	V_7,
		class [mscorlib]System.EventHandler	V_8,
		class [mscorlib]System.EventHandler	V_9,
		class [mscorlib]System.EventHandler	V_10,
		valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>	V_11,
		valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>	V_12)
	IL_0000:  ldnull 
	IL_0001:  stloc.s 7
	IL_0003:  ldnull 
	IL_0004:  stloc.s 8
	IL_0006:  ldnull 
	IL_0007:  stloc.s 9
	IL_0009:  ldnull 
	IL_000a:  stloc.s 10
	IL_000c:  ldarg.0 
	IL_000d:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::'.ctor'()
	IL_0012:  ldarg.0 
	IL_0013:  ldstr bytearray (
	52 00 65 00 74 00 6f 00 70 00 6f 00 20 00 41 00  // R.e.t.o.p.o. .A.
	6e 00 6e 00 6f 00 74 00 61 00 74 00 65 00 20 00  // n.n.o.t.a.t.e. .
	24 c1 58 ce 01 )                                 // $.X..
	
	IL_0018:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Text(string)
	IL_001d:  ldarg.0 
	IL_001e:  ldstr "Malgun Gothic"
	IL_0023:  ldc.r4 9.5
	IL_0028:  newobj instance void class [System.Drawing]System.Drawing.Font::'.ctor'(string, float32)
	IL_002d:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Font(class [System.Drawing]System.Drawing.Font)
	IL_0032:  ldarg.0 
	IL_0033:  ldc.i4.3 
	IL_0034:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::set_FormBorderStyle(valuetype [System.Windows.Forms]System.Windows.Forms.FormBorderStyle)
	IL_0039:  ldarg.0 
	IL_003a:  ldc.i4.0 
	IL_003b:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::set_MaximizeBox(bool)
	IL_0040:  ldarg.0 
	IL_0041:  ldc.i4.1 
	IL_0042:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::set_StartPosition(valuetype [System.Windows.Forms]System.Windows.Forms.FormStartPosition)
	IL_0047:  ldarg.0 
	IL_0048:  ldc.i4.2 
	IL_0049:  call instance void class [System.Windows.Forms]System.Windows.Forms.ContainerControl::set_AutoScaleMode(valuetype [System.Windows.Forms]System.Windows.Forms.AutoScaleMode)
	IL_004e:  ldarg.0 
	IL_004f:  ldc.i4 560
	IL_0054:  ldc.i4 520
	IL_0059:  newobj instance void valuetype [System.Drawing]System.Drawing.Size::'.ctor'(int32, int32)
	IL_005e:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::set_ClientSize(valuetype [System.Drawing]System.Drawing.Size)
	IL_0063:  ldarg.0 
	IL_0064:  ldc.i4 250
	IL_0069:  ldc.i4 250
	IL_006e:  ldc.i4 252
	IL_0073:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::FromArgb(int32, int32, int32)
	IL_0078:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_BackColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_007d:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.Panel::'.ctor'()
	IL_0082:  stloc.0 
	IL_0083:  ldloc.0 
	IL_0084:  ldc.i4.1 
	IL_0085:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Dock(valuetype [System.Windows.Forms]System.Windows.Forms.DockStyle)
	IL_008a:  ldloc.0 
	IL_008b:  ldc.i4.s 0x4e
	IL_008d:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Height(int32)
	IL_0092:  ldloc.0 
	IL_0093:  ldc.i4.s 0x22
	IL_0095:  ldc.i4.s 0x28
	IL_0097:  ldc.i4.s 0x34
	IL_0099:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::FromArgb(int32, int32, int32)
	IL_009e:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_BackColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_00a3:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.Label::'.ctor'()
	IL_00a8:  stloc.1 
	IL_00a9:  ldloc.1 
	IL_00aa:  ldstr "Retopo Annotate"
	IL_00af:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Text(string)
	IL_00b4:  ldloc.1 
	IL_00b5:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::get_White()
	IL_00ba:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_ForeColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_00bf:  ldloc.1 
	IL_00c0:  ldstr "Malgun Gothic"
	IL_00c5:  ldc.r4 16.
	IL_00ca:  ldc.i4.1 
	IL_00cb:  newobj instance void class [System.Drawing]System.Drawing.Font::'.ctor'(string, float32, valuetype [System.Drawing]System.Drawing.FontStyle)
	IL_00d0:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Font(class [System.Drawing]System.Drawing.Font)
	IL_00d5:  ldloc.1 
	IL_00d6:  ldc.i4.1 
	IL_00d7:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_AutoSize(bool)
	IL_00dc:  ldloc.1 
	IL_00dd:  ldc.i4.s 0x12
	IL_00df:  ldc.i4.s 0x0a
	IL_00e1:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_00e6:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_00eb:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.Label::'.ctor'()
	IL_00f0:  stloc.2 
	IL_00f1:  ldloc.2 
	IL_00f2:  ldstr bytearray (
	42 00 6c 00 65 00 6e 00 64 00 65 00 72 00 20 00  // B.l.e.n.d.e.r. .
	b7 00 20 00 33 00 64 00 73 00 20 00 4d 00 61 00  // .. .3.d.s. .M.a.
	78 00 20 00 ac b9 a0 d1 f4 d3 5c b8 c0 c9 20 00  // x. .......\... .
	34 d2 20 00 14 20 20 00 fc c8 1d c1 3c c7 5c b8  // 4. ..  .....<.\.
	20 00 f8 ad ac b9 74 ba 20 00 54 ba 6c c2 20 00  //  .....t. .T.l. .
	dd c0 31 c1 20 00 2f 00 20 00 f7 ce 20 00 2f 00  // ..1. ./. ... ./.
	20 00 fc cf dc b4 20 00 75 c7 a4 c2 b8 d2 e8 b8  //  ..... .u.......
	dc b4 01 )                                       // ...
	
	IL_00f7:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Text(string)
	IL_00fc:  ldloc.2 
	IL_00fd:  ldc.i4 200
	IL_0102:  ldc.i4 210
	IL_0107:  ldc.i4 225
	IL_010c:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::FromArgb(int32, int32, int32)
	IL_0111:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_ForeColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_0116:  ldloc.2 
	IL_0117:  ldc.i4.1 
	IL_0118:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_AutoSize(bool)
	IL_011d:  ldloc.2 
	IL_011e:  ldc.i4.s 0x14
	IL_0120:  ldc.i4.s 0x30
	IL_0122:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_0127:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_012c:  ldloc.0 
	IL_012d:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_0132:  ldloc.1 
	IL_0133:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_0138:  ldloc.0 
	IL_0139:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_013e:  ldloc.2 
	IL_013f:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_0144:  ldarg.0 
	IL_0145:  call instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_014a:  ldloc.0 
	IL_014b:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_0150:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.Label::'.ctor'()
	IL_0155:  stloc.3 
	IL_0156:  ldloc.3 
	IL_0157:  ldstr bytearray (
	24 c1 58 ce 60 d5 20 00 04 d5 5c b8 f8 ad a8 b7  // $.X.`. ...\.....
	44 c7 20 00 20 c1 dd d0 58 d5 38 c1 94 c6 20 00  // D. . ...X.8... .
	28 00 1c bc ac ac 1c b4 20 00 84 bc 04 c8 29 00  // (....... .....).
	3a 00 01 )                                       // :..
	
	IL_015c:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Text(string)
	IL_0161:  ldloc.3 
	IL_0162:  ldc.i4.1 
	IL_0163:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_AutoSize(bool)
	IL_0168:  ldloc.3 
	IL_0169:  ldc.i4.s 0x12
	IL_016b:  ldc.i4.s 0x5c
	IL_016d:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_0172:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_0177:  ldarg.0 
	IL_0178:  call instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_017d:  ldloc.3 
	IL_017e:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_0183:  ldarg.0 
	IL_0184:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::'.ctor'()
	IL_0189:  stfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_018e:  ldarg.0 
	IL_018f:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_0194:  ldc.i4.s 0x14
	IL_0196:  ldc.i4.s 0x74
	IL_0198:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_019d:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_01a2:  ldarg.0 
	IL_01a3:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_01a8:  ldc.i4 520
	IL_01ad:  ldc.i4 150
	IL_01b2:  newobj instance void valuetype [System.Drawing]System.Drawing.Size::'.ctor'(int32, int32)
	IL_01b7:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Size(valuetype [System.Drawing]System.Drawing.Size)
	IL_01bc:  ldarg.0 
	IL_01bd:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_01c2:  ldc.i4.1 
	IL_01c3:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::set_CheckOnClick(bool)
	IL_01c8:  ldarg.0 
	IL_01c9:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_01ce:  ldc.i4.0 
	IL_01cf:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.ListBox::set_IntegralHeight(bool)
	IL_01d4:  ldarg.0 
	IL_01d5:  call instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_01da:  ldarg.0 
	IL_01db:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_01e0:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_01e5:  ldarg.0 
	IL_01e6:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.TextBox::'.ctor'()
	IL_01eb:  stfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_01f0:  ldarg.0 
	IL_01f1:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_01f6:  ldc.i4.1 
	IL_01f7:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.TextBoxBase::set_Multiline(bool)
	IL_01fc:  ldarg.0 
	IL_01fd:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_0202:  ldc.i4.1 
	IL_0203:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.TextBoxBase::set_ReadOnly(bool)
	IL_0208:  ldarg.0 
	IL_0209:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_020e:  ldc.i4.2 
	IL_020f:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.TextBox::set_ScrollBars(valuetype [System.Windows.Forms]System.Windows.Forms.ScrollBars)
	IL_0214:  ldarg.0 
	IL_0215:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_021a:  ldc.i4.s 0x14
	IL_021c:  ldc.i4 276
	IL_0221:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_0226:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_022b:  ldarg.0 
	IL_022c:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_0231:  ldc.i4 520
	IL_0236:  ldc.i4 180
	IL_023b:  newobj instance void valuetype [System.Drawing]System.Drawing.Size::'.ctor'(int32, int32)
	IL_0240:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Size(valuetype [System.Drawing]System.Drawing.Size)
	IL_0245:  ldarg.0 
	IL_0246:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_024b:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::get_White()
	IL_0250:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_BackColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_0255:  ldarg.0 
	IL_0256:  call instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_025b:  ldarg.0 
	IL_025c:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_0261:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_0266:  ldarg.0 
	IL_0267:  ldarg.0 
	IL_0268:  ldstr bytearray (
	24 c1 58 ce 01 )                                 // $.X..
	
	IL_026d:  ldc.i4.s 0x14
	IL_026f:  ldc.i4.1 
	IL_0270:  call instance class [System.Windows.Forms]System.Windows.Forms.Button class RetopoAnnotateSetup.SetupForm::MakeButton(string, int32, bool)
	IL_0275:  stfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnInstall
	IL_027a:  ldarg.0 
	IL_027b:  ldarg.0 
	IL_027c:  ldstr bytearray (
	1c c8 70 ac 01 )                                 // ..p..
	
	IL_0281:  ldc.i4 132
	IL_0286:  ldc.i4.0 
	IL_0287:  call instance class [System.Windows.Forms]System.Windows.Forms.Button class RetopoAnnotateSetup.SetupForm::MakeButton(string, int32, bool)
	IL_028c:  stfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnUninstall
	IL_0291:  ldarg.0 
	IL_0292:  ldarg.0 
	IL_0293:  ldstr bytearray (
	ac c0 a9 c6 95 bc 01 )                           // .......
	
	IL_0298:  ldc.i4 244
	IL_029d:  ldc.i4.0 
	IL_029e:  call instance class [System.Windows.Forms]System.Windows.Forms.Button class RetopoAnnotateSetup.SetupForm::MakeButton(string, int32, bool)
	IL_02a3:  stfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnGuide
	IL_02a8:  ldarg.0 
	IL_02a9:  ldarg.0 
	IL_02aa:  ldstr bytearray (
	eb b2 30 ae 01 )                                 // ..0..
	
	IL_02af:  ldc.i4 428
	IL_02b4:  ldc.i4.0 
	IL_02b5:  call instance class [System.Windows.Forms]System.Windows.Forms.Button class RetopoAnnotateSetup.SetupForm::MakeButton(string, int32, bool)
	IL_02ba:  stfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnClose
	IL_02bf:  ldarg.0 
	IL_02c0:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnInstall
	IL_02c5:  ldloc.s 7
	IL_02c7:  brtrue.s IL_02d7

	IL_02c9:  ldarg.0 
	IL_02ca:  ldftn instance void class RetopoAnnotateSetup.SetupForm::'<.ctor>b__0'(object, class [mscorlib]System.EventArgs)
	IL_02d0:  newobj instance void class [mscorlib]System.EventHandler::'.ctor'(object, native int)
	IL_02d5:  stloc.s 7
	IL_02d7:  ldloc.s 7
	IL_02d9:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::add_Click(class [mscorlib]System.EventHandler)
	IL_02de:  ldarg.0 
	IL_02df:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnUninstall
	IL_02e4:  ldloc.s 8
	IL_02e6:  brtrue.s IL_02f6

	IL_02e8:  ldarg.0 
	IL_02e9:  ldftn instance void class RetopoAnnotateSetup.SetupForm::'<.ctor>b__1'(object, class [mscorlib]System.EventArgs)
	IL_02ef:  newobj instance void class [mscorlib]System.EventHandler::'.ctor'(object, native int)
	IL_02f4:  stloc.s 8
	IL_02f6:  ldloc.s 8
	IL_02f8:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::add_Click(class [mscorlib]System.EventHandler)
	IL_02fd:  ldarg.0 
	IL_02fe:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnGuide
	IL_0303:  ldloc.s 9
	IL_0305:  brtrue.s IL_0315

	IL_0307:  ldarg.0 
	IL_0308:  ldftn instance void class RetopoAnnotateSetup.SetupForm::'<.ctor>b__2'(object, class [mscorlib]System.EventArgs)
	IL_030e:  newobj instance void class [mscorlib]System.EventHandler::'.ctor'(object, native int)
	IL_0313:  stloc.s 9
	IL_0315:  ldloc.s 9
	IL_0317:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::add_Click(class [mscorlib]System.EventHandler)
	IL_031c:  ldarg.0 
	IL_031d:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnClose
	IL_0322:  ldloc.s 10
	IL_0324:  brtrue.s IL_0334

	IL_0326:  ldarg.0 
	IL_0327:  ldftn instance void class RetopoAnnotateSetup.SetupForm::'<.ctor>b__3'(object, class [mscorlib]System.EventArgs)
	IL_032d:  newobj instance void class [mscorlib]System.EventHandler::'.ctor'(object, native int)
	IL_0332:  stloc.s 10
	IL_0334:  ldloc.s 10
	IL_0336:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::add_Click(class [mscorlib]System.EventHandler)
	IL_033b:  ldarg.0 
	IL_033c:  ldarg.0 
	IL_033d:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnInstall
	IL_0342:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::set_AcceptButton(class [System.Windows.Forms]System.Windows.Forms.IButtonControl)
	IL_0347:  ldarg.0 
	IL_0348:  call class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> class RetopoAnnotateSetup.Installer::Detect()
	IL_034d:  stfld class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> RetopoAnnotateSetup.SetupForm::targets
	IL_0352:  ldarg.0 
	IL_0353:  ldfld class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> RetopoAnnotateSetup.SetupForm::targets
	IL_0358:  callvirt instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::GetEnumerator()
	IL_035d:  stloc.s 11
	.try { // 0
	  IL_035f:  br.s IL_037e

	  IL_0361:  ldloca.s 11
	  IL_0363:  call instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::get_Current()
	  IL_0368:  stloc.s 4
	  IL_036a:  ldarg.0 
	  IL_036b:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	  IL_0370:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/ObjectCollection class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::get_Items()
	  IL_0375:  ldloc.s 4
	  IL_0377:  ldc.i4.1 
	  IL_0378:  callvirt instance int32 class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/ObjectCollection::Add(object, bool)
	  IL_037d:  pop 
	  IL_037e:  ldloca.s 11
	  IL_0380:  call instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::MoveNext()
	  IL_0385:  brtrue.s IL_0361

	  IL_0387:  leave.s IL_0397

	} // end .try 0
	finally  { // 0
	  IL_0389:  ldloca.s 11
	  IL_038b:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>
	  IL_0391:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_0396:  endfinally 
	} // end handler 0
	IL_0397:  ldarg.0 
	IL_0398:  ldfld class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> RetopoAnnotateSetup.SetupForm::targets
	IL_039d:  callvirt instance int32 class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::get_Count()
	IL_03a2:  brtrue.s IL_03b1

	IL_03a4:  ldarg.0 
	IL_03a5:  ldstr bytearray (
	42 00 6c 00 65 00 6e 00 64 00 65 00 72 00 28 00  // B.l.e.n.d.e.r.(.
	34 00 2e 00 32 00 20 00 74 c7 c1 c0 29 00 20 00  // 4...2. .t...). .
	10 b6 94 b2 20 00 33 00 64 00 73 00 20 00 4d 00  // .... .3.d.s. .M.
	61 00 78 00 20 00 24 c1 58 ce 7c b9 20 00 3e cc  // a.x. .$.X.|. .>.
	c0 c9 20 00 bb ba 88 d5 b5 c2 c8 b2 e4 b2 2e 00  // .. .............
	01 )                                             // .
	
	IL_03aa:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	IL_03af:  br.s IL_042c

	IL_03b1:  ldarg.0 
	IL_03b2:  ldstr bytearray (
	1c bc ac ac 3a 00 20 00 01 )                     // ....:. ..
	
	IL_03b7:  ldarg.0 
	IL_03b8:  ldfld class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> RetopoAnnotateSetup.SetupForm::targets
	IL_03bd:  callvirt instance int32 class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::get_Count()
	IL_03c2:  box [mscorlib]System.Int32
	IL_03c7:  ldstr bytearray (
	1c ac 2e 00 20 00 5b 00 24 c1 58 ce 5d 00 7c b9  // .... .[.$.X.].|.
	20 00 04 b2 74 b9 74 ba 20 00 20 c1 dd d0 5c d5  //  ...t.t. . ...\.
	20 00 f3 ac d0 c5 20 00 24 c1 58 ce 69 d5 c8 b2  //  ..... .$.X.i...
	e4 b2 2e 00 01 )                                 // .....
	
	IL_03cc:  call string string::Concat(object, object, object)
	IL_03d1:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	IL_03d6:  ldarg.0 
	IL_03d7:  ldfld class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> RetopoAnnotateSetup.SetupForm::targets
	IL_03dc:  callvirt instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::GetEnumerator()
	IL_03e1:  stloc.s 12
	.try { // 1
	  IL_03e3:  br.s IL_0413

	  IL_03e5:  ldloca.s 12
	  IL_03e7:  call instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::get_Current()
	  IL_03ec:  stloc.s 5
	  IL_03ee:  ldloc.s 5
	  IL_03f0:  call bool class RetopoAnnotateSetup.Installer::IsInstalled(class RetopoAnnotateSetup.Target)
	  IL_03f5:  brfalse.s IL_0413

	  IL_03f7:  ldarg.0 
	  IL_03f8:  ldstr bytearray (
	b7 00 20 00 01 )                                 // .. ..
	
	  IL_03fd:  ldloc.s 5
	  IL_03ff:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0404:  ldstr bytearray (
	20 00 3a 00 20 00 74 c7 f8 bb 20 00 24 c1 58 ce  //  .:. .t... .$.X.
	28 b4 20 00 28 00 e4 b2 dc c2 20 00 24 c1 58 ce  // (. .(..... .$.X.
	58 d5 74 ba 20 00 5c cd e0 c2 20 00 84 bc 04 c8  // X.t. .\... .....
	3c c7 5c b8 20 00 50 ad b4 cc 29 00 01 )         // <.\. .P...)..
	
	  IL_0409:  call string string::Concat(string, string, string)
	  IL_040e:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	  IL_0413:  ldloca.s 12
	  IL_0415:  call instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::MoveNext()
	  IL_041a:  brtrue.s IL_03e5

	  IL_041c:  leave.s IL_042c

	} // end .try 1
	finally  { // 1
	  IL_041e:  ldloca.s 12
	  IL_0420:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>
	  IL_0426:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_042b:  endfinally 
	} // end handler 1
	IL_042c:  call string class RetopoAnnotateSetup.Installer::RunningApps()
	IL_0431:  stloc.s 6
	IL_0433:  ldloc.s 6
	IL_0435:  callvirt instance int32 string::get_Length()
	IL_043a:  ldc.i4.0 
	IL_043b:  ble.s IL_0454

	IL_043d:  ldarg.0 
	IL_043e:  ldstr bytearray (
	a0 26 20 00 e4 c2 89 d5 20 00 11 c9 3a 00 20 00  // .& ..... ...:. .
	01 )                                             // .
	
	IL_0443:  ldloc.s 6
	IL_0445:  ldstr bytearray (
	20 00 14 20 20 00 24 c1 58 ce 20 00 c4 d6 20 00  //  ..  .$.X. ... .
	74 d5 f9 b2 20 00 04 d5 5c b8 f8 ad a8 b7 44 c7  // t... ...\.....D.
	20 00 e4 b2 dc c2 20 00 dc c2 91 c7 58 d5 38 c1  //  ..... .....X.8.
	94 c6 2e 00 20 00 28 00 42 00 6c 00 65 00 6e 00  // .... .(.B.l.e.n.
	64 00 65 00 72 00 20 00 94 b2 20 00 24 c1 58 ce  // d.e.r. ... .$.X.
	20 00 04 c8 d0 c5 20 00 eb b2 94 b2 20 00 83 ac  //  ..... ..... ...
	44 c7 20 00 8c ad a5 c7 3a 00 20 00 eb b2 44 c7  // D. .....:. ...D.
	20 00 4c b5 20 00 58 d6 bd ac 24 c1 15 c8 74 c7  //  .L. .X...$...t.
	20 00 6e b3 b4 c5 68 c3 c8 c9 20 00 18 c2 20 00  //  .n...h... ... .
	88 c7 4c c7 29 00 01 )                           // ..L.)..
	
	IL_044a:  call string string::Concat(string, string, string)
	IL_044f:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	IL_0454:  ret 
    } // end of method SetupForm::.ctor

    // method line 18
    .method private hidebysig 
           instance default class [System.Windows.Forms]System.Windows.Forms.Button MakeButton (string text, int32 x, bool primary)  cil managed 
    {
        // Method begins at RVA 0x322c
	// Code size 112 (0x70)
	.maxstack 4
	.locals init (
		class [System.Windows.Forms]System.Windows.Forms.Button	V_0)
	IL_0000:  newobj instance void class [System.Windows.Forms]System.Windows.Forms.Button::'.ctor'()
	IL_0005:  stloc.0 
	IL_0006:  ldloc.0 
	IL_0007:  ldarg.1 
	IL_0008:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Text(string)
	IL_000d:  ldloc.0 
	IL_000e:  ldarg.2 
	IL_000f:  ldc.i4 468
	IL_0014:  newobj instance void valuetype [System.Drawing]System.Drawing.Point::'.ctor'(int32, int32)
	IL_0019:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Location(valuetype [System.Drawing]System.Drawing.Point)
	IL_001e:  ldloc.0 
	IL_001f:  ldc.i4.s 0x68
	IL_0021:  ldc.i4.s 0x24
	IL_0023:  newobj instance void valuetype [System.Drawing]System.Drawing.Size::'.ctor'(int32, int32)
	IL_0028:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Size(valuetype [System.Drawing]System.Drawing.Size)
	IL_002d:  ldloc.0 
	IL_002e:  ldc.i4.0 
	IL_002f:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.ButtonBase::set_FlatStyle(valuetype [System.Windows.Forms]System.Windows.Forms.FlatStyle)
	IL_0034:  ldarg.3 
	IL_0035:  brfalse.s IL_0062

	IL_0037:  ldloc.0 
	IL_0038:  ldc.i4.s 0x2e
	IL_003a:  ldc.i4.s 0x6e
	IL_003c:  ldc.i4 230
	IL_0041:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::FromArgb(int32, int32, int32)
	IL_0046:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_BackColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_004b:  ldloc.0 
	IL_004c:  call valuetype [System.Drawing]System.Drawing.Color valuetype [System.Drawing]System.Drawing.Color::get_White()
	IL_0051:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_ForeColor(valuetype [System.Drawing]System.Drawing.Color)
	IL_0056:  ldloc.0 
	IL_0057:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.FlatButtonAppearance class [System.Windows.Forms]System.Windows.Forms.ButtonBase::get_FlatAppearance()
	IL_005c:  ldc.i4.0 
	IL_005d:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.FlatButtonAppearance::set_BorderSize(int32)
	IL_0062:  ldarg.0 
	IL_0063:  call instance class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection class [System.Windows.Forms]System.Windows.Forms.Control::get_Controls()
	IL_0068:  ldloc.0 
	IL_0069:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control/ControlCollection::Add(class [System.Windows.Forms]System.Windows.Forms.Control)
	IL_006e:  ldloc.0 
	IL_006f:  ret 
    } // end of method SetupForm::MakeButton

    // method line 19
    .method private hidebysig 
           instance default void Log (string s)  cil managed 
    {
        // Method begins at RVA 0x32a8
	// Code size 23 (0x17)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldfld class [System.Windows.Forms]System.Windows.Forms.TextBox RetopoAnnotateSetup.SetupForm::logBox
	IL_0006:  ldarg.1 
	IL_0007:  call string class [mscorlib]System.Environment::get_NewLine()
	IL_000c:  call string string::Concat(string, string)
	IL_0011:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.TextBoxBase::AppendText(string)
	IL_0016:  ret 
    } // end of method SetupForm::Log

    // method line 20
    .method private hidebysig 
           instance default void Run (bool install)  cil managed 
    {
        // Method begins at RVA 0x32c0
	// Code size 486 (0x1e6)
	.maxstack 5
	.locals init (
		int32	V_0,
		object	V_1,
		class RetopoAnnotateSetup.Target	V_2,
		string	V_3,
		bool	V_4,
		class [mscorlib]System.Collections.IEnumerator	V_5,
		class [mscorlib]System.IDisposable	V_6,
		bool	V_7,
		object[]	V_8,
		object[]	V_9)
	IL_0000:  ldarg.0 
	IL_0001:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_0006:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::get_CheckedItems()
	IL_000b:  callvirt instance int32 class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection::get_Count()
	IL_0010:  brtrue.s IL_001e

	IL_0012:  ldarg.0 
	IL_0013:  ldstr bytearray (
	20 c1 dd d0 1c b4 20 00 6d d5 a9 ba 74 c7 20 00  //  ..... .m...t. .
	c6 c5 b5 c2 c8 b2 e4 b2 2e 00 01 )               // ...........
	
	IL_0018:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	IL_001d:  ret 
	IL_001e:  ldarg.0 
	IL_001f:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnInstall
	IL_0024:  ldarg.0 
	IL_0025:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnUninstall
	IL_002a:  ldc.i4.0 
	IL_002b:  dup 
	IL_002c:  stloc.s 4
	IL_002e:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Enabled(bool)
	IL_0033:  ldloc.s 4
	IL_0035:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Enabled(bool)
	IL_003a:  ldarg.0 
	IL_003b:  call class [System.Windows.Forms]System.Windows.Forms.Cursor class [System.Windows.Forms]System.Windows.Forms.Cursors::get_WaitCursor()
	IL_0040:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Cursor(class [System.Windows.Forms]System.Windows.Forms.Cursor)
	IL_0045:  ldc.i4.0 
	IL_0046:  stloc.0 
	IL_0047:  ldarg.0 
	IL_0048:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_004d:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::get_CheckedItems()
	IL_0052:  callvirt instance class [mscorlib]System.Collections.IEnumerator class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection::GetEnumerator()
	IL_0057:  stloc.s 5
	.try { // 0
	  IL_0059:  br.s IL_00c8

	  IL_005b:  ldloc.s 5
	  IL_005d:  callvirt instance object class [mscorlib]System.Collections.IEnumerator::get_Current()
	  IL_0062:  stloc.1 
	  IL_0063:  ldloc.1 
	  IL_0064:  castclass RetopoAnnotateSetup.Target
	  IL_0069:  stloc.2 
	  IL_006a:  ldarg.0 
	  IL_006b:  ldarg.1 
	  IL_006c:  brtrue.s IL_0075

	  IL_006e:  ldstr bytearray (
	1c c8 70 ac 20 00 11 c9 3a 00 20 00 01 )         // ..p. ...:. ..
	
	  IL_0073:  br.s IL_007a

	  IL_0075:  ldstr bytearray (
	24 c1 58 ce 20 00 11 c9 3a 00 20 00 01 )         // $.X. ...:. ..
	
	  IL_007a:  ldloc.2 
	  IL_007b:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_0080:  ldstr " ..."
	  IL_0085:  call string string::Concat(string, string, string)
	  IL_008a:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	  IL_008f:  call void class [System.Windows.Forms]System.Windows.Forms.Application::DoEvents()
	  IL_0094:  ldarg.1 
	  IL_0095:  brtrue.s IL_00ab

	  IL_0097:  ldloc.2 
	  IL_0098:  ldarg.0 
	  IL_0099:  ldftn instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	  IL_009f:  newobj instance void class [mscorlib]System.Action`1<string>::'.ctor'(object, native int)
	  IL_00a4:  call bool class RetopoAnnotateSetup.Installer::Uninstall(class RetopoAnnotateSetup.Target, class [mscorlib]System.Action`1<string>)
	  IL_00a9:  br.s IL_00bd

	  IL_00ab:  ldloc.2 
	  IL_00ac:  ldarg.0 
	  IL_00ad:  ldftn instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	  IL_00b3:  newobj instance void class [mscorlib]System.Action`1<string>::'.ctor'(object, native int)
	  IL_00b8:  call bool class RetopoAnnotateSetup.Installer::Install(class RetopoAnnotateSetup.Target, class [mscorlib]System.Action`1<string>)
	  IL_00bd:  brfalse.s IL_00c3

	  IL_00bf:  ldloc.0 
	  IL_00c0:  ldc.i4.1 
	  IL_00c1:  add 
	  IL_00c2:  stloc.0 
	  IL_00c3:  call void class [System.Windows.Forms]System.Windows.Forms.Application::DoEvents()
	  IL_00c8:  ldloc.s 5
	  IL_00ca:  callvirt instance bool class [mscorlib]System.Collections.IEnumerator::MoveNext()
	  IL_00cf:  brtrue.s IL_005b

	  IL_00d1:  leave.s IL_00e8

	} // end .try 0
	finally  { // 0
	  IL_00d3:  ldloc.s 5
	  IL_00d5:  isinst [mscorlib]System.IDisposable
	  IL_00da:  stloc.s 6
	  IL_00dc:  ldloc.s 6
	  IL_00de:  brfalse.s IL_00e7

	  IL_00e0:  ldloc.s 6
	  IL_00e2:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_00e7:  endfinally 
	} // end handler 0
	IL_00e8:  ldarg.0 
	IL_00e9:  call class [System.Windows.Forms]System.Windows.Forms.Cursor class [System.Windows.Forms]System.Windows.Forms.Cursors::get_Default()
	IL_00ee:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Cursor(class [System.Windows.Forms]System.Windows.Forms.Cursor)
	IL_00f3:  ldarg.0 
	IL_00f4:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnInstall
	IL_00f9:  ldarg.0 
	IL_00fa:  ldfld class [System.Windows.Forms]System.Windows.Forms.Button RetopoAnnotateSetup.SetupForm::btnUninstall
	IL_00ff:  ldc.i4.1 
	IL_0100:  dup 
	IL_0101:  stloc.s 7
	IL_0103:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Enabled(bool)
	IL_0108:  ldloc.s 7
	IL_010a:  callvirt instance void class [System.Windows.Forms]System.Windows.Forms.Control::set_Enabled(bool)
	IL_010f:  ldarg.0 
	IL_0110:  ldarg.1 
	IL_0111:  brtrue.s IL_0162

	IL_0113:  ldc.i4.5 
	IL_0114:  newarr [mscorlib]System.Object
	IL_0119:  stloc.s 8
	IL_011b:  ldloc.s 8
	IL_011d:  ldc.i4.0 
	IL_011e:  ldstr bytearray (
	1c c8 70 ac 20 00 44 c6 cc b8 20 00 28 00 01 )   // ..p. .D... .(..
	
	IL_0123:  stelem.ref 
	IL_0124:  ldloc.s 8
	IL_0126:  ldc.i4.1 
	IL_0127:  ldloc.0 
	IL_0128:  box [mscorlib]System.Int32
	IL_012d:  stelem.ref 
	IL_012e:  ldloc.s 8
	IL_0130:  ldc.i4.2 
	IL_0131:  ldstr "/"
	IL_0136:  stelem.ref 
	IL_0137:  ldloc.s 8
	IL_0139:  ldc.i4.3 
	IL_013a:  ldarg.0 
	IL_013b:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_0140:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::get_CheckedItems()
	IL_0145:  callvirt instance int32 class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection::get_Count()
	IL_014a:  box [mscorlib]System.Int32
	IL_014f:  stelem.ref 
	IL_0150:  ldloc.s 8
	IL_0152:  ldc.i4.4 
	IL_0153:  ldstr ")"
	IL_0158:  stelem.ref 
	IL_0159:  ldloc.s 8
	IL_015b:  call string string::Concat(object[])
	IL_0160:  br.s IL_01af

	IL_0162:  ldc.i4.5 
	IL_0163:  newarr [mscorlib]System.Object
	IL_0168:  stloc.s 9
	IL_016a:  ldloc.s 9
	IL_016c:  ldc.i4.0 
	IL_016d:  ldstr bytearray (
	44 c6 cc b8 21 00 20 00 28 00 01 )               // D...!. .(..
	
	IL_0172:  stelem.ref 
	IL_0173:  ldloc.s 9
	IL_0175:  ldc.i4.1 
	IL_0176:  ldloc.0 
	IL_0177:  box [mscorlib]System.Int32
	IL_017c:  stelem.ref 
	IL_017d:  ldloc.s 9
	IL_017f:  ldc.i4.2 
	IL_0180:  ldstr "/"
	IL_0185:  stelem.ref 
	IL_0186:  ldloc.s 9
	IL_0188:  ldc.i4.3 
	IL_0189:  ldarg.0 
	IL_018a:  ldfld class [System.Windows.Forms]System.Windows.Forms.CheckedListBox RetopoAnnotateSetup.SetupForm::list
	IL_018f:  callvirt instance class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection class [System.Windows.Forms]System.Windows.Forms.CheckedListBox::get_CheckedItems()
	IL_0194:  callvirt instance int32 class [System.Windows.Forms]System.Windows.Forms.CheckedListBox/CheckedItemCollection::get_Count()
	IL_0199:  box [mscorlib]System.Int32
	IL_019e:  stelem.ref 
	IL_019f:  ldloc.s 9
	IL_01a1:  ldc.i4.4 
	IL_01a2:  ldstr bytearray (
	29 00 20 00 20 00 42 00 6c 00 65 00 6e 00 64 00  // ). . .B.l.e.n.d.
	65 00 72 00 3a 00 20 00 4e 00 20 00 ac c0 74 c7  // e.r.:. .N. ...t.
	dc b4 14 bc 20 00 3e 00 20 00 52 00 65 00 74 00  // .... .>. .R.e.t.
	6f 00 70 00 6f 00 20 00 ed d0 20 00 2f 00 20 00  // o.p.o. ... ./. .
	33 00 64 00 73 00 20 00 4d 00 61 00 78 00 3a 00  // 3.d.s. .M.a.x.:.
	20 00 c1 c0 e8 b2 20 00 54 ba 74 b2 20 00 52 00  //  ..... .T.t. .R.
	65 00 74 00 6f 00 70 00 6f 00 01 )               // e.t.o.p.o..
	
	IL_01a7:  stelem.ref 
	IL_01a8:  ldloc.s 9
	IL_01aa:  call string string::Concat(object[])
	IL_01af:  call instance void class RetopoAnnotateSetup.SetupForm::Log(string)
	IL_01b4:  call string class RetopoAnnotateSetup.Installer::RunningApps()
	IL_01b9:  stloc.3 
	IL_01ba:  ldarg.1 
	IL_01bb:  brfalse.s IL_01e5

	IL_01bd:  ldloc.3 
	IL_01be:  callvirt instance int32 string::get_Length()
	IL_01c3:  ldc.i4.0 
	IL_01c4:  ble.s IL_01e5

	IL_01c6:  ldarg.0 
	IL_01c7:  ldstr bytearray (
	c0 c9 08 ae 20 00 e4 c2 89 d5 20 00 11 c9 78 c7  // .... ..... ...x.
	20 00 01 )                                       //  ..
	
	IL_01cc:  ldloc.3 
	IL_01cd:  ldstr bytearray (
	20 00 d0 c5 94 b2 20 00 44 c5 c1 c9 20 00 01 c8  //  ..... .D... ...
	a9 c6 18 b4 c0 c9 20 00 4a c5 58 c5 b5 c2 c8 b2  // ...... .J.X.....
	e4 b2 2e 00 0a 00 0a 00 91 c7 c5 c5 44 c7 20 00  // ............D. .
	00 c8 a5 c7 5c d5 20 00 a4 b4 20 00 04 d5 5c b8  // ....\. ... ...\.
	f8 ad a8 b7 44 c7 20 00 44 c6 04 c8 88 d7 20 00  // ....D. .D..... .
	d0 ae e4 b2 00 ac 20 00 e4 b2 dc c2 20 00 e4 c2  // ...... ..... ...
	89 d5 58 d5 38 c1 94 c6 2e 00 0a 00 0a 00 b7 00  // ..X.8...........
	20 00 33 00 64 00 73 00 20 00 4d 00 61 00 78 00  //  .3.d.s. .M.a.x.
	3a 00 20 00 e4 b2 dc c2 20 00 1c cf 74 ba 20 00  // :. ..... ...t. .
	27 00 52 00 65 00 74 00 6f 00 70 00 6f 00 20 00  // '.R.e.t.o.p.o. .
	41 00 6e 00 6e 00 6f 00 74 00 61 00 74 00 65 00  // A.n.n.o.t.a.t.e.
	27 00 20 00 3d cc 74 c7 20 00 90 c7 d9 b3 3c c7  // '. .=.t. .....<.
	5c b8 20 00 f4 c5 ac b9 e0 ac 2c 00 0a 00 20 00  // \. .......,... .
	20 00 20 00 c1 c0 e8 b2 20 00 54 ba 74 b2 14 bc  //  . ..... .T.t...
	20 00 e8 b9 20 00 24 c6 78 b9 bd ca d0 c5 20 00  //  ... .$.x..... .
	27 00 52 00 65 00 74 00 6f 00 70 00 6f 00 27 00  // '.R.e.t.o.p.o.'.
	20 00 54 ba 74 b2 00 ac 20 00 dd c0 41 ae c8 b2  //  .T.t... ...A...
	e4 b2 2e 00 0a 00 b7 00 20 00 42 00 6c 00 65 00  // ........ .B.l.e.
	6e 00 64 00 65 00 72 00 3a 00 20 00 33 00 44 00  // n.d.e.r.:. .3.D.
	20 00 f0 bd d0 c5 1c c1 20 00 4e 00 20 00 a4 d0  //  ....... .N. ...
	20 00 92 21 20 00 24 c6 78 b9 bd ca 20 00 ac c0  //  ..! .$.x... ...
	74 c7 dc b4 14 bc 58 c7 20 00 27 00 52 00 65 00  // t.....X. .'.R.e.
	74 00 6f 00 70 00 6f 00 27 00 20 00 ed d0 01 )   // t.o.p.o.'. ....
	
	IL_01d2:  call string string::Concat(string, string, string)
	IL_01d7:  ldstr bytearray (
	e4 b2 dc c2 20 00 dc c2 91 c7 20 00 44 d5 94 c6  // .... ..... .D...
	01 )                                             // .
	
	IL_01dc:  ldc.i4.0 
	IL_01dd:  ldc.i4.s 0x40
	IL_01df:  call valuetype [System.Windows.Forms]System.Windows.Forms.DialogResult class [System.Windows.Forms]System.Windows.Forms.MessageBox::Show(class [System.Windows.Forms]System.Windows.Forms.IWin32Window, string, string, valuetype [System.Windows.Forms]System.Windows.Forms.MessageBoxButtons, valuetype [System.Windows.Forms]System.Windows.Forms.MessageBoxIcon)
	IL_01e4:  pop 
	IL_01e5:  ret 
    } // end of method SetupForm::Run

    // method line 21
    .method private hidebysig 
           instance default void ShowGuide ()  cil managed 
    {
        // Method begins at RVA 0x34c4
	// Code size 65 (0x41)
	.maxstack 4
	.locals init (
		string	V_0)
	IL_0000:  call string class [mscorlib]System.IO.Path::GetTempPath()
	IL_0005:  ldstr bytearray (
	52 00 65 00 74 00 6f 00 70 00 6f 00 41 00 6e 00  // R.e.t.o.p.o.A.n.
	6e 00 6f 00 74 00 61 00 74 00 65 00 5f 00 ac c0  // n.o.t.a.t.e._...
	a9 c6 95 bc 2e 00 74 00 78 00 74 00 01 )         // ......t.x.t..
	
	IL_000a:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_000f:  stloc.0 
	IL_0010:  ldloc.0 
	IL_0011:  ldstr "README.txt"
	IL_0016:  call unsigned int8[] class RetopoAnnotateSetup.Installer::Resource(string)
	IL_001b:  call void class [mscorlib]System.IO.File::WriteAllBytes(string, unsigned int8[])
	.try { // 0
	  IL_0020:  ldstr "notepad.exe"
	  IL_0025:  ldstr "\""
	  IL_002a:  ldloc.0 
	  IL_002b:  ldstr "\""
	  IL_0030:  call string string::Concat(string, string, string)
	  IL_0035:  call class [System]System.Diagnostics.Process class [System]System.Diagnostics.Process::Start(string, string)
	  IL_003a:  pop 
	  IL_003b:  leave.s IL_0040

	} // end .try 0
	catch class [mscorlib]System.Object { // 0
	  IL_003d:  pop 
	  IL_003e:  leave.s IL_0040

	} // end handler 0
	IL_0040:  ret 
    } // end of method SetupForm::ShowGuide

    // method line 22
    .method private hidebysig 
           instance default void '<.ctor>b__0' (object param0, class [mscorlib]System.EventArgs param1)  cil managed 
    {
        .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x2d87
	// Code size 8 (0x8)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldc.i4.1 
	IL_0002:  call instance void class RetopoAnnotateSetup.SetupForm::Run(bool)
	IL_0007:  ret 
    } // end of method SetupForm::<.ctor>b__0

    // method line 23
    .method private hidebysig 
           instance default void '<.ctor>b__1' (object param0, class [mscorlib]System.EventArgs param1)  cil managed 
    {
        .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x2d90
	// Code size 8 (0x8)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldc.i4.0 
	IL_0002:  call instance void class RetopoAnnotateSetup.SetupForm::Run(bool)
	IL_0007:  ret 
    } // end of method SetupForm::<.ctor>b__1

    // method line 24
    .method private hidebysig 
           instance default void '<.ctor>b__2' (object param0, class [mscorlib]System.EventArgs param1)  cil managed 
    {
        .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x2d99
	// Code size 7 (0x7)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  call instance void class RetopoAnnotateSetup.SetupForm::ShowGuide()
	IL_0006:  ret 
    } // end of method SetupForm::<.ctor>b__2

    // method line 25
    .method private hidebysig 
           instance default void '<.ctor>b__3' (object param0, class [mscorlib]System.EventArgs param1)  cil managed 
    {
        .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x2da1
	// Code size 7 (0x7)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  call instance void class [System.Windows.Forms]System.Windows.Forms.Form::Close()
	IL_0006:  ret 
    } // end of method SetupForm::<.ctor>b__3

  } // end of class RetopoAnnotateSetup.SetupForm
}

.namespace RetopoAnnotateSetup
{
  .class private auto ansi abstract sealed beforefieldinit Program
  	extends [mscorlib]System.Object
  {

    // method line 26
    .method private static hidebysig 
           default int32 Main (string[] args)  cil managed 
    {
        .custom instance void class [mscorlib]System.STAThreadAttribute::'.ctor'() =  (01 00 00 00 ) // ....

        // Method begins at RVA 0x354c
	.entrypoint
	// Code size 410 (0x19a)
	.maxstack 5
	.locals init (
		bool	V_0,
		bool	V_1,
		string	V_2,
		string	V_3,
		int32	V_4,
		class RetopoAnnotateSetup.Target	V_5,
		class [mscorlib]System.Action`1<string>	V_6,
		class [mscorlib]System.Action`1<string>	V_7,
		class RetopoAnnotateSetup.Program/'<>c__DisplayClass4'	V_8,
		string[]	V_9,
		int32	V_10,
		char[]	V_11,
		valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>	V_12)
	IL_0000:  ldc.i4.0 
	IL_0001:  stloc.0 
	IL_0002:  ldc.i4.0 
	IL_0003:  stloc.1 
	IL_0004:  ldarg.0 
	IL_0005:  stloc.s 9
	IL_0007:  ldc.i4.0 
	IL_0008:  stloc.s 10
	IL_000a:  br.s IL_008b

	IL_000c:  ldloc.s 9
	IL_000e:  ldloc.s 10
	IL_0010:  ldelem.ref 
	IL_0011:  stloc.2 
	IL_0012:  ldloc.2 
	IL_0013:  callvirt instance string string::ToLowerInvariant()
	IL_0018:  stloc.3 
	IL_0019:  ldloc.3 
	IL_001a:  ldstr "/s"
	IL_001f:  call bool string::op_Equality(string, string)
	IL_0024:  brtrue.s IL_0033

	IL_0026:  ldloc.3 
	IL_0027:  ldstr "/silent"
	IL_002c:  call bool string::op_Equality(string, string)
	IL_0031:  brfalse.s IL_0037

	IL_0033:  ldc.i4.1 
	IL_0034:  stloc.0 
	IL_0035:  br.s IL_0085

	IL_0037:  ldloc.3 
	IL_0038:  ldstr "/u"
	IL_003d:  call bool string::op_Equality(string, string)
	IL_0042:  brtrue.s IL_0051

	IL_0044:  ldloc.3 
	IL_0045:  ldstr "/uninstall"
	IL_004a:  call bool string::op_Equality(string, string)
	IL_004f:  brfalse.s IL_0057

	IL_0051:  ldc.i4.1 
	IL_0052:  stloc.1 
	IL_0053:  ldc.i4.1 
	IL_0054:  stloc.0 
	IL_0055:  br.s IL_0085

	IL_0057:  ldloc.3 
	IL_0058:  ldstr "/root="
	IL_005d:  callvirt instance bool string::StartsWith(string)
	IL_0062:  brfalse.s IL_0085

	IL_0064:  ldloc.2 
	IL_0065:  ldc.i4.6 
	IL_0066:  callvirt instance string string::Substring(int32)
	IL_006b:  ldc.i4.1 
	IL_006c:  newarr [mscorlib]System.Char
	IL_0071:  stloc.s 11
	IL_0073:  ldloc.s 11
	IL_0075:  ldc.i4.0 
	IL_0076:  ldc.i4.s 0x22
	IL_0078:  stelem.i2 
	IL_0079:  ldloc.s 11
	IL_007b:  callvirt instance string string::Trim(char[])
	IL_0080:  stsfld string RetopoAnnotateSetup.Installer::TestRoot
	IL_0085:  ldloc.s 10
	IL_0087:  ldc.i4.1 
	IL_0088:  add 
	IL_0089:  stloc.s 10
	IL_008b:  ldloc.s 10
	IL_008d:  ldloc.s 9
	IL_008f:  ldlen 
	IL_0090:  conv.i4 
	IL_0091:  blt IL_000c

	IL_0096:  ldloc.0 
	IL_0097:  brfalse IL_0183

	IL_009c:  ldnull 
	IL_009d:  stloc.s 6
	IL_009f:  ldnull 
	IL_00a0:  stloc.s 7
	IL_00a2:  newobj instance void class RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::'.ctor'()
	IL_00a7:  stloc.s 8
	IL_00a9:  ldloc.s 8
	IL_00ab:  newobj instance void class [mscorlib]System.Text.StringBuilder::'.ctor'()
	IL_00b0:  stfld class [mscorlib]System.Text.StringBuilder RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::sb
	IL_00b5:  ldc.i4.0 
	IL_00b6:  stloc.s 4
	IL_00b8:  call class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target> class RetopoAnnotateSetup.Installer::Detect()
	IL_00bd:  callvirt instance valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<!0> class [mscorlib]System.Collections.Generic.List`1<class RetopoAnnotateSetup.Target>::GetEnumerator()
	IL_00c2:  stloc.s 12
	.try { // 0
	  IL_00c4:  br.s IL_013e

	  IL_00c6:  ldloca.s 12
	  IL_00c8:  call instance !0 valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::get_Current()
	  IL_00cd:  stloc.s 5
	  IL_00cf:  ldloc.s 8
	  IL_00d1:  ldfld class [mscorlib]System.Text.StringBuilder RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::sb
	  IL_00d6:  ldstr "["
	  IL_00db:  ldloc.s 5
	  IL_00dd:  ldfld string RetopoAnnotateSetup.Target::Label
	  IL_00e2:  ldstr "] "
	  IL_00e7:  ldloc.s 5
	  IL_00e9:  ldfld string RetopoAnnotateSetup.Target::Dir
	  IL_00ee:  call string string::Concat(string, string, string, string)
	  IL_00f3:  callvirt instance class [mscorlib]System.Text.StringBuilder class [mscorlib]System.Text.StringBuilder::AppendLine(string)
	  IL_00f8:  pop 
	  IL_00f9:  ldloc.1 
	  IL_00fa:  brtrue.s IL_011a

	  IL_00fc:  ldloc.s 5
	  IL_00fe:  ldloc.s 7
	  IL_0100:  brtrue.s IL_0111

	  IL_0102:  ldloc.s 8
	  IL_0104:  ldftn instance void class RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::'<Main>b__1'(string)
	  IL_010a:  newobj instance void class [mscorlib]System.Action`1<string>::'.ctor'(object, native int)
	  IL_010f:  stloc.s 7
	  IL_0111:  ldloc.s 7
	  IL_0113:  call bool class RetopoAnnotateSetup.Installer::Install(class RetopoAnnotateSetup.Target, class [mscorlib]System.Action`1<string>)
	  IL_0118:  br.s IL_0136

	  IL_011a:  ldloc.s 5
	  IL_011c:  ldloc.s 6
	  IL_011e:  brtrue.s IL_012f

	  IL_0120:  ldloc.s 8
	  IL_0122:  ldftn instance void class RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::'<Main>b__0'(string)
	  IL_0128:  newobj instance void class [mscorlib]System.Action`1<string>::'.ctor'(object, native int)
	  IL_012d:  stloc.s 6
	  IL_012f:  ldloc.s 6
	  IL_0131:  call bool class RetopoAnnotateSetup.Installer::Uninstall(class RetopoAnnotateSetup.Target, class [mscorlib]System.Action`1<string>)
	  IL_0136:  brtrue.s IL_013e

	  IL_0138:  ldloc.s 4
	  IL_013a:  ldc.i4.1 
	  IL_013b:  add 
	  IL_013c:  stloc.s 4
	  IL_013e:  ldloca.s 12
	  IL_0140:  call instance bool valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>::MoveNext()
	  IL_0145:  brtrue IL_00c6

	  IL_014a:  leave.s IL_015a

	} // end .try 0
	finally  { // 0
	  IL_014c:  ldloca.s 12
	  IL_014e:  constrained. valuetype [mscorlib]System.Collections.Generic.List`1/Enumerator<class RetopoAnnotateSetup.Target>
	  IL_0154:  callvirt instance void class [mscorlib]System.IDisposable::Dispose()
	  IL_0159:  endfinally 
	} // end handler 0
	IL_015a:  call string class [mscorlib]System.IO.Path::GetTempPath()
	IL_015f:  ldstr "RetopoAnnotateSetup.log"
	IL_0164:  call string class [mscorlib]System.IO.Path::Combine(string, string)
	IL_0169:  ldloc.s 8
	IL_016b:  ldfld class [mscorlib]System.Text.StringBuilder RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::sb
	IL_0170:  callvirt instance string object::ToString()
	IL_0175:  ldc.i4.1 
	IL_0176:  newobj instance void class [mscorlib]System.Text.UTF8Encoding::'.ctor'(bool)
	IL_017b:  call void class [mscorlib]System.IO.File::WriteAllText(string, string, class [mscorlib]System.Text.Encoding)
	IL_0180:  ldloc.s 4
	IL_0182:  ret 
	IL_0183:  call void class [System.Windows.Forms]System.Windows.Forms.Application::EnableVisualStyles()
	IL_0188:  ldc.i4.0 
	IL_0189:  call void class [System.Windows.Forms]System.Windows.Forms.Application::SetCompatibleTextRenderingDefault(bool)
	IL_018e:  newobj instance void class RetopoAnnotateSetup.SetupForm::'.ctor'()
	IL_0193:  call void class [System.Windows.Forms]System.Windows.Forms.Application::Run(class [System.Windows.Forms]System.Windows.Forms.Form)
	IL_0198:  ldc.i4.0 
	IL_0199:  ret 
    } // end of method Program::Main

  .class nested private auto ansi sealed beforefieldinit '<>c__DisplayClass4'
  	extends [mscorlib]System.Object
  {
    .custom instance void class [mscorlib]System.Runtime.CompilerServices.CompilerGeneratedAttribute::'.ctor'() =  (01 00 00 00 ) // ....

    .field  public  class [mscorlib]System.Text.StringBuilder sb

    // method line 27
    .method public hidebysig specialname rtspecialname 
           instance default void '.ctor' ()  cil managed 
    {
        // Method begins at RVA 0x3524
	// Code size 7 (0x7)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  call instance void object::'.ctor'()
	IL_0006:  ret 
    } // end of method <>c__DisplayClass4::.ctor

    // method line 28
    .method public hidebysig 
           instance default void '<Main>b__0' (string s)  cil managed 
    {
        // Method begins at RVA 0x352c
	// Code size 14 (0xe)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldfld class [mscorlib]System.Text.StringBuilder RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::sb
	IL_0006:  ldarg.1 
	IL_0007:  callvirt instance class [mscorlib]System.Text.StringBuilder class [mscorlib]System.Text.StringBuilder::AppendLine(string)
	IL_000c:  pop 
	IL_000d:  ret 
    } // end of method <>c__DisplayClass4::<Main>b__0

    // method line 29
    .method public hidebysig 
           instance default void '<Main>b__1' (string s)  cil managed 
    {
        // Method begins at RVA 0x353b
	// Code size 14 (0xe)
	.maxstack 8
	IL_0000:  ldarg.0 
	IL_0001:  ldfld class [mscorlib]System.Text.StringBuilder RetopoAnnotateSetup.Program/'<>c__DisplayClass4'::sb
	IL_0006:  ldarg.1 
	IL_0007:  callvirt instance class [mscorlib]System.Text.StringBuilder class [mscorlib]System.Text.StringBuilder::AppendLine(string)
	IL_000c:  pop 
	IL_000d:  ret 
    } // end of method <>c__DisplayClass4::<Main>b__1

  } // end of class <>c__DisplayClass4

  } // end of class RetopoAnnotateSetup.Program
}

