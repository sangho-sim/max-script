# -*- coding: utf-8 -*-
"""한글 프롬프트 -> (레시피, 파라미터 값) 해석.

bpy 에 의존하지 않는다. 순서:
1. 레시피 별칭 완전 일치 (공백 무시, 가장 긴 별칭 우선, 겹치지 않게 여러 개)
2. 없으면 자모 단위 유사도로 오타 허용 ("문어다라" -> 문어다리)
3. 숫자+단위 ("다리 6개", "여섯 개", "3m") 와 형용사 ("길게", "굵게") 를 파라미터에 반영
"""

import difflib
import re

from .recipes.base import GENERATE, ATTACH, MODIFY

_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_JONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

# 오타로 보고 자동으로 받아들이는 최소 유사도 / 후보로 보여주는 최소 유사도
AUTO_FUZZY = 0.8
SUGGEST_FUZZY = 0.6

# 형용사 -> (파라미터 역할, 배율)
ADJECTIVES = [
    (("길게", "길쭉", "기다란", "길다란", "긴"), "length", 1.6),
    (("짧게", "짧은", "짤막"), "length", 0.6),
    (("굵게", "굵은", "두껍게", "두꺼운", "통통", "뚱뚱"), "thickness", 1.6),
    (("얇게", "얇은", "가늘게", "가느다란", "가는"), "thickness", 0.6),
    (("많이", "많은", "빽빽", "촘촘", "잔뜩", "무성"), "count", 2.0),
    (("적게", "적은", "드문드문", "듬성듬성"), "count", 0.5),
    (("크게", "커다란", "큰", "거대", "대형"), "size", 1.6),
    (("작게", "작은", "조그만", "미니"), "size", 0.6),
    (("꼬불꼬불", "구불구불", "꿈틀", "거칠게", "거친", "심하게", "강하게", "세게"), "wiggle", 2.0),
    (("잔잔", "살짝", "약하게", "얌전"), "wiggle", 0.4),
    (("돌돌", "말린", "꼬인", "감긴", "말려"), "curl", 1.8),
]

_NATIVE_NUMBERS = [
    ("스물", 20), ("스무", 20), ("열하나", 11), ("열한", 11), ("열둘", 12), ("열두", 12),
    ("하나", 1), ("한", 1), ("둘", 2), ("두", 2), ("셋", 3), ("세", 3), ("넷", 4), ("네", 4),
    ("다섯", 5), ("여섯", 6), ("일곱", 7), ("여덟", 8), ("아홉", 9), ("열", 10),
]
# 숫자 뒤에 오면 숫자로 보는 단위 (고유어 수사는 단위가 있을 때만 숫자로 본다)
_ANY_UNIT = ("개", "가닥", "줄기", "줄", "바퀴", "번", "회전", "고리", "마디", "m", "미터", "다리")


