import os, math, json, re, uuid
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
folder1 = os.path.join(BASE_DIR, "maps")
folder2 = os.path.join(BASE_DIR, "scn")

os.makedirs(folder1, exist_ok=True)
os.makedirs(folder2, exist_ok=True)

class ImageMarkerApp:
    """A tool designed to make modding with coordinates easier with a visual guide, also an initial SCN Editor"""
    def __init__(self, root):
        self.root = root
        self.root.title("Halo Wars SCN Coordinate Guider Version 3.6.12")
        self.root.resizable(True, True)

        # Viewport limits (maximum size)
        self.max_viewport_width = 800
        self.max_viewport_height = 800

        # Current viewport size (adjusted per image since maps vary in size)
        self.viewport_width = self.max_viewport_width
        self.viewport_height = self.max_viewport_height

        # Map size in logical coordinates (set when an image loads)
        self.map_width = self.viewport_width
        self.map_height = self.viewport_height
        # Backwards compat aliases
        self.original_width = self.map_width
        self.original_height = self.map_height

        # Base and display images
        self.base_image = None          # original PhotoImage
        self.display_image = None       # scaled PhotoImage used on canvas
        self.image = None               # kept for compatibility
        self.image_id = None

        # Zoom handling
        self.zoom_levels = [0.5, 1.0, 2.0, 3.0]  # allowed zoom factors
        self.zoom_index = 1                      # index into zoom_levels (start at 1.0)
        self.scale = 1.0                         # actual scale is display_pixels/map_units

        # Non-blocking batch add (keeps UI responsive when importing 1k+ markers)
        self.batch_after_id = None
        self._batch_items = None
        self._batch_index = 0
        self.batch_total = 0
        self.batch_chunk_size = 150
        self._batch_add_fn = None
        self._batch_done_fn = None
        self._batch_label = ""

        # Initialize variables

        self.markers = []     # list of marker dicts
        self.grid_lines = []  # grid line/cross ids

        # Listbox ↔ marker mapping (because search can filter the list)
        self.listbox_marker_uids = []

        # Group visibility (name -> bool)
        self.group_visibility = {"Ungrouped": True}

        # Track current map image name for export/import metadata
        self.current_image_name = None

        # SCN editing state (current map's paired scn)
        self.scn_path = None
        self.scn_lines = None

        # Parsed items
        self.scn_objects = []     # parsed objects from <Objects>
        self.scn_positions = []   # parsed player placement positions from <Positions>

        # Listbox mapping: listbox index -> (Position/Object, index)
        self.scn_items_index_by_list = []

        # Bounds for in-place editing
        self._scn_objects_bounds = None     # (start_idx, end_idx) for <Objects> block
        self._scn_positions_bounds = None   # (start_idx, end_idx) for <Positions> block

        # Main horizontal layout: left = canvas+controls, right = marker list
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Canvas with scrollbars (in left frame)
        canvas_frame = tk.Frame(left_frame)
        canvas_frame.pack()

        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.viewport_width,
            height=self.viewport_height,
            bg="black"
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        vbar.grid(row=0, column=1, sticky="ns")

        hbar = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        hbar.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)

        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        # Coordinate + name controls (left, under canvas)
        controls_frame = tk.Frame(left_frame)
        controls_frame.pack(pady=5)

        vcmd = (self.root.register(self.validate_int), '%S', '%P')

        tk.Label(controls_frame, text="X:").pack(side=tk.LEFT)
        self.x_entry = tk.Entry(controls_frame, width=8, validate='key', validatecommand=vcmd)
        self.x_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(controls_frame, text="Y:").pack(side=tk.LEFT)
        self.y_entry = tk.Entry(controls_frame, width=8, validate='key', validatecommand=vcmd)
        self.y_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(controls_frame, text="Name:").pack(side=tk.LEFT)
        self.name_entry = tk.Entry(controls_frame, width=20)
        self.name_entry.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(controls_frame, text="Group:").pack(side=tk.LEFT)
        self.group_var = tk.StringVar(value="Ungrouped")
        self.group_combo = ttk.Combobox(
            controls_frame,
            width=16,
            textvariable=self.group_var,
            state="normal"
        )
        self.group_combo.pack(side=tk.LEFT, padx=(0, 5))

        # Marker type selector
        tk.Label(controls_frame, text="Type:").pack(side=tk.LEFT)

        self.marker_type_var = tk.StringVar()
        self.marker_type_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.marker_type_var,
            state="readonly",
            width=18,
            values=[
                "Default (circle)",
                "UNSC Base (U)",
                "Covenant Base (C)",
                "Reactor (star)",
                "Player 1 (P1)",
                "Player 2 (P2)",
                "Player 3 (P3)",
                "Player 4 (P4)",
                "Player 5 (P5)",
                "Player 6 (P6)",
                "Creeps (N)"
            ]
        )
        self.marker_type_combo.current(0)
        self.marker_type_combo.pack(side=tk.LEFT, padx=(0, 5))

        # Marker type IDs used internally (also used by the Filters tab)
        self.marker_type_ids = [
            "default", "unsc", "cov", "reactor",
            "PL1", "PL2", "PL3", "PL4", "PL5", "PL6",
            "N1"
        ]
        self.marker_type_labels = {
            "default": "Default (circle)",
            "unsc": "UNSC Base (U)",
            "cov": "Covenant Base (C)",
            "reactor": "Reactor (star)",
            "PL1": "Player 1 (P1)",
            "PL2": "Player 2 (P2)",
            "PL3": "Player 3 (P3)",
            "PL4": "Player 4 (P4)",
            "PL5": "Player 5 (P5)",
            "PL6": "Player 6 (P6)",
            "N1": "Creeps (N)"
        }

        # Filter state (all visible by default)
        self.marker_filter_vars = {}
        self.visible_marker_types = set(self.marker_type_ids)


        # Button to mark the image
        self.mark_button = tk.Button(controls_frame, text="Mark", command=self.mark_image)
        self.mark_button.pack(side=tk.LEFT, padx=5)

        # Map selector, clear button, grid + zoom controls (left, under controls)
        map_frame = tk.Frame(left_frame)
        map_frame.pack(pady=5)

        # pairs with the selected image (HW1 maps)
        self.scn_pair = [
            "baron_1_swe.scn", "beaconhill_2.scn", "beasleys_plateau.scn", "blood_gulch.scn", "campaigntutorial.scn",
            "campaigntutorialadvanced.scn", "chasms.scn", "crevice.scn", "exile.scn",
            "fort_deen.scn", "frozen_valley.scn", "glacial_ravine_3.scn", "labyrinth.scn", "phxscn01.scn",
            "phxscn02.scn", "phxscn03.scn", "phxscn04.scn", "phxscn05.scn", "phxscn06.scn",
            "phxscn07.scn", "phxscn08.scn", "phxscn09.scn", "phxscn10.scn", "phxscn11.scn",
            "phxscn12.scn", "phxscn13.scn", "phxscn14.scn", "phxscn15.scn", "pirth_outskirts.scn",
            "redriver_1.scn", "release.scn", "repository.scn", "terminal_moraine.scn", "the_docks.scn", "tundra.scn",
            # HW2 example
            "minimap_fort_jordan.scn", "minimap_mp_bridges.scn"
        ]

        self.image_selector = ttk.Combobox(
            map_frame,
            values=[
                # HW1 maps
                "baron_1_swe.png", "beaconhill_2.png", "beasleys_plateau.png", "blood_gulch.png", "campaigntutorial.png",
                "campaigntutorialadvanced.png", "chasms.png", "crevice.png", "exile.png",
                "fort_deen.png", "frozen_valley.png", "glacial_ravine_3.png", "labyrinth.png", "phxscn01.png",
                "phxscn02.png", "phxscn03.png", "phxscn04.png", "phxscn05.png", "phxscn06.png",
                "phxscn07.png", "phxscn08.png", "phxscn09.png", "phxscn10.png", "phxscn11.png",
                "phxscn12.png", "phxscn13.png", "phxscn14.png", "phxscn15.png", "pirth_outskirts.png",
                "redriver_1.png", "release.png", "repository.png", "terminal_moraine.png", "the_docks.png", "tundra.png",
                # HW2 minimaps
                "minimap_fort_jordan.png", "minimap_mp_boneyard.png", "minimap_mp_bridges.png", "minimap_mp_caldera.png",
                "minimap_mp_eagle.png", "minimap_mp_ff_stopthesignal.png", "minimap_mp_fracture.png",
                "minimap_mp_razorblade.png", "minimap_mp_ricochet.png", "minimap_mp_stopthesignal_firefight.png", "minimap_mp_veteran.png",
                "minimap_sp_ep2_m01.png", "minimap_sp_ep2_m02.png", "minimap_sp_ep2_m04.png", "minimap_sp_ep2_m05.png",
                "minimap_sp_m01.png", "minimap_sp_m02.png", "minimap_sp_m03.png", "minimap_sp_m04.png",
                "minimap_sp_m05.png", "minimap_sp_m06.png", "minimap_sp_m07.png",
                "minimap_sp_m08.png", "minimap_sp_prologue.png", "minimap_sp_tutorial.png", "rm_evenflow.png"
            ],
            state="readonly",
            width=25
        )
        self.image_selector.current(0)
        self.image_selector.pack(side=tk.LEFT, padx=5)
        self.image_selector.bind("<<ComboboxSelected>>", self.update_image)

        # Button to clear markers on the image
        self.clear_button = tk.Button(map_frame, text="Clear Markers", command=self.clear_markers)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Auto populate markers from paired SCN file
        self.autopop_button = tk.Button(map_frame, text="Auto Populate", command=self.auto_populate_from_scn)
        self.autopop_button.pack(side=tk.LEFT, padx=5)

        # Grid controls
        tk.Label(map_frame, text="Grid step:").pack(side=tk.LEFT)
        self.grid_step_entry = tk.Entry(map_frame, width=5)
        self.grid_step_entry.insert(0, "32")
        self.grid_step_entry.pack(side=tk.LEFT, padx=(2, 5))

        self.show_grid_var = tk.BooleanVar(value=True)
        self.grid_check = tk.Checkbutton(
            map_frame, text="Show Grid",
            variable=self.show_grid_var,
            command=self.toggle_grid
        )
        self.grid_check.pack(side=tk.LEFT, padx=2)

        self.grid_apply_button = tk.Button(map_frame, text="Apply Grid", command=self.draw_grid)
        self.grid_apply_button.pack(side=tk.LEFT, padx=5)

        # Boundary controls
        tk.Label(map_frame, text="Bounds:").pack(side=tk.LEFT, padx=(10, 0))

        self.show_boundaries_var = tk.BooleanVar(value=True)
        self.bounds_check = tk.Checkbutton(
            map_frame,
            text="Show",
            variable=self.show_boundaries_var,
            command=self.toggle_boundaries
        )
        self.bounds_check.pack(side=tk.LEFT, padx=(2, 2))

        # Marker filters override (ignores the Filters tab)
        self.ignore_marker_filters_var = tk.BooleanVar(value=False)
        self.all_markers_check = tk.Checkbutton(
            map_frame,
            text="All markers",
            variable=self.ignore_marker_filters_var,
            command=self.toggle_marker_filter_override
        )
        self.all_markers_check.pack(side=tk.LEFT, padx=(8, 2))

        # Zoom controls

        tk.Label(map_frame, text="Zoom:").pack(side=tk.LEFT, padx=(10, 0))
        self.zoom_out_button = tk.Button(map_frame, text="-", width=2, command=self.zoom_out)
        self.zoom_out_button.pack(side=tk.LEFT)
        self.zoom_in_button = tk.Button(map_frame, text="+", width=2, command=self.zoom_in)
        self.zoom_in_button.pack(side=tk.LEFT)
        self.zoom_value_label = tk.Label(map_frame, text="100%")
        self.zoom_value_label.pack(side=tk.LEFT, padx=(2, 0))

        # Right sidebar: Legend (left) + tabs (Markers/Boundaries)
        sidebar_frame = tk.Frame(right_frame)
        sidebar_frame.pack(fill=tk.BOTH, expand=True)

        # Legend panel (left of lists)
        legend_frame = tk.LabelFrame(sidebar_frame, text="Legend")
        legend_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6), pady=5)

        self.build_legend_panel(legend_frame)

        # Tabs for lists
        notebook = ttk.Notebook(sidebar_frame)
        notebook.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Markers tab
        markers_tab = tk.Frame(notebook)
        notebook.add(markers_tab, text="Markers")

        markers_frame = tk.Frame(markers_tab)
        markers_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Header row: label + delete button
        header_frame = tk.Frame(markers_frame)
        header_frame.pack(fill=tk.X)

        tk.Label(header_frame, text="Markers:").pack(side=tk.LEFT, anchor="w")

        self.delete_marker_button = tk.Button(
            header_frame,
            text="Delete",
            command=self.delete_selected_markers
        )
        self.delete_marker_button.pack(side=tk.RIGHT)

        # Search bar (filters the marker list by name/group/type)
        search_frame = tk.Frame(markers_frame)
        search_frame.pack(fill=tk.X, pady=(2, 4))

        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.marker_search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.marker_search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        tk.Button(search_frame, text="Clear", command=self.clear_search).pack(side=tk.RIGHT)

        # Update list as you type
        self.marker_search_var.trace_add("write", lambda *_: self.refresh_marker_listbox())

        list_frame = tk.Frame(markers_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.marker_listbox = tk.Listbox(
            list_frame,
            height=25,
            width=30,
            selectmode=tk.EXTENDED,  # allow multi-select for distance measurement
            exportselection=False
        )
        self.marker_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        marker_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.marker_listbox.yview)
        marker_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.marker_listbox.config(yscrollcommand=marker_scroll.set)

        # When a marker is selected, pan to it (single selection case)
        self.marker_listbox.bind("<<ListboxSelect>>", self.on_marker_select)

        # Import/Export + distance buttons under the list
        buttons_frame = tk.Frame(markers_frame)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))

        self.export_button = tk.Button(buttons_frame, text="Export Markers", command=self.export_markers)
        self.export_button.pack(side=tk.LEFT, padx=2)

        self.import_button = tk.Button(buttons_frame, text="Import Markers", command=self.import_markers)
        self.import_button.pack(side=tk.LEFT, padx=2)

        self.measure_button = tk.Button(buttons_frame, text="Measure Dist", command=self.measure_distance)
        self.measure_button.pack(side=tk.LEFT, padx=2)


        # Grouping + show/hide per group
        groups_box = tk.LabelFrame(markers_frame, text="Groups")
        groups_box.pack(fill=tk.BOTH, expand=False, pady=(6, 0))

        group_top = tk.Frame(groups_box)
        group_top.pack(fill=tk.X, pady=(2, 2))

        tk.Label(group_top, text="Group:").pack(side=tk.LEFT)
        self.group_assign_var = tk.StringVar()
        self.group_assign_entry = tk.Entry(group_top, textvariable=self.group_assign_var, width=22)
        self.group_assign_entry.pack(side=tk.LEFT, padx=(5, 5))

        tk.Button(group_top, text="Assign Selected", command=self.assign_selected_to_group).pack(side=tk.LEFT, padx=2)
        tk.Button(group_top, text="Ungroup", command=self.ungroup_selected_markers).pack(side=tk.LEFT, padx=2)

        group_list_frame = tk.Frame(groups_box)
        group_list_frame.pack(fill=tk.BOTH, expand=True)

        self.group_listbox = tk.Listbox(group_list_frame, height=6, exportselection=False)
        self.group_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        group_scroll = tk.Scrollbar(group_list_frame, orient=tk.VERTICAL, command=self.group_listbox.yview)
        group_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.group_listbox.config(yscrollcommand=group_scroll.set)

        self.group_listbox.bind("<<ListboxSelect>>", self.on_group_select)
        self.group_listbox.bind("<Double-Button-1>", self.toggle_selected_group_visibility)

        self.refresh_group_listbox()


        # Batch status (used for large imports/autopop)
        self.batch_status_var = tk.StringVar(value="")
        self.batch_status_label = tk.Label(markers_frame, textvariable=self.batch_status_var, anchor="w")
        self.batch_status_label.pack(fill=tk.X, pady=(4, 0))

        # Boundaries tab
        bounds_tab = tk.Frame(notebook)
        notebook.add(bounds_tab, text="Boundaries")

        bounds_frame = tk.Frame(bounds_tab)
        bounds_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        bounds_header = tk.Frame(bounds_frame)
        bounds_header.pack(fill=tk.X)

        tk.Label(bounds_header, text="Boundaries:").pack(side=tk.LEFT, anchor="w")

        tk.Label(bounds_header, text="Color:").pack(side=tk.RIGHT, padx=(2, 0))

        self.boundary_color_edit_var = tk.StringVar(value="Default")
        self.boundary_color_edit_combo = ttk.Combobox(
            bounds_header,
            textvariable=self.boundary_color_edit_var,
            state="disabled",  # enabled only when a boundary is selected
            width=8,
            values=["Default", "Red", "Green", "Blue"]
        )
        self.boundary_color_edit_combo.pack(side=tk.RIGHT, padx=(2, 0))
        self.boundary_color_edit_combo.bind("<<ComboboxSelected>>", self.on_boundary_edit_color_changed)

        bounds_list_frame = tk.Frame(bounds_frame)
        bounds_list_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.boundary_listbox = tk.Listbox(
            bounds_list_frame,
            height=25,
            width=36,
            selectmode=tk.EXTENDED,
            exportselection=False
        )
        self.boundary_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bounds_scroll = tk.Scrollbar(bounds_list_frame, orient=tk.VERTICAL, command=self.boundary_listbox.yview)
        bounds_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.boundary_listbox.config(yscrollcommand=bounds_scroll.set)

        self.boundary_listbox.bind("<<ListboxSelect>>", self.on_boundary_select)

        # Filters tab
        filters_tab = tk.Frame(notebook)
        notebook.add(filters_tab, text="Filters")

        filters_frame = tk.Frame(filters_tab)
        filters_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(filters_frame, text="Show marker types:").pack(anchor="w")

        checks_frame = tk.Frame(filters_frame)
        checks_frame.pack(fill=tk.X, pady=(6, 8))

        # 2 column checkbox layout
        for i, type_id in enumerate(self.marker_type_ids):
            var = tk.BooleanVar(value=True)
            self.marker_filter_vars[type_id] = var
            label = self.marker_type_labels.get(type_id, type_id)
            cb = tk.Checkbutton(
                checks_frame,
                text=label,
                variable=var,
                command=self.on_marker_filter_changed
            )
            cb.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=2)

        buttons_row = tk.Frame(filters_frame)
        buttons_row.pack(fill=tk.X, pady=(6, 0))

        tk.Button(buttons_row, text="Show All", command=self.filter_show_all).pack(side=tk.LEFT, padx=2)
        tk.Button(buttons_row, text="Hide All", command=self.filter_hide_all).pack(side=tk.LEFT, padx=2)
        tk.Button(buttons_row, text="Invert", command=self.filter_invert).pack(side=tk.LEFT, padx=2)

        tk.Label(
            filters_frame,
            text='Tip: Hidden marker types are not drawn. The Markers list shows "[HIDDEN]" when filters are active.'
        ).pack(anchor="w", pady=(10, 0))


        # SCN Editor tab (basic editing for <Objects> + <Positions>)
        scn_tab = tk.Frame(notebook)
        notebook.add(scn_tab, text="SCN Editor")

        scn_frame = tk.Frame(scn_tab)
        scn_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        scn_top = tk.Frame(scn_frame)
        scn_top.pack(fill=tk.X)

        self.scn_status_var = tk.StringVar(value="No SCN loaded.")
        tk.Label(scn_top, textvariable=self.scn_status_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(scn_top, text="Save SCN", command=self.save_current_scn).pack(side=tk.RIGHT, padx=2)
        tk.Button(scn_top, text="Sync Markers ↔ SCN", command=self.sync_scn_objects_from_markers).pack(side=tk.RIGHT, padx=2)
        tk.Button(scn_top, text="Load SCN", command=self.load_scn_objects_for_current_map).pack(side=tk.RIGHT, padx=2)

        scn_body = tk.Frame(scn_frame)
        scn_body.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        # Item list (Objects + PlayerPlacement Positions)
        scn_list_frame = tk.Frame(scn_body)
        scn_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Search (filters SCN items)
        scn_search_frame = tk.Frame(scn_list_frame)
        scn_search_frame.pack(fill=tk.X, pady=(0, 4))

        tk.Label(scn_search_frame, text="Search:").pack(side=tk.LEFT)
        self.scn_search_var = tk.StringVar()
        self.scn_search_entry = tk.Entry(scn_search_frame, textvariable=self.scn_search_var)
        self.scn_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        tk.Button(scn_search_frame, text="Clear", command=self.clear_scn_search).pack(side=tk.RIGHT)

        # Update list as you type
        self.scn_search_var.trace_add("write", lambda *_: self.refresh_scn_object_listbox())

        scn_lb_frame = tk.Frame(scn_list_frame)
        scn_lb_frame.pack(fill=tk.BOTH, expand=True)

        self.scn_object_listbox = tk.Listbox(scn_lb_frame, height=18, width=52, exportselection=False)
        self.scn_object_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scn_scroll = tk.Scrollbar(scn_lb_frame, orient=tk.VERTICAL, command=self.scn_object_listbox.yview)
        scn_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.scn_object_listbox.config(yscrollcommand=scn_scroll.set)
        self.scn_object_listbox.bind("<<ListboxSelect>>", self.on_scn_object_select)

        # Selected item editor
        editor_frame = tk.LabelFrame(scn_body, text="Selected SCN Item")
        editor_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(8, 0))

        # Keep widget groups so we can show/hide per selected kind
        self._scn_obj_widgets = []
        self._scn_pp_widgets = []

        # Object editor vars
        self.scn_edit_is_squad_var = tk.StringVar()
        self.scn_edit_player_var = tk.StringVar()
        self.scn_edit_id_var = tk.StringVar()
        self.scn_edit_tint_var = tk.StringVar()
        self.scn_edit_editorname_var = tk.StringVar()
        self.scn_edit_pos_x_var = tk.StringVar()
        self.scn_edit_pos_y_var = tk.StringVar()
        self.scn_edit_pos_z_var = tk.StringVar()
        self.scn_edit_forward_var = tk.StringVar()
        self.scn_edit_right_var = tk.StringVar()
        self.scn_edit_group_var = tk.StringVar()
        self.scn_edit_vvi_var = tk.StringVar()
        self.scn_edit_objtype_var = tk.StringVar()

        def _scn_obj_row(r, label, var, w=26, *, readonly=False):
            lab = tk.Label(editor_frame, text=label)
            lab.grid(row=r, column=0, sticky="w", padx=4, pady=2)
            ent = tk.Entry(editor_frame, textvariable=var, width=w, state=("readonly" if readonly else "normal"))
            ent.grid(row=r, column=1, sticky="w", padx=4, pady=2)
            self._scn_obj_widgets.extend([lab, ent])

        r = 0
        _scn_obj_row(r, "EditorName", self.scn_edit_editorname_var); r += 1

        lab = tk.Label(editor_frame, text="Object")
        lab.grid(row=r, column=0, sticky="w", padx=4, pady=2)
        ent = tk.Entry(editor_frame, textvariable=self.scn_edit_objtype_var, width=26, state="readonly")
        ent.grid(row=r, column=1, sticky="w", padx=4, pady=2)
        self._scn_obj_widgets.extend([lab, ent])
        r += 1

        _scn_obj_row(r, "ID", self.scn_edit_id_var); r += 1
        _scn_obj_row(r, "Player", self.scn_edit_player_var); r += 1
        _scn_obj_row(r, "IsSquad", self.scn_edit_is_squad_var); r += 1
        _scn_obj_row(r, "TintValue", self.scn_edit_tint_var); r += 1
        _scn_obj_row(r, "Position X", self.scn_edit_pos_x_var); r += 1
        _scn_obj_row(r, "Position Y", self.scn_edit_pos_y_var); r += 1
        _scn_obj_row(r, "Position Z", self.scn_edit_pos_z_var); r += 1
        _scn_obj_row(r, "Forward", self.scn_edit_forward_var); r += 1
        _scn_obj_row(r, "Right", self.scn_edit_right_var); r += 1
        _scn_obj_row(r, "Group", self.scn_edit_group_var); r += 1
        _scn_obj_row(r, "VisualVarIdx", self.scn_edit_vvi_var); r += 1

        # PlayerPlacement (<Positions>/</Position>) editor vars
        self.scn_pp_number_var = tk.StringVar()
        self.scn_pp_player_var = tk.StringVar()
        self.scn_pp_defaultcamera_var = tk.StringVar()
        self.scn_pp_camyaw_var = tk.StringVar()
        self.scn_pp_campitch_var = tk.StringVar()
        self.scn_pp_camzoom_var = tk.StringVar()
        self.scn_pp_unit1_var = tk.StringVar()
        self.scn_pp_unit2_var = tk.StringVar()
        self.scn_pp_unit3_var = tk.StringVar()
        self.scn_pp_unit4_var = tk.StringVar()
        self.scn_pp_rally_var = tk.StringVar()

        def _scn_pp_row(r, label, var, w=26):
            lab = tk.Label(editor_frame, text=label)
            lab.grid(row=r, column=0, sticky="w", padx=4, pady=2)
            ent = tk.Entry(editor_frame, textvariable=var, width=w)
            ent.grid(row=r, column=1, sticky="w", padx=4, pady=2)
            self._scn_pp_widgets.extend([lab, ent])

        # Start PP rows at current r but hide them until a Position is selected
        pp_start_r = r
        _scn_pp_row(r, "PP Number", self.scn_pp_number_var); r += 1
        _scn_pp_row(r, "PP Player", self.scn_pp_player_var); r += 1
        _scn_pp_row(r, "PP Position X", self.scn_edit_pos_x_var); r += 1
        _scn_pp_row(r, "PP Position Y", self.scn_edit_pos_y_var); r += 1
        _scn_pp_row(r, "PP Position Z", self.scn_edit_pos_z_var); r += 1
        _scn_pp_row(r, "PP Forward", self.scn_edit_forward_var); r += 1
        _scn_pp_row(r, "PP DefaultCamera", self.scn_pp_defaultcamera_var); r += 1
        _scn_pp_row(r, "PP CameraYaw", self.scn_pp_camyaw_var); r += 1
        _scn_pp_row(r, "PP CameraPitch", self.scn_pp_campitch_var); r += 1
        _scn_pp_row(r, "PP CameraZoom", self.scn_pp_camzoom_var); r += 1
        _scn_pp_row(r, "PP UnitStartObject1", self.scn_pp_unit1_var); r += 1
        _scn_pp_row(r, "PP UnitStartObject2", self.scn_pp_unit2_var); r += 1
        _scn_pp_row(r, "PP UnitStartObject3", self.scn_pp_unit3_var); r += 1
        _scn_pp_row(r, "PP UnitStartObject4", self.scn_pp_unit4_var); r += 1
        _scn_pp_row(r, "PP RallyStartObject", self.scn_pp_rally_var); r += 1

        scn_btns = tk.Frame(editor_frame)
        scn_btns.grid(row=r, column=0, columnspan=2, sticky="w", padx=4, pady=(6, 4))

        tk.Button(scn_btns, text="Apply", command=self.apply_scn_selected_item_changes).pack(side=tk.LEFT, padx=2)
        tk.Button(scn_btns, text="Use Selected Marker Pos", command=self.set_scn_selected_item_pos_from_selected_marker).pack(side=tk.LEFT, padx=2)
        tk.Button(scn_btns, text="Delete", command=self.delete_selected_scn_item).pack(side=tk.LEFT, padx=2)

        # Hide PP widgets by default
        for w in self._scn_pp_widgets:
            w.grid_remove()

        # Add new object (Objects only)
        add_frame = tk.LabelFrame(scn_frame, text="Add Object (appends inside <Objects>)")
        add_frame.pack(fill=tk.X, pady=(8, 0))

        self.scn_add_type_var = tk.StringVar(value="hook_bldg_sniperplatform_01")
        self.scn_add_player_var = tk.StringVar(value="0")
        self.scn_add_is_squad_var = tk.StringVar(value="false")
        self.scn_add_tint_var = tk.StringVar(value="1")
        self.scn_add_y_var = tk.StringVar(value="0")
        self.scn_add_forward_var = tk.StringVar(value="0,0,1")
        self.scn_add_right_var = tk.StringVar(value="1,0,0")
        self.scn_add_group_var = tk.StringVar(value="-1")
        self.scn_add_vvi_var = tk.StringVar(value="0")

        add_row1 = tk.Frame(add_frame)
        add_row1.pack(fill=tk.X, pady=(2, 2))
        tk.Label(add_row1, text="Object Type:").pack(side=tk.LEFT)
        tk.Entry(add_row1, textvariable=self.scn_add_type_var, width=30).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row1, text="Player:").pack(side=tk.LEFT)
        tk.Entry(add_row1, textvariable=self.scn_add_player_var, width=6).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row1, text="IsSquad:").pack(side=tk.LEFT)
        tk.Entry(add_row1, textvariable=self.scn_add_is_squad_var, width=6).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row1, text="Tint:").pack(side=tk.LEFT)
        tk.Entry(add_row1, textvariable=self.scn_add_tint_var, width=6).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row1, text="Y:").pack(side=tk.LEFT)
        tk.Entry(add_row1, textvariable=self.scn_add_y_var, width=6).pack(side=tk.LEFT, padx=(5, 0))

        add_row2 = tk.Frame(add_frame)
        add_row2.pack(fill=tk.X, pady=(0, 2))
        tk.Label(add_row2, text="Forward:").pack(side=tk.LEFT)
        tk.Entry(add_row2, textvariable=self.scn_add_forward_var, width=18).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row2, text="Right:").pack(side=tk.LEFT)
        tk.Entry(add_row2, textvariable=self.scn_add_right_var, width=18).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row2, text="Group:").pack(side=tk.LEFT)
        tk.Entry(add_row2, textvariable=self.scn_add_group_var, width=6).pack(side=tk.LEFT, padx=(5, 10))
        tk.Label(add_row2, text="VVI:").pack(side=tk.LEFT)
        tk.Entry(add_row2, textvariable=self.scn_add_vvi_var, width=6).pack(side=tk.LEFT, padx=(5, 10))

        add_row3 = tk.Frame(add_frame)
        add_row3.pack(fill=tk.X, pady=(0, 4))
        tk.Button(add_row3, text="Add at Selected Marker", command=self.add_scn_object_from_selected_marker).pack(side=tk.LEFT, padx=2)
        tk.Label(add_row3, text="(Select a marker first)").pack(side=tk.LEFT, padx=(6, 0))
        # Drag state
        self._drag_uid = None
        self._drag_last_canvas = (0, 0)
        
        # Map boundary polylines (camera/playable/etc)
        self.boundaries = []  # list of {"name", "type", "points", "canvas_ids"}

        self.boundary_selected_indices = []  # cache selection so combobox clicks don't clear it

        # Left-click: drag existing markers, or click empty space to place a new marker
        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)

        # Middle mouse drag to pan
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)

        # right click drag also pans
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)

        # Load default image
        self.update_image()

    # Basic helpers

    def validate_int(self, char_typed, new_value):
        if new_value == "":
            return True
        return new_value.isdigit()

    def update_zoom_label(self):
        percent = int(round(self.scale * 100))
        self.zoom_value_label.config(text=f"{percent}%")

    # Non-blocking batch operations

    def cancel_batch(self):
        """Cancel any in-progress batch add"""
        if getattr(self, "batch_after_id", None) is not None:
            try:
                self.root.after_cancel(self.batch_after_id)
            except Exception:
                pass

        self.batch_after_id = None
        self._batch_items = None
        self._batch_add_fn = None
        self._batch_done_fn = None
        self._batch_index = 0
        self.batch_total = 0
        self._batch_label = ""

        if hasattr(self, "batch_status_var"):
            self.batch_status_var.set("")

        # Re-enable controls (safe even if already enabled)
        for attr in ("autopop_button", "import_button", "export_button", "mark_button"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.config(state="normal")
                except Exception:
                    pass

    def start_batch(self, items, add_fn, done_fn=None, *, chunk_size=None, delay_ms=1, label="Working"):
        """
        Run a large UI operation in chunks via after() to keep Tk responsive

        items: iterable of work specs
        add_fn(spec): must do the actual add (marker/boundary/etc) on the UI thread
        done_fn(): called after all items are processed
        """
        self.cancel_batch()

        self._batch_items = list(items) if items is not None else []
        self._batch_add_fn = add_fn
        self._batch_done_fn = done_fn
        self._batch_index = 0
        self.batch_total = len(self._batch_items)
        self.batch_chunk_size = int(chunk_size or getattr(self, "batch_chunk_size", 150))
        self._batch_label = label or "Working"

        # Disable controls that would conflict with an in-progress import/autopop
        for attr in ("autopop_button", "import_button", "export_button", "mark_button"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.config(state="disabled")
                except Exception:
                    pass

        if hasattr(self, "batch_status_var"):
            self.batch_status_var.set(f"{self._batch_label}: 0/{self.batch_total}")

        # Schedule the first chunk
        self.batch_after_id = self.root.after(max(1, int(delay_ms)), self.batch_step)

    def batch_step(self):
        if not self._batch_items or self._batch_add_fn is None:
            # nothing to do
            self.cancel_batch()
            return

        # Process next chunk
        end = min(self._batch_index + self.batch_chunk_size, self.batch_total)
        for i in range(self._batch_index, end):
            try:
                self._batch_add_fn(self._batch_items[i])
            except Exception:
                # Skip bad entries, keep going
                pass

        self._batch_index = end

        if hasattr(self, "batch_status_var"):
            self.batch_status_var.set(f"{self._batch_label}: {self._batch_index}/{self.batch_total}")

        if self._batch_index >= self.batch_total:
            done = self._batch_done_fn
            # Clear batch state + re-enable UI first
            self.cancel_batch()
            if callable(done):
                try:
                    done()
                except Exception:
                    pass
            return

        # Schedule next chunk
        self.batch_after_id = self.root.after(1, self.batch_step)

    # Map canvas transform

    def map_to_canvas(self, map_x, map_y):
        """Convert logical map coords (map_width, map_height) to canvas coords"""
        scale = self.scale or 1.0
        display_h = self.map_height * scale
        canvas_x = map_x * scale
        canvas_y = display_h - map_y * scale
        return canvas_x, canvas_y

    def canvas_to_map(self, canvas_x, canvas_y):
        """Convert canvas coords back into logical map coords"""
        scale = self.scale or 1.0
        if scale == 0:
            return 0, 0
        display_h = self.map_height * scale
        map_x = int(round(canvas_x / scale))
        map_y = int(round((display_h - canvas_y) / scale))
        return map_x, map_y

    def get_view_center_in_map_coords(self):
        """Return the current viewport center in map coords"""
        if self.map_width == 0 or self.map_height == 0:
            return 0, 0
        x0 = self.canvas.canvasx(0)
        y0 = self.canvas.canvasy(0)
        x1 = self.canvas.canvasx(self.viewport_width)
        y1 = self.canvas.canvasy(self.viewport_height)
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        return self.canvas_to_map(cx, cy)

    def center_on_map_coord(self, map_x, map_y):
        """Center the viewport around a given map coordinate"""
        scale = self.scale or 1.0
        display_w = self.map_width * scale
        display_h = self.map_height * scale

        canvas_x, canvas_y = self.map_to_canvas(map_x, map_y)

        target_x = canvas_x - self.viewport_width / 2
        target_y = canvas_y - self.viewport_height / 2

        max_x = max(0, display_w - self.viewport_width)
        max_y = max(0, display_h - self.viewport_height)

        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))

        if display_w > 0:
            self.canvas.xview_moveto(target_x / display_w)
        if display_h > 0:
            self.canvas.yview_moveto(target_y / display_h)

    # Image loading and zoom

    def load_image(self, image_path):
        # Clear previous content
        self.canvas.delete("all")
        self.cancel_batch()
        self.clear_markers()
        self.markers = []
        self.grid_lines = []
        self.canvas.delete("measure")
        self.image_id = None

        # Track current map name
        self.current_image_name = image_path

        # Load base image
        path = os.path.join(folder1, image_path)
        try:
            self.base_image = tk.PhotoImage(file=path)
        except Exception as e:
            messagebox.showerror(
                "Image Loading",
                f"Failed to load image '{path}':\n{e}"
            )
            self.base_image = None
            self.current_image_name = None
            return

        # Map size in logical coords
        self.map_width = self.base_image.width()
        self.map_height = self.base_image.height()
        self.original_width = self.map_width
        self.original_height = self.map_height

        # Reset zoom to 100%
        self.zoom_index = 1
        self.scale = 1.0

        # Create image item placeholder and apply zoom
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW)
        self.apply_zoom()

    def apply_zoom(self):
        """Rebuild the display image for the current zoom level and redraw overlays"""
        if self.base_image is None:
            return

        zoom_factor = self.zoom_levels[self.zoom_index]

        # Build scaled display image from base
        if zoom_factor == 1.0:
            self.display_image = self.base_image
        elif zoom_factor > 1.0:
            factor = int(round(zoom_factor))
            self.display_image = self.base_image.zoom(factor, factor)
        else:
            factor = int(round(1.0 / zoom_factor))
            self.display_image = self.base_image.subsample(factor, factor)

        # Attach to canvas image item
        self.image = self.display_image  # keep reference
        if self.image_id is None:
            self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)
        else:
            self.canvas.itemconfig(self.image_id, image=self.display_image)

        # Compute actual scale from pixels
        self.scale = self.display_image.width() / self.map_width if self.map_width else 1.0

        display_w = self.display_image.width()
        display_h = self.display_image.height()

        # Update viewport + scrollregion
        self.viewport_width = min(display_w, self.max_viewport_width)
        self.viewport_height = min(display_h, self.max_viewport_height)
        self.canvas.config(width=self.viewport_width, height=self.viewport_height)
        self.canvas.config(scrollregion=(0, 0, display_w, display_h))

        # Redraw grid & markers for new scale
        self.draw_grid()
        self.redraw_markers()
        # Redraw map boundaries at new scale
        self.redraw_boundaries()

        self.update_zoom_label()

    def zoom_in(self):
        if self.base_image is None:
            return
        if self.zoom_index < len(self.zoom_levels) - 1:
            center = self.get_view_center_in_map_coords()
            self.zoom_index += 1
            self.apply_zoom()
            self.center_on_map_coord(*center)

    def zoom_out(self):
        if self.base_image is None:
            return
        if self.zoom_index > 0:
            center = self.get_view_center_in_map_coords()
            self.zoom_index -= 1
            self.apply_zoom()
            self.center_on_map_coord(*center)

    def update_image(self, event=None):
        selected_image = self.image_selector.get()
        self.load_image(selected_image)

    # Grid Logic

    def clear_grid(self):
        self.canvas.delete("grid")
        self.grid_lines = []

    def draw_grid(self):
        self.clear_grid()
        if not self.show_grid_var.get() or self.base_image is None:
            return

        fine_color = "#303030"
        coarse_color = "#707070"
        cross_color = "#d0d0d0"

        try:
            fine_step_map = int(self.grid_step_entry.get())
            if fine_step_map <= 0:
                raise ValueError
        except ValueError:
            fine_step_map = 32
            self.grid_step_entry.delete(0, tk.END)
            self.grid_step_entry.insert(0, str(fine_step_map))

        coarse_factor = 4
        coarse_step_map = fine_step_map * coarse_factor

        scale = self.scale or 1.0
        w_disp = self.map_width * scale
        h_disp = self.map_height * scale

        # vertical lines (iterate in map units, draw in display units)
        x_map = 0
        while x_map <= self.map_width:
            x_disp = x_map * scale
            is_coarse = (x_map % coarse_step_map == 0)
            color = coarse_color if is_coarse else fine_color
            dash = () if is_coarse else (2, 4)
            lid = self.canvas.create_line(
                x_disp, 0, x_disp, h_disp,
                fill=color,
                dash=dash,
                tags=("grid",)
            )
            self.grid_lines.append(lid)
            x_map += fine_step_map

        # horizontal lines
        y_map = 0
        while y_map <= self.map_height:
            y_disp = y_map * scale
            is_coarse = (y_map % coarse_step_map == 0)
            color = coarse_color if is_coarse else fine_color
            dash = () if is_coarse else (2, 4)
            lid = self.canvas.create_line(
                0, y_disp, w_disp, y_disp,
                fill=color,
                dash=dash,
                tags=("grid",)
            )
            self.grid_lines.append(lid)
            y_map += fine_step_map

        # plus shaped crosses at coarse intersections
        size = 4
        x_map = coarse_step_map
        while x_map < self.map_width:
            y_map = coarse_step_map
            x_disp = x_map * scale
            while y_map < self.map_height:
                y_disp = y_map * scale
                h1 = self.canvas.create_line(
                    x_disp - size, y_disp, x_disp + size, y_disp,
                    fill=cross_color,
                    tags=("grid",)
                )
                h2 = self.canvas.create_line(
                    x_disp, y_disp - size, x_disp, y_disp + size,
                    fill=cross_color,
                    tags=("grid",)
                )
                self.grid_lines.extend([h1, h2])
                y_map += coarse_step_map
            x_map += coarse_step_map

    def toggle_grid(self):
        if self.show_grid_var.get():
            self.draw_grid()
        else:
            self.clear_grid()

    # Marker Logic

    def get_marker_type_id(self):
        label = self.marker_type_var.get()
        if "UNSC" in label:
            return "unsc"
        if "Covenant" in label:
            return "cov"
        if "Reactor" in label:
            return "reactor"
        if "Player 1" in label:
            return "PL1"
        if "Player 2" in label:
            return "PL2"
        if "Player 3" in label:
            return "PL3"
        if "Player 4" in label:
            return "PL4"
        if "Player 5" in label:
            return "PL5"
        if "Player 6" in label:
            return "PL6"
        if "Creeps" in label:
            return "N1"
        return "default"

    def infer_marker_type_from_name(self, name: str) -> str:
        """
        Heuristic: guess marker type from EditorName/Name string
        If nothing matches, return default
        """
        n = name.lower()

        # Reactors
        if "reactor" in n or ("hook" in n and "bonus" in n):
            return "reactor"

        # Creeps/rebels/neutral enemies
        if any(k in n for k in ["creep", "rebel", "rebels", "neutral"]):
            return "N1"

        # Player markers: try PL1–PL6 based on common patterns
        player_patterns = {
            "PL1": ["pl1", "player1", "player_1", "player 1", "p1_", "p1 "],
            "PL2": ["pl2", "player2", "player_2", "player 2", "p2_", "p2 "],
            "PL3": ["pl3", "player3", "player_3", "player 3", "p3_", "p3 "],
            "PL4": ["pl4", "player4", "player_4", "player 4", "p4_", "p4 "],
            "PL5": ["pl5", "player5", "player_5", "player 5", "p5_", "p5 "],
            "PL6": ["pl6", "player6", "player_6", "player 6", "p6_", "p6 "],
        }
        for mtype, patterns in player_patterns.items():
            if any(p in n for p in patterns):
                return mtype

        # Bases/sockets/starts UNSC vs Covenant
        if any(k in n for k in ["base", "socket", "start"]):
            if any(k in n for k in ["cov", "covenant", "banished", "banish"]):
                return "cov"
            return "unsc"

        return "default"

    def create_marker_shape(self, marker_type, canvas_x, canvas_y):
        """
        Draw iconified vector markers: combination of shapes instead of plain letters
        Returns a list of canvas item IDs or a single ID
        """
        ids = []

        # UNSC base: square body + roof triangle
        if marker_type == "unsc":
            size = 8
            body_id = self.canvas.create_rectangle(
                canvas_x - size, canvas_y - size / 2,
                canvas_x + size, canvas_y + size / 2,
                outline="white",
                width=2
            )
            roof_id = self.canvas.create_polygon(
                canvas_x - size, canvas_y - size / 2,
                canvas_x + size, canvas_y - size / 2,
                canvas_x,       canvas_y - size,
                outline="white",
                fill="",
                width=2
            )
            ids.extend([body_id, roof_id])

        # Covenant base: diamond + inner circle
        elif marker_type == "cov":
            size = 9
            diamond_id = self.canvas.create_polygon(
                canvas_x,         canvas_y - size,
                canvas_x + size,  canvas_y,
                canvas_x,         canvas_y + size,
                canvas_x - size,  canvas_y,
                outline="#c030ff",
                fill="",
                width=2
            )
            inner_id = self.canvas.create_oval(
                canvas_x - 3, canvas_y - 3,
                canvas_x + 3, canvas_y + 3,
                outline="#c030ff",
                width=1
            )
            ids.extend([diamond_id, inner_id])

        # Reactor: yellow star
        elif marker_type == "reactor":
            outer_r = 9
            inner_r = 4
            points = []
            for i in range(10):
                angle_deg = i * 36 - 90
                angle_rad = math.radians(angle_deg)
                r = outer_r if i % 2 == 0 else inner_r
                px = canvas_x + r * math.cos(angle_rad)
                py = canvas_y + r * math.sin(angle_rad)
                points.extend([px, py])
            star_id = self.canvas.create_polygon(
                points,
                outline="yellow",
                fill=""
            )
            ids.append(star_id)

        # Player markers: colored ring + number
        elif marker_type in {"PL1", "PL2", "PL3", "PL4", "PL5", "PL6"}:
            player_colors = {
                "PL1": "lime",
                "PL2": "cyan",
                "PL3": "yellow",
                "PL4": "orange",
                "PL5": "magenta",
                "PL6": "red",
            }
            outline = player_colors.get(marker_type, "white")
            number = marker_type[-1]  # PL1 -> 1

            radius = 9
            ring_id = self.canvas.create_oval(
                canvas_x - radius, canvas_y - radius,
                canvas_x + radius, canvas_y + radius,
                outline=outline,
                width=2
            )
            text_id = self.canvas.create_text(
                canvas_x, canvas_y,
                text=number,
                fill="white",
                font=("TkDefaultFont", 9, "bold")
            )
            ids.extend([ring_id, text_id])

        # Creeps/neutral camps: spiky sun
        elif marker_type == "N1":
            outer_r = 9
            inner_r = 4
            points = []
            spikes = 12
            for i in range(spikes * 2):
                angle_deg = i * (360 / (spikes * 2)) - 90
                angle_rad = math.radians(angle_deg)
                r = outer_r if i % 2 == 0 else inner_r
                px = canvas_x + r * math.cos(angle_rad)
                py = canvas_y + r * math.sin(angle_rad)
                points.extend([px, py])
            poly_id = self.canvas.create_polygon(
                points,
                outline="#aaaa00",
                fill=""
            )
            ids.append(poly_id)

        else:
            # Default: simple blue circle
            circle_id = self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5,
                canvas_x + 5, canvas_y + 5,
                outline="blue", width=3
            )
            ids.append(circle_id)

        return ids if len(ids) > 1 else (ids[0] if ids else None)

    def add_marker(self, map_x, map_y, canvas_x=None, canvas_y=None, name=None, marker_type=None, group=None, uid=None):
        if name is None:
            name = self.name_entry.get().strip()
            if not name:
                name = f"Marker {len(self.markers) + 1}"

        # Group/UID (for grouping, filtering, and drag-selection)
        if group is None:
            group = getattr(self, "group_var", tk.StringVar()).get()
        try:
            group = str(group).strip()
        except Exception:
            group = "Ungrouped"
        if not group:
            group = "Ungrouped"

        if uid is None:
            uid = uuid.uuid4().hex

        if marker_type is None:
            marker_type = self.get_marker_type_id()
        else:
            # sanity check on imported/heuristic type
            allowed_types = {
                "default", "unsc", "cov", "reactor",
                "PL1", "PL2", "PL3", "PL4", "PL5", "PL6",
                "N1",
            }
            if marker_type not in allowed_types:
                marker_type = "default"

        if canvas_x is None or canvas_y is None:
            canvas_x, canvas_y = self.map_to_canvas(map_x, map_y)

        marker_ids = self.create_marker_shape(marker_type, canvas_x, canvas_y)
        if isinstance(marker_ids, (list, tuple)):
            primary_id = marker_ids[0]
        else:
            primary_id = marker_ids
            marker_ids = [marker_ids]

        # Tag marker canvas items so we can hit-test for dragging
        for cid in marker_ids:
            if cid is None:
                continue
            try:
                existing = set(self.canvas.gettags(cid))
            except Exception:
                existing = set()
            existing.update({"marker", f"muid:{uid}"})
            try:
                self.canvas.itemconfigure(cid, tags=tuple(existing))
            except Exception:
                pass

        marker_info = {
            "id": primary_id,
            "ids": marker_ids,
            "uid": uid,
            "group": group,
            "name": name,
            "type": marker_type,
            "map_x": map_x,
            "map_y": map_y,
            "canvas_x": canvas_x,
            "canvas_y": canvas_y,
        }
        self.markers.append(marker_info)

        # Keep group registry up to date
        if not hasattr(self, "group_visibility"):
            self.group_visibility = {"Ungrouped": True}
        if group not in self.group_visibility:
            self.group_visibility[group] = True

        # Listbox population respects search filtering
        if hasattr(self, "marker_listbox"):
            q = (self.marker_search_var.get().strip().lower() if hasattr(self, "marker_search_var") else "")
            if (not q) or self._search_matches_marker(marker_info, q):
                self.marker_listbox.insert(tk.END, self.format_marker_list_entry(marker_info))
                if hasattr(self, "listbox_marker_uids"):
                    self.listbox_marker_uids.append(uid)
            else:
                # If search is active and this marker doesn't match, leave listbox alone
                pass

        # Refresh groups UI (avoid doing this per-marker during batch imports)
        if getattr(self, "batch_after_id", None) is None:
            self.refresh_group_listbox()

        # Apply current filters to just this new marker (important for batch imports)
        if not self.is_marker_type_visible(marker_type):
            for cid in marker_ids:
                if cid is not None:
                    self.canvas.itemconfigure(cid, state="hidden")

    def redraw_markers(self):
        """Recreate marker shapes at the current zoom level"""
        # delete old shapes
        for m in self.markers:
            ids = m.get("ids") or [m.get("id")]
            for cid in ids:
                if cid is not None:
                    self.canvas.delete(cid)
            m["ids"] = []
            m["id"] = None

        # redraw
        for m in self.markers:
            canvas_x, canvas_y = self.map_to_canvas(m["map_x"], m["map_y"])
            marker_ids = self.create_marker_shape(m["type"], canvas_x, canvas_y)
            if isinstance(marker_ids, (list, tuple)):
                primary_id = marker_ids[0]
            else:
                primary_id = marker_ids
                marker_ids = [marker_ids]

            # Re-tag items for hit-testing (dragging)
            uid = m.get("uid") or uuid.uuid4().hex
            m["uid"] = uid
            for cid in marker_ids:
                if cid is None:
                    continue
                try:
                    existing = set(self.canvas.gettags(cid))
                except Exception:
                    existing = set()
                existing.update({"marker", f"muid:{uid}"})
                try:
                    self.canvas.itemconfigure(cid, tags=tuple(existing))
                except Exception:
                    pass

            m["canvas_x"] = canvas_x
            m["canvas_y"] = canvas_y
            m["id"] = primary_id
            m["ids"] = marker_ids

        # Re-apply marker visibility after recreating shapes
        self.apply_marker_filters()

    def mark_image(self):
        try:
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())
            if 0 <= x <= self.map_width and 0 <= y <= self.map_height:
                self.add_marker(map_x=x, map_y=y)
            else:
                messagebox.showerror(
                    "Error",
                    f"Coordinates must be within the range 0 to {self.map_width} (x) "
                    f"and 0 to {self.map_height} (y)."
                )
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid integer coordinates.")

    def mark_image_with_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        map_x, map_y = self.canvas_to_map(canvas_x, canvas_y)
        if not (0 <= map_x <= self.map_width and 0 <= map_y <= self.map_height):
            return

        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(map_x))
        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(map_y))

        self.add_marker(map_x=map_x, map_y=map_y, canvas_x=canvas_x, canvas_y=canvas_y)


    def delete_selected_markers(self):
        """
        Delete the currently selected marker(s) from the list and canvas
        Works with search-filtered lists by deleting via marker UID
        """
        selection = list(self.marker_listbox.curselection())
        if not selection:
            messagebox.showinfo("Delete Markers", "Select one or more markers to delete.")
            return

        # Translate listbox indices -> marker UIDs
        uids_to_delete = set()
        for idx in selection:
            if 0 <= idx < len(getattr(self, "listbox_marker_uids", [])):
                uids_to_delete.add(self.listbox_marker_uids[idx])

        if not uids_to_delete:
            return

        kept = []
        for m in self.markers:
            if (m.get("uid") or "") in uids_to_delete:
                ids = m.get("ids") or [m.get("id")]
                for cid in ids:
                    if cid is not None:
                        try:
                            self.canvas.delete(cid)
                        except Exception:
                            pass
            else:
                kept.append(m)

        self.markers = kept

        # Remove any existing measurement line (it may reference deleted markers)
        self.canvas.delete("measure")

        self.refresh_marker_listbox()
        self.refresh_group_listbox()
        self.apply_marker_filters()
    def _marker_type_symbol(self, marker_type: str) -> str:
        return {
            "default": "●",
            "unsc": "U",
            "cov": "C",
            "reactor": "★",
            "PL1": "P1",
            "PL2": "P2",
            "PL3": "P3",
            "PL4": "P4",
            "PL5": "P5",
            "PL6": "P6",
            "N1": "N"
        }.get(marker_type, "?")

    def is_marker_type_visible(self, marker_type: str) -> bool:
        # If override is on, ignore all filters and show everything
        if hasattr(self, "ignore_marker_filters_var") and self.ignore_marker_filters_var.get():
            return True
        return marker_type in getattr(self, "visible_marker_types", set())


    def is_marker_canvas_visible(self, marker: dict) -> bool:
        """
        True if the marker should be visible on the canvas under current type filters + group visibility
        
        the All markers override only affects type filters, not group visibility
        """
        marker_type = marker.get("type", "default")
        group = (marker.get("group") or "Ungrouped")
        gv = getattr(self, "group_visibility", {"Ungrouped": True})
        group_visible = gv.get(group, True)
        type_visible = self.is_marker_type_visible(marker_type)
        return bool(type_visible and group_visible)

    def _search_matches_marker(self, marker: dict, q: str) -> bool:
        """Case-insensitive substring match against name, group, or type"""
        if not q:
            return True
        try:
            q = str(q).strip().lower()
        except Exception:
            return True
        if not q:
            return True

        name = str(marker.get("name", "")).lower()
        group = str(marker.get("group", "")).lower()
        mtype = str(marker.get("type", "")).lower()
        return (q in name) or (q in group) or (q in mtype)

    def get_marker_by_uid(self, uid: str):
        if not uid:
            return None
        for m in self.markers:
            if m.get("uid") == uid:
                return m
        return None

    def clear_search(self):
        if hasattr(self, "marker_search_var"):
            self.marker_search_var.set("")
        self.refresh_marker_listbox()

    def clear_scn_search(self):
        if hasattr(self, "scn_search_var"):
            self.scn_search_var.set("")
        self.refresh_scn_object_listbox()

    # Grouping UI

    def refresh_group_listbox(self):
        """Rebuild the Groups listbox from current markers and update group dropdown values"""
        if not hasattr(self, "group_visibility"):
            self.group_visibility = {"Ungrouped": True}

        # Compute counts
        counts = {}
        for m in self.markers:
            g = (m.get("group") or "Ungrouped")
            counts[g] = counts.get(g, 0) + 1
            if g not in self.group_visibility:
                self.group_visibility[g] = True

        # Always show Ungrouped, even if empty
        if "Ungrouped" not in counts:
            counts["Ungrouped"] = 0
            if "Ungrouped" not in self.group_visibility:
                self.group_visibility["Ungrouped"] = True

        groups = sorted(counts.keys(), key=lambda x: (x != "Ungrouped", str(x).lower()))

        # Update the add-marker combobox values
        if hasattr(self, "group_combo"):
            try:
                self.group_combo["values"] = groups
            except Exception:
                pass

        if not hasattr(self, "group_listbox"):
            return

        # Preserve selection
        prev_sel = self.group_listbox.curselection()
        prev_group = None
        if prev_sel and hasattr(self, "_group_listbox_names") and prev_sel[0] < len(self._group_listbox_names):
            prev_group = self._group_listbox_names[prev_sel[0]]

        self.group_listbox.delete(0, tk.END)
        self._group_listbox_names = []

        for g in groups:
            vis = self.group_visibility.get(g, True)
            prefix = "[x]" if vis else "[ ]"
            self.group_listbox.insert(tk.END, f"{prefix} {g} ({counts.get(g, 0)})")
            self._group_listbox_names.append(g)

        # Restore selection
        if prev_group in self._group_listbox_names:
            i = self._group_listbox_names.index(prev_group)
            self.group_listbox.selection_set(i)

    def on_group_select(self, event=None):
        if not hasattr(self, "group_listbox") or not hasattr(self, "_group_listbox_names"):
            return
        sel = self.group_listbox.curselection()
        if len(sel) != 1:
            return
        g = self._group_listbox_names[sel[0]]
        if hasattr(self, "group_assign_var"):
            self.group_assign_var.set(g)
        # Convenience: also set the add-marker group dropdown
        if hasattr(self, "group_var"):
            self.group_var.set(g)

    def toggle_selected_group_visibility(self, event=None):
        if not hasattr(self, "group_listbox") or not hasattr(self, "_group_listbox_names"):
            return
        sel = self.group_listbox.curselection()
        if len(sel) != 1:
            return
        g = self._group_listbox_names[sel[0]]
        self.group_visibility[g] = not self.group_visibility.get(g, True)
        self.apply_marker_filters()
        self.refresh_marker_listbox()
        self.refresh_group_listbox()

    def assign_selected_to_group(self, group_name: str = None):
        """Assign currently selected markers in marker list to a group"""
        if group_name is None:
            group_name = (self.group_assign_var.get() if hasattr(self, "group_assign_var") else "").strip()
        try:
            group_name = str(group_name).strip()
        except Exception:
            group_name = "Ungrouped"
        if not group_name:
            group_name = "Ungrouped"

        sel = list(self.marker_listbox.curselection())
        if not sel:
            messagebox.showinfo("Grouping", "Select one or more markers to assign to a group.")
            return

        uids = []
        for idx in sel:
            if 0 <= idx < len(getattr(self, "listbox_marker_uids", [])):
                uids.append(self.listbox_marker_uids[idx])

        if not uids:
            return

        if group_name not in self.group_visibility:
            self.group_visibility[group_name] = True

        for uid in uids:
            m = self.get_marker_by_uid(uid)
            if m:
                m["group"] = group_name

        self.apply_marker_filters()
        self.refresh_group_listbox()
        self.refresh_marker_listbox()

    def ungroup_selected_markers(self):
        """
        If a group is selected in the Groups listbox, ungroup all markers in that group
        
        Otherwise, ungroup the currently selected markers in the marker listbox
        """
        # Prefer group selection (Groups box)
        selected_group = None
        if hasattr(self, "group_listbox") and hasattr(self, "_group_listbox_names"):
            sel = self.group_listbox.curselection()
            if len(sel) == 1 and sel[0] < len(self._group_listbox_names):
                selected_group = self._group_listbox_names[sel[0]]

        if selected_group and selected_group != "Ungrouped":
            changed = False
            for m in getattr(self, "markers", []):
                g = (m.get("group") or "Ungrouped")
                if g == selected_group:
                    m["group"] = "Ungrouped"
                    changed = True

            if changed:
                # Optional cleanup: if the group is now empty, drop its visibility entry
                still_exists = any((mm.get("group") or "Ungrouped") == selected_group for mm in self.markers)
                if not still_exists and hasattr(self, "group_visibility"):
                    self.group_visibility.pop(selected_group, None)

                self.apply_marker_filters()
                self.refresh_group_listbox()
                self.refresh_marker_listbox()
            return

        # Fallback: ungroup selected markers (Marker list)
        if hasattr(self, "marker_listbox") and self.marker_listbox.curselection():
            self.assign_selected_to_group("Ungrouped")
            return

        messagebox.showinfo("Grouping", "Select a group (in Groups) or one or more markers (in the marker list) to ungroup.")

    def select_marker_in_listbox(self, uid: str):
        """Select a marker in the listbox if it's currently shown (respects search filter)."""
        if not uid or not hasattr(self, "marker_listbox"):
            return
        try:
            i = self.listbox_marker_uids.index(uid)
        except Exception:
            return
        self.marker_listbox.selection_clear(0, tk.END)
        self.marker_listbox.selection_set(i)
        self.marker_listbox.see(i)

    # Dragging markers
    
    def _find_marker_uid_near(self, canvas_x: float, canvas_y: float, tol: int = 10):
        try:
            items = self.canvas.find_overlapping(canvas_x - tol, canvas_y - tol, canvas_x + tol, canvas_y + tol)
        except Exception:
            return None

        # Iterate top-to-bottom
        for item in reversed(items):
            try:
                tags = self.canvas.gettags(item)
            except Exception:
                continue
            if "marker" not in tags:
                continue
            for t in tags:
                if isinstance(t, str) and t.startswith("muid:"):
                    return t.split("muid:", 1)[1]
        return None

    def on_left_press(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        uid = self._find_marker_uid_near(canvas_x, canvas_y)
        if uid:
            self._drag_uid = uid
            self._drag_last_canvas = (canvas_x, canvas_y)

            m = self.get_marker_by_uid(uid)
            if m:
                # Update entries
                self.x_entry.delete(0, tk.END)
                self.x_entry.insert(0, str(m.get("map_x", 0)))
                self.y_entry.delete(0, tk.END)
                self.y_entry.insert(0, str(m.get("map_y", 0)))
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, m.get("name", ""))

                # Select it in the list if currently visible under search
                self.select_marker_in_listbox(uid)
            return

        # Clicked empty space -> keep original behavior (add marker)
        self._drag_uid = None
        self.mark_image_with_click(event)

    def on_left_drag(self, event):
        if not self._drag_uid:
            return

        m = self.get_marker_by_uid(self._drag_uid)
        if not m:
            self._drag_uid = None
            return

        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Convert cursor to map coords and clamp
        map_x, map_y = self.canvas_to_map(canvas_x, canvas_y)
        try:
            map_x = int(round(map_x))
            map_y = int(round(map_y))
        except Exception:
            return

        map_x = max(0, min(self.map_width, map_x))
        map_y = max(0, min(self.map_height, map_y))

        new_cx, new_cy = self.map_to_canvas(map_x, map_y)

        old_cx = m.get("canvas_x", new_cx)
        old_cy = m.get("canvas_y", new_cy)

        dx = new_cx - old_cx
        dy = new_cy - old_cy

        ids = m.get("ids") or [m.get("id")]
        for cid in ids:
            if cid is not None:
                try:
                    self.canvas.move(cid, dx, dy)
                except Exception:
                    pass

        m["map_x"] = map_x
        m["map_y"] = map_y
        m["canvas_x"] = new_cx
        m["canvas_y"] = new_cy

        # Live update coordinate entries while dragging
        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(map_x))
        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(map_y))

    def on_left_release(self, event):
        if not self._drag_uid:
            return
        uid = self._drag_uid
        self._drag_uid = None

        # Update list display (coords changed)
        self.refresh_marker_listbox()
        self.select_marker_in_listbox(uid)
    def format_marker_list_entry(self, marker: dict) -> str:
        marker_type = marker.get("type", "default")
        name = marker.get("name", "Unnamed")
        group = (marker.get("group") or "Ungrouped")
        map_x = marker.get("map_x", 0)
        map_y = marker.get("map_y", 0)

        hidden_prefix = ""
        if not self.is_marker_canvas_visible(marker):
            hidden_prefix = "[HIDDEN] "

        return f'{hidden_prefix}[{self._marker_type_symbol(marker_type)}] {name}  ({map_x}, {map_y})  <{group}>'

    def sync_visible_types_from_vars(self):
        if not hasattr(self, "marker_filter_vars"):
            return
        self.visible_marker_types = {t for t, v in self.marker_filter_vars.items() if v.get()}

    def refresh_marker_listbox(self):
        if not hasattr(self, "marker_listbox"):
            return

        # Preserve current selection by UID (because list order can change under search)
        selected_uids = set()
        try:
            selection = list(self.marker_listbox.curselection())
            for idx in selection:
                if 0 <= idx < len(getattr(self, "listbox_marker_uids", [])):
                    selected_uids.add(self.listbox_marker_uids[idx])
        except Exception:
            pass

        q = (self.marker_search_var.get().strip().lower() if hasattr(self, "marker_search_var") else "")

        self.marker_listbox.delete(0, tk.END)
        self.listbox_marker_uids = []

        for m in self.markers:
            uid = m.get("uid") or uuid.uuid4().hex
            m["uid"] = uid

            # Search filter (matches name/group/type)
            if q and (not self._search_matches_marker(m, q)):
                continue

            self.marker_listbox.insert(tk.END, self.format_marker_list_entry(m))
            self.listbox_marker_uids.append(uid)

        # Restore selection
        for i, uid in enumerate(self.listbox_marker_uids):
            if uid in selected_uids:
                self.marker_listbox.selection_set(i)

    def apply_marker_filters(self):
        """Hide/show marker canvas items based on the Filters tab + override toggle"""
        # Make sure visible set is current
        self.sync_visible_types_from_vars()

        for m in self.markers:
            marker_type = m.get("type", "default")
            visible = self.is_marker_canvas_visible(m)
            ids = m.get("ids") or [m.get("id")]
            for cid in ids:
                if cid is None:
                    continue
                try:
                    self.canvas.itemconfigure(cid, state=("normal" if visible else "hidden"))
                except tk.TclError:
                    # Canvas item may not exist if deleted elsewhere; ignore
                    pass

    def on_marker_filter_changed(self):
        self.sync_visible_types_from_vars()
        self.apply_marker_filters()
        self.refresh_marker_listbox()

    def toggle_marker_filter_override(self):
        # When toggling All markers, immediately re-apply filters and refresh the list display
        self.apply_marker_filters()
        self.refresh_marker_listbox()

    def filter_show_all(self):
        for v in self.marker_filter_vars.values():
            v.set(True)
        self.on_marker_filter_changed()

    def filter_hide_all(self):
        for v in self.marker_filter_vars.values():
            v.set(False)
        self.on_marker_filter_changed()

    def filter_invert(self):
        for v in self.marker_filter_vars.values():
            v.set(not v.get())
        self.on_marker_filter_changed()

    # Legend UI

    def build_legend_panel(self, parent):
        """
        Build a simple legend panel using pure Tkinter (no Pillow, I don't want to force users to download anything not needed)
        
        Icons are drawn as vector shapes on small canvases
        """
        # (label, marker_type)
        entries = [
            ("Default", "default"),
            ("UNSC Base", "unsc"),
            ("Covenant Base", "cov"),
            ("Reactor", "reactor"),
            ("Player 1", "PL1"),
            ("Player 2", "PL2"),
            ("Player 3", "PL3"),
            ("Player 4", "PL4"),
            ("Player 5", "PL5"),
            ("Player 6", "PL6"),
            ("Creeps", "N1"),
        ]

        for label, mtype in entries:
            row = tk.Frame(parent)
            row.pack(fill=tk.X, padx=6, pady=2)

            icon = tk.Canvas(row, width=26, height=26, highlightthickness=0, bg="black")
            icon.pack(side=tk.LEFT)

            self.draw_legend_icon(icon, mtype)

            tk.Label(row, text=label).pack(side=tk.LEFT, padx=(6, 0))

    def draw_legend_icon(self, canvas, marker_type):
        """Draw a small icon centered in a 26x26 canvas"""
        cx, cy = 13, 13

        if marker_type == "unsc":
            size = 8
            canvas.create_rectangle(cx - size, cy - size / 2, cx + size, cy + size / 2,
                                    outline="white", width=2)
            canvas.create_polygon(cx - size, cy - size / 2,
                                  cx + size, cy - size / 2,
                                  cx, cy - size,
                                  outline="white", fill="", width=2)

        elif marker_type == "cov":
            size = 9
            canvas.create_polygon(cx, cy - size, cx + size, cy, cx, cy + size, cx - size, cy,
                                  outline="#c030ff", fill="", width=2)
            canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, outline="#c030ff", width=1)

        elif marker_type == "reactor":
            outer_r, inner_r = 9, 4
            pts = []
            for i in range(10):
                ang = math.radians(i * 36 - 90)
                r = outer_r if i % 2 == 0 else inner_r
                pts.extend([cx + r * math.cos(ang), cy + r * math.sin(ang)])
            canvas.create_polygon(pts, outline="yellow", fill="")

        elif marker_type in {"PL1", "PL2", "PL3", "PL4", "PL5", "PL6"}:
            player_colors = {
                "PL1": "lime",
                "PL2": "cyan",
                "PL3": "yellow",
                "PL4": "orange",
                "PL5": "magenta",
                "PL6": "red",
            }
            outline = player_colors.get(marker_type, "white")
            number = marker_type[-1]
            r = 9
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=outline, width=2)
            canvas.create_text(cx, cy, text=number, fill="white", font=("TkDefaultFont", 9, "bold"))

        elif marker_type == "N1":
            outer_r, inner_r = 9, 4
            spikes = 12
            pts = []
            for i in range(spikes * 2):
                ang = math.radians(i * (360 / (spikes * 2)) - 90)
                r = outer_r if i % 2 == 0 else inner_r
                pts.extend([cx + r * math.cos(ang), cy + r * math.sin(ang)])
            canvas.create_polygon(pts, outline="#aaaa00", fill="")

        else:
            canvas.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="blue", width=3)

    # Boundary list and per-boundary colors

    def boundary_display_text(self, b):
        btype = (b.get("type") or "generic")
        name = (b.get("name") or "Boundary")
        override = (b.get("color_override") or "")
        if override:
            return f"[{btype}] {name}  *{override}"
        return f"[{btype}] {name}"

    def refresh_boundary_listbox(self):
        if not hasattr(self, "boundary_listbox") or self.boundary_listbox is None:
            return
        prev_sel = list(getattr(self, 'boundary_selected_indices', []) or [])
        self.boundary_listbox.delete(0, tk.END)
        for b in self.boundaries:
            self.boundary_listbox.insert(tk.END, self.boundary_display_text(b))

        # Restore previous selection (if any)
        for i in prev_sel:
            if 0 <= i < self.boundary_listbox.size():
                self.boundary_listbox.selection_set(i)
        self.boundary_selected_indices = [i for i in prev_sel if 0 <= i < self.boundary_listbox.size()]

        # Disable edit combo until something is selected
        if hasattr(self, "boundary_color_edit_combo"):
            self.boundary_color_edit_combo.config(state="disabled")
            self.boundary_color_edit_var.set("Default")

    def on_boundary_select(self, event=None):
        if not hasattr(self, "boundary_listbox") or self.boundary_listbox is None:
            return
        sel = list(self.boundary_listbox.curselection())
        self.boundary_selected_indices = sel[:]  # cache
        if not sel:
            self.boundary_color_edit_combo.config(state="disabled")
            self.boundary_color_edit_var.set("Default")
            return

        # Enable edit combo once anything is selected
        self.boundary_color_edit_combo.config(state="readonly")

        # If exactly one is selected, sync the combobox to that boundary's override
        if len(sel) == 1 and 0 <= sel[0] < len(self.boundaries):
            b = self.boundaries[sel[0]]
            override = (b.get("color_override") or "").strip().lower()
            if override in {"red", "green", "blue"}:
                self.boundary_color_edit_var.set(override.capitalize())
            else:
                self.boundary_color_edit_var.set("Default")

            # Optional: center view on the first point of the boundary
            pts = b.get("points") or []
            if pts:
                self.center_on_map_coord(pts[0][0], pts[0][1])

        else:
            # Multi-select: show Default (neutral) but still allow applying a color
            self.boundary_color_edit_var.set("Default")

    def on_boundary_edit_color_changed(self, event=None):
        """Apply the chosen color override to the selected boundary(ies)"""
        if not hasattr(self, "boundary_listbox") or self.boundary_listbox is None:
            return
        sel = list(self.boundary_listbox.curselection())
        if not sel:
            # Some Tk builds clear listbox selection when focus moves to the combobox
            sel = list(getattr(self, 'boundary_selected_indices', []) or [])
        if not sel:
            messagebox.showinfo('Boundary Color', 'Select one or more boundaries in the Boundaries list first.')
            return

        choice = (self.boundary_color_edit_var.get() or "Default").strip().lower()
        override = None
        if choice in {"red", "green", "blue"}:
            override = choice

        for idx in sel:
            if 0 <= idx < len(self.boundaries):
                self.boundaries[idx]["color_override"] = override

        # Redraw boundaries and refresh list text (to show *override)
        self.redraw_boundaries()
        prev_sel = sorted(set(sel))
        self.refresh_boundary_listbox()
        # Restore selection after list rebuild
        for i in prev_sel:
            if 0 <= i < self.boundary_listbox.size():
                self.boundary_listbox.selection_set(i)
        self.boundary_selected_indices = prev_sel

    # Boundary Logic

    def get_boundary_draw_color(self, boundary):
        """
        Per-boundary color policy:

        If boundary (color_override) is set (red/green/blue), use it
        
        Otherwise fall back to type-based colors (camera/playable/default)
        """
        override = (boundary.get("color_override") or "").strip().lower()
        if override == "red":
            return "red"
        if override == "green":
            return "#00ff00"
        if override == "blue":
            return "blue"

        btype = boundary.get("type")
        if btype == "camera":
            return "#ff8800"  # orange
        if btype == "playable":
            return "#00ff00"  # green
        return "red"

    def toggle_boundaries(self):
        """Show/hide all boundary polylines (keeps boundary data)"""
        if self.show_boundaries_var.get():
            self.redraw_boundaries()
        else:
            self.canvas.delete("boundary")

    def clear_boundaries(self):
        """Remove all boundary polylines from the canvas and reset list"""
        self.canvas.delete("boundary")
        self.boundaries = []
        # Keep the UI list in sync
        self.refresh_boundary_listbox()

    def add_boundary(self, points, name=None, boundary_type=None, color_override=None):
        """
        Add a boundary polyline

        points: list of (map_x, map_y) in map coordinates (map_width/map_height)
        
        boundary_type: camera, playable, or None (for generic)
        """
        if not points:
            return

        # Ensure closed polygon: last point equals first
        if len(points) > 1 and points[0] != points[-1]:
            points = points + [points[0]]

        boundary = {
            "name": name or "Boundary",
            "type": boundary_type,
            "points": points,              # map coords
            "canvas_ids": [],
            "color_override": (color_override or None), # red/green/blue or None
        }

        # Draw now if visible
        if getattr(self, "show_boundaries_var", None) is None or self.show_boundaries_var.get():
            coords = []
            for (mx, my) in points:
                cx, cy = self.map_to_canvas(mx, my)
                coords.extend([cx, cy])

            color = self.get_boundary_draw_color(boundary)
            line_id = self.canvas.create_line(
                *coords,
                fill=color,
                width=2,
                tags=("boundary",)
            )
            boundary["canvas_ids"] = [line_id]

        self.boundaries.append(boundary)
        # Update the UI list
        if hasattr(self, "boundary_listbox"):
            self.boundary_listbox.insert(tk.END, self.boundary_display_text(boundary))

    def redraw_boundaries(self):
        """Recreate all boundary polylines at the current zoom level"""
        self.canvas.delete("boundary")

        # Respect show/hide toggle
        if getattr(self, "show_boundaries_var", None) is not None and not self.show_boundaries_var.get():
            return

        for b in self.boundaries:
            coords = []
            for (mx, my) in b["points"]:
                cx, cy = self.map_to_canvas(mx, my)
                coords.extend([cx, cy])

            color = self.get_boundary_draw_color(b)
            line_id = self.canvas.create_line(
                *coords,
                fill=color,
                width=2,
                tags=("boundary",)
            )
            b["canvas_ids"] = [line_id]


    def clear_markers(self):
        self.cancel_batch()
        for m in self.markers:
            ids = m.get("ids") or [m.get("id")]
            for cid in ids:
                if cid is not None:
                    self.canvas.delete(cid)
        self.markers = []
        self.marker_listbox.delete(0, tk.END)
        self.listbox_marker_uids = []
        self.group_visibility = {"Ungrouped": True}
        self.refresh_group_listbox()
        self.canvas.delete("measure")

        # Also clear any boundary polylines
        self.clear_boundaries()

    # SCN Auto Populate
    def auto_populate_from_scn(self):
        """
        Auto-populate markers and map boundaries by reading a paired .scn file
        whose name matches the current map image (PNG) but with .scn extension,
        located in folder2

        Lines containing Position="x,z,y" are parsed, using x (0) and y (2)
          (skipping the middle z) as map coordinates.

        Marker names are taken from EditorName when available, else Name,
          else a generic AutoMarker index

        Marker type is inferred heuristically from that name

        <Points> blocks are parsed as boundary polylines, also using x,z,y

        triples with (x, y) from 1st and 3rd components
        """
        if not self.current_image_name:
            messagebox.showerror("SCN Auto Populate", "No map image is currently loaded.")
            return

        base_name, _ = os.path.splitext(self.current_image_name)
        scn_filename = base_name + ".scn"
        scn_path = os.path.join(folder2, scn_filename)

        if not os.path.isfile(scn_path):
            if base_name.startswith("minimap_"):
                messagebox.showwarning(
                    "SCN Auto Populate",
                    f"No SCN file found for Halo Wars 2 minimap '{base_name}'.\n"
                    f"Auto-populating is not yet supported for this map."
                )
            else:
                messagebox.showwarning(
                    "SCN Auto Populate",
                    f"No SCN file '{scn_filename}' found in '{folder2}'."
                )
            return

        try:
            with open(scn_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror(
                "SCN Auto Populate",
                f"Failed to read SCN file '{scn_path}':\n{e}"
            )
            return
        
        # Clear existing markers + boundaries before auto-populating
        self.clear_markers()  # this also calls clear_boundaries()

        marker_specs = []
        boundary_specs = []

        auto_index = 1


        player_auto_index = 1
        # Pass 1: Positions -> markers (collect first, then batch-add)
        in_positions = False
        player_slot_index = 1
        for line in lines:
            # Track when we're inside <Positions> ... </Positions>
            if "<Positions" in line:
                in_positions = True
                continue
            if "</Positions" in line:
                in_positions = False
                continue
            if "Position" not in line:
                continue

            pos_match = re.search(r'Position="([^"]+)"', line)
            if not pos_match:
                continue

            coords_str = pos_match.group(1)
            parts = coords_str.split(",")
            if len(parts) < 3:
                continue

            try:
                x_val = int(float(parts[0]))
                y_val = int(float(parts[2]))    # (x, z, y) -> use x & y
            except ValueError:
                continue
            # Name: prefer EditorName, then Name, but special-case PlayerPlacement (<Position>) lines
            forced_type = None
            stripped = line.lstrip()
            if in_positions and stripped.startswith("<Position"):
                # In <Positions>, Player="-1" are real start slots (sequential Player 1-N)
                # Player="7" (and other non -1 values) are still valid markers (often neutral/creeps),
                # but should not consume the Player 1-N counter
                pl_m = re.search(r'\bPlayer="(-?\d+)"', line)
                if not pl_m:
                    continue

                try:
                    pl_val = int(pl_m.group(1))
                except ValueError:
                    continue

                if pl_val == -1:
                    name = f"Player {player_slot_index}"
                    pn = player_slot_index
                    player_slot_index += 1
                    forced_type = f"PL{pn}" if 1 <= pn <= 6 else None
                else:
                    # Keep the literal player number (so it shows as Player 7/etc)
                    name = f"Player {pl_val}"
                    # Force creeps type for Player 7
                    forced_type = "N1" if pl_val == 7 else None
            else:
                name_match = re.search(r'EditorName="([^"]+)"', line)
                if not name_match:
                    name_match = re.search(r'EditorName=([^\s">]+)', line)
                if not name_match:
                    name_match = re.search(r'Name="([^"]+)"', line)
                if not name_match:
                    name_match = re.search(r'Name=([^\s">]+)', line)

                if name_match:
                    name = name_match.group(1)
                else:
                    name = f"AutoMarker {auto_index}"
                    auto_index += 1

            map_x = x_val
            map_y = y_val

            if not (0 <= map_x <= self.map_width and 0 <= map_y <= self.map_height):
                continue

            marker_type = forced_type or self.infer_marker_type_from_name(name)
            marker_specs.append({"map_x": map_x, "map_y": map_y, "name": name, "type": marker_type})

        # Pass 2: Points -> boundary polylines (collect)
        for idx, line in enumerate(lines):
            if "<Points>" not in line:
                continue

            pts_match = re.search(r'<Points>([^<]+)</Points>', line)
            if not pts_match:
                continue

            pts_str = pts_match.group(1).strip()
            triple_strs = pts_str.split("|")

            boundary_points = []
            for t in triple_strs:
                comps = t.split(",")
                if len(comps) < 3:
                    continue
                try:
                    x_val = int(float(comps[0]))
                    y_val = int(float(comps[2]))
                except ValueError:
                    continue

                if 0 <= x_val <= self.map_width and 0 <= y_val <= self.map_height:
                    boundary_points.append((x_val, y_val))

            if len(boundary_points) < 2:
                continue

            boundary_name = None
            boundary_type = None
            for back in range(idx - 1, -1, -1):
                parent_line = lines[back]
                if "<Lines" in parent_line:
                    name_match = re.search(r'Name="([^"]+)"', parent_line)
                    if name_match:
                        boundary_name = name_match.group(1)
                        lname = boundary_name.lower()
                        if "camerabound" in lname or "camerabounds" in lname or "cameraboundary" in lname:
                            boundary_type = "camera"
                        elif "playable" in lname:
                            boundary_type = "playable"
                    break

            boundary_specs.append({"points": boundary_points, "name": boundary_name, "type": boundary_type})

        # Batch add markers first, then boundaries
        def _add_marker_spec(spec):
            self.add_marker(
                map_x=spec["map_x"],
                map_y=spec["map_y"],
                name=spec.get("name"),
                marker_type=spec.get("type", "default"),
                group=spec.get("group", "Ungrouped"),
                uid=spec.get("uid"),
            )
    
        def _add_boundary_spec(spec):
            self.add_boundary(
                spec["points"],
                name=spec.get("name"),
                boundary_type=spec.get("type")
            )
    
        def _done_bounds():
            # Ensure UI list shows overrides (none for SCN by default)
            self.refresh_boundary_listbox()
            # Re-apply marker visibility + refresh group/list views
            self.apply_marker_filters()
            self.refresh_group_listbox()
            self.refresh_marker_listbox()
            if not marker_specs:
                messagebox.showinfo(
                    "SCN Auto Populate",
                    f"No valid Position entries were imported from '{scn_filename}'."
                )
            else:
                messagebox.showinfo(
                    "SCN Auto Populate",
                    f"Auto-populated {len(marker_specs)} markers from '{scn_filename}'."
                )
    
        def _done_markers():
            if boundary_specs:
                self.start_batch(boundary_specs, _add_boundary_spec, done_fn=_done_bounds, label="Adding boundaries")
            else:
                _done_bounds()
    
        # Kick off batch
        if marker_specs:
            self.start_batch(marker_specs, _add_marker_spec, done_fn=_done_markers, label="Adding markers")
        else:
            _done_markers()
    
    # Export/Import

    def export_markers(self):
        """Handles exporting of markers, some users may want to save their changes after all"""
        if not self.markers:
            messagebox.showinfo("Export Markers", "No markers to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Markers"
        )
        if not filename:
            return

        data = {
            "map_image": self.current_image_name,
            "markers": [
                {
                    "name": m["name"],
                    "type": m["type"],
                    "map_x": m["map_x"],
                    "map_y": m["map_y"],
                    "group": (m.get("group") or "Ungrouped"),
                    "uid": (m.get("uid") or ""),
                }
                for m in self.markers
            ],
            "boundaries": [
                {
                    "name": (b.get("name") or "Boundary"),
                    "type": (b.get("type") or None),
                    "color_override": (b.get("color_override") or None),
                    "points": [[int(p[0]), int(p[1])] for p in (b.get("points") or [])],
                }
                for b in self.boundaries
            ],
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export Markers", f"Exported {len(self.markers)} markers and {len(self.boundaries)} boundaries.")
        except Exception as e:
            messagebox.showerror("Export Markers", f"Failed to export markers:\n{e}")

    def import_markers(self):
        """Import markers and boundaries from a JSON file created by Export"""
        filename = filedialog.askopenfilename(
            title="Import Markers",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Markers", f"Failed to import markers:\n{e}")
            return
        
        # Map mismatch guard (refuse import if JSON belongs to a different map)
        saved_map = data.get("map_image")
        if saved_map and self.current_image_name:
            # Compare only filenames so JSON can be moved between folders
            if os.path.basename(saved_map).casefold() != os.path.basename(self.current_image_name).casefold():
                messagebox.showwarning(
                    "Map Mismatch",
                    f"This JSON was exported for:\n  {os.path.basename(saved_map)}\n\n"
                    f"But you currently have selected:\n  {os.path.basename(self.current_image_name)}\n\n"
                    "Import cancelled to prevent mismatching markers. Select the correct map image and try again."
                )
                return

        # Clear existing markers + boundaries
        self.clear_markers()  # this also calls clear_boundaries()

        markers_data = data.get("markers", [])
        boundaries_data = data.get("boundaries", [])

        marker_specs = []
        if isinstance(markers_data, list):
            for m in markers_data:
                try:
                    map_x = int(m.get("map_x"))
                    map_y = int(m.get("map_y"))
                except Exception:
                    continue

                # Basic sanity (don't hard-require in-bounds, but avoid absurd values)
                if not (-100000 <= map_x <= 100000 and -100000 <= map_y <= 100000):
                    continue

                marker_specs.append({
                    "map_x": map_x,
                    "map_y": map_y,
                    "name": (m.get("name") or "Marker"),
                    "type": (m.get("type") or "default"),
                    "group": (m.get("group") or "Ungrouped"),
                    "uid": (m.get("uid") or None),
                })

        boundary_specs = []
        if isinstance(boundaries_data, list):
            for b in boundaries_data:
                try:
                    pts = b.get("points", [])
                    if not isinstance(pts, list):
                        continue

                    boundary_points = []
                    for p in pts:
                        if isinstance(p, (list, tuple)) and len(p) >= 2:
                            boundary_points.append((int(p[0]), int(p[1])))

                    if len(boundary_points) < 2:
                        continue

                    bname = b.get("name") or "Boundary"
                    btype = b.get("type", None)

                    # Accept either key for compatibility
                    override = b.get("color_override", None)
                    if override is None:
                        override = b.get("override", None)
                    if isinstance(override, str):
                        override = override.strip().lower()
                        if override not in {"red", "green", "blue"}:
                            override = None
                    else:
                        override = None

                    # Avoid absurd points (keep tool responsive)
                    clipped = []
                    for (xv, yv) in boundary_points:
                        if -100000 <= xv <= 100000 and -100000 <= yv <= 100000:
                            clipped.append((xv, yv))
                    if len(clipped) < 2:
                        continue

                    boundary_specs.append({
                        "points": clipped,
                        "name": bname,
                        "type": btype,
                        "override": override,
                    })
                except Exception:
                    continue

        def _add_marker_spec(spec):
            self.add_marker(
                map_x=spec["map_x"],
                map_y=spec["map_y"],
                name=spec.get("name"),
                marker_type=spec.get("type", "default"),
                group=spec.get("group", "Ungrouped"),
                uid=spec.get("uid"),
            )

        def _add_boundary_spec(spec):
            self.add_boundary(
                spec["points"],
                name=spec.get("name"),
                boundary_type=spec.get("type"),
                color_override=spec.get("override"),
            )

        def _done_bounds():
            self.refresh_boundary_listbox()
            # Re-apply marker visibility to reflect current filter checkboxes
            self.apply_marker_filters()
            self.refresh_group_listbox()
            self.refresh_marker_listbox()
            messagebox.showinfo(
                "Import Markers",
                f"Imported {len(self.markers)} markers and {len(self.boundaries)} boundaries."
            )

        def _done_markers():
            if boundary_specs:
                self.start_batch(
                    boundary_specs,
                    _add_boundary_spec,
                    done_fn=_done_bounds,
                    label="Adding boundaries"
                )
            else:
                _done_bounds()

        # Kick off batch
        if marker_specs:
            self.start_batch(
                marker_specs,
                _add_marker_spec,
                done_fn=_done_markers,
                label="Adding markers"
            )
        else:
            _done_markers()
            
    # Distance measurement

    def measure_distance(self):
        """
        Measure distance between two markers selected in the list
        
        Use Ctrl+click to select exactly two entries, then press this button
        """
        selection = self.marker_listbox.curselection()
        if len(selection) != 2:
            messagebox.showinfo(
                "Measure Distance",
                "Select exactly two markers in the list (Ctrl+click) before measuring."
            )
            return

        idx1, idx2 = selection
        uid1 = self.listbox_marker_uids[idx1] if idx1 < len(self.listbox_marker_uids) else None
        uid2 = self.listbox_marker_uids[idx2] if idx2 < len(self.listbox_marker_uids) else None
        m1 = self.get_marker_by_uid(uid1)
        m2 = self.get_marker_by_uid(uid2)

        if not m1 or not m2:
            messagebox.showinfo("Measure Distance", "Could not resolve one or both selected markers.")
            return

        dx = m1["map_x"] - m2["map_x"]
        dy = m1["map_y"] - m2["map_y"]
        dist = math.sqrt(dx * dx + dy * dy)

        # remove previous measurement line
        self.canvas.delete("measure")
        x1, y1 = self.map_to_canvas(m1["map_x"], m1["map_y"])
        x2, y2 = self.map_to_canvas(m2["map_x"], m2["map_y"])
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill="white",
            dash=(4, 2),
            width=2,
            tags=("measure",)
        )

        messagebox.showinfo(
            "Measure Distance",
            f"{m1['name']} ↔ {m2['name']}\n"
            f"X = {dx}, Y = {dy}\n"
            f"Distance = {dist:.2f} units"
        )

    # Panning/Selection

    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_marker_select(self, event):
        selection = self.marker_listbox.curselection()
        if len(selection) != 1:
            # Only recenter on single-selection, multi-select is for measuring
            return
        idx = selection[0]
        uid = self.listbox_marker_uids[idx] if idx < len(self.listbox_marker_uids) else None
        marker = self.get_marker_by_uid(uid)
        if not marker:
            return

        # Center view on this marker at current zoom
        self.center_on_map_coord(marker["map_x"], marker["map_y"])

        # Update entries
        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(marker["map_x"]))
        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(marker["map_y"]))
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, marker["name"])

        type_to_label = {
            "default": "Default (circle)",
            "unsc": "UNSC Base (U)",
            "cov": "Covenant Base (C)",
            "reactor": "Reactor (star)",
            "PL1": "Player 1 (P1)",
            "PL2": "Player 2 (P2)",
            "PL3": "Player 3 (P3)",
            "PL4": "Player 4 (P4)",
            "PL5": "Player 5 (P5)",
            "PL6": "Player 6 (P6)",
            "N1":  "Creeps (N)",
        }
        label = type_to_label.get(marker["type"], "Default (circle)")
        self.marker_type_var.set(label)

    # SCN Editor (Objects and PlayerPlacement Positions)

    def _get_current_scn_path(self):
        if not getattr(self, "current_image_name", None):
            return None
        base_name, _ = os.path.splitext(self.current_image_name)
        scn_filename = base_name + ".scn"
        return os.path.join(folder2, scn_filename)

    def load_scn_objects_for_current_map(self):
        """Load the paired SCN for the currently selected map and parse <Objects> and <Positions>"""
        scn_path = self._get_current_scn_path()
        if not scn_path:
            messagebox.showerror("SCN Editor", "No map image is currently loaded.")
            return
        if not os.path.isfile(scn_path):
            messagebox.showwarning("SCN Editor", f"No SCN file found for this map:\n{os.path.basename(scn_path)}")
            self.scn_path = scn_path
            self.scn_lines = None
            self.scn_objects = []
            self.scn_positions = []
            self._scn_objects_bounds = None
            self._scn_positions_bounds = None
            self.refresh_scn_object_listbox()
            if hasattr(self, "scn_status_var"):
                self.scn_status_var.set(f"Missing SCN: {os.path.basename(scn_path)}")
            return

        try:
            with open(scn_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
                lines = f.readlines()
        except Exception as e:
            messagebox.showerror("SCN Editor", f"Failed to read SCN:\n{e}")
            return

        self.scn_path = scn_path
        self.scn_lines = lines
        self._parse_scn_objects()
        self._parse_scn_positions()
        self.refresh_scn_object_listbox()
        if hasattr(self, "scn_status_var"):
            self.scn_status_var.set(
                f"Loaded: {os.path.basename(scn_path)}  "
                f"({len(self.scn_positions)} player pos, {len(self.scn_objects)} objects)"
            )

    def _parse_scn_objects(self):
        """Parse <Objects> blocks into self.scn_objects, keeping line indices for in-place editing"""
        self.scn_objects = []
        self._scn_objects_bounds = None

        lines = self.scn_lines or []
        if not lines:
            return

        start_idx = None
        end_idx = None
        for i, line in enumerate(lines):
            if start_idx is None and "<Objects" in line:
                start_idx = i
                continue
            if start_idx is not None and "</Objects>" in line:
                end_idx = i
                break

        if start_idx is None or end_idx is None or end_idx <= start_idx:
            return

        self._scn_objects_bounds = (start_idx, end_idx)

        i = start_idx + 1
        while i < end_idx:
            line = lines[i]
            if "<Object" not in line:
                i += 1
                continue

            block_start = i
            block_end = i
            while block_end < end_idx and "</Object>" not in lines[block_end]:
                block_end += 1
            if block_end >= end_idx:
                break

            start_line = lines[block_start]
            gt_pos = start_line.find(">")
            if gt_pos == -1:
                i = block_end + 1
                continue

            order = []
            attrs = {}
            for m in re.finditer(r'(\w+)="([^"]*)"', start_line[:gt_pos]):
                k = m.group(1)
                v = m.group(2)
                order.append(k)
                attrs[k] = v

            block_text = "".join(lines[block_start:block_end + 1])
            obj_name = None
            m1 = re.search(r"</Flag>\s*([^<\r\n]+)\s*</Object>", block_text)
            if m1:
                obj_name = m1.group(1).strip()
            else:
                m2 = re.search(r">\s*([^<\r\n]+)\s*</Object>", block_text)
                if m2:
                    obj_name = m2.group(1).strip()

            pos_raw = attrs.get("Position")
            pos_ok = False
            x = y = z = None
            if pos_raw:
                parts = pos_raw.split(",")
                if len(parts) >= 3:
                    try:
                        x = float(parts[0]); y = float(parts[1]); z = float(parts[2])
                        pos_ok = True
                    except ValueError:
                        pos_ok = False

            if pos_ok:
                self.scn_objects.append({
                    "start_idx": block_start,
                    "end_idx": block_end,
                    "attrs": attrs,
                    "attr_order": order,
                    "obj_name": obj_name,
                    "pos": (x, y, z),
                })

            i = block_end + 1

    def _parse_scn_positions(self):
        """Parse the PlayerPlacement <Positions>/</Position> block into self.scn_positions"""
        self.scn_positions = []
        self._scn_positions_bounds = None

        lines = self.scn_lines or []
        if not lines:
            return

        # There can be multiple <Positions> tags in some XMLs, pick the first one that contains </Position>
        positions_blocks = []
        start = None
        for i, line in enumerate(lines):
            if start is None and re.search(r"<Positions\b", line):
                start = i
                continue
            if start is not None and "</Positions>" in line:
                end = i
                positions_blocks.append((start, end))
                start = None

        chosen = None
        for (s, e) in positions_blocks:
            block_txt = "".join(lines[s:e+1])
            if "<Position" in block_txt:
                chosen = (s, e)
                break

        if not chosen:
            return

        start_idx, end_idx = chosen
        self._scn_positions_bounds = (start_idx, end_idx)

        # Count by Number if possible, fallback to file order
        i = start_idx + 1
        seq = 1
        while i < end_idx:
            line = lines[i]
            if "<Position" not in line:
                i += 1
                continue

            # attribute parsing
            order = []
            attrs = {}
            for m in re.finditer(r'(\w+)="([^"]*)"', line):
                k = m.group(1)
                v = m.group(2)
                if k not in order:
                    order.append(k)
                attrs[k] = v

            pos_raw = attrs.get("Position")
            pos_ok = False
            x = y = z = None
            if pos_raw:
                parts = pos_raw.split(",")
                if len(parts) >= 3:
                    try:
                        x = float(parts[0]); y = float(parts[1]); z = float(parts[2])
                        pos_ok = True
                    except ValueError:
                        pos_ok = False

            if pos_ok:
                num = attrs.get("Number", "").strip()
                if num == "":
                    num = str(seq)
                display = f"Player {num}"
                self.scn_positions.append({
                    "line_idx": i,
                    "attrs": attrs,
                    "attr_order": order,
                    "pos": (x, y, z),
                    "display_name": display,
                })
                seq += 1

            i += 1

    def refresh_scn_object_listbox(self):
        if not hasattr(self, "scn_object_listbox"):
            return

        # Preserve selection by (kind, idx) across filtering
        prev_key = None
        try:
            sel = self.scn_object_listbox.curselection()
            if len(sel) == 1 and sel[0] < len(getattr(self, "scn_items_index_by_list", [])):
                prev_key = self.scn_items_index_by_list[sel[0]]
        except Exception:
            prev_key = None

        q = ""
        if hasattr(self, "scn_search_var"):
            try:
                q = (self.scn_search_var.get() or "").strip().lower()
            except Exception:
                q = ""

        self.scn_object_listbox.delete(0, tk.END)
        self.scn_items_index_by_list = []

        # Positions first
        for idx, pos in enumerate(getattr(self, "scn_positions", []) or []):
            a = pos.get("attrs", {})
            num = a.get("Number", "")
            disp = pos.get("display_name") or (f"Player {num}" if num else "Player")
            x, y, z = pos.get("pos") or (None, None, None)
            if x is None or z is None:
                continue

            if q:
                hay = " ".join([disp, str(num), a.get("Player", ""), "position", "playerplacement"]).lower()
                if q not in hay:
                    continue

            self.scn_object_listbox.insert(tk.END, f"[PP] {disp}  ({int(round(x))},{int(round(z))})")
            self.scn_items_index_by_list.append(("Position", idx))

        # Then Objects
        for idx, obj in enumerate(getattr(self, "scn_objects", []) or []):
            a = obj.get("attrs", {})
            oid = a.get("ID", "?")
            en = a.get("EditorName") or obj.get("obj_name") or "Object"
            obj_type = obj.get("obj_name") or ""
            x, y, z = obj.get("pos") or (None, None, None)
            if x is None or z is None:
                continue

            if q:
                hay = " ".join([str(oid), str(en), str(obj_type)]).lower()
                if q not in hay:
                    continue

            display_name = en
            if obj_type and obj_type != en:
                display_name = f"{en} | {obj_type}"
            self.scn_object_listbox.insert(tk.END, f"[{oid}] {display_name}  ({int(round(x))},{int(round(z))})")
            self.scn_items_index_by_list.append(("Object", idx))

        # Restore selection if still visible
        if prev_key is not None and prev_key in self.scn_items_index_by_list:
            new_lb_idx = self.scn_items_index_by_list.index(prev_key)
            self.scn_object_listbox.selection_set(new_lb_idx)
            self.scn_object_listbox.see(new_lb_idx)

    def _get_selected_scn_item(self):
        if not hasattr(self, "scn_object_listbox"):
            return None, None, None
        sel = self.scn_object_listbox.curselection()
        if len(sel) != 1:
            return None, None, None
        lb_idx = sel[0]
        if lb_idx >= len(getattr(self, "scn_items_index_by_list", [])):
            return None, None, None
        kind, idx = self.scn_items_index_by_list[lb_idx]
        if kind == "Object":
            if idx >= len(self.scn_objects):
                return None, None, None
            return kind, self.scn_objects[idx], idx
        if kind == "Position":
            if idx >= len(self.scn_positions):
                return None, None, None
            return kind, self.scn_positions[idx], idx
        return None, None, None

    def _scn_show_mode(self, kind: str):
        """Show Object fields or PlayerPlacement fields"""
        if not hasattr(self, "_scn_obj_widgets") or not hasattr(self, "_scn_pp_widgets"):
            return
        if kind == "Position":
            for w in self._scn_obj_widgets:
                w.grid_remove()
            for w in self._scn_pp_widgets:
                w.grid()
        else:
            for w in self._scn_pp_widgets:
                w.grid_remove()
            for w in self._scn_obj_widgets:
                w.grid()

    def on_scn_object_select(self, event=None):
        kind, item, _ = self._get_selected_scn_item()
        if not item:
            return

        if kind == "Position":
            self._scn_show_mode("Position")
            a = item.get("attrs", {})
            x, y, z = item.get("pos") or ("", "", "")
            self.scn_pp_number_var.set(a.get("Number", ""))
            self.scn_pp_player_var.set(a.get("Player", ""))
            self.scn_pp_defaultcamera_var.set(a.get("DefaultCamera", ""))
            self.scn_pp_camyaw_var.set(a.get("CameraYaw", ""))
            self.scn_pp_campitch_var.set(a.get("CameraPitch", ""))
            self.scn_pp_camzoom_var.set(a.get("CameraZoom", ""))
            self.scn_pp_unit1_var.set(a.get("UnitStartObject1", ""))
            self.scn_pp_unit2_var.set(a.get("UnitStartObject2", ""))
            self.scn_pp_unit3_var.set(a.get("UnitStartObject3", ""))
            self.scn_pp_unit4_var.set(a.get("UnitStartObject4", ""))
            self.scn_pp_rally_var.set(a.get("RallyStartObject", ""))

            self.scn_edit_pos_x_var.set("" if x is None else str(x))
            self.scn_edit_pos_y_var.set("" if y is None else str(y))
            self.scn_edit_pos_z_var.set("" if z is None else str(z))
            self.scn_edit_forward_var.set(a.get("Forward", ""))

            # Center view on this player position (X,Z -> map X,Y)
            try:
                mx = int(round(float(x)))
                my = int(round(float(z)))
                if 0 <= mx <= self.map_width and 0 <= my <= self.map_height:
                    self.center_on_map_coord(mx, my)
            except Exception:
                pass
            return

        # Object
        self._scn_show_mode("Object")
        obj = item
        a = obj.get("attrs", {})
        x, y, z = obj.get("pos") or ("", "", "")

        self.scn_edit_editorname_var.set(a.get("EditorName", ""))
        self.scn_edit_id_var.set(a.get("ID", ""))
        self.scn_edit_player_var.set(a.get("Player", ""))
        self.scn_edit_is_squad_var.set(a.get("IsSquad", ""))
        self.scn_edit_tint_var.set(a.get("TintValue", ""))
        self.scn_edit_pos_x_var.set("" if x is None else str(x))
        self.scn_edit_pos_y_var.set("" if y is None else str(y))
        self.scn_edit_pos_z_var.set("" if z is None else str(z))
        self.scn_edit_forward_var.set(a.get("Forward", ""))
        self.scn_edit_right_var.set(a.get("Right", ""))
        self.scn_edit_group_var.set(a.get("Group", ""))
        self.scn_edit_vvi_var.set(a.get("VisualVariationIndex", ""))
        self.scn_edit_objtype_var.set(obj.get("obj_name") or "")

        # Center view on this object (X,Z -> map X,Y)
        try:
            mx = int(round(float(x)))
            my = int(round(float(z)))
            if 0 <= mx <= self.map_width and 0 <= my <= self.map_height:
                self.center_on_map_coord(mx, my)
        except Exception:
            pass

    def apply_scn_selected_item_changes(self):
        kind, item, idx = self._get_selected_scn_item()
        if not kind or not item:
            messagebox.showinfo("SCN Editor", "Select exactly one SCN item to edit.")
            return
        if not self.scn_lines:
            messagebox.showinfo("SCN Editor", "Load a SCN first.")
            return

        if kind == "Position":
            if not self._scn_positions_bounds:
                messagebox.showinfo("SCN Editor", "This SCN has no <Positions> block to edit.")
                return

            # Gather updates
            new_player = (self.scn_pp_player_var.get() or "").strip()
            new_number = (self.scn_pp_number_var.get() or "").strip()
            new_forward = (self.scn_edit_forward_var.get() or "").strip()
            new_defcam = (self.scn_pp_defaultcamera_var.get() or "").strip()
            new_yaw = (self.scn_pp_camyaw_var.get() or "").strip()
            new_pitch = (self.scn_pp_campitch_var.get() or "").strip()
            new_zoom = (self.scn_pp_camzoom_var.get() or "").strip()
            new_u1 = (self.scn_pp_unit1_var.get() or "").strip()
            new_u2 = (self.scn_pp_unit2_var.get() or "").strip()
            new_u3 = (self.scn_pp_unit3_var.get() or "").strip()
            new_u4 = (self.scn_pp_unit4_var.get() or "").strip()
            new_rally = (self.scn_pp_rally_var.get() or "").strip()

            try:
                px = float(self.scn_edit_pos_x_var.get().strip())
                py = float(self.scn_edit_pos_y_var.get().strip())
                pz = float(self.scn_edit_pos_z_var.get().strip())
            except Exception:
                messagebox.showerror("SCN Editor", "Position X/Y/Z must be valid numbers.")
                return

            # Enforce unique Number within the Positions block (except for this one)
            used_numbers = set()
            for j, p in enumerate(self.scn_positions):
                if j == idx:
                    continue
                n = (p.get("attrs", {}) or {}).get("Number", "").strip()
                if n:
                    used_numbers.add(n)
            if new_number and new_number in used_numbers:
                messagebox.showerror("SCN Editor", f"PP Number '{new_number}' is already used in <Positions>.")
                return

            attrs = dict(item.get("attrs", {}))

            def _set(k, v):
                if v == "":
                    return
                attrs[k] = v

            _set("Player", new_player)
            _set("Number", new_number)
            _set("Forward", new_forward)
            _set("DefaultCamera", new_defcam)
            _set("CameraYaw", new_yaw)
            _set("CameraPitch", new_pitch)
            _set("CameraZoom", new_zoom)
            _set("UnitStartObject1", new_u1)
            _set("UnitStartObject2", new_u2)
            _set("UnitStartObject3", new_u3)
            _set("UnitStartObject4", new_u4)
            _set("RallyStartObject", new_rally)
            attrs["Position"] = f"{px:g},{py:g},{pz:g}"

            # Rebuild the line, keeping indentation and newline
            line_idx = item["line_idx"]
            old_line = self.scn_lines[line_idx]
            ind = re.match(r"\s*", old_line).group(0)
            nl = "\r\n" if old_line.endswith("\r\n") else "\n"

            order = list(item.get("attr_order") or [])
            for k in attrs.keys():
                if k not in order:
                    order.append(k)

            attr_text = " ".join([f'{k}="{attrs.get(k, "")}"' for k in order if k in attrs])
            self.scn_lines[line_idx] = f"{ind}<Position {attr_text} />{nl}"

            self._parse_scn_positions()
            self.refresh_scn_object_listbox()
            if hasattr(self, "scn_status_var") and self.scn_path:
                self.scn_status_var.set(f"Edited (not saved): {os.path.basename(self.scn_path)}")
            return

        # Objects
        if not self._scn_objects_bounds:
            messagebox.showinfo("SCN Editor", "This SCN has no <Objects> block to edit.")
            return

        obj = item
        new_editorname = (self.scn_edit_editorname_var.get() or "").strip()
        new_id = (self.scn_edit_id_var.get() or "").strip()
        new_player = (self.scn_edit_player_var.get() or "").strip()
        new_is_squad = (self.scn_edit_is_squad_var.get() or "").strip()
        new_tint = (self.scn_edit_tint_var.get() or "").strip()
        new_forward = (self.scn_edit_forward_var.get() or "").strip()
        new_right = (self.scn_edit_right_var.get() or "").strip()
        new_group = (self.scn_edit_group_var.get() or "").strip()
        new_vvi = (self.scn_edit_vvi_var.get() or "").strip()

        try:
            px = float(self.scn_edit_pos_x_var.get().strip())
            py = float(self.scn_edit_pos_y_var.get().strip())
            pz = float(self.scn_edit_pos_z_var.get().strip())
        except Exception:
            messagebox.showerror("SCN Editor", "Position X/Y/Z must be valid numbers.")
            return

        file_text = "".join(self.scn_lines)
        used_ids = set(re.findall(r'\bID="([^"]+)"', file_text))
        used_names = set(re.findall(r'\bEditorName="([^"]+)"', file_text))

        cur_a = obj.get("attrs", {})
        cur_id = cur_a.get("ID")
        cur_en = cur_a.get("EditorName")
        if cur_id:
            used_ids.discard(cur_id)
        if cur_en:
            used_names.discard(cur_en)

        if new_id and new_id in used_ids:
            messagebox.showerror("SCN Editor", f"ID '{new_id}' is already used in this SCN.")
            return
        if new_editorname and new_editorname in used_names:
            messagebox.showerror("SCN Editor", f"EditorName '{new_editorname}' is already used in this SCN.")
            return

        attrs = dict(obj.get("attrs", {}))

        def _set(k, v):
            if v == "":
                return
            attrs[k] = v

        _set("EditorName", new_editorname)
        _set("ID", new_id)
        _set("Player", new_player)
        _set("IsSquad", new_is_squad)
        _set("TintValue", new_tint)
        _set("Forward", new_forward)
        _set("Right", new_right)
        _set("Group", new_group)
        _set("VisualVariationIndex", new_vvi)
        attrs["Position"] = f"{px:g},{py:g},{pz:g}"

        start_idx = obj["start_idx"]
        old_line = self.scn_lines[start_idx]
        indent = re.match(r"\s*", old_line).group(0)
        gt = old_line.find(">")
        suffix = old_line[gt + 1:] if gt != -1 else "\n"

        order = list(obj.get("attr_order") or [])
        for k in attrs.keys():
            if k not in order:
                order.append(k)

        attr_text = " ".join([f'{k}="{attrs.get(k, "")}"' for k in order if k in attrs])
        self.scn_lines[start_idx] = f"{indent}<Object {attr_text}>{suffix}"

        self._parse_scn_objects()
        self.refresh_scn_object_listbox()
        if hasattr(self, "scn_status_var") and self.scn_path:
            self.scn_status_var.set(f"Edited (not saved): {os.path.basename(self.scn_path)}")

    def set_scn_selected_item_pos_from_selected_marker(self):
        """Set selected SCN item's Position.X and Position.Z from the selected marker"""
        kind, item, idx = self._get_selected_scn_item()
        if not kind or not item:
            messagebox.showinfo("SCN Editor", "Select exactly one SCN item first.")
            return
        if not self.scn_lines:
            messagebox.showinfo("SCN Editor", "Load a SCN first.")
            return

        sel = self.marker_listbox.curselection()
        if len(sel) != 1:
            messagebox.showinfo("SCN Editor", "Select exactly one marker in the Markers listbox first.")
            return
        lb_idx = sel[0]
        uid = self.listbox_marker_uids[lb_idx] if lb_idx < len(self.listbox_marker_uids) else None
        m = self.get_marker_by_uid(uid)
        if not m:
            messagebox.showerror("SCN Editor", "Could not resolve the selected marker.")
            return

        # Keep Y (height) the same, update X and Z
        try:
            py = float(self.scn_edit_pos_y_var.get().strip())
        except Exception:
            pos = item.get("pos") or (0.0, 0.0, 0.0)
            try:
                py = float(pos[1] or 0.0)
            except Exception:
                py = 0.0

        self.scn_edit_pos_x_var.set(str(float(m["map_x"])))
        self.scn_edit_pos_z_var.set(str(float(m["map_y"])))
        self.scn_edit_pos_y_var.set(str(py))
        self.apply_scn_selected_item_changes()

    def add_scn_object_from_selected_marker(self):
        if not self.scn_lines or not self._scn_objects_bounds:
            messagebox.showinfo("SCN Editor", "Load a SCN first.")
            return

        sel = self.marker_listbox.curselection()
        if len(sel) != 1:
            messagebox.showinfo("SCN Editor", "Select exactly one marker first (to use as Position).")
            return
        lb_idx = sel[0]
        uid = self.listbox_marker_uids[lb_idx] if lb_idx < len(self.listbox_marker_uids) else None
        m = self.get_marker_by_uid(uid)
        if not m:
            messagebox.showerror("SCN Editor", "Could not resolve the selected marker.")
            return

        obj_type = (self.scn_add_type_var.get() or "").strip()
        if not obj_type:
            messagebox.showerror("SCN Editor", "Object Type is required.")
            return

        file_text = "".join(self.scn_lines)

        used_ids_int = set()
        for mm in re.finditer(r'\bID="(\d+)"', file_text):
            try:
                used_ids_int.add(int(mm.group(1)))
            except Exception:
                pass

        new_id = (max(used_ids_int) + 1) if used_ids_int else 1

        used_names = set(re.findall(r'\bEditorName="([^"]+)"', file_text))

        candidate = f"{obj_type}_{new_id}"
        while candidate in used_names:
            candidate += "1"

        player = (self.scn_add_player_var.get() or "0").strip()
        is_squad = (self.scn_add_is_squad_var.get() or "false").strip()
        tint = (self.scn_add_tint_var.get() or "1").strip()
        forward = (self.scn_add_forward_var.get() or "0,0,1").strip()
        right = (self.scn_add_right_var.get() or "1,0,0").strip()
        group = (self.scn_add_group_var.get() or "-1").strip()
        vvi = (self.scn_add_vvi_var.get() or "0").strip()
        try:
            y = float((self.scn_add_y_var.get() or "0").strip())
        except Exception:
            y = 0.0

        x = float(m["map_x"])
        z = float(m["map_y"])

        start_idx, end_idx = self._scn_objects_bounds
        newline = "\n"
        for ln in self.scn_lines:
            if ln.endswith("\r\n"):
                newline = "\r\n"
                break

        indent = "\t\t"
        for o in self.scn_objects:
            sline = self.scn_lines[o["start_idx"]]
            m_ind = re.match(r"\s*", sline)
            if m_ind:
                indent = m_ind.group(0)
                break

        new_line = (
            f'{indent}<Object IsSquad="{is_squad}" Player="{player}" '
            f'ID="{new_id}" TintValue="{tint}" EditorName="{candidate}" '
            f'Position="{x:g},{y:g},{z:g}" Forward="{forward}" Right="{right}" '
            f'Group="{group}" VisualVariationIndex="{vvi}">{obj_type}</Object>{newline}'
        )

        self.scn_lines.insert(end_idx, new_line)

        self._parse_scn_objects()
        self.refresh_scn_object_listbox()
        if hasattr(self, "scn_status_var") and self.scn_path:
            self.scn_status_var.set(f"Added (not saved): {os.path.basename(self.scn_path)}")

    def delete_selected_scn_item(self):
        kind, item, idx = self._get_selected_scn_item()
        if not kind or not item:
            messagebox.showinfo("SCN Editor", "Select exactly one SCN item to delete.")
            return
        if not self.scn_lines:
            messagebox.showinfo("SCN Editor", "Load a SCN first.")
            return

        if kind == "Position":
            if not self._scn_positions_bounds:
                messagebox.showinfo("SCN Editor", "This SCN has no <Positions> block to delete from.")
                return
            a = item.get("attrs", {})
            label = item.get("display_name") or f"Player {a.get('Number','')}"
            if not messagebox.askyesno("SCN Editor", f"Delete '{label}' from <Positions>?"):
                return
            li = item["line_idx"]
            del self.scn_lines[li]
            self._parse_scn_positions()
            self.refresh_scn_object_listbox()
            if hasattr(self, "scn_status_var") and self.scn_path:
                self.scn_status_var.set(f"Deleted (not saved): {os.path.basename(self.scn_path)}")
            return

        # Object
        if not self._scn_objects_bounds:
            messagebox.showinfo("SCN Editor", "This SCN has no <Objects> block to delete from.")
            return

        a = item.get("attrs", {})
        label = a.get("EditorName") or a.get("ID") or "Object"
        if not messagebox.askyesno("SCN Editor", f"Delete '{label}' from <Objects>?"):
            return

        s = item["start_idx"]
        e = item["end_idx"]
        del self.scn_lines[s:e + 1]

        self._parse_scn_objects()
        self.refresh_scn_object_listbox()
        if hasattr(self, "scn_status_var") and self.scn_path:
            self.scn_status_var.set(f"Deleted (not saved): {os.path.basename(self.scn_path)}")

    def sync_scn_objects_from_markers(self):
        """Batch sync: update existing <Objects> and <Positions> positions from markers, append missing markers"""
        if not self.scn_lines:
            messagebox.showinfo("SCN Editor", "Load a SCN first.")
            return
        if not getattr(self, "markers", None):
            messagebox.showinfo("SCN Editor", "No markers exist to sync.")
            return

        marker_by_name = {}
        for m in self.markers:
            nm = (m.get("name") or "").strip()
            if not nm:
                continue
            marker_by_name.setdefault(nm, m)

        if not marker_by_name:
            messagebox.showinfo("SCN Editor", "No named markers to sync.")
            return

        file_text = "".join(self.scn_lines)

        used_editor_names = set(re.findall(r'\bEditorName="([^"]+)"', file_text))
        used_other_names = set(re.findall(r'\bName="([^"]+)"', file_text))
        existing_names_anywhere = set(used_editor_names) | used_other_names

        # IDs across whole file
        used_ids_int = set()
        for mm in re.finditer(r'\bID="(\d+)"', file_text):
            try:
                used_ids_int.add(int(mm.group(1)))
            except Exception:
                pass

        def _newline_style():
            for ln in self.scn_lines:
                if ln.endswith("\r\n"):
                    return "\r\n"
            return "\n"

        newline = _newline_style()

        # Update existing Objects
        updated_obj = 0
        if self._scn_objects_bounds:
            def _rebuild_object_start_line(obj, new_attrs):
                sidx = obj["start_idx"]
                old_line = self.scn_lines[sidx]
                ind = re.match(r"\s*", old_line).group(0)
                gt = old_line.find(">")
                suffix = old_line[gt + 1:] if gt != -1 else newline

                order = list(obj.get("attr_order") or [])
                for k in new_attrs.keys():
                    if k not in order:
                        order.append(k)

                attr_text = " ".join([f'{k}="{new_attrs.get(k, "")}"' for k in order if k in new_attrs])
                self.scn_lines[sidx] = f"{ind}<Object {attr_text}>{suffix}"

            for obj in getattr(self, "scn_objects", []) or []:
                a = obj.get("attrs", {}) or {}
                en = a.get("EditorName")
                if not en:
                    continue
                marker = marker_by_name.get(en)
                if not marker:
                    continue

                pos = obj.get("pos") or (0.0, 0.0, 0.0)
                try:
                    py = float(pos[1])
                except Exception:
                    py = 0.0

                px = float(marker.get("map_x", 0))
                pz = float(marker.get("map_y", 0))

                new_attrs = dict(a)
                new_attrs["Position"] = f"{px:g},{py:g},{pz:g}"
                _rebuild_object_start_line(obj, new_attrs)
                updated_obj += 1

        # Update existing PlayerPlacement Positions
        updated_pp = 0
        if self._scn_positions_bounds:
            for pos in getattr(self, "scn_positions", []) or []:
                a = pos.get("attrs", {}) or {}
                num = (a.get("Number", "") or "").strip()
                # Match markers named "Player N"
                mname = f"Player {num}" if num else (pos.get("display_name") or "")
                marker = marker_by_name.get(mname)
                if not marker:
                    # also try "PlayerN"
                    marker = marker_by_name.get(f"Player{num}") if num else None
                if not marker:
                    continue

                try:
                    py = float((pos.get("pos") or (0, 0, 0))[1])
                except Exception:
                    py = 0.0

                px = float(marker.get("map_x", 0))
                pz = float(marker.get("map_y", 0))

                attrs = dict(a)
                attrs["Position"] = f"{px:g},{py:g},{pz:g}"

                line_idx = pos["line_idx"]
                old_line = self.scn_lines[line_idx]
                ind = re.match(r"\s*", old_line).group(0)
                order = list(pos.get("attr_order") or [])
                for k in attrs.keys():
                    if k not in order:
                        order.append(k)
                attr_text = " ".join([f'{k}="{attrs.get(k, "")}"' for k in order if k in attrs])
                nl = "\r\n" if old_line.endswith("\r\n") else "\n"
                self.scn_lines[line_idx] = f"{ind}<Position {attr_text} />{nl}"
                updated_pp += 1

        # Re-parse before deciding what to add
        self._parse_scn_objects()
        self._parse_scn_positions()

        # Existing names inside <Objects>
        existing_obj_names = set()
        if self._scn_objects_bounds:
            _s, _e = self._scn_objects_bounds
            for ln in self.scn_lines[_s:_e]:
                mm = re.search(r'\bEditorName="([^"]+)"', ln)
                if mm:
                    existing_obj_names.add(mm.group(1))
        else:
            for obj in getattr(self, "scn_objects", []) or []:
                en = (obj.get("attrs", {}) or {}).get("EditorName")
                if en:
                    existing_obj_names.add(en)

        # Existing Numbers in <Positions>
        existing_pp_numbers = set()
        for p in getattr(self, "scn_positions", []) or []:
            n = (p.get("attrs", {}) or {}).get("Number", "")
            if n != "":
                existing_pp_numbers.add(str(n).strip())

        # Helper: detect marker is a player placement marker
        def _player_number_from_marker_name(name: str):
            m = re.match(r"^\s*player\s*#?\s*(\d+)\s*$", name.strip(), re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
            m = re.match(r"^\s*player(\d+)\s*$", name.strip(), re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except Exception:
                    return None
            return None

        # What to add:
        to_add_objects = []
        to_add_pp = []
        skipped_elsewhere = 0

        for name, marker in marker_by_name.items():
            pn = _player_number_from_marker_name(name)
            if pn is not None:
                if str(pn) in existing_pp_numbers:
                    continue
                if name in existing_names_anywhere:
                    skipped_elsewhere += 1
                    continue
                to_add_pp.append((pn, name, marker))
                continue

            # normal objects
            if name in existing_obj_names:
                continue
            if name in existing_names_anywhere:
                skipped_elsewhere += 1
                continue
            to_add_objects.append((name, marker))

        to_add_objects.sort(key=lambda t: t[0].lower())
        to_add_pp.sort(key=lambda t: t[0])

        added_obj = 0
        added_pp = 0

        # Append PP entries
        if to_add_pp:
            # Ensure <Positions> exists; if not, create it right after </PlayerPlacement>
            if not self._scn_positions_bounds:
                insert_after = None
                for i, ln in enumerate(self.scn_lines):
                    if "<PlayerPlacement" in ln:
                        insert_after = i
                        break
                if insert_after is None:
                    # fallback: insert before <Players>
                    for i, ln in enumerate(self.scn_lines):
                        if "<Players" in ln:
                            insert_after = i - 1
                            break
                if insert_after is None:
                    insert_after = 0

                # determine indentation: use the same indentation as the PlayerPlacement line, plus one tab
                base_ind = re.match(r"\s*", self.scn_lines[insert_after]).group(0)
                ind_positions = base_ind
                ind_pos = base_ind + "\t"

                block = [
                    f"{ind_positions}<Positions>{newline}",
                    f"{ind_positions}</Positions>{newline}",
                ]
                self.scn_lines[insert_after + 1:insert_after + 1] = block
                self._parse_scn_positions()

            # Now we have bounds
            p_start, p_end = self._scn_positions_bounds

            # Indentation + template attributes
            indent_pos = "\t\t\t"
            template_attrs = None
            template_order = None
            for p in getattr(self, "scn_positions", []) or []:
                li = p.get("line_idx")
                if li is not None:
                    indent_pos = re.match(r"\s*", self.scn_lines[li]).group(0)
                    template_attrs = dict(p.get("attrs", {}) or {})
                    template_order = list(p.get("attr_order") or [])
                    break

            if template_attrs is None:
                template_attrs = {
                    "Player": "-1",
                    "Number": "1",
                    "Position": "0,0,0",
                    "Forward": "0,0,1",
                    "DefaultCamera": "true",
                    "CameraYaw": "0",
                    "CameraPitch": "42",
                    "CameraZoom": "85",
                    "UnitStartObject1": "-1",
                    "UnitStartObject2": "-1",
                    "UnitStartObject3": "-1",
                    "UnitStartObject4": "-1",
                    "RallyStartObject": "-1",
                }
                template_order = list(template_attrs.keys())

            insert_at = p_end  # before </Positions>
            for pn, name, marker in to_add_pp:
                # keep uniqueness of Number
                nstr = str(pn)
                if nstr in existing_pp_numbers:
                    continue

                x = float(marker.get("map_x", 0))
                z = float(marker.get("map_y", 0))
                # keep Y from template
                try:
                    y = float(template_attrs.get("Position", "0,0,0").split(",")[1])
                except Exception:
                    y = 0.0

                attrs = dict(template_attrs)
                attrs["Number"] = nstr
                attrs["Position"] = f"{x:g},{y:g},{z:g}"

                order = list(template_order)
                for k in attrs.keys():
                    if k not in order:
                        order.append(k)
                attr_text = " ".join([f'{k}="{attrs.get(k, "")}"' for k in order if k in attrs])

                self.scn_lines.insert(insert_at, f"{indent_pos}<Position {attr_text} />{newline}")
                insert_at += 1
                existing_pp_numbers.add(nstr)
                added_pp += 1

            self._parse_scn_positions()

        # Append Object entries
        if to_add_objects and self._scn_objects_bounds:
            start_idx, end_idx = self._scn_objects_bounds

            def _infer_indent_obj():
                for o in self.scn_objects:
                    sline = self.scn_lines[o["start_idx"]]
                    m_ind = re.match(r"\s*", sline)
                    if m_ind:
                        return m_ind.group(0)
                return "\t\t"

            indent = _infer_indent_obj()

            default_type = (getattr(self, "scn_add_type_var", tk.StringVar(value="hook_bldg_sniperplatform_01")).get() or "").strip() or "hook_bldg_sniperplatform_01"
            player = (getattr(self, "scn_add_player_var", tk.StringVar(value="0")).get() or "0").strip()
            is_squad = (getattr(self, "scn_add_is_squad_var", tk.StringVar(value="false")).get() or "false").strip()
            tint = (getattr(self, "scn_add_tint_var", tk.StringVar(value="1")).get() or "1").strip()
            forward = (getattr(self, "scn_add_forward_var", tk.StringVar(value="0,0,1")).get() or "0,0,1").strip()
            right = (getattr(self, "scn_add_right_var", tk.StringVar(value="1,0,0")).get() or "1,0,0").strip()
            group = (getattr(self, "scn_add_group_var", tk.StringVar(value="-1")).get() or "-1").strip()
            vvi = (getattr(self, "scn_add_vvi_var", tk.StringVar(value="0")).get() or "0").strip()
            try:
                default_y = float((getattr(self, "scn_add_y_var", tk.StringVar(value="0")).get() or "0").strip())
            except Exception:
                default_y = 0.0

            insert_at = end_idx
            cur_max_id = max(used_ids_int) if used_ids_int else 0

            for name, marker in to_add_objects:
                obj_type = default_type
                mm = re.match(r"^(.*)_(\d+)$", name)
                if mm:
                    obj_type = (mm.group(1) or default_type).strip() or default_type

                preferred_id = None
                if mm:
                    try:
                        preferred_id = int(mm.group(2))
                    except Exception:
                        preferred_id = None

                if preferred_id is not None and preferred_id not in used_ids_int:
                    new_id = preferred_id
                else:
                    cur_max_id += 1
                    new_id = cur_max_id
                    while new_id in used_ids_int:
                        cur_max_id += 1
                        new_id = cur_max_id

                used_ids_int.add(new_id)

                editor_name = name
                while editor_name in used_editor_names:
                    editor_name += "1"
                used_editor_names.add(editor_name)

                x = float(marker.get("map_x", 0))
                z = float(marker.get("map_y", 0))
                y = default_y

                new_line = (
                    f'{indent}<Object IsSquad="{is_squad}" Player="{player}" '
                    f'ID="{new_id}" TintValue="{tint}" EditorName="{editor_name}" '
                    f'Position="{x:g},{y:g},{z:g}" Forward="{forward}" Right="{right}" '
                    f'Group="{group}" VisualVariationIndex="{vvi}">{obj_type}</Object>{newline}'
                )

                self.scn_lines.insert(insert_at, new_line)
                insert_at += 1
                added_obj += 1

            self._parse_scn_objects()

        self.refresh_scn_object_listbox()

        if hasattr(self, "scn_status_var") and self.scn_path:
            self.scn_status_var.set(f"Synced (not saved): {os.path.basename(self.scn_path)}")

        messagebox.showinfo(
            "SCN Sync",
            f"Updated {updated_pp} player position(s) and {updated_obj} object(s) from marker positions.\n"
            f"Added {added_pp} new player position(s) and {added_obj} new object(s) from markers.\n"
            f"Skipped {skipped_elsewhere} marker(s) because their name already exists elsewhere in the SCN."
        )

    def save_current_scn(self):
        if not self.scn_path or not self.scn_lines:
            messagebox.showinfo("SCN Editor", "Nothing to save (load a SCN first).")
            return
        try:
            with open(self.scn_path, "w", encoding="utf-8", newline="") as f:
                f.writelines(self.scn_lines)
        except Exception as e:
            messagebox.showerror("SCN Editor", f"Failed to save SCN:\n{e}")
            return

        if hasattr(self, "scn_status_var"):
            self.scn_status_var.set(f"Saved: {os.path.basename(self.scn_path)}")


if __name__ == "__main__":
    os.makedirs(folder1, exist_ok=True)
    root = tk.Tk()
    app = ImageMarkerApp(root)
    root.mainloop()
