#! /usr/bin/python
# -*- coding: iso-8859-1 -*-
"""
Copyright (C) 2003  John-Paul Gignac (Game)
          (C) 2004  Joe Wreschnig (Game)
          (C) 2016 Nina Ripoll (Editor)

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
"""

# Import Modules
import os, pygame, random, time, math, re, sys, getpass, hashlib
md5 = hashlib.md5()

from shutil import copyfile
from pygame.locals import *

# Parse the command line
screenshot = 0
fullscreen = 0
colorblind = 0
sound_on = 1
music_on = 1
music_pending_song = 0
for arg in sys.argv[1:]:
	if arg == '-s':
		screenshot = 1
	elif arg == '-f':
		fullscreen = 1
	elif arg == '-cb':
		colorblind = 1
	elif arg == '-q':
		sound_on = 0
		music_on = 0
	elif arg[0] == '-':
		print("Usage: "+sys.argv[0]+" [-cb] [-f] [-s]\n")
		sys.exit(1)
	else:
		print("Usage: "+sys.argv[0]+" [-cb] [-f] [-s]\n")
		sys.exit(1)

if colorblind:
	cbext = '-cb'
else:
	cbext = ''

# Game constants
wheel_steps = 9
frames_per_sec = 100
timer_width = 36
timer_margin = 4
info_height = 20

# Volume levels
intro_music_volume = 0.3
ingame_music_volume = 0.3
sound_effects_volume = 0.6

# Changing these may affect the playability of levels
default_colors = (2,3,4,6)  # Blue, Green, Yellow, Red
default_stoplight = (6,4,3) # Red, Yellow, Green

# Don't change these constants unless you
# redo all of the levels
horiz_tiles = 8
vert_tiles = 6

# Don't change these constants unless you
# update the graphics files correspondingly.
screen_width = 1000
screen_height = 800
marble_size = 28
tile_size = 92
wheel_margin = 4
stoplight_marble_size = 28

# The positions of the holes in the wheels in
# each of the three rotational positions
holecenter_radius = (tile_size - marble_size) / 2 - wheel_margin
holecenters = []
for i in range(wheel_steps):
	theta = math.pi * i / (2 * wheel_steps)
	c = math.floor( 0.5 + math.cos(theta)*holecenter_radius)
	s = math.floor( 0.5 + math.sin(theta)*holecenter_radius)
	holecenters.append((
		(tile_size/2 + s, tile_size/2 - c),
		(tile_size/2 + c, tile_size/2 + s),
		(tile_size/2 - s, tile_size/2 + c),
		(tile_size/2 - c, tile_size/2 - s)))

# Directions/tiles references
tilesSymbols = {'Tile':'','Wheel':'O','Painter':'&','Filter':'#','Buffer':'@',\
	'Replicator':'*','Shredder':'X', 'Teleporter':'=','Stoplight':'!','Trigger':'%'}
directionsSymbols = ['^','>','v','<']

# More global variables
board_width = horiz_tiles * tile_size
board_height = vert_tiles * tile_size
launch_timer_pos = (0,info_height)
board_pos = (timer_width, info_height + marble_size)
timer_height = board_height + marble_size
music_loaded = 0

# Levelset variables
levelset = 'all-boards'
levelsetFolder = 'circuits'
customsSetsFiles = ['Default']
customsSetsFiles += [f for f in os.listdir('user_circuits') \
	if os.path.isfile(os.path.join('user_circuits', f)) and '~' not in f]

# Functions to create our resourcesxws
def load_image(name, colorkey=-1, size=None):
	fullname = os.path.join('graphics', name)
	try:
		image = pygame.image.load(fullname)
	except pygame.error as message:
		print('Cannot load image:', fullname)
		raise SystemExit(message)

	if size is not None:
		image = pygame.transform.scale( image, size)
	image = image.convert()

	if colorkey is not None:
		if colorkey == -1:
			colorkey = image.get_at((0,0))
		image.set_colorkey(colorkey, RLEACCEL)
	return image

def load_sound(name, volume=1.0):
	class NoneSound:
		def play(self): pass
	if not pygame.mixer or not pygame.mixer.get_init():
		return NoneSound()
	fullname = os.path.join('sounds', name)
	try:
		sound = pygame.mixer.Sound(fullname)
	except pygame.error as message:
		print('Cannot load sound:', fullname)
		return NoneSound()

	sound.set_volume( volume * sound_effects_volume)

	return sound

def play_sound(sound):
	if sound_on: sound.play()

def start_music(name, volume=-1):
	global music_pending_song, music_loaded, music_volume

	music_volume = volume

	if not music_on:
		music_pending_song = name
		return

	if not pygame.mixer or not pygame.mixer.music:
		print("Background music not available.")
		return
	pygame.mixer.music.stop()
	fullname = os.path.join('music', name)
	try:
		pygame.mixer.music.load(fullname)
	except pygame.error as message:
		print('Cannot load music:', fullname)
		return
	music_loaded = 1
	pygame.mixer.music.play(-1)

	if music_volume >= 0:
		pygame.mixer.music.set_volume( music_volume)

	music_pending_song = 0

def toggle_fullscreen():
	global fullscreen
	if pygame.display.toggle_fullscreen():
		fullscreen = fullscreen ^ 1
		return 1
	else:
		return 0

def toggle_sound():
	global sound_on
	sound_on = sound_on ^ 1

def toggle_music():
	global music_pending_song, music_on
	music_on = music_on ^ 1
	if music_on:
		if music_pending_song:
			start_music( music_pending_song)
		elif music_loaded:
			pygame.mixer.music.unpause()
	elif music_loaded:
		if not music_pending_song:
			pygame.mixer.music.pause()

def setLevelset():
	global levelset, levelsetFolder
	levelset = customsSetsFiles[IntroScreen.start_levelset] 
	if levelset == 'Default':
		levelset = 'all-boards'
		levelsetFolder = 'circuits'
	else: levelsetFolder = 'user_circuits'
	IntroScreen.start_level = 0
	
def countLevels(customSet=False):

	if customSet==True: circuit = ('user_circuits','Custom')
	else: circuit = (levelsetFolder,levelset)

	fullname = os.path.join(circuit[0], circuit[1])
	f = open( fullname)
	j=0
	while 1:
		line = f.readline()
		if line == '': break
		if line[0] == '|': j += 1
	f.close()
	
	numlevels = j / vert_tiles

	return numlevels

# A better tick function
next_frame = pygame.time.get_ticks()
def my_tick( frames_per_sec):
	global next_frame
	# Wait for the next frame
	next_frame += 1000.0 / frames_per_sec
	now = pygame.time.get_ticks()
	if next_frame < now:
		# No time to wait - just hide our mistake
		# and keep going as fast as we can.
		next_frame = now
	else:
		pygame.time.wait( int(next_frame) - now)

# Load the sounds
def load_sounds():
	global filter_admit,wheel_turn,wheel_completed,change_color
	global direct_marble,ping,trigger_setup,teleport,marble_release
	global levelfinish,die,incorrect,switch,shredder,replicator
	global extra_life,menu_scroll,menu_select
	
	filter_admit = load_sound('filter_admit.wav', 0.8)
	wheel_turn = load_sound('wheel_turn.wav', 0.8)
	wheel_completed = load_sound('wheel_completed.wav', 0.7)
	change_color = load_sound('change_color.wav', 0.8)
	direct_marble = load_sound('direct_marble.wav', 0.6)
	ping = load_sound('ping.wav', 0.8)
	trigger_setup = load_sound('trigger_setup.wav')
	teleport = load_sound('teleport.wav', 0.6)
	marble_release = load_sound('marble_release.wav', 0.5)
	levelfinish = load_sound('levelfinish.wav', 0.6)
	die = load_sound('die.wav')
	incorrect = load_sound('incorrect.wav', 0.15)
	switch = load_sound('switch.wav')
	shredder = load_sound('shredder.wav')
	replicator = load_sound('replicator.wav')
	extra_life = load_sound('extra_life.wav')
	menu_scroll = load_sound('menu_scroll.wav', 0.8)
	menu_select = load_sound('switch.wav')

# Load the fonts for various parts of the game
def load_fonts():
	global launch_timer_font,active_marbles_font,popup_font,info_font

	launch_timer_font = pygame.font.Font(None, timer_width - 2*timer_margin)
	active_marbles_font = pygame.font.Font(None, marble_size)
	popup_font = pygame.font.Font(None, 24)
	info_font = pygame.font.Font(None, info_height)

