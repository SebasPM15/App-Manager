import customtkinter as ctk
from ui.theme import Colors, Fonts, Dims
from ui.icons import icon
from ui.widgets import Label, Box, font, make_panel, make_eyebrow, make_button, make_status_dot

KEY_BACK, KEY_HOME, KEY_RECENTS = 4, 3, 187
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_OK = 19, 20, 21, 22, 23


class RemoteTab(ctk.CTkFrame):

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, fg_color="transparent")
        self._cb = callbacks
        self._wifi_on = True
        self._data_on = True
        self._build()

    def _key(self, keycode: int):
        return lambda: self._cb.get("remote_key", lambda k: None)(keycode)

    def _build(self):
        self.grid_columnconfigure(0, weight=11, uniform="remote")
        self.grid_columnconfigure(1, weight=9, uniform="remote")
        self.grid_rowconfigure(0, weight=1)

        main = make_panel(self)
        main.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(0, weight=1)

        preview = ctk.CTkFrame(main, fg_color="#111f30", corner_radius=Dims.PANEL_RADIUS)
        preview.grid(row=0, column=0, padx=1, pady=(1, 0), sticky="nsew")
        preview.grid_columnconfigure(0, weight=1)
        preview.grid_rowconfigure(1, weight=1)

        top = Box(preview, fg_color="transparent")
        top.grid(row=0, column=0, padx=18, pady=(18, 0), sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.lbl_device = Label(top, text="Sin dispositivo", font=font(Fonts.SIZE_BASE), text_color="#c1d0df", anchor="w")
        self.lbl_device.grid(row=0, column=0, sticky="w")
        pill = ctk.CTkFrame(top, fg_color=Colors.GREEN_DIM, corner_radius=5)
        pill.grid(row=0, column=1)
        self.pill_dot = make_status_dot(pill)
        self.pill_dot.configure(fg_color="transparent")
        self.pill_dot.pack(side="left", padx=(8, 0), pady=4)
        self.pill_text = Label(pill, text="Desconectado", font=font(Fonts.SIZE_XS), text_color="#79d0a4")
        self.pill_text.pack(side="left", padx=(4, 8))

        screen = ctk.CTkFrame(preview, fg_color="#0f1d2d", border_width=1, border_color="#2c4157", corner_radius=8)
        screen.grid(row=1, column=0, padx=18, pady=(17, 18), sticky="nsew")
        screen.grid_columnconfigure(0, weight=1)
        screen.grid_rowconfigure((0, 4), weight=1)
        Label(screen, text="", image=icon("smartphone", 50, "#7ea8d9"), width=54, height=54).grid(row=1, column=0)
        self.lbl_screen_title = Label(screen, text="Control remoto", font=font(Fonts.SIZE_MD, "bold"), text_color="#bdcede")
        self.lbl_screen_title.grid(row=2, column=0, pady=(6, 0))
        self.lbl_screen_hint = Label(screen, text="Selecciona un dispositivo para controlarlo", font=font(Fonts.SIZE_XS), text_color="#71869b")
        self.lbl_screen_hint.grid(row=3, column=0, pady=(6, 0))

        nav = Box(main, fg_color="transparent")
        nav.grid(row=1, column=0, padx=15, pady=15, sticky="ew")
        nav.grid_columnconfigure((0, 1, 2), weight=1, uniform="nav")
        for col, (text, kc, icon_name) in enumerate([("Volver", KEY_BACK, "arrow-left"), ("Inicio", KEY_HOME, "home"), ("Recientes", KEY_RECENTS, "recents")]):
            btn = make_button(nav, text, self._key(kc), height=35, icon_name=icon_name)
            btn.configure(fg_color="#18293d", border_color="#294058")
            btn.grid(row=0, column=col, padx=4, sticky="ew")

        side = Box(self, fg_color="transparent")
        side.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        side.grid_columnconfigure(0, weight=1)

        control = make_panel(side)
        control.grid(row=0, column=0, sticky="ew")
        control.grid_columnconfigure(0, weight=1)
        Label(control, text="Controles del dispositivo", font=font(Fonts.SIZE_MD, "bold"), text_color=Colors.TEXT, anchor="w").grid(
            row=0, column=0, padx=17, pady=(17, 0), sticky="w"
        )

        dpad = Box(control, fg_color="transparent")
        dpad.grid(row=1, column=0, pady=(22, 20))
        pad_style = dict(width=44, height=36, corner_radius=6, fg_color="#20344c", hover_color="#2b4766",
                         border_width=1, border_color="#314e6b", text_color="#b8cce1", font=font(Fonts.SIZE_LG))
        ctk.CTkButton(dpad, text="", image=icon("arrow-up", 16, "#b8cce1"), command=self._key(KEY_UP), **pad_style).grid(row=0, column=1, pady=3)
        ctk.CTkButton(dpad, text="", image=icon("arrow-left", 16, "#b8cce1"), command=self._key(KEY_LEFT), **pad_style).grid(row=1, column=0, padx=3)
        ok_style = dict(pad_style, fg_color="#31557d", hover_color="#3d6593", text_color="#dbe9f8", font=font(Fonts.SIZE_SM))
        ctk.CTkButton(dpad, text="OK", command=self._key(KEY_OK), **ok_style).grid(row=1, column=1, padx=3)
        ctk.CTkButton(dpad, text="", image=icon("arrow-right", 16, "#b8cce1"), command=self._key(KEY_RIGHT), **pad_style).grid(row=1, column=2, padx=3)
        ctk.CTkButton(dpad, text="", image=icon("arrow-down", 16, "#b8cce1"), command=self._key(KEY_DOWN), **pad_style).grid(row=2, column=1, pady=3)

        Box(control, height=1, fg_color="#263a4f").grid(row=2, column=0, padx=17, sticky="ew")
        bright = Box(control, fg_color="transparent")
        bright.grid(row=3, column=0, padx=17, pady=(14, 17), sticky="ew")
        bright.grid_columnconfigure(0, weight=1)
        Label(bright, text="Brillo", font=font(Fonts.SIZE_XS), text_color="#94a6b8", anchor="w").grid(row=0, column=0, sticky="w")
        self.lbl_brightness = Label(bright, text="50%", font=font(Fonts.SIZE_XS), text_color="#c8d7e6", anchor="e")
        self.lbl_brightness.grid(row=0, column=1, sticky="e")
        self.slider = ctk.CTkSlider(
            bright, from_=0, to=255, height=16,
            progress_color="#6f9fe2", button_color="#6f9fe2", button_hover_color="#8ab3ee",
            fg_color=Colors.LINE_STRONG, command=self._on_slider,
        )
        self.slider.set(128)
        self.slider.grid(row=1, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        actions = make_panel(side)
        actions.grid(row=1, column=0, pady=(14, 0), sticky="ew")
        actions.grid_columnconfigure(0, weight=1)
        make_eyebrow(actions, "Acciones rápidas").grid(row=0, column=0, padx=16, pady=(16, 7), sticky="w")

        def add(row: int, text: str, command, kind: str = "secondary", icon_name: str | None = None) -> ctk.CTkButton:
            btn = make_button(actions, text, command, kind=kind, height=35, anchor="w", icon_name=icon_name)
            if kind == "secondary":
                btn.configure(fg_color="#18293d", border_color="#294058", hover_color="#223a57")
            btn.grid(row=row, column=0, padx=16, pady=3, sticky="ew")
            return btn

        add(1, " Ajustes de fecha y hora", lambda: self._cb.get("open_settings", lambda a: None)("android.settings.DATE_SETTINGS"), icon_name="clock")
        add(2, " Sincronizar hora con este equipo", self._cb.get("sync_time", lambda: None), icon_name="sync")
        self.btn_wifi = add(3, " Desactivar WiFi", self._toggle_wifi, icon_name="wifi")
        self.btn_data = add(4, " Desactivar datos móviles", self._toggle_data, icon_name="signal")
        add(5, " Captura de pantalla", self._cb.get("screenshot", lambda: None), icon_name="camera")
        add(6, " Apagar dispositivo", self._cb.get("power_off", lambda: None), kind="danger", icon_name="power").grid_configure(pady=(3, 16))

    def _toggle_wifi(self):
        self._cb.get("set_wifi", lambda v: None)(not self._wifi_on)

    def set_wifi_state(self, enabled: bool):
        self._wifi_on = enabled
        self.btn_wifi.configure(
            text=" Desactivar WiFi" if enabled else " Activar WiFi",
            image=icon("wifi" if enabled else "wifi-off", 15, "#b7c6d7"),
        )

    def _toggle_data(self):
        self._data_on = not self._data_on
        self._cb.get("set_data", lambda v: None)(self._data_on)
        self.btn_data.configure(text=" Desactivar datos móviles" if self._data_on else " Activar datos móviles")

    def _on_slider(self, val: float):
        self.lbl_brightness.configure(text=f"{round(val / 255 * 100)}%")
        self._cb.get("brightness_change", lambda v: None)(val)

    def set_brightness(self, val: int):
        self.slider.set(val)
        self.lbl_brightness.configure(text=f"{round(val / 255 * 100)}%")

    def set_device(self, name: str | None, address: str = ""):
        if name:
            self.lbl_device.configure(text=name)
            self.pill_text.configure(text="En línea")
            self.pill_dot.configure(text_color=Colors.GREEN)
            self.lbl_screen_title.configure(text="Control remoto activo")
            self.lbl_screen_hint.configure(text=f"Usa los controles para interactuar con {address or 'el dispositivo'}")
        else:
            self.lbl_device.configure(text="Sin dispositivo")
            self.pill_text.configure(text="Desconectado")
            self.pill_dot.configure(text_color=Colors.TEXT_DIM)
            self.lbl_screen_title.configure(text="Control remoto")
            self.lbl_screen_hint.configure(text="Selecciona un dispositivo para controlarlo")
