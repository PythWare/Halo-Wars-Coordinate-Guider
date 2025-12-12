import os, math, json
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog

# folder used for storing map files, map files must be kept there
folder1 = "maps"

class ImageMarkerApp:
    """A tool designed to make modding with coordinates easier with a visual guide"""
    def __init__(self, root):
        self.root = root
        self.root.title("Halo Wars SCN Coordinate Guider Version 2.2")
        self.root.resizable(True, True)

        # Viewport limits (maximum size)
        self.max_viewport_width = 800
        self.max_viewport_height = 800

        # Current viewport size (adjusted per image since maps vary in size)
        self.viewport_width = self.max_viewport_width
        self.viewport_height = self.max_viewport_height

        # Actual image size (will  update per image)
        self.original_width = self.viewport_width
        self.original_height = self.viewport_height

        # Track current map image name for export/import metadata
        self.current_image_name = None

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

        # Button to mark the image
        self.mark_button = tk.Button(controls_frame, text="Mark", command=self.mark_image)
        self.mark_button.pack(side=tk.LEFT, padx=5)

        # Map selector, clear button, grid controls (left, under controls)
        map_frame = tk.Frame(left_frame)
        map_frame.pack(pady=5)

        self.image_selector = ttk.Combobox(
            map_frame,
            values=[
                "baron_1_swe.png", "beaconhill_2.png", "beasleys_plateau.png", "blood_gulch.png", "campaigntutorial.png",
                "campaigntutorialadvanced.png", "chasms.png", "crevice.png", "exile.png",
                "fort_deen.png", "frozen_valley.png", "glacial_ravine_3.png", "labyrinth.png", "phxscn01.png",
                "phxscn02.png", "phxscn03.png", "phxscn04.png", "phxscn05.png", "phxscn06.png",
                "phxscn07.png", "phxscn08.png", "phxscn09.png", "phxscn10.png", "phxscn11.png",
                "phxscn12.png", "phxscn13.png", "phxscn14.png", "phxscn15.png", "pirth_outskirts.png",
                "redriver_1.png", "release.png", "repository.png", "terminal_moraine.png", "the_docks.png", "tundra.png"
            ],
            state="readonly",
            width=25
        )
        self.image_selector.current(0)  # Select the first image by default
        self.image_selector.pack(side=tk.LEFT, padx=5)
        self.image_selector.bind("<<ComboboxSelected>>", self.update_image)

        # Button to clear markers on the image
        self.clear_button = tk.Button(map_frame, text="Clear Markers", command=self.clear_markers)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        # Grid controls
        tk.Label(map_frame, text="Grid step:").pack(side=tk.LEFT)
        self.grid_step_entry = tk.Entry(map_frame, width=5)
        self.grid_step_entry.insert(0, "32")  # finer default
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

        # Marker list (name + coords) on the right side
        markers_frame = tk.Frame(right_frame)
        markers_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(markers_frame, text="Markers:").pack(anchor="w")

        list_frame = tk.Frame(markers_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.marker_listbox = tk.Listbox(list_frame, height=25, width=30)
        self.marker_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        marker_scroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.marker_listbox.yview)
        marker_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.marker_listbox.config(yscrollcommand=marker_scroll.set)

        # When a marker is selected, pan to it
        self.marker_listbox.bind("<<ListboxSelect>>", self.on_marker_select)

        # Import/Export buttons under the list
        buttons_frame = tk.Frame(markers_frame)
        buttons_frame.pack(fill=tk.X, pady=(5, 0))

        self.export_button = tk.Button(buttons_frame, text="Export Markers", command=self.export_markers)
        self.export_button.pack(side=tk.LEFT, padx=2)

        self.import_button = tk.Button(buttons_frame, text="Import Markers", command=self.import_markers)
        self.import_button.pack(side=tk.LEFT, padx=2)

        # Initialize variables
        self.image = None
        self.image_id = None
        # each marker: {"id": canvas_id, "name": str, "type": str,
        #               "map_x": int, "map_y": int,
        #               "canvas_x": float, "canvas_y": float}
        self.markers = []
        # grid line/cross ids
        self.grid_lines = []

        # Bind mouse click to mark image
        self.canvas.bind("<Button-1>", self.mark_image_with_click)

        # Middle mouse drag to pan
        self.canvas.bind("<ButtonPress-2>", self.start_pan)
        self.canvas.bind("<B2-Motion>", self.do_pan)

        # right click drag also pans
        self.canvas.bind("<ButtonPress-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)

        # Load default image
        self.update_image()

    def validate_int(self, char_typed, new_value):
        if new_value == "":
            return True
        return new_value.isdigit()

    def load_image(self, image_path):
        # Clear previous image, markers, and grid
        self.canvas.delete("all")
        self.clear_markers()
        self.markers = []
        self.grid_lines = []

        # Track current map name
        self.current_image_name = image_path

        # Load image
        path = os.path.join(folder1, image_path)
        try:
            self.image = tk.PhotoImage(file=path)
        except Exception as e:
            messagebox.showerror(
                "Image Loading",
                f"Failed to load image '{path}':\n{e}"
            )
            # Don't continue trying to draw/use dimensions
            self.current_image_name = None
            return

        # Update actual image dimensions
        self.original_width = self.image.width()
        self.original_height = self.image.height()

        # Draw image at 0,0
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.image)

        # Scrollable area
        self.canvas.config(scrollregion=(0, 0, self.original_width, self.original_height))

        # Auto scale viewport (max 800x800)
        self.viewport_width = min(self.original_width, self.max_viewport_width)
        self.viewport_height = min(self.original_height, self.max_viewport_height)
        self.canvas.config(width=self.viewport_width, height=self.viewport_height)

        # Draw grid if enabled
        self.draw_grid()

    def update_image(self, event=None):
        selected_image = self.image_selector.get()
        self.load_image(selected_image)

    # Grid Logic
    def clear_grid(self):
        self.canvas.delete("grid")
        self.grid_lines = []

    def draw_grid(self):
        self.clear_grid()

        if not self.show_grid_var.get():
            return

        fine_color = "#303030"
        coarse_color = "#707070"
        cross_color = "#d0d0d0"

        try:
            fine_step = int(self.grid_step_entry.get())
            if fine_step <= 0:
                raise ValueError
        except ValueError:
            fine_step = 32
            self.grid_step_entry.delete(0, tk.END)
            self.grid_step_entry.insert(0, str(fine_step))

        coarse_factor = 4
        coarse_step = fine_step * coarse_factor

        w = self.original_width
        h = self.original_height

        # vertical lines
        x = 0
        while x <= w:
            is_coarse = (x % coarse_step == 0)
            color = coarse_color if is_coarse else fine_color
            dash = () if is_coarse else (2, 4)
            lid = self.canvas.create_line(
                x, 0, x, h,
                fill=color,
                dash=dash,
                tags=("grid",)
            )
            self.grid_lines.append(lid)
            x += fine_step

        # horizontal lines
        y = 0
        while y <= h:
            is_coarse = (y % coarse_step == 0)
            color = coarse_color if is_coarse else fine_color
            dash = () if is_coarse else (2, 4)
            lid = self.canvas.create_line(
                0, y, w, y,
                fill=color,
                dash=dash,
                tags=("grid",)
            )
            self.grid_lines.append(lid)
            y += fine_step

        # plus shaped crosses at coarse intersections
        size = 4
        x = 0
        while x <= w:
            if x % coarse_step == 0 and 0 < x < w:
                y = 0
                while y <= h:
                    if y % coarse_step == 0 and 0 < y < h:
                        h1 = self.canvas.create_line(
                            x - size, y, x + size, y,
                            fill=cross_color,
                            tags=("grid",)
                        )
                        h2 = self.canvas.create_line(
                            x, y - size, x, y + size,
                            fill=cross_color,
                            tags=("grid",)
                        )
                        self.grid_lines.extend([h1, h2])
                    y += coarse_step
            x += coarse_step

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

    def create_marker_shape(self, marker_type, canvas_x, canvas_y):
        """
        Draw iconified vector markers:
        combination of shapes instead of plain letters
        Returns a list of canvas item IDs or a single ID
        """
        ids = []

        # Faction/base types
        if marker_type == "unsc":
            # UNSC base: square building with a small roof triangle
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

        elif marker_type == "cov":
            # Covenant base: diamond with an inner circle
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

        elif marker_type == "reactor":
            # Reactor: yellow star
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

        # Player markers: colored rings with numbers
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

        # Creeps/neutral Stuff
        elif marker_type == "N1":
            # Spiky sun for neutral/creep types
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

    def add_marker(self, map_x, map_y, canvas_x, canvas_y, name=None, marker_type=None):
        if name is None:
            name = self.name_entry.get().strip()
            if not name:
                name = f"Marker {len(self.markers) + 1}"

        if marker_type is None:
            marker_type = self.get_marker_type_id()
        else:
            # sanity check on imported type, allow all known codes
            allowed_types = {
                "default", "unsc", "cov", "reactor",
                "PL1", "PL2", "PL3", "PL4", "PL5", "PL6",
                "N1",
            }
            if marker_type not in allowed_types:
                marker_type = "default"

        marker_ids = self.create_marker_shape(marker_type, canvas_x, canvas_y)
        if isinstance(marker_ids, (list, tuple)):
            primary_id = marker_ids[0]
        else:
            primary_id = marker_ids
            marker_ids = [marker_ids]

        marker_info = {
            "id": primary_id,       # primary ID for backwards compatibility
            "ids": marker_ids,      # all IDs for this marker which is ring, text, etc
            "name": name,
            "type": marker_type,
            "map_x": map_x,
            "map_y": map_y,
            "canvas_x": canvas_x,
            "canvas_y": canvas_y,
        }
        self.markers.append(marker_info)

        type_symbol = {
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

        self.marker_listbox.insert(tk.END, f"[{type_symbol}] {name}  ({map_x}, {map_y})")

    def mark_image(self):
        try:
            x = int(self.x_entry.get())
            y = int(self.y_entry.get())

            if 0 <= x <= self.original_width and 0 <= y <= self.original_height:
                display_y = self.original_height - y
                display_x = x
                self.add_marker(map_x=x, map_y=y, canvas_x=display_x, canvas_y=display_y)
            else:
                messagebox.showerror(
                    "Error",
                    f"Coordinates must be within the range 0 to {self.original_width} (x) "
                    f"and 0 to {self.original_height} (y)."
                )
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please enter valid integer coordinates.")

    def mark_image_with_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        if not (0 <= canvas_x <= self.original_width and 0 <= canvas_y <= self.original_height):
            return

        map_x = int(round(canvas_x))
        map_y = int(round(self.original_height - canvas_y))

        self.x_entry.delete(0, tk.END)
        self.x_entry.insert(0, str(map_x))
        self.y_entry.delete(0, tk.END)
        self.y_entry.insert(0, str(map_y))

        self.add_marker(map_x=map_x, map_y=map_y, canvas_x=canvas_x, canvas_y=canvas_y)

    def clear_markers(self):
        for m in self.markers:
            ids = m.get("ids") or [m.get("id")]
            for cid in ids:
                if cid is not None:
                    self.canvas.delete(cid)
        self.markers = []
        self.marker_listbox.delete(0, tk.END)

    # Export/Import Logic
    def export_markers(self):
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
                }
                for m in self.markers
            ]
        }

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Export Markers", f"Exported {len(self.markers)} markers.")
        except Exception as e:
            messagebox.showerror("Export Markers", f"Failed to export markers:\n{e}")

    def import_markers(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Import Markers"
        )
        if not filename:
            return

        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import Markers", f"Failed to read file:\n{e}")
            return

        if not isinstance(data, dict) or "markers" not in data:
            messagebox.showerror("Import Markers", "Invalid marker file format.")
            return

        saved_map = data.get("map_image")
        if saved_map and self.current_image_name and saved_map != self.current_image_name:
            proceed = messagebox.askyesno(
                "Map Mismatch",
                f"Markers were saved for map '{saved_map}', but the current map is "
                f"'{self.current_image_name}'. Import anyway?"
            )
            if not proceed:
                return

        markers_data = data.get("markers", [])
        if not isinstance(markers_data, list):
            messagebox.showerror("Import Markers", "Invalid marker list in file.")
            return

        # Clear current markers
        self.clear_markers()

        imported_count = 0
        for m in markers_data:
            try:
                map_x = int(m["map_x"])
                map_y = int(m["map_y"])
            except (KeyError, ValueError, TypeError):
                continue

            if not (0 <= map_x <= self.original_width and 0 <= map_y <= self.original_height):
                continue

            name = m.get("name")
            marker_type = m.get("type", "default")

            canvas_x = map_x
            canvas_y = self.original_height - map_y

            self.add_marker(
                map_x=map_x,
                map_y=map_y,
                canvas_x=canvas_x,
                canvas_y=canvas_y,
                name=name,
                marker_type=marker_type
            )
            imported_count += 1

        messagebox.showinfo("Import Markers", f"Imported {imported_count} markers.")

    # Panning/Dragging
    def start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def do_pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    # When a marker is chosen from the list, pan to it
    def on_marker_select(self, event):
        if not self.marker_listbox.curselection():
            return
        idx = self.marker_listbox.curselection()[0]
        marker = self.markers[idx]

        cx = marker["canvas_x"]
        cy = marker["canvas_y"]

        target_x = cx - self.viewport_width / 2
        target_y = cy - self.viewport_height / 2

        max_x = max(0, self.original_width - self.viewport_width)
        max_y = max(0, self.original_height - self.viewport_height)

        target_x = max(0, min(target_x, max_x))
        target_y = max(0, min(target_y, max_y))

        if self.original_width > 0:
            self.canvas.xview_moveto(target_x / self.original_width)
        if self.original_height > 0:
            self.canvas.yview_moveto(target_y / self.original_height)

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


if __name__ == "__main__":
    os.makedirs(folder1, exist_ok=True)
    root = tk.Tk()
    app = ImageMarkerApp(root)
    root.mainloop()