# Load all of the images for the various game classes.
# The images are stored as class variables in the corresponding classes.
def load_images():
	Marble.images = []
	for i in range(9):
		Marble.images.append( load_image('marble-'+repr(i)+cbext+'.png', -1,
			(marble_size, marble_size)))
	Marble.crossImg = load_image('cross.png', 0, (marble_size,marble_size))
	Marble.onPathImg = load_image('marblePath.png', -1, (tile_size-6,tile_size-6))

	Tile.plain_tiles = []
	Tile.tunnels = []
	for i in range(16):
		tile = load_image('tile.png', (206,53,53), (tile_size,tile_size))
		path = load_image('path-'+repr(i)+'.png', -1, (tile_size,tile_size))
		tile.blit( path, (0,0))
		Tile.plain_tiles.append( tile)
		Tile.tunnels.append(load_image('tunnel-'+repr(i)+'.png',
			-1,(tile_size,tile_size)))
	Tile.paths = 0
	
	Tile.image = load_image('tile.png', (206,53,53), (tile_size,tile_size))
	Tile.image.blit(load_image('blank-bg-tile.png',-1,(tile_size,tile_size)), (0,0))
	Tile.imageSmall = load_image('blank-bg-tile.png',-1,(tile_size-6,tile_size-6))
	
	Wheel.image = load_image('wheel.png',-1,(tile_size,tile_size))
	
	Buffer.bottom = load_image('buffer.png',-1,(tile_size,tile_size))
	Buffer.top = load_image('buffer-top.png',-1,(tile_size,tile_size))
	Buffer.selectedImg = [load_image('buffer-empty.jpg',-1,(38,38)), \
		load_image('buffer-full.jpg',-1,(38,38))]
	
	Painter.images = []
	for i in range(8):
		Painter.images.append( load_image('painter-'+repr(i)+cbext+'.png', -1,
			(tile_size,tile_size)))

	Filter.images = []
	for i in range(8):
		Filter.images.append( load_image('filter-'+repr(i)+cbext+'.png', -1,
			(tile_size,tile_size)))

	Director.images = (
		load_image('director-0.png',-1,(tile_size,tile_size)),
		load_image('director-1.png',-1,(tile_size,tile_size)),
		load_image('director-2.png',-1,(tile_size,tile_size)),
		load_image('director-3.png',-1,(tile_size,tile_size)),
		)

	Shredder.image = load_image('shredder.png',-1,(tile_size,tile_size))

	Switch.images = []
	for i in range(4):
		Switch.images.append( [])
		for j in range(4):
			if i == j: Switch.images[i].append( None)
			else: Switch.images[i].append( load_image(
				'switch-'+repr(i)+repr(j)+'.png',-1,(tile_size,tile_size)))
	Switch.directionsImages = [Switch.images[0][1],Switch.images[1][0], \
		Switch.images[2][1],Switch.images[3][2]]

	Replicator.image = load_image('replicator.png',-1,(tile_size,tile_size))
	Replicator.selectedImg = {2:load_image('replicatorX2.jpg',-1,(38,38)), \
		4:load_image('replicatorX4.jpg',-1,(38,38))}

	Teleporter.image_h = load_image('teleporter-h.png',-1,(tile_size,tile_size))
	Teleporter.image_v = load_image('teleporter-v.png',-1,(tile_size,tile_size))

	Trigger.image = load_image('trigger.png',-1,(tile_size,tile_size))

	Stoplight.image = load_image('stoplight.png',-1,(tile_size,tile_size))
	Stoplight.smallmarbles = []
	for im in Marble.images:
		Stoplight.smallmarbles.append( pygame.transform.scale(im,
			(stoplight_marble_size,stoplight_marble_size)))

	Board.toolOptionsImg = load_image('options'+cbext+'.jpg', None, (736,200))
	Board.saveIcon = load_image('save-icon.jpg', -1, (34,34))
	Board.exitIcon = load_image('exit.png', -1, (40,40))

	IntroScreen.background = load_image('introEditor.png', None,
		(screen_width, screen_height))
	IntroScreen.menu_font = pygame.font.Font(
		None, IntroScreen.menu_font_height)
	IntroScreen.scroller_font = pygame.font.Font(
		None, IntroScreen.scroller_font_height)

# Function to set the video mode
def set_video_mode():
	global screen

	icon = pygame.image.load(os.path.join('graphics','icon.png'))
	icon.set_colorkey(icon.get_at((0,0)), RLEACCEL)
	pygame.display.set_icon(icon) # Needed both before and after set_mode
	screen = pygame.display.set_mode( (screen_width, screen_height),
		fullscreen * FULLSCREEN)
	pygame.display.set_icon(icon) # Needed both before and after set_mode
	pygame.display.set_caption('Pathological')

# Classes for our game objects
class Marble:
	def __init__(self, color, center, direction, tilePos):
		self.color = color
		self.rect = pygame.Rect((0,0,marble_size,marble_size))
		self.rect.center = center
		self.direction = direction
		self.tilePos = tilePos

	def update(self, board): pass

	def draw(self, screen):
		screen.blit( self.images[self.color], self.rect.topleft)

class Tile:
	def __init__(self, paths=0, center=None):
		self.paths = paths
		self.empty = 0
		
		if center is None:
			center = (0,0)

		self.center = center
		self.rect = pygame.Rect((0,0,tile_size,tile_size))
		self.rect.center = center
		self.drawn = 0

	def draw_back(self, surface):
		if self.empty==1:
			surface.blit( self.image, self.rect.topleft)
			self.empty = 0
		if self.drawn: return 0
		surface.blit( self.plain_tiles[self.paths], self.rect.topleft)
		self.drawn = 1
		return 1

	def update(self, board): pass

	def draw_fore(self, surface): return 0

	def click(self, board, posx, posy, tile_x, tile_y): pass

class Wheel(Tile):
	def __init__(self, paths, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer

	def draw_back(self, surface):
		if self.drawn: return 0
		Tile.draw_back(self, surface)
		surface.blit( self.image, self.rect.topleft)
		return 1

	def update(self, board): pass
	
	def draw_fore(self, surface): return 0
	
	def click(self, board, posx, posy, tile_x, tile_y): pass

class Buffer(Tile):
	def __init__(self, paths, color=-1):
		Tile.__init__(self, paths) # Call base class intializer
		self.marble = color
		self.entering = None

	def draw_back(self, surface):
		if self.drawn: return 0

		Tile.draw_back(self, surface)

		color = self.marble
		if color >= 0:
			holecenter = self.rect.center
			surface.blit( Marble.images[color],
				(holecenter[0]-marble_size/2,
				holecenter[1]-marble_size/2))
		else:
			surface.blit( self.bottom, self.rect.topleft)

		return 1

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.top, self.rect.topleft)
		return 0

class Painter(Tile):
	def __init__(self, paths, color, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		self.color = color

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.images[self.color], self.rect.topleft)
		return 0

class Filter(Tile):
	def __init__(self, paths, color, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		self.color = color

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.images[self.color], self.rect.topleft)
		return 0

class Director(Tile):
	def __init__(self, paths, direction, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		self.direction = direction

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.images[self.direction], self.rect.topleft)
		return 0

class Shredder(Tile):
	def __init__(self, paths, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.image, self.rect.topleft)
		return 0

class Switch(Tile):
	def __init__(self, paths, dir1, dir2, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		self.curdir = dir1
		self.otherdir = dir2

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.images[self.curdir][self.otherdir],
			self.rect.topleft)
		return 0

class Replicator(Tile):
	def __init__(self, paths, count, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		self.count = count
		self.pending = []
		
	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.image, self.rect.topleft)
		textLabel= info_font.render( 'x'+str(self.count), 1, (0,0,0))
		surface.blit( textLabel, (self.rect.left+40,self.rect.top+52))
		return 0

	def update(self, board): pass

class Teleporter(Tile):
	def __init__(self, paths, other=None, center=None):
		Tile.__init__(self, paths, center) # Call base class intializer
		if paths & 5: self.image = self.image_v
		else: self.image = self.image_h
		self.labelDrawn = False

	def draw_fore(self, surface):
		surface.blit( self.tunnels[self.paths], self.rect.topleft)
		surface.blit( self.image, self.rect.topleft)
		if not self.labelDrawn:
			textLabel= info_font.render( str(self.label), 1, (0,0,0))
			screen.blit( textLabel, (self.rect.left+4,self.rect.top+2))
			self.labelDrawn = True
		return 0