def _jamo(text):
    out = []
    for ch in text:
        code = ord(ch) - 0xAC00
        if 0 <= code < 11172:
            out.append(_CHO[code // 588])
            out.append(_JUNG[(code % 588) // 28])
            if code % 28:
                out.append(_JONG[code % 28])
        else:
            out.append(ch)
    return "".join(out)


def compact(text):
    return re.sub(r"[\s\.,!?~'\"()\[\]{}:;/+\-_]+", "", text.lower())


class Match:
    def __init__(self, recipe, values, alias, span, fuzzy_from=None):
        self.recipe = recipe
        self.values = values
        self.alias = alias
        self.span = span
        self.fuzzy_from = fuzzy_from


class ParseResult:
    def __init__(self):
        self.matches = []       # 실행할 레시피들 (첫 번째가 기반, 나머지는 MODIFY 체인)
        self.suggestions = []   # 확신이 없을 때 보여줄 후보 레시피
        self.notes = []         # 사용자에게 보여줄 해석 메모


def _exact_matches(text, recipes):
    candidates = []
    for recipe in recipes:
        for alias in recipe.aliases:
            key = compact(alias)
            if not key:
                continue
            start = text.find(key)
            while start != -1:
                candidates.append((len(key), -start, recipe, alias, (start, start + len(key))))
                start = text.find(key, start + 1)
    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    taken, used, chosen = [], set(), []
    for _score, _neg, recipe, alias, span in candidates:
        if recipe.id in used:
            continue
        if any(span[0] < e and s < span[1] for s, e in taken):
            continue
        taken.append(span)
        used.add(recipe.id)
        chosen.append((recipe, alias, span))
    chosen.sort(key=lambda c: c[2][0])
    return chosen


def _fuzzy_scores(text, recipes):
    """레시피별 최고 자모 유사도 [(score, recipe, alias, span)] 높은 순."""
    best = {}
    for recipe in recipes:
        for alias in recipe.aliases:
            key = compact(alias)
            if len(key) < 2:
                continue
            key_j = _jamo(key)
            for width in (len(key) - 1, len(key), len(key) + 1):
                if width < 2 or width > len(text):
                    continue
                for start in range(0, len(text) - width + 1):
                    window = text[start:start + width]
                    score = difflib.SequenceMatcher(None, key_j, _jamo(window)).ratio()
                    if score > best.get(recipe.id, (0,))[0]:
                        best[recipe.id] = (score, recipe, alias, (start, start + width))
    return sorted(best.values(), key=lambda b: b[0], reverse=True)


def _numbers(prompt):
    """[(값, 단위)] — 단위는 숫자 바로 뒤 글자들 (없으면 '')."""
    found = []
    text = prompt.lower()
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*([a-z가-힣]*)", text):
        found.append((float(m.group(1)), m.group(2), m.span()))
    for word, value in _NATIVE_NUMBERS:
        for m in re.finditer(r"(?<![가-힣])" + word + r"\s*(" + "|".join(_ANY_UNIT) + ")", text):
            if not any(s <= m.start() < e for _v, _u, (s, e) in found):
                found.append((float(value), m.group(1), m.span()))
    return found


def _apply_numbers(prompt, matches, notes):
    numbers = _numbers(prompt)
    bare = [n for n in numbers if not any(n[1].startswith(u) for u in _ANY_UNIT)]
    for value, unit, _span in numbers:
        if not unit or not any(unit.startswith(u) for u in _ANY_UNIT):
            continue
        for match in matches:
            param = next((p for p in match.recipe.params if any(unit.startswith(u) for u in p.units)), None)
            if param is not None:
                match.values[param.key] = param.clamp(value)
                notes.append("{} {}".format(param.label, match.values[param.key]))
                break
    # 단위 없는 숫자가 하나뿐이면 첫 레시피의 개수 역할 파라미터로
    if len(bare) == 1 and matches:
        param = next((p for p in matches[0].recipe.params if p.role == "count"), None)
        if param is not None:
            matches[0].values[param.key] = param.clamp(bare[0][0])
            notes.append("{} {}".format(param.label, matches[0].values[param.key]))


def _apply_adjectives(prompt, text_wo_alias, matches, notes):
    tokens = prompt.lower().split()
    for forms, role, factor in ADJECTIVES:
        hit = None
        for form in forms:
            if len(form) >= 2 and form in text_wo_alias:
                hit = form
            elif len(form) == 1 and any(t == form or (t.startswith(form) and len(t) <= 2) for t in tokens):
                hit = form
            if hit:
                break
        if not hit:
            continue
        for match in matches:
            param = next((p for p in match.recipe.params if p.role == role), None)
            if param is None:
                continue
            match.values[param.key] = param.clamp(match.values[param.key] * factor)
            notes.append("'{}' -> {} {}".format(hit, param.label, match.values[param.key]))
            break


def parse(prompt, recipes):
    result = ParseResult()
    text = compact(prompt)
    if not text:
        return result

    chosen = _exact_matches(text, recipes)
    fuzzy_from = None
    if not chosen:
        scores = _fuzzy_scores(text, recipes)
        top = [s for s in scores if s[0] >= SUGGEST_FUZZY]
        # 두 글자 별칭은 한 자모만 달라도 엉뚱한 단어("잔치"->"잔디")라서 자동으로 받지 않고 후보로만
        if (top and top[0][0] >= AUTO_FUZZY and len(compact(top[0][2])) >= 3
                and (len(top) == 1 or top[0][0] - top[1][0] >= 0.08)):
            score, recipe, alias, span = top[0]
            fuzzy_from = text[span[0]:span[1]]
            chosen = [(recipe, alias, span)]
            result.notes.append("'{}' 를 '{}' 로 이해했어요".format(fuzzy_from, recipe.name))
        else:
            result.suggestions = [s[1] for s in top[:3]]
            if not result.suggestions:
                result.suggestions = [s[1] for s in scores[:3] if s[0] > 0.3]
            return result

    # 기반(GENERATE/ATTACH) 레시피는 하나만, 나머지 MODIFY 는 순서대로 체인
    base = [c for c in chosen if c[0].kind in (GENERATE, ATTACH)]
    mods = [c for c in chosen if c[0].kind == MODIFY]
    if len(base) > 1:
        result.notes.append("'{}' 만 만들고 '{}' 은 건너뛰었어요".format(
            base[0][0].name, ", ".join(c[0].name for c in base[1:])))
    ordered = base[:1] + mods
    for recipe, alias, span in ordered:
        result.matches.append(Match(recipe, recipe.defaults(), alias, span, fuzzy_from))

    remaining = text
    for _r, _a, (s, e) in sorted(chosen, key=lambda c: c[2][0], reverse=True):
        remaining = remaining[:s] + " " + remaining[e:]
    _apply_numbers(prompt, result.matches, result.notes)
    _apply_adjectives(prompt, remaining, result.matches, result.notes)
    return result
