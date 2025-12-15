# Halo-Wars-Coordinate-Guider
A GUI Visual Guide Tool for displaying coordinates on map images to help with placing/moving objects, buildings, troops, NPCS, etc stuff.

What's needed to use this tool:

Python 3 and the files included with the release, this is a lightweight GUI tool.

Also make sure to extract the files from scn.zip with either windows, 7zip, etc. It includes the SCN folder which has .SCN files needed for Auto Populating usage. I had to upload it as a zip due to the size.

What this tool does:

Ever got tired of trying to guess where something will spawn/appear on the map? Well this tool will help you. It displays the map images (all 35 Halo Wars 1 maps, skirmish and campaign maps incase you want to mod campaign too) and supports manually typing coordinates or clicking anywhere on the map to get coordinates.

What this essentially does is serve as a visual guide so you don't have to guess for where something will appear in the game, you won't have to constantly open and close the game for every small coordinate adjustment like you used to. Instead, the Coordinate Guider will show you the coordinates needed for what you want. Want to move a base, creep, etc location or just want to see where things are positioned like objects, troops, etc so you can decide where you want to place your stuff? Just click on the map or type coordinates and use those coordinates it displays for the SCN files.

Other features are custom markers for various types, Auto Populate (it reads the .SCN file and automatically marks on the map everything listed in the SCN file that is an object, troop, building, wall, etc that uses coordinates), the ability to save/load your markings so you don't lose your progress, name your markers, optional grid overlay, clicking a marker in the list takes you to the position of the marker, scrollbars to move vertically/horizontally when dealing with larger images, boundary support, filtering marker types to display, map legend, zoom in/out (especially useful if you want to see the exact position of a marker when clicking on the marker listbox, brings you in close nicely), delete markers from the listbox, measure distance between markers, moving a marker on the map updates its coordinates for you automatically, you can now group markers into named groups, search bar for filtering quickly through markers list, etc.

For SCN Editor it loads entries from a SCN file (specifically Objects and PlayerPlacement sections since the tool is primarily a visual guide), a search bar for quick filtering, editing entries, adding new markers to the SCN file for you (meaning you don't have to manually type it out in the xml file), batch syncing (adds markers not currently within the Objects section of the SCN file and updates all entries for Objects/PlayerPlacement with the current coordinates they have in the SCN Coordinate Guider), save changes, etc. So if you had like, 1,000 new markers added to the map image the sync button will add them all and when you click save all of them are added to the SCN file. This saves so much time because that saves you from having to type thousands of lines manually.

Controls:

Holding the middle mouse button or holding right click also enables moving around the image if you don't want to use scrollbars. To delete several marks hold the shift button and select the markers, or just for individual marker deleting select and click Delete button on the GUI. To measure distance between markers select 1 marker and then press ctrl + click on the other marker you want to measure.

Coordinate Guider Image with grid overlay enabled and using custom named markers:

<img width="1759" height="917" alt="y25" src="https://github.com/user-attachments/assets/9d30b132-6c5c-4e48-8f71-1513662453a9" />


Coordinate Guider Image With Grid Disabled:

<img width="1762" height="889" alt="y14" src="https://github.com/user-attachments/assets/170cec26-0a98-4617-947e-a53305ef72cf" />

Coordinate Guider with Auto Populate:

<img width="1753" height="761" alt="y16" src="https://github.com/user-attachments/assets/1ae5fe2b-ea24-44a3-b35e-198f7414ec0c" />

Coordinate Guider with filters:

<img width="1757" height="764" alt="y17" src="https://github.com/user-attachments/assets/3635a001-5d35-40bb-99d2-09a02b19af16" />

Coordinate Guider with boundaries:

<img width="1765" height="919" alt="y18" src="https://github.com/user-attachments/assets/654a2bb0-5e75-41c9-9229-a7b988f7a1dc" />

Coordinate Guider with changeable boundary color:

<img width="1768" height="919" alt="y19" src="https://github.com/user-attachments/assets/53083d8b-ef07-4dd8-88ff-79be8b84bbe3" />

Coordinate Guider measuring distance between markers:

<img width="1754" height="745" alt="y21" src="https://github.com/user-attachments/assets/b9a28979-1755-463b-90f0-4f5585b4c79a" />

Coordinate Guider grouping:

<img width="1763" height="920" alt="y22" src="https://github.com/user-attachments/assets/a1400998-0825-459c-8099-7666286ee071" />

SCN Editor Objects Example:

<img width="1763" height="920" alt="y23" src="https://github.com/user-attachments/assets/d595e6f7-5cb2-4590-a5c0-c703c8e08466" />

SCN Editor PlayerPlacement Example:

<img width="1770" height="916" alt="y24" src="https://github.com/user-attachments/assets/88179d59-a7ef-4d4c-8ab4-ed19b123a20f" />

Extra Info:

If you have any issues please let me know on here, reddit, or the halo wars modding discord server.

Info For Halo Wars 2 Usage:

I tried implementing support for Halo Wars 2 maps but I don't own Halo Wars 2 (I only own Halo Wars 1) so Spartan Tanner (a modder from the halo wars discord server) provided me with the minimaps and info needed for scaling most of the Halo Wars 2 maps. The Halo Wars 2 maps I don't have supported yet (since I don't have the needed scaling info yet) are minimap_mp_dlc_m01, minimap_mp_floodcano, minimap_sp_dlc_m01, minimap_sp_dlc_m02, minimap_sp_m02a, minimap_sp_m04a, minimap_sp_m06a. So essentially the Coordinate Guider only supports 26 of the 33 maps for Halo Wars 2. Also, I only have 2 .SCOL files (which i renamed to .SCN for usage with Coordinate Guider) so if you plan to use Auto Populate with Halo Wars 2 maps it will work if the needed .SCN file is in the SCN folder (minimap_mp_bridges.scn and minimap_fort_jordan.scn are the ones I have and included in the repository), if it's missing the Guider will have a popup saying it's not supported yet. If you want Auto Populate supported for all Halo Wars 2 maps I need the .SCOL files and the simsboundmax (specifically SimBoundsMaxX and SimBoundsMaxY) for the maps I listed that I don't have supported yet. However the Guider still works even without Auto Populate for Halo Wars 2 maps that don't have the .SCOL (again, renamed to .SCN for usage with Guider), Auto Populate is just a neat feature that fills the map with objects, troops, buildings, etc described in the SCN/SCOL file.