class Trigger(Tile):
	def __init__(self, colors, center=None):
		Tile.__init__(self, 0, center) # Call base class intializer
		self.marbles = None
		self._setup( colors)

	def _setup(self, colors):
		self.countdown = 0
		self.marbles = [
			random.choice(colors),
			random.choice(colors),
			random.choice(colors),
			random.choice(colors),
			]
		self.drawn = 0

	def update(self, board): pass

	def draw_back(self, surface):
		if self.drawn: return 0
		Tile.draw_back(self, surface)
		surface.blit( self.image, self.rect.topleft)
		if self.marbles is not None:
			for i in range(4):
				surface.blit( Marble.images[self.marbles[i]],
					(holecenters[0][i][0]+self.rect.left-marble_size/2,
					 holecenters[0][i][1]+self.rect.top-marble_size/2))
		return 1

class Stoplight(Tile):
	def __init__(self, colors, center=None):
		Tile.__init__(self, 0, center) # Call base class intializer
		self.marbles = list(colors)
		self.current = 0

	def draw_back(self, surface):
		if self.drawn: return 0
		Tile.draw_back(self, surface)
		surface.blit( self.image, self.rect.topleft)
		for i in range(self.current,3):
			surface.blit( self.smallmarbles[self.marbles[i]],
				(self.rect.centerx-14,
				 self.rect.top+3+(29*i)))
		return 1

