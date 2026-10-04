bl_info = {
    "name": "Korean IME Helper (한글 입력 도우미)",
    "author": "RetopoAnnotate",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "3D 뷰 > 사이드바(N) > 한글입력 탭",
    "description": "블렌더 자체 텍스트 입력창의 한글 조합(IME) 문제를 우회 - 두벌식 자모를 직접 조합해 완성형 한글을 만들고 클립보드로 전달",
    "category": "Interface",
}

import glob
import os

import bpy
from bpy.props import StringProperty

# ---------------------------------------------------------------------------
# 두벌식(2-beolsik) 한글 자모 조합 엔진
#
# 블렌더 UI의 기본 텍스트 입력창(uiBut)은 플랫폼에 따라 한글 IME 조합
# (자모가 완성형으로 합쳐지는 과정)을 제대로 받지 못하는 경우가 있다.
# 이 모듈은 OS IME에 의존하지 않고, 물리 키 입력(표준 두벌식 배열)을
# 직접 받아 유니코드 한글 완성형 문자를 조합한다.
# ---------------------------------------------------------------------------

CHO = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
       'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

JUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ',
        'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']

JONG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ',
        'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
        'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

JUNG_COMBOS = {
    ('ㅗ', 'ㅏ'): 'ㅘ', ('ㅗ', 'ㅐ'): 'ㅙ', ('ㅗ', 'ㅣ'): 'ㅚ',
    ('ㅜ', 'ㅓ'): 'ㅝ', ('ㅜ', 'ㅔ'): 'ㅞ', ('ㅜ', 'ㅣ'): 'ㅟ',
    ('ㅡ', 'ㅣ'): 'ㅢ',
}

JONG_COMBOS = {
    ('ㄱ', 'ㅅ'): 'ㄳ', ('ㄴ', 'ㅈ'): 'ㄵ', ('ㄴ', 'ㅎ'): 'ㄶ',
    ('ㄹ', 'ㄱ'): 'ㄺ', ('ㄹ', 'ㅁ'): 'ㄻ', ('ㄹ', 'ㅂ'): 'ㄼ',
    ('ㄹ', 'ㅅ'): 'ㄽ', ('ㄹ', 'ㅌ'): 'ㄾ', ('ㄹ', 'ㅍ'): 'ㄿ',
    ('ㄹ', 'ㅎ'): 'ㅀ', ('ㅂ', 'ㅅ'): 'ㅄ',
}
JONG_SPLIT = {v: k for k, v in JONG_COMBOS.items()}

NOT_FINAL = {'ㄸ', 'ㅃ', 'ㅉ'}

# 표준 두벌식(KS X 5002) 키 배열: 키 -> (기본 자모, Shift 자모, 종류 'C'/'V')
DUBEOLSIK = {
    'Q': ('ㅂ', 'ㅃ', 'C'), 'W': ('ㅈ', 'ㅉ', 'C'), 'E': ('ㄷ', 'ㄸ', 'C'),
    'R': ('ㄱ', 'ㄲ', 'C'), 'T': ('ㅅ', 'ㅆ', 'C'),
    'Y': ('ㅛ', 'ㅛ', 'V'), 'U': ('ㅕ', 'ㅕ', 'V'), 'I': ('ㅑ', 'ㅑ', 'V'),
    'O': ('ㅐ', 'ㅒ', 'V'), 'P': ('ㅔ', 'ㅖ', 'V'),
    'A': ('ㅁ', 'ㅁ', 'C'), 'S': ('ㄴ', 'ㄴ', 'C'), 'D': ('ㅇ', 'ㅇ', 'C'),
    'F': ('ㄹ', 'ㄹ', 'C'), 'G': ('ㅎ', 'ㅎ', 'C'),
    'H': ('ㅗ', 'ㅗ', 'V'), 'J': ('ㅓ', 'ㅓ', 'V'), 'K': ('ㅏ', 'ㅏ', 'V'),
    'L': ('ㅣ', 'ㅣ', 'V'),
    'Z': ('ㅋ', 'ㅋ', 'C'), 'X': ('ㅌ', 'ㅌ', 'C'), 'C': ('ㅊ', 'ㅊ', 'C'),
    'V': ('ㅍ', 'ㅍ', 'C'), 'B': ('ㅠ', 'ㅠ', 'V'), 'N': ('ㅜ', 'ㅜ', 'V'),
    'M': ('ㅡ', 'ㅡ', 'V'),
}


def key_to_jamo(key, shift):
    """이벤트 key(예: 'R') -> (자모, 'C'/'V') 또는 매핑 없으면 None."""
    entry = DUBEOLSIK.get(key)
    if entry is None:
        return None
    base, shifted, kind = entry
    return (shifted if shift else base), kind


