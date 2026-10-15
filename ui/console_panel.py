import tkinter as tk
import customtkinter as ctk
from datetime import datetime
from ui.theme import Colors, Fonts, Dims
from ui.icons import icon
from ui.widgets import Label, Box, font, _scale, _tk_font, track_scaling

LEVEL_COLORS = {
    "INFO": Colors.BLUE,
    "OK":   Colors.GREEN,
    "ERR":  Colors.RED,
}
ERROR_MARKERS = ("error", "fallo", "no encontrado", "no válida", "failed", "unable")
MAX_LINES = 2000
TRIM_LINES = 500


class ConsolePanel(ctk.CTkFrame):

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, fg_color=Colors.CONSOLE, corner_radius=0, height=Dims.CONSOLE_H)
        self.grid_propagate(False)
        self._cb = callbacks
        self._expanded = True
        self._build()

    def _link(self, parent, text: str, command, color: str = Colors.TEXT_MUTED, icon_name: str | None = None) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            image=icon(icon_name, 13, color) if icon_name else None,
            compound="left",
            width=0,
            height=26,
            fg_color="transparent",
            hover_color=Colors.CONSOLE,
            text_color=color,
            font=font(Fonts.SIZE_XS),
            corner_radius=4,
        )

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        Box(self, height=1, fg_color="#263a50").grid(row=0, column=0, sticky="ew")

        header = ctk.CTkFrame(self, fg_color="transparent", height=Dims.CONSOLE_H_BAR - 1, corner_radius=0)
        header.grid(row=1, column=0, sticky="ew", padx=(Dims.PAD_LG, 20))
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        title = Box(header)
        title.grid(row=0, column=0, sticky="w", pady=7)
        self.btn_expand = ctk.CTkButton(
            title, text=" Consola ADB", command=self._toggle_expand,
            image=icon("chevron-down", 14, "#c2cfdd"), compound="left",
            width=0, height=26, fg_color="transparent", hover_color=Colors.CONSOLE,
            text_color="#c2cfdd", font=font(Fonts.SIZE_SM, "bold"),
        )
        self.btn_expand.pack(side="left")
        self.status_chip = Label(
            title, text="Lista", font=font(Fonts.SIZE_XS),
            text_color="#69c398", fg_color=Colors.GREEN_DIM, corner_radius=5, height=20, width=88,
        )
        self.status_chip.pack(side="left", padx=(4, 0))

        controls = Box(header)
        controls.grid(row=0, column=1, sticky="e")

        self.combo_level = ctk.CTkComboBox(
            controls,
            values=["Verbose", "Debug", "Info", "Warning", "Error"],
            width=92, height=24, state="readonly",
            fg_color=Colors.PANEL_DEEP, border_color=Colors.LINE_STRONG,
            button_color=Colors.SECONDARY_HOVER, button_hover_color=Colors.LINE_STRONG,
            dropdown_fg_color=Colors.SURFACE, dropdown_hover_color=Colors.ROW_HOVER,
            text_color=Colors.TEXT_SOFT,
            font=font(Fonts.SIZE_XS), dropdown_font=font(Fonts.SIZE_XS),
            command=self._cb.get("change_log_level", lambda v: None),
        )
        self.combo_level.set("Verbose")
        self.combo_level.pack(side="left", padx=4)

        self.entry_filter = ctk.CTkEntry(
            controls, placeholder_text="Filtrar texto", width=120, height=24,
            fg_color=Colors.PANEL_DEEP, border_color=Colors.LINE_STRONG,
            text_color=Colors.TEXT, placeholder_text_color=Colors.TEXT_DIM,
            font=font(Fonts.SIZE_XS),
        )
        self.entry_filter.pack(side="left", padx=4)

        self.check_filter = ctk.CTkCheckBox(
            controls, text="App seleccionada", height=20, checkbox_width=16, checkbox_height=16,
            fg_color=Colors.PRIMARY, hover_color=Colors.PRIMARY_HOVER, border_color=Colors.LINE_STRONG,
            text_color=Colors.TEXT_MUTED, font=font(Fonts.SIZE_XS),
            command=self._cb.get("toggle_logcat_filter", lambda: None),
        )
        self.check_filter.pack(side="left", padx=8)

        self.btn_logcat = self._link(controls, "Iniciar logcat", self._cb.get("toggle_logcat", lambda: None), icon_name="play")
        self.btn_logcat.pack(side="left", padx=4)
        self._link(controls, "Limpiar", self._cb.get("clear_logs", lambda: None), icon_name="trash").pack(side="left", padx=4)
        self._link(controls, "Guardar", self._cb.get("save_logs", lambda: None), icon_name="download").pack(side="left", padx=4)

        self.body = Box(self)
        self.body.grid(row=2, column=0, sticky="nsew", padx=(Dims.PAD_LG, 20), pady=(0, 10))
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)

        scale = _scale(self)
        self.text_logs = tk.Text(
            self.body,
            state="disabled",
            bg=Colors.CONSOLE,
            fg="#8da1b3",
            font=_tk_font(font(Fonts.SIZE_XS, mono=True), scale),
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            padx=0,
            pady=0,
            cursor="arrow",
            insertwidth=0,
            selectbackground=Colors.BLUE_DIM,
            height=1,
        )
        self.text_logs.grid(row=0, column=0, sticky="nsew")
        track_scaling(self.text_logs, lambda s: self.text_logs.configure(font=_tk_font(font(Fonts.SIZE_XS, mono=True), s)))
        self.text_logs.tag_config("time", foreground="#536b80")
        for level, color in LEVEL_COLORS.items():
            self.text_logs.tag_config(level, foreground=color)

        command_line = Box(self.body)
        command_line.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        command_line.grid_columnconfigure(1, weight=1)
        Box(command_line, height=1, fg_color="#1c2b3c").grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
        Label(command_line, text="$", font=font(Fonts.SIZE_SM, mono=True), text_color="#6fc59b").grid(row=1, column=0)
        self.entry_cmd = ctk.CTkEntry(
            command_line,
            placeholder_text="Escribe un comando ADB...",
            height=24, border_width=0, fg_color=Colors.CONSOLE,
            text_color="#bfcee0", placeholder_text_color=Colors.TEXT_DIM,
            font=font(Fonts.SIZE_XS, mono=True),
        )
        self.entry_cmd.grid(row=1, column=1, sticky="ew", padx=6)
        self.entry_cmd.bind("<Return>", lambda e: self._execute_cmd())
        self._link(command_line, "Ejecutar", self._execute_cmd, color="#79a8df", icon_name="command").grid(row=1, column=2)

    def _execute_cmd(self):
        cmd = self.entry_cmd.get().strip()
        if cmd:
            self._cb.get("execute_cmd", lambda c: None)(cmd)
            self.entry_cmd.delete(0, "end")

    def _toggle_expand(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        if expanded:
            self.configure(height=Dims.CONSOLE_H)
            self.body.grid()
            self.btn_expand.configure(image=icon("chevron-down", 14, "#c2cfdd"))
        else:
            self.body.grid_remove()
            self.configure(height=Dims.CONSOLE_H_BAR)
            self.btn_expand.configure(image=icon("chevron-right", 14, "#c2cfdd"))
        cb = self._cb.get("on_expand_change")
        if cb:
            cb(expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def get_filter_text(self) -> str:
        return self.entry_filter.get().strip().lower()

    def get_log_level_char(self) -> str:
        return self.combo_level.get()[0]

    def is_filter_app_active(self) -> bool:
        return self.check_filter.get() == 1

    def log(self, msg: str, raw: bool = False):
        self.log_batch([(msg, raw)])

    def log_batch(self, entries: list):
        text = self.text_logs
        text.configure(state="normal")
        for msg, raw in entries:
            if raw:
                text.insert("end", msg + "\n")
                continue
            lowered = msg.lower()
            if msg.startswith("$ "):
                level = "INFO"
            elif any(marker in lowered for marker in ERROR_MARKERS):
                level = "ERR"
            else:
                level = "OK"
            text.insert("end", datetime.now().strftime("%H:%M:%S") + "  ", "time")
            text.insert("end", f"{level:<5}", level)
            text.insert("end", f"  {msg}\n")
        if int(text.index("end-1c").split(".")[0]) > MAX_LINES:
            text.delete("1.0", f"{TRIM_LINES}.0")
        text.see("end")
        text.configure(state="disabled")

    def clear(self):
        self.text_logs.configure(state="normal")
        self.text_logs.delete("1.0", "end")
        self.text_logs.configure(state="disabled")

    def get_content(self) -> str:
        return self.text_logs.get("1.0", "end").strip()

    def set_logcat_running(self, running: bool):
        if running:
            self.btn_logcat.configure(text="Detener logcat", text_color=Colors.RED, image=icon("stop", 13, Colors.RED))
            self.status_chip.configure(text="Logcat activo", text_color=Colors.BLUE_BRIGHT, fg_color="#213b5d")
        else:
            self.btn_logcat.configure(text="Iniciar logcat", text_color=Colors.TEXT_MUTED, image=icon("play", 13, Colors.TEXT_MUTED))
            self.status_chip.configure(text="Lista", text_color="#69c398", fg_color=Colors.GREEN_DIM)