class Board:
	def __init__(self, game, pos):
		self.game = game
		self.level = game.level
		self.savedFromDefaultSet = False
		self.pos = pos
		self.marbles = []
		self.screen = game.screen
		self.trigger = None
		self.stoplight = None
		self.quitPopup = 0
		self.warningPopup = []
		self.name = "Unnamed"
		self.boardTimer = 600
		self.launchTimer = 6
		self.author = getpass.getuser().title()
		self.live_marbles_limit = 10
		self.colors = default_colors
		self.StoplightColors = default_stoplight
				
		self.levelConfig_drawn = 0
		self.tools_drawn = 0
		self.selectedOptions_drawn = 0
		# Tools / toolTiles positions
		self.toolsList = {(8,0):'Wheel',(9,0):'Tile',(8,1):'Painter',(9,1):'Filter', \
			(8,2):'Buffer',(9,2):'Teleporter', (8,3):'Switch',(9,3):'Replicator', \
			(8,4):'Director',(9,4):'Shredder',(8,5):'Trigger',(9,5):'Stoplight', \
			(8,6):'Tile', (9,6):'Marble'}
		# Tools images
		self.toolsImages = {'Wheel':((0,0),Wheel.image), 'Painter':((0,1),Painter.images[0]), \
			'Filter':((1,1),Filter.images[0]), 'Buffer':((0,2),Buffer.top), \
			'Teleporter':((1,2),Teleporter.image_v), 'Switch':((0,3),Switch.images[0][2]), \
			'Replicator':((1,3),Replicator.image), 'Director':((0,4),Director.images[0]), \
			'Shredder':((1,4),Shredder.image), 'Stoplight':((1,5),Stoplight.image),\
			'Trigger':((0,5),Trigger.image), 'Path':((1,0),Tile.plain_tiles[5]), \
			'Tile':((0,6),Tile.imageSmall),	'Marble':((1,6),Marble.onPathImg)}
		# Option Tiles positions
		self.colorOptionsPos = {(0,0):6,(1,0):4,(0,1):3,(1,1):2,(0,2):5,(1,2):7,(0,3):1,(1,3):0}
		self.pathOptionsPos = {(2,0):1,(2,1):4,(2,2):8,(2,3):2,(3,0):5,(3,1):10,(3,2):3,(3,3):9, \
							(4,0):6,(4,1):12,(4,2):15,(4,3):11,(5,0):14,(5,1):7,(5,2):13,(5,3):0}
		self.tool = 'Wheel'
		self.toolPath = 5	
		self.toolColor = 0
		self.toolBuffer = 0
		self.toolSwitchDirector = 0
		self.toolSwitchDirection = 3
		self.toolReplicatorFactor = 2
		self.toolTeleporters = {}
		self.toolTeleporterLabel = 0

		# Create the board array
		self.tiles = []
		for j in range( vert_tiles):
			row = list(range( horiz_tiles))
			self.tiles.append( row)

		# Load the level
		self._load( game.circuit, self.level)

		# Create The Background
		self.background = pygame.Surface(screen.get_size()).convert()
		self.background.fill((200, 200, 200)) # Color of Info Bar

		# Draw the Backdrop
		backdrop = load_image('backdrop.jpg', None,
			(horiz_tiles * tile_size, vert_tiles * tile_size))
		self.background.blit( backdrop, board_pos);
				
		# Draw options box + save / exit icons
		self.background.blit( self.toolOptionsImg, \
			(board_pos[0], tile_size*7-info_height*2))
		self.background.blit( self.saveIcon, \
			(board_pos[0]+tile_size*9+45, tile_size*8-info_height*2+55))
		self.background.blit( self.exitIcon, \
			(board_pos[0]+tile_size*9+85, tile_size*8-info_height*2+55))

		# Initialize the screen
		screen.blit(self.background, (0, 0))
		
		if self.StoplightColors != default_stoplight:
			i=0
			for color in self.StoplightColors:
				self.toolColor = color
				self.setStoplightColor(i)
				i+=1
			self.toolColor = 0
	
	def draw_tools(self, dirty_rects):
		
		if self.tools_drawn == 1: return

		# Prepare
		toolsSurface = pygame.Surface((190,650)).convert()
		toolsSurface.fill((200, 200, 200))
		screen.blit(toolsSurface, (772, 45))
		selectedSurface = pygame.Surface((tile_size,tile_size)).convert()
		selectedSurface.fill((100, 200, 200))
		for tool,coord_img in list(self.toolsImages.items()):
			coordX,coordY=coord_img[0]
			posImgX = board_pos[0]+(horiz_tiles+coordX)*tile_size
			posImgY = board_pos[1]+tile_size*coordY
			coordSelect = (posImgX,posImgY)
			if tool == 'Tile' or tool == 'Marble': 
				posImgX+=3
				posImgY+=3
			img=coord_img[1]
			# Selector
			if (self.tool=='Tile'==tool and self.toolPath==0) or \
				(self.tool=='Tile' and tool=='Path' and self.toolPath!=0) or \
				(tool == self.tool and self.tool!='Tile'):
				screen.blit(selectedSurface,coordSelect)
				
			# Draw tool
			screen.blit(img,(posImgX,posImgY))
			if tool == 'Buffer': screen.blit(Buffer.bottom,(posImgX,posImgY))
		updateZone = Rect(770, 45, 190, 650)
		dirty_rects.append(updateZone)
		self.tools_drawn = 1
		
	def draw_selectedOptions(self, dirty_rects):
	
		if self.selectedOptions_drawn == 1: return
		bg = pygame.Surface((150,170))
		bg.fill((200, 200, 200))
		screen.blit(bg, (600,625))
		
		screen.blit( Marble.images[self.toolColor], (607,630))		
		screen.blit( Tile.plain_tiles[self.toolPath], (653,626))
		screen.blit( Director.images[self.toolSwitchDirector], (630,702))
		screen.blit( Switch.directionsImages[self.toolSwitchDirection], (680,702))
		screen.blit( Replicator.selectedImg[self.toolReplicatorFactor], (603,665))
		screen.blit( Buffer.selectedImg[self.toolBuffer], (603,715))
		updateZone = Rect(600, 625, 150, 170)
		dirty_rects.append(updateZone)
		self.selectedOptions_drawn = 1
	
	def draw_levelConfig(self, dirty_rects):
	
		if self.levelConfig_drawn == 1: return

		bg = pygame.Surface((screen_width,45))
		bg.fill((200, 200, 200))
		
		if self.level == -1: board_name = "New level - " + self.name
		else: board_name = repr(self.level+1) + " - " + self.name
		if self.level != game.level and levelset != 'Custom':
			levelsetDisplay = levelset
			if levelset == 'all-boards': levelsetDisplay = 'Default'
			board_name += " (from "+levelsetDisplay+" / level "+repr(game.level+1)+")"
		textName = info_font.render( board_name, 1, (0,0,0))
		rect = textName.get_rect()
		rect.top = 10
		rect.left = timer_width
		bg.blit( textName, rect)
		
		board_timer = "Board timer: "+str(self.boardTimer)+ "s"
		textBoardTimer = info_font.render( board_timer, 1, (0,0,0))
		rect = textBoardTimer.get_rect()
		rect.top = 30
		rect.left = timer_width
		bg.blit( textBoardTimer, rect)
		
		launch_timer = "Launch timer (passes): "+str(self.launchTimer)
		textLaunchTimer = info_font.render( launch_timer, 1, (0,0,0))
		rect = textLaunchTimer.get_rect()
		rect.top = 30
		rect.left = timer_width + 140
		bg.blit( textLaunchTimer, rect)
		
		maxMarbles = "Max marbles: "+str(self.live_marbles_limit)
		textMaxMarbles = info_font.render( maxMarbles, 1, (0,0,0))
		rect = textMaxMarbles.get_rect()
		rect.top = 30
		rect.left = timer_width + 320
		bg.blit( textMaxMarbles, rect)
		
		levelColors = "Level colors"
		textlevelColors = info_font.render( levelColors, 1, (0,0,0))
		rect = textlevelColors.get_rect()
		rect.top = 2
		rect.left = timer_width + 545
		bg.blit( textlevelColors, rect)
		i=timer_width + 450
		for color in range(9):
			if color in self.colors:
				bg.blit(Marble.images[color],(i,17))
			else:
				bg.blit(Marble.images[color],(i,17))
				bg.blit(Marble.crossImg,(i,17))
			i+=30
		
		author = "Author: "+self.author
		textAuthor = info_font.render( author, 1, (0,0,0))
		rect = textAuthor.get_rect()
		rect.top = 10
		rect.right = screen_width - timer_width
		bg.blit( textAuthor, rect)
		
		self.screen.set_clip()
		self.screen.blit( bg, (0,0))
		
		updateZone = Rect(0, 0, 1000, 45)
		dirty_rects.append(updateZone)
		self.levelConfig_drawn = 1
		
	def draw_back(self, dirty_rects):
		for row in self.tiles:
			for tile in row:
				if tile.draw_back( self.background):
					self.screen.set_clip( tile.rect)
					self.screen.blit( self.background, (0,0))
					self.screen.set_clip()
					dirty_rects.append( tile.rect)

	def draw_fore(self, dirty_rects):
		for row in self.tiles:
			for tile in row:
				if tile.draw_fore(self.screen):
					dirty_rects.append( tile.rect)

	def update(self):
	
		# Create the list of dirty rectangles
		dirty_rects = []
		
		# Draw the tools
		self.draw_tools( dirty_rects)
		# Draw selected tools options
		self.draw_selectedOptions( dirty_rects)
		# Draw level configuration
		self.draw_levelConfig( dirty_rects)

		# Draw the background
		self.draw_back( dirty_rects)

		# Draw all of the marbles
		for marble in self.marbles:
			marble.draw( self.screen)
			dirty_rects.append( marble.rect)
			textColor = (0,0,0)
			if marble.color == 0 or marble.color == 2: textColor = (255,255,255)
			dirSymbol = directionsSymbols[marble.direction]
			textDirection= info_font.render( dirSymbol, 1, textColor)
			txtX = marble.rect.center[0] - 3
			txtY = marble.rect.center[1] - 8
			if colorblind: txtY += 9
			self.screen.blit( textDirection, (txtX,txtY))

		# Draw the foreground
		self.draw_fore( dirty_rects)

		# Flip the display
		pygame.display.update( dirty_rects)

	def set_tile(self, x, y, tile, emptyTile=False):
		
		self.background = pygame.Surface(screen.get_size()).convert()
		self.background.blit( Tile.image, \
			(timer_width+tile_size*x,info_height + marble_size + tile_size*y))
		
		# set tile		
		self.tiles[y][x] = tile
		tile.rect.left = self.pos[0] + tile_size * x
		tile.rect.top = self.pos[1] + tile_size * y

		tile.x = x
		tile.y = y
		
		if emptyTile == True: tile.empty=1

		# If it's a trigger, keep track of it
		if isinstance( tile, Trigger):
			self.trigger = tile

		# If it's a stoplight, keep track of it
		if isinstance( tile, Stoplight):
			self.stoplight = tile
			
	def setLevelConfig(self,title,attr):
		chooseCfg = popup(title+":\n\n\nPress enter", (300, 180))
		cfg = get_name(self.screen, popup_font,((screen_width-250)/2,310,250, \
			popup_font.get_height()), (255,255,255), (0,0,0))
		# Check if int for board timer, launch timer and max marbles
		if(attr == 'boardTimer' or attr == 'launchTimer' \
			or attr == 'live_marbles_limit') and cfg.isdigit() == False:
			popdown(chooseCfg)
			play_sound(filter_admit)
			self.warning("WARNING\nMust be a number")
			return
		if cfg:	setattr(self,attr,cfg)
		popdown(chooseCfg)
		self.levelConfig_drawn = 0
		
	def setStoplightColor(self,pos):
		temp = list(self.StoplightColors)
		temp[pos] = self.toolColor
		self.StoplightColors = tuple(temp)
		if pos == 0: coord = (484,629)
		elif pos == 1: coord = (484,670)
		elif pos == 2: coord = (484,710)
		screen.blit( Marble.images[self.toolColor], coord)
		updateZone = Rect(485, 630, 40, 110)
		pygame.display.update(updateZone)


	def click(self, pos):

		play_sound(menu_select)

		# Determine where the pointer is
		tile_x = (pos[0] - self.pos[0]) / tile_size
		tile_y = (pos[1] - self.pos[1]) / tile_size
		tile_xr = pos[0] - self.pos[0] - tile_x * tile_size
		tile_yr = pos[1] - self.pos[1] - tile_y * tile_size
		
		# Click on a tile
		if tile_x >= 0 and tile_x < horiz_tiles and \
			tile_y >= 0 and tile_y < vert_tiles:
			tile = self.tiles[tile_y][tile_x]

			# Trigger / stoplights special cases
			if isinstance( tile, Stoplight): self.stoplight = None
			if isinstance( tile, Trigger): self.trigger = None
			if self.tool == 'Stoplight':
				if (self.stoplight is not None): 
					play_sound(filter_admit)
					self.warning("WARNING\nOnly one stoplight per level")
					return
			elif self.tool == 'Trigger':
				if (self.trigger is not None):
					play_sound(filter_admit)
					self.warning("WARNING\nOnly one trigger per level")
					return
			
			# Remove potential marble
			if self.tool != 'Marble':
				for marble in self.marbles:
					if marble.tilePos == (tile_x,tile_y): self.marbles.remove(marble)
			
			# Teleporter special cases
			if isinstance( tile, Teleporter):
				# Don't put a teleporter on another one
				if self.tool == 'Teleporter':
					play_sound(filter_admit)
					self.warning("WARNING\nCan't add teleporter on another one\nDelete it first")
					return
				# Remove teleporter(s) in list
				else:
					teleportersCoords = list((k) for k, v \
						in list(self.toolTeleporters.items()) if v == tile.label)
					for coord in teleportersCoords:
						self.toolTeleporters.pop(coord, None)
						# Remove other teleporter tile
						if coord != (tile_x,tile_y):			
							otherTeleporter = Tile()							
							self.set_tile(coord[0],coord[1],otherTeleporter, True)
			
			# Create new tile
			constructor = globals()[self.tool]	
			
			if self.tool == 'Painter' or self.tool == 'Filter': 
				tile = constructor(self.toolPath,self.toolColor)
			elif self.tool == 'Replicator': 
				tile = constructor(self.toolPath,self.toolReplicatorFactor)
			elif self.tool == 'Director': 
				tile = constructor(self.toolPath,self.toolSwitchDirector)
			elif self.tool == 'Switch':
				if self.toolSwitchDirector == self.toolSwitchDirection:
					play_sound(filter_admit)
					self.warning("WARNING\nSwitcher's 1st and 2nd direction can't be identical")
					return
				tile = constructor(self.toolPath,self.toolSwitchDirector,self.toolSwitchDirection)
			elif self.tool == 'Trigger': tile = constructor(self.colors)
			elif self.tool == 'Stoplight': tile = constructor(self.StoplightColors)
			elif self.tool == 'Buffer' and self.toolBuffer == 1: 
				tile = constructor(self.toolPath,self.toolColor)
			# Teleporter special case
			elif self.tool == 'Teleporter':
				tile = constructor(self.toolPath)
				tile.label = self.toolTeleporterLabel
				
				teleportersNum = len(self.toolTeleporters)
				# Create new teleporter
				if (teleportersNum%2 == 0):
					self.toolTeleporters[(tile_x,tile_y)] = self.toolTeleporterLabel
				# Create 2nd teleporter
				else:
					self.toolTeleporters[(tile_x,tile_y)] = self.toolTeleporterLabel
					self.toolTeleporterLabel += 1
			elif self.tool == 'Marble':
				if self.toolPath == 0: 
					play_sound(filter_admit)
					self.warning("WARNING\nChoose a path first")
					return
				tile = Tile(self.toolPath)
				marbleCoord = tile_x*tile_size+tile_size-10,tile_y*tile_size+tile_size+2
				self.marbles.append(Marble(self.toolColor,marbleCoord,self.toolSwitchDirection,(tile_x,tile_y)))
			else: tile = constructor(self.toolPath)
				
			self.set_tile(tile_x,tile_y,tile)		
		
		# click on a tool		
		elif horiz_tiles <= tile_x < horiz_tiles+2 and 0 <= tile_y < vert_tiles+1:
			self.tool = self.toolsList[(tile_x,tile_y)]
			# empty tile: set path to 0
			if tile_x == 8 and tile_y == 6: self.toolPath = 0
			
			self.tools_drawn = 0
		
		# click on level global option
		elif pos[1]<45:
			if pos[1]<25 and pos[0] < 450: self.setLevelConfig('Level name','name')
			elif pos[1]<25 and pos[0] > 775: self.setLevelConfig('Author','author')
			elif pos[1]>25 and 150 > pos[0] > timer_width: 
				self.setLevelConfig('Board timer','boardTimer')
			elif pos[1]>25 and 330 > pos[0] > timer_width+140: 
				self.setLevelConfig('Launch timer','launchTimer')
			elif pos[1]>25 and 460 > pos[0] > timer_width+320: 
				self.setLevelConfig('Max marbles','live_marbles_limit')
			# Level colors
			elif pos[1]>25 and timer_width+450 < pos[0] < timer_width+450+30*9:
				tempColors=list(self.colors)
				for i in range(9):
					i=30*i
					if timer_width+450+30+i > pos[0] > timer_width+450+i:
						clickedColor=i/30
						if clickedColor in tempColors: 
							tempColors.remove(clickedColor)
						else: tempColors.append(clickedColor)
				self.colors = tuple(tempColors)
				
				self.levelConfig_drawn = 0
				
		# click on an option
		else:		
			# Determine which option the pointer is in
			option_x = (pos[0] - self.pos[0]) / 44
			option_y = (pos[1] - tile_size*6-info_height*2-30) / 40
			optionTile = (option_x,option_y)
			
			# colors
			if 0 <= optionTile[0] <= 1:
				self.toolColor = self.colorOptionsPos[optionTile]
			
			# paths
			elif optionTile[0] <= 5:
				self.toolPath = self.pathOptionsPos[optionTile]

			# Replicator factor
			elif optionTile == (6,0): self.toolReplicatorFactor = 2
			elif optionTile == (6,1): self.toolReplicatorFactor = 4

			# Director / switch
			elif optionTile == (7,0): self.toolSwitchDirector = 0
			elif optionTile == (7,1): self.toolSwitchDirector = 3
			elif optionTile == (7,2): self.toolSwitchDirector = 2
			elif optionTile == (7,3): self.toolSwitchDirector = 1
			
			# 2nd switch direction
			elif optionTile == (8,0): self.toolSwitchDirection = 0
			elif optionTile == (8,1): self.toolSwitchDirection = 3
			elif optionTile == (8,2): self.toolSwitchDirection = 2
			elif optionTile == (8,3): self.toolSwitchDirection = 1
			
			# Buffer type
			elif optionTile == (9,0): self.toolBuffer = 1
			elif optionTile == (9,1): self.toolBuffer = 0
			
			# Stoplight colors
			elif optionTile == (10,0): self.setStoplightColor(0)
			elif optionTile == (10,1): self.setStoplightColor(1)
			elif optionTile == (10,2): self.setStoplightColor(2)
			
			# Save
			elif 910 < pos[0] < 943 and 745 < pos[1] < 785: self.save()
			
			# Exit
			elif 950 < pos[0] < 986 and 750 < pos[1] < 785:
				event = pygame.event.Event(KEYDOWN,key=K_ESCAPE)
				pygame.event.post(event)
			
			# Empty area
			else: return
			
			self.selectedOptions_drawn = 0

	def save(self):
			
		# Check teleporters
		teleportersNum = len(self.toolTeleporters)
		if (teleportersNum%2 != 0):
			play_sound(filter_admit)
			self.warning("WARNING\nTeleporters are not in pairs")
			return
			
		# Check stoplight
		stoplightColors = ''
		if self.stoplight is not None:
			for StoplightColor in self.StoplightColors:
				# Check if color in level colors
				if StoplightColor not in self.colors:
					play_sound(filter_admit)
					msg = "Some stoplight colors are not available in this level\n"
					msg += "Make sure you have painters or marbles on board for this color"
					self.warning("WARNING\n"+msg)
			stoplightColors = ','.join(map(str,self.StoplightColors))
		
		# Prepare marbles
		marblesToSave = {}
		for marble in self.marbles: 
			marblesToSave[marble.tilePos] = (marble.color,marble.direction)
		
		# Open/read file
		if levelset!='Custom' and self.savedFromDefaultSet==False:
			customLevelsNum = countLevels(True)
			self.level = customLevelsNum
			self.savedFromDefaultSet=True
			self.levelConfig_drawn = 0

		# All modified levels go in custom-set
		filename = os.path.join('user_circuits', 'Custom')
		f = open(filename,'r+')
		lines = f.readlines()
		if self.level == -1: edit=False
		else:
			edit=True
			f.seek(0)
			f.truncate()
			l=0
			# re-write levels before
			for line in lines:
				if l==16*self.level: break
				f.write(line)
				l+=1
        
		# Write level header
		levelColors = ','.join(map(str,self.colors))
		header = "name="+self.name+"\nauthor="+self.author \
			+"\nboardtimer="+str(self.boardTimer)+"\nlaunchtimer="+str(self.launchTimer) \
			+"\nmaxmarbles="+str(self.live_marbles_limit)+"\ncolors="+levelColors \
			+"\nstoplight="+stoplightColors
		header += "\n+---+---+---+---+---+---+---+---+\n"
		f.write(header)
		
		# Write level tiles
		for y in range(6):
			for x in range(8):
				tile = self.tiles[y][x]
				tileType = tile.__class__.__name__
				path = tile.paths
				if path > 9: path = chr(path+ ord('a') - 10)
				f.write('|')
				if tileType == 'Director':
					f.write(str(directionsSymbols[tile.direction])+str(path)+' ')
				elif tileType == 'Switch': 
					f.write(str(directionsSymbols[tile.curdir])+str(path)+ \
						str(directionsSymbols[tile.otherdir]))
				elif tileType == 'Filter' or tileType == 'Painter':
					f.write(tilesSymbols[tileType]+str(path)+str(tile.color))
				elif tileType == 'Trigger' or tileType == 'Stoplight':
					f.write(tilesSymbols[tileType]+'  ')
				elif tileType == 'Tile':
					# Empty tile
					if path==0: f.write('   ')
					# Path with marble
					elif (x,y) in list(marblesToSave.keys()): 
						f.write(str(marblesToSave[(x,y)][0])+str(path)+ \
							str(directionsSymbols[marblesToSave[(x,y)][1]]))
					# Path
					else: f.write(' '+str(path)+' ')
				elif tileType == 'Buffer':
					f.write(tilesSymbols[tileType]+str(path))
					if tile.marble == -1: f.write(' ')
					else: f.write(str(tile.marble))
				elif tileType == 'Teleporter':
					label = tile.label
					if isinstance(label,(int)) and label > 9: 
						label = chr(label+ ord('a') - 10)
					f.write(tilesSymbols[tileType]+str(path)+str(label))
				elif tileType == 'Replicator':
					f.write(tilesSymbols[tileType]+str(path)+str(tile.count))
				else:
					f.write(tilesSymbols[tileType]+str(path)+" ")
				x+=1
				if x==8:f.write('|')
			f.write("\n")
			y+=1

		footer = "+---+---+---+---+---+---+---+---+\n\n"
		f.write(footer)
		
		if edit:
			# Existing level: re-write levels after
			for l in range(16*self.level+16,len(lines)):
				f.write(lines[l])
		else:
			# New level: set level number / update display
			newLevelNum = len(lines)/16
			self.level = newLevelNum
			if levelset == 'Custom': game.level = newLevelNum
			game.numlevels += 1
			self.levelConfig_drawn = 0
			
		f.close()
		play_sound(change_color)
		self.warning("SUCCESS\nLevel saved in custom set")
		
	def _load(self, circuit, level):
		# Create new level
		if level < 0:
			j = 0
			while j < vert_tiles:
				for i in range(horiz_tiles):
					tile = Tile()
					self.set_tile( i, j, tile)
				j += 1
		# Edit existing level
		else:
			fullname = os.path.join(circuit[0], circuit[1])
			f = open( fullname)

			# Skip the previous levels
			j = 0
			while j < vert_tiles * level:
				line = f.readline()
				if line == '':
					f.close()
					return 0
				if line[0] == '|': j += 1

			teleporters = []
			teleporter_names = []
			self.toolTeleporters = {}
			stoplight = default_stoplight

			j = 0
			while j < vert_tiles:
				line = f.readline()

				if line[0] != '|':
					if line[0:5] == 'name=':
						self.name = line[5:-1]
					elif line[0:7] == 'author=':
						self.author = line[7:-1]
					elif line[0:11] == 'maxmarbles=':
						self.live_marbles_limit = int(line[11:-1])
					elif line[0:12] == 'launchtimer=':
						self.launchTimer = int(line[12:-1])
					elif line[0:11] == 'boardtimer=':
						self.boardTimer = int(line[11:-1])
					elif line[0:7] == 'colors=':
						self.colors = []
						for c in line[7:-1]:
							if c >= '0' and c <= '8':
								self.colors.append(int(c))
					elif line[0:10] == 'stoplight=':
						stoplight = []
						for c in line[10:-1]:
							if c >= '0' and c <= '7':
								stoplight.append(int(c))
							self.StoplightColors = tuple(stoplight)

					continue

				for i in range(horiz_tiles):
					type = line[i*4+1]
					paths = line[i*4+2]
					if paths == ' ': pathsint = 0
					elif paths >= 'a': pathsint = ord(paths)-ord('a')+10
					elif paths >= '0' and paths <= '9': pathsint = int(paths)
					else: pathsint = int(paths)
					color = line[i*4+3]
					if color == ' ': colorint = 0
					elif color >= 'a': colorint = ord(color)-ord('a')+10
					elif color >= '0' and color <= '9': colorint = int(color)
					else: colorint = 0

					if type == 'O': tile = Wheel( pathsint)
					elif type == '%': tile = Trigger(self.colors)
					elif type == '!': tile = Stoplight(stoplight)
					elif type == '&': tile = Painter(pathsint, colorint)
					elif type == '#': tile = Filter(pathsint, colorint)
					elif type == '@':
						if color == ' ': tile = Buffer(pathsint)
						else: tile = Buffer(pathsint, colorint)
					elif type == ' ' or \
						(type >= '0' and type <= '8'): tile = Tile(pathsint)
					elif type == 'X': tile = Shredder(pathsint)
					elif type == '*': tile = Replicator(pathsint, colorint)
					elif type == '^':
						if color == ' ': tile = Director(pathsint, 0)
						elif color == '>': tile = Switch(pathsint, 0, 1)
						elif color == 'v': tile = Switch(pathsint, 0, 2)
						elif color == '<': tile = Switch(pathsint, 0, 3)
					elif type == '>':
						if color == ' ': tile = Director(pathsint, 1)
						elif color == '^': tile = Switch(pathsint, 1, 0)
						elif color == 'v': tile = Switch(pathsint, 1, 2)
						elif color == '<': tile = Switch(pathsint, 1, 3)
					elif type == 'v':
						if color == ' ': tile = Director(pathsint, 2)
						elif color == '^': tile = Switch(pathsint, 2, 0)
						elif color == '>': tile = Switch(pathsint, 2, 1)
						elif color == '<': tile = Switch(pathsint, 2, 3)
					elif type == '<':
						if color == ' ': tile = Director(pathsint, 3)
						elif color == '^': tile = Switch(pathsint, 3, 0)
						elif color == '>': tile = Switch(pathsint, 3, 1)
						elif color == 'v': tile = Switch(pathsint, 3, 2)
					elif type == '=': 
						if color in teleporter_names:
							other = teleporters[teleporter_names.index(color)]
							tile = Teleporter( pathsint, other)
						else:
							tile = Teleporter( pathsint)
							teleporters.append( tile)
							teleporter_names.append( color)
						tile.label = color
						self.toolTeleporters[(i,j)] = color
						self.toolTeleporterLabel = len(teleporters)+1

					self.set_tile( i, j, tile)

					if type >= '0' and type <= '8':
						if color == '^': direction = 0
						elif color == '>': direction = 1
						elif color == 'v': direction = 2
						else: direction = 3
						self.marbles.append(
							Marble(int(type),tile.rect.center,direction,(i,j)))
				j += 1
			f.close()
		return 1
	
	def warning(self,msg):
		msg += "\n(click to close)"
		self.warningPopup.append(popup(msg))

	# Return values for this function:
	# -4: User closed the application window
	# -3: User aborted the level
	#  2: User requested a skip to the next level
	#  3: User requested a skip to the previous level
	def play_level( self):
		global music_volume
		
		# Perform the first render
		self.update()

		# Do the first update
		pygame.display.update()

		# Game Loop
		while True:
			# Wait for the next frame

			my_tick( frames_per_sec)

			# Handle Input Events
			for event in pygame.event.get():
				if event.type == QUIT:
					return -4
				elif event.type == KEYDOWN:
				
					# Ask quit confirmation
					if event.key == K_ESCAPE or event.key == K_q :
						self.quitPopup = self.quitPopup ^ 1
						if self.quitPopup:
							if screenshot:
								quit_popup = None
							else:
								quit_popup = popup('Exit editor?\nEnter to confirm')
						else:
							popdown(quit_popup)
					# Quit		
					elif event.key == K_RETURN and self.quitPopup:
						popdown(quit_popup)
						return -3
					# Change level
					elif event.key == ord('n'): return 2
					elif event.key == ord('b'): return 3
					# Tools hotkeys
					elif event.key == ord('w'): self.tool = 'Wheel'
					elif event.key == ord('p'): self.tool = 'Tile'
					
					elif event.key == K_F2:
						toggle_fullscreen()
					elif event.key == K_F3:
						toggle_music()
					elif event.key == K_F4:
						toggle_sound()
					elif event.key == K_PLUS or event.key == 270:
						if music_volume < 1: 
							music_volume +=0.1
							pygame.mixer.music.set_volume(music_volume)
					elif event.key == K_MINUS or event.key == 269:
						if music_volume > 0: 
							music_volume -=0.1
							pygame.mixer.music.set_volume(music_volume)

				elif event.type == MOUSEBUTTONDOWN:
					if self.quitPopup:
						self.quitPopup = 0
						popdown( quit_popup)
					elif self.warningPopup:
						curPopup = self.warningPopup[-1]
						popdown(curPopup)
						del self.warningPopup[-1]
					else: self.click( pygame.mouse.get_pos())

			if not self.quitPopup and not self.warningPopup: self.update()
			

