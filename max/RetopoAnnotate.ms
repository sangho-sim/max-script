-- ============================================================================
-- Retopo Annotate for 3ds Max 2020+  (리토폴로지 주석 툴)
--  * 뷰포트에 선(주석)을 그리면: 메쉬 가로지름 → 컷 / 닫힌 도형 → 쿼드 채우기 /
--    두 선 → 사이 메쉬 / 그 외 → 쿼드 스트립
--  * 쿼드 익스트루드: 선택 버텍스를 익스트루드하면 인접 4버텍스로 면 자동 생성
--  * 그린 선은 변환 즉시 사라져 화면을 가리지 않음
-- ============================================================================

global RA_S
global RA_Rollout
global RA_drawCB
global RA_fillPending = false
global RA_lastCutVerts = #()
global RA_lastSnapCount = 0
global ra_syncUI
global ra_startDraw
global RA_ScriptDir = try (getFilenamePath (getThisScriptFilename())) catch undefined
global RA_ScanNode

if RA_drawCB != undefined do (try (unregisterRedrawViewsCallback RA_drawCB) catch ())

struct RA_State
(
	target = undefined,
	retopo = undefined,
	spacing = 5.0,
	mergeDist = 1.0,
	offset = 0.05,
	relaxIters = 3,
	mode = 1,            -- 1 자동, 2 스트립, 3 채우기, 4 두 선 사이, 5 컷
	autoFill = true,
	strokeColor = (color 255 90 25),
	pendingColor = (color 90 200 255),
	showPending = true,
	drawing = false,
	curPts = #(),
	curNrm = #(),
	pending = #(),       -- #(#(pts, nrms), ...)
	projFn = undefined,  -- world -> screen 오버라이드(테스트용)
	busy = false,
	densityMode = 1,     -- 1 엣지 길이, 2 분할 수
	countU = 6,
	countV = 6,
	countEdge = 8,
	redoOnChange = true,
	lastRec = undefined, -- #(pts, nrms, pendingBefore, 변환 전 메쉬 스냅샷)
	lastSig = undefined,
	targets = #(),       -- 타겟 노드들 (오브젝트 하나 / 여러 개 / 레이어 전체)
	targetLabel = "",
	stripWidth = 0.0,    -- 0 = 엣지 길이와 같게
	pendingRing = undefined,  -- 컨투어 첫 링 (아직 면 없음, 파란색 표시)
	ringVerts = undefined,    -- 마지막으로 브리지한 링 버텍스 (다음 컨투어가 여기서 이어짐)
	curOn = #(),
	curView = undefined,
	creaseRatio = 0.35,
	creaseClosed = false,
	showConnect = true,       -- 이어짐/새로 생성 표시
	connColor = (color 60 255 110),
	newColor = (color 255 170 40),
	tracking = false,         -- 주석 그리기 모드(mouseTrack) 중
	hoverPt = undefined,      -- 그리기 모드에서 커서가 가리키는 표면 점
	hoverInfo = undefined,
	startInfo = undefined,    -- 지금 긋는 선의 시작점 연결 정보
	endInfo = undefined,
	flash = undefined,        -- 방금 만든 결과 표시 #(테두리들, 색, 글자, 위치, 시간)
	snapCreases = true,       -- 꺾이는 곳(교차선)에 버텍스 맞춤
	creases = #(),            -- #(#(점, 교선 방향), ...) 이 점들에는 반드시 버텍스가 옴
	remCand = #(),            -- 성기게: 지운 루프에 있던 버텍스 위치 (남은 2-엣지 점 정리용)
	flowDir = undefined,      -- 흐름 재구성: 엣지 줄이 따를 방향
	extDirs = undefined,      -- 고르게 재구성: 경계 점마다 주변에서 들어오는 엣지 방향 (그 흐름을 이어 감)
	lastMsg = "",             -- 영역 선택/흐름 재구성 결과 메시지
	nextMode = 0,             -- 다음 선 한 번만 이 방식으로 (5 컷 / 7 영역 선택 / 8 흐름 재구성), 0 = 없음
	scanSharp = true,         -- 스캔: 모서리(꺾인 엣지·판 가장자리·뾰족한 끝) 살리기
	scanAngle = 35.0,         -- 스캔: 이 각도 이상 꺾인 엣지를 모서리로
	scanPureQuad = true,      -- 스캔: 전부 쿼드 (끄면 삼각형이 조금 섞인 쿼드 위주)
	scanDelBack = true,       -- 스캔: 두께 없는 판(열린 면)의 뒷면 지우기
	scanTarget = 0,           -- 스캔: 목표 면 수 (0 = 엣지 길이 사용)
	guideMode = false,        -- 가이드 선 그리기 중 (선이 메쉬가 되지 않고 스캔 재구성 가이드로 남음)
	scanGuides = #(),         -- #(#(점들, 법선들), ...) 스캔 결과 위에 그은 가이드 선
	guideColor = (color 255 40 200)
)
RA_S = RA_State()

-- ---------------------------------------------------------------------------
-- 수학 / 폴리라인 유틸
-- ---------------------------------------------------------------------------

fn ra_round x = ((floor (x + 0.5)) as integer)
fn ra_wrap i n = (local r = (mod (i - 1) n) as integer; if r < 0 do r += n; r + 1)
fn ra_rev arr = (for i = arr.count to 1 by -1 collect arr[i])

fn ra_angle a b =
(
	local la = length a
	local lb = length b
	if la < 1e-12 or lb < 1e-12 then 0.0 else acos (amax -1.0 (amin 1.0 ((dot a b) / (la * lb))))
)

fn ra_polyLen pts =
(
	local L = 0.0
	for i = 1 to pts.count - 1 do L += distance pts[i] pts[i + 1]
	L
)

fn ra_dedupe pts nrms eps =
(
	local op = #(pts[1])
	local nl = #(nrms[1])
	for i = 2 to pts.count do
	(
		if distance pts[i] op[op.count] > eps do (append op pts[i]; append nl nrms[i])
	)
	#(op, nl)
)

fn ra_smooth pts iters fixed:#{} =
(
	local p = for x in pts collect x
	local n = p.count
	if n >= 3 do
	(
		for it = 1 to iters do
		(
			local q = for x in p collect x
			for i = 2 to n - 1 where not fixed[i] do q[i] = p[i] * 0.5 + (p[i - 1] + p[i + 1]) * 0.25
			p = q
		)
	)
	p
)

-- ---------------------------------------------------------------------------
-- 꺾임(두 오브젝트 교차선 / 모서리): 선이 한 표면에서 다른 표면으로 넘어가면 두 샘플 사이 직선은
-- 허공을 지나므로 두 평면의 교선 위 점을 끼워 넣고, 그 점에 반드시 버텍스가 오게 나눈다
-- ---------------------------------------------------------------------------

-- 두 평면 (pA,nA)(pB,nB) 교선 위에서 pA-pB 중점과 가장 가까운 점
fn ra_planeCross pA nA pB nB =
(
	local d = cross nA nB
	if length d < 1e-6 then undefined
	else
	(
		local m = (pA + pB) * 0.5
		local den = dot nA (cross nB d)
		if abs den < 1e-12 then undefined
		else ((dot nA pA) * (cross nB d) + (dot nB pB) * (cross d nA) + (dot d m) * (cross nA nB)) / den
	)
)

-- 꺾임 점을 끼워 넣음 → #(pts, nrms, #(#(점, 교선 방향), ...))
fn ra_insertCreases pts nrms =
(
	local op = #(pts[1])
	local onr = #(nrms[1])
	local cr = #()
	local n = pts.count
	for i = 1 to n - 1 do
	(
		local a = nrms[i]
		local b = nrms[i + 1]
		if (ra_angle a b) > 30 do
		(
			local flatA = i == 1 or (ra_angle nrms[i - 1] a) < 15
			local flatB = i + 2 > n or (ra_angle b nrms[i + 2]) < 15
			local q = if flatA and flatB then ra_planeCross pts[i] a pts[i + 1] b else undefined
			local ch = distance pts[i] pts[i + 1]
			if q != undefined and (distance q ((pts[i] + pts[i + 1]) * 0.5)) < (amax (ch * 1.5) (RA_S.spacing * 0.5)) do
			(
				local far = true
				for c in cr where (distance c[1] q) < RA_S.spacing * 0.5 do far = false
				if far do
				(
					append op q
					append onr (normalize (a + b))
					append cr #(q, normalize (cross a b))
				)
			)
		)
		append op pts[i + 1]
		append onr nrms[i + 1]
	)
	#(op, onr, cr)
)

fn ra_creaseAt p =
(
	local r = undefined
	for c in RA_S.creases while r == undefined where (distance p c[1]) < 1e-4 do r = c
	r
)

-- ra_resampleN 과 같지만 꺾임 점마다 반드시 버텍스가 오도록 구간별로 나눔
fn ra_resampleAnch pts nrms nseg =
(
	nseg = amax 1 (nseg as integer)
	local cuts = for i = 2 to pts.count - 1 where (ra_creaseAt pts[i]) != undefined collect i
	if cuts.count == 0 or nseg < cuts.count + 1 then ra_resampleN pts nrms nseg
	else
	(
		local bounds = #(1) + cuts + #(pts.count)
		local lens = #()
		for k = 1 to bounds.count - 1 do
		(
			local L = 0.0
			for i = bounds[k] to bounds[k + 1] - 1 do L += distance pts[i] pts[i + 1]
			append lens (amax 1e-9 L)
		)
		local total = 0.0
		for L in lens do total += L
		local segs = for L in lens collect (amax 1 (ra_round (nseg * L / total)))
		local s = 0
		for x in segs do s += x
		local guard = 0
		while s > nseg and guard < 10000 do
		(
			guard += 1
			local bi = 0
			local bv = 1
			for k = 1 to segs.count where segs[k] > bv do (bv = segs[k]; bi = k)
			if bi == 0 then guard = 10000 else (segs[bi] -= 1; s -= 1)
		)
		while s < nseg do
		(
			local bi = 1
			for k = 1 to segs.count where lens[k] / segs[k] > lens[bi] / segs[bi] do bi = k
			segs[bi] += 1
			s += 1
		)
		local op = #()
		local onr = #()
		for k = 1 to bounds.count - 1 do
		(
			local sp = for i = bounds[k] to bounds[k + 1] collect pts[i]
			local sn = for i = bounds[k] to bounds[k + 1] collect nrms[i]
			local r = ra_resampleN sp sn segs[k]
			local st = if k == 1 then 1 else 2
			for i = st to r[1].count do (append op r[1][i]; append onr r[2][i])
		)
		#(op, onr)
	)
)

-- 점/노멀을 같이 호 길이 기준 nseg 등분
fn ra_resampleN pts nrms nseg =
(
	nseg = amax 1 (nseg as integer)
	local cum = #(0.0)
	for i = 1 to pts.count - 1 do append cum (cum[i] + distance pts[i] pts[i + 1])
	local total = cum[cum.count]
	local op = #()
	local nl = #()
	if total < 1e-9 or pts.count < 2 then
	(
		for k = 0 to nseg do (append op pts[1]; append nl nrms[1])
	)
	else
	(
		local j = 1
		for k = 0 to nseg do
		(
			local t = total * k / (nseg as float)
			while j < pts.count - 1 and cum[j + 1] < t do j += 1
			local seg = cum[j + 1] - cum[j]
			local f = if seg < 1e-12 then 0.0 else (t - cum[j]) / seg
			f = amax 0.0 (amin 1.0 f)
			append op (pts[j] + (pts[j + 1] - pts[j]) * f)
			local nn = nrms[j] + (nrms[j + 1] - nrms[j]) * f
			append nl (if length nn < 1e-9 then nrms[j] else normalize nn)
		)
	)
	#(op, nl)
)

fn ra_isClosed pts =
(
	local L = ra_polyLen pts
	if L < RA_S.spacing * 3 then false
	else (distance pts[1] pts[pts.count]) < (amax (RA_S.spacing * 1.5) (L * 0.2))
)

fn ra_cmpDesc i1 i2 vals: =
(
	local d = vals[i2] - vals[i1]
	if d > 0 then 1 else if d < 0 then -1 else 0
)

-- 닫힌 루프에서 모서리 4개(0-based 인덱스)
fn ra_findCorners dense =
(
	local n = dense.count
	local k = amax 2 (n / 24)
	local ang = #()
	for i = 1 to n do
	(
		local a = dense[i] - dense[ra_wrap (i - k) n]
		local b = dense[ra_wrap (i + k) n] - dense[i]
		append ang (ra_angle a b)
	)
	local order = for i = 1 to n collect i
	qsort order ra_cmpDesc vals:ang
	local picked = #()
	local minsep = amax 1 (n / 8)
	local stop = false
	for i in order while not stop do
	(
		if ang[i] < 35 then stop = true
		else
		(
			local ok = true
			for j in picked do
			(
				local cd = abs ((i - 1) - j)
				cd = amin cd (n - cd)
				if cd < minsep do ok = false
			)
			if ok do append picked (i - 1)
			if picked.count == 4 do stop = true
		)
	)
	if picked.count == 0 do picked = #(0)
	sort picked
	while picked.count < 4 do
	(
		local bestGap = -1
		local bestI = 1
		for i = 1 to picked.count do
		(
			local a = picked[i]
			local b = if i == picked.count then picked[1] + n else picked[i + 1]
			if b - a > bestGap do (bestGap = b - a; bestI = i)
		)
		append picked ((mod (picked[bestI] + bestGap / 2) n) as integer)
		sort picked
	)
	picked
)

-- B:아래(c00→c10) R:오른쪽(c10→c11) T:위(c01→c11) L:왼쪽(c00→c01)
fn ra_coons cB cR cT cL =
(
	local a = cB.count - 1
	local b = cR.count - 1
	local c00 = cB[1]
	local c10 = cB[a + 1]
	local c01 = cT[1]
	local c11 = cT[a + 1]
	local grid = #()
	for j = 0 to b do
	(
		local v = j / (b as float)
		local row = #()
		for i = 0 to a do
		(
			local u = i / (a as float)
			local p
			if j == 0 then p = cB[i + 1]
			else if j == b then p = cT[i + 1]
			else if i == 0 then p = cL[j + 1]
			else if i == a then p = cR[j + 1]
			else p = (1 - v) * cB[i + 1] + v * cT[i + 1] + (1 - u) * cL[j + 1] + u * cR[j + 1] - \
				((1 - u) * (1 - v) * c00 + u * (1 - v) * c10 + (1 - u) * v * c01 + u * v * c11)
			append row p
		)
		append grid row
	)
	grid
)

fn ra_lerpList a b m = (for j = 0 to m collect (a + (b - a) * (j / (m as float))))

-- ---------------------------------------------------------------------------
-- 타겟 표면
-- ---------------------------------------------------------------------------

-- 타겟: 오브젝트 하나 / 선택한 여러 오브젝트 / 레이어 전체
fn ra_targets =
(
	local out = for n in RA_S.targets where isValidNode n and not (isValidNode RA_S.retopo and n == RA_S.retopo) and superClassOf n == GeometryClass collect n
	if out.count == 0 and isValidNode RA_S.target and not (isValidNode RA_S.retopo and RA_S.target == RA_S.retopo) do out = #(RA_S.target)
	out
)

fn ra_hasTarget = ((ra_targets()).count > 0)

-- 모든 타겟 중 레이 시작점에서 가장 가까운 교차
fn ra_rayHit r =
(
	local best = undefined
	local bd = 1e30
	-- 가이드 선은 스캔 결과 메쉬 위에 그음
	local nodes = if RA_S.guideMode and isValidNode RA_ScanNode then #(RA_ScanNode) else ra_targets()
	for n in nodes do
	(
		local h = intersectRay n r
		if h != undefined do
		(
			local d = distance h.pos r.pos
			if d < bd do (bd = d; best = h)
		)
	)
	best
)

fn ra_project p n =
(
	if not (ra_hasTarget()) then p
	else
	(
		local d = amax (RA_S.spacing * 4.0) 0.001
		local nn = normalize n
		local best = undefined
		local bd = 1e30
		for r in #(ray (p + nn * d) (-nn), ray (p - nn * d) nn) do
		(
			local h = ra_rayHit r
			if h != undefined do
			(
				local dd = distance h.pos p
				if dd < bd do (bd = dd; best = h)
			)
		)
		if best == undefined then p
		else
		(
			local hn = normalize best.dir
			if dot hn nn < 0 do hn = -hn
			best.pos + hn * RA_S.offset
		)
	)
)

-- 표면 투영 + 그 지점 표면 노멀 → #(위치, 노멀) (못 찾으면 노멀 undefined)
fn ra_projectHit p n =
(
	local d = amax (RA_S.spacing * 4.0) 0.001
	local nn = normalize n
	local best = undefined
	local bd = 1e30
	for r in #(ray (p + nn * d) (-nn), ray (p - nn * d) nn) do
	(
		local h = ra_rayHit r
		if h != undefined do
		(
			local dd = distance h.pos p
			if dd < bd do (bd = dd; best = h)
		)
	)
	if best == undefined then #(p, undefined)
	else
	(
		local hn = normalize best.dir
		if dot hn nn < 0 do hn = -hn
		#(best.pos, hn)
	)
)

-- 그리드 안쪽 점 중 꺾이는 곳(두 표면 교차선) 바로 옆 점을 교선 위로 옮김
-- → 채우기 면이 오목한 모서리를 가로질러 허공에 뜨지 않음
fn ra_snapGridCreases grid ngrid =
(
	local rows = grid.count
	local cols = grid[1].count
	if rows >= 3 and cols >= 3 do
	(
		local hn = #()
		for j = 1 to rows do
		(
			local row = #()
			for i = 1 to cols do append row (ra_projectHit grid[j][i] ngrid[j][i])[2]
			append hn row
		)
		local newP = #()
		for j = 2 to rows - 1 do for i = 2 to cols - 1 where hn[j][i] != undefined do
		(
			local p = grid[j][i]
			local np = hn[j][i]
			local best = undefined
			local bd = 1e30
			local nbs = #(#(j - 1, i), #(j + 1, i), #(j, i - 1), #(j, i + 1))
			for nb in nbs do
			(
				local q = grid[nb[1]][nb[2]]
				local nq = hn[nb[1]][nb[2]]
				if nq != undefined and (ra_angle np nq) > 30 do
				(
					local x = ra_planeCross p np q nq
					if x != undefined do
					(
						local dp = distance p x
						local dq = distance q x
						-- 이웃이 이미 교차선 위면 이 점은 옮기지 않음 (옮기면 쿼드가 찌그러짐)
						if dq >= (distance p q) * 0.15 and dp <= dq and dp < (distance p q) * 0.75 and dp < bd do (bd = dp; best = x)
					)
				)
			)
			if best != undefined do append newP #(j, i, best)
		)
		for e in newP do grid[e[1]][e[2]] = e[3]
	)
	grid
)

-- 삼각형 중심이 표면에서 떠 있는 거리
fn ra_triFloat a b c =
(
	local m = (a + b + c) / 3.0
	local n = cross (b - a) (c - a)
	if length n < 1e-9 then 0.0 else distance (ra_project m (normalize n)) m
)

-- 쿼드는 첫 버텍스에서 대각선(1-3)으로 삼각형이 나뉨. 꺾이는 곳에서 2-4 대각선이 표면에 더 잘 붙으면
-- 버텍스 순서를 한 칸 돌려서 그 대각선으로 나뉘게 함 (쿼드는 그대로)
fn ra_bestQuadOrder obj q =
(
	if q.count != 4 or not RA_S.snapCreases then q
	else
	(
		local p = for v in q collect polyop.getVert obj v
		local d13 = amax (ra_triFloat p[1] p[2] p[3]) (ra_triFloat p[1] p[3] p[4])
		local d24 = amax (ra_triFloat p[1] p[2] p[4]) (ra_triFloat p[2] p[3] p[4])
		if d24 < d13 * 0.7 and (d13 - d24) > RA_S.spacing * 0.02 then #(q[2], q[3], q[4], q[1]) else q
	)
)

fn ra_toScreen p =
(
	if RA_S.projFn != undefined then RA_S.projFn p
	else
	(
		gw.setTransform (matrix3 1)
		local s = gw.wTransPoint p
		[s.x, s.y]
	)
)

-- ---------------------------------------------------------------------------
-- Editable Poly 유틸
-- ---------------------------------------------------------------------------

fn ra_isPoly obj = (obj != undefined and isValidNode obj and classOf obj.baseObject == Editable_Poly)

fn ra_edgeBetween obj a b =
(
	local ba = (polyop.getEdgesUsingVert obj a) * (polyop.getEdgesUsingVert obj b)
	if ba.isEmpty then undefined else (ba as array)[1]
)

fn ra_isOpen obj e = ((polyop.getEdgeFaces obj e).count == 1)
fn ra_openEdges obj v = (for e in (polyop.getEdgesUsingVert obj v) where ra_isOpen obj e collect e)
fn ra_other obj e v = (local ev = polyop.getEdgeVerts obj e; if ev[1] == v then ev[2] else ev[1])

fn ra_quadOk cos =
(
	local n = cross (cos[3] - cos[1]) (cos[4] - cos[2])
	if length n < 1e-12 then false
	else
	(
		local neg = 0
		for i = 1 to 4 do
		(
			local i1 = (mod i 4) as integer + 1
			local i2 = (mod (i + 1) 4) as integer + 1
			if dot (cross (cos[i1] - cos[i]) (cos[i2] - cos[i1])) n <= 0 do neg += 1
		)
		neg <= 1
	)
)

-- order 순서로 면을 만들 때 인접 면과 같은 방향(same)/반대 방향(opp) 엣지 수
fn ra_winding obj order =
(
	local same = 0
	local opp = 0
	local m = order.count
	for i = 1 to m do
	(
		local p = order[i]
		local q = order[(mod i m) as integer + 1]
		local e = ra_edgeBetween obj p q
		if e != undefined do
		(
			for f in polyop.getEdgeFaces obj e do
			(
				local fv = polyop.getFaceVerts obj f
				local k = findItem fv p
				if k > 0 do
				(
					if fv[(mod k fv.count) as integer + 1] == q then same += 1 else opp += 1
				)
			)
		)
	)
	#(same, opp)
)

fn ra_makeFace obj vs refN =
(
	local order = vs
	local rev = ra_rev vs
	local w = ra_winding obj vs
	if w[1] > 0 and w[2] == 0 then (order = rev; rev = vs)
	else if w[1] == 0 and w[2] == 0 and refN != undefined and vs.count == 4 do
	(
		local cos = for v in vs collect polyop.getVert obj v
		local n = cross (cos[3] - cos[1]) (cos[4] - cos[2])
		if dot n refN < 0 do (order = rev; rev = vs)
	)
	local f = polyop.createPolygon obj order
	if f == undefined do f = polyop.createPolygon obj rev
	f
)

fn ra_vertNormal obj v =
(
	local fs = (polyop.getFacesUsingVert obj v) as array
	local n = [0, 0, 0]
	for f in fs do n += polyop.getFaceNormal obj f
	if length n < 1e-9 then undefined else normalize n
)

fn ra_vertFaceCenter obj v =
(
	local fs = (polyop.getFacesUsingVert obj v) as array
	if fs.count == 0 then undefined
	else (local c = [0, 0, 0]; for f in fs do c += polyop.getFaceCenter obj f; c / fs.count)
)

-- 새 버텍스와 가까운(병합 거리) 기존 버텍스를 함께 용접
-- 새 버텍스를 가까운(병합 거리) '기존' 버텍스에만 붙임 (새 버텍스끼리는 용접하지 않음)
fn ra_weldTo obj newVerts =
(
	local md = amin RA_S.mergeDist (RA_S.spacing * 0.45)
	if md <= 0 then 0
	else
	(
		local pairs = #{}
		local nv = polyop.getNumVerts obj
		local existing = for v = 1 to nv where not newVerts[v] collect v
		local exPos = for v in existing collect polyop.getVert obj v
		for v in newVerts do
		(
			local p = polyop.getVert obj v
			local best = 0
			local bd = md
			for i = 1 to existing.count do
			(
				local d = distance p exPos[i]
				if d <= bd do (bd = d; best = i)
			)
			if best > 0 do
			(
				polyop.setVert obj #(v) exPos[best]
				pairs[v] = true
				pairs[existing[best]] = true
			)
		)
		if not pairs.isEmpty do
		(
			obj.weldThreshold = 0.0001
			polyop.weldVertsByThreshold obj pairs
		)
		if pairs.isEmpty then 0 else 1
	)
)

-- 닫힌 루프 스무딩 (시작/끝 이음매의 꺾임 제거)
fn ra_smoothClosed pts iters =
(
	local p = for x in pts collect x
	local n = p.count
	if n >= 4 do
	(
		for it = 1 to iters do
		(
			local q = for i = 1 to n collect (p[i] * 0.5 + (p[ra_wrap (i - 1) n] + p[ra_wrap (i + 1) n]) * 0.25)
			p = q
		)
	)
	p
)
-- ---------------------------------------------------------------------------
-- 메쉬 생성: 그리드 / 채우기 / 로프트 / 스트립
-- ---------------------------------------------------------------------------