class HangulComposer:
    """두벌식 키 입력 시퀀스를 완성형 한글 문자열로 조합한다."""

    def __init__(self):
        self.keys = []  # [('C'|'V'|'RAW', char), ...]

    def clear(self):
        self.keys = []

    def push_jamo(self, kind, ch):
        self.keys.append((kind, ch))

    def push_raw(self, ch):
        self.keys.append(('RAW', ch))

    def backspace(self):
        if self.keys:
            self.keys.pop()

    def is_empty(self):
        return not self.keys

    def text(self):
        return self._compose(self.keys)

    @staticmethod
    def _compose(keys):
        blocks = []

        def new_block():
            blocks.append({'cho': None, 'jung': None, 'jong': None})

        for kind, ch in keys:
            if kind == 'RAW':
                blocks.append({'raw': ch})
                continue

            cur = blocks[-1] if blocks else None
            if cur is None or 'raw' in cur:
                if kind == 'C':
                    new_block()
                    blocks[-1]['cho'] = ch
                else:
                    blocks.append({'raw': ch})
                continue

            if kind == 'C':
                if cur['cho'] is None:
                    cur['cho'] = ch
                elif cur['jung'] is None:
                    # 모음 없이 자음이 연속 -> 앞 자음은 낱자로 확정
                    blocks[-1] = {'raw': cur['cho']}
                    new_block()
                    blocks[-1]['cho'] = ch
                elif cur['jong'] is None:
                    if ch in NOT_FINAL:
                        new_block()
                        blocks[-1]['cho'] = ch
                    else:
                        cur['jong'] = ch
                else:
                    combo = JONG_COMBOS.get((cur['jong'], ch))
                    if combo:
                        cur['jong'] = combo
                    else:
                        new_block()
                        blocks[-1]['cho'] = ch
            else:  # kind == 'V'
                if cur['jung'] is None:
                    cur['jung'] = ch
                elif cur['jong'] is None:
                    combo = JUNG_COMBOS.get((cur['jung'], ch))
                    if combo:
                        cur['jung'] = combo
                    else:
                        blocks.append({'raw': ch})
                else:
                    jong = cur['jong']
                    if jong in JONG_SPLIT:
                        remain, pulled = JONG_SPLIT[jong]
                        cur['jong'] = remain
                    else:
                        pulled = jong
                        cur['jong'] = None
                    new_block()
                    blocks[-1]['cho'] = pulled
                    blocks[-1]['jung'] = ch

        out = []
        for b in blocks:
            if 'raw' in b:
                out.append(b['raw'])
            elif b['jung'] is None:
                out.append(b['cho'])
            else:
                cho_i = CHO.index(b['cho'])
                jung_i = JUNG.index(b['jung'])
                jong_i = JONG.index(b['jong'] or '')
                out.append(chr(0xAC00 + (cho_i * 21 + jung_i) * 28 + jong_i))
        return ''.join(out)


# ---------------------------------------------------------------------------
# 한글 지원 폰트 자동 탐색 (3D 텍스트 오브젝트용)
# ---------------------------------------------------------------------------

_FONT_DIRS = [
    "C:/Windows/Fonts",
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    "/Library/Fonts", os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
]

_FONT_NAME_HINTS = [
    "malgun", "nanumgothic", "nanum", "notosanskr", "notosanscjk",
    "notosanscjkkr", "applesdgothicneo", "applegothic", "batang", "gulim",
    "dotum", "undotum", "unbatang", "pretendard", "spoqahansans", "spoqa",
]


def find_korean_font():
    """시스템에서 한글 글리프를 포함할 가능성이 높은 폰트 파일 경로를 찾는다."""
    for base in _FONT_DIRS:
        if not os.path.isdir(base):
            continue
        for path in glob.glob(os.path.join(base, "**", "*"), recursive=True):
            name = os.path.basename(path).lower()
            if not name.endswith((".ttf", ".ttc", ".otf")):
                continue
            if any(hint in name for hint in _FONT_NAME_HINTS):
                return path
    return None


def apply_korean_font(text_curve):
    path = find_korean_font()
    if not path:
        return False
    try:
        font = bpy.data.fonts.load(path, check_existing=True)
    except RuntimeError:
        return False
    text_curve.font = font
    return True


# ---------------------------------------------------------------------------
# 모달 오퍼레이터 - 두벌식 한글 입력창
# ---------------------------------------------------------------------------

_HELP_LINES = (
    "두벌식 키보드 배열로 입력하세요",
    "Enter: 완성 (클립보드로 복사) / Esc: 취소",
    "Back Space: 한 키 지우기 / Tab: 한글-영문 전환",
)