def wait_one_sec():
	time.sleep(1)
	pygame.event.get() # Clear the event queue

def popup( text, minsize=None):
	maxwidth = 0
	objs = []
	while text != "":
		if '\n' in text:
			newline = text.index('\n')
			line = text[:newline]
			text = text[newline+1:]
		else:
			line = text
			text = ""

		obj = popup_font.render( line, 1, (0, 0, 0))
		maxwidth = max( maxwidth, obj.get_rect().width)
		objs.append( obj)

	linespacing = popup_font.get_ascent() - \
		popup_font.get_descent() + popup_font.get_linesize()
	# Work around an apparent pygame bug on Windows
	linespacing = min( linespacing, int(1.2 * popup_font.get_height()))

	# Leave a bit more room
	linespacing = int(linespacing * 1.3)

	window_width = maxwidth + 40
	window_height = popup_font.get_height()+linespacing*(len(objs)-1)+40
	if minsize is not None:
		window_width = max( window_width, minsize[0])
		window_height = max( window_height, minsize[1])

	window = pygame.Surface((window_width, window_height))
	winrect = window.get_rect()
	window.fill((0, 0, 0))
	window.fill((250, 250, 250), winrect.inflate(-2,-2))

	y = 20
	for obj in objs:
		textpos = obj.get_rect()
		textpos.top = y
		textpos.centerx = winrect.centerx
		window.blit( obj, textpos)
		y += linespacing

	winrect.center = screen.get_rect().center
	winrect.top -= 40

	backbuf = pygame.Surface(winrect.size).convert()
	backbuf.blit( screen, (0,0), winrect)

	screen.blit( window, winrect)
	pygame.display.update()

	return (backbuf, winrect)

