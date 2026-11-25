-- Retopo Annotate 1.6 스캔 자동 테스트
-- 사용: 설치 후 Max 를 다시 켜고 → 새 빈 씬 → Scripting > Run Script... 에서 이 파일 실행
--       결과는 MAXScript 리스너(F11)에 [TEST] 로 찍힘. 그 내용을 그대로 복사해 보내 주세요.
(
	local ok = 0
	local bad = 0
	fn rep okFlag msg = (format "[TEST] % %\n" (if okFlag then "OK  " else "FAIL") msg; okFlag)
	fn quadInfo obj =
	(
		local n = polyop.getNumFaces obj
		local q = 0
		for f = 1 to n do if (polyop.getFaceDeg obj f) == 4 do q += 1
		#(n, q)
	)

	clearListener()
	format "[TEST] Max % / 스크립트 폴더: %\n" ((maxVersion())[1] / 1000) RA_ScriptDir
	if RA_S == undefined or ra_scanMerge == undefined then
		format "[TEST] FAIL RetopoAnnotate 스크립트가 로드되지 않았습니다 (메뉴 Retopo > Retopo Annotate 를 한 번 연 뒤 다시 실행)\n"
	else
	(
		-- 1) 엔진(DLL) 로드
		local q = ra_quadEngine()
		if rep (q != undefined) "RAKeys.dll 안의 RAQuad 엔진 로드" then ok += 1 else bad += 1

		-- 2) 겹친 두 오브젝트 합치기 (상자 + 원기둥) — 전부 쿼드, 시간
		local b = Box length:40 width:60 height:30 pos:[0, 0, 0] name:"RA_Test_Box"
		local c = Cylinder radius:15 height:50 pos:[0, 0, -45] sides:32 name:"RA_Test_Cyl"
		RA_S.spacing = 4.0
		RA_S.scanTarget = 0
		RA_S.scanSharp = true
		RA_S.scanPureQuad = true
		local t0 = timeStamp()
		local r = ra_scanMerge #(b, c)
		local dt = (timeStamp() - t0) / 1000.0
		if r[1] == undefined then (rep false ("스캔 실패: " + r[2]); bad += 1)
		else
		(
			RA_S.retopo = r[1]
			local qi = quadInfo r[1]
			format "[TEST]      %\n" r[2]
			if rep (qi[1] > 50 and qi[1] == qi[2]) ("상자+원기둥 스캔: 면 " + qi[1] as string + ", 쿼드 " + qi[2] as string + ", " + dt as string + "s") then ok += 1 else bad += 1
			if rep (RA_ScanQ != undefined) "새 엔진으로 만들어짐 (예전 느린 방식 아님)" then ok += 1 else bad += 1

			-- 3) 면 수 조절 (목표 400 → +1 단계)
			local ok1 = ra_scanRebuild 400
			local n1 = if isValidNode RA_ScanNode then polyop.getNumFaces RA_ScanNode else 0
			if rep (ok1 == true and n1 > 300 and n1 < 520) ("목표 면 400 으로 다시 만들기 → " + n1 as string) then ok += 1 else bad += 1
			ra_scanAdjust 1
			local n2 = if isValidNode RA_ScanNode then polyop.getNumFaces RA_ScanNode else 0
			if rep (n2 > n1) ("+ 한 단계 → " + n2 as string) then ok += 1 else bad += 1

			-- 4) 가이드 선 (상자 윗면 대각선) 으로 다시 만들기
			local gp = for i = 0 to 20 collect ([-25, -15, 30.05] + ([50, 30, 0] * (i / 20.0)))
			local gn = for p in gp collect [0, 0, 1]
			RA_S.scanGuides = #(#(gp, gn))
			local ok3 = ra_scanApplyGuides()
			if rep (ok3 == true and RA_ScanQ.GuideCount == 1) ("가이드 선으로 다시 만들기 → 면 " + (polyop.getNumFaces RA_ScanNode) as string) then ok += 1 else bad += 1
		)

		-- 5) 두께 없는 판(열린 면) — 뒷면 지워진 한 겹
		local p = Plane length:60 width:80 lengthsegs:6 widthsegs:8 pos:[120, 0, 0] name:"RA_Test_Plane"
		local r2 = ra_scanMerge #(p)
		if r2[1] == undefined then (rep false ("판 스캔 실패: " + r2[2]); bad += 1)
		else
		(
			local qi = quadInfo r2[1]
			local open = (polyop.getOpenEdges r2[1]).numberSet
			if rep (qi[1] > 20 and open > 0) ("판 스캔: 면 " + qi[1] as string + ", 열린 엣지 " + open as string + " (한 겹)") then ok += 1 else bad += 1
		)
		format "[TEST] 끝: 통과 % / 실패 %\n" ok bad
		redrawViews()
	)
)