fn ra_buildGrid obj grid ngrid relax =
(
	local b = grid.count - 1
	local a = grid[1].count - 1
	for j = 1 to grid.count do for i = 1 to grid[j].count do grid[j][i] = ra_project grid[j][i] ngrid[j][i]
	for it = 1 to relax do
	(
		for j = 2 to b do for i = 2 to a do
			grid[j][i] = (grid[j - 1][i] + grid[j + 1][i] + grid[j][i - 1] + grid[j][i + 1]) * 0.25
		for j = 2 to b do for i = 2 to a do grid[j][i] = ra_project grid[j][i] ngrid[j][i]
	)
	if RA_S.snapCreases do grid = ra_snapGridCreases grid ngrid
	local nsum = [0, 0, 0]
	for row in ngrid do for n in row do nsum += n
	local vid = for row in grid collect (for p in row collect (polyop.createVert obj p))
	local n0 = cross (grid[1][2] - grid[1][1]) (grid[2][1] - grid[1][1])
	local flip = (dot n0 nsum) < 0
	local made = 0
	for j = 1 to b do for i = 1 to a do
	(
		local q = #(vid[j][i], vid[j][i + 1], vid[j + 1][i + 1], vid[j + 1][i])
		if flip do q = ra_rev q
		if (polyop.createPolygon obj (ra_bestQuadOrder obj q)) != undefined do made += 1
	)
	local bverts = #{}
	for i = 1 to a + 1 do (bverts[vid[1][i]] = true; bverts[vid[b + 1][i]] = true)
	for j = 1 to b + 1 do (bverts[vid[j][1]] = true; bverts[vid[j][a + 1]] = true)
	ra_weldTo obj bverts
	made
)

fn ra_normGrid ng = (for row in ng collect (for n in row collect (if length n < 1e-9 then [0, 0, 1] else normalize n)))

fn ra_fillLoop obj pts nrms =
(
	local lp = pts + #(pts[1])
	local ln = nrms + #(nrms[1])
	local rs = ra_resampleN lp ln 128
	local dense = for i = 1 to 128 collect rs[1][i]
	local denseN = for i = 1 to 128 collect rs[2][i]
	local n = 128
	local cs = ra_findCorners dense
	local sideP = #()
	local sideN = #()
	for i = 1 to 4 do
	(
		local a = cs[i]
		local b = if i == 4 then cs[1] + n else cs[i + 1]
		append sideP (for k = a to b collect dense[(mod k n) as integer + 1])
		append sideN (for k = a to b collect denseN[(mod k n) as integer + 1])
	)
	local Ls = for s in sideP collect ra_polyLen s
	local na = amax 1 (ra_round ((Ls[1] + Ls[3]) / (2.0 * RA_S.spacing)))
	local nb = amax 1 (ra_round ((Ls[2] + Ls[4]) / (2.0 * RA_S.spacing)))
	if RA_S.densityMode == 2 do (na = RA_S.countU; nb = RA_S.countV)
	local SS = #()
	for i = 1 to 4 do append SS (ra_resampleN sideP[i] sideN[i] (if (mod i 2) == 1 then na else nb))
	local grid = ra_coons SS[1][1] SS[2][1] (ra_rev SS[3][1]) (ra_rev SS[4][1])
	local ngrid = ra_normGrid (ra_coons SS[1][2] SS[2][2] (ra_rev SS[3][2]) (ra_rev SS[4][2]))
	ra_buildGrid obj grid ngrid RA_S.relaxIters
)

fn ra_loft obj A AN B BN =
(
	if (distance A[1] B[1]) + (distance A[A.count] B[B.count]) > (distance A[1] B[B.count]) + (distance A[A.count] B[1]) do
	(
		B = ra_rev B
		BN = ra_rev BN
	)
	local n = if RA_S.densityMode == 2 then RA_S.countU else amax 1 (ra_round ((ra_polyLen A + ra_polyLen B) / 2.0 / RA_S.spacing))
	local SA = ra_resampleN A AN n
	local SB = ra_resampleN B BN n
	local avg = 0.0
	for i = 1 to n + 1 do avg += distance SA[1][i] SB[1][i]
	avg /= (n + 1)
	local m = if RA_S.densityMode == 2 then RA_S.countV else amax 1 (ra_round (avg / RA_S.spacing))
	local R = ra_lerpList SA[1][n + 1] SB[1][n + 1] m
	local L = ra_lerpList SA[1][1] SB[1][1] m
	local RN = ra_lerpList SA[2][n + 1] SB[2][n + 1] m
	local LN = ra_lerpList SA[2][1] SB[2][1] m
	local grid = ra_coons SA[1] R SB[1] L
	local ngrid = ra_normGrid (ra_coons SA[2] RN SB[2] LN)
	ra_buildGrid obj grid ngrid RA_S.relaxIters
)