def popdown( popup_rc):
	if popup_rc is not None:
		screen.blit( popup_rc[0], popup_rc[1])
		pygame.display.update( popup_rc[1])

class Game:
	def __init__(self, screen, circuit, level = 0):
	
		global levelset
	
		self.screen = screen
		self.circuit = circuit
		self.numlevels = countLevels()

		self.level = level
		self.score = 0

		self.gamestart = time.time()

	# Return values for this function:
	# -1: User closed the application window
	#  0: The level was aborted
	def play(self):
		# Draw the loading screen
		backdrop = load_image('backdrop.jpg', None,
			(screen_width, screen_height))
		screen.blit( backdrop, (0,0))
		
		pygame.display.update()

		popup("Please wait...\n", (150, 50))

		while 1:
			# Play a level
			board = Board( self, board_pos)
			rc = board.play_level()

			# Close the window
			if rc == -4: return -1
			
			# Load next level ('n')
			if rc == 2:
				if self.level+1 < self.numlevels:
					self.level += 1
				else:
					self.level = -1
				continue
				
			# Load previous level ('b')
			if rc == 3:
				if self.level > -1: self.level -= 1
				continue

			# Exit level > back to menu
			if rc == -3: return 0
			
def translate_key( key, shift_state): # TODO what if keyboard layout is not EN?
	if shift_state:
		if key >= ord('a') and key <= ord('z'): key += ord('A') - ord('a')
		elif key == ord('1'): key = ord('!')
		elif key == ord('2'): key = ord('@')
		elif key == ord('3'): key = ord('#')
		elif key == ord('4'): key = ord('$')
		elif key == ord('5'): key = ord('%')
		elif key == ord('6'): key = ord('^')
		elif key == ord('7'): key = ord('&')
		elif key == ord('8'): key = ord('*')
		elif key == ord('9'): key = ord('(')
		elif key == ord('0'): key = ord(')')
		elif key == ord('`'): key = ord('~')
		elif key == ord("'"): key = ord('"')
		elif key == ord(";"): key = ord(':')
		elif key == ord("\\"): key = ord('|')
		elif key == ord("["): key = ord('{')
		elif key == ord("]"): key = ord('}')
		elif key == ord(","): key = ord('<')
		elif key == ord("."): key = ord('>')
		elif key == ord("/"): key = ord('?')
		elif key == ord("-"): key = ord('_')
		elif key == ord("="): key = ord('+')
	return key

