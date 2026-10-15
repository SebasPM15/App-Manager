import tkinter as tk
import tkinter.font as tkfont

from ui.theme import Colors, Fonts
from ui.widgets import _scale, track_scaling

ROW_HEIGHT = 58
SYMBOL_COLORS = ["#f8b84e", "#6b86a8", "#e55b61", "#63a3e2", "#4ac48a", "#548ddd", "#a28ee8", "#d07fb0"]


class AppList(tk.Canvas):

    def __init__(self, master, on_select, background: str = Colors.PANEL):
        super().__init__(master, bg=background, highlightthickness=0, borderwidth=0, cursor="arrow")
        self._on_select = on_select
        self._items: list[tuple[str, str, str]] = []
        self._selected: str | None = None
        self._hover: int = -1
        self._offset = 0
        self._scale = _scale(master)
        self._row_h = round(ROW_HEIGHT * self._scale)
        self._font_name = tkfont.Font(family=Fonts.FAMILY_PRIMARY, size=-round(Fonts.SIZE_SM * self._scale), weight="bold")
        self._font_pkg = tkfont.Font(family=Fonts.FAMILY_PRIMARY, size=-round(Fonts.SIZE_XS * self._scale))
        self._font_badge = tkfont.Font(family=Fonts.FAMILY_PRIMARY, size=-round(Fonts.SIZE_XS * self._scale))
        self._font_letter = tkfont.Font(family=Fonts.FAMILY_PRIMARY, size=-round(Fonts.SIZE_BASE * self._scale), weight="bold")
        track_scaling(self, self._apply_scaling)
        self._drag_from: int | None = None

        self.bind("<Configure>", lambda e: self._redraw())
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag_from", None))

    def set_items(self, items: list):
        self._items = items
        self._offset = min(self._offset, self._max_offset())
        self._hover = -1
        self._redraw()

    def set_selected(self, package: str | None):
        self._selected = package
        self._redraw()

    def scroll_to(self, package: str):
        for index, item in enumerate(self._items):
            if item[0] == package:
                top = index * self._row_h
                if top < self._offset or top > self._offset + self.winfo_height() - self._row_h:
                    self._offset = min(top, self._max_offset())
                self._redraw()
                return

    def _max_offset(self) -> int:
        return max(0, len(self._items) * self._row_h - self.winfo_height())

    def handle_wheel(self, delta: int) -> bool:
        if self._max_offset() <= 0:
            return False
        self._offset = max(0, min(self._max_offset(), self._offset - int(delta / 120 * self._row_h * 1.5)))
        self._redraw()
        return True

    def _index_at(self, y: int) -> int:
        index = (y + self._offset) // self._row_h
        return index if 0 <= index < len(self._items) else -1

    def _on_motion(self, event):
        index = self._index_at(event.y)
        if index != self._hover:
            self._hover = index
            self.configure(cursor="hand2" if index >= 0 else "arrow")
            self._redraw()

    def _on_leave(self, _event):
        if self._hover != -1:
            self._hover = -1
            self._redraw()

    def _on_click(self, event):
        if event.x >= self.winfo_width() - round(12 * self._scale) and self._items:
            self._drag_from = event.y
            self._drag_to(event.y)
            return
        index = self._index_at(event.y)
        if index >= 0:
            self._on_select(self._items[index][0])

    def _on_drag(self, event):
        if self._drag_from is not None:
            self._drag_to(event.y)

    def _drag_to(self, y: int):
        height = max(1, self.winfo_height())
        self._offset = max(0, min(self._max_offset(), int(y / height * len(self._items) * self._row_h - height / 2)))
        self._redraw()

    @staticmethod
    def symbol_color(pkg: str) -> str:
        return SYMBOL_COLORS[sum(map(ord, pkg)) % len(SYMBOL_COLORS)]

    def _round_rect(self, x1, y1, x2, y2, radius, **kw):
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kw)

    def _apply_scaling(self, scale: float):
        self._scale = scale
        self._row_h = round(ROW_HEIGHT * scale)
        self._font_name.configure(size=-round(Fonts.SIZE_SM * scale))
        self._font_pkg.configure(size=-round(Fonts.SIZE_XS * scale))
        self._font_badge.configure(size=-round(Fonts.SIZE_XS * scale))
        self._font_letter.configure(size=-round(Fonts.SIZE_BASE * scale))
        self._redraw()

    def _redraw(self):
        self.delete("all")
        width, height = self.winfo_width(), self.winfo_height()
        if width < 10 or not self._items:
            return
        s = self._scale
        first = self._offset // self._row_h
        last = min(len(self._items), (self._offset + height) // self._row_h + 2)
        scrollbar_gutter = round(12 * s)

        for index in range(first, last):
            pkg, name, kind = self._items[index]
            top = index * self._row_h - self._offset
            if pkg == self._selected or index == self._hover:
                self._round_rect(round(4 * s), top + round(2 * s), width - scrollbar_gutter, top + self._row_h - round(2 * s), round(6 * s), fill=Colors.ROW_HOVER, outline="")
            self.create_line(round(6 * s), top + self._row_h - 1, width - scrollbar_gutter, top + self._row_h - 1, fill="#1d2c3e")

            sym = round(28 * s)
            sx, sy = round(14 * s), top + (self._row_h - sym) // 2
            self._round_rect(sx, sy, sx + sym, sy + sym, round(7 * s), fill=self.symbol_color(pkg), outline="")
            self.create_text(sx + sym / 2, sy + sym / 2, text=name[:1].upper(), fill="#ffffff", font=self._font_letter)

            text_x = sx + sym + round(12 * s)
            self.create_text(text_x, top + round(14 * s), text=name, anchor="nw", fill=Colors.TEXT, font=self._font_name)
            self.create_text(text_x, top + round(35 * s), text=pkg, anchor="nw", fill="#6f8398", font=self._font_pkg)

            is_system = kind == "Sistema"
            badge_w = self._font_badge.measure(kind) + round(14 * s)
            right = width - scrollbar_gutter - round(10 * s)
            self._round_rect(right - badge_w, top + round(17 * s), right, top + round(41 * s), round(4 * s),
                             fill="#302a49" if is_system else "#1d354e", outline="")
            self.create_text(right - badge_w / 2, top + round(29 * s), text=kind,
                             fill="#b6a1df" if is_system else "#75b5de", font=self._font_badge)

        total = len(self._items) * self._row_h
        if total > height:
            thumb = max(round(24 * s), int(height * height / total))
            y = int(self._offset / (total - height) * (height - thumb))
            x = width - round(6 * s)
            self._round_rect(x - round(2 * s), y, x + round(2 * s), y + thumb, round(2 * s), fill=Colors.LINE_STRONG, outline="")
