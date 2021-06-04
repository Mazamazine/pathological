# IN PROGRESS
- A python3 version already is available in Debian so this is 
  me playing around and trying things out.  The level editor 
  is nice and should be added to Debian somehow...

# CHANGES
- Adds ability to play different levelsets to original game
- Adds a level editor to original game
- Adds hotkeys to increase/decrease music volume: '+' and '-'

# TODO
- Ability to remove a level graphically
- Ability to create a new set graphically
- Empty level in editor
- Undo/Redo in editor
- Add a "test level" button in editor
- Clean-up in backups

# TOFIX
- Unlock done level even if no highscore has been recorded
- Key translations for all keyboard layouts
- Pygame 1.9.6 works fine for fullscreen and back, but Pygame 
  Pygame 2.0.1 (SDL 2.0.14, Python 3.9.2) has problems and 
  may lock up your screen if you try to go to fullscreen and 
  back again.

* ----------------------------------------------------------------- *

# Where are levels saved?
All new levels go into the Custom levelset
All edited levels - whatever levelset it is from - will be saved into the Custom set
The custom sets are in the Pathological folder, in \user_circuits\

# How to add an existing levelset?
Copy the levelset into Pathological folder > user_circuits

# How to create a new levelset?
If you're done with the default Custom set, simply rename it in the user_circuits folder.
A new Custom file will automatically be created to start the new set

# How to remove a level or a set?
There's no other choice at the moment but to open the set file in the user_circuits folder to remove it.
To remove a set, remove the set file in the user_circuits folder.

* ----------------------------------------------------------------- *

ReadMe updated by Nina Ripoll
On Feb. 6th, 2016
Amended for Python 3 by flowerbug

* ----------------------------------------------------------------- *

Copyright (C) 2003  John-Paul Gignac (Game)
          (C) 2004  Joe Wreschnig (Game)
          (C) 2016 Nina Ripoll (Editor)
          (C) 2021 flowerbug

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
