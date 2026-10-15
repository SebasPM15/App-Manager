import tkinter as tk

from ui.theme import Colors
from ui.widgets import _scale, track_scaling

GUTTER = 12
THUMB_MIN = 28


class ScrollArea(tk.Frame):

    def __init__(self, master, background: str = Colors.BG):
        super().__init__(master, bg=background, highlightthickness=0, borderwidth=0)
        self._scale = _scale(master)
        self._canvas = tk.Canvas(self, bg=background, highlightthickness=0, borderwidth=0, yscrollincrement=round(24 * self._scale))
        self._canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self._canvas, bg=background, highlightthickness=0, borderwidth=0)
        self._window = self._canvas.create_window(0, 0, window=self.body, anchor="nw")
        self._thumb = tk.Frame(self, bg=Colors.LINE_STRONG, highlightthickness=0, borderwidth=0, cursor="hand2")
        self._drag_origin: tuple[int, float] | None = None

        self._canvas.bind("<Configure>", lambda e: self._layout())
        self.body.bind("<Configure>", lambda e: self._layout())
        self._thumb.bind("<Button-1>", self._start_drag)
        self._thumb.bind("<B1-Motion>", self._drag)
        track_scaling(self, self._apply_scaling)

    def _apply_scaling(self, scale: float):
        self._scale = scale
        self._canvas.configure(yscrollincrement=round(24 * scale))
        self._layout()

    def _overflow(self) -> int:
        return max(0, self.body.winfo_reqheight() - self._canvas.winfo_height())

    def _layout(self):
        width, height = self._canvas.winfo_width(), self._canvas.winfo_height()
        if width < 10 or height < 10:
            return
        required = self.body.winfo_reqheight()
        overflow = required > height
        gutter = round(GUTTER * self._scale) if overflow else 0
        total = max(required, height)
        self._canvas.itemconfigure(self._window, width=max(1, width - gutter), height=total)
        self._canvas.configure(scrollregion=(0, 0, width, total))
        if not overflow:
            self._canvas.yview_moveto(0)
        self._sync_thumb()

    def _sync_thumb(self):
        height = self._canvas.winfo_height()
        first, last = self._canvas.yview()
        if last - first >= 0.999 or height < 10:
            self._thumb.place_forget()
            return
        size = max(round(THUMB_MIN * self._scale), int((last - first) * height))
        top = int(first / max(1e-6, 1 - (last - first)) * (height - size)) if first > 0 else 0
        top = max(0, min(height - size, top))
        width = round(4 * self._scale)
        self._thumb.place(x=self.winfo_width() - width - round(3 * self._scale), y=top, width=width, height=size)

    def handle_wheel(self, delta: int) -> bool:
        first, last = self._canvas.yview()
        if last - first >= 0.999:
            return False
        self._canvas.yview_scroll(int(-delta / 120 * 3), "units")
        self._sync_thumb()
        return True

    def _start_drag(self, event):
        self._drag_origin = (event.y_root, self._canvas.yview()[0])

    def _drag(self, event):
        if self._drag_origin is None:
            return
        height = max(1, self._canvas.winfo_height())
        first, last = self._canvas.yview()
        span = last - first
        start_y, start_first = self._drag_origin
        travel = (event.y_root - start_y) / max(1, height * (1 - span))
        self._canvas.yview_moveto(max(0.0, min(1.0 - span, start_first + travel * (1 - span))))
        self._sync_thumb()
