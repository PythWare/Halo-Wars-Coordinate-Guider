# Halo Wars Coordinate Guider

A GUI Visual Guide Tool for displaying coordinates on map images to help with placing/moving objects, buildings, troops, NPCs, etc. A comprehensive Guider/Editor with ~3,850 lines of pure Python code using only the standard library (Tkinter).

## Requirements

- Python 3.x ([Download](https://www.python.org/downloads/))
- No external dependencies - uses only Python's built-in Tkinter

## Quick Start

1. **Double-click `start.bat`** to launch the application
2. Alternatively, double-click `Halo_Wars_Coordinate_Guider.pyw` directly

## Project Structure

```
├── Halo_Wars_Coordinate_Guider.pyw  # Main application
├── start.bat                        # Windows launcher script
├── start.ps1                        # PowerShell launcher script
├── maps/                            # 61 map images (HW1 + HW2)
└── scn/                             # 37 SCN files for Auto Populate
```

## Setup Notes

- The `scn/` folder contains `.SCN` files needed for Auto Populate functionality
- I recommend keeping a backup of the SCN files before editing

## What This Tool Does

Ever got tired of trying to guess where something will spawn/appear on the map? This tool will help you! It displays map images (61 maps including Halo Wars 1 and Halo Wars 2 skirmish and campaign maps) and supports manually typing coordinates or clicking anywhere on the map to get coordinates.

This serves as a visual guide so you don't have to guess where something will appear in-game. No more constantly opening and closing the game for every small coordinate adjustment. Instead, the Coordinate Guider shows you the exact coordinates needed. Want to move a base, creep location, or see where things are positioned? Just click on the map or type coordinates and use them in your SCN files.

### Features

- **Custom Markers** - Various marker types with custom naming
- **Auto Populate** - Reads `.SCN` files and automatically marks everything (objects, troops, buildings, walls, etc.)
- **Save/Load** - Save and load your markings to preserve progress
- **Grid Overlay** - Optional grid for precise positioning
- **Boundary Support** - Visualize map boundaries with customizable colors
- **Zoom In/Out** - Get close-up views of marker positions
- **Distance Measurement** - Measure distance between markers
- **Marker Groups** - Organize markers into named groups
- **Search & Filter** - Quick filtering through markers list
- **Drag to Move** - Moving a marker updates its coordinates automatically

### SCN Editor Features

- Load entries from SCN files (Objects and PlayerPlacement sections)
- Search bar for quick filtering
- Edit and remove entries
- Click an entry to jump to its position on the map
- Add new markers directly to the SCN file
- **Batch Sync** - Adds all new markers to the Objects section and updates coordinates
- Save changes directly to SCN files

## Controls

| Action                  | Control                                               |
| ----------------------- | ----------------------------------------------------- |
| Pan/Move around map     | Hold **Middle Mouse** or **Right Click** and drag     |
| Delete multiple markers | Hold **Shift** and select markers, then click Delete  |
| Delete single marker    | Select marker and click Delete button                 |
| Measure distance        | Select a marker, then **Ctrl + Click** another marker |

## Screenshots

### Coordinate Guider with Grid Overlay and Custom Markers

<img width="1759" height="917" alt="Grid overlay with custom markers" src="https://github.com/user-attachments/assets/9d30b132-6c5c-4e48-8f71-1513662453a9" />

### Grid Disabled

<img width="1762" height="889" alt="Grid disabled view" src="https://github.com/user-attachments/assets/170cec26-0a98-4617-947e-a53305ef72cf" />

### Auto Populate

<img width="1753" height="761" alt="Auto populate feature" src="https://github.com/user-attachments/assets/1ae5fe2b-ea24-44a3-b35e-198f7414ec0c" />

### Marker Filters

<img width="1757" height="764" alt="Marker filters" src="https://github.com/user-attachments/assets/3635a001-5d35-40bb-99d2-09a02b19af16" />

### Boundaries

<img width="1765" height="919" alt="Boundary display" src="https://github.com/user-attachments/assets/654a2bb0-5e75-41c9-9229-a7b988f7a1dc" />

### Customizable Boundary Colors

<img width="1768" height="919" alt="Custom boundary color" src="https://github.com/user-attachments/assets/53083d8b-ef07-4dd8-88ff-79be8b84bbe3" />

### Distance Measurement

<img width="1754" height="745" alt="Distance measurement" src="https://github.com/user-attachments/assets/b9a28979-1755-463b-90f0-4f5585b4c79a" />

### Marker Grouping

<img width="1763" height="920" alt="Marker grouping" src="https://github.com/user-attachments/assets/a1400998-0825-459c-8099-7666286ee071" />

### SCN Editor - Objects

<img width="1763" height="920" alt="SCN Editor objects" src="https://github.com/user-attachments/assets/d595e6f7-5cb2-4590-a5c0-c703c8e08466" />

### SCN Editor - Player Placement

<img width="1770" height="916" alt="SCN Editor player placement" src="https://github.com/user-attachments/assets/88179d59-a7ef-4d4c-8ab4-ed19b123a20f" />

### In-Game Result

<img width="1197" height="672" alt="In-game result" src="https://github.com/user-attachments/assets/d20283fb-cd2e-48a6-afc3-d9dafbc12a82" />

## Support

If you have any issues, please let me know on GitHub, Reddit, or the Halo Wars modding Discord server.

## Halo Wars 2 Support

Halo Wars 2 map support was added with help from **Spartan Tanner** (from the Halo Wars modding Discord), who provided minimaps and scaling info.

### Supported Maps

- **26 of 33** Halo Wars 2 maps are currently supported

### Unsupported Maps (need scaling info)

- `minimap_mp_dlc_m01`
- `minimap_mp_floodcano`
- `minimap_sp_dlc_m01`
- `minimap_sp_dlc_m02`
- `minimap_sp_m02a`
- `minimap_sp_m04a`
- `minimap_sp_m06a`

### Auto Populate for HW2

Auto Populate works with `.SCOL` files (renamed to `.SCN`). Currently included:

- `minimap_mp_bridges.scn`
- `minimap_fort_jordan.scn`

The tool works without Auto Populate for maps missing `.SCOL` files - Auto Populate is just a convenience feature.

**Want full HW2 Auto Populate support?** I need the `.SCOL` files and `SimBoundsMaxX`/`SimBoundsMaxY` values for the unsupported maps listed above.