class KOREAN_OT_input_popup(bpy.types.Operator):
    bl_idname = "wm.korean_input_popup"
    bl_label = "한글 입력"
    bl_description = "두벌식 자모 조합으로 한글을 입력하고 클립보드에 복사합니다"
    bl_options = {'REGISTER'}

    target: StringProperty(default='CLIPBOARD')

    _handle = None

    def invoke(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self.report({'ERROR'}, "3D 뷰포트에서 실행해주세요")
            return {'CANCELLED'}

        self.composer = HangulComposer()
        self.korean_mode = True
        self.area = context.area
        self.area.tag_redraw()

        KOREAN_OT_input_popup._handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw, (context,), 'WINDOW', 'POST_PIXEL')

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _draw(self, context):
        import blf

        text = self.composer.text()
        mode = "한" if self.korean_mode else "EN"
        lines = [f"[{mode}] {text}_"] + list(_HELP_LINES)

        x, y = 20, 20 + 20 * len(lines)
        font_id = 0
        for i, line in enumerate(lines):
            blf.size(font_id, 18 if i == 0 else 13)
            blf.color(font_id, 1.0, 0.9, 0.2, 1.0) if i == 0 else blf.color(font_id, 1.0, 1.0, 1.0, 0.7)
            blf.position(font_id, x, y - i * 20, 0)
            blf.draw(font_id, line)

    def _finish(self, context, cancelled):
        bpy.types.SpaceView3D.draw_handler_remove(KOREAN_OT_input_popup._handle, 'WINDOW')
        KOREAN_OT_input_popup._handle = None
        context.area.tag_redraw()
        if cancelled:
            return {'CANCELLED'}

        text = self.composer.text()
        context.window_manager.clipboard = text
        self.on_confirm(context, text)
        return {'FINISHED'}

    def on_confirm(self, context, text):
        if text:
            self.report({'INFO'}, f"클립보드에 복사됨: {text}")
        else:
            self.report({'INFO'}, "입력된 텍스트가 없습니다")

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.value != 'PRESS':
            return {'RUNNING_MODAL'}

        if event.type == 'ESC':
            return self._finish(context, cancelled=True)

        if event.type in {'RET', 'NUMPAD_ENTER'}:
            return self._finish(context, cancelled=False)

        if event.type == 'BACK_SPACE':
            self.composer.backspace()
            return {'RUNNING_MODAL'}

        if event.type == 'TAB':
            self.korean_mode = not self.korean_mode
            return {'RUNNING_MODAL'}

        if event.type == 'SPACE':
            self.composer.push_raw(' ')
            return {'RUNNING_MODAL'}

        if self.korean_mode and event.type in DUBEOLSIK:
            jamo, kind = key_to_jamo(event.type, event.shift)
            self.composer.push_jamo(kind, jamo)
            return {'RUNNING_MODAL'}

        if event.ascii:
            self.composer.push_raw(event.ascii)
            return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}


class KOREAN_OT_rename_active(KOREAN_OT_input_popup):
    bl_idname = "object.korean_rename"
    bl_label = "한글로 이름 변경"
    bl_description = "두벌식으로 입력한 한글로 선택한 오브젝트의 이름을 변경합니다"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def on_confirm(self, context, text):
        if text and context.active_object:
            context.active_object.name = text
            self.report({'INFO'}, f"이름 변경: {text}")
        else:
            self.report({'WARNING'}, "변경할 텍스트가 없습니다")


class KOREAN_OT_create_text_object(KOREAN_OT_input_popup):
    bl_idname = "object.korean_text_object"
    bl_label = "한글 3D 텍스트 만들기"
    bl_description = "두벌식으로 입력한 한글로 3D 텍스트 오브젝트를 만들고 한글 폰트를 자동 적용합니다"

    def on_confirm(self, context, text):
        if not text:
            self.report({'WARNING'}, "입력된 텍스트가 없습니다")
            return
        curve = bpy.data.curves.new(name="KoreanText", type='FONT')
        curve.body = text
        obj = bpy.data.objects.new(name="KoreanText", object_data=curve)
        context.collection.objects.link(obj)
        for o in context.selected_objects:
            o.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        if apply_korean_font(curve):
            self.report({'INFO'}, f"3D 텍스트 생성 및 한글 폰트 적용: {text}")
        else:
            self.report({'WARNING'}, f"3D 텍스트 생성됨 (한글 폰트를 찾지 못해 기본 폰트 사용): {text}")


# ---------------------------------------------------------------------------
# 사이드바 패널
# ---------------------------------------------------------------------------

class KOREAN_PT_panel(bpy.types.Panel):
    bl_label = "한글 입력"
    bl_idname = "KOREAN_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "한글입력"

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("wm.korean_input_popup", text="한글 입력창 열기", icon='OUTLINER_DATA_FONT')
        col.operator("object.korean_rename", text="선택 오브젝트 이름 변경", icon='GREASEPENCIL')
        col.operator("object.korean_text_object", text="3D 텍스트 만들기", icon='FONT_DATA')

        box = layout.box()
        col = box.column(align=True)
        col.scale_y = 0.8
        col.label(text="사용법: 표준 두벌식 배열로 입력")
        for line in _HELP_LINES:
            col.label(text=line)
        col.label(text="※ 입력창은 OS IME를 거치지 않으므로")
        col.label(text="  블렌더 자체 한글 조합 문제와 무관하게 동작합니다")


# ---------------------------------------------------------------------------
# 등록
# ---------------------------------------------------------------------------

classes = (
    KOREAN_OT_input_popup,
    KOREAN_OT_rename_active,
    KOREAN_OT_create_text_object,
    KOREAN_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
