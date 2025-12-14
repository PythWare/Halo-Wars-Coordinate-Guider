# Halo-Wars-Coordinate-Guider
A GUI Visual Guide Tool for displaying coordinates on map images to help with placing/moving objects, buildings, troops, NPCS, etc stuff.

What's needed to use this tool:

Python 3 and the files included with the release, this is a lightweight GUI tool.

Also make sure to extract the files from scn.zip with either windows, 7zip, etc. It includes the SCN folder which has .SCN files needed for Auto Populating usage. I had to upload it as a zip due to the size.

What this tool does:

Ever got tired of trying to guess where something will spawn/appear on the map? Well this tool will help you. It displays the map images (all 35 Halo Wars 1 maps, skirmish and campaign maps incase you want to mod campaign too) and supports manually typing coordinates or clicking anywhere on the map to get coordinates.

What this essentially does is serve as a visual guide so you don't have to guess for where something will appear in the game, you won't have to constantly open and close the game for every small coordinate adjustment like you used to. Instead, the Coordinate Guider will show you the coordinates needed for what you want. Want to move a base, creep, etc location or just want to see where things are positioned like objects, troops, etc so you can decide where you want to place your stuff? Just click on the map or type coordinates and use those coordinates it displays for the SCN files.

Other features are custom markers for various types, Auto Populate (it reads the .SCN file and automaticaly marks on the map everything listed in the SCN file that is an object, troop, building, wall, etc that uses coordinates), the ability to save/load your markings so you don't lose your progress, name your markers, optional grid overlay, clicking a marker in the list takes you to the position of the marker, scrollbars to move vertically/horizontally when dealing with larger images, boundary support, filtering marker types to display, map legend, zoom in/out (especially useful if you want to see the exact position of a marker when clicking on the marker listbox, brings you in close nicely), delete markers from the listbox, measure distance between markers, etc. 

Controls:

Holding the middle mouse button or holding right click also enables moving around the image if you don't want to use scrollbars. To delete several marks hold the shift button and select the markers, or just for individual marker deleting select and click Delete button on the GUI. To measure distance between markers select 1 marker and then press ctrl + click on the other marker you want to measure.

Coordinate Guider Image with grid overlay disabled and using custom named markers:

<img width="1667" height="922" alt="y14" src="https://github.com/user-attachments/assets/4bfdc986-d723-4ad3-9ec5-11d903430be1" />

Coordinate Guider Image With Grid Enabled:

<img width="1661" height="916" alt="y17" src="https://github.com/user-attachments/assets/c2cbcb36-8c3a-4075-a5ec-1bbbd0bbb979" />

Coordinate Guider with Auto Populate:

<img width="1657" height="625" alt="y15" src="https://github.com/user-attachments/assets/a89e0096-c1e9-4981-9780-8159eb4972df" />

Coordinate Guider with filters:

<img width="1661" height="631" alt="y16" src="https://github.com/user-attachments/assets/b8b2dbcb-5463-4636-ac5f-bcb51a08a972" />

Coordinate Guider with boundaries:

<img width="1659" height="920" alt="y18" src="https://github.com/user-attachments/assets/802eef38-910c-405f-9ca3-bd8bf87d72d1" />

Coordinate Guider with changeable boundary color:

<img width="1657" height="916" alt="y19" src="https://github.com/user-attachments/assets/ed52162d-b00b-46ea-bbe4-ce59c24ddc32" />

Coordinate Guider measuring distance between markers:

<img width="1661" height="756" alt="y20" src="https://github.com/user-attachments/assets/25b34c56-205b-4e29-ba83-1ab9b86d6f56" />

Extra Info:

If you have any issues please let me know on here, reddit, or the halo wars modding discord server.

Info For Halo Wars 2 Usage:

I tried implementing support for Halo Wars 2 maps but I don't own Halo Wars 2 (I only own Halo Wars 1) so Spartan Tanner (a modder from the halo wars discord server) provided me with the minimaps and info needed for scaling most of the Halo Wars 2 maps. The Halo Wars 2 maps I don't have supported yet (since I don't have the needed scaling info yet) are minimap_mp_dlc_m01, minimap_mp_floodcano, minimap_sp_dlc_m01, minimap_sp_dlc_m02, minimap_sp_m02a, minimap_sp_m04a, minimap_sp_m06a. So essentially the Coordinate Guider only supports 26 of the 33 maps for Halo Wars 2. Also, I only have 2 .SCOL files (which i renamed to .SCN for usage with Coordinate Guider) so if you plan to use Auto Populate with Halo Wars 2 maps it will work if the needed .SCN file is in the SCN folder (minimap_mp_bridges.scn and minimap_fort_jordan.scn are the ones I have and included in the repository), if it's missing the Guider will have a popup saying it's not supported yet. If you want Auto Populate supported for all Halo Wars 2 maps I need the .SCOL files and the simsboundmax (specifically SimBoundsMaxX and SimBoundsMaxY) for the maps I listed that I don't have supported yet. However the Guider still works even without Auto Populate for Halo Wars 2 maps that don't have the .SCOL (again, renamed to .SCN for usage with Guider), Auto Populate is just a neat feature that fills the map with objects, troops, buildings, etc described in the SCN/SCOL file.