def get_name( screen, font, cursor_box, backcol, forecol):
	cursor_width = cursor_box[3] / 3
	cursor_pos = [cursor_box[0], cursor_box[1], cursor_width, cursor_box[3]]
	name = ""

	inner_box = pygame.Rect(cursor_box)
	cursor_box = inner_box.inflate( 2, 2)
	outer_box = cursor_box.inflate( 2, 2)

	enter_pressed = 0
	while not enter_pressed:
		screen.fill( forecol, outer_box)
		screen.fill( backcol, cursor_box)
		cursor_pos[0] = inner_box.left
		if name != "":
			obj = font.render( name, 1, forecol)
			screen.blit( obj, inner_box)
			cursor_pos[0] += obj.get_width()
		screen.fill( forecol, cursor_pos)
		pygame.display.update( (outer_box,))

		# Keep track of the shift keys
		shift_state = pygame.key.get_mods() & KMOD_SHIFT

		pygame.time.wait(20)
		for event in pygame.event.get():
			if event.type == QUIT:
				return None
			elif event.type == KEYUP:
				if event.key == K_LSHIFT:
					shift_state &= ~KMOD_LSHIFT
				elif event.key == K_RSHIFT:
					shift_state &= ~KMOD_RSHIFT
			elif event.type == KEYDOWN:
				if event.key == K_LSHIFT:
					shift_state |= KMOD_LSHIFT
				elif event.key == K_RSHIFT:
					shift_state |= KMOD_RSHIFT
				elif event.key == K_RETURN:
					enter_pressed = 1
					break
				elif event.key == K_ESCAPE:
					return None
				elif event.key == K_F2:
					toggle_fullscreen()
				elif event.key == K_F3:
					toggle_music()
				elif event.key == K_F4:
					toggle_sound()
				elif event.key == K_BACKSPACE:
					name = name[:-1]
				elif event.key >= 32 and event.key <= 127:
					key = translate_key( event.key, shift_state)
					name = name + chr(key)
				# Add numpad numbers for non EN keyb layout
				elif 256 <= event.key <= 265:
					key = event.str
					name = name + key
			elif event.type == pygame.MOUSEBUTTONDOWN:
				return None
				
	return name