-- 스트립 시작/끝 근처(폭의 0.75 이내)의 열린 엣지 → #(v1, v2, 길이)
-- dir: 선이 나가는 방향. 주면 선과 나란한 엣지(옆면)에는 붙지 않음 (꺾인 L자에서 면이 뒤틀리던 원인)
fn ra_findAttach obj p w dir:undefined =
(
	local best = undefined
	local bd = w * 0.75
	local nd = if dir != undefined and (length dir) > 1e-9 then normalize dir else undefined
	for e in (polyop.getOpenEdges obj) do
	(
		local ev = polyop.getEdgeVerts obj e
		local a = polyop.getVert obj ev[1]
		local b = polyop.getVert obj ev[2]
		local d = distance ((a + b) * 0.5) p
		if d < bd and (nd == undefined or (distance a b) < 1e-9 or abs (dot (normalize (b - a)) nd) < 0.7) do
			(bd = d; best = #(ev[1], ev[2], distance a b))
	)
	best
)

fn ra_nearestVert obj p maxd =
(
	local best = 0
	local bd = maxd
	for v = 1 to polyop.getNumVerts obj do
	(
		local d = distance (polyop.getVert obj v) p
		if d < bd do (bd = d; best = v)
	)
	best
)

-- PolyStrips: 선을 따라 폭 w 의 쿼드 띠. 기존 열린 엣지에서 시작/끝나면 그 엣지에 붙고 폭을 이어받음
fn ra_strip obj pts nrms =
(
	local w = if RA_S.stripWidth > 0 then RA_S.stripWidth else RA_S.spacing
	local k = amin 4 pts.count
	local att1 = ra_findAttach obj pts[1] w dir:(pts[k] - pts[1])
	local att2 = ra_findAttach obj pts[pts.count] w dir:(pts[pts.count + 1 - k] - pts[pts.count])
	if att1 != undefined then w = att1[3] else if att2 != undefined do w = att2[3]
	local n = if RA_S.densityMode == 2 then RA_S.countEdge else amax 1 (ra_round (ra_polyLen pts / RA_S.spacing))
	local rs = ra_resampleAnch pts nrms n
	local c = rs[1]
	local cn = rs[2]
	local hw = w * 0.5
	local rowA = #()
	local rowB = #()
	for i = 1 to c.count do
	(
		local t = if i == 1 then c[2] - c[1] else if i == c.count then c[i] - c[i - 1] else c[i + 1] - c[i - 1]
		local s = normalize (cross t cn[i])
		local h = hw
		local cr = if i > 1 and i < c.count then ra_creaseAt c[i] else undefined
		if cr != undefined then
		(
			-- 꺾임 점: 폭 방향을 교선 방향으로 → 양쪽 버텍스도 교선 위에 놓임.
			-- 방향 부호는 바로 앞 줄(한 표면 위)에 맞추고, 비스듬히 지나가면 폭이 줄지 않게 늘림
			local prev = rowB[rowB.count] - rowA[rowA.count]
			s = if dot cr[2] prev >= 0 then cr[2] else -cr[2]
			local t1 = normalize (c[i] - c[i - 1])
			local t2 = normalize (c[i + 1] - c[i])
			local sinT = ((length (cross t1 s)) + (length (cross t2 s))) * 0.5
			h = hw / (amax sinT 0.4)
		)
		else if rowA.count > 0 and (dot s (rowB[rowB.count] - rowA[rowA.count])) < 0 do s = -s  -- 앞 줄과 좌우가 뒤바뀌지 않게
		append rowA (c[i] - s * h)
		append rowB (c[i] + s * h)
	)
	local made = ra_buildGrid obj #(rowA, rowB) #(cn, cn) 0
	-- 끝을 기존 엣지에 붙이기 (버텍스 위치를 맞춘 뒤 용접)
	local pairs = #{}
	for e in #(#(att1, 1), #(att2, c.count)) where e[1] != undefined do
	(
		local a = e[1]
		local pa = ra_project rowA[e[2]] cn[e[2]]
		local pb = ra_project rowB[e[2]] cn[e[2]]
		local va = ra_nearestVert obj pa (w * 0.4)
		local vb = ra_nearestVert obj pb (w * 0.4)
		if va > 0 and vb > 0 and va != a[1] and va != a[2] and vb != a[1] and vb != a[2] do
		(
			local e1 = polyop.getVert obj a[1]
			local e2 = polyop.getVert obj a[2]
			local ta = a[1]; local tb = a[2]
			if (distance pa e1) + (distance pb e2) > (distance pa e2) + (distance pb e1) do (ta = a[2]; tb = a[1])
			polyop.setVert obj #(va) (polyop.getVert obj ta)
			polyop.setVert obj #(vb) (polyop.getVert obj tb)
			pairs[va] = true; pairs[vb] = true; pairs[ta] = true; pairs[tb] = true
		)
	)
	if not pairs.isEmpty do (obj.weldThreshold = 0.0001; polyop.weldVertsByThreshold obj pairs)
	made
)
-- ---------------------------------------------------------------------------
-- 컷: 그은 선(화면 기준)과 엣지 교차점을 나누고 면을 분할
-- ---------------------------------------------------------------------------

fn ra_segX a b c d =
(
	local r = b - a
	local s = d - c
	local den = r.x * s.y - r.y * s.x
	if abs den < 1e-9 then undefined
	else
	(
		local qp = c - a
		local t = (qp.x * s.y - qp.y * s.x) / den
		local u = (qp.x * r.y - qp.y * r.x) / den
		if t < 0 or t > 1 or u < 0 or u > 1 then undefined else [t, u]
	)
)

fn ra_cmpHit a b = (if a[1] < b[1] then -1 else if a[1] > b[1] then 1 else 0)
fn ra_cmpT a b = (if a[1] < b[1] then -1 else if a[1] > b[1] then 1 else 0)

-- snap: 교차점이 엣지 양 끝 버텍스에서 이 비율 안이면 새 버텍스를 만들지 않고 그 버텍스를 사용
fn ra_cut obj pts dry snap:0.08 =
(
	local S2 = for p in pts collect ra_toScreen p
	local minx = 1e30; local maxx = -1e30; local miny = 1e30; local maxy = -1e30
	for s in S2 do (minx = amin minx s.x; maxx = amax maxx s.x; miny = amin miny s.y; maxy = amax maxy s.y)
	local vcache = #()
	local hits = #()
	local ne = polyop.getNumEdges obj
	for e = 1 to ne do
	(
		local ev = polyop.getEdgeVerts obj e
		if ev == undefined do continue
		local a3 = polyop.getVert obj ev[1]
		local b3 = polyop.getVert obj ev[2]
		local a2 = vcache[ev[1]]
		if a2 == undefined do (a2 = ra_toScreen a3; vcache[ev[1]] = a2)
		local b2 = vcache[ev[2]]
		if b2 == undefined do (b2 = ra_toScreen b3; vcache[ev[2]] = b2)
		if (amax a2.x b2.x) < minx or (amin a2.x b2.x) > maxx or (amax a2.y b2.y) < miny or (amin a2.y b2.y) > maxy do continue
		local tol = amax ((distance a3 b3) * 0.75) (RA_S.spacing * 1.5)
		for k = 1 to S2.count - 1 do
		(
			local r = ra_segX a2 b2 S2[k] S2[k + 1]
			if r != undefined do
			(
				local h3 = a3 + (b3 - a3) * r.x
				local s3 = pts[k] + (pts[k + 1] - pts[k]) * r.y
				if distance h3 s3 <= tol do append hits #(k + r.y, e, r.x, ev[1], ev[2])
			)
		)
	)
	if dry or hits.count < 2 then hits.count
	else
	(
		qsort hits ra_cmpHit
		local hitVert = for h in hits collect 0
		local edgesDone = #{}
		RA_lastSnapCount = 0
		for hi = 1 to hits.count where not edgesDone[hits[hi][2]] do
		(
			local e = hits[hi][2]
			edgesDone[e] = true
			local v0 = hits[hi][4]
			local v1 = hits[hi][5]
			local lst = for k = 1 to hits.count where hits[k][2] == e collect #(hits[k][3], k)
			qsort lst ra_cmpT
			local curV = v0
			local curT = 0.0
			for it in lst do
			(
				local t = it[1]
				local idx = it[2]
				if t < snap then (hitVert[idx] = v0; if t >= 0.08 do RA_lastSnapCount += 1)
				else if t > 1.0 - snap then (hitVert[idx] = v1; if t <= 0.92 do RA_lastSnapCount += 1)
				else
				(
					local ce = ra_edgeBetween obj curV v1
					if ce != undefined do
					(
						local fac = (t - curT) / (1.0 - curT)
						local evs = polyop.getEdgeVerts obj ce
						local f = if evs[1] == curV then fac else 1.0 - fac
						local nv = polyop.divideEdge obj ce f
						if nv != undefined and nv > 0 do
						(
							local np = polyop.getVert obj nv
							local vn = ra_vertNormal obj nv
							if vn != undefined do polyop.setVert obj #(nv) (ra_project np vn)
							hitVert[idx] = nv
							curV = nv
							curT = t
						)
					)
				)
			)
		)
		local seq = for v in hitVert where v > 0 collect v
		RA_lastCutVerts = seq
		local made = 0
		for i = 1 to seq.count - 1 do
		(
			local va = seq[i]
			local vb = seq[i + 1]
			if va == vb or (ra_edgeBetween obj va vb) != undefined do continue
			local common = (polyop.getFacesUsingVert obj va) * (polyop.getFacesUsingVert obj vb)
			if not common.isEmpty do
			(
				if (polyop.createEdge obj va vb) != undefined do made += 1
			)
		)
		made
	)
)

-- ---------------------------------------------------------------------------
-- 쿼드 익스트루드 / 4버텍스 구멍 채우기
-- ---------------------------------------------------------------------------

fn ra_projectNear p obj v =
(
	local n = ra_vertNormal obj v
	if n == undefined then p else ra_project p n
)

fn ra_extrudeOne obj v =
(
	local pv = polyop.getVert obj v
	local vc = ra_vertFaceCenter obj v
	local refN = ra_vertNormal obj v
	local best = undefined
	local bestScore = -1.0
	-- 1) 이웃 n 이 이미 m 쪽으로 익스트루드 되어 있으면 (v, n, m, v') 쿼드
	for en in ra_openEdges obj v do
	(
		local n = ra_other obj en v
		local pn = polyop.getVert obj n
		for em in ra_openEdges obj n do
		(
			local m = ra_other obj em n
			if m == v or (ra_edgeBetween obj m v) != undefined do continue
			local pm = polyop.getVert obj m
			local d = pm - pn
			local side = pv - pn
			if length d < 1e-9 or length side < 1e-9 do continue
			local ang = ra_angle d side
			if ang < 40 or ang > 140 do continue
			if vc != undefined and (dot d (pv - vc)) <= 0 do continue
			if not (ra_quadOk #(pv, pn, pm, pv + d)) do continue
			local w = ra_winding obj #(v, n, m)
			if w[1] > 0 and w[2] > 0 do continue
			local score = 1.0 / (1.0 + abs (ang - 90))
			if score > bestScore do (bestScore = score; best = #(n, m, d))
		)
	)
	if best != undefined then
	(
		local nv = polyop.createVert obj (ra_projectNear (pv + best[3]) obj v)
		local f = ra_makeFace obj #(v, best[1], best[2], nv) refN
		if f == undefined then (polyop.deleteVerts obj (#(nv) as bitArray); undefined) else nv
	)
	else
	(
		local oe = ra_openEdges obj v
		local result = undefined
		-- 2) 안쪽 모서리(L자) → 평행사변형 쿼드
		if oe.count == 2 do
		(
			local f1 = polyop.getEdgeFaces obj oe[1]
			local f2 = polyop.getEdgeFaces obj oe[2]
			if f1[1] != f2[1] do
			(
				local n1 = ra_other obj oe[1] v
				local n2 = ra_other obj oe[2] v
				local p1 = polyop.getVert obj n1
				local p2 = polyop.getVert obj n2
				if (ra_angle (p1 - pv) (p2 - pv)) < 150 do
				(
					local cand = p1 + p2 - pv
					if ra_quadOk #(pv, p1, cand, p2) do
					(
						local nv = polyop.createVert obj (ra_projectNear cand obj v)
						if (ra_makeFace obj #(v, n1, nv, n2) refN) != undefined then result = nv
						else polyop.deleteVerts obj (#(nv) as bitArray)
					)
				)
			)
		)
		-- 3) 경계 엣지를 바깥으로 익스트루드 (Max 폴리는 면 없는 엣지를 가질 수 없음)
		if result == undefined and oe.count >= 1 do
		(
			local e0 = oe[1]
			local n = ra_other obj e0 v
			local pn = polyop.getVert obj n
			local fc = polyop.getFaceCenter obj (polyop.getEdgeFaces obj e0)[1]
			local fnrm = polyop.getFaceNormal obj (polyop.getEdgeFaces obj e0)[1]
			local outd = normalize (cross (normalize (pn - pv)) fnrm)
			if (dot outd (pv - fc)) < 0 do outd = -outd
			local d = outd * RA_S.spacing
			local a = polyop.createVert obj (ra_projectNear (pv + d) obj v)
			local b = polyop.createVert obj (ra_projectNear (pn + d) obj n)
			if (ra_makeFace obj #(v, n, b, a) fnrm) != undefined then result = a
			else polyop.deleteVerts obj (#(a, b) as bitArray)
		)
		result
	)
)

fn ra_quadExtrude obj =
(
	if not ra_isPoly obj then 0
	else
	(
		local sel = (polyop.getVertSelection obj) as array
		local newV = #{}
		RA_S.busy = true
		undo "Retopo 쿼드 익스트루드" on
		(
			for v in sel do
			(
				local r = ra_extrudeOne obj v
				if r != undefined do newV[r] = true
			)
			polyop.setVertSelection obj newV
		)
		RA_S.busy = false
		redrawViews()
		newV.numberSet
	)
)

fn ra_orderBorder obj border =
(
	local es = border as array
	local ev = polyop.getEdgeVerts obj es[1]
	local order = #(ev[1], ev[2])
	local used = #{es[1]}
	local ok = true
	while ok and order.count < es.count do
	(
		local last = order[order.count]
		local found = false
		for e in es where not used[e] while not found do
		(
			local vv = polyop.getEdgeVerts obj e
			if vv[1] == last then (append order vv[2]; used[e] = true; found = true)
			else if vv[2] == last do (append order vv[1]; used[e] = true; found = true)
		)
		if not found do ok = false
	)
	if ok then order else undefined
)

fn ra_fillHoles obj near dry:false =
(
	local openE = polyop.getOpenEdges obj
	local done = #{}
	local cnt = 0
	for e in openE where not done[e] do
	(
		local border = polyop.getBorderFromEdge obj e
		done += border
		if border.numberSet != 4 do continue
		if near != undefined and ((polyop.getVertsUsingEdge obj border) * near).isEmpty do continue
		local vs = ra_orderBorder obj border
		if vs == undefined or vs.count != 4 do continue
		local cos = for v in vs collect polyop.getVert obj v
		if not (ra_quadOk cos) do continue
		if dry then cnt += 1
		else if (ra_makeFace obj vs undefined) != undefined do cnt += 1
	)
	cnt
)

fn ra_autoFillTick =
(
	RA_fillPending = false
	local obj = RA_S.retopo
	if not RA_S.busy and RA_S.autoFill and ra_isPoly obj do
	(
		RA_S.busy = true
		try
		(
			local sel = polyop.getVertSelection obj
			local near = copy sel
			for v in sel do near += polyop.getVertsUsingEdge obj (polyop.getEdgesUsingVert obj v)
			local n = 0
			-- 채울 구멍이 있을 때만 undo 기록을 만든다 (빈 기록이 쌓이면 되돌리기가 꼬임)
			if (ra_fillHoles obj near dry:true) > 0 do
				undo "Retopo 자동 채우기" on (n = ra_fillHoles obj near)
			if n > 0 do redrawViews()
		)
		catch (format "[RetopoAnnotate] %\n" (getCurrentException()))
		RA_S.busy = false
	)
)

fn ra_enableAutoFill enable =
(
	deleteAllChangeHandlers id:#RetopoAnnotateFill
	if enable and ra_isPoly RA_S.retopo do
	(
		when topology RA_S.retopo changes id:#RetopoAnnotateFill do
		(
			-- 되돌리기/다시 실행으로 바뀐 경우는 채우지 않음 (다시 채우면 Ctrl+Z 가 안 먹고 다시 실행 기록도 사라짐)
			if not RA_S.busy and not (try (theHold.RestoreOrRedoing()) catch false) do RA_fillPending = true
		)
	)
)

-- 되돌리기/다시 실행 직후에는 자동 채우기 대기 취소
fn ra_onUndoRedo = (RA_fillPending = false)
callbacks.removeScripts id:#RetopoAnnotateUndo
callbacks.addScript #sceneUndo "ra_onUndoRedo()" id:#RetopoAnnotateUndo
callbacks.addScript #sceneRedo "ra_onUndoRedo()" id:#RetopoAnnotateUndo

-- ---------------------------------------------------------------------------
-- 설정 / 스트로크 처리
-- ---------------------------------------------------------------------------

-- 타겟 지정 (여러 노드 가능). 엣지 길이 기본값은 오브젝트 평균 크기의 1/40
fn ra_setTargets nodes label =
(
	RA_S.targets = for n in nodes where isValidNode n and superClassOf n == GeometryClass and not (isValidNode RA_S.retopo and n == RA_S.retopo) collect n
	RA_S.target = if RA_S.targets.count > 0 then RA_S.targets[1] else undefined
	RA_S.targetLabel = label
	if RA_S.targets.count > 0 do
	(
		local diag = 0.0
		for n in RA_S.targets do diag += distance n.min n.max
		diag /= RA_S.targets.count
		RA_S.spacing = diag / 40.0
		RA_S.mergeDist = RA_S.spacing * 0.3
		RA_S.offset = diag * 0.0005
	)
	RA_S.targets.count
)

fn ra_setTarget obj = (ra_setTargets #(obj) (if isValidNode obj then obj.name else ""))

fn ra_layerNames = (for i = 0 to LayerManager.count - 1 collect (LayerManager.getLayer i).name)

fn ra_layerNodes lname =
(
	local lay = LayerManager.getLayerFromName lname
	if lay == undefined then #()
	else
	(
		local arr = #()
		lay.nodes &arr
		arr
	)
)

fn ra_setupRetopo =
(
	if not (ra_hasTarget()) then (messageBox "타겟(하이폴리) 오브젝트나 레이어를 먼저 지정하세요" title:"Retopo"; undefined)
	else
	(
		local m = Editable_Mesh()
		m.name = uniqueName ("Retopo_" + (if RA_S.targetLabel != "" then RA_S.targetLabel else RA_S.target.name) + "_")
		convertTo m PolyMeshObject
		m.wirecolor = color 40 160 255
		m.xray = true
		m.backfacecull = false
		RA_S.retopo = m
		ra_enableAutoFill RA_S.autoFill
		if not (GetQuietMode()) do
		(
			select m
			max modify mode
			subobjectLevel = 1
		)
		m
	)
)

fn ra_joinTol = (amax (RA_S.spacing * 2.5) (RA_S.mergeDist * 2.0))

-- 대기 중인 열린 선들을 끝점으로 이어 닫히면 채우기, 떨어진 두 선이면 로프트
fn ra_tryPending obj =
(
	local P = RA_S.pending
	local join = ra_joinTol()
	local cur = P[P.count]
	local cp = for x in cur[1] collect x
	local cn = for x in cur[2] collect x
	local used = #(P.count)
	local changed = true
	while changed do
	(
		changed = false
		for k = 1 to P.count where (findItem used k) == 0 while not changed do
		(
			local sp = P[k][1]
			local sn = P[k][2]
			local ok = true
			if distance cp[cp.count] sp[1] < join then (cp += sp; cn += sn)
			else if distance cp[cp.count] sp[sp.count] < join then (cp += ra_rev sp; cn += ra_rev sn)
			else if distance cp[1] sp[sp.count] < join then (cp = sp + cp; cn = sn + cn)
			else if distance cp[1] sp[1] < join then (cp = (ra_rev sp) + cp; cn = (ra_rev sn) + cn)
			else ok = false
			if ok do (append used k; changed = true)
		)
	)
	if used.count > 1 and (distance cp[1] cp[cp.count]) < join then
	(
		ra_fillLoop obj cp cn
		RA_S.pending = for k = 1 to P.count where (findItem used k) == 0 collect P[k]
		#fill
	)
	else if P.count == 2 and used.count == 1 then
	(
		local A = P[1][1]
		local B = P[2][1]
		local na = A.count
		local nb = B.count
		local s1 = #(distance A[1] B[1], distance A[na] B[nb])
		local s2 = #(distance A[1] B[nb], distance A[na] B[1])
		local d = if (s1[1] + s1[2]) <= (s2[1] + s2[2]) then s1 else s2
		if (amin d[1] d[2]) > (amax d[1] d[2]) * 0.3 then
		(
			ra_loft obj P[1][1] P[1][2] P[2][1] P[2][2]
			RA_S.pending = #()
			#loft
		)
		else
		(
			-- 한쪽 끝이 붙어 있는 L/V 모양: 두 선 사이를 채우면 찌그러진 삼각형이 되므로
			-- 가까운 끝끼리 이어 한 줄로 합쳐 대기 (끝낼 때 꺾인 스트립 한 줄이 됨)
			local AN = P[1][2]
			local BN = P[2][2]
			local cands = #(#(distance A[na] B[1], A + B, AN + BN), \
			                #(distance A[na] B[nb], A + (ra_rev B), AN + (ra_rev BN)), \
			                #(distance A[1] B[nb], B + A, BN + AN), \
			                #(distance A[1] B[1], (ra_rev B) + A, (ra_rev BN) + AN))
			local best = cands[1]
			for c in cands where c[1] < best[1] do best = c
			RA_S.pending = #(#(best[2], best[3]))
			#wait
		)
	)
	else #wait
)

-- ---------------------------------------------------------------------------
-- 이어짐 / 새로 생성 표시
-- ---------------------------------------------------------------------------

-- 이 점에서 선을 시작/끝내면 기존 메쉬(또는 대기 선)에 이어지는지
--  #(#edge, v1, v2) 열린 엣지에 붙음 / #(#vert, v) 버텍스에 합쳐짐 / #(#pending, 점) 대기 선과 이어짐 / #(#none)
fn ra_connectAt p dir:undefined =
(
	local r = #(#none)
	local obj = RA_S.retopo
	if p != undefined do
	(
		if ra_isPoly obj and (polyop.getNumVerts obj) > 0 do
		(
			local w = if RA_S.stripWidth > 0 then RA_S.stripWidth else RA_S.spacing
			local att = ra_findAttach obj p w dir:dir
			if att != undefined then r = #(#edge, att[1], att[2])
			else
			(
				local v = ra_nearestVert obj p (amax (amin RA_S.mergeDist (RA_S.spacing * 0.45)) (w * 0.5))
				if v > 0 do r = #(#vert, v)
			)
		)
		if r[1] == #none do
		(
			local join = ra_joinTol()
			for s in RA_S.pending do
				for q in #(s[1][1], s[1][s[1].count]) where r[1] == #none and (distance q p) < join do r = #(#pending, q)
		)
	)
	r
)

-- 변환 전 열린 경계 버텍스 위치 (결과가 기존 메쉬에 붙었는지 판단용)
fn ra_openPos obj =
(
	if not ra_isPoly obj or (polyop.getNumFaces obj) == 0 then #()
	else for v in (polyop.getVertsUsingEdge obj (polyop.getOpenEdges obj)) collect polyop.getVert obj v
)

-- 방금 만든 면을 잠깐 강조: 기존 메쉬에 붙었으면 초록 "이어서 생성", 떨어져 있으면 주황 "따로 생성"
fn ra_makeFlash obj oldNF oldOpen result =
(
	RA_S.flash = undefined
	if RA_S.showConnect and ra_isPoly obj do
	(
		local nf = polyop.getNumFaces obj
		local loops = #()
		local connected = (result == #cut)
		local tol = RA_S.spacing * 0.02
		local c = [0, 0, 0]
		local cnt = 0
		for f = (oldNF + 1) to nf do
		(
			local vs = polyop.getFaceVerts obj f
			if vs != undefined do
			(
				local pts = for v in vs collect polyop.getVert obj v
				append loops pts
				for q in pts do
				(
					c += q
					cnt += 1
					if not connected do for o in oldOpen while not connected do if (distance o q) < tol do connected = true
				)
			)
		)
		if loops.count > 0 do
		(
			local lbl = if result == #cut then "컷" else if connected then "이어서 생성" else "따로 생성"
			RA_S.flash = #(loops, (if connected then RA_S.connColor else RA_S.newColor), lbl, c / cnt, timeStamp())
		)
	)
)

fn ra_flushPending =
(
	if RA_S.pending.count > 0 and ra_isPoly RA_S.retopo do
	(
		local oldNF = polyop.getNumFaces RA_S.retopo
		local oldOpen = ra_openPos RA_S.retopo
		RA_S.busy = true
		undo "Retopo 스트립" on
		(
			for s in RA_S.pending do ra_strip RA_S.retopo s[1] s[2]
		)
		RA_S.busy = false
		ra_makeFlash RA_S.retopo oldNF oldOpen #strip
	)
	RA_S.pending = #()
	redrawViews()
)

-- ---------------------------------------------------------------------------
-- 주름 만들기: 선택 버텍스들을 잇는 경로로 컷 + 컷으로 생긴 버텍스 자동 합치기
-- ---------------------------------------------------------------------------

-- 선택 순서 정보가 없으므로: 가장 바깥 점에서 시작해 가까운 점을 차례로 잇는다
fn ra_orderPoints obj vs =
(
	local pos = for v in vs collect polyop.getVert obj v
	local c = [0, 0, 0]
	for q in pos do c += q
	c /= pos.count
	local start = 1
	local md = -1.0
	for i = 1 to pos.count do (local d = distance pos[i] c; if d > md do (md = d; start = i))
	local order = #(vs[start])
	local used = #{start}
	while order.count < vs.count do
	(
		local last = polyop.getVert obj order[order.count]
		local bi = 0
		local bd = 1e30
		for i = 1 to vs.count where not used[i] do (local d = distance pos[i] last; if d < bd do (bd = d; bi = i))
		used[bi] = true
		append order vs[bi]
	)
	order
)

fn ra_projectCrease p n obj reach =
(
	if ra_hasTarget() then ra_project p n
	else
	(
		local best = undefined
		local bd = 1e30
		for r in #(ray (p + n * reach) (-n), ray (p - n * reach) n) do
		(
			local h = intersectRay obj r
			if h != undefined do (local d = distance h.pos p; if d < bd do (bd = d; best = h.pos))
		)
		if best == undefined then p else best
	)
)

-- 반환: #(구간 수, 컷 수, 합친 버텍스 수)
fn ra_crease obj ratio closed =
(
	local sel = (polyop.getVertSelection obj) as array
	if sel.count < 2 then #(0, 0, 0)
	else
	(
		local order = ra_orderPoints obj sel
		local anchors = for v in order collect polyop.getVert obj v
		local nrm = ra_vertNormal obj order[1]
		if nrm == undefined do nrm = [0, 0, 1]
		local ne = polyop.getNumEdges obj
		local avg = 0.0
		for e = 1 to ne do (local ev = polyop.getEdgeVerts obj e; avg += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]))
		avg /= amax 1 ne
		local savedSpacing = RA_S.spacing
		RA_S.spacing = avg
		local oldCount = polyop.getNumVerts obj
		local segs = for i = 1 to anchors.count - 1 collect #(anchors[i], anchors[i + 1], order[i], order[i + 1])
		if closed and anchors.count > 2 do append segs #(anchors[anchors.count], anchors[1], order[order.count], order[1])
		local cuts = 0
		local merged = 0
		local passed = #()
		RA_S.busy = true
		undo "Retopo 주름 만들기" on
		(
			for sg in segs do
			(
				local A = sg[1]
				local B = sg[2]
				local n = amax 8 (((distance A B) / (avg * 0.2)) as integer + 1)
				local pts = #()
				for t = 0 to n do
				(
					local q = A + (B - A) * (t / (n as float))
					append pts (if t == 0 or t == n then q else ra_projectCrease q nrm obj (avg * 2.0))
				)
				RA_lastCutVerts = #()
				if (ra_cut obj pts false snap:(amax 0.08 ratio)) > 0 do cuts += 1
				merged += RA_lastSnapCount
				passed += RA_lastCutVerts
				-- 앵커 → 컷 경로 → 앵커: 같은 면인데 엣지가 없으면 직접 연결 (끝점 교차 누락 보정)
				local chain = #(sg[3]) + RA_lastCutVerts + #(sg[4])
				for i = 1 to chain.count - 1 do
				(
					local va = chain[i]
					local vb = chain[i + 1]
					if va != vb and (ra_edgeBetween obj va vb) == undefined do
					(
						local common = (polyop.getFacesUsingVert obj va) * (polyop.getFacesUsingVert obj vb)
						if not common.isEmpty do polyop.createEdge obj va vb
					)
				)
			)
			-- 원래 버텍스 근처 교차점은 컷 단계에서 이미 그 버텍스로 합쳐짐(snap). 경로 버텍스 선택
			local selB = (order as bitArray) + (passed as bitArray)
			polyop.setVertSelection obj selB
		)
		RA_S.busy = false
		RA_S.spacing = savedSpacing
		redrawViews()
		#(segs.count, cuts, merged)
	)
)

-- ---------------------------------------------------------------------------
-- 빈 곳 채우기: 스트립/면으로 둘러싸인 빈 곳을 기존 경계 버텍스를 그대로 써서 쿼드로 채움
--  - 빈 곳을 둘러싼 경계 버텍스를 선택 (U자 안쪽이면 입구 양 끝 버텍스 2개만 골라도 됨)
--  - 같은 경계에서 고른 점들은 그 사이 '짧은 쪽' 경계를 따라 이어짐
--  - 경계 줄 1개(열림) → 두 끝을 새 변으로 이어 닫음 / 2개 → 두 줄 사이 / 닫힌 경계 → 구멍
-- ---------------------------------------------------------------------------

fn ra_openAdj obj =
(
	local adj = for i = 1 to polyop.getNumVerts obj collect #()
	for e in (polyop.getOpenEdges obj) do
	(
		local ev = polyop.getEdgeVerts obj e
		append adj[ev[1]] ev[2]
		append adj[ev[2]] ev[1]
	)
	adj
)

-- start 가 속한 경계가 단순한 고리면 순서대로 버텍스 목록
fn ra_openCycle adj start =
(
	local loop = #(start)
	local prev = 0
	local cur = start
	local ok = true
	local done = false
	while ok and not done do
	(
		local nb = adj[cur]
		if nb.count != 2 or nb[1] == nb[2] then ok = false
		else
		(
			local nx = if nb[1] != prev then nb[1] else nb[2]
			if nx == start then done = true
			else if loop.count > 100000 then ok = false
			else (append loop nx; prev = cur; cur = nx)
		)
	)
	if ok then loop else undefined
)

-- 열린 엣지만 따라 a→b 최단 경로
fn ra_openPath obj adj a b =
(
	local nv = adj.count
	local dist = for i = 1 to nv collect 1e30
	local back = for i = 1 to nv collect 0
	local done = #{}
	dist[a] = 0.0
	local front = #(a)
	local found = false
	while front.count > 0 and not found do
	(
		local bi = 1
		for k = 2 to front.count where dist[front[k]] < dist[front[bi]] do bi = k
		local v = front[bi]
		deleteItem front bi
		if not done[v] do
		(
			done[v] = true
			if v == b then found = true
			else
			(
				local pv = polyop.getVert obj v
				for y in adj[v] where not done[y] do
				(
					local nd = dist[v] + distance pv (polyop.getVert obj y)
					if nd < dist[y] do (dist[y] = nd; back[y] = v; append front y)
				)
			)
		)
	)
	if not found then undefined
	else
	(
		local p = #(b)
		while p[p.count] != a do append p back[p[p.count]]
		ra_rev p
	)
)

-- 선택에서 채울 경계 줄들 → #(#(버텍스 목록, 닫힘), ...) 또는 오류 문자열
fn ra_gapChains obj =
(
	local adj = ra_openAdj obj
	local nv = adj.count
	local comp = for i = 1 to nv collect 0
	local cid = 0
	for v = 1 to nv where adj[v].count > 0 and comp[v] == 0 do
	(
		cid += 1
		local stack = #(v)
		while stack.count > 0 do
		(
			local x = stack[stack.count]
			deleteItem stack stack.count
			if comp[x] == 0 do
			(
				comp[x] = cid
				for y in adj[x] where comp[y] == 0 do append stack y
			)
		)
	)
	local sel = polyop.getVertSelection obj
	if (try (subObjectLevel == 2 or subObjectLevel == 3) catch false) do sel += polyop.getVertsUsingEdge obj (polyop.getEdgeSelection obj)
	local groups = for i = 1 to cid collect #()
	for v in sel where v <= nv and comp[v] > 0 do append groups[comp[v]] v
	groups = for g in groups where g.count >= 2 collect g
	if groups.count == 0 then "빈 곳을 둘러싼 경계(열린 엣지) 버텍스를 2개 이상 선택하세요"
	else
	(
		local chains = #()
		local err = undefined
		for g in groups while err == undefined do
		(
			local cyc = ra_openCycle adj g[1]
			if cyc != undefined then
			(
				if g.count == cyc.count then append chains #(cyc, true)
				else
				(
					-- 고른 점들을 모두 덮는 가장 짧은 호 = 고리에서 선택 사이 가장 큰 빈틈을 뺀 나머지
					local n = cyc.count
					local selB = g as bitArray
					local idx = for i = 1 to n where selB[cyc[i]] collect i
					local lens = for i = 1 to n collect distance (polyop.getVert obj cyc[i]) (polyop.getVert obj cyc[ra_wrap (i + 1) n])
					local bestK = 1
					local bestL = -1.0
					for k = 1 to idx.count do
					(
						local i1 = idx[k]
						local i2 = idx[ra_wrap (k + 1) idx.count]
						local L = 0.0
						local j = i1
						while j != i2 do (L += lens[j]; j = ra_wrap (j + 1) n)
						if L > bestL do (bestL = L; bestK = k)
					)
					local startI = idx[ra_wrap (bestK + 1) idx.count]
					local endI = idx[bestK]
					local arc = #(cyc[startI])
					local j = startI
					while j != endI do (j = ra_wrap (j + 1) n; append arc cyc[j])
					append chains #(arc, false)
				)
			)
			else if g.count != 2 then err = "경계가 여러 갈래로 이어져 있습니다. 빈 곳 입구의 양 끝 버텍스 2개만 선택하세요"
			else
			(
				local p = ra_openPath obj adj g[1] g[2]
				if p == undefined or p.count < 2 then err = "선택한 두 버텍스가 경계로 이어져 있지 않습니다"
				else append chains #(p, false)
			)
		)
		if err != undefined then err
		else if chains.count > 2 then ("경계 줄은 1~2개만 선택하세요 (지금 " + chains.count as string + "개)")
		else chains
	)
)

fn ra_turnAt P i N w = ((ra_angle (P[i] - P[ra_wrap (i - w) N]) (P[ra_wrap (i + w) N] - P[i])) * pi / 180.0)
fn ra_segLen cum total N i k = (local j = i + k; if j <= N + 1 then cum[j] - cum[i] else (total - cum[i]) + cum[j - N])

-- 닫힌 경계 점 P(N개, 짝수)를 마주보는 변끼리 개수가 같은 4변으로 나눔 → #(i0, a, b)
-- 경계 점마다 영역 밖에서 들어오는 엣지 방향 (영역 안쪽을 향함). 딱 하나가 아니면 undefined
fn ra_boundaryExt obj lp fs =
(
	for v in lp collect
	(
		local cand = #()
		for e in (polyop.getEdgesUsingVert obj v) do
		(
			local inR = false
			for f in (polyop.getEdgeFaces obj e) where fs[f] do inR = true
			if not inR do append cand (ra_other obj e v)
		)
		local r = undefined
		if cand.count == 1 do
		(
			local d = (polyop.getVert obj v) - (polyop.getVert obj cand[1])
			if (length d) > 1e-9 do r = normalize d
		)
		r
	)
)

-- 모서리 (i0, a, b) 로 나눴을 때 격자 선이 주변에서 들어오는 엣지를 얼마나 곧게 잇는지 (0~1)
fn ra_flowContinuity P ext i0 a b step:1 =
(
	local N = P.count
	local s = 0.0
	local n = 0
	local prs = #()
	for k = 1 to a - 1 by step do
	(
		local lo = ra_wrap (i0 + k) N
		local hi = ra_wrap (i0 + 2 * a + b - k) N
		append prs #(lo, hi)
		append prs #(hi, lo)
	)
	for j = 1 to b - 1 by step do
	(
		local lf = ra_wrap (i0 - j) N
		local rt = ra_wrap (i0 + a + j) N
		append prs #(lf, rt)
		append prs #(rt, lf)
	)
	for pr in prs where ext[pr[1]] != undefined do
	(
		local d = P[pr[2]] - P[pr[1]]
		if (length d) > 1e-9 do (s += amax 0.0 (dot (normalize d) ext[pr[1]]); n += 1)
	)
	if n > 0 then s / n else 0.0
)

fn ra_gridMaxAspect grid =
(
	local worst = 1.0
	for j = 1 to grid.count - 1 do for i = 1 to grid[1].count - 1 do
	(
		local q = #(grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
		local ls = for k = 1 to 4 collect distance q[k] q[ra_wrap (k + 1) 4]
		worst = amax worst ((amax ls) / (amax (amin ls) 1e-9))
	)
	worst
)

fn ra_cmpScoreDesc a b = (if a[1] > b[1] then -1 else if a[1] < b[1] then 1 else 0)

-- top > 1 이면 점수 높은 순 후보 목록 #(#(i0, a, b), ...)
fn ra_solveQuadSides P bonus top:1 =
(
	local N = P.count
	local half = N / 2
	local cum = #(0.0)
	for i = 1 to N do append cum (cum[i] + distance P[i] P[ra_wrap (i + 1) N])
	local total = cum[N + 1]
	local turn = for i = 1 to N collect (amax (ra_turnAt P i N 1) ((ra_turnAt P i N 2) * 0.8))
	local bon = bonus as bitArray
	local best = #(1, 1, half - 1)
	local bestS = -1e30
	local allc = #()
	for i0 = 1 to N do for a = 1 to half - 1 do
	(
		local b = half - a
		local c2 = ra_wrap (i0 + a) N
		local c3 = ra_wrap (i0 + half) N
		local c4 = ra_wrap (i0 + half + a) N
		local sc = turn[i0] + turn[c2] + turn[c3] + turn[c4]
		for c in #(i0, c2, c3, c4) where bon[c] do sc += 0.6
		local L1 = ra_segLen cum total N i0 a
		local L2 = ra_segLen cum total N c2 b
		local L3 = ra_segLen cum total N c3 a
		local L4 = ra_segLen cum total N c4 b
		sc -= 1.5 * ((abs (L1 - L3)) / (amax (L1 + L3) 1e-9) + (abs (L2 - L4)) / (amax (L2 + L4) 1e-9))
		-- 칸이 정사각형에 가깝게 (한 줄짜리 길쭉한 쿼드 방지): 실제로 마주보는 변 사이 거리로 칸 크기 추정
		local along = 0.0
		local across = 0.0
		for t in #(0.25, 0.5, 0.75) do
		(
			local kb = ra_round (t * b)
			local ka = ra_round (t * a)
			along += (distance P[ra_wrap (i0 - kb) N] P[ra_wrap (i0 + a + kb) N]) / a
			across += (distance P[ra_wrap (i0 + ka) N] P[ra_wrap (i0 + 2 * a + b - ka) N]) / b
		)
		sc -= 2.0 * abs ((log (amax along 1e-9)) - (log (amax across 1e-9)))
		if RA_S.flowDir != undefined and (length RA_S.flowDir) > 1e-9 do
		(
			-- 엣지 줄(첫 변과 셋째 변 방향)이 그은 선과 나란할수록 좋음
			local fl = normalize RA_S.flowDir
			local d1 = P[c2] - P[i0]
			local d3 = P[c3] - P[c4]
			if (length d1) > 1e-9 do sc += 3.0 * abs (dot (normalize d1) fl)
			if (length d3) > 1e-9 do sc += 3.0 * abs (dot (normalize d3) fl)
		)
		if RA_S.extDirs != undefined do sc += 4.0 * (ra_flowContinuity P RA_S.extDirs i0 a b step:(if N > 80 then 3 else 1))
		if top > 1 do append allc #(sc, i0, a, b)
		if sc > bestS do (bestS = sc; best = #(i0, a, b))
	)
	if top > 1 then
	(
		qsort allc ra_cmpScoreDesc
		for k = 1 to (amin top allc.count) collect #(allc[k][2], allc[k][3], allc[k][4])
	)
	else best
)

fn ra_vnrm obj v = (local n = ra_vertNormal obj v; if n == undefined then [0, 0, 1] else n)

-- pa→pb 사이 새 점 (cnt 칸, 양 끝 제외) → #(#(위치, 노멀), ...)
fn ra_closingPts pa pb na nb cnt =
(
	local out = #()
	for k = 1 to cnt - 1 do
	(
		local t = k / (cnt as float)
		local nn = na + (nb - na) * t
		nn = if length nn < 1e-9 then na else normalize nn
		append out #(ra_project (pa + (pb - pa) * t) nn, nn)
	)
	out
)

-- 경계 고리에서 꺾이는 곳(두 표면 교차선) 위에 있는 점 찾기 → #(#(번호, 거리, 앞쪽 노멀, 뒤쪽 노멀), ...)
fn ra_loopCreases GP GN avg =
(
	local N = GP.count
	local hn = #()
	for i = 1 to N do
	(
		local h = ra_projectHit GP[i] GN[i]
		append hn (if h[2] == undefined then GN[i] else h[2])
	)
	local cand = #()
	for i = 1 to N do
	(
		local ia = ra_wrap (i - 1) N
		local ib = ra_wrap (i + 1) N
		local a = hn[ia]
		local b = hn[ib]
		if (ra_angle a b) > 30 do
		(
			local x = ra_planeCross GP[ia] a GP[ib] b
			if x != undefined do
			(
				local d = distance x GP[i]
				if d < avg * 0.25 do append cand #(i, d, a, b)
			)
		)
	)
	-- 붙어 있는 후보는 교차선에 가장 가까운 하나만
	local out = #()
	for c in cand do
	(
		local merged = false
		for k = 1 to out.count while not merged do
		(
			local dj = abs (out[k][1] - c[1])
			if dj <= 1 or dj >= N - 1 do
			(
				merged = true
				if c[2] < out[k][2] do out[k] = c
			)
		)
		if not merged do append out c
	)
	out
)

-- 점 x 를 두 표면(노멀 nA, nB)의 교선 위로
fn ra_onCrease x nA nB =
(
	local pa = (ra_projectHit x nA)[1]
	local pb = (ra_projectHit x nB)[1]
	local q = ra_planeCross pa nA pb nB
	if q == undefined or (distance q x) > RA_S.spacing * 3 then x else q
)

-- 경계 고리 하나(전체 항목 번호 목록)를 쿼드 그리드로 계획 → #(그리드 칸의 항목 번호(안쪽 0), 위치 그리드, 노멀 그리드, a, b)
-- 뒤집히거나 꼬인(보타이) 칸이 있으면 true (한 모서리만 오목한 칸은 허용)
fn ra_gridTangled grid ngrid =
(
	local rows = grid.count
	local cols = grid[1].count
	local bad = false
	local negc = 0
	local tot = 0
	for j = 1 to rows - 1 while not bad do for i = 1 to cols - 1 do
	(
		local q = #(grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
		local ref = ngrid[j][i] + ngrid[j + 1][i + 1]
		local pos = 0
		local neg = 0
		for k = 1 to 4 do
		(
			local s = dot (cross (q[ra_wrap (k + 1) 4] - q[k]) (q[ra_wrap (k + 2) 4] - q[ra_wrap (k + 1) 4])) ref
			if s > 0 then pos += 1 else if s < 0 do neg += 1
		)
		if pos == 2 and neg == 2 do bad = true
		if neg > pos do negc += 1
		tot += 1
	)
	bad or (negc > 0 and negc < tot)
)

fn ra_planPatch GP GN loopIdx bonusLocal sides:undefined =
(
	local N = loopIdx.count
	local P = for k in loopIdx collect GP[k]
	local NR = for k in loopIdx collect GN[k]
	local sol = if sides != undefined then sides else ra_solveQuadSides P bonusLocal
	local i0 = sol[1]
	local a = sol[2]
	local b = sol[3]
	local S1 = for k = 0 to a collect ra_wrap (i0 + k) N
	local S2 = for k = 0 to b collect ra_wrap (i0 + a + k) N
	local S3 = for k = 0 to a collect ra_wrap (i0 + a + b + k) N
	local S4 = for k = 0 to b collect ra_wrap (i0 + 2 * a + b + k) N
	-- (for 식을 함수 인자로 바로 넘기면 오류가 나므로 먼저 변수에 담음 / 대소문자 구분 없음 주의)
	local sideP1 = for k in S1 collect P[k]
	local sideP2 = for k in S2 collect P[k]
	local sideP3 = for k = S3.count to 1 by -1 collect P[S3[k]]
	local sideP4 = for k = S4.count to 1 by -1 collect P[S4[k]]
	local sideN1 = for k in S1 collect NR[k]
	local sideN2 = for k in S2 collect NR[k]
	local sideN3 = for k = S3.count to 1 by -1 collect NR[S3[k]]
	local sideN4 = for k = S4.count to 1 by -1 collect NR[S4[k]]
	local grid = ra_coons sideP1 sideP2 sideP3 sideP4
	local ng0 = ra_coons sideN1 sideN2 sideN3 sideN4
	local ngrid = ra_normGrid ng0
	for j = 2 to b do for i = 2 to a do grid[j][i] = ra_project grid[j][i] ngrid[j][i]
	-- 경계 점 → 바로 안쪽 점 쌍 (주변에서 들어오는 엣지 방향이 있는 것만): 그 방향으로 당겨 흐름을 곧게 이음
	local pulls = #()
	local ext = RA_S.extDirs
	if ext != undefined and a > 1 and b > 1 do
	(
		for i = 1 to a - 1 do
		(
			append pulls #(1, i + 1, 2, i + 1, ext[loopIdx[S1[i + 1]]])
			append pulls #(b + 1, i + 1, b, i + 1, ext[loopIdx[S3[a - i + 1]]])
		)
		for j = 1 to b - 1 do
		(
			append pulls #(j + 1, 1, j + 1, 2, ext[loopIdx[S4[b - j + 1]]])
			append pulls #(j + 1, a + 1, j + 1, a, ext[loopIdx[S2[j + 1]]])
		)
		pulls = for p in pulls where p[5] != undefined collect p
	)
	local relaxN = amax 2 RA_S.relaxIters
	for pass = 1 to 13 do
	(
		-- 첫 번은 기본 이완(+경계 흐름 잇기), 그다음은 칸이 꼬이거나 뒤집혔을 때만 더 고르게 펴서 풀어 줌
		if pass == 1 or (ra_gridTangled grid ngrid) then
		(
			for it = 1 to (if pass == 1 then relaxN else 5) do
			(
				for j = 2 to b do for i = 2 to a do grid[j][i] = (grid[j - 1][i] + grid[j + 1][i] + grid[j][i - 1] + grid[j][i + 1]) * 0.25
				if pass == 1 do for p in pulls do
				(
					local pb = grid[p[1]][p[2]]
					local pn = grid[p[3]][p[4]]
					local tgt = pb + p[5] * (distance pn pb)
					grid[p[3]][p[4]] = pn + (tgt - pn) * 0.6
				)
				for j = 2 to b do for i = 2 to a do grid[j][i] = ra_project grid[j][i] ngrid[j][i]
			)
		)
		else exit
	)
	if RA_S.snapCreases do grid = ra_snapGridCreases grid ngrid
	local gi = #()
	for j = 0 to b do
	(
		local row = #()
		for i = 0 to a do
		(
			local li = if j == 0 then S1[i + 1] else if j == b then S3[a - i + 1] else if i == 0 then S4[b - j + 1] else if i == a then S2[j + 1] else 0
			append row (if li > 0 then loopIdx[li] else 0)
		)
		append gi row
	)
	#(gi, grid, ngrid, a, b)
)

-- 선택한 경계로 둘러싼 빈 곳을 쿼드로 채움 → #(만든 면 수, 메시지)
fn ra_fillGap obj =
(
	local chains = ra_gapChains obj
	if classOf chains == String then #(0, chains)
	else
	(
		local oes = polyop.getOpenEdges obj
		local avg = 0.0
		for e in oes do (local ev = polyop.getEdgeVerts obj e; avg += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]))
		avg = if oes.numberSet > 0 then avg / oes.numberSet else RA_S.spacing
		-- 경계 고리: 항목 = 기존 버텍스 번호(integer) 또는 새 점 #(위치, 노멀)
		local items = #()
		local bonus = #()
		if chains.count == 1 and chains[1][2] then
		(
			items = for v in chains[1][1] collect v
			if (mod items.count 2) == 1 do
			(
				-- 홀수면 쿼드로 못 채우므로 가장 긴 경계 엣지 가운데에 버텍스 하나 추가
				local n = items.count
				local k = 1
				local bl = -1.0
				for i = 1 to n do (local L = distance (polyop.getVert obj items[i]) (polyop.getVert obj items[ra_wrap (i + 1) n]); if L > bl do (bl = L; k = i))
				local e = ra_edgeBetween obj items[k] items[ra_wrap (k + 1) n]
				-- (되돌리기 기록 안에서 바꿔야 Ctrl+Z 가 안전함)
				local nvx = 0
				undo "Retopo 빈 곳 채우기 (버텍스 추가)" on
				(
					nvx = polyop.divideEdge obj e 0.5
					if nvx > 0 do polyop.setVert obj #(nvx) (ra_project (polyop.getVert obj nvx) (ra_vnrm obj items[k]))
				)
				if nvx > 0 do insertItem nvx items (k + 1)
			)
		)
		else if chains.count == 1 then
		(
			local ch = chains[1][1]
			local pa = polyop.getVert obj ch[ch.count]
			local pb = polyop.getVert obj ch[1]
			local g = (distance pa pb) / avg
			local c = amax 1 (ra_round g)
			if (mod (ch.count - 1 + c) 2) == 1 do c = if g >= c or c == 1 then c + 1 else c - 1
			items = (for v in ch collect v) + (ra_closingPts pa pb (ra_vnrm obj ch[ch.count]) (ra_vnrm obj ch[1]) c)
			bonus = #(1, ch.count)
		)
		else
		(
			local A = chains[1][1]
			local B = chains[2][1]
			local a1 = polyop.getVert obj A[1]
			local an = polyop.getVert obj A[A.count]
			if (distance an (polyop.getVert obj B[1])) + (distance (polyop.getVert obj B[B.count]) a1) > \
			   (distance an (polyop.getVert obj B[B.count])) + (distance (polyop.getVert obj B[1]) a1) do B = ra_rev B
			local b1 = polyop.getVert obj B[1]
			local bn = polyop.getVert obj B[B.count]
			local c1 = amax 1 (ra_round ((distance an b1) / avg))
			local c2 = amax 1 (ra_round ((distance bn a1) / avg))
			if (mod (A.count - 1 + B.count - 1 + c1 + c2) 2) == 1 do c2 += 1
			items = (for v in A collect v) + (ra_closingPts an b1 (ra_vnrm obj A[A.count]) (ra_vnrm obj B[1]) c1) + \
			        (for v in B collect v) + (ra_closingPts bn a1 (ra_vnrm obj B[B.count]) (ra_vnrm obj A[1]) c2)
			bonus = #(1, A.count, A.count + c1, A.count + c1 + B.count - 1)
		)
		local N = items.count
		if N < 4 then #(0, "채울 경계가 너무 짧습니다")
		else
		(
			local GP = for x in items collect (if classOf x == Integer then polyop.getVert obj x else x[1])
			local GN = for x in items collect (if classOf x == Integer then ra_vnrm obj x else x[2])
			-- 빈 곳이 두 표면(바닥/벽 등)에 걸쳐 있으면 교차선을 따라 두 조각으로 나눠 채움
			-- → 조각마다 한 표면 위에만 있어 면이 접히거나 겹치지 않고, 교차선 위에 버텍스 줄이 생김
			local patches = #()
			local cz = if RA_S.snapCreases then ra_loopCreases GP GN avg else #()
			if cz.count == 2 do
			(
				local ca = if cz[1][1] < cz[2][1] then cz[1] else cz[2]
				local cb = if cz[1][1] < cz[2][1] then cz[2] else cz[1]
				local i1 = ca[1]
				local i2 = cb[1]
				local n1 = i2 - i1
				local n2 = N - n1
				if n1 >= 2 and n2 >= 2 do
				(
					local nA = ca[3]
					local nB = ca[4]
					local nC = normalize (nA + nB)
					local q1 = GP[i1]
					local q2 = GP[i2]
					local g = (distance q1 q2) / avg
					local c = amax 1 (ra_round g)
					if (mod (n1 + c) 2) == 1 do c = if g >= c or c == 1 then c + 1 else c - 1
					local row = #()
					for k = 1 to c - 1 do
					(
						local x = ra_onCrease (q1 + (q2 - q1) * (k / (c as float))) nA nB
						append items #(x, nC)
						append GP x
						append GN nC
						append row items.count
					)
					local loop1 = (for k = i1 to i2 collect k) + (ra_rev row)
					local loop2 = (for k = i2 to N collect k) + (for k = 1 to i1 collect k) + row
					local b1 = #(1, i2 - i1 + 1)
					local b2 = #(1, N - i2 + 1 + i1)
					for k in bonus do
					(
						local p1 = findItem loop1 k
						local p2 = findItem loop2 k
						if p1 > 0 do appendIfUnique b1 p1
						if p2 > 0 do appendIfUnique b2 p2
					)
					patches = #(#(loop1, b1), #(loop2, b2))
				)
			)
			if patches.count == 0 do patches = #(#((for k = 1 to N collect k), bonus))
			local plans = for pt in patches collect ra_planPatch GP GN pt[1] pt[2]
			global RA_lastFillInfo = #(N, cz.count, (for pt in patches collect #(pt[1].count, pt[2])), (for pl in plans collect #(pl[4], pl[5])))
			-- 검사: 접힌 쿼드 / 선택한 경계 안쪽이 이미 면인지
			local total = 0
			local bad = 0
			local over = 0
			local under = 0
			for pl in plans do
			(
				local gi = pl[1]
				local grid = pl[2]
				local a = pl[4]
				local b = pl[5]
				for j = 1 to b do for i = 1 to a do
				(
					local qp = #(grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i])
					total += 1
					if not (ra_quadOk qp) do bad += 1
					local cells = #(gi[j][i], gi[j][i + 1], gi[j + 1][i + 1], gi[j + 1][i])
					local qc = (qp[1] + qp[2] + qp[3] + qp[4]) / 4.0
					for k = 1 to 4 do
					(
						local u = cells[k]
						local w = cells[(mod k 4) as integer + 1]
						if u > 0 and w > 0 and classOf items[u] == Integer and classOf items[w] == Integer do
						(
							local e = ra_edgeBetween obj items[u] items[w]
							if e != undefined do
							(
								local fs = polyop.getEdgeFaces obj e
								if fs.count > 0 do
								(
									local pa = polyop.getVert obj items[u]
									local pb = polyop.getVert obj items[w]
									local m = (pa + pb) * 0.5
									local d = normalize (pb - pa)
									local fc = polyop.getFaceCenter obj fs[1]
									local u1 = (qc - m) - d * (dot (qc - m) d)
									local u2 = (fc - m) - d * (dot (fc - m) d)
									if dot u1 u2 > 0 then over += 1 else under += 1
								)
							)
						)
					)
				)
			)
			if bad > total * 0.3 do over = 1000000
			if over > under then #(0, "채울 빈 곳이 없습니다 (선택한 경계 안쪽이 이미 면이거나 폭이 없음). 빈 곳을 둘러싼 경계를 선택하세요")
			else
			(
				local oldNF = polyop.getNumFaces obj
				local oldOpen = ra_openPos obj
				local made = 0
				local sizes = ""
				RA_S.busy = true
				undo "Retopo 빈 곳 채우기" on
				(
					-- 새 버텍스: 닫는 변 / 교차선 점 + 조각마다 안쪽 점
					local vid = for k = 1 to items.count collect (if classOf items[k] == Integer then items[k] else polyop.createVert obj items[k][1])
					local quads = #()
					local firstP = undefined
					local firstN = undefined
					for pl in plans do
					(
						local gi = pl[1]
						local grid = pl[2]
						local a = pl[4]
						local b = pl[5]
						sizes += (if sizes == "" then "" else " + ") + a as string + " x " + b as string
						local V = for j = 0 to b collect (for i = 0 to a collect \
							(if gi[j + 1][i + 1] > 0 then vid[gi[j + 1][i + 1]] else polyop.createVert obj grid[j + 1][i + 1]))
						for j = 1 to b do for i = 1 to a do append quads #(V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i])
						if firstP == undefined do (firstP = #(grid[1][1], grid[1][2], grid[2][2], grid[2][1]); firstN = pl[3][1][1])
					)
					-- 방향: 이웃 면과 같은 방향이면 뒤집음 (조각끼리도 순서대로 만들어 서로 맞춰짐)
					local same = 0
					local opp = 0
					for q in quads do (local r = ra_winding obj q; same += r[1]; opp += r[2])
					local flip = same > opp
					if same == 0 and opp == 0 do flip = (dot (cross (firstP[2] - firstP[1]) (firstP[4] - firstP[1])) firstN) < 0
					local newF = #{}
					for q in quads do
					(
						local qq = if flip then ra_rev q else q
						local f = polyop.createPolygon obj (ra_bestQuadOrder obj qq)
						if f != undefined do (newF[f] = true; made += 1)
					)
					polyop.setVertSelection obj #{}
					polyop.setFaceSelection obj newF
				)
				RA_S.busy = false
				RA_S.lastRec = undefined
				ra_makeFlash obj oldNF oldOpen #fill
				redrawViews()
				#(made, "빈 곳 채우기: 면 " + made as string + "개 (" + sizes + (if plans.count > 1 then ", 꺾이는 곳에서 나눔" else "") + ")")
			)
		)
	)
)

-- ---------------------------------------------------------------------------
-- 영역 재구성: 선택한 면 영역을 바깥 경계는 그대로 두고 쿼드 격자로 다시 채움
--  - 흐름 방향(주석으로 그은 선)을 주면 엣지 줄이 그 방향을 따르도록 모서리를 고름
--  - 방향 없이 = 고르게(평평하게) 재구성: 극점·삼각형·찌그러진 면을 없애고 간격을 고르게
-- ---------------------------------------------------------------------------

-- 면 영역의 바깥 경계 → 순서대로 버텍스 목록 또는 오류 문자열
fn ra_regionLoop obj fs =
(
	local nv = polyop.getNumVerts obj
	local adj = for i = 1 to nv collect #()
	local bcount = 0
	for e in (polyop.getEdgesUsingFace obj fs) do
	(
		local c = 0
		for f in (polyop.getEdgeFaces obj e) where fs[f] do c += 1
		if c == 1 do
		(
			local ev = polyop.getEdgeVerts obj e
			append adj[ev[1]] ev[2]
			append adj[ev[2]] ev[1]
			bcount += 1
		)
	)
	local start = 0
	for v = 1 to nv while start == 0 where adj[v].count > 0 do start = v
	if start == 0 then "영역 경계를 찾지 못했습니다 (면을 선택하세요)"
	else
	(
		local bad = false
		for v = 1 to nv where adj[v].count > 0 and adj[v].count != 2 do bad = true
		if bad then "영역 경계가 한 줄로 이어지지 않습니다 (모서리 한 점으로만 붙은 면이 있음)"
		else
		(
			local lp = ra_openCycle adj start
			if lp == undefined or lp.count != bcount then "영역 안에 구멍이 있거나 떨어진 조각이 있습니다 (구멍 없는 한 덩어리를 선택하세요)"
			else lp
		)
	)
)

-- 선택 면 영역을 다시 채움 → #(새 면 수, 메시지)
-- 오목하게 파인 칸(영역과 엣지 2개 이상 맞닿은 바깥 쿼드)을 채워 경계를 매끈하게 (너무 커지면 undefined)
fn ra_growRegion obj fs limit:1.6 =
(
	local r = copy fs
	local n0 = fs.numberSet
	local go = true
	for it = 1 to 40 while go do
	(
		local cnt = #()
		for f in r do for e in (polyop.getEdgesUsingFace obj #{f}) do
			for g in (polyop.getEdgeFaces obj e) where not r[g] do cnt[g] = (if cnt[g] == undefined then 1 else cnt[g] + 1)
		local add = #{}
		for g = 1 to cnt.count where cnt[g] != undefined and cnt[g] >= 2 and (polyop.getFaceDeg obj g) == 4 do add[g] = true
		if add.isEmpty then go = false else r += add
		if r.numberSet > n0 * limit do (go = false; r = undefined)
	)
	r
)

-- 선택 면 영역을 다시 채움 → #(새 면 수, 메시지)
-- 들쭉날쭉한 영역은 파인 칸을 메운 영역도 시도하고, 모서리 후보 여러 개 중 꼬이거나 뒤집힌 칸이 없는 것을 고름.
-- 끝내 안 되면 메쉬를 건드리지 않고 알려 줌
fn ra_rebuildRegion obj fsIn flowDir =
(
	local variants = #(fsIn)
	local grown = ra_growRegion obj fsIn
	if grown != undefined and grown.numberSet != fsIn.numberSet do append variants grown
	local err = undefined
	local chosen = undefined
	RA_S.flowDir = flowDir
	try
	(
		for fv in variants do
		(
			local lpv = ra_regionLoop obj fv
			if classOf lpv == String then (if err == undefined do err = lpv)
			else if lpv.count < 4 then (if err == undefined do err = "영역이 너무 작습니다")
			else if (mod lpv.count 2) == 1 then (if err == undefined do err = "경계 버텍스 수가 홀수라 쿼드로만 다시 채울 수 없습니다 (삼각형/오각형이 섞인 영역)")
			else
			(
				local GPv = for v in lpv collect polyop.getVert obj v
				local GNv = for v in lpv collect ra_vnrm obj v
				local idxs = for k = 1 to lpv.count collect k
				-- 주변 메쉬에서 들어오는 엣지 → 그 흐름을 이어 가도록
				local ext = ra_boundaryExt obj lpv fv
				local anyExt = false
				for e in ext where e != undefined do anyExt = true
				RA_S.extDirs = if anyExt then ext else undefined
				local cands = ra_solveQuadSides GPv #() top:10
				local found = false
				for sd in cands while not found do
				(
					local plv = ra_planPatch GPv GNv idxs #() sides:sd
					if not (ra_gridTangled plv[2] plv[3]) do
					(
						found = true
						-- 주변 흐름을 잇는 정도 − 길쭉한 칸 감점 (주변 메쉬가 없으면 이을 흐름도 없으므로 만점)
						local cont = if anyExt then ra_flowContinuity GPv ext sd[1] sd[2] sd[3] else 1.0
						local qual = cont - 0.15 * ((ra_gridMaxAspect plv[2]) - 1.0)
						if chosen == undefined or qual > chosen[4] + 0.02 do chosen = #(fv, lpv, plv, qual)
					)
				)
				RA_S.extDirs = undefined
				if not found do err = "이 영역 모양으로는 꼬이지 않게 다시 채울 수 없습니다. 더 둥글거나 네모난 영역을 선택하세요 (메쉬는 그대로)"
			)
		)
	)
	catch (RA_S.flowDir = undefined; RA_S.extDirs = undefined; throw())
	RA_S.flowDir = undefined
	RA_S.extDirs = undefined
	if chosen == undefined then #(0, (if err == undefined then "다시 채울 수 없습니다" else err))
	else
	(
		local fs = chosen[1]
		local lp = chosen[2]
		local pl = chosen[3]
		local N = lp.count
		local nf0 = fs.numberSet
		local refN = [0, 0, 0]
		for f in fs do refN += polyop.getFaceNormal obj f
		local gi = pl[1]
		local grid = pl[2]
		local a = pl[4]
		local b = pl[5]
		local lpSet = lp as bitArray
		local interior = ((polyop.getVertsUsingFace obj fs) - lpSet) as array
		sort interior
		local made = 0
		local newF = #{}
		RA_S.busy = true
		undo "Retopo 재구성" on
		(
			polyop.deleteFaces obj fs delIsoVerts:false
			if interior.count > 0 do polyop.deleteVerts obj (interior as bitArray)
			-- 안쪽 버텍스를 지우면 번호가 당겨지므로 경계 버텍스 번호를 다시 계산
			local vid = for v in lp collect
			(
				local sh = 0
				for x in interior while x < v do sh += 1
				v - sh
			)
			local V = for j = 0 to b collect (for i = 0 to a collect \
				(if gi[j + 1][i + 1] > 0 then vid[gi[j + 1][i + 1]] else polyop.createVert obj grid[j + 1][i + 1]))
			local quads = #()
			for j = 1 to b do for i = 1 to a do append quads #(V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i])
			local same = 0
			local opp = 0
			for q in quads do (local r = ra_winding obj q; same += r[1]; opp += r[2])
			local flip = same > opp
			if same == 0 and opp == 0 do
			(
				local q = quads[1]
				local p1 = polyop.getVert obj q[1]
				flip = (dot (cross ((polyop.getVert obj q[2]) - p1) ((polyop.getVert obj q[4]) - p1)) refN) < 0
			)
			for q in quads do
			(
				local qq = if flip then ra_rev q else q
				local f = polyop.createPolygon obj (ra_bestQuadOrder obj qq)
				if f != undefined do (newF[f] = true; made += 1)
			)
			polyop.setVertSelection obj #{}
			polyop.setFaceSelection obj newF
		)
		RA_S.busy = false
		RA_S.lastRec = undefined
		redrawViews()
		#(made, "재구성: 면 " + nf0 as string + " → " + made as string + " (" + a as string + " x " + b as string + ")")
	)
)

-- 선택 면 영역 경계 안쪽에 루프를 하나 더(인셋) → 영역 둘레를 따라 흐름이 바뀜
-- (UI 버튼 명령에 기대지 않고 직접: 경계 점마다 안쪽 점을 만들고, 영역 면은 안쪽 점으로 다시, 둘레에 쿼드 한 줄)
fn ra_offsetRegion obj fs =
(
	if fs.isEmpty then #(0, "면을 선택하세요")
	else
	(
		local lp = ra_regionLoop obj fs
		if classOf lp == String then #(0, lp)
		else
		(
			local avg = 0.0
			local cnt = 0
			for e in (polyop.getEdgesUsingFace obj fs) do (local ev = polyop.getEdgeVerts obj e; avg += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]); cnt += 1)
			avg /= (amax cnt 1)
			local d = avg * 0.5
			-- 경계 점마다 영역 안쪽 방향 (그 점에 붙은 영역 면 중심 쪽)
			local inner = #()
			for v in lp do
			(
				local p = polyop.getVert obj v
				local dir = [0, 0, 0]
				for f in (polyop.getFacesUsingVert obj v) where fs[f] do dir += normalize ((polyop.getFaceCenter obj f) - p)
				local q = if (length dir) > 1e-9 then p + (normalize dir) * d else p
				local n = ra_vnrm obj v
				append inner (ra_project q n)
			)
			local faceData = for f in fs collect #(f, polyop.getFaceVerts obj f)
			-- 경계 엣지마다 그 엣지를 가진 영역 면에서의 순서 (u→w)
			local ringOrder = #()
			local N = lp.count
			for k = 1 to N do
			(
				local u = lp[k]
				local w = lp[ra_wrap (k + 1) N]
				local ord = #(u, w)
				for fd in faceData do
				(
					local vs = fd[2]
					local iu = findItem vs u
					if iu > 0 and vs[ra_wrap (iu + 1) vs.count] == w do ord = #(u, w)
					if iu > 0 and vs[ra_wrap (iu - 1) vs.count] == w do ord = #(w, u)
				)
				append ringOrder ord
			)
			local nf0 = polyop.getNumFaces obj
			local made = 0
			RA_S.busy = true
			undo "Retopo 오프셋" on
			(
				local iv = for p in inner collect polyop.createVert obj p
				local map = #()
				for k = 1 to N do map[lp[k]] = iv[k]
				polyop.deleteFaces obj fs delIsoVerts:false
				local newF = #{}
				for fd in faceData do
				(
					local q = for v in fd[2] collect (if map[v] != undefined then map[v] else v)
					local f = polyop.createPolygon obj q
					if f != undefined do (newF[f] = true; made += 1)
				)
				for k = 1 to N do
				(
					local o = ringOrder[k]
					local f = polyop.createPolygon obj #(o[1], o[2], map[o[2]], map[o[1]])
					if f != undefined do made += 1
				)
				polyop.setFaceSelection obj newF
			)
			RA_S.busy = false
			RA_S.lastRec = undefined
			redrawViews()
			local added = (polyop.getNumFaces obj) - nf0
			#(added, "오프셋: 경계 안쪽에 루프 추가 (새 면 " + added as string + ")")
		)
	)
)
fn ra_pointInPoly p poly =
(
	local inside = false
	local n = poly.count
	local j = n
	for i = 1 to n do
	(
		local a = poly[i]
		local b = poly[j]
		if (a.y > p.y) != (b.y > p.y) do
		(
			local dy = b.y - a.y
			if abs dy < 1e-12 do dy = 1e-12
			local x = a.x + (p.y - a.y) * (b.x - a.x) / dy
			if p.x < x do inside = not inside
		)
		j = i
	)
	inside
)

-- 주석으로 둘러싼 곳의 면 선택 (이후 촘촘하게/성기게/고르게 재구성 버튼이 이 영역에 적용)
fn ra_regionSelect obj pts =
(
	local poly = for p in pts collect ra_toScreen p
	local fsel = #{}
	if poly.count >= 3 do
	(
		local vt = try (inverse (getViewTM())) catch (matrix3 1)
		local eye = vt.row4
		local persp = try (viewport.IsPerspView()) catch true
		local vdir = normalize vt.row3
		for f = 1 to polyop.getNumFaces obj do
		(
			local c = polyop.getFaceCenter obj f
			if ra_pointInPoly (ra_toScreen c) poly do
			(
				local v = if persp then eye - c else vdir
				if obj.xray or (dot (polyop.getFaceNormal obj f) v) > 0 do fsel[f] = true
			)
		)
	)
	polyop.setFaceSelection obj fsel
	if not (GetQuietMode()) do (try (if subObjectLevel != 4 do subObjectLevel = 4) catch ())
	redrawViews()
	fsel.numberSet
)

-- ---------------------------------------------------------------------------
-- 스캔 → 합친 리토 메쉬: 여러 오브젝트 표면을 하나로 합쳐 고른 쿼드 메쉬(새 오브젝트)로
-- ---------------------------------------------------------------------------

fn ra_isOpenNode n =
(
	local m = snapshotAsMesh n
	local r = (meshop.getOpenEdges m).numberSet > 0
	free m
	r
)

-- 광선이 오브젝트 표면을 지나는 모든 z 값 (아래→위)
fn ra_columnHits n x y z0 z1 step =
(
	local hits = #()
	local p = [x, y, z0]
	local go = true
	while go and hits.count < 400 do
	(
		local h = intersectRay n (ray p [0, 0, 1])
		if h == undefined or h.pos.z > z1 then go = false
		else
		(
			append hits h.pos.z
			p = [x, y, h.pos.z + step]
		)
	)
	hits
)

-- 여러 오브젝트 표면을 스캔해 하나로 합친 고른 쿼드 메쉬 (복셀 방식: 안쪽 공간을 격자로 채우고 겉면을 쿼드로)
-- RAKeys.dll 의 빠른 엔진(RAQuad)을 못 쓸 때만 쓰는 예전 방식 (느림)
fn ra_scanMergeVoxel nodes =
(
	local src = for n in nodes where isValidNode n and superClassOf n == GeometryClass and classOf n != Targetobject and \
		not (isValidNode RA_S.retopo and n == RA_S.retopo) and not (matchPattern n.name pattern:"Retopo*") collect n
	if src.count == 0 then #(undefined, "스캔할 오브젝트를 선택하세요")
	else
	(
		local vs = amax RA_S.spacing 1e-4
		local bmin = [1e30, 1e30, 1e30]
		local bmax = [-1e30, -1e30, -1e30]
		for n in src do
		(
			bmin = [amin bmin.x n.min.x, amin bmin.y n.min.y, amin bmin.z n.min.z]
			bmax = [amax bmax.x n.max.x, amax bmax.y n.max.y, amax bmax.z n.max.z]
		)
		-- 격자가 너무 크면 칸을 키움 (약 120만 칸 이하)
		local ext = bmax - bmin
		while ((ext.x / vs + 3) * (ext.y / vs + 3) * (ext.z / vs + 3)) > 1.2e6 do vs *= 1.25
		bmin -= [vs, vs, vs] * 1.5
		bmax += [vs, vs, vs] * 1.5
		local nx = (ceil ((bmax.x - bmin.x) / vs)) as integer
		local ny = (ceil ((bmax.y - bmin.y) / vs)) as integer
		local nz = (ceil ((bmax.z - bmin.z) / vs)) as integer
		local openFlags = for n in src collect ra_isOpenNode n
		-- 광선 검사는 앞면만 맞으므로, 면을 뒤집은 복사본으로 '나가는' 표면을 찾음
		local flipped = for n in src collect
		(
			local c = copy n
			convertToMesh c
			meshop.flipNormals c #{1..c.numfaces}
			c
		)
		local solid = #{}
		solid.count = nx * ny * nz
		-- 1) 안쪽 공간 채우기: 열마다 위로 광선 → 들어가는 면/나가는 면 순서로 안/밖 판정 (여러 오브젝트는 합집합)
		try
		(
			for j = 0 to ny - 1 do for i = 0 to nx - 1 do
			(
				local x = bmin.x + (i + 0.5) * vs
				local y = bmin.y + (j + 0.5) * vs
				for oi = 1 to src.count do
				(
					local ins = ra_columnHits src[oi] x y (bmin.z - vs) (bmax.z + vs) (vs * 1e-3)
					local outs = ra_columnHits flipped[oi] x y (bmin.z - vs) (bmax.z + vs) (vs * 1e-3)
					if ins.count > 0 or outs.count > 0 do
					(
						if openFlags[oi] then
						(
							-- 열린 면(판 등): 표면이 지나는 칸 한 겹
							for z in (ins + outs) do
							(
								local k = (floor ((z - bmin.z) / vs)) as integer
								if k >= 0 and k < nz do solid[i + nx * (j + ny * k) + 1] = true
							)
						)
						else
						(
							-- 들어감(+1) / 나감(-1) 을 높이 순으로
							local ev = (for z in ins collect [z, 1, 0]) + (for z in outs collect [z, -1, 0])
							qsort ev ra_cmpHit
							local depth = 0
							local zin = 0.0
							for e in ev do
							(
								if e.y > 0 then (if depth == 0 do zin = e.x; depth += 1)
								else if depth > 0 do
								(
									depth -= 1
									if depth == 0 do
									(
										local k0 = amax 0 ((ceil ((zin - bmin.z) / vs - 0.5)) as integer)
										local k1 = amin (nz - 1) ((floor ((e.x - bmin.z) / vs - 0.5)) as integer)
										for k = k0 to k1 do solid[i + nx * (j + ny * k) + 1] = true
									)
								)
							)
						)
					)
				)
			)
		)
		catch (for c in flipped where isValidNode c do delete c; throw())
		for c in flipped where isValidNode c do delete c
		-- 2) 모서리/꼭짓점으로만 닿은 칸 메우기 (한 엣지에 면이 4개 붙는 비정상 형태 방지)
		for pass = 1 to 6 do
		(
			local add = #{}
			for k = 0 to nz - 2 do for j = 0 to ny - 2 do for i = 0 to nx - 2 do
			(
				local c = #()
				for dk = 0 to 1 do for dj = 0 to 1 do for di = 0 to 1 do append c solid[(i + di) + nx * ((j + dj) + ny * (k + dk)) + 1]
				-- c 순서: (000)(100)(010)(110)(001)(101)(011)(111)
				local bad = false
				-- 세 방향 평면마다 대각선 모양
				for pr in #(#(1, 2, 3, 4), #(5, 6, 7, 8), #(1, 2, 5, 6), #(3, 4, 7, 8), #(1, 3, 5, 7), #(2, 4, 6, 8)) do
					if (c[pr[1]] and c[pr[4]] and not c[pr[2]] and not c[pr[3]]) or (c[pr[2]] and c[pr[3]] and not c[pr[1]] and not c[pr[4]]) do bad = true
				-- 꼭짓점만 닿은 경우
				local cnt = 0
				for x in c where x do cnt += 1
				if cnt == 2 and ((c[1] and c[8]) or (c[2] and c[7]) or (c[3] and c[6]) or (c[4] and c[5])) do bad = true
				if bad do for dk = 0 to 1 do for dj = 0 to 1 do for di = 0 to 1 do add[(i + di) + nx * ((j + dj) + ny * (k + dk)) + 1] = true
			)
			local before = solid.numberSet
			solid += add
			if solid.numberSet == before do exit
		)
		-- 3) 겉면을 쿼드로
		local m = Editable_Mesh()
		convertTo m PolyMeshObject
		m.name = uniqueName "Retopo_Scan_"
		(LayerManager.getLayer 0).addNode m
		local lx = nx + 1
		local ly = ny + 1
		local vmap = #()
		vmap[lx * ly * (nz + 1)] = 0
		fn lv m vmap bmin vs lx ly i j k =
		(
			local id = i + lx * (j + ly * k) + 1
			local v = vmap[id]
			if v == undefined or v == 0 do
			(
				v = polyop.createVert m (bmin + [i * vs, j * vs, k * vs])
				vmap[id] = v
			)
			v
		)
		local isS = fn isS solid nx ny nz i j k = (i >= 0 and j >= 0 and k >= 0 and i < nx and j < ny and k < nz and solid[i + nx * (j + ny * k) + 1])
		local made = 0
		for k = 0 to nz - 1 do for j = 0 to ny - 1 do for i = 0 to nx - 1 where solid[i + nx * (j + ny * k) + 1] do
		(
			local fcs = #()
			if not (isS solid nx ny nz (i - 1) j k) do append fcs #([i, j, k], [i, j, k + 1], [i, j + 1, k + 1], [i, j + 1, k])
			if not (isS solid nx ny nz (i + 1) j k) do append fcs #([i + 1, j, k], [i + 1, j + 1, k], [i + 1, j + 1, k + 1], [i + 1, j, k + 1])
			if not (isS solid nx ny nz i (j - 1) k) do append fcs #([i, j, k], [i + 1, j, k], [i + 1, j, k + 1], [i, j, k + 1])
			if not (isS solid nx ny nz i (j + 1) k) do append fcs #([i, j + 1, k], [i, j + 1, k + 1], [i + 1, j + 1, k + 1], [i + 1, j + 1, k])
			if not (isS solid nx ny nz i j (k - 1)) do append fcs #([i, j, k], [i, j + 1, k], [i + 1, j + 1, k], [i + 1, j, k])
			if not (isS solid nx ny nz i j (k + 1)) do append fcs #([i, j, k + 1], [i + 1, j, k + 1], [i + 1, j + 1, k + 1], [i, j + 1, k + 1])
			for fc in fcs do
			(
				local q = for c in fc collect lv m vmap bmin vs lx ly (c.x as integer) (c.y as integer) (c.z as integer)
				if (polyop.createPolygon m q) != undefined do made += 1
			)
		)
		-- 4) 원래 표면에 붙이고 고르게 (타겟을 잠시 스캔 대상으로)
		local keepT = RA_S.targets
		local keepT1 = RA_S.target
		RA_S.targets = src
		RA_S.target = src[1]
		try
		(
			for it = 1 to 3 do
			(
				local nv = polyop.getNumVerts m
				local np = #()
				for v = 1 to nv do
				(
					local nb = (polyop.getEdgesUsingVert m v) as array
					local s = [0, 0, 0]
					for e in nb do s += polyop.getVert m (ra_other m e v)
					append np (if nb.count > 0 then s / nb.count else polyop.getVert m v)
				)
				for v = 1 to nv do
				(
					local n = ra_vertNormal m v
					polyop.setVert m #(v) (if n != undefined then ra_project np[v] n else np[v])
				)
			)
			-- 열린 면(판)에서 생긴 뒷면 겹 지우기: 면 방향이 가까운 표면 방향과 반대인 면
			local anyOpen = false
			for x in openFlags where x do anyOpen = true
			if anyOpen do
			(
				local back = #{}
				local d = vs * 4.0
				for f = 1 to polyop.getNumFaces m do
				(
					local c = polyop.getFaceCenter m f
					local fn0 = polyop.getFaceNormal m f
					-- 가장 가까운 표면의 '원래' 방향 (겹치는 곳은 열린 면(판) 우선)
					local best = undefined
					for oi = 1 to src.count do
					(
						for r in #(ray (c + fn0 * d) (-fn0), ray (c - fn0 * d) fn0) do
						(
							local h = intersectRay src[oi] r
							if h != undefined do
							(
								local dd = distance h.pos c
								if best == undefined or dd < best[1] - vs * 0.05 or (abs (dd - best[1]) <= vs * 0.05 and openFlags[oi] and not best[3]) do
									best = #(dd, normalize h.dir, openFlags[oi])
							)
						)
					)
					if best != undefined and (dot best[2] fn0) < 0 do back[f] = true
				)
				if not back.isEmpty and back.numberSet < polyop.getNumFaces m do polyop.deleteFaces m back delIsoVerts:true
			)
		)
		catch (format "[RetopoAnnotate] scan relax %\n" (getCurrentException()))
		RA_S.targets = keepT
		RA_S.target = keepT1
		m.wirecolor = color 40 160 255
		m.xray = true
		m.backfacecull = false
		#(m, "스캔 합치기: 오브젝트 " + src.count as string + "개 → 쿼드 " + (polyop.getNumFaces m) as string + "개 (칸 크기 " + vs as string + ")")
	)
)

-- 빠른 엔진: RAKeys.dll 안의 RAQuad (복셀로 합친 껍질 → 방향장 쿼드 리메쉬 → 원래 표면·모서리에 맞춤)
global RA_QuadAsm
fn ra_quadEngine =
(
	if RA_QuadAsm == undefined and RA_ScriptDir != undefined and doesFileExist (RA_ScriptDir + "RAKeys.dll") do
		RA_QuadAsm = try (dotNet.loadAssembly (RA_ScriptDir + "RAKeys.dll")) catch undefined
	if RA_QuadAsm == undefined then undefined
	else try (RA_QuadAsm.CreateInstance "RAQuad") catch undefined
)

-- .NET 배열 → MAXScript 배열 (이미 변환돼 오면 그대로)
fn ra_netArr a =
(
	if classOf a == Array then a
	else
	(
		local n = a.Length
		local r = #()
		if n > 0 do r[n] = undefined
		for i = 0 to n - 1 do r[i + 1] = a.GetValue i
		r
	)
)

fn ra_scanSource nodes =
(
	for n in nodes where isValidNode n and superClassOf n == GeometryClass and classOf n != Targetobject and \
		not (isValidNode RA_S.retopo and n == RA_S.retopo) and not (matchPattern n.name pattern:"Retopo*") collect n
)

-- 방금 스캔한 결과: 엔진(입력 메쉬를 들고 있음)과 만든 노드. 면 수를 바꿔 다시 만들 때 오브젝트를 다시 읽지 않음
global RA_ScanQ
global RA_ScanNode
global RA_ScanFaces = 0

-- 엔진 결과로 Editable Poly 노드 만들기
fn ra_scanBuildNode q =
(
	local vs = ra_netArr (q.GetVerts())
	local ts = ra_netArr (q.GetTris())
	local hid = ra_netArr (q.GetTriHidden())
	local pts = for i = 1 to vs.count by 3 collect [vs[i], vs[i + 1], vs[i + 2]]
	local fcs = for i = 1 to ts.count by 3 collect [ts[i], ts[i + 1], ts[i + 2]]
	local m = mesh vertices:pts faces:fcs
	-- 쿼드(n각형)를 이루는 삼각형 사이 엣지는 숨겨 Editable Poly 로 바꿀 때 하나의 면이 되게
	for f = 1 to fcs.count do
	(
		local b = hid[f]
		if b != 0 do
		(
			if (bit.and b 1) != 0 do setEdgeVis m f 1 false
			if (bit.and b 2) != 0 do setEdgeVis m f 2 false
			if (bit.and b 4) != 0 do setEdgeVis m f 3 false
		)
	)
	update m
	convertTo m PolyMeshObject
	m.wirecolor = color 40 160 255
	m.xray = true
	m.backfacecull = false
	m
)

fn ra_scanFlags =
(
	local flags = 0
	if RA_S.scanPureQuad do flags += 1
	if RA_S.scanSharp do flags += 2
	if not RA_S.scanDelBack do flags += 4
	flags
)

fn ra_scanMerge nodes =
(
	local src = ra_scanSource nodes
	local q = if src.count > 0 then ra_quadEngine() else undefined
	if src.count == 0 then #(undefined, "스캔할 오브젝트를 선택하세요")
	else if q == undefined then
	(
		format "[RetopoAnnotate] RAKeys.dll 의 RAQuad 를 불러오지 못해 예전(느린) 스캔을 씁니다\n"
		ra_scanMergeVoxel nodes
	)
	else
	(
		local t0 = timeStamp()
		local nTri = 0
		local sgl = dotNetClass "System.Single[]"
		local i32 = dotNetClass "System.Int32[]"
		for n in src do
		(
			local m = try (snapshotAsMesh n) catch undefined
			if m != undefined do
			(
				local nv = m.numverts
				local nf = m.numfaces
				if nv > 0 and nf > 0 do
				(
					local xyz = #()
					xyz[nv * 3] = 0.0
					for i = 1 to nv do
					(
						local p = getVert m i
						local b = i * 3
						xyz[b - 2] = p.x; xyz[b - 1] = p.y; xyz[b] = p.z
					)
					local tri = #()
					tri[nf * 3] = 0
					for i = 1 to nf do
					(
						local f = getFace m i
						local b = i * 3
						tri[b - 2] = (f.x as integer) - 1; tri[b - 1] = (f.y as integer) - 1; tri[b] = (f.z as integer) - 1
					)
					q.AddMesh (dotNet.ValueToDotNetObject xyz sgl) (dotNet.ValueToDotNetObject tri i32)
					nTri += nf
				)
				free m
			)
		)
		local t1 = timeStamp()
		q.TargetFaces = RA_S.scanTarget
		local res = q.Run RA_S.spacing RA_S.scanAngle (ra_scanFlags()) 0
		format "[RetopoAnnotate] 스캔 엔진 로그\n%" (q.GetLog())
		if res != "OK" then #(undefined, "스캔 실패: " + res)
		else
		(
			local t2 = timeStamp()
			local m = ra_scanBuildNode q
			m.name = uniqueName "Retopo_Scan_"
			(LayerManager.getLayer 0).addNode m
			RA_ScanQ = q
			RA_ScanNode = m
			RA_S.scanGuides = #()
			RA_ScanFaces = polyop.getNumFaces m
			local tEnd = timeStamp()
			#(m, "스캔 합치기: 오브젝트 " + src.count as string + "개 (삼각형 " + nTri as string + ") → 면 " + RA_ScanFaces as string + \
				"  [읽기 " + ((t1 - t0) / 1000.0) as string + "s · 계산 " + ((t2 - t1) / 1000.0) as string + "s · 생성 " + ((tEnd - t2) / 1000.0) as string + "s]" + \
				"  — +/−, Alt+휠, '스캔 목표 면 수' 로 면 수 조절")
		)
	)
)

-- 방금 스캔한 메쉬를 면 수만 바꿔 다시 만들 수 있는지 (그 뒤 메쉬를 고치지 않았을 때)
fn ra_canAdjustScan =
(
	RA_ScanQ != undefined and isValidNode RA_ScanNode and RA_ScanNode == RA_S.retopo and (ra_isPoly RA_ScanNode) and \
		(polyop.getNumFaces RA_ScanNode) == RA_ScanFaces
)

-- 스캔 결과를 목표 면 수 faces 로 다시 만들어 같은 자리에 바꿔 넣음
fn ra_scanRebuild faces =
(
	if not (ra_canAdjustScan()) then false
	else
	(
		local q = RA_ScanQ
		local old = RA_ScanNode
		q.TargetFaces = if faces > 0 then (amax 8 faces) else 0
		local res = q.Run RA_S.spacing RA_S.scanAngle (ra_scanFlags()) 0
		if res != "OK" then (format "[RetopoAnnotate] %\n%" res (q.GetLog()); displayTempPrompt ("스캔 다시 만들기 실패: " + res) 4000; false)
		else
		(
			local m
			undo "Retopo 스캔 면 수" on
			(
				m = ra_scanBuildNode q
				m.name = old.name
				m.wirecolor = old.wirecolor
				m.xray = old.xray
				try (old.layer.addNode m) catch ()
				local wasSel = old.isSelected
				delete old
				if wasSel do selectMore m
			)
			RA_ScanNode = m
			RA_S.retopo = m
			RA_ScanFaces = polyop.getNumFaces m
			RA_S.scanTarget = faces
			ra_syncUI()
			if not (GetQuietMode()) do displayTempPrompt ("스캔 결과 면 " + RA_ScanFaces as string + \
				(if faces > 0 then (" (목표 " + faces as string + ")") else "") + \
				(if q.GuideCount > 0 then (" · 가이드 선 " + q.GuideCount as string + "개") else "")) 3000
			redrawViews()
			true
		)
	)
)

-- 그은 가이드 선을 엔진에 넣고 스캔 결과를 다시 만듦 (엣지 루프가 가이드 선을 따라감)
fn ra_scanApplyGuides =
(
	if not (ra_canAdjustScan()) then
	(
		messageBox "가이드로 다시 만들 스캔 결과가 없습니다.\n[스캔 → 합친 메쉬] 로 만든 메쉬(그 뒤 고치지 않은 것)에 가이드 선을 그은 뒤 누르세요." title:"Retopo"
		false
	)
	else
	(
		local q = RA_ScanQ
		local sgl = dotNetClass "System.Single[]"
		q.ClearGuides()
		for g in RA_S.scanGuides where g[1].count >= 2 do
		(
			local xyz = #()
			local nrm = #()
			for i = 1 to g[1].count do
			(
				local p = g[1][i]
				local n = if g[2] != undefined and g[2][i] != undefined then g[2][i] else [0, 0, 0]
				join xyz #(p.x, p.y, p.z)
				join nrm #(n.x, n.y, n.z)
			)
			q.AddGuide (dotNet.ValueToDotNetObject xyz sgl) (dotNet.ValueToDotNetObject nrm sgl)
		)
		ra_scanRebuild RA_S.scanTarget
	)
)

fn ra_scanClearGuides =
(
	RA_S.scanGuides = #()
	-- 엔진에도 가이드가 있었으면 가이드 없이 다시 만듦
	if RA_ScanQ != undefined and RA_ScanQ.GuideCount > 0 do
	(
		RA_ScanQ.ClearGuides()
		ra_scanRebuild RA_S.scanTarget
	)
	redrawViews()
)

-- 가이드 선 그리기 시작 (우클릭으로 끝남)
fn ra_drawGuides =
(
	if not (isValidNode RA_ScanNode) or RA_ScanQ == undefined then
		messageBox "먼저 [스캔 → 합친 메쉬] 로 메쉬를 만드세요. 가이드 선은 그 메쉬 위에 긋습니다." title:"Retopo"
	else if not RA_S.tracking do
	(
		RA_S.guideMode = true
		RA_S.retopo = RA_ScanNode
		displayTempPrompt "가이드 선: 원하는 엣지 흐름을 따라 그으세요 (우클릭 = 끝, Ctrl+Z = 마지막 선 지우기) → [가이드로 다시 만들기]" 8000
		try (ra_startDraw()) catch (format "[RetopoAnnotate] %\n" (getCurrentException()))
		RA_S.guideMode = false
		redrawViews()
	)
)

-- +/− , Alt+휠: 한 칸에 면 수 약 1.3배 / ÷1.3
fn ra_scanAdjust step =
(
	local cur = if RA_S.scanTarget > 0 then RA_S.scanTarget else RA_ScanFaces
	ra_scanRebuild ((ra_round (cur * (1.3 ^ step))) as integer)
)

-- ---------------------------------------------------------------------------
-- 만든 메쉬 밀도 조절: 선택 면(없으면 전체)을 촘촘하게(쿼드 1→4) / 성기게(엣지 루프 하나 건너 하나 제거)
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- 떨어진 메쉬 연결: 따로 떨어진 두 조각의 마주 보는 경계를 찾아 쿼드로 이어 붙임
-- ---------------------------------------------------------------------------

-- 가장 가까운 점까지 거리와 그 점 번호
fn ra_nearestIn p pts =
(
	local bd = 1e30
	local bi = 0
	for i = 1 to pts.count do (local d = distance p pts[i]; if d < bd do (bd = d; bi = i))
	#(bd, bi)
)

-- 마주 보는 경계 버텍스를 골라 버텍스 선택 → undefined 또는 오류 문자열
fn ra_connectSelect obj =
(
	local adj = ra_openAdj obj
	local nv = adj.count
	-- 경계 묶음
	local comp = for i = 1 to nv collect 0
	local cid = 0
	for v = 1 to nv where adj[v].count > 0 and comp[v] == 0 do
	(
		cid += 1
		local stack = #(v)
		while stack.count > 0 do
		(
			local x = stack[stack.count]
			deleteItem stack stack.count
			if comp[x] == 0 do (comp[x] = cid; for y in adj[x] where comp[y] == 0 do append stack y)
		)
	)
	if cid < 2 then "연결할 떨어진 조각이 없습니다 (열린 경계가 있는 조각이 2개 이상 필요)"
	else
	(
		-- 조각(엘리먼트) 번호
		local isl = for i = 1 to nv collect 0
		local k = 0
		local doneF = #{}
		for f = 1 to polyop.getNumFaces obj where not doneF[f] do
		(
			k += 1
			local el = polyop.getElementsUsingFace obj #{f}
			doneF += el
			for v in (polyop.getVertsUsingFace obj el) do isl[v] = k
		)
		local byComp = for c = 1 to cid collect #()
		for v = 1 to nv where comp[v] > 0 do append byComp[comp[v]] v
		local posC = for c = 1 to cid collect (for v in byComp[c] collect polyop.getVert obj v)
		local sel = polyop.getVertSelection obj
		if (try (subObjectLevel == 2 or subObjectLevel == 3) catch false) do sel += polyop.getVertsUsingEdge obj (polyop.getEdgeSelection obj)
		local selC = #()
		for v in sel where v <= nv and comp[v] > 0 and findItem selC comp[v] == 0 do append selC comp[v]
		local selN = for c in selC collect (local n = 0; for v in byComp[c] where sel[v] do n += 1; n)
		if selC.count == 2 and selN[1] >= 2 and selN[2] >= 2 then undefined  -- 직접 고른 경계 그대로
		else
		(
			local pairs = #()
			if selC.count == 2 then pairs = #(#(selC[1], selC[2]))
			else if selC.count == 1 then (for c = 1 to cid where c != selC[1] do append pairs #(selC[1], c))
			else (for a = 1 to cid do for b = a + 1 to cid do append pairs #(a, b))
			-- 가장 가까운 두 경계 (다른 조각끼리 우선)
			local best = undefined
			for pr in pairs do
			(
				local diff = isl[byComp[pr[1]][1]] != isl[byComp[pr[2]][1]]
				local P2 = posC[pr[2]]
				for i = 1 to posC[pr[1]].count do
				(
					local r = ra_nearestIn posC[pr[1]][i] P2
					local key = r[1] + (if diff then 0.0 else 1e20)
					if best == undefined or key < best[1] do best = #(key, pr[1], pr[2], byComp[pr[1]][i], byComp[pr[2]][r[2]], r[1])
				)
			)
			local ca = best[2]
			local cb = best[3]
			local dmin = best[6]
			local avg = 0.0
			local ne = 0
			for e in (polyop.getOpenEdges obj) do (local ev = polyop.getEdgeVerts obj e; avg += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]); ne += 1)
			avg = if ne > 0 then avg / ne else RA_S.spacing
			local lim = dmin * 2.0 + avg
			-- 상대 조각을 마주 보는 경계만 (모서리를 돌아 옆면으로 가면 멈춤)
			fn facing adj obj start otherPts lim =
			(
				local cyc = ra_openCycle adj start
				if cyc == undefined then (local nb = adj[start]; #(start, nb[1]))
				else
				(
					local n = cyc.count
					local i0 = findItem cyc start
					local chain = #(start)
					for stp in #(1, -1) do
					(
						local kk = i0
						local go = true
						for s = 1 to n - 1 while go do
						(
							kk = ra_wrap (kk + stp) n
							local v = cyc[kk]
							local p = polyop.getVert obj v
							local r = ra_nearestIn p otherPts
							local t = (polyop.getVert obj cyc[ra_wrap (kk + 1) n]) - (polyop.getVert obj cyc[ra_wrap (kk - 1) n])
							local w = otherPts[r[2]] - p
							local ok = findItem chain v == 0 and r[1] <= lim
							if ok and (length t) > 1e-9 and (length w) > 1e-9 do ok = abs (dot (normalize t) (normalize w)) < 0.8
							if not ok then go = false
							else if stp == 1 then append chain v else insertItem v chain 1
						)
					)
					if chain.count < 2 do append chain cyc[ra_wrap (i0 + 1) n]
					if chain.count >= n then undefined else chain
				)
			)
			local A = facing adj obj best[4] posC[cb] lim
			local B = facing adj obj best[5] posC[ca] lim
			if A == undefined or B == undefined then "마주 보는 경계를 찾지 못했습니다. 두 조각의 마주 보는 경계 버텍스를 직접 선택하세요"
			else
			(
				polyop.setEdgeSelection obj #{}
				polyop.setFaceSelection obj #{}
				polyop.setVertSelection obj ((A + B) as bitArray)
				undefined
			)
		)
	)
)

fn ra_connectPieces obj =
(
	local err = ra_connectSelect obj
	if err != undefined then #(0, err)
	else
	(
		try (if subObjectLevel == 2 or subObjectLevel == 3 do subObjectLevel = 1) catch ()
		local r = ra_fillGap obj
		#(r[1], substituteString r[2] "빈 곳 채우기" "조각 연결")
	)
)

-- 지금 보이는 선택(버텍스/엣지/면 모드)에 해당하는 면. 선택이 없거나 오브젝트 모드면 전체
fn ra_regionFaces obj =
(
	local lvl = try (if subObjectLevel == undefined then 0 else subObjectLevel) catch 0
	local fs = case lvl of
	(
		1: polyop.getFacesUsingVert obj (polyop.getVertSelection obj)
		2: polyop.getFacesUsingEdge obj (polyop.getEdgeSelection obj)
		3: polyop.getFacesUsingEdge obj (polyop.getEdgeSelection obj)
		4: polyop.getFaceSelection obj
		5: polyop.getFaceSelection obj
		default: #{}
	)
	-- 모드를 알 수 없으면(오브젝트 모드 등) 면 선택 → 버텍스 선택 순서로
	if fs.isEmpty and (lvl < 1 or lvl > 5) do
	(
		fs = polyop.getFaceSelection obj
		if fs.isEmpty do fs = polyop.getFacesUsingVert obj (polyop.getVertSelection obj)
	)
	if fs.isEmpty do fs = #{1..(polyop.getNumFaces obj)}
	fs
)

-- 쿼드의 엣지를 둘레 순서대로 (es[i] 맞은편 = es[i+2])
fn ra_quadEdges obj f =
(
	local vs = polyop.getFaceVerts obj f
	for i = 1 to 4 collect ra_edgeBetween obj vs[i] vs[ra_wrap (i + 1) 4]
)

-- 촘촘하게: 나눌 엣지. 영역 면의 엣지 + 둘레에서 바깥으로 이어지는 엣지 링
-- (영역 옆 면이 한 변만 나뉘면 5각형이 되므로 맞은편 변도 나눠 메쉬 끝/영역까지 이어 감)
fn ra_densifyEdges obj fs =
(
	local split = polyop.getEdgesUsingFace obj fs
	local queue = ((polyop.getFacesUsingEdge obj split) - fs) as array
	local inQ = queue as bitArray
	local guard = 0
	while queue.count > 0 and guard < 500000 do
	(
		guard += 1
		local f = queue[queue.count]
		deleteItem queue queue.count
		inQ[f] = false
		if (polyop.getFaceDeg obj f) == 4 do
		(
			local es = ra_quadEdges obj f
			if findItem es undefined == 0 do
			(
				local fl = for x in es collect split[x]
				local k = 0
				for b in fl where b do k += 1
				if not (k == 0 or k == 4 or (k == 2 and fl[1] == fl[3])) do
				(
					local add = for i = 1 to 4 where fl[i] and not fl[ra_wrap (i + 2) 4] collect es[ra_wrap (i + 2) 4]
					for x in add do split[x] = true
					local fl2 = for x in es collect split[x]
					local k2 = 0
					for b in fl2 where b do k2 += 1
					if k2 == 3 do for i = 1 to 4 where not fl2[i] do (split[es[i]] = true; append add es[i])
					for x in add do for nf in (polyop.getEdgeFaces obj x) where not inQ[nf] do (append queue nf; inQ[nf] = true)
					if not inQ[f] do (append queue f; inQ[f] = true)
				)
			)
		)
	)
	split
)

fn ra_densify obj =
(
	if not ra_isPoly obj or (polyop.getNumFaces obj) == 0 then 0
	else
	(
		local fs = ra_regionFaces obj
		local whole = fs.numberSet == (polyop.getNumFaces obj)
		local nv0 = polyop.getNumVerts obj
		RA_S.busy = true
		undo "Retopo 촘촘하게" on
		(
			local split = ra_densifyEdges obj fs
			local affected = polyop.getFacesUsingEdge obj split
			for x in split do polyop.divideEdge obj x 0.5
			local quads = #()
			local fromRegion = #()
			local gone = #{}
			for f in affected do
			(
				local R = polyop.getFaceVerts obj f
				local n = R.count
				local mids = for i = 1 to n where R[i] > nv0 collect i
				if mids.count == 4 and n == 8 then
				(
					-- 네 변이 모두 나뉜 쿼드 → 가운데 점 + 쿼드 4개
					local c = [0, 0, 0]
					for v in R do c += polyop.getVert obj v
					local cv = polyop.createVert obj (c / n)
					for i = 1 to n where R[i] <= nv0 do (append quads #(R[ra_wrap (i - 1) n], R[i], R[ra_wrap (i + 1) n], cv); append fromRegion fs[f])
					gone[f] = true
				)
				else if mids.count == 2 and n == 6 and (mids[2] - mids[1]) == 3 do
				(
					-- 마주 보는 두 변만 나뉜 쿼드 → 쿼드 2개
					local p = mids[1]
					local q = mids[2]
					append quads (for k = p to q collect R[k])
					append quads (for k = q to p + n collect R[ra_wrap k n])
					append fromRegion fs[f]
					append fromRegion fs[f]
					gone[f] = true
				)
			)
			polyop.deleteFaces obj gone delIsoVerts:false
			local sel = #{}
			for i = 1 to quads.count do
			(
				local nf = polyop.createPolygon obj quads[i]
				if nf != undefined and fromRegion[i] do sel[nf] = true
			)
			for v = nv0 + 1 to polyop.getNumVerts obj do
			(
				local nn = ra_vertNormal obj v
				if nn != undefined do polyop.setVert obj #(v) (ra_project (polyop.getVert obj v) nn)
			)
			polyop.setFaceSelection obj (if whole then #{} else sel)
			polyop.setVertSelection obj #{}
			polyop.setEdgeSelection obj #{}
		)
		RA_S.busy = false
		RA_S.lastRec = undefined
		redrawViews()
		(polyop.getNumVerts obj) - nv0
	)
)

-- 쿼드에서 엣지 e 의 맞은편 엣지
fn ra_oppositeEdge obj f e =
(
	local r = undefined
	if (polyop.getFaceDeg obj f) == 4 do
	(
		local ev = polyop.getEdgeVerts obj e
		for x in (polyop.getEdgesUsingFace obj #{f}) where x != e while r == undefined do
		(
			local xv = polyop.getEdgeVerts obj x
			if findItem ev xv[1] == 0 and findItem ev xv[2] == 0 do r = x
		)
	)
	r
)

-- 엣지 링: e0 에서 쿼드를 건너 맞은편 엣지를 따라 양쪽으로 (영역 fs 안에서만)
fn ra_edgeRing obj e0 fs =
(
	local ring = #(e0)
	local seenF = #{}
	for dirI = 1 to 2 do
	(
		local cur = e0
		local go = true
		local side = #()
		while go do
		(
			local nf = for f in (polyop.getEdgeFaces obj cur) where fs[f] and not seenF[f] collect f
			if nf.count == 0 then go = false
			else
			(
				local f = nf[1]
				seenF[f] = true
				local o = ra_oppositeEdge obj f cur
				if o == undefined or findItem ring o > 0 or findItem side o > 0 then go = false
				else (append side o; cur = o)
			)
		)
		if dirI == 1 then ring = (ra_rev side) + ring else ring = ring + side
	)
	ring
)

-- 엣지 루프: 버텍스 4개짜리(원자가 4) 점을 곧게 통과하며 양쪽으로
-- → #(엣지 목록, 완전한가) 완전 = 양 끝이 열린 경계에서 끝나거나 한 바퀴 닫힘 (중간 극점에서 끊기면 n각형이 생김)
fn ra_edgeLoop obj e0 =
(
	local loop = #(e0)
	local complete = true
	local ev0 = polyop.getEdgeVerts obj e0
	for k = 1 to 2 do
	(
		local cur = e0
		local v = ev0[k]
		local go = true
		while go do
		(
			local es = (polyop.getEdgesUsingVert obj v) as array
			if es.count != 4 then
			(
				go = false
				local onBorder = false
				for x in es where (polyop.getEdgeFaces obj x).count < 2 do onBorder = true
				if not onBorder do complete = false
			)
			else
			(
				local curF = polyop.getEdgeFaces obj cur
				local nxt = undefined
				for x in es where x != cur and nxt == undefined do
				(
					local xf = polyop.getEdgeFaces obj x
					local share = false
					for f in xf where findItem curF f > 0 do share = true
					if not share do nxt = x
				)
				if nxt == undefined then (go = false; complete = false)
				else if findItem loop nxt > 0 then go = false
				else
				(
					append loop nxt
					cur = nxt
					local nv = polyop.getEdgeVerts obj nxt
					v = if nv[1] == v then nv[2] else nv[1]
				)
			)
		)
	)
	#(loop, complete)
)

-- 루프가 꺾이는 곳(양쪽 면이 30도 넘게 꺾임) 위에 있으면 true → 지우면 모서리에서 면이 뜸
fn ra_isCreaseLoop obj lp =
(
	local r = false
	for e in lp while not r do
	(
		local fs = polyop.getEdgeFaces obj e
		if fs.count == 2 and (ra_angle (polyop.getFaceNormal obj fs[1]) (polyop.getFaceNormal obj fs[2])) > 30 do r = true
	)
	r
)

-- 링을 따라 하나 건너 하나 루프 제거 (경계 루프는 남김)
fn ra_removeAlternateLoops obj seedE fs =
(
	local ring = ra_edgeRing obj seedE fs
	local rem = #{}
	local ne = polyop.getNumEdges obj
	for k = 2 to ring.count - 1 by 2 do
	(
		local lr = ra_edgeLoop obj ring[k]
		local lp = lr[1]
		local ok = lr[2] and not (ra_isCreaseLoop obj lp)
		for e in lp where (polyop.getEdgeFaces obj e).count < 2 do ok = false
		-- 루프 전체를 지움 (영역 안 부분만 지우면 영역 둘레에 5각형이 생김)
		if ok do for e in lp do for f in (polyop.getEdgeFaces obj e) where (polyop.getFaceDeg obj f) != 4 do ok = false
		if ok do
		(
			local lb = lp as bitArray
			if not (lb * rem).isEmpty do ok = false
			if ok do rem += lb
		)
	)
	if not rem.isEmpty do
	(
		local vs = polyop.getVertsUsingEdge obj rem
		for v in vs do append RA_S.remCand (polyop.getVert obj v)
		polyop.setEdgeSelection obj rem
		obj.EditablePoly.Remove selLevel:#Edge
		-- 루프가 빠지고 엣지 2개만 남은 버텍스(직선 가운데 점) 정리
		local two = for v in vs where v <= (polyop.getNumVerts obj) and ((polyop.getEdgesUsingVert obj v).numberSet == 2) collect v
		if two.count > 0 do
		(
			polyop.setVertSelection obj (two as bitArray)
			obj.EditablePoly.Remove selLevel:#Vertex
		)
	)
	rem.numberSet
)

-- 엣지 2개만 남은 버텍스 정리 (면 가운데 / 곧은 경계 위). 진짜 쿼드 모서리(꺾인 경계 끝)는 남김
fn ra_cleanTwoValent obj cand =
(
	local total = 0
	for pass = 1 to 3 do
	(
		local two = #()
		for v = 1 to polyop.getNumVerts obj do
		(
			local es = (polyop.getEdgesUsingVert obj v) as array
			local near = false
			if es.count == 2 do
			(
				local pv = polyop.getVert obj v
				for c in cand while not near do if (distance c pv) < 1e-4 do near = true
			)
			if es.count == 2 and near do
			(
				local nf = (polyop.getFacesUsingVert obj v).numberSet
				local p = polyop.getVert obj v
				local a = (polyop.getVert obj (ra_other obj es[1] v)) - p
				local b = (polyop.getVert obj (ra_other obj es[2] v)) - p
				if nf == 2 or (ra_angle a b) > 150 do append two v
			)
		)
		if two.count > 0 do
		(
			polyop.setVertSelection obj (two as bitArray)
			obj.EditablePoly.Remove selLevel:#Vertex
			total += two.count
		)
		if two.count == 0 do exit
	)
	total
)

fn ra_sparsify obj =
(
	if not ra_isPoly obj or (polyop.getNumFaces obj) == 0 then 0
	else
	(
		local fs = ra_regionFaces obj
		local nf0 = polyop.getNumFaces obj
		-- 영역 가운데 쿼드에서 시작
		local c = [0, 0, 0]
		for f in fs do c += polyop.getFaceCenter obj f
		c /= fs.numberSet
		local seedF = 0
		local bd = 1e30
		for f in fs where (polyop.getFaceDeg obj f) == 4 do (local d = distance (polyop.getFaceCenter obj f) c; if d < bd do (bd = d; seedF = f))
		local removed = 0
		if seedF > 0 do
		(
			local es = (polyop.getEdgesUsingFace obj #{seedF}) as array
			local e1 = es[1]
			local e2 = undefined
			local ev1 = polyop.getEdgeVerts obj e1
			for x in es where e2 == undefined and x != e1 do (local xv = polyop.getEdgeVerts obj x; if findItem ev1 xv[1] > 0 or findItem ev1 xv[2] > 0 do e2 = x)
			local e2v = polyop.getEdgeVerts obj e2
			local m2 = ((polyop.getVert obj e2v[1]) + (polyop.getVert obj e2v[2])) * 0.5
			local dir1 = normalize ((polyop.getVert obj ev1[2]) - (polyop.getVert obj ev1[1]))
			local faceCenters = for f in fs collect polyop.getFaceCenter obj f
			local avgE = 0.0
			local cntE = 0
			for e in (polyop.getEdgesUsingFace obj fs) do (local ev = polyop.getEdgeVerts obj e; avgE += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]); cntE += 1)
			avgE = if cntE > 0 then avgE / cntE else RA_S.spacing
			RA_S.busy = true
			undo "Retopo 성기게" on
			(
				removed += ra_removeAlternateLoops obj e1 fs
				-- 첫 방향을 지우면 번호가 바뀌므로 위치로 두 번째 방향 시작 엣지를 다시 찾음
				local nf = polyop.getNumFaces obj
				local fs2 = #{}
				for f = 1 to nf do
				(
					local cc = polyop.getFaceCenter obj f
					local near = false
					for q in faceCenters while not near do if distance q cc < avgE * 1.5 do near = true
					if near do fs2[f] = true
				)
				-- 두 번째 방향: 첫 방향과 직각인 엣지 중 원래 e2 자리를 지나는 것
				local seed2 = undefined
				local bd2 = 1e30
				for e = 1 to polyop.getNumEdges obj do
				(
					local ev = polyop.getEdgeVerts obj e
					if ev != undefined do
					(
						local a = polyop.getVert obj ev[1]
						local b = polyop.getVert obj ev[2]
						if (distance a b) > 1e-9 and abs (dot (normalize (b - a)) dir1) < 0.5 do
						(
							local t = amax 0.0 (amin 1.0 ((dot (m2 - a) (b - a)) / ((length (b - a)) ^ 2)))
							local d = distance m2 (a + (b - a) * t)
							if d < bd2 do (bd2 = d; seed2 = e)
						)
					)
				)
				if seed2 != undefined do removed += ra_removeAlternateLoops obj seed2 fs2
				ra_cleanTwoValent obj RA_S.remCand
				RA_S.remCand = #()
				polyop.setEdgeSelection obj #{}
				polyop.setVertSelection obj #{}
				-- 원래 선택 영역이었던 면만 다시 선택 (전체였으면 선택 없음). 번호가 또 바뀌었으므로 위치로 찾음
				local fs3 = #{}
				if fs.numberSet != nf0 do for f = 1 to polyop.getNumFaces obj do
				(
					local cc = polyop.getFaceCenter obj f
					local near = false
					for q in faceCenters while not near do if distance q cc < avgE * 1.5 do near = true
					if near do fs3[f] = true
				)
				polyop.setFaceSelection obj fs3
			)
			RA_S.busy = false
		)
		RA_S.lastRec = undefined
		redrawViews()
		removed
	)
)

-- ---------------------------------------------------------------------------
-- 컨투어: 원통형(팔/다리 등)을 밖→안→밖으로 가로지르는 선 → 둘레 링
-- ---------------------------------------------------------------------------

fn ra_isContourFlags flags =
(
	local n = flags.count
	if n < 6 then false
	else
	(
		local k = amax 1 (n / 10)
		local ok = true
		for i = 1 to k do if flags[i] or flags[n - i + 1] do ok = false
		local cnt = 0
		for f in flags where f do cnt += 1
		ok and cnt >= n * 0.25
	)
)

fn ra_contourRing onPts view =
(
	if onPts.count < 2 then undefined
	else
	(
		local u = onPts[onPts.count] - onPts[1]
		u = u - view * (dot u view)
		if length u < 1e-9 then undefined
		else
		(
			u = normalize u
			local v = normalize (view - u * (dot view u))
			local width = distance onPts[1] onPts[onPts.count]
			local R = (amax width RA_S.spacing) * 1.5
			local mid = (onPts[1] + onPts[onPts.count]) * 0.5
			local fh = ra_rayHit (ray (mid + view * R * 2) (-view))
			local front = if fh != undefined then fh.pos else mid
			local center = front - view * (width * 0.5)
			local ring = #()
			for s = 0 to 71 do
			(
				local a = s * 5.0
				local dv = u * (cos a) + v * (sin a)
				local h = ra_rayHit (ray (center + dv * R) (-dv))
				if h != undefined and (distance h.pos center) < R * 1.2 do append ring h.pos
			)
			if ring.count < 43 then undefined else ra_smoothClosed ring 1
		)
	)
)

fn ra_ringAlign A B =
(
	local k = A.count
	local best = undefined
	local bs = 1e30
	for rv in #(false, true) do
	(
		local BB = if rv then ra_rev B else B
		for ofs = 0 to k - 1 do
		(
			local s = 0.0
			for i = 1 to k do s += distance A[i] BB[(mod (i - 1 + ofs) k) as integer + 1]
			if s < bs do (bs = s; best = for i = 1 to k collect BB[(mod (i - 1 + ofs) k) as integer + 1])
		)
	)
	best
)

-- 기존 링 버텍스(aIdx) 와 새 링 위치(B) 사이를 쿼드로 채움
fn ra_bridgeRing obj aIdx B =
(
	local k = aIdx.count
	local A = for v in aIdx collect polyop.getVert obj v
	B = ra_ringAlign A B
	local cA = [0, 0, 0]
	for q in A do cA += q
	cA /= k
	local cB = [0, 0, 0]
	for q in B do cB += q
	cB /= k
	local avg = 0.0
	for i = 1 to k do avg += distance A[i] B[i]
	avg /= k
	local m = if RA_S.densityMode == 2 then RA_S.countV else amax 1 (ra_round (avg / RA_S.spacing))
	local rows = #(aIdx)
	for j = 1 to m do
	(
		local t = j / (m as float)
		local cc = cA + (cB - cA) * t
		local row = #()
		for i = 1 to k do
		(
			local q = A[i] + (B[i] - A[i]) * t
			append row (polyop.createVert obj (ra_project q (normalize (q - cc))))
		)
		append rows row
	)
	-- 방향을 면을 만들기 전에 결정: 첫 쿼드가 링 중심축에서 바깥을 향하는 순서
	local q1 = for v in #(rows[1][1], rows[1][2], rows[2][2], rows[2][1]) collect polyop.getVert obj v
	local qc = (q1[1] + q1[2] + q1[3] + q1[4]) * 0.25
	local rev = (dot (cross (q1[3] - q1[1]) (q1[4] - q1[2])) (qc - cA)) < 0
	local faces = #()
	for j = 1 to m do for i = 1 to k do
	(
		local i2 = (mod i k) as integer + 1
		local ord = #(rows[j][i], rows[j][i2], rows[j + 1][i2], rows[j + 1][i])
		if rev do ord = ra_rev ord
		local f = polyop.createPolygon obj ord
		if f == undefined do f = polyop.createPolygon obj (ra_rev ord)
		if f != undefined do append faces f
	)
	RA_S.ringVerts = rows[m + 1]
	faces.count
)

fn ra_contour obj onPts view =
(
	local ring = ra_contourRing onPts view
	if ring == undefined then #none
	else
	(
		local cc = [0, 0, 0]
		for q in ring do cc += q
		cc /= ring.count
		local per = (ra_polyLen ring) + (distance ring[ring.count] ring[1])
		local nv = polyop.getNumVerts obj
		local haveRing = RA_S.ringVerts != undefined and (for v in RA_S.ringVerts where v > nv collect v).count == 0
		local spans = if haveRing then RA_S.ringVerts.count \
			else if RA_S.pendingRing != undefined then RA_S.pendingRing.count \
			else if RA_S.densityMode == 2 then RA_S.countU else amax 4 (ra_round (per / RA_S.spacing))
		local loopP = ring + #(ring[1])
		local rsn = ra_resampleN loopP (for q in loopP collect [0, 0, 1]) spans
		local rs = for i = 1 to spans collect (ra_project rsn[1][i] (normalize (rsn[1][i] - cc)))
		if haveRing then (ra_bridgeRing obj RA_S.ringVerts rs; #bridge)
		else if RA_S.pendingRing != undefined then
		(
			local aIdx = for q in RA_S.pendingRing collect polyop.createVert obj q
			RA_S.pendingRing = undefined
			ra_bridgeRing obj aIdx rs
			#bridge
		)
		else (RA_S.pendingRing = rs; #ring)
	)
)

fn ra_processContour onPts view =
(
	if not ra_isPoly RA_S.retopo do ra_setupRetopo()
	local obj = RA_S.retopo
	local r = #none
	if obj != undefined do
	(
		local oldNF = polyop.getNumFaces obj
		local oldOpen = ra_openPos obj
		RA_S.busy = true
		undo "Retopo 컨투어" on (r = ra_contour obj onPts view)
		RA_S.busy = false
		RA_S.lastRec = undefined
		if r == #bridge do ra_makeFlash obj oldNF oldOpen r
	)
	r
)

-- ---------------------------------------------------------------------------
-- 이완 / 대칭
-- ---------------------------------------------------------------------------

fn ra_relax obj iters strength =
(
	if ra_isPoly obj do
	(
		local vs = polyop.getVertSelection obj
		if vs.isEmpty do vs = #{1..(polyop.getNumVerts obj)}
		local openV = polyop.getVertsUsingEdge obj (polyop.getOpenEdges obj)
		undo "Retopo 이완" on
		(
			for it = 1 to iters do
			(
				local moves = #()
				for v in vs where not openV[v] do
				(
					local nbs = for e in (polyop.getEdgesUsingVert obj v) collect polyop.getVert obj (ra_other obj e v)
					if nbs.count >= 2 do
					(
						local avg = [0, 0, 0]
						for q in nbs do avg += q
						avg /= nbs.count
						local q0 = polyop.getVert obj v
						append moves #(v, q0 + (avg - q0) * strength)
					)
				)
				for mv in moves do
				(
					local n = ra_vertNormal obj mv[1]
					polyop.setVert obj #(mv[1]) (if n != undefined and ra_hasTarget() then ra_project mv[2] n else mv[2])
				)
			)
		)
		redrawViews()
	)
)

fn ra_setSymmetry enable =
(
	local obj = RA_S.retopo
	if isValidNode obj do
	(
		local mods = for md in obj.modifiers where md.name == "Retopo Symmetry" collect md
		if enable and mods.count == 0 then
		(
			local s = Symmetry()
			s.name = "Retopo Symmetry"
			try (s.axis = 0) catch ()
			addModifier obj s
			try (showEndResult = true) catch ()
		)
		else if not enable do for md in mods do deleteModifier obj md
	)
)

fn ra_meshSig obj = (if ra_isPoly obj then #(polyop.getNumVerts obj, polyop.getNumEdges obj, polyop.getNumFaces obj) else undefined)

fn ra_processStroke pts nrms mode:undefined =
(
	-- '다음 선' 버튼으로 정한 방식은 이 선 하나에만 적용
	local md = if mode != undefined then mode else if RA_S.nextMode > 0 then RA_S.nextMode else RA_S.mode
	if RA_S.nextMode > 0 do (RA_S.nextMode = 0; ra_syncUI())
	local pendingBefore = for s in RA_S.pending collect s
	local snap = if ra_isPoly RA_S.retopo then copy RA_S.retopo.baseObject else undefined
	local origP = pts
	local origN = nrms
	if not ra_isPoly RA_S.retopo do ra_setupRetopo()
	local obj = RA_S.retopo
	if obj == undefined do return #none
	local savedSpacing = RA_S.spacing
	if RA_S.densityMode == 3 do
	(
		-- 평균: 선택한 엣지(없으면 열린 엣지)의 평균 길이를 간격으로
		local es = polyop.getEdgeSelection obj
		if es.isEmpty do es = polyop.getOpenEdges obj
		if not es.isEmpty do
		(
			local s = 0.0
			for e in es do (local ev = polyop.getEdgeVerts obj e; s += distance (polyop.getVert obj ev[1]) (polyop.getVert obj ev[2]))
			RA_S.spacing = amax 1e-4 (s / es.numberSet)
		)
	)
	local dd = ra_dedupe pts nrms 1e-6
	if RA_S.snapCreases and dd[1].count >= 2 then
	(
		local ic = ra_insertCreases dd[1] dd[2]
		for c in ic[3] where (ra_creaseAt c[1]) == undefined do append RA_S.creases c
		if RA_S.creases.count > 400 do RA_S.creases = for i = RA_S.creases.count - 399 to RA_S.creases.count collect RA_S.creases[i]
		local fixed = #{}
		for i = 1 to ic[1].count where (ra_creaseAt ic[1][i]) != undefined do fixed[i] = true
		pts = ra_smooth ic[1] 2 fixed:fixed
		nrms = ic[2]
	)
	else
	(
		pts = ra_smooth dd[1] 2
		nrms = dd[2]
	)
	if pts.count < 2 or (ra_polyLen pts) < RA_S.spacing * 0.25 do (RA_S.spacing = savedSpacing; return #none)
	local closed = ra_isClosed pts
	local cp = pts
	local cn = nrms
	if closed do
	(
		local head = for i = 1 to pts.count - 1 collect pts[i]
		cp = ra_smoothClosed head 3
		cn = for i = 1 to nrms.count - 1 collect nrms[i]
	)
	local result = #none
	local oldNF = polyop.getNumFaces obj
	local oldOpen = ra_openPos obj
	RA_S.busy = true
	undo "Retopo 주석" on
	(
		case md of
		(
			1: (
				if (polyop.getNumFaces obj) > 0 and (ra_cut obj pts true) >= 2 then (ra_cut obj pts false; result = #cut)
				else if closed then (ra_fillLoop obj cp cn; result = #fill)
				else (append RA_S.pending #(pts, nrms); result = ra_tryPending obj)
			)
			2: (ra_strip obj pts nrms; result = #strip)
			3: (ra_fillLoop obj cp cn; result = #fill)
			4: (
				append RA_S.pending #(pts, nrms)
				if RA_S.pending.count >= 2 do
				(
					local P = RA_S.pending
					ra_loft obj P[1][1] P[1][2] P[2][1] P[2][2]
					RA_S.pending = #()
					result = #loft
				)
			)
			5: (ra_cut obj pts false; result = #cut)
			7: (
				-- 영역 선택: 둘러싼 곳의 면 선택
				local n = ra_regionSelect obj pts
				format "[RetopoAnnotate] 영역 선택: 면 %개 (촘촘하게/성기게/고르게 재구성 버튼이 이 영역에 적용)\n" n
				RA_S.lastMsg = "영역 선택: 면 " + n as string + "개 (촘촘하게/성기게/고르게 재구성 버튼이 이 영역에 적용)"
				if not (GetQuietMode()) do displayTempPrompt RA_S.lastMsg 5000
			)
			8: (
				-- 흐름 재구성: 선택 면 영역을 그은 선 방향으로 다시 채움
				local fs = polyop.getFaceSelection obj
				if fs.isEmpty do
				(
					local vs = polyop.getVertSelection obj
					if not vs.isEmpty do fs = polyop.getFacesUsingVert obj vs
				)
				if fs.isEmpty then RA_S.lastMsg = "흐름 재구성: 먼저 다시 만들 면 영역을 선택하세요 ('영역 선택' 모드로 둘러싸도 됨)"
				else
				(
					local r = ra_rebuildRegion obj fs (pts[pts.count] - pts[1])
					RA_S.lastMsg = r[2]
					if r[1] > 0 do result = #fill
				)
				format "[RetopoAnnotate] %\n" RA_S.lastMsg
				if not (GetQuietMode()) do displayTempPrompt RA_S.lastMsg 5000
			)
		)
	)
	RA_S.busy = false
	RA_S.spacing = savedSpacing
	if result != #none do RA_S.ringVerts = undefined  -- 다른 작업 뒤에는 컨투어 이어가기 종료
	if result != #none and result != #wait do
	(
		ra_makeFlash obj oldNF oldOpen result
		RA_S.lastRec = #(origP, origN, pendingBefore, snap, md)
		RA_S.lastSig = ra_meshSig obj
	)
	result
)

-- 밀도 값을 바꾸면 마지막 결과를 되돌리고 새 밀도로 다시 생성
fn ra_redoLast =
(
	local obj = RA_S.retopo
	if RA_S.redoOnChange and RA_S.lastRec != undefined and RA_S.lastRec[4] != undefined and ra_isPoly obj do
	(
		local sig = ra_meshSig obj
		if sig[1] == RA_S.lastSig[1] and sig[2] == RA_S.lastSig[2] and sig[3] == RA_S.lastSig[3] do
		(
			local rec = RA_S.lastRec
			RA_S.busy = true
			obj.baseObject = copy rec[4]   -- 변환 전 상태로 복원
			ra_enableAutoFill RA_S.autoFill
			RA_fillPending = false
			RA_S.pending = rec[3]
			ra_processStroke rec[1] rec[2] mode:rec[5]
			redrawViews()
		)
	)
)

-- ---------------------------------------------------------------------------
-- 뷰포트 그리기 (주석)
-- ---------------------------------------------------------------------------

fn ra_drawPoly pts = (if pts.count > 1 do gw.polyline pts false)

-- 점 p 의 연결 상태 표시: 초록 = 기존 메쉬(또는 대기 선)에 이어짐, 주황 = 새로 따로 생성
fn ra_drawConn p info =
(
	if p != undefined and info != undefined do
	(
		local ok = info[1] != #none
		local c = if ok then RA_S.connColor else RA_S.newColor
		local obj = RA_S.retopo
		if info[1] == #edge and ra_isPoly obj and info[3] <= (polyop.getNumVerts obj) do
		(
			local a = polyop.getVert obj info[2]
			local b = polyop.getVert obj info[3]
			gw.setColor #line c
			gw.polyline #(a, b) false
			gw.wMarker (gw.wTransPoint a) #bigBox color:c
			gw.wMarker (gw.wTransPoint b) #bigBox color:c
		)
		if info[1] == #vert and ra_isPoly obj and info[2] <= (polyop.getNumVerts obj) do
			gw.wMarker (gw.wTransPoint (polyop.getVert obj info[2])) #bigBox color:c
		if info[1] == #pending do gw.wMarker (gw.wTransPoint info[2]) #bigBox color:c
		local sp = gw.wTransPoint p
		gw.wMarker sp #circle color:c
		gw.wMarker sp #smallCircle color:c
		gw.wText (sp + [12, -6, 0]) (if ok then "이어짐" else "새로 생성") color:c
	)
)

fn ra_drawCBfn =
(
	if RA_S != undefined do
	(
		gw.setTransform (matrix3 1)
		if RA_S.curPts.count > 1 do (gw.setColor #line (if RA_S.guideMode then RA_S.guideColor else RA_S.strokeColor); ra_drawPoly RA_S.curPts)
		if RA_S.showPending do for s in RA_S.pending do (gw.setColor #line RA_S.pendingColor; ra_drawPoly s[1])
		if RA_S.showPending and RA_S.pendingRing != undefined do (gw.setColor #line RA_S.pendingColor; gw.polyline RA_S.pendingRing true)
		for g in RA_S.scanGuides do (gw.setColor #line RA_S.guideColor; ra_drawPoly g[1])
		if RA_S.showConnect and RA_S.tracking and not RA_S.guideMode do
		(
			if RA_S.drawing and RA_S.curPts.count > 0 then
			(
				ra_drawConn RA_S.curPts[1] RA_S.startInfo
				if RA_S.curPts.count > 1 do ra_drawConn RA_S.curPts[RA_S.curPts.count] RA_S.endInfo
			)
			else ra_drawConn RA_S.hoverPt RA_S.hoverInfo
		)
		local fl = RA_S.flash
		if fl != undefined do
		(
			gw.setColor #line fl[2]
			for lp in fl[1] do gw.polyline lp true
			gw.wText ((gw.wTransPoint fl[4]) + [-30, 0, 0]) fl[3] color:fl[2]
		)
		gw.enlargeUpdateRect #whole
		gw.updateScreen()
	)
)
RA_drawCB = ra_drawCBfn
registerRedrawViewsCallback RA_drawCB

fn ra_endStroke =
(
	if RA_S.drawing do
	(
		RA_S.drawing = false
		local pts = RA_S.curPts
		local nrms = RA_S.curNrm
		local onF = RA_S.curOn
		local view = RA_S.curView
		RA_S.curPts = #()
		RA_S.curNrm = #()
		RA_S.curOn = #()
		RA_S.curView = undefined
		RA_S.startInfo = undefined
		RA_S.endInfo = undefined
		RA_S.hoverPt = undefined
		if pts.count >= 2 do
		(
			try
			(
				-- 형태 밖에서 시작해 가로질러 밖에서 끝난 선 = 컨투어
				local isContour = RA_S.nextMode == 0 and (RA_S.mode == 1 or RA_S.mode == 6) and view != undefined and ra_isContourFlags onF
				if RA_S.guideMode then append RA_S.scanGuides #(pts, nrms)
				else if isContour then ra_processContour pts view
				else if RA_S.mode != 6 or RA_S.nextMode > 0 do ra_processStroke pts nrms
			)
			catch (format "[RetopoAnnotate] %\n" (getCurrentException()))
		)
		redrawViews()
	)
)

-- 현재 마우스 위치에서 모든 타겟에 레이캐스트 (여러 오브젝트/레이어 타겟 지원)
fn ra_addScreen =
(
	local r = mapScreenToWorldRay mouse.pos
	if RA_S.curView == undefined do RA_S.curView = -(normalize r.dir)
	local h = ra_rayHit r
	append RA_S.curOn (h != undefined)
	if h != undefined do
	(
		local nn = normalize h.dir
		if dot nn r.dir > 0 do nn = -nn
		local p = h.pos + nn * RA_S.offset
		local n = RA_S.curPts.count
		if n == 0 or (distance RA_S.curPts[n] p) > RA_S.spacing * 0.05 do
		(
			append RA_S.curPts p
			append RA_S.curNrm nn
			if RA_S.showConnect and not RA_S.guideMode do
			(
				local cp = RA_S.curPts
				local m = cp.count
				if m == 1 then (RA_S.startInfo = ra_connectAt p; RA_S.endInfo = undefined)
				else if m == 4 do RA_S.startInfo = ra_connectAt cp[1] dir:(cp[4] - cp[1])
				if m >= 2 and (mod m 3) == 0 do RA_S.endInfo = ra_connectAt p dir:(cp[amax 1 (m - 3)] - p)
			)
		)
	)
)

-- 그리기 모드에서 버튼을 누르지 않고 움직일 때: 커서 위치가 이어지는 곳인지 미리 표시
fn ra_updateHover =
(
	if RA_S.showConnect and not RA_S.guideMode do
	(
		local h = ra_rayHit (mapScreenToWorldRay mouse.pos)
		if h != undefined then (RA_S.hoverPt = h.pos; RA_S.hoverInfo = ra_connectAt h.pos)
		else (RA_S.hoverPt = undefined; RA_S.hoverInfo = undefined)
		redrawViews()
	)
)
-- mouseTrack 콜백: 누르고 끌면 그리기, 버튼을 떼면(freeMove) 변환, 우클릭 = 종료
fn ra_trackCB msg ir obj faceNum shift ctrl alt =
(
	case msg of
	(
		#mousePoint:
		(
			if RA_S.drawing then ra_endStroke()
			else (RA_S.drawing = true; RA_S.curPts = #(); RA_S.curNrm = #(); RA_S.curOn = #(); RA_S.curView = undefined; ra_addScreen())
			#continue
		)
		#mouseMove:
		(
			if not RA_S.drawing do (RA_S.drawing = true; RA_S.curPts = #(); RA_S.curNrm = #(); RA_S.curOn = #(); RA_S.curView = undefined)
			ra_addScreen()
			redrawViews()
			#continue
		)
		#freeMove:
		(
			if RA_S.drawing then ra_endStroke() else ra_updateHover()
			#continue
		)
		#mouseAbort: (ra_endStroke(); #abort)
		default: #continue
	)
)

fn ra_startDraw =
(
	if not (ra_hasTarget()) and not (RA_S.guideMode and isValidNode RA_ScanNode) then messageBox "타겟(하이폴리) 오브젝트나 레이어를 먼저 지정하세요" title:"Retopo"
	else
	(
		if not ra_isPoly RA_S.retopo do ra_setupRetopo()
		RA_S.drawing = false
		RA_S.curPts = #()
		RA_S.curNrm = #()
		RA_S.tracking = true
		try (mouseTrack trackCallback:ra_trackCB prompt:"주석 그리기: 드래그 = 선, 우클릭 = 종료, Ctrl+Z / Ctrl+Y(Ctrl+Shift+Z) = 되돌리기 / 다시")
		catch (format "[RetopoAnnotate] %\n" (getCurrentException()))
		RA_S.tracking = false
		RA_S.hoverPt = undefined
		RA_S.hoverInfo = undefined
		ra_endStroke()
		ra_flushPending()
	)
)
fn ra_projectAll obj =
(
	if ra_isPoly obj and ra_hasTarget() do
	(
		local vs = polyop.getVertSelection obj
		if vs.isEmpty do vs = #{1..(polyop.getNumVerts obj)}
		undo "Retopo 표면에 붙이기" on
		(
			for v in vs do
			(
				local n = ra_vertNormal obj v
				if n != undefined do polyop.setVert obj #(v) (ra_project (polyop.getVert obj v) n)
			)
		)
		redrawViews()
	)
)

-- ---------------------------------------------------------------------------
-- UI
-- ---------------------------------------------------------------------------

fn ra_geoFilter o = (superClassOf o == GeometryClass)

-- ---------------------------------------------------------------------------
-- 키 입력 도우미 (백그라운드 스레드)
--  * 주석 그리기 모드(mouseTrack) 중에는 Max 단축키가 막히므로 Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z 를 직접 처리
--  * Alt+휠 / Shift+Alt+휠: 방금 만든 결과의 밀도 / 스트립 폭 (조절할 결과가 있을 때만 휠을 가로챔)
-- ---------------------------------------------------------------------------
global RA_Keys
fn ra_initKeys =
(
	-- 1) 설치된 미리 컴파일한 RAKeys.dll (Max 2025+ 의 .NET 8 에서도 동작)
	if RA_Keys == undefined and RA_ScriptDir != undefined and doesFileExist (RA_ScriptDir + "RAKeys.dll") do
	(
		try
		(
			local asm = dotNet.loadAssembly (RA_ScriptDir + "RAKeys.dll")
			local k = asm.CreateInstance "RAKeys"
			k.Start ((windows.getMAXHWND()) as integer64)
			RA_Keys = k
		)
		catch (RA_Keys = undefined)
	)
	-- 2) 없으면 실행 중 컴파일 (.NET Framework 를 쓰는 Max 2024 이하)
	if RA_Keys == undefined do
	(
		try
		(
			local src = "using System; using System.Threading; using System.Runtime.InteropServices;\n" + \
				"public class RAKeys {\n" + \
				" [DllImport(\"user32.dll\")] static extern short GetAsyncKeyState(int k);\n" + \
				" [DllImport(\"user32.dll\")] static extern IntPtr GetForegroundWindow();\n" + \
				" [DllImport(\"user32.dll\")] static extern IntPtr GetAncestor(IntPtr h, uint f);\n" + \
				" [DllImport(\"user32.dll\")] static extern IntPtr SetWindowsHookEx(int id, HookProc fn, IntPtr mod, uint tid);\n" + \
				" [DllImport(\"user32.dll\")] static extern IntPtr CallNextHookEx(IntPtr h, int n, IntPtr w, IntPtr l);\n" + \
				" [DllImport(\"user32.dll\")] static extern int GetMessage(out MSG m, IntPtr h, uint a, uint b);\n" + \
				" [DllImport(\"kernel32.dll\")] static extern IntPtr GetModuleHandle(string n);\n" + \
				" public delegate IntPtr HookProc(int n, IntPtr w, IntPtr l);\n" + \
				" [StructLayout(LayoutKind.Sequential)] public struct MSG { public IntPtr hwnd; public uint message; public IntPtr wp; public IntPtr lp; public uint time; public int x; public int y; }\n" + \
				" [StructLayout(LayoutKind.Sequential)] public struct MSLL { public int x; public int y; public uint data; public uint flags; public uint time; public IntPtr extra; }\n" + \
				" volatile int pend; int wheel; int wheelS; public volatile bool Armed; long owner; Thread th; Thread th2; IntPtr hook; HookProc proc;\n" + \
				" static bool D(int k) { return (GetAsyncKeyState(k) & 0x8000) != 0; }\n" + \
				" bool Front() { return GetAncestor(GetForegroundWindow(), 3).ToInt64() == owner; }\n" + \
				" public void Start(long hwnd) { owner = hwnd; if (th != null) return;\n" + \
				"  th = new Thread(Loop); th.IsBackground = true; th.Start();\n" + \
				"  th2 = new Thread(HookLoop); th2.IsBackground = true; th2.Start(); }\n" + \
				" void Loop() { bool prev = false; while (true) {\n" + \
				"  bool c = D(0x11), z = D(0x5A), y = D(0x59);\n" + \
				"  bool fire = c && (z || y);\n" + \
				"  if (fire && !prev && Front()) pend = (z && !D(0x10)) ? 1 : 2;\n" + \
				"  prev = fire; Thread.Sleep(5); } }\n" + \
				" void HookLoop() { proc = new HookProc(OnMouse); hook = SetWindowsHookEx(14, proc, GetModuleHandle(null), 0);\n" + \
				"  MSG m; while (GetMessage(out m, IntPtr.Zero, 0, 0) > 0) { } }\n" + \
				" IntPtr OnMouse(int n, IntPtr w, IntPtr l) {\n" + \
				"  if (n >= 0 && w.ToInt64() == 0x020A && Armed && D(0x12) && Front()) {\n" + \
				"   MSLL s = (MSLL)Marshal.PtrToStructure(l, typeof(MSLL));\n" + \
				"   int d = (short)((s.data >> 16) & 0xffff);\n" + \
				"   int st = d > 0 ? 1 : -1;\n" + \
				"   lock (this) { if (D(0x10)) wheelS += st; else wheel += st; }\n" + \
				"   return (IntPtr)1; }\n" + \
				"  return CallNextHookEx(hook, n, w, l); }\n" + \
				" public int Take() { int p = pend; pend = 0; return p; }\n" + \
				" public int TakeWheel() { lock (this) { int p = wheel; wheel = 0; return p; } }\n" + \
				" public int TakeWheelShift() { lock (this) { int p = wheelS; wheelS = 0; return p; } }\n" + \
				"}"
			local prov = dotNetObject "Microsoft.CSharp.CSharpCodeProvider"
			local prm = dotNetObject "System.CodeDom.Compiler.CompilerParameters"
			prm.GenerateInMemory = true
			local srcs = dotNet.ValueToDotNetObject #(src) (dotNetClass "System.String[]")
			local res = prov.CompileAssemblyFromSource prm srcs
			if res.Errors.Count == 0 then
			(
				RA_Keys = res.CompiledAssembly.CreateInstance "RAKeys"
				RA_Keys.Start ((windows.getMAXHWND()) as integer64)
			)
			else RA_Keys = false
		)
		catch (RA_Keys = false)
	)
	if RA_Keys == false then undefined else RA_Keys
)

-- 방금 만든 결과를 다시 만들 수 있는지 (그 뒤 메쉬를 고치지 않았는지)
fn ra_canAdjust =
(
	local obj = RA_S.retopo
	if RA_S.lastRec == undefined or RA_S.lastRec[4] == undefined or not RA_S.redoOnChange or not (ra_isPoly obj) then false
	else
	(
		local sig = ra_meshSig obj
		sig[1] == RA_S.lastSig[1] and sig[2] == RA_S.lastSig[2] and sig[3] == RA_S.lastSig[3]
	)
)

-- Alt+휠 / 버튼: 방금 만든 결과의 밀도(what #density) 또는 스트립 폭(#width) 한 단계
fn ra_adjustLast what step =
(
	if what == #density and not (ra_canAdjust()) and (ra_canAdjustScan()) then ra_scanAdjust step
	else if not (ra_canAdjust()) then
	(
		if not (GetQuietMode()) do displayTempPrompt "조절할 결과가 없습니다 — 주석으로 방금 만든 결과에만 적용 (그 뒤 고치거나 되돌렸다면 새로 그은 뒤)" 4000
		false
	)
	else
	(
		if what == #width then
		(
			local base = if RA_S.stripWidth > 0 then RA_S.stripWidth else RA_S.spacing
			RA_S.stripWidth = amax 1e-4 (base * (1.2 ^ step))
		)
		else if RA_S.densityMode == 2 then
		(
			RA_S.countU = amax 1 (RA_S.countU + step)
			RA_S.countV = amax 1 (RA_S.countV + step)
			RA_S.countEdge = amax 1 (RA_S.countEdge + step)
		)
		else
		(
			if RA_S.densityMode == 3 do RA_S.densityMode = 1
			RA_S.spacing = amax 1e-4 (RA_S.spacing * (0.85 ^ step))
		)
		ra_redoLast()
		ra_syncUI()
		if not (GetQuietMode()) do
			displayTempPrompt (if what == #width then ("스트립 폭 " + RA_S.stripWidth as string) \
				else if RA_S.densityMode == 2 then ("분할 수 " + RA_S.countU as string) else ("엣지 길이 " + RA_S.spacing as string)) 2000
		true
	)
)

fn ra_keyTick =
(
	local k = ra_initKeys()
	if k != undefined do
	(
		k.Armed = ra_canAdjust() or ra_canAdjustScan()
		-- Alt+휠 / Shift+Alt+휠
		local w = k.TakeWheel()
		local ws = k.TakeWheelShift()
		if not RA_S.busy do
		(
			if w != 0 do ra_adjustLast #density w
			if ws != 0 do ra_adjustLast #width ws
		)
		-- 그리기 모드 중 Ctrl+Z / Ctrl+Y (그 밖에는 Max 가 직접 처리하므로 버림)
		local p = k.Take()
		if p > 0 and RA_S.tracking and not RA_S.busy and not RA_S.drawing do
		(
			if p == 1 then
			(
				-- 가이드 선 그리는 중이면 마지막 가이드 선을 지움
				if RA_S.guideMode then (if RA_S.scanGuides.count > 0 do RA_S.scanGuides = for i = 1 to RA_S.scanGuides.count - 1 collect RA_S.scanGuides[i])
				-- 아직 메쉬가 안 된 대기 선이 있으면 그 선부터 지움
				else if RA_S.pending.count > 0 then RA_S.pending = for i = 1 to RA_S.pending.count - 1 collect RA_S.pending[i]
				else if RA_S.pendingRing != undefined then RA_S.pendingRing = undefined
				else (RA_S.ringVerts = undefined; RA_S.lastRec = undefined; max undo)
			)
			else if not RA_S.guideMode do (RA_S.ringVerts = undefined; RA_S.lastRec = undefined; max redo)
			RA_S.flash = undefined
			RA_S.hoverInfo = undefined
			redrawViews()
		)
	)
	-- 결과 강조는 1.5초 뒤 사라짐
	if RA_S.flash != undefined and (timeStamp() - RA_S.flash[5]) > 1500 do (RA_S.flash = undefined; redrawViews())
)

-- ---------------------------------------------------------------------------
-- 버튼 공용 동작
-- ---------------------------------------------------------------------------

fn ra_editObj =
(
	local obj = if ra_isPoly RA_S.retopo then RA_S.retopo else (if selection.count == 1 and ra_isPoly selection[1] then selection[1] else undefined)
	if obj == undefined do messageBox "리토 메쉬(Editable Poly)가 필요합니다 — 먼저 '리토폴로지 시작'" title:"Retopo"
	obj
)

-- 한 번만: 다음에 긋는 주석 선을 이 방식(7 영역 선택 / 8 흐름 재구성 / 5 컷)으로. 그리기 모드가 아니면 바로 시작
fn ra_armNext md =
(
	if RA_S.nextMode == md then (RA_S.nextMode = 0; displayTempPrompt "다음 선: 취소" 2000)
	else
	(
		RA_S.nextMode = md
		local names = #("", "", "", "", "컷 — 자를 곳을 그으세요", "", "영역 둘러싸기 — 수정할 곳을 둘러싸세요", "흐름 선 — 선택 영역 위에 원하는 흐름 방향으로 그으세요")
		displayTempPrompt ("다음 선: " + names[md]) 6000
	)
	ra_syncUI()
	redrawViews()
	if RA_S.nextMode > 0 and not RA_S.tracking do ra_startDraw()
)

fn ra_doRebuild =
(
	local obj = ra_editObj()
	if obj != undefined do
	(
		if (polyop.getFaceSelection obj).isEmpty and (polyop.getVertSelection obj).isEmpty then
			messageBox "다시 만들 면 영역을 선택하세요 ('영역 둘러싸기'로 둘러싸도 됨)" title:"Retopo"
		else
		(
			local r = try (ra_rebuildRegion obj (ra_regionFaces obj) undefined) catch (RA_S.busy = false; #(0, "오류: " + getCurrentException()))
			if r[1] == 0 then messageBox r[2] title:"Retopo 고르게 재구성" else (format "[RetopoAnnotate] %\n" r[2]; displayTempPrompt r[2] 3000)
		)
	)
)

fn ra_doOffset =
(
	local obj = ra_editObj()
	if obj != undefined do
	(
		if (polyop.getFaceSelection obj).isEmpty and (polyop.getVertSelection obj).isEmpty then messageBox "면을 선택하세요" title:"Retopo"
		else
		(
			local r = try (ra_offsetRegion obj (ra_regionFaces obj)) catch (RA_S.busy = false; #(0, "오류: " + getCurrentException()))
			if r[1] == 0 then messageBox r[2] title:"Retopo 오프셋" else displayTempPrompt r[2] 3000
		)
	)
)

fn ra_doDensity step =
(
	local obj = ra_editObj()
	if obj != undefined do
	(
		if step > 0 then (try (ra_densify obj) catch (RA_S.busy = false; messageBox ("오류: " + getCurrentException()) title:"Retopo"))
		else
		(
			local n = try (ra_sparsify obj) catch (RA_S.busy = false; messageBox ("오류: " + getCurrentException()) title:"Retopo"; -1)
			if n == 0 do messageBox "줄일 엣지 루프가 없습니다 (쿼드 격자 모양 영역에서 동작)" title:"Retopo"
		)
	)
)

fn ra_doFillGap =
(
	local obj = ra_editObj()
	if obj != undefined do
	(
		local r = try (ra_fillGap obj) catch (RA_S.busy = false; #(0, "오류: " + (getCurrentException())))
		if r[1] == 0 then messageBox r[2] title:"Retopo 빈 곳 채우기" else displayTempPrompt r[2] 3000
	)
)

-- 떨어진 메쉬 연결: Editable Poly 오브젝트 여러 개를 골랐으면 먼저 하나로 합친 뒤 가장 가까운 두 조각을 이음
fn ra_doConnect =
(
	local tg = ra_targets()
	local polys = for o in selection where ra_isPoly o and findItem tg o == 0 collect o
	local obj = undefined
	if polys.count >= 2 then
	(
		obj = if findItem polys RA_S.retopo > 0 then RA_S.retopo else polys[1]
		undo "Retopo 오브젝트 합치기" on (for o in polys where o != obj do polyop.attach obj o)
		RA_S.retopo = obj
		ra_enableAutoFill RA_S.autoFill
		select obj
		polyop.setVertSelection obj #{}
	)
	else obj = ra_editObj()
	if obj != undefined do
	(
		local r = try (ra_connectPieces obj) catch (RA_S.busy = false; #(0, "오류: " + getCurrentException()))
		if r[1] == 0 then messageBox r[2] title:"Retopo 떨어진 메쉬 연결" else (format "[RetopoAnnotate] %\n" r[2]; displayTempPrompt r[2] 3000)
		r[1]
	)
)

fn ra_doCrease =
(
	local obj = ra_editObj()
	if obj != undefined do
	(
		if ((polyop.getVertSelection obj) as array).count < 2 then messageBox "주름이 지나갈 버텍스를 2개 이상 선택하세요" title:"Retopo"
		else
		(
			local r = ra_crease obj RA_S.creaseRatio RA_S.creaseClosed
			format "[RetopoAnnotate] 주름: 구간 % / 컷 % / 합친 버텍스 %\n" r[1] r[2] r[3]
		)
	)
)

fn ra_doScan =
(
	local nodes = for o in selection collect o
	if nodes.count == 0 do nodes = ra_targets()
	local r = try (ra_scanMerge nodes) catch (#(undefined, "오류: " + getCurrentException()))
	if r[1] == undefined then messageBox r[2] title:"Retopo 스캔"
	else
	(
		RA_S.retopo = r[1]
		ra_enableAutoFill RA_S.autoFill
		select r[1]
		format "[RetopoAnnotate] %\n" r[2]
		displayTempPrompt r[2] 5000
	)
)

-- ---------------------------------------------------------------------------
-- 창: 시작·그리기 / 수정 (항상) · 표시 / 고급 설정 / 단축키 (접혀 있음)
-- ---------------------------------------------------------------------------
global RA_Floater
global RA_EditRO
global RA_ViewRO
global RA_AdvRO
global RA_KeysRO

rollout RA_Rollout "시작 · 그리기"
(
	pickbutton pbTarget "타겟(하이폴리) 선택" width:236 filter:ra_geoFilter autoDisplay:true
	button btnTargetsSel "선택 오브젝트들" width:116 across:2
	button btnTargetLayer "레이어 전체 ▶" width:116
	dropdownlist ddLayer "" width:236
	label lbTarget "타겟: 없음" align:#left
	button btnSetup "리토폴로지 시작" width:116 height:26 across:2
	button btnScan "스캔 → 합친 메쉬" width:116 height:26
	spinner spScanTarget "스캔 목표 면 수 (0=엣지 길이)" range:[0, 2000000, 0] type:#integer fieldwidth:60 align:#right
	checkbox ckScanSharp "스캔: 모서리 살리기" checked:true across:2
	checkbox ckScanQuad "전부 쿼드" checked:true offset:[20, 0]
	checkbutton ckGuide "가이드 선 그리기" width:116 across:2 tooltip:"스캔 결과 위에 원하는 엣지 흐름을 그음 (우클릭 = 끝)"
	button btnGuideApply "가이드로 다시 만들기" width:116 tooltip:"그은 가이드 선을 따라 스캔 메쉬 토폴로지를 다시 만듦"
	button btnGuideClear "가이드 지우기" width:236
	button btnUseSel "선택한 Editable Poly를 리토 메쉬로" width:236
	dropdownlist ddMode "그리기 방식" items:#("자동", "스트립", "도형 채우기", "두 선 사이", "컷", "컨투어", "영역 선택", "흐름 재구성") width:236
	spinner spSpacing "엣지 길이" range:[0.0001, 1e6, 5] type:#worldunits fieldwidth:60 across:3 align:#left
	button btnDenP "+" width:24 offset:[34, 0]
	button btnDenM "−" width:24 offset:[-2, 0]
	spinner spStripW "스트립 폭" range:[0, 1e6, 0] type:#worldunits fieldwidth:60 across:3 align:#left
	button btnWidP "+" width:24 offset:[34, 0]
	button btnWidM "−" width:24 offset:[-2, 0]
	checkbutton ckDraw "주석 그리기 시작 (우클릭 = 종료)" width:236 height:32
	button btnFlush "대기 선 → 스트립" width:116 across:2
	button btnClearPend "대기 선 지우기" width:116
	label lbHint "+/−, Alt+휠: 방금 만든 결과 다시 만들기" align:#left
	timer tmFill interval:50 active:true

	fn syncUI = ra_syncUI()
	on RA_Rollout open do (ra_initKeys(); ra_syncUI())
	on tmFill tick do
	(
		if RA_fillPending do ra_autoFillTick()
		ra_keyTick()
	)
	on pbTarget picked obj do (ra_setTarget obj; ra_syncUI())
	on btnTargetsSel pressed do
	(
		local objs = for o in selection where superClassOf o == GeometryClass and o != RA_S.retopo collect o
		if objs.count == 0 then messageBox "타겟으로 쓸 오브젝트를 선택하세요" title:"Retopo"
		else (ra_setTargets objs ((objs.count as string) + "개 오브젝트"); ra_syncUI())
	)
	on btnTargetLayer pressed do
	(
		if ddLayer.selected != undefined do
		(
			local n = ra_setTargets (ra_layerNodes ddLayer.selected) ("레이어 " + ddLayer.selected)
			if n == 0 do messageBox "그 레이어에 지오메트리 오브젝트가 없습니다" title:"Retopo"
			ra_syncUI()
		)
	)
	on btnSetup pressed do
	(
		if not (ra_hasTarget()) and selection.count >= 1 do
			ra_setTargets (for o in selection collect o) (if selection.count == 1 then selection[1].name else ((selection.count as string) + "개 오브젝트"))
		ra_setupRetopo()
		ra_syncUI()
	)
	on btnScan pressed do ra_doScan()
	on spScanTarget changed v inSpin do
	(
		RA_S.scanTarget = v
		-- 값을 입력(Enter)했을 때만 바로 다시 만듦. 화살표를 끄는 동안은 놓을 때(buttonup)
		if not inSpin and v > 0 do ra_scanRebuild v
	)
	on spScanTarget buttonup do (if RA_S.scanTarget > 0 do ra_scanRebuild RA_S.scanTarget)
	on ckScanSharp changed st do RA_S.scanSharp = st
	on ckScanQuad changed st do RA_S.scanPureQuad = st
	on ckGuide changed st do
	(
		if st do ra_drawGuides()
		ckGuide.checked = false
	)
	on btnGuideApply pressed do ra_scanApplyGuides()
	on btnGuideClear pressed do ra_scanClearGuides()
	on btnUseSel pressed do
	(
		if selection.count == 1 and ra_isPoly selection[1] then (RA_S.retopo = selection[1]; ra_enableAutoFill RA_S.autoFill)
		else messageBox "Editable Poly 오브젝트 하나를 선택하세요" title:"Retopo"
	)
	on ddMode selected i do RA_S.mode = i
	on spSpacing changed v do (RA_S.spacing = v; if RA_S.densityMode == 1 do ra_redoLast())
	on btnDenP pressed do ra_adjustLast #density 1
	on btnDenM pressed do ra_adjustLast #density -1
	on spStripW changed v do (RA_S.stripWidth = v; ra_redoLast())
	on btnWidP pressed do ra_adjustLast #width 1
	on btnWidM pressed do ra_adjustLast #width -1
	on ckDraw changed st do
	(
		if st do
		(
			ra_startDraw()
			ckDraw.checked = false
		)
	)
	on btnFlush pressed do ra_flushPending()
	on btnClearPend pressed do (RA_S.pending = #(); RA_S.pendingRing = undefined; RA_S.ringVerts = undefined; redrawViews())
)

rollout RA_EditRO "수정"
(
	label lb1 "주석으로 (다음 선 한 번만):" align:#left
	checkbutton ckRegion "영역 둘러싸기" width:78 across:3
	checkbutton ckFlow "흐름 선" width:78
	checkbutton ckCut "컷 선" width:78
	label lb2 "선택한 면 영역:" align:#left
	button btnRebuild "고르게 재구성" width:116 across:2
	button btnOffset "오프셋 (루프 추가)" width:116
	button btnDenser "촘촘하게 ×2" width:116 across:2
	button btnSparser "성기게 ÷2" width:116
	label lb3 "선택한 버텍스:" align:#left
	button btnFillGap "빈 곳 채우기" width:116 across:2
	button btnCrease "주름 만들기" width:116
	button btnConnect "떨어진 메쉬 연결" width:236
	button btnQuadEx "쿼드 익스트루드" width:116 across:2
	button btnProject "표면에 붙이기" width:116
	button btnRelax "이완" width:116 across:2
	checkbox ckSym "대칭 X" checked:false offset:[20, 2]

	on ckRegion changed st do ra_armNext 7
	on ckFlow changed st do ra_armNext 8
	on ckCut changed st do ra_armNext 5
	on btnRebuild pressed do ra_doRebuild()
	on btnOffset pressed do ra_doOffset()
	on btnDenser pressed do ra_doDensity 1
	on btnSparser pressed do ra_doDensity -1
	on btnFillGap pressed do ra_doFillGap()
	on btnCrease pressed do ra_doCrease()
	on btnConnect pressed do ra_doConnect()
	on btnQuadEx pressed do ra_quadExtrude (if ra_isPoly RA_S.retopo then RA_S.retopo else (if selection.count == 1 then selection[1] else undefined))
	on btnProject pressed do ra_projectAll RA_S.retopo
	on btnRelax pressed do ra_relax RA_S.retopo 5 0.5
	on ckSym changed st do ra_setSymmetry st
)

rollout RA_ViewRO "표시"
(
	checkbox ckXray "리토 X-Ray" checked:true across:2
	checkbox ckFreeze "타겟 동결" checked:false
	checkbox ckShowConn "이어짐 표시" checked:true across:2
	checkbox ckShowPend "대기 선 표시" checked:true
	colorpicker cpStroke "선 색" color:(color 255 90 25) across:2
	colorpicker cpPend "대기 색" color:(color 90 200 255)

	on ckXray changed st do (if isValidNode RA_S.retopo do RA_S.retopo.xray = st)
	on ckFreeze changed st do
	(
		for t in ra_targets() do
		(
			t.showFrozenInGray = false
			if st then freeze t else unfreeze t
		)
	)
	on cpStroke changed c do (RA_S.strokeColor = c; redrawViews())
	on cpPend changed c do (RA_S.pendingColor = c; redrawViews())
	on ckShowPend changed st do (RA_S.showPending = st; redrawViews())
	on ckShowConn changed st do (RA_S.showConnect = st; RA_S.flash = undefined; redrawViews())
)

rollout RA_AdvRO "고급 설정"
(
	radiobuttons rbDensity "밀도 방식" labels:#("엣지 길이", "분할 수", "평균") columns:3 default:1
	spinner spU "가로 분할" range:[1, 200, 6] type:#integer
	spinner spV "세로 분할" range:[1, 200, 6] type:#integer
	spinner spEdge "스트립 분할" range:[1, 500, 8] type:#integer
	spinner spMerge "병합 거리" range:[0, 1e6, 1] type:#worldunits
	spinner spOffset "표면 띄우기" range:[0, 1e5, 0.05] type:#worldunits
	spinner spRelax "이완 반복" range:[0, 50, 3] type:#integer
	checkbox ckRedo "값을 바꾸면 방금 만든 결과에 바로 적용" checked:true
	checkbox ckCrease "꺾이는 곳 교차선에 맞춤" checked:true
	checkbox ckAuto "자동 4버텍스 구멍 채우기" checked:true across:2
	button btnFill4 "지금 채우기" width:80 offset:[20, -2]
	spinner spCreaseR "주름: 합치기 거리" range:[0, 0.49, 0.35] type:#float scale:0.01
	checkbox ckCreaseClosed "주름: 처음·끝 잇기" checked:false
	spinner spScanAngle "스캔: 모서리 각도" range:[5, 170, 35] type:#float fieldwidth:50
	checkbox ckScanDelBack "스캔: 두께 없는 판 뒷면 지우기" checked:true

	on rbDensity changed st do (RA_S.densityMode = st; ra_redoLast())
	on spU changed v do (RA_S.countU = v; if RA_S.densityMode == 2 do ra_redoLast())
	on spV changed v do (RA_S.countV = v; if RA_S.densityMode == 2 do ra_redoLast())
	on spEdge changed v do (RA_S.countEdge = v; if RA_S.densityMode == 2 do ra_redoLast())
	on spMerge changed v do RA_S.mergeDist = v
	on spOffset changed v do RA_S.offset = v
	on spRelax changed v do RA_S.relaxIters = v
	on ckRedo changed st do RA_S.redoOnChange = st
	on ckCrease changed st do RA_S.snapCreases = st
	on ckAuto changed st do (RA_S.autoFill = st; ra_enableAutoFill st)
	on btnFill4 pressed do
	(
		if ra_isPoly RA_S.retopo do
		(
			RA_S.busy = true
			undo "Retopo 4버텍스 채우기" on (ra_fillHoles RA_S.retopo undefined)
			RA_S.busy = false
			redrawViews()
		)
	)
	on spCreaseR changed v do RA_S.creaseRatio = v
	on ckCreaseClosed changed st do RA_S.creaseClosed = st
	on spScanAngle changed v do RA_S.scanAngle = v
	on ckScanDelBack changed st do RA_S.scanDelBack = st
)

rollout RA_KeysRO "단축키"
(
	label k1 "Alt+휠: 방금 만든 결과 밀도" align:#left
	label k2 "Shift+Alt+휠: 방금 만든 스트립 폭" align:#left
	label k3 "그리기 중 Ctrl+Z / Ctrl+Y: 되돌리기 / 다시" align:#left
	label k4 "그 밖의 기능은 Customize > Hotkey Editor" align:#left
	label k5 "  → 카테고리 'RetopoAnnotate' 에서 지정" align:#left
	label k6 "  (영역 · 흐름 · 컷 선, 고르게 재구성, 오프셋," align:#left
	label k7 "   촘촘하게, 성기게, 빈 곳 채우기, 연결, 스캔)" align:#left
)

-- 열려 있는 창의 값들을 현재 설정에 맞춤
fn ra_syncUI =
(
	try
	(
		if RA_Rollout.open do
		(
			RA_Rollout.spSpacing.value = RA_S.spacing
			RA_Rollout.spStripW.value = RA_S.stripWidth
			RA_Rollout.spScanTarget.value = RA_S.scanTarget
			RA_Rollout.ckScanSharp.checked = RA_S.scanSharp
			RA_Rollout.ckScanQuad.checked = RA_S.scanPureQuad
			RA_Rollout.ddMode.selection = RA_S.mode
			if isValidNode RA_S.target do RA_Rollout.pbTarget.text = RA_S.target.name
			local n = (ra_targets()).count
			RA_Rollout.lbTarget.text = if n == 0 then "타겟: 없음" else ("타겟: " + RA_S.targetLabel + "  (" + (n as string) + "개)")
			RA_Rollout.ddLayer.items = ra_layerNames()
		)
		if RA_EditRO.open do
		(
			RA_EditRO.ckRegion.checked = RA_S.nextMode == 7
			RA_EditRO.ckFlow.checked = RA_S.nextMode == 8
			RA_EditRO.ckCut.checked = RA_S.nextMode == 5
		)
		if RA_AdvRO.open do
		(
			RA_AdvRO.rbDensity.state = RA_S.densityMode
			RA_AdvRO.spU.value = RA_S.countU
			RA_AdvRO.spV.value = RA_S.countV
			RA_AdvRO.spEdge.value = RA_S.countEdge
			RA_AdvRO.spMerge.value = RA_S.mergeDist
			RA_AdvRO.spOffset.value = RA_S.offset
			RA_AdvRO.spRelax.value = RA_S.relaxIters
			RA_AdvRO.ckAuto.checked = RA_S.autoFill
			RA_AdvRO.ckCrease.checked = RA_S.snapCreases
			RA_AdvRO.spScanAngle.value = RA_S.scanAngle
			RA_AdvRO.ckScanDelBack.checked = RA_S.scanDelBack
			RA_AdvRO.ckRedo.checked = RA_S.redoOnChange
		)
	)
	catch ()
)

fn ra_openDialog =
(
	try (closeRolloutFloater RA_Floater) catch ()
	try (destroyDialog RA_Rollout) catch ()
	RA_Floater = newRolloutFloater "Retopo Annotate" 272 760
	addRollout RA_Rollout RA_Floater
	addRollout RA_EditRO RA_Floater
	addRollout RA_ViewRO RA_Floater rolledUp:true
	addRollout RA_AdvRO RA_Floater rolledUp:true
	addRollout RA_KeysRO RA_Floater rolledUp:true
	ra_syncUI()
)


fn ra_quadExtrudeSel =
(
	local obj = if selection.count == 1 and ra_isPoly selection[1] then selection[1] else RA_S.retopo
	ra_quadExtrude obj
)

macroScript RetopoAnnotate_Open category:"RetopoAnnotate" buttonText:"Retopo Annotate" tooltip:"리토폴로지 주석 툴 열기"
(
	on execute do ra_openDialog()
)

macroScript RetopoAnnotate_QuadExtrude category:"RetopoAnnotate" buttonText:"Quad Extrude" tooltip:"쿼드 익스트루드 (인접 4버텍스 자동 면)"
(
	on execute do ra_quadExtrudeSel()
)

macroScript RetopoAnnotate_Draw category:"RetopoAnnotate" buttonText:"Draw Strokes" tooltip:"주석 그리기 (우클릭 종료)"
(
	on execute do ra_startDraw()
)

-- 단축키 지정용 (Customize > Hotkey Editor > 카테고리 RetopoAnnotate)
macroScript RetopoAnnotate_RegionStroke category:"RetopoAnnotate" buttonText:"Region Stroke" tooltip:"다음 선: 영역 둘러싸기 (면 선택)"
(
	on execute do ra_armNext 7
)
macroScript RetopoAnnotate_FlowStroke category:"RetopoAnnotate" buttonText:"Flow Stroke" tooltip:"다음 선: 흐름 선 (선택 영역을 그 방향으로 재구성)"
(
	on execute do ra_armNext 8
)
macroScript RetopoAnnotate_CutStroke category:"RetopoAnnotate" buttonText:"Cut Stroke" tooltip:"다음 선: 컷"
(
	on execute do ra_armNext 5
)
macroScript RetopoAnnotate_Rebuild category:"RetopoAnnotate" buttonText:"Rebuild Region" tooltip:"고르게 재구성 (선택 면)"
(
	on execute do ra_doRebuild()
)
macroScript RetopoAnnotate_Offset category:"RetopoAnnotate" buttonText:"Offset Region" tooltip:"오프셋 (선택 면 둘레에 루프 추가)"
(
	on execute do ra_doOffset()
)
macroScript RetopoAnnotate_Denser category:"RetopoAnnotate" buttonText:"Denser" tooltip:"촘촘하게 ×2 (선택 면, 없으면 전체)"
(
	on execute do ra_doDensity 1
)
macroScript RetopoAnnotate_Sparser category:"RetopoAnnotate" buttonText:"Sparser" tooltip:"성기게 ÷2 (선택 면, 없으면 전체)"
(
	on execute do ra_doDensity -1
)
macroScript RetopoAnnotate_FillGap category:"RetopoAnnotate" buttonText:"Fill Gap" tooltip:"빈 곳 채우기 (둘레 경계 버텍스 선택)"
(
	on execute do ra_doFillGap()
)
macroScript RetopoAnnotate_Connect category:"RetopoAnnotate" buttonText:"Connect Pieces" tooltip:"떨어진 메쉬 연결 (가장 가까운 두 조각 / 선택한 두 오브젝트)"
(
	on execute do ra_doConnect()
)
macroScript RetopoAnnotate_Scan category:"RetopoAnnotate" buttonText:"Scan Merge" tooltip:"선택 오브젝트 표면 스캔 → 합친 리토 메쉬"
(
	on execute do ra_doScan()
)

-- 메인 메뉴에 "Retopo" 메뉴 추가 (한 번만)
-- 3ds Max 2025 이상: 새 메뉴 시스템(#cuiRegisterMenus 콜백)으로 "Retopo" 메뉴 등록
-- 647394 = MacroScript 액션 테이블, 액션 ID 형식은 "매크로이름`카테고리"
fn ra_registerMenus2025 =
(
	try
	(
		local mgr = callbacks.notificationParam()
		local bar = mgr.mainMenuBar
		local sub = bar.CreateSubMenu "5f3c1a7e-2b4d-4e8a-9c61-7d2e0b9a4f10" "Retopo"
		sub.CreateAction "5f3c1a7e-2b4d-4e8a-9c61-7d2e0b9a4f11" 647394 "RetopoAnnotate_Open`RetopoAnnotate"
		sub.CreateAction "5f3c1a7e-2b4d-4e8a-9c61-7d2e0b9a4f12" 647394 "RetopoAnnotate_QuadExtrude`RetopoAnnotate"
		sub.CreateAction "5f3c1a7e-2b4d-4e8a-9c61-7d2e0b9a4f13" 647394 "RetopoAnnotate_Draw`RetopoAnnotate"
	)
	catch (format "[RetopoAnnotate] menu(2025+): %\n" (getCurrentException()))
)

fn ra_isMax2025Plus = ((maxVersion())[1] >= 27000)

-- 3ds Max 2024 이하: 메인 메뉴바에 "Retopo" 가 없으면 추가
fn ra_installMenu =
(
	local added = false
	try
	(
		if menuMan != undefined and not (GetQuietMode()) do
		(
			local main = menuMan.getMainMenuBar()
			local inBar = false
			for i = 1 to main.numItems() do
				if (main.getItem i).getTitle() == "Retopo" do inBar = true
			if not inBar do
			(
				local sub = menuMan.findMenu "Retopo"
				if sub == undefined do
				(
					sub = menuMan.createMenu "Retopo"
					sub.addItem (menuMan.createActionItem "RetopoAnnotate_Open" "RetopoAnnotate") -1
					sub.addItem (menuMan.createActionItem "RetopoAnnotate_QuadExtrude" "RetopoAnnotate") -1
					sub.addItem (menuMan.createActionItem "RetopoAnnotate_Draw" "RetopoAnnotate") -1
				)
				main.addItem (menuMan.createSubMenuItem "Retopo" sub) (main.numItems() + 1)
				menuMan.updateMenuBar()
				added = true
			)
		)
	)
	catch (format "[RetopoAnnotate] menu: %\n" (getCurrentException()))
	added
)
if ra_isMax2025Plus() then
(
	callbacks.removeScripts id:#RetopoAnnotateMenu
	callbacks.addScript #cuiRegisterMenus ra_registerMenus2025 id:#RetopoAnnotateMenu
)
else ra_installMenu()

-- 설치 후 첫 실행: 설치 프로그램이 남긴 표시 파일이 있으면 툴 창을 바로 열어 찾기 쉽게 함
fn ra_firstRun =
(
	try
	(
		local flag = (getFilenamePath (getThisScriptFilename())) + "RetopoAnnotate.firstrun"
		if doesFileExist flag and not (GetQuietMode()) do
		(
			deleteFile flag
			ra_openDialog()
		)
	)
	catch ()
)
ra_firstRun()
format "[RetopoAnnotate] loaded — 메뉴: Retopo > Retopo Annotate  (또는 리스너에서 ra_openDialog())\n"
