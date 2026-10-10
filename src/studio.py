"""Native Boot Studio: English/German editor with the modern native animation."""

import argparse
import copy
import json
import os
from pathlib import Path
import queue
import re
import tempfile
import threading
import time

import native_boot_color as backend
from native_extension import defaults, profile_preset, validate, MATERIAL_NAMES, TEXT_NAMES
from editor_model import History, TARGET_LABELS, COLOR_KEYS, themed, parse_hex
from editor_model import project, read_project, save_project
from scene import extract, render_view, hexcolor
import palettes
import native_preview
import user_presets
from i18n import locale, t, load_preferences, save_preferences

VERSION = "4.2.2"
COLORS = {
    "bg": "#101216",
    "panel": "#191c22",
    "field": "#242830",
    "line": "#343944",
    "text": "#edf0f5",
    "muted": "#a3aab8",
    "accent": "#3989ff",
    "green": "#61d9ad",
}


def read_source(source, tool):
    source, tool = Path(source), Path(tool)
    original = source.read_bytes()
    with tempfile.TemporaryDirectory(prefix="boot-studio-preview-") as tmp:
        tmp = Path(tmp)
        copied, unpacked = tmp / "input.xex", tmp / "unpacked.xex"
        copied.write_bytes(original)
        backend.run_tool(tool, "-e", "u", "-c", "u", "-o", unpacked, copied)
        raw = unpacked.read_bytes()
        _, image = backend.read_uncompressed(raw)
        backend.verify_hook_pages(raw)
        model = extract(image)
    return model, {
        "source_sha256": backend.sha(original),
        "image_sha256": backend.sha(image),
        "animation": "modern",
        "_preview_xex": raw,
        "vertices": sum(len(v) for v, _ in model[0]),
        "text_vertices": sum(len(v) for v, _ in model[1]),
    }


def read_scene(source, tool):
    return read_source(source, tool)[0]


def path_get(profile, path):
    value = profile
    for item in path:
        value = value[item]
    return value


def path_set(profile, path, value):
    node = profile
    for item in path[:-1]:
        node = node[item]
    node[path[-1]] = value