class IntroScreen:

	menu = ("Edit level", "Levelset:", "Fullscreen:", "Music:",
		"Sound Effects:", "Play", "Quit Game")
	start_level = 0
	start_levelset = 0
	menu_width = 370
	menu_pos = ((800 - menu_width)/2, 230)
	menu_font_height = 32
	menu_color = (255,255,255)
	menu_cursor_color = (60,60,60)
	menu_cursor_leftright_margin = 2
	menu_cursor_bottom_margin = -2
	menu_cursor_top_margin = 0
	menu_option_left = 200
	menu_rect = (menu_pos[0]-menu_cursor_leftright_margin,
		 menu_pos[1]-menu_cursor_top_margin,
		 menu_width + 2 * menu_cursor_leftright_margin,
		 menu_font_height * len(menu) +
			menu_cursor_top_margin + menu_cursor_bottom_margin)

	scroller_font_height = 28
	scroller_rect = (10,750,980,scroller_font_height)
	scroller_text = \
		"   Copyright \A9 2003  John-Paul Gignac (game).   "+ \
		"   Editor by Nina Ripoll / http://www.maze-photo.com / 2016.   "+ \
		"   Editor soundtrack by The Gaping Fools.   "+ \
		"   Game soundtrack by Matthias Le Bidan.   "+ \
		"   Board designs contributed by Mike Brenneman and Kim Gignac.   "+ \
		"   Website: http://pathological.sourceforge.net/   "+ \
		"   Logo by Carrie Bloomfield.   "+ \
		"   Other graphics based on artwork by Mike Brenneman.   "+ \
		"   This program is free software; you can redistribute it and/or "+ \
		"modify it under the terms of the GNU General Public License.  "+ \
		"See the LICENSE file for details.   "

	scroller_color = (60,60,60)
	scroller_speed = 2

	def __init__(self, screen):
		self.screen = screen
		self.curpage = 0

		self.scroller_image = self.scroller_font.render(
			self.scroller_text, 1, self.scroller_color)

		self.menu_cursor = 0

	def draw_background(self):
		self.screen.blit( self.background, (0,0))

	def undraw_menu(self):
		self.screen.set_clip( self.menu_rect)
		self.draw_background()
		self.screen.set_clip()
		self.dirty_rects.append( self.menu_rect)

	def draw_menu(self):

		self.undraw_menu()

		self.screen.fill( self.menu_cursor_color,
			(self.menu_pos[0]-self.menu_cursor_leftright_margin,
			 self.menu_pos[1]-self.menu_cursor_top_margin +
			 self.menu_cursor * self.menu_font_height,
			 self.menu_width + 2 * self.menu_cursor_leftright_margin,
			 self.menu_font_height + self.menu_cursor_top_margin +
			 self.menu_cursor_bottom_margin))

		y = self.menu_pos[1]
		for i in self.menu:
			menu_option = self.menu_font.render(i, 1, self.menu_color)
			self.screen.blit( menu_option, (self.menu_pos[0], y))
			y += self.menu_font_height
		menuLevelName = IntroScreen.start_level
		if menuLevelName == 0: menuLevelName = "new"
		levelt = self.menu_font.render("(Lvl. %s)" %
					       menuLevelName,
					       1, self.menu_color)
		lt_r = levelt.get_rect()
		lt_r.right = self.menu_pos[0] + self.menu_option_left + 40
		lt_r.top = self.menu_pos[1]
		self.screen.blit(levelt, lt_r)
		
		levelSetText = customsSetsFiles[IntroScreen.start_levelset]
		if len(levelSetText) > 16: levelSetText = levelSetText[0:16]+'.'
		levelSetText = self.menu_font.render( levelSetText, 1, self.menu_color)
		self.screen.blit( levelSetText,
			(self.menu_pos[0]+self.menu_option_left,
			self.menu_pos[1]+self.menu_font_height))

		if fullscreen: offon = 'On'
		else: offon = 'Off'
		offon = self.menu_font.render( offon, 1, self.menu_color)
		self.screen.blit( offon,
			(self.menu_pos[0]+self.menu_option_left,
			self.menu_pos[1]+self.menu_font_height * 2))

		if music_on: offon = 'On'
		else: offon = 'Off'
		offon = self.menu_font.render( offon, 1, self.menu_color)
		self.screen.blit( offon,
			(self.menu_pos[0]+self.menu_option_left,
			self.menu_pos[1]+self.menu_font_height * 3))

		if sound_on: offon = 'On'
		else: offon = 'Off'
		offon = self.menu_font.render( offon, 1, self.menu_color)
		self.screen.blit( offon,
			(self.menu_pos[0]+self.menu_option_left,
			self.menu_pos[1]+self.menu_font_height * 4))

		self.dirty_rects.append( self.menu_rect)

	def draw_scroller(self):
		self.screen.set_clip( self.scroller_rect)
		self.draw_background()
		self.screen.blit( self.scroller_image,
			(self.scroller_rect[0] - self.scroller_pos,
			self.scroller_rect[1]))
		self.screen.set_clip()
		self.dirty_rects.append( self.scroller_rect)

	def draw(self):
		self.dirty_rects = []
		self.draw_background()
		self.draw_menu()
		self.draw_scroller()
		pygame.display.update()

	def go_to_main_menu(self):
		# Return to the main menu
		play_sound( menu_select)
		self.undraw_menu()
		self.curpage = 0
		self.draw_menu()

	def inc_level(self):
		levelNumber = countLevels()
		if IntroScreen.start_level < levelNumber:
			IntroScreen.start_level += 1
		else: IntroScreen.start_level = 0

	def dec_level(self):
		if IntroScreen.start_level > 0:
			IntroScreen.start_level -= 1
			
	def inc_levelset(self):
		if IntroScreen.start_levelset < len(customsSetsFiles)-1:
			IntroScreen.start_levelset += 1
		else: IntroScreen.start_levelset = 0
	
	def do(self):
		self.scroller_pos = -self.scroller_rect[2]

		self.draw()

		start_music("Gaping_Fools_I_Need_a_Haircut.ogg", intro_music_volume)

		while 1:
			# Wait for the next frame
			my_tick( frames_per_sec)

			self.dirty_rects = []
			self.draw_scroller()

			# Advance the scroller
			self.scroller_pos += self.scroller_speed
			if self.scroller_pos >= self.scroller_image.get_rect().width:
				self.scroller_pos = -self.scroller_rect[2]

			pygame.time.wait(20)
			for event in pygame.event.get():
				if event.type == QUIT:
					return -4
				elif event.type == KEYDOWN:
					if event.key == K_F2:
						play_sound( menu_select)
						if not toggle_fullscreen(): return -3
						self.draw_menu()
					elif event.key == K_F3:
						play_sound( menu_select)
						toggle_music()
						self.draw_menu()
					elif event.key == K_F4:
						toggle_sound()
						play_sound( menu_select)
						self.draw_menu()
					elif self.curpage == 1:
						self.go_to_main_menu()
					elif event.key == K_ESCAPE:
						return -1
					elif event.key == K_DOWN:
						self.menu_cursor += 1
						play_sound( menu_scroll)
						if self.menu_cursor == len(self.menu):
							self.menu_cursor = 0
						self.draw_menu()
					elif event.key == K_UP:
						self.menu_cursor -= 1
						play_sound( menu_scroll)
						if self.menu_cursor < 0:
							self.menu_cursor = len(self.menu) - 1
						self.draw_menu()
					elif event.key == K_SPACE or event.key == K_RETURN:
						rc = self.menu_select( self.menu_cursor)
						if rc: return rc
					elif event.key == K_LEFT:
						if self.menu_cursor == 0:
							self.dec_level()
							self.draw_menu()
					elif event.key == K_RIGHT:
						if self.menu_cursor == 0:
							self.inc_level()
							self.draw_menu()
					continue
				elif event.type == pygame.MOUSEBUTTONDOWN:

					pos = pygame.mouse.get_pos()

					# Figure out which menu option is being clicked, if any

					if pos[0] < self.menu_pos[0]: continue
					if pos[0] >= self.menu_pos[0] + self.menu_width: continue
					if pos[1] < self.menu_pos[1]: continue
					i = (pos[1] - self.menu_pos[1]) / self.menu_font_height
					if i >= len(self.menu): continue
					rc = self.menu_select( i)
					if rc: return rc

			pygame.display.update( self.dirty_rects)

	# Return values:
	# -3 - Toggle fullscreen requires warm restart
	# -1 - User selected the Quit option or opened Editor
	#  0 - User selected Begin Game
	#  1 - User selected Levelset
	def menu_select( self, i):
		if i == 0:
			if IntroScreen.start_level == 0: return -2
			return IntroScreen.start_level
		elif i == 1:
			play_sound( menu_select)
			self.inc_levelset()
			setLevelset()
			self.draw_menu()
		elif i == 2:
			play_sound( menu_select)
			if not toggle_fullscreen(): return -3
			self.draw_menu()
		elif i == 3:
			play_sound( menu_select)
			toggle_music()
			self.draw_menu()
		elif i == 4:
			toggle_sound()
			play_sound( menu_select)
			self.draw_menu()
		elif i == 5:
			if colorblind == 1: os.system('python pathological.py -cb &')
			else: os.system('python pathological.py &')
			return -1
		elif i == 6:
			return -1
		return 0

def setup_everything():
	global introscreen
	
	# Check if default Custom levelset file exists, if not create it
	if not os.path.isfile(os.path.join('user_circuits', 'Custom')):
		open('user_circuits/Custom', 'a').close()

	# Configure the audio settings
	if sys.platform[0:3] == 'win':
		# On Windows platforms, increase the sample rate and the buffer size
		pygame.mixer.pre_init(44100,-16,1,4096)

	# Initialize the game module
	pygame.display.init()
	try:
		pygame.mixer.init()
	except:
		print("error on pygame.mixer.init() inside setup_everything():")
		print(sys.exc_info()[0],":",sys.exc_info()[1])
		print("...ignoring it")
	pygame.font.init()
	pygame.key.set_repeat(500, 30)

	if not pygame.font: print('Warning, fonts disabled')
	if not pygame.mixer: print('Warning, sound disabled')
	
	# Backup Custom levelset in case anything goes wrong (TODO: cleanup)
	date = time.strftime("%Y%m%d-%H:%M")
	src = os.path.join('user_circuits', 'Custom')
	dst = os.path.join('user_circuits', 'backups', date+'_Custom')
	copyfile(src, dst)

	set_video_mode()
	load_sounds()
	load_fonts()
	load_images()

	introscreen = IntroScreen( screen)

setup_everything()

# Main loop
while 1:
	# Display the intro screen
	while 1:
		
		# If rc is positive, it's an existing level
		rc = introscreen.do()
		
		# New level (always work with Custom set)
		if rc == -2:
			levelset = 'Custom'
			levelsetFolder = 'user_circuits'
			rc = 0

		# Warm restart to toggle fullscreen
		if rc == -3:
			fullscreen = fullscreen ^ 1
			setup_everything()
		else:
			break
			
	# Handle the QUIT message
	if rc < 0: break  
		
	levelsPath = (levelsetFolder,levelset)
	
	game = Game(screen, levelsPath, rc - 1)

	rc = game.play()
	# Back to menu
	if rc == 0: setLevelset()
	# Handle the QUIT message
	if rc < 0: break   
	
