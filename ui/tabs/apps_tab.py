import customtkinter as ctk
from ui.theme import Colors, Fonts, Dims
from ui.icons import icon
from ui.app_list import AppList
from ui.widgets import Label, Box, font, make_panel, make_eyebrow, make_button, make_search_field, bind_click

FILTERS = ["Todas", "Terceros", "Sistema"]


class AppsTab(ctk.CTkFrame):

    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, fg_color="transparent")
        self._cb = callbacks
        self.selected_package: str | None = None
        self._packages: list[str] = []
        self._third_party: set[str] = set()
        self._filter = "Todas"
        self._filter_buttons: dict[str, ctk.CTkButton] = {}
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1, uniform="apps")
        self.grid_columnconfigure(1, weight=1, uniform="apps")
        self.grid_rowconfigure(0, weight=1)

        left = make_panel(self)
        left.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        toolbar = Box(left, fg_color="transparent")
        toolbar.grid(row=0, column=0, padx=16, pady=(16, 0), sticky="ew")
        toolbar.grid_columnconfigure(0, weight=1)

        self.entry_search = make_search_field(toolbar, "Buscar aplicaciones...")
        self.entry_search.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self._render())

        tabs = ctk.CTkFrame(toolbar, fg_color=Colors.PANEL_DEEP, border_width=1, border_color=Colors.LINE_STRONG, corner_radius=6)
        tabs.grid(row=0, column=1)
        for name in FILTERS:
            btn = ctk.CTkButton(
                tabs, text=name, width=0, height=26, corner_radius=4,
                fg_color="transparent", hover_color=Colors.ROW_HOVER,
                text_color="#7e91a5", font=font(Fonts.SIZE_XS),
                command=lambda n=name: self._set_filter(n),
            )
            btn.pack(side="left", padx=2, pady=2)
            self._filter_buttons[name] = btn
        self._style_filters()

        self.lbl_count = Label(left, text="", font=font(Fonts.SIZE_XS), text_color="#72869b", anchor="w")
        self.lbl_count.grid(row=1, column=0, padx=18, pady=(14, 6), sticky="w")

        self.app_list = AppList(left, on_select=lambda p: self._cb.get("select_app", lambda *a: None)(p))
        self.app_list.grid(row=2, column=0, padx=(10, 6), pady=(0, 10), sticky="nsew")

        right = make_panel(self)
        right.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        header = Box(right, fg_color="transparent")
        header.grid(row=0, column=0, padx=22, pady=(22, 0), sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        self.detail_symbol = Label(
            header, text="?", width=43, height=43, corner_radius=7,
            fg_color=Colors.LINE_STRONG, text_color="#ffffff", font=font(Fonts.SIZE_LG, "bold"),
        )
        self.detail_symbol.grid(row=0, column=0, rowspan=2, padx=(0, 13))
        self.lbl_name = Label(header, text="Ninguna aplicación", font=font(Fonts.SIZE_LG, "bold"), text_color=Colors.TEXT, anchor="w")
        self.lbl_name.grid(row=0, column=1, sticky="sw")
        self.lbl_package = Label(header, text="Selecciona una aplicación de la lista", font=font(Fonts.SIZE_XS), text_color="#778ba1", anchor="w")
        self.lbl_package.grid(row=1, column=1, sticky="nw", pady=(4, 0))

        Box(right, height=1, fg_color="#26394d").grid(row=1, column=0, padx=22, pady=(20, 0), sticky="ew")

        fields = Box(right, fg_color="transparent")
        fields.grid(row=2, column=0, padx=22, pady=20, sticky="ew")
        fields.grid_columnconfigure((0, 1, 2), weight=1, uniform="fields")
        self._field_values: dict[str, ctk.CTkLabel] = {}
        for col, (key, label) in enumerate([("version", "Versión"), ("type", "Tipo"), ("state", "Estado")]):
            cell = Box(fields, fg_color="transparent")
            cell.grid(row=0, column=col, sticky="w")
            Label(cell, text=label, font=font(Fonts.SIZE_XS), text_color="#718399", anchor="w").pack(anchor="w")
            value = Label(cell, text="—", font=font(Fonts.SIZE_SM), text_color="#d2deeb", anchor="w")
            value.pack(anchor="w", pady=(6, 0))
            self._field_values[key] = value

        actions = Box(right, fg_color="transparent")
        actions.grid(row=3, column=0, padx=22, sticky="ew")
        actions.grid_columnconfigure((0, 1), weight=1, uniform="actions")
        spec = [
            ("Abrir aplicación",     "primary",   "launch"),
            ("Forzar detención",     "secondary", "force_stop"),
            ("Limpiar y abrir",      "secondary", "clean_start"),
            ("Borrar datos",         "secondary", "clear_data"),
            ("Permiso superposición", "secondary", "grant_overlay"),
            ("Desinstalar",          "danger",    "uninstall"),
        ]
        self._action_btns: list[ctk.CTkButton] = []
        for idx, (text, kind, key) in enumerate(spec):
            btn = make_button(actions, text, self._cb.get(key, lambda: None), kind=kind, state="disabled")
            btn.grid(row=idx // 2, column=idx % 2, padx=(0 if idx % 2 == 0 else 4, 4 if idx % 2 == 0 else 0), pady=4, sticky="ew")
            self._action_btns.append(btn)

        Box(right, height=1, fg_color="#26394d").grid(row=4, column=0, padx=22, pady=(22, 0), sticky="ew")

        install = Box(right, fg_color="transparent")
        install.grid(row=5, column=0, padx=22, pady=(20, 0), sticky="ew")
        install.grid_columnconfigure(1, weight=1)
        Label(
            install, text="", image=icon("upload", 17, "#76a9e7"), width=31, height=31, corner_radius=6,
            fg_color="#203858",
        ).grid(row=0, column=0, rowspan=2, padx=(0, 10))
        Label(install, text="Instalar APK", font=font(Fonts.SIZE_SM, "bold"), text_color=Colors.TEXT, anchor="w").grid(row=0, column=1, sticky="sw")
        Label(install, text="Selecciónalo desde tu equipo", font=font(Fonts.SIZE_XS), text_color="#74889e", anchor="w").grid(row=1, column=1, sticky="nw")
        make_button(install, "Seleccionar APK", self._cb.get("install_apk", lambda: None)).grid(row=0, column=2, rowspan=2, padx=(10, 0))

        self.prog_install = ctk.CTkProgressBar(
            right, height=6, corner_radius=3, mode="determinate",
            fg_color=Colors.LINE_STRONG, progress_color=Colors.BLUE, indeterminate_speed=1.2,
        )
        self.prog_install.grid(row=6, column=0, padx=22, pady=(14, 22), sticky="ew")
        self.prog_install.set(0)

    def _style_filters(self):
        for name, btn in self._filter_buttons.items():
            active = name == self._filter
            btn.configure(
                fg_color="#284467" if active else "transparent",
                text_color="#c8daf0" if active else "#7e91a5",
            )

    def _set_filter(self, name: str):
        self._filter = name
        self._style_filters()
        self._render()

    def get_search_query(self) -> str:
        return self.entry_search.get().strip().lower()

    @staticmethod
    def display_name(pkg: str) -> str:
        skip = {"android", "com", "org", "app", "apps", "mobile", "google"}
        parts = [p for p in pkg.split(".") if p not in skip]
        return (parts[-1] if parts else pkg).replace("_", " ").title()

    def _type_of(self, pkg: str) -> str:
        return "Terceros" if pkg in self._third_party else "Sistema"

    def set_packages(self, pkgs: list, third_party: set):
        self._packages = pkgs
        self._third_party = third_party
        self._render()

    def _render(self):
        query = self.get_search_query()
        items = [
            (p, self.display_name(p), self._type_of(p)) for p in self._packages
            if (not query or query in p.lower() or query in self.display_name(p).lower())
            and (self._filter == "Todas" or self._type_of(p) == self._filter)
        ]
        self.app_list.set_items(items)
        self.lbl_count.configure(text=f"{len(items)} aplicaciones encontradas")

    def set_selected(self, package: str | None, display: str = ""):
        self.selected_package = package

        self.app_list.set_selected(package)
        if package:
            self.app_list.scroll_to(package)

        if package:
            self.lbl_name.configure(text=display or self.display_name(package))
            self.lbl_package.configure(text=package)
            self.detail_symbol.configure(text=self.display_name(package)[:1].upper(), fg_color=AppList.symbol_color(package))
            self._field_values["type"].configure(text=self._type_of(package))
            self._field_values["state"].configure(text="Instalada", text_color=Colors.GREEN)
            self._field_values["version"].configure(text="…")
        else:
            self.lbl_name.configure(text="Ninguna aplicación")
            self.lbl_package.configure(text="Selecciona una aplicación de la lista")
            self.detail_symbol.configure(text="?", fg_color=Colors.LINE_STRONG)
            for key, lbl in self._field_values.items():
                lbl.configure(text="—", text_color="#d2deeb")

        state = "normal" if package else "disabled"
        for btn in self._action_btns:
            btn.configure(state=state)

    def set_version(self, package: str, version: str):
        if package == self.selected_package:
            self._field_values["version"].configure(text=version or "—")

    def set_installing(self, running: bool, ok: bool | None = None):
        if running:
            self.prog_install.configure(mode="indeterminate", progress_color=Colors.BLUE)
            self.prog_install.start()
            return
        self.prog_install.stop()
        self.prog_install.configure(mode="determinate")
        self.prog_install.set(1.0 if ok else 0)
        self.prog_install.configure(progress_color=Colors.GREEN if ok else Colors.RED)

    def clear(self):
        self._packages = []
        self._third_party = set()
        self._render()
        self.set_selected(None)