class Studio:
    def __init__(self, root):
        locale.install()
        import tkinter as tk
        from tkinter import ttk

        self.tk, self.ttk, self.root = tk, ttk, root
        self.history = History(profile_preset("blue", backend.preset("blue")))
        self.events = queue.Queue()
        self.render_jobs = queue.Queue(maxsize=1)
        self.scene = None
        self.metadata = None
        self.verified_identity = None
        self.load_token = 0
        self.view_revision = 0
        self.render_serial = 0
        self.last_render_key = None
        self.busy = False
        self.loading = False
        self.updating = False
        self.playing = False
        self.closed = False
        self.last_time = time.monotonic()
        self.project_path = None
        self.saved_state = None
        self.last_output = None
        self.swatches = []
        self.sliders = {}
        self.slider_labels = {}
        self.gallery = None
        self.gallery_token = 0
        self.gallery_cards = {}
        self.preset_store = user_presets.Store()
        self.user_records, self.user_errors = self.preset_store.list()
        self.library = None
        self.library_tree = None
        self.preview_info = False
        self.auto_gpu = False
        self.gpu = native_preview.Session()
        self.gpu_mode = False
        self.gpu_token = 0
        self.gpu_key = None
        self.gpu_deadline = 0.0
        self.gpu_preparing = False
        preferences = load_preferences()
        self.source = locale.RawStringVar(
            value=os.environ.get(
                "NBS_BOOTANIM", preferences.get("source", str(backend.DEFAULT_INPUT))
            )
        )
        self.tool = locale.RawStringVar(
            value=os.environ.get(
                "NBS_XEXTOOL", preferences.get("xextool", str(backend.find_tool()))
            )
        )
        self.xenia = locale.RawStringVar(value=str(self.gpu.executable))
        self.source_display = locale.RawStringVar()
        self.tool_display = locale.RawStringVar()
        self.xenia_display = locale.RawStringVar()
        self.update_file_labels()
        for variable in (self.source, self.tool, self.xenia):
            variable.trace_add("write", self.update_file_labels)
        self.language = locale.RawStringVar(
            value="English" if locale.language == "en" else "Deutsch"
        )
        self.target = tk.StringVar(value=next(iter(TARGET_LABELS)))
        self.status = tk.StringVar(value="Originaldatei wird geprüft …")
        self.source_status = tk.StringVar(value="Originaldatei noch nicht geprüft")
        self.target_note = tk.StringVar()
        self.timeline = tk.DoubleVar(value=7.0)
        self.mode = tk.StringVar(value="Gesamtbild")
        self.compare = tk.BooleanVar(value=False)
        self.dark = tk.BooleanVar(value=False)
        self.zoom = tk.DoubleVar(value=1.0)
        self.orbit = tk.DoubleVar(value=0.0)
        self.phase = tk.StringVar(value="Modellansicht")
        self.color_summary = tk.StringVar()
        self.setup_style()
        self.build()
        self.refresh()
        self.saved_state = self.document()
        self.refresh()
        for variable in (self.source, self.tool):
            variable.trace_add("write", self.files_changed)
        self.target.trace_add("write", self.target_changed)
        for variable in (self.mode, self.compare, self.dark, self.zoom, self.orbit):
            variable.trace_add("write", self.invalidate)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        for key, callback in [
            ("<Control-z>", self.undo),
            ("<Control-y>", self.redo),
            ("<Control-s>", self.save),
            ("<Control-o>", self.open_project),
        ]:
            self.root.bind(key, lambda event, fn=callback: fn())
        threading.Thread(target=self.render_worker, daemon=True).start()
        self.root.after(50, self.poll)

    @property
    def profile(self):
        return self.history.profile

    def setup_style(self):
        root = self.root
        root.title(f"Native Boot Studio {VERSION}")
        root.geometry("1440x940")
        root.minsize(1080, 740)
        root.configure(bg=COLORS["bg"])
        style = self.ttk.Style(root)
        style.theme_use("clam")
        for name in ("TFrame", "TLabel", "TLabelframe", "TLabelframe.Label"):
            style.configure(
                name, background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI", 10)
            )
        style.configure("Root.TFrame", background=COLORS["bg"])
        style.configure("Root.TLabel", background=COLORS["bg"])
        style.configure("Muted.TLabel", foreground=COLORS["muted"])
        style.configure(
            "Subtle.TButton",
            background=COLORS["panel"],
            foreground=COLORS["muted"],
            padding=(10, 7),
        )
        style.map(
            "Subtle.TButton",
            background=[("active", COLORS["field"])],
            foreground=[("active", COLORS["text"])],
        )
        style.configure(
            "Treeview",
            background=COLORS["panel"],
            fieldbackground=COLORS["panel"],
            foreground=COLORS["text"],
            rowheight=40,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure(
            "Treeview.Heading",
            background=COLORS["field"],
            foreground=COLORS["muted"],
            relief="flat",
            font=("Segoe UI", 9),
            padding=10,
        )
        style.map(
            "Treeview", background=[("selected", "#263b59")], foreground=[("selected", "white")]
        )
        style.configure(
            "TButton",
            background=COLORS["field"],
            foreground=COLORS["text"],
            borderwidth=0,
            padding=(12, 8),
            font=("Segoe UI", 10),
        )
        style.map(
            "TButton",
            background=[("active", "#343b48"), ("disabled", COLORS["panel"])],
            foreground=[("disabled", "#626a79")],
        )
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="white",
            font=("Segoe UI", 11, "bold"),
        )
        style.map("Accent.TButton", background=[("active", "#4aa0ff"), ("disabled", "#244361")])
        style.configure(
            "TEntry",
            fieldbackground=COLORS["field"],
            foreground=COLORS["text"],
            insertcolor="white",
            bordercolor=COLORS["line"],
            padding=7,
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["field"],
            background=COLORS["field"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["muted"],
            padding=6,
            bordercolor=COLORS["line"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["field"])],
            foreground=[("readonly", COLORS["text"])],
        )
        root.option_add("*TCombobox*Listbox.background", COLORS["field"])
        root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        style.configure("TNotebook", background=COLORS["panel"], borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=COLORS["field"], foreground=COLORS["muted"], padding=(12, 9)
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["panel"])],
            foreground=[("selected", "white")],
        )
        style.configure(
            "TCheckbutton",
            background=COLORS["panel"],
            foreground=COLORS["text"],
            font=("Segoe UI", 9),
            indicatorbackground=COLORS["field"],
            indicatorforeground="white",
            indicatorbordercolor=COLORS["line"],
            bordercolor=COLORS["line"],
        )
        style.map("TCheckbutton", indicatorbackground=[("selected", COLORS["accent"])])
        style.map("TCheckbutton", background=[("active", COLORS["panel"])])
        style.configure(
            "Horizontal.TScale",
            background=COLORS["accent"],
            troughcolor=COLORS["field"],
            bordercolor=COLORS["field"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
            sliderlength=16,
            gripcount=0,
        )
        style.configure(
            "TProgressbar",
            background=COLORS["accent"],
            troughcolor=COLORS["field"],
            borderwidth=0,
            bordercolor=COLORS["field"],
            lightcolor=COLORS["accent"],
            darkcolor=COLORS["accent"],
        )
        style.configure(
            "TNotebook.Tab",
            bordercolor=COLORS["panel"],
            lightcolor=COLORS["panel"],
            darkcolor=COLORS["panel"],
        )
        style.element_create("FlatTab", "from", "default", "label.border")
        style.layout(
            "TNotebook.Tab",
            [
                (
                    "FlatTab",
                    {
                        "sticky": "nswe",
                        "children": [
                            (
                                "Notebook.padding",
                                {
                                    "sticky": "nswe",
                                    "children": [("Notebook.label", {"sticky": "nswe"})],
                                },
                            )
                        ],
                    },
                )
            ],
        )
        style.configure("TNotebook.Tab", padding=(14, 10), borderwidth=0)
        style.map(
            "TNotebook.Tab",
            background=[("selected", COLORS["field"]), ("active", "#2d323d")],
            foreground=[("selected", COLORS["accent"]), ("active", COLORS["text"])],
        )
        style.configure(
            "TNotebook",
            bordercolor=COLORS["panel"],
            lightcolor=COLORS["panel"],
            darkcolor=COLORS["panel"],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=COLORS["line"],
            troughcolor=COLORS["panel"],
            bordercolor=COLORS["panel"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
            arrowcolor=COLORS["muted"],
            gripcount=0,
        )
        style.configure("TPanedwindow", background=COLORS["bg"])

    def label(self, parent, text=None, **kwargs):
        label = self.ttk.Label(parent, text=text, **kwargs)
        return label

    def section(self, parent, text):
        self.label(parent, text, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(11, 7))

    def scroll_tab(self, notebook, title):
        outer = self.ttk.Frame(notebook)
        notebook.add(outer, text=title)
        canvas = self.tk.Canvas(outer, bg=COLORS["panel"], highlightthickness=0, borderwidth=0)
        scrollbar = self.ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)

        def scroll_position(first, last):
            scrollbar.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scrollbar.pack_forget()
            elif not scrollbar.winfo_manager():
                scrollbar.pack(side="right", fill="y", before=canvas)

        canvas.configure(yscrollcommand=scroll_position)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = self.ttk.Frame(canvas, padding=(16, 2, 12, 18))
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))

        def wheel(event):
            canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

        # Bind descendants after their creation, without stealing wheel events elsewhere.
        def bind_children():
            def visit(widget):
                widget.bind("<MouseWheel>", wheel, add="+")
                for child in widget.winfo_children():
                    visit(child)

            visit(inner)
            canvas.bind("<MouseWheel>", wheel)

        self.root.after_idle(bind_children)
        return inner

    def build(self):
        ttk = self.ttk
        self.frame = ttk.Frame(self.root, padding=24, style="Root.TFrame")
        self.frame.pack(fill="both", expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        header = ttk.Frame(self.frame, style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)
        self.label(
            header, "Native Boot Studio", style="Root.TLabel", font=("Segoe UI", 21, "bold")
        ).grid(row=0, column=0, sticky="w")
        self.label(
            header,
            f"Xbox 360 · {VERSION}",
            style="Root.TLabel",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        toolbar = ttk.Frame(header, style="Root.TFrame")
        toolbar.grid(row=0, column=1, rowspan=2)
        for text, command in [("Öffnen", self.open_project), ("Speichern", self.save)]:
            ttk.Button(toolbar, text=text, command=command).pack(side="left", padx=(0, 7))
        self.undo_button = ttk.Button(toolbar, text="↶", width=3, command=self.undo)
        self.undo_button.pack(side="left", padx=(0, 5))
        self.redo_button = ttk.Button(toolbar, text="↷", width=3, command=self.redo)
        self.redo_button.pack(side="left")
        selectors = ttk.Frame(toolbar, style="Root.TFrame")
        selectors.pack(side="left", padx=(18, 0))
        self.language_box = ttk.Combobox(
            selectors,
            textvariable=self.language,
            values=["English", "Deutsch"],
            state="readonly",
            width=12,
        )
        self.language_box.pack(side="right")
        self.language_box.bind("<<ComboboxSelected>>", self.change_language)
        pane = ttk.Panedwindow(self.frame, orient="horizontal")
        pane.grid(row=1, column=0, sticky="nsew")
        left = ttk.Frame(pane, padding=20)
        right = ttk.Frame(pane, padding=(12, 8, 12, 8))
        pane.add(left, weight=3)
        pane.add(right, weight=2)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        top = ttk.Frame(left)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top.columnconfigure(0, weight=1)
        self.label(top, "VORSCHAU", foreground=COLORS["muted"], font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        self.mode_box = ttk.Combobox(
            top,
            textvariable=self.mode,
            values=["Gesamtbild", "Kugel", "Kugel-X", "Oberfläche", "Schriftzug", "Farbverläufe"],
            state="readonly",
            width=15,
        )
        self.mode_box.grid(row=0, column=1)
        choices = ttk.Frame(left)
        choices.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ttk.Checkbutton(choices, text="Original vergleichen", variable=self.compare).pack(
            side="left"
        )
        self.ttk.Button(
            choices, text="Vorschau-Info", style="Subtle.TButton", command=self.toggle_preview_info
        ).pack(side="right")
        self.preview = self.tk.Canvas(left, bg="#f5f5f5", highlightthickness=0)
        self.preview.grid(row=2, column=0, sticky="nsew")
        self.preview.bind("<Configure>", self.invalidate)
        self.gpu_button = ttk.Button(
            choices, text="Shader-Vorschau starten", command=self.toggle_gpu, state="disabled"
        )
        self.gpu_button.pack(side="left", padx=(12, 0))
        self.preview_note = self.label(
            left,
            "Originalmodelle · Beleuchtung und Bewegung angenähert",
            style="Muted.TLabel",
            font=("Segoe UI", 9),
            wraplength=680,
        )
        self.preview_note.grid(row=3, column=0, sticky="w", pady=(10, 2))
        self.preview_help = self.label(
            left,
            "Farbverläufe zeigen native Ausgangsfarben. Die Xbox-Shader werden nicht emuliert.",
            style="Muted.TLabel",
            wraplength=700,
            font=("Segoe UI", 9),
        )
        self.preview_help.grid(row=4, column=0, sticky="w")
        self.preview_help.grid_remove()
        playback = ttk.Frame(left)
        playback.grid(row=5, column=0, sticky="ew", pady=(14, 8))
        playback.columnconfigure(1, weight=1)
        self.play_button = ttk.Button(playback, text="▶ Abspielen", command=self.toggle)
        self.play_button.grid(row=0, column=0, padx=(0, 10))
        ttk.Scale(playback, from_=0, to=8, variable=self.timeline, command=self.seek).grid(
            row=0, column=1, sticky="ew"
        )
        self.time_label = self.label(playback, "7,0 s", width=7)
        self.time_label.grid(row=0, column=2, padx=(8, 0))
        view = ttk.Frame(left)
        self.view_panel = view
        view.grid(row=6, column=0, sticky="ew")
        view.columnconfigure(1, weight=1)
        view.columnconfigure(3, weight=1)
        self.label(view, "Drehen", style="Muted.TLabel").grid(row=0, column=0, padx=(0, 8))
        ttk.Scale(view, from_=-3.14, to=3.14, variable=self.orbit).grid(
            row=0, column=1, sticky="ew"
        )
        self.label(view, "Zoom", style="Muted.TLabel").grid(row=0, column=2, padx=(14, 8))
        ttk.Scale(view, from_=0.7, to=1.4, variable=self.zoom).grid(row=0, column=3, sticky="ew")
        ttk.Button(view, text="Ansicht zurücksetzen", command=self.reset_view).grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(9, 0)
        )
        self.view_widgets = [
            widget
            for widget in view.winfo_children()
            if widget.winfo_class() in ("TScale", "TButton")
        ]
        self.view_note = self.label(
            left,
            "Ansicht, Zoom und Vorschauzeit ändern die exportierte XEX nicht.",
            style="Muted.TLabel",
            font=("Segoe UI", 9),
        )
        self.view_note.grid(row=7, column=0, sticky="w", pady=(10, 0))
        self.view_note.grid_remove()
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        palette = self.scroll_tab(self.notebook, "Palette")
        details = self.scroll_tab(self.notebook, "Details")
        motion = self.scroll_tab(self.notebook, "Ablauf")
        files = self.scroll_tab(self.notebook, "Dateien")
        self.edit_tabs = list(self.notebook.tabs())[:3]
        self.build_palette(palette)
        self.build_details(details)
        self.build_motion(motion)
        self.build_files(files)
        self.build_export()

    def color_row(self, parent, title, path):
        row = self.ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        row.columnconfigure(0, weight=1)
        self.label(row, title, font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        button = self.tk.Button(
            row,
            width=9,
            relief="flat",
            borderwidth=0,
            font=("Consolas", 10, "bold"),
            pady=0,
            cursor="hand2",
            command=lambda: self.choose_color(title, path),
        )
        button.grid(row=0, column=1, padx=(8, 0), ipady=2)
        self.swatches.append((button, path))
        return button

    def build_palette(self, parent):
        self.section(parent, "Farb-Presets")
        selectors = self.ttk.Frame(parent)
        selectors.pack(fill="x")
        selectors.columnconfigure(1, weight=1)
        self.preset_group = self.tk.StringVar(value="Alle")
        self.preset_name = self.tk.StringVar(value="Blau · Standard")
        self.group_box = self.ttk.Combobox(
            selectors,
            textvariable=self.preset_group,
            values=palettes.GROUPS,
            state="readonly",
            width=11,
        )
        self.group_box.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.group_box.bind("<<ComboboxSelected>>", lambda event: self.filter_presets())
        self.preset_box = self.ttk.Combobox(
            selectors,
            textvariable=self.preset_name,
            values=[p[1] for p in palettes.PALETTES],
            state="readonly",
            height=16,
            width=20,
        )
        self.preset_box.grid(row=0, column=1, sticky="ew")
        self.preset_box.bind(
            "<<ComboboxSelected>>",
            lambda event: self.preset(palettes.BY_LABEL[self.preset_name.get()]),
        )
        actions = self.ttk.Frame(parent)
        actions.pack(fill="x", pady=(10, 4))
        self.gallery_button = self.ttk.Button(
            actions, text="Galerie", command=self.show_gallery, state="disabled"
        )
        self.gallery_button.pack(side="left", padx=(0, 6))
        self.ttk.Button(actions, text="Preset speichern", command=self.save_user_preset).pack(
            side="left", padx=(0, 6)
        )
        self.library_button = self.ttk.Button(
            actions, text="Eigene Presets", command=self.show_library
        )
        self.library_button.pack(side="left")
        self.preset_hint_text = locale.RawStringVar(
            value=t("40 Farbvorlagen · eigene Presets in deiner Bibliothek")
        )
        self.preset_hint = self.label(
            parent,
            textvariable=self.preset_hint_text,
            style="Muted.TLabel",
            wraplength=460,
            font=("Segoe UI", 9),
        )
        self.preset_hint.pack(anchor="w", pady=(4, 0))
        self.section(parent, "Ein abgestimmter Farbton")
        row = self.ttk.Frame(parent)
        row.pack(fill="x", pady=(0, 6))
        self.theme_button = self.tk.Button(
            row,
            text="#0080FF",
            relief="flat",
            borderwidth=0,
            font=("Consolas", 12, "bold"),
            cursor="hand2",
            command=lambda: self.choose_color("Abgestimmter Farbton", None),
        )
        self.theme_button.pack(side="left", ipadx=12, ipady=8)
        self.label(
            row,
            "Wirbel, Kugel-X, Leuchten und Schrift",
            style="Muted.TLabel",
            wraplength=280,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12)
        self.section(parent, "Farben einzeln anpassen")
        for title, path in [
            ("Hintergrund · Xbox & Vorschau", ("background_color",)),
            ("Ausströmender Wirbel", ("ribbon_tint",)),
            ("Kugel-X / Texturen", ("texture_tint",)),
            ("Leuchten", ("effects", 0)),
            ("Helle Effektschicht", ("effects", 1)),
            ("Szenenfarbe", ("effects", 2)),
            ("XBOX-Schriftzug", ("text_colors", 0)),
        ]:
            self.color_row(parent, title, path)
        self.ttk.Button(
            parent,
            text="Originalen Hintergrund wiederherstellen",
            style="Subtle.TButton",
            command=self.reset_background,
        ).pack(anchor="w", pady=(8, 0))

    def build_details(self, parent):
        self.section(parent, "Effekte & Shader")
        for title, path in [
            ("Leuchten", ("effects", 0)),
            ("Helle Effektschicht", ("effects", 1)),
            ("Szenenfarbe", ("effects", 2)),
            ("Shaderfarbe A", ("shader_colors", 0)),
            ("Shaderfarbe B", ("shader_colors", 1)),
            ("Kugel-X / Texturen", ("texture_tint",)),
            ("Ausströmender Wirbel", ("ribbon_tint",)),
        ]:
            self.color_row(parent, title, path)
        self.section(parent, "Kugelmaterialien")
        for index, name in enumerate(MATERIAL_NAMES):
            self.color_row(parent, name, ("materials", index, "diffuse"))
        self.label(
            parent,
            "Grundfarben der Materialien. Dynamische Glanzfarben\nkönnen sie in einzelnen Phasen überlagern. Die inneren\nModelle werden in der Vorschau nicht separat gezeigt.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=9)
        self.section(parent, "Originaler Schriftzug")
        for index, name in enumerate(TEXT_NAMES):
            self.color_row(parent, name, ("text_colors", index))
        for label, key, lo, hi in [
            ("Größe", "scale", 0.6, 1.1),
            ("Horizontal", "x", -0.3, 0.3),
            ("Vertikal", "y", -0.18, 0.18),
        ]:
            self.profile_slider(parent, label, ("text_transform", key), lo, hi)
        self.ttk.Button(
            parent, text="Schriftgröße & Position zurücksetzen", command=self.reset_text
        ).pack(anchor="w", pady=(9, 0))

    def build_motion(self, parent):
        self.section(parent, "Natives Animationstempo")
        self.profile_slider(parent, "Tempo", ("animation_speed",), 0.75, 1.25)
        self.ttk.Button(parent, text="Originaltempo · 1,00 ×", command=self.reset_speed).pack(
            anchor="w", pady=(9, 0)
        )
        self.label(
            parent,
            "0,75 × langsam  ·  1,00 × original  ·  1,25 × schnell\n\nDas Tempo wird in die neue bootanim.xex übernommen.\nDie originalen Bewegungsbahnen bleiben erhalten.\n\nDer Ton bleibt unverändert. Die Synchronität bei\nanderem Tempo ist auf der Xbox noch ungeprüft.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=16)
        self.section(parent, "Was wird exportiert?")
        self.label(
            parent,
            "✓ Hintergrundfarbe\n✓ Farben von Effekten, Texturen und Wirbel\n✓ Grundfarben der Modelle und des Schriftzugs\n✓ Größe / Position des originalen Schriftzugs\n✓ Natives Tempo\n\nDie Vorschauansicht selbst dient der Betrachtung.\nFreier Text und neue Bewegungsbahnen sind nicht enthalten.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 10),
        ).pack(anchor="w")

    def build_files(self, parent):
        from tkinter import filedialog

        self.section(parent, "Einrichtung")
        self.label(
            parent,
            "Originalanimation und XexTool werden separat benötigt.\nXenia ist optional für die Shader-Vorschau.",
            style="Muted.TLabel",
            wraplength=460,
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        self.section(parent, "Originaldatei")
        self.label(
            parent,
            "Die unveränderte Eingabe bleibt deine Grundlage.\nZum Weiterbearbeiten ein Studio-Projekt öffnen.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))
        self.ttk.Entry(parent, textvariable=self.source_display, state="readonly").pack(fill="x")
        self.ttk.Button(
            parent,
            text="Original bootanim.xex auswählen …",
            command=lambda: self.browse(self.source, [("Xbox-XEX", "*.xex")]),
        ).pack(anchor="w", pady=7)
        self.section(parent, "XexTool 6.3")
        self.ttk.Entry(parent, textvariable=self.tool_display, state="readonly").pack(fill="x")
        self.ttk.Button(
            parent,
            text="XexTool auswählen …",
            command=lambda: self.browse(self.tool, [("XexTool", "*.exe")]),
        ).pack(anchor="w", pady=7)
        self.label(
            parent,
            "XexTool 6.3 selbst bereitstellen. Eine Datei im Ordner tools wird automatisch erkannt.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=8)
        self.section(parent, "Xenia · optionale Shader-Vorschau")
        self.ttk.Entry(parent, textvariable=self.xenia_display, state="readonly").pack(fill="x")
        actions = self.ttk.Frame(parent)
        actions.pack(fill="x", pady=8)
        self.ttk.Button(actions, text="Xenia auswählen …", command=self.choose_xenia).pack(
            side="left", padx=(0, 6)
        )
        self.ttk.Button(
            actions,
            text="Offizielle Xenia-Version öffnen",
            style="Subtle.TButton",
            command=self.open_xenia_page,
        ).pack(side="left")
        self.ttk.Button(parent, text="Eingabe erneut prüfen", command=self.start_load).pack(
            anchor="w", pady=12
        )
        self.section(parent, "Eingabeprüfung")
        self.label(
            parent, textvariable=self.source_status, wraplength=380, style="Muted.TLabel"
        ).pack(anchor="w")
        self.section(parent, "Projekt")
        self.label(
            parent,
            "Ein Projekt speichert deine Einstellungen und den\nOriginalpfad. Auf der Xbox wird weiterhin eine\nneu exportierte bootanim.xex verwendet.",
            style="Muted.TLabel",
            wraplength=380,
            font=("Segoe UI", 9),
        ).pack(anchor="w")
        self.ttk.Button(
            parent, text="Alle Einstellungen zurücksetzen", command=self.reset_all
        ).pack(anchor="w", pady=14)

    def build_export(self):
        ttk = self.ttk
        self.export_panel = ttk.Frame(self.frame, padding=14)
        self.export_panel.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self.export_panel.columnconfigure(1, weight=1)
        self.label(
            self.export_panel,
            "XEX-EXPORT",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.target_box = ttk.Combobox(
            self.export_panel,
            textvariable=self.target,
            values=list(TARGET_LABELS),
            state="readonly",
            width=27,
        )
        self.target_box.grid(row=0, column=1, sticky="w")
        self.output_button = ttk.Button(
            self.export_panel, text="Ausgabe öffnen", command=self.open_output, state="disabled"
        )
        self.output_button.grid(row=0, column=2, padx=9)
        self.export_button = ttk.Button(
            self.export_panel,
            text="bootanim.xex exportieren …",
            style="Accent.TButton",
            command=self.export,
        )
        self.export_button.grid(row=0, column=3)
        self.label(
            self.export_panel,
            textvariable=self.target_note,
            style="Muted.TLabel",
            font=("Segoe UI", 9),
            wraplength=1200,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(9, 0))
        self.progress = ttk.Progressbar(self.frame, mode="indeterminate")
        self.progress.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        self.progress.grid_remove()
        self.label(
            self.frame,
            textvariable=self.status,
            style="Root.TLabel",
            foreground=COLORS["muted"],
            wraplength=1260,
            font=("Segoe UI", 9),
        ).grid(row=4, column=0, sticky="w", pady=(7, 0))
        self.target_changed()

    def profile_slider(self, parent, label, path, lo, hi):
        row = self.ttk.Frame(parent)
        row.pack(fill="x", pady=(10, 1))
        row.columnconfigure(0, weight=1)
        self.label(row, label).grid(row=0, column=0, sticky="w")
        value = self.label(row, "", width=9)
        value.grid(row=0, column=1, sticky="e")
        variable = self.tk.DoubleVar(value=path_get(self.profile, path))
        self.sliders[path] = variable
        self.slider_labels[path] = value
        self.ttk.Scale(
            parent,
            from_=lo,
            to=hi,
            variable=variable,
            command=lambda raw, p=path: self.slider_changed(p, raw),
        ).pack(fill="x")

    def choose_color(self, title, path):
        from tkinter import ttk

        initial = path_get(self.profile, path) if path else self.profile["ribbon_tint"]
        initial = (
            initial
            if initial is not None
            else ([1.0, 1.0, 1.0] if path == ("background_color",) else [0.4, 1.0, 0.0])
        )
        dialog = self.tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=COLORS["panel"])
        dialog.geometry("440x440")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=20)
        body.pack(fill="both", expand=True)
        self.label(body, title, font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10))
        swatch = self.tk.Canvas(body, height=64, bg=hexcolor(initial), highlightthickness=0)
        swatch.pack(fill="x")
        color = self.tk.StringVar(value=hexcolor(initial).upper())
        error = self.tk.StringVar()
        guard = [False]
        channels = []
        channel_entries = []
        draft = [list(initial)]

        def preview(rgb):
            value = copy.deepcopy(self.profile)
            if path:
                path_set(value, path, rgb)
            else:
                value = themed(value, rgb)
            self.color_draft = value
            swatch.configure(bg=hexcolor(rgb))
            self.invalidate()

        def from_hex(*_):
            if guard[0]:
                return
            try:
                rgb = parse_hex(color.get())
                draft[0] = rgb
                error.set("")
                guard[0] = True
                for var, text, v in zip(channels, channel_entries, rgb):
                    var.set(round(v * 255))
                    text.set(str(round(v * 255)))
                guard[0] = False
                preview(rgb)
                apply_button.configure(state="normal")
            except ValueError as exc:
                error.set(str(exc))
                apply_button.configure(state="disabled")

        def from_rgb(*_):
            if guard[0]:
                return
            rgb = [round(var.get()) / 255 for var in channels]
            draft[0] = rgb
            guard[0] = True
            color.set(hexcolor(rgb).upper())
            for text, v in zip(channel_entries, rgb):
                text.set(str(round(v * 255)))
            guard[0] = False
            error.set("")
            preview(rgb)
            apply_button.configure(state="normal")

        def from_entries(*_):
            if guard[0]:
                return
            values = [text.get().strip() for text in channel_entries]
            if any(not text.isdigit() or not 0 <= int(text) <= 255 for text in values):
                error.set("RGB-Kanäle brauchen ganze Zahlen von 0 bis 255.")
                apply_button.configure(state="disabled")
                return
            guard[0] = True
            for var, text in zip(channels, values):
                var.set(int(text))
            guard[0] = False
            from_rgb()

        entry_row = ttk.Frame(body)
        entry_row.pack(fill="x", pady=12)
        self.label(entry_row, "HEX").pack(side="left", padx=(0, 12))
        entry = ttk.Entry(entry_row, textvariable=color, width=16, font=("Consolas", 13))
        entry.pack(side="left", fill="x", expand=True)
        for label, c in zip(("Rot", "Grün", "Blau"), initial):
            row = ttk.Frame(body)
            row.pack(fill="x", pady=4)
            row.columnconfigure(1, weight=1)
            self.label(row, label, width=6).grid(row=0, column=0)
            var = self.tk.DoubleVar(value=round(c * 255))
            channels.append(var)
            ttk.Scale(row, from_=0, to=255, variable=var, command=from_rgb).grid(
                row=0, column=1, sticky="ew"
            )
            text = self.tk.StringVar(value=str(round(c * 255)))
            channel_entries.append(text)
            ttk.Entry(row, textvariable=text, width=5, justify="right").grid(
                row=0, column=2, padx=(10, 0)
            )
        self.label(
            body, textvariable=error, foreground="#ffadad", wraplength=395, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=8)
        buttons = ttk.Frame(body)
        buttons.pack(side="bottom", fill="x", pady=(8, 0))

        def finish(apply):
            if apply:
                if any(
                    not text.get().strip().isdigit() or not 0 <= int(text.get().strip()) <= 255
                    for text in channel_entries
                ):
                    error.set("RGB-Kanäle brauchen ganze Zahlen von 0 bis 255.")
                    return
                try:
                    rgb = parse_hex(color.get())
                except ValueError as exc:
                    error.set(str(exc))
                    return
                value = copy.deepcopy(self.profile)
                if path:
                    path_set(value, path, rgb)
                else:
                    value = themed(value, rgb)
                self.history.replace(value)
                self.refresh()
            self.color_draft = None
            dialog.destroy()
            self.invalidate()

        ttk.Button(buttons, text="Abbrechen", command=lambda: finish(False)).pack(side="left")
        apply_button = ttk.Button(
            buttons, text="Übernehmen", style="Accent.TButton", command=lambda: finish(True)
        )
        apply_button.pack(side="right")
        color.trace_add("write", from_hex)
        for text in channel_entries:
            text.trace_add("write", from_entries)
        dialog.protocol("WM_DELETE_WINDOW", lambda: finish(False))
        dialog.bind("<Escape>", lambda event: finish(False))
        dialog.bind("<Return>", lambda event: finish(True))
        entry.focus_set()
        entry.selection_range(0, "end")

    def document(self):
        value = project(
            self.profile, self.source.get(), self.tool.get(), TARGET_LABELS[self.target.get()]
        )
        value["animation"] = "modern"
        return value

    def change_language(self, *_):
        locale.set("en" if self.language.get() == "English" else "de", self.root)
        self.update_file_labels()
        self.refresh()
        self.target_changed()
        self.refresh_library()
        self.invalidate()

    def refresh_library(self, select=None):
        self.user_records, self.user_errors = self.preset_store.list()
        self.library_button.configure(text="Eigene Presets")
        if self.library is None or not self.library.winfo_exists():
            return
        tree = self.library_tree
        selection = select or (tree.selection()[0] if tree.selection() else None)
        for item in tree.get_children():
            tree.delete(item)
        self.library_images = {}
        for identity, record in self.user_records.items():
            colors = record["colors"]
            main = colors["ribbon_tint"]
            background = colors["background_color"]
            icon = self.tk.PhotoImage(width=24, height=24)
            icon.put(hexcolor(main or [0.4, 1.0, 0.0]), to=(0, 0, 24, 24))
            icon.put(
                hexcolor(background) if background is not None else "#f5f5f5", to=(0, 17, 24, 24)
            )
            self.library_images[identity] = icon
            tree.insert(
                "",
                "end",
                iid=identity,
                image=icon,
                values=(
                    record["name"],
                    hexcolor(main or [0.4, 1.0, 0.0]).upper(),
                    hexcolor(background).upper() if background is not None else t("Original"),
                ),
            )
        if selection in self.user_records:
            tree.selection_set(selection)
            tree.focus(selection)
            tree.see(selection)
        for column, title in [
            ("name", "Name"),
            ("color", "Hauptfarbe"),
            ("background", "Hintergrund"),
        ]:
            tree.heading(column, text=t(title))
        self.library_note.configure(
            text=(
                t("Keine eigenen Presets. Speichere zuerst deine aktuelle Farbpalette.")
                if not self.user_records
                else t("Doppelklick zum Anwenden. Größe, Position und Tempo bleiben erhalten.")
            )
        )
        if self.user_errors:
            self.library_note.configure(
                text=t("Einige Preset-Dateien sind beschädigt und wurden übersprungen.")
            )
        self.library_selection_changed()

    def library_selection_changed(self, *_):
        state = "normal" if self.library_tree.selection() else "disabled"
        for button in self.library_actions:
            button.configure(state=state)

    def selected_user_preset(self):
        selection = self.library_tree.selection() if self.library_tree is not None else ()
        return selection[0] if selection else None

    def apply_user_preset(self, identity):
        record = user_presets.read(self.preset_store.path(identity))
        self.history.replace(user_presets.apply(self.profile, record))
        self.refresh()
        # Names are user data: do not translate them or treat them as built-in palette IDs.
        self.preset_hint_text.set(t("Eigenes Preset angewendet: ") + record["name"])
        if self.library is not None and self.library.winfo_exists():
            self.library.destroy()

    def save_user_preset(self):
        self.preset_name_dialog()

    def preset_name_dialog(self, identity=None):
        from tkinter import ttk

        record = self.user_records.get(identity)
        title = "Preset umbenennen" if identity else "Farb-Preset speichern"
        window = self.tk.Toplevel(self.root)
        window.title(title)
        window.geometry("460x285")
        window.configure(bg=COLORS["panel"])
        window.resizable(False, False)
        window.transient(self.root)
        window.grab_set()
        body = ttk.Frame(window, padding=24)
        body.pack(fill="both", expand=True)
        self.label(body, title, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        self.label(body, "Ein Name für deine Farbpalette", style="Muted.TLabel").pack(
            anchor="w", pady=(6, 14)
        )
        name = locale.RawStringVar(value=record["name"] if record else "")
        entry = ttk.Entry(body, textvariable=name)
        entry.pack(fill="x")
        error = self.tk.StringVar()
        self.label(
            body, textvariable=error, foreground="#ffb4ad", wraplength=410, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(7, 0))
        actions = ttk.Frame(body)
        actions.pack(side="bottom", fill="x", pady=(12, 0))

        def finish():
            try:
                saved = (
                    self.preset_store.rename(identity, name.get())
                    if identity
                    else self.preset_store.save(user_presets.from_profile(name.get(), self.profile))
                )
            except (OSError, ValueError) as exc:
                error.set(str(exc))
                return
            self.refresh_library(saved)
            window.destroy()
            self.preset_hint_text.set(
                t("Eigenes Preset gespeichert: ") + self.user_records[saved]["name"]
            )

        ttk.Button(actions, text="Abbrechen", style="Subtle.TButton", command=window.destroy).pack(
            side="left"
        )
        ttk.Button(actions, text="Speichern", style="Accent.TButton", command=finish).pack(
            side="right"
        )
        window.bind("<Return>", lambda event: finish())
        window.bind("<Escape>", lambda event: window.destroy())
        entry.focus_set()
        entry.selection_range(0, "end")

    def show_library(self):
        if self.library is not None and self.library.winfo_exists():
            self.library.lift()
            return
        window = self.tk.Toplevel(self.root)
        self.library = window
        window.title("Eigene Presets · Native Boot Studio")
        window.geometry("760x490")
        window.minsize(650, 420)
        window.configure(bg=COLORS["panel"])
        window.transient(self.root)
        body = self.ttk.Frame(window, padding=24)
        body.pack(fill="both", expand=True)
        head = self.ttk.Frame(body)
        head.pack(fill="x", pady=(0, 8))
        self.label(head, "Deine Farbpalette-Bibliothek", font=("Segoe UI", 16, "bold")).pack(
            side="left"
        )
        self.ttk.Button(head, text="Importieren …", command=self.import_user_preset).pack(
            side="right"
        )
        self.library_note = self.label(
            body, "", style="Muted.TLabel", wraplength=700, font=("Segoe UI", 9)
        )
        self.library_note.pack(anchor="w", pady=(0, 18))
        content = self.ttk.Frame(body)
        content.pack(fill="both", expand=True)
        tree = self.ttk.Treeview(
            content,
            columns=("name", "color", "background"),
            show="tree headings",
            selectmode="browse",
        )
        self.library_tree = tree
        tree.column("#0", width=44, minwidth=44, stretch=False)
        tree.column("name", width=280, minwidth=180)
        tree.column("color", width=120, minwidth=100, stretch=False)
        tree.column("background", width=120, minwidth=100, stretch=False)
        scrollbar = self.ttk.Scrollbar(content, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        actions = self.ttk.Frame(body)
        actions.pack(side="bottom", fill="x", pady=(18, 0), before=content)
        self.library_actions = []

        def apply():
            from tkinter import messagebox

            identity = self.selected_user_preset()
            if identity:
                try:
                    self.apply_user_preset(identity)
                except (OSError, ValueError) as exc:
                    messagebox.showerror(
                        "Preset konnte nicht geladen werden", self.display_error(exc), parent=window
                    )

        for title, command in [
            ("Umbenennen", lambda: self.preset_name_dialog(self.selected_user_preset())),
            ("Exportieren …", self.export_user_preset),
            ("Ersetzen", self.replace_user_preset),
            ("Löschen", self.delete_user_preset),
        ]:
            button = self.ttk.Button(actions, text=title, style="Subtle.TButton", command=command)
            button.pack(side="left", padx=(0, 6))
            self.library_actions.append(button)
        button = self.ttk.Button(actions, text="Anwenden", style="Accent.TButton", command=apply)
        button.pack(side="right")
        self.library_actions.append(button)
        tree.bind("<<TreeviewSelect>>", self.library_selection_changed)
        tree.bind("<Double-1>", lambda event: apply())
        window.bind("<Escape>", lambda event: window.destroy())
        self.refresh_library()

    def import_user_preset(self):
        from tkinter import filedialog, messagebox

        path = filedialog.askopenfilename(
            parent=self.library,
            title="Farb-Preset importieren",
            filetypes=[("Farb-Preset", "*.nbpalette.json"), ("JSON", "*.json")],
        )
        if not path:
            return
        try:
            self.refresh_library(self.preset_store.import_file(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Import fehlgeschlagen", self.display_error(exc), parent=self.library
            )

    def export_user_preset(self):
        from tkinter import filedialog, messagebox

        identity = self.selected_user_preset()
        if identity is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.library,
            title="Farb-Preset exportieren",
            initialfile="My-Palette.nbpalette.json",
            defaultextension=".nbpalette.json",
            filetypes=[("Farb-Preset", "*.nbpalette.json")],
        )
        if not path:
            return
        try:
            self.preset_store.export_file(identity, path)
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Export fehlgeschlagen", self.display_error(exc), parent=self.library
            )

    def delete_user_preset(self):
        from tkinter import messagebox

        identity = self.selected_user_preset()
        if identity is None:
            return
        if not messagebox.askyesno(
            "Preset löschen",
            "Dieses eigene Preset aus der Bibliothek entfernen?",
            parent=self.library,
        ):
            return
        try:
            self.preset_store.delete(identity)
            self.refresh_library()
        except OSError as exc:
            messagebox.showerror(
                "Löschen fehlgeschlagen", self.display_error(exc), parent=self.library
            )

    def replace_user_preset(self):
        from tkinter import messagebox

        identity = self.selected_user_preset()
        if identity is None:
            return
        if not messagebox.askyesno(
            "Preset ersetzen",
            "Die gespeicherten Farben durch deine aktuelle Palette ersetzen?",
            parent=self.library,
        ):
            return
        try:
            self.preset_store.save(
                user_presets.from_profile(self.user_records[identity]["name"], self.profile),
                identity,
            )
            self.refresh_library(identity)
            self.refresh()
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "Speichern fehlgeschlagen", self.display_error(exc), parent=self.library
            )

    def dirty(self):
        try:
            return self.document() != self.saved_state
        except ValueError:
            return True

    def refresh(self):
        was_updating = self.updating
        self.updating = True
        background = self.profile.get("background_color")
        self.preview.configure(bg=hexcolor(background) if background is not None else "#f5f5f5")
        for button, path in self.swatches:
            rgb = path_get(self.profile, path)
            original_background = rgb is None and path == ("background_color",)
            if rgb is None:
                rgb = [1.0, 1.0, 1.0] if original_background else [0.4, 1.0, 0.0]
            color = hexcolor(rgb)
            button.configure(
                bg=color,
                activebackground=color,
                text="Original" if original_background else color.upper(),
                fg="white" if sum(rgb) / 3 < 0.48 else "#101a2b",
            )
        rgb = self.profile["ribbon_tint"]
        rgb = rgb if rgb is not None else [0.4, 1.0, 0.0]
        self.theme_button.configure(
            bg=hexcolor(rgb),
            activebackground=hexcolor(rgb),
            text=hexcolor(rgb).upper(),
            fg="white" if sum(rgb) / 3 < 0.48 else "#101a2b",
        )
        for path, var in self.sliders.items():
            value = path_get(self.profile, path)
            var.set(value)
            number = f"{value:.2f}" if locale.language == "en" else f"{value:.2f}".replace(".", ",")
            self.slider_labels[path].configure(
                text=number + (" ×" if path == ("animation_speed",) else "")
            )
        self.undo_button.configure(state="normal" if self.history.undo_stack else "disabled")
        self.redo_button.configure(state="normal" if self.history.redo_stack else "disabled")
        matching = None
        for name in palettes.BY_ID:
            candidate = palettes.palette(name)
            if all(candidate[key] == self.profile[key] for key in COLOR_KEYS):
                matching = name
                break
        if matching and self.preset_group.get() not in ("Alle", palettes.BY_ID[matching][2]):
            self.preset_group.set(palettes.BY_ID[matching][2])
        self.preset_name.set(palettes.BY_ID[matching][1] if matching else "Eigene Palette")
        self.filter_presets()
        own = next(
            (
                record
                for record in self.user_records.values()
                if all(record["colors"][key] == self.profile[key] for key in COLOR_KEYS)
            ),
            None,
        )
        self.preset_hint_text.set(
            t("Eigenes Preset: ") + own["name"]
            if own
            else (
                t("40 Farbvorlagen · eigene Presets in deiner Bibliothek")
                if matching
                else t("Eigene Farbpalette · als Preset speichern")
            )
        )
        for name, card in self.gallery_cards.items():
            if card.winfo_exists():
                card.configure(
                    highlightbackground=COLORS["accent"] if name == matching else COLORS["line"]
                )
        title = self.project_path.stem if self.project_path else "Neuer Entwurf"
        self.root.title(t(f'{title}{" *" if self.dirty() else ""} · Native Boot Studio {VERSION}'))
        self.updating = was_updating
        self.invalidate()

    def slider_changed(self, path, raw):
        if self.updating:
            return
        value = copy.deepcopy(self.profile)
        path_set(value, path, float(raw))
        self.history.replace(value, key=path)
        self.refresh()

    def preset(self, name):
        self.history.replace(palettes.apply(self.profile, name))
        self.preset_name.set(palettes.BY_ID[name][1])
        self.refresh()
        if self.gallery is not None and self.gallery.winfo_exists():
            self.gallery.title("Preset: " + palettes.BY_ID[name][1])
        self.status.set(
            "Preset „"
            + palettes.BY_ID[name][1]
            + "“ übernommen. Hintergrund wird exportiert; Größe, Position und Tempo bleiben erhalten."
        )

    def filter_presets(self):
        group = self.preset_group.get()
        labels = [p[1] for p in palettes.PALETTES if group == "Alle" or p[2] == group]
        self.preset_box.configure(values=labels)
        if self.preset_name.get() not in labels and self.preset_name.get() != "Eigene Palette":
            self.preset_name.set("Preset wählen …")

    def show_gallery(self):
        if self.scene is None:
            return
        if self.gallery is not None and self.gallery.winfo_exists():
            self.gallery.lift()
            return
        window = self.tk.Toplevel(self.root)
        self.gallery = window
        window.title("40 Farb-Presets · Native Boot Studio")
        window.geometry("960x740")
        window.minsize(930, 580)
        window.configure(bg=COLORS["panel"])
        window.transient(self.root)
        head = self.ttk.Frame(window, padding=16)
        head.pack(fill="x")
        self.label(head, "Preset auswählen", font=("Segoe UI", 18, "bold")).pack(side="left")
        group = self.tk.StringVar(value="Alle")
        box = self.ttk.Combobox(
            head, textvariable=group, values=palettes.GROUPS, state="readonly", width=15
        )
        box.pack(side="right")
        self.label(
            window,
            "Ein Klick übernimmt die Farben. Originalmodelle mit angenäherter Beleuchtung.",
            style="Muted.TLabel",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(0, 10))
        outer = self.ttk.Frame(window)
        outer.pack(fill="both", expand=True, padx=12)
        canvas = self.tk.Canvas(outer, bg=COLORS["panel"], highlightthickness=0)
        scrollbar = self.ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        cards = self.ttk.Frame(canvas)
        canvas.create_window((0, 0), window=cards, anchor="nw")
        cards.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))

        def wheel(event):
            canvas.yview_scroll(-int(event.delta / 120), "units")
            return "break"

        canvas.bind("<MouseWheel>", wheel)
        self.ttk.Button(window, text="Zurück zum Entwurf", command=window.destroy).pack(
            anchor="e", padx=16, pady=12
        )

        def fill(*_):
            self.gallery_token += 1
            token = self.gallery_token
            self.gallery_cards = {}
            for child in cards.winfo_children():
                child.destroy()
            selected = [
                p for p in palettes.PALETTES if group.get() == "Alle" or p[2] == group.get()
            ]
            for index, row in enumerate(selected):
                name, title = row[:2]
                p = palettes.palette(name)
                bg = (
                    hexcolor(p["background_color"])
                    if p["background_color"] is not None
                    else "#f5f5f5"
                )
                card = self.tk.Canvas(
                    cards,
                    width=216,
                    height=158,
                    bg=COLORS["field"],
                    highlightthickness=1,
                    highlightbackground=COLORS["line"],
                    cursor="hand2",
                )
                card.grid(row=index // 4, column=index % 4, padx=5, pady=5)
                card.create_rectangle(0, 0, 216, 122, fill=bg, outline="", tags="preview")
                card.create_text(
                    108, 140, text=t(title), fill=COLORS["text"], font=("Segoe UI", 9), width=205
                )
                card.bind("<Button-1>", lambda event, n=name: self.preset(n))
                card.bind("<MouseWheel>", wheel)
                self.gallery_cards[name] = card
            canvas.yview_moveto(0)
            model = self.scene

            def worker():
                for row in selected:
                    if token != self.gallery_token or self.closed:
                        return
                    try:
                        bitmap = render_view(model, palettes.palette(row[0]), (216, 122))
                    except Exception:
                        continue
                    self.events.put(("gallery", (token, row[0], bitmap)))

            threading.Thread(target=worker, daemon=True).start()

        box.bind("<<ComboboxSelected>>", fill)
        fill()

    def reset_background(self):
        p = copy.deepcopy(self.profile)
        p["background_color"] = None
        self.history.replace(p)
        self.refresh()

    def undo(self):
        if self.history.undo():
            self.refresh()

    def redo(self):
        if self.history.redo():
            self.refresh()

    def reset_text(self):
        p = copy.deepcopy(self.profile)
        p["text_transform"] = defaults()["text_transform"]
        self.history.replace(p)
        self.refresh()

    def reset_speed(self):
        p = copy.deepcopy(self.profile)
        p["animation_speed"] = 1.0
        self.history.replace(p)
        self.refresh()

    def reset_all(self):
        self.history.replace(defaults())
        self.refresh()
        self.status.set("Alle Einstellungen auf Original zurückgesetzt. Rückgängig ist verfügbar.")

    def reset_view(self):
        self.orbit.set(0.0)
        self.zoom.set(1.0)
        self.timeline.set(7.0)
        self.seek()

    def target_changed(self, *_):
        if self.closed:
            return
        target = TARGET_LABELS.get(self.target.get(), "hdd")
        self.target_note.set(
            "HDD: Speichere bootanim.xex auf der Xbox-Festplatte. Die Konsole muss für das Laden von dort eingerichtet sein."
            if target == "hdd"
            else "NAND: Verwende bootanim.xex beim Erstellen deines NAND-Abbilds. Dieses Programm installiert oder flasht nichts auf die Xbox."
        )
        if hasattr(self, "theme_button"):
            self.refresh()

    def update_file_labels(self, *_):
        for path_variable, display in (
            (self.source, self.source_display),
            (self.tool, self.tool_display),
            (self.xenia, self.xenia_display),
        ):
            path = Path(path_variable.get())
            try:
                exists = path.is_file()
            except OSError:
                exists = False
            display.set(path.name if exists else t("Keine Datei ausgewählt"))

    def display_error(self, error):
        text = str(error)
        for variable in (self.source, self.tool, self.xenia):
            value = variable.get()
            if value:
                name = Path(value).name
                for spelling in (value, value.replace("\\", "/"), value.replace("/", "\\")):
                    text = text.replace(spelling, name)
        # Exceptions may mention temporary files under a Windows user profile.
        return re.sub(r"(?i)[a-z]:[\\/]users[\\/][^\\/]+[\\/]", "~/", text)

    def files_changed(self, *_):
        if self.updating:
            return
        self.load_token += 1
        self.verified_identity = None
        self.scene = None
        self.metadata = None
        self.loading = False
        if not self.busy:
            self.progress.stop()
            self.progress.grid_remove()
        self.source_status.set("Dateipfade geändert. Bitte Eingabe prüfen.")
        self.status.set("Eingabeprüfung erforderlich. Reiter „Dateien“ → „Eingabe erneut prüfen“.")
        self.update_export_state()
        self.refresh()

    def browse(self, variable, filetypes):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            parent=self.root, filetypes=filetypes + [("Alle Dateien", "*.*")]
        )
        if path:
            variable.set(path)
            self.start_load()

    def start_load(self):
        if self.busy:
            return
        if not all(Path(path).is_file() for path in (self.source.get(), self.tool.get())):
            self.load_token += 1
            self.loading = False
            self.scene = None
            self.verified_identity = None
            self.metadata = None
            self.progress.stop()
            self.progress.grid_remove()
            self.notebook.select(3)
            self.source_status.set("Bitte deine Originalanimation und XexTool auswählen.")
            self.status.set("Einrichtung erforderlich · Dateien auswählen und Eingabe prüfen.")
            self.update_export_state()
            self.invalidate()
            return
        self.load_token += 1
        token = self.load_token
        identity = (self.source.get(), self.tool.get())
        self.loading = True
        self.scene = None
        self.verified_identity = None
        self.metadata = None
        self.source_status.set("Originaldatei und ausführbare Codebereiche werden geprüft …")
        self.status.set("Originalgeometrie wird geladen …")
        self.progress.grid()
        self.progress.start(12)
        self.update_export_state()
        self.invalidate()

        def worker():
            try:
                model, metadata = read_source(*identity)
                self.events.put(("source", (token, identity, model, metadata)))
            except Exception as exc:
                self.events.put(("source-error", (token, str(exc))))

        threading.Thread(target=worker, daemon=True).start()

    def choose_xenia(self):
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            parent=self.root, title="Xenia auswählen", filetypes=[("Xenia", "*.exe")]
        )
        if not path:
            return
        if self.gpu_mode:
            self.toggle_gpu()
        self.gpu.executable = Path(path)
        self.xenia.set(path)
        try:
            save_preferences(xenia=path)
        except OSError:
            pass
        self.update_export_state()

    def open_xenia_page(self):
        import webbrowser

        webbrowser.open(
            "https://github.com/xenia-project/release-builds-windows/releases/tag/v1.0.2844-master"
        )

    def maybe_discard(self):
        from tkinter import messagebox

        if not self.dirty():
            return True
        answer = messagebox.askyesnocancel(
            "Ungespeicherte Änderungen",
            "Möchtest du dein aktuelles Projekt zuerst speichern?",
            parent=self.root,
        )
        if answer is None:
            return False
        return self.save() if answer else True

    def open_project(self):
        from tkinter import filedialog, messagebox

        if self.busy:
            return
        path = filedialog.askopenfilename(
            parent=self.root, filetypes=[("Boot-Studio-Projekt", "*.nbstudio.json *.json")]
        )
        if not path:
            return
        try:
            checked = read_project(path)
        except Exception as exc:
            messagebox.showerror(
                "Projekt konnte nicht geöffnet werden", self.display_error(exc), parent=self.root
            )
            return
        if not self.maybe_discard():
            return
        self.history = History(checked["profile"])
        self.updating = True
        self.source.set(checked["source"])
        self.tool.set(checked["xextool"])
        self.target.set(
            next(label for label, value in TARGET_LABELS.items() if value == checked["target"])
        )
        self.updating = False
        self.project_path = Path(path)
        self.saved_state = self.document()
        self.refresh()
        self.target_changed()
        self.start_load()

    def save(self):
        from tkinter import filedialog, messagebox

        try:
            checked = self.document()
        except Exception as exc:
            messagebox.showerror(
                "Projekt konnte nicht gespeichert werden", self.display_error(exc), parent=self.root
            )
            return False
        path = self.project_path
        if path is None:
            selected = filedialog.asksaveasfilename(
                parent=self.root,
                initialfile="Meine-Animation.nbstudio.json",
                defaultextension=".nbstudio.json",
                filetypes=[("Boot-Studio-Projekt", "*.nbstudio.json")],
            )
            if not selected:
                return False
            path = Path(selected)
        try:
            save_project(path, checked)
        except Exception as exc:
            messagebox.showerror(
                "Projekt konnte nicht gespeichert werden", self.display_error(exc), parent=self.root
            )
            return False
        self.project_path = path
        self.saved_state = checked
        self.refresh()
        self.status.set("Projekt gespeichert: " + path.name)
        return True

    def update_export_state(self):
        self.export_button.configure(
            state=(
                "normal"
                if self.verified_identity == (self.source.get(), self.tool.get())
                and not self.busy
                and not self.loading
                else "disabled"
            )
        )
        self.target_box.configure(state="disabled" if self.busy else "readonly")
        self.gallery_button.configure(state="normal" if self.scene is not None else "disabled")
        self.gpu_button.configure(
            state="normal" if self.scene is not None and self.gpu.available else "disabled"
        )

    def export(self):
        from tkinter import filedialog, messagebox

        if (
            self.busy
            or self.loading
            or self.verified_identity != (self.source.get(), self.tool.get())
        ):
            return
        try:
            checked = self.document()
        except Exception as exc:
            messagebox.showerror("Ungültige Einstellungen", str(exc), parent=self.root)
            return
        name = filedialog.asksaveasfilename(
            parent=self.root,
            initialfile="bootanim.xex",
            defaultextension=".xex",
            filetypes=[("Xbox-XEX", "*.xex")],
        )
        if not name:
            return
        target = Path(name)
        if target.suffix.lower() != ".xex":
            messagebox.showerror(
                "Dateiname", "Die Ausgabe muss die Endung .xex haben.", parent=self.root
            )
            return
        # Freeze every argument so edits during an export cannot change its bytes.
        args = (
            Path(checked["source"]),
            target,
            Path(checked["xextool"]),
            copy.deepcopy(checked["profile"]["effects"]),
            checked["target"],
            True,
            checked["profile"],
        )
        self.busy = True
        self.update_export_state()
        self.progress.grid()
        self.progress.start(12)
        self.status.set("XEX wird erstellt, erneut entpackt und bytegenau geprüft …")

        def worker():
            try:
                self.events.put(("export", backend.build(*args)))
            except Exception as exc:
                self.events.put(("export-error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def open_output(self):
        if self.last_output and self.last_output.exists():
            os.startfile(str(self.last_output.parent))

    def toggle(self):
        self.playing = not self.playing
        self.last_time = time.monotonic()
        self.play_button.configure(text="Ⅱ Pause" if self.playing else "▶ Abspielen")

    def seek(self, *_):
        self.last_render_key = None

    def invalidate(self, *_):
        self.view_revision += 1
        self.last_render_key = None

    def render_worker(self):
        from PIL import Image

        while not self.closed:
            job = self.render_jobs.get()
            if job is None:
                return
            revision, serial, model, p, size, args = job
            try:
                w, h = size
                scale = 1.4
                image = render_view(model, p, (round(w * scale), round(h * scale)), **args)
                image = image.resize(size, Image.Resampling.LANCZOS)
                self.events.put(("render", (revision, serial, image)))
            except Exception as exc:
                self.events.put(("render-error", (revision, str(exc))))

    def toggle_gpu(self):
        if not self.gpu_mode and not self.gpu.available:
            return
        self.gpu_mode = not self.gpu_mode
        self.gpu_token += 1
        self.gpu_preparing = False
        self.gpu_key = None
        self.gpu_button.configure(
            text="Modell-Vorschau anzeigen" if self.gpu_mode else "Shader-Vorschau starten"
        )
        if not self.gpu_mode:
            self.gpu.stop()
            self.preview_note.configure(
                text="Originalmodelle · Beleuchtung und Bewegung angenähert"
            )
            self.preview_help.configure(
                text="Farbverläufe zeigen native Ausgangsfarben. Die Xbox-Shader werden nicht emuliert."
            )
        else:
            self.playing = False
            self.play_button.configure(text="▶ Abspielen")
            self.mode.set("Gesamtbild")
            self.orbit.set(0.0)
            self.zoom.set(1.0)
            self.preview_note.configure(
                text="Native Shader-Vorschau · Originaler Xbox-Renderer über Xenia"
            )
            self.preview_help.configure(
                text="Originale Shader, Texturen und Kamerafahrt. Emulator-Vorschau; Abgleich auf der Xbox steht noch aus."
            )
        self.mode_box.configure(state="disabled" if self.gpu_mode else "readonly")
        for widget in self.view_widgets:
            widget.configure(state="disabled" if self.gpu_mode else "normal")
        if self.gpu_mode:
            self.view_panel.grid_remove()
            self.mode_box.grid_remove()
        else:
            self.view_panel.grid()
            self.mode_box.grid()
        self.view_note.configure(
            text=(
                "Die Zeitleiste steuert die native Animation. Farben werden nach einer kurzen Ladepause aktualisiert."
                if self.gpu_mode
                else "Ansicht, Zoom und Vorschauzeit ändern die exportierte XEX nicht."
            )
        )
        self.invalidate()

    def toggle_preview_info(self):
        self.preview_info = not self.preview_info
        for widget in (self.preview_help, self.view_note):
            if self.preview_info:
                widget.grid()
            else:
                widget.grid_remove()

    def submit_gpu(self):
        if self.scene is None or self.metadata is None:
            self.gpu.stop()
            return
        p = copy.deepcopy(getattr(self, "color_draft", None) or self.profile)
        if self.compare.get():
            p = defaults()
        key = json.dumps(p, sort_keys=True) + self.metadata["source_sha256"]
        now = time.monotonic()
        if key != self.gpu_key:
            self.gpu_key = key
            self.gpu_token += 1
            self.gpu_preparing = False
            self.gpu_deadline = now + 0.55
        if now >= self.gpu_deadline and not self.gpu_preparing:
            token = self.gpu_token
            raw = self.metadata["_preview_xex"]
            at = self.timeline.get()
            self.gpu_preparing = True
            self.gpu_deadline = float("inf")
            self.gpu.stop()
            self.preview.delete("all")
            self.preview.create_text(
                self.preview.winfo_width() / 2,
                self.preview.winfo_height() / 2,
                text=t("Native Shader werden geladen …"),
                fill=COLORS["muted"],
                font=("Segoe UI", 12),
            )

            def worker():
                try:
                    self.events.put(("gpu-ready", (token, native_preview.prepare(raw, p, at))))
                except Exception as exc:
                    self.events.put(("gpu-error", (token, str(exc))))

            threading.Thread(target=worker, daemon=True).start()
        state = self.gpu.tick(
            self.preview.winfo_id(),
            self.preview.winfo_width(),
            self.preview.winfo_height(),
            self.timeline.get(),
        )
        if state == "failed":
            self.status.set("Shader-Vorschau konnte nicht gestartet werden. Details: preview.log")
            self.toggle_gpu()

    def submit_render(self):
        if self.gpu_mode:
            self.submit_gpu()
            return
        w, h = self.preview.winfo_width(), self.preview.winfo_height()
        if w < 30 or h < 30:
            return
        p = copy.deepcopy(getattr(self, "color_draft", None) or self.profile)
        background = p.get("background_color")
        self.preview.configure(bg=hexcolor(background) if background is not None else "#f5f5f5")
        if self.scene is None:
            self.preview.configure(bg=COLORS["field"])
            self.preview.delete("all")
            self.preview.create_text(
                w / 2,
                h / 2,
                text=t(
                    "Originaldatei wird geprüft …"
                    if self.loading
                    else "Originaldatei im Reiter „Dateien“ auswählen und prüfen."
                ),
                fill="#7186a2",
                font=("Segoe UI", 12),
                width=w - 40,
            )
            return
        width = min(w, 1100)
        height = round(width * 9 / 16)
        if height > h:
            height = h
            width = round(height * 16 / 9)
        args = {
            "time": self.timeline.get(),
            "orbit": self.orbit.get(),
            "mode": self.mode.get(),
            "compare": self.compare.get(),
            "dark": self.dark.get(),
            "zoom": self.zoom.get(),
        }
        key = (self.view_revision, round(args["time"], 1), width, height)
        if key == self.last_render_key:
            return
        self.last_render_key = key
        self.render_serial += 1
        job = (self.view_revision, self.render_serial, self.scene, p, (width, height), args)
        try:
            self.render_jobs.get_nowait()
        except queue.Empty:
            pass
        self.render_jobs.put_nowait(job)

    def poll(self):
        from PIL import ImageTk
        from tkinter import messagebox

        if self.closed:
            return
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind in ("source", "source-error"):
                if value[0] != self.load_token:
                    continue
                self.loading = False
                if not self.busy:
                    self.progress.stop()
                    self.progress.grid_remove()
                if kind == "source":
                    _, identity, self.scene, self.metadata = value
                    self.verified_identity = identity
                    try:
                        save_preferences(source=identity[0], xextool=identity[1])
                    except OSError:
                        pass
                    self.source_status.set(
                        f"✓ Unterstützte Originalanimation\n✓ Originaldaten geprüft\n"
                        f'{self.metadata["vertices"]:,} Modellvertices · {self.metadata["text_vertices"]} Textvertices'.replace(
                            ",", "."
                        )
                    )
                    self.status.set(
                        "Originaldatei geprüft. Entwurf bearbeiten und eine neue bootanim.xex exportieren."
                    )
                else:
                    self.scene = None
                    self.verified_identity = None
                    self.source_status.set(
                        "Eingabeprüfung fehlgeschlagen.\n" + self.display_error(value[1])
                    )
                    self.status.set("Eingabeprüfung fehlgeschlagen. Details im Reiter „Dateien“.")
                self.update_export_state()
                self.invalidate()
                if kind == "source" and self.auto_gpu and self.gpu.available and not self.gpu_mode:
                    self.auto_gpu = False
                    self.toggle_gpu()
            elif kind in ("export", "export-error"):
                self.busy = False
                self.progress.stop()
                self.progress.grid_remove()
                self.update_export_state()
                if kind == "export":
                    self.last_output = Path(value["output"])
                    self.output_button.configure(state="normal")
                    self.status.set(
                        f'✓ Export geprüft · {self.last_output.name} · {value["changed_byte_count"]} geänderte Abbildbytes · Prüfbericht gespeichert'
                    )
                else:
                    self.status.set("Export fehlgeschlagen.")
                    messagebox.showerror(
                        "Export fehlgeschlagen", self.display_error(value), parent=self.root
                    )
            elif kind == "gpu-ready":
                if self.gpu_mode and value[0] == self.gpu_token:
                    self.gpu_preparing = False
                    try:
                        self.gpu.start(value[1])
                    except Exception as exc:
                        self.status.set("Vorschaufehler: " + self.display_error(exc))
                        self.toggle_gpu()
            elif kind == "gpu-error":
                if self.gpu_mode and value[0] == self.gpu_token:
                    self.status.set("Vorschaufehler: " + self.display_error(value[1]))
                    self.toggle_gpu()
            elif kind == "render":
                revision, serial, bitmap = value
                if self.gpu_mode or revision != self.view_revision or self.scene is None:
                    continue
                photo = ImageTk.PhotoImage(bitmap)
                self.preview.image = photo
                self.preview.delete("all")
                self.preview.create_image(
                    self.preview.winfo_width() / 2, self.preview.winfo_height() / 2, image=photo
                )
            elif kind == "render-error" and value[0] == self.view_revision:
                self.status.set("Vorschaufehler: " + self.display_error(value[1]))
            elif kind == "gallery":
                token, name, bitmap = value
                if (
                    token != self.gallery_token
                    or self.gallery is None
                    or not self.gallery.winfo_exists()
                ):
                    continue
                card = self.gallery_cards.get(name)
                if card is None:
                    continue
                card.image = ImageTk.PhotoImage(bitmap)
                card.delete("preview")
                card.create_image(0, 0, image=card.image, anchor="nw", tags="preview")
        now = time.monotonic()
        if self.playing:
            self.timeline.set(
                (self.timeline.get() + (now - self.last_time) * self.profile["animation_speed"]) % 8
            )
        self.last_time = now
        self.time_label.configure(
            text=(
                f"{self.timeline.get():.1f} s"
                if locale.language == "en"
                else f"{self.timeline.get():.1f} s".replace(".", ",")
            )
        )
        self.submit_render()
        self.root.after(75, self.poll)

    def close(self):
        if self.busy:
            self.status.set("Der Export läuft noch. Bitte dessen Abschluss abwarten.")
            return
        if not self.maybe_discard():
            return
        self.closed = True
        self.gpu.close()
        try:
            self.render_jobs.get_nowait()
        except queue.Empty:
            pass
        self.render_jobs.put_nowait(None)
        self.root.destroy()


def gui(
    smoke=False,
    snapshot=None,
    small=False,
    preset="blue",
    gallery=False,
    language=None,
    gpu_smoke=False,
    library_smoke=False,
    setup_smoke=False,
):
    if language:
        locale.set(language, persist=False)
    import tkinter as tk

    if os.name == "nt":
        import ctypes

        ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    app = Studio(root)
    app.auto_gpu = not smoke and app.gpu.available
    if small:
        root.geometry("1080x740")
    if setup_smoke:
        app.source.set(str(Path("missing-original.xex")))
        app.tool.set(str(Path("missing-xextool.exe")))
        app.start_load()
        root.update()
        app.submit_render()
        root.update()
        assert (
            not app.loading
            and app.verified_identity is None
            and str(app.export_button["state"]) == "disabled"
        )
        assert app.notebook.index(app.notebook.select()) == 3
        if snapshot:
            root.update()
            from PIL import ImageGrab
            import ctypes

            ImageGrab.grab(window=ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)).save(
                snapshot
            )
        app.closed = True
        app.gpu.close()
        try:
            app.render_jobs.get_nowait()
        except queue.Empty:
            pass
        app.render_jobs.put_nowait(None)
        root.destroy()
        return
    if smoke:
        app.preset(preset)
        app.scene, app.metadata = read_source(app.source.get(), app.tool.get())
        app.verified_identity = (app.source.get(), app.tool.get())
        app.loading = False
        app.update_export_state()
        app.source_status.set(
            f"✓ Unterstützte Originalanimation\n✓ Originaldaten geprüft\n"
            f'{app.metadata["vertices"]:,} Modellvertices · {app.metadata["text_vertices"]} Textvertices'
        )
        app.status.set(
            "Originaldatei geprüft. Entwurf bearbeiten und eine neue bootanim.xex exportieren."
        )
        root.update()
        w, h = app.preview.winfo_width(), app.preview.winfo_height()
        from PIL import ImageTk, ImageGrab

        width = min(w, 1100)
        height = round(width * 9 / 16)
        if height > h:
            height = h
            width = round(height * 16 / 9)
        bitmap = render_view(app.scene, app.profile, (width, height))
        app.preview.image = ImageTk.PhotoImage(bitmap)
        app.preview.create_image(w / 2, h / 2, image=app.preview.image)
        root.update()
        assert len(app.swatches) == 22
        assert (
            app.export_panel.winfo_y() + app.export_panel.winfo_height() < app.frame.winfo_height()
        )
        assert app.preview.winfo_width() > 400
        assert str(app.export_button["state"]) == "normal"
        for tab in range(4):
            app.notebook.select(tab)
            root.update()
        app.notebook.select(0)
        root.update()
        if gallery:
            app.show_gallery()
            deadline = time.monotonic() + 12
            while (
                not all(hasattr(card, "image") for card in app.gallery_cards.values())
                and time.monotonic() < deadline
            ):
                root.update()
                time.sleep(0.005)
            assert len(app.gallery_cards) == 40 and all(
                hasattr(card, "image") for card in app.gallery_cards.values()
            )
        library_tmp = None
        if library_smoke:
            library_tmp = tempfile.TemporaryDirectory(prefix="Studio palette library ")
            folder = Path(library_tmp.name)
            app.preset_store = user_presets.Store(folder / "UserPresets")
            identities = {
                name: app.preset_store.save(
                    user_presets.from_profile(title, palettes.palette(name))
                )
                for name, title in [
                    ("black_blue", "My Blue / Black"),
                    ("black_gold", "My Gold"),
                    ("arctic", "Arctic Night"),
                ]
            }
            app.refresh_library()
            identity = identities["black_blue"]
            shared = folder / "shared.nbpalette.json"
            app.preset_store.export_file(identity, shared)
            other = user_presets.Store(folder / "Imported")
            imported = other.import_file(shared)
            assert other.list()[0][imported] == app.user_records[identity]
            app.slider_changed(("animation_speed",), "1.12")
            app.preset("black_gold")
            before = copy.deepcopy(app.profile)
            app.apply_user_preset(identity)
            assert (
                app.profile["animation_speed"] == 1.12
                and app.profile["ribbon_tint"] == palettes.palette("black_blue")["ribbon_tint"]
            )
            app.undo()
            assert app.profile == before
            app.show_library()
            app.library_tree.selection_set(identity)
            root.update()
            assert app.library_tree.item(identity, "values")[0] == "My Blue / Black"
            assert all(button.winfo_ismapped() for button in app.library_actions)
        if gpu_smoke:
            app.timeline.set(3.0)
            app.toggle_gpu()
            deadline = time.monotonic() + 25
            while app.gpu.frames < 8 and time.monotonic() < deadline:
                root.update()
                time.sleep(0.01)
            if app.gpu.frames < 8 or not app.gpu_mode:
                app.gpu.close()
                app.closed = True
                root.destroy()
                raise AssertionError("Native GPU preview did not produce frames")
            if snapshot:
                ImageGrab.grab(
                    bbox=(
                        root.winfo_rootx(),
                        root.winfo_rooty(),
                        root.winfo_rootx() + root.winfo_width(),
                        root.winfo_rooty() + root.winfo_height(),
                    )
                ).save(snapshot)
        if snapshot and not gpu_smoke:
            import ctypes

            window = app.library if library_smoke else app.gallery if gallery else root
            hwnd = ctypes.windll.user32.GetAncestor(window.winfo_id(), 2)
            ImageGrab.grab(window=hwnd).save(snapshot)
        app.closed = True
        app.gpu.close()
        try:
            app.render_jobs.get_nowait()
        except queue.Empty:
            pass
        app.render_jobs.put_nowait(None)
        root.destroy()
        if library_tmp:
            library_tmp.cleanup()
        return
    app.start_load()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=backend.DEFAULT_INPUT)
    parser.add_argument("--xextool", type=Path, default=backend.find_tool())
    parser.add_argument("--output", type=Path)
    parser.add_argument("--project", type=Path)
    parser.add_argument("--preset", choices=list(palettes.BY_ID))
    parser.add_argument("--animation", choices=["modern"], default="modern", help=argparse.SUPPRESS)
    parser.add_argument("--language", choices=["en", "de"])
    parser.add_argument("--target", choices=["hdd", "flash", "nand"], default="hdd")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--smoke-ui", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--small", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--snapshot", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--gallery", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-gpu", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-library", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke-setup", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    preset = args.preset or "blue"
    if args.smoke_ui or args.smoke_setup:
        gui(
            True,
            args.snapshot,
            args.small,
            preset,
            args.gallery,
            args.language,
            args.smoke_gpu,
            args.smoke_library,
            args.smoke_setup,
        )
    elif args.output:
        p = palettes.palette(preset)
        target = "flash" if args.target == "nand" else args.target
        if args.project:
            checked = read_project(args.project)
            p = checked["profile"]
            args.input, args.xextool, target = (
                Path(checked["source"]),
                Path(checked["xextool"]),
                checked["target"],
            )
        report = backend.build(
            args.input, args.output, args.xextool, p["effects"], target, args.overwrite, p
        )
        if getattr(__import__("sys"), "stdout", None):
            print(
                json.dumps(
                    {
                        k: report[k]
                        for k in ("status", "output", "roundtrip_equal", "changed_byte_count")
                    },
                    indent=2,
                )
            )
    else:
        gui(language=args.language)


if __name__ == "__main__":
    main()
