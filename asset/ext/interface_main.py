''' Data
		addr = The address.
			('127.0.0.1', 6000)

		code = An address encoded by the socket_encoder.
			('127.0.0.1', 6000) = 32yvqix8dc0

		id = A unique number given to a room.
			0 = Server=Specific Room
			1 = 2-User Room
			2~= Multi-User Room

		room = A combination of a unique ID number and a code.
			id = 1; addr = ('127.0.0.1', 6000) = 32yvqix8dc0
			132yvqix8dc0

		name = The given name by the client when connecting.
			This is given the client itself.

	Room Protocol
		global = Global Room
		0[code] = 2-User Room
		[1 to ...][code] = Multi-User Room

	Data Protocol
		0[name]_[addr]
			A chat message to be added in a room.

		1[room]_[addr1]:[name1]_[addr2]:[name2]...
			A list of players to be added to a room.

		2[room]_[addr1]:[name1]_[addr2]:[name2]...
			A list of players to be removed from a room.

		3[room]_[name]
			A chat message to be added in a room.
'''
import pygame, re, math
import asset.ext.socket_encoder as socket_encoder
import asset.ext.room as room

import asset.api.SenPy as senpai
ahoge = senpai.remote["ahoge"]
kouhai = senpai.remote["kouhai"]
imouto = senpai.remote["imouto"]
kuudere = senpai.remote["kuudere"]

# Server Init
server = ahoge.stream((ahoge.ip, 0))
code = socket_encoder.encode(server.addr)
selected_room = "global"
rooms = {
	"global": room.Room("global", "Global")
}
room_id = 1
name = ""

# Set server.
room.set_server(server)

# Font
header = kuudere.get("segoe ui", 24, False, True)
body = kuudere.get("calibri", 18, False)
body_line = body.get_linesize() + 10

# Image
img_bg = pygame.image.load("asset/img/bg.png")
img_highlight = pygame.image.load("asset/img/highlight.png")

placeholder = "[Invite Code Here]"
imouto.background = None


# Update

def update():
	imouto.screen.blit(img_bg, (0, 0))

	imouto.screen.blit(
		surface_info,
		(0, 0)
	)

	imouto.screen.blit(
		chat_surface,
		(210, 570)
	)

	if room_surface:
		imouto.screen.blit(
			room_surface,
			(0, 270)
		)

	v = rooms[selected_room]

	if v.player_surface:
		imouto.screen.blit(
			v.player_surface,
			(600, 0)
		)

	if v.chat_surface:
		if v.chat_scroll_delta != v.chat_scroll:
			v.chat_scroll_delta = math.ceil((
				v.chat_scroll_delta +
				v.chat_scroll
			)/2)

		imouto.screen.blit(
			v.chat_surface,
			(210,
			10 + max(0, 570 - v.chat_surface.get_rect().height)),
			(0, v.chat_scroll_delta, 380, 560)
		)


# Server

def success(addr):
	# Successfully connected to a server.
	global name, code, rooms

	server.send("1global" + rooms["global"].players, addr)

server.on("success", success)

def connected(addr):
	# A client has connected.
	global rooms

	server.send("1global" + rooms["global"].players, addr)

server.on("connected", connected)

def disconnected(addr):
	global rooms
	i = socket_encoder.encode(addr)

	for k in rooms:
		if k == "global" and rooms[k].has(addr):
			rooms[k].chat(
				"'" + rooms[k].get(addr) +
				"' has disconnected."
			)

		rooms[k].rem(addr)
		rooms[k].update()

	update()

server.on("disconnected", disconnected)

def received(addr, data):
	global name, code
	i = data[:1]
	data = data[1:]

	if i == "0": # Data Chat
		sep = data.index("_")
		i = data[:sep]
		text = data[sep+1:]

		if i[0] == "0":
			i = "0" + socket_encoder.encode(addr)

		if i in rooms:
			rooms[i].chat(text)

			if not rooms[i].visible:
				rooms[i].visible = True

				room_update()

			update()
	elif i == "1": # Data Player
		sep = data.index("_")
		i = data[:sep]

		if i[0] == "0":
			i = "0" + socket_encoder.encode(addr)

		if i not in rooms:

			rooms[i] = room.Room(i)

			room_update()

		for v in re.split("_", data[sep+1:]):
			sep = v.index(":")
			n = v[sep+1:]
			v = socket_encoder.decode(v[:sep])

			if not rooms[i].has(v):
				rooms[i].add(v, n)

				server.connect(v)

				if i == "global":
					rooms[i].chat("connected with '" + n + "'.")

		rooms[i].update()
		update()
	elif i == "2": # Data Disconnect
		pass
	elif i == "3": # Data Room
		sep = data.index("_")
		i = data[:sep]
		data = data[sep+1:]

		if i in rooms:
			rooms[i].name = data
		else:
			rooms[i] = room.Room(i, data)

		room_update()

server.on("received", received)

# Info Surface (Top-left Corner)

surface_info = None

def write(v, pos=(0, 0)):
	global surface_info

	image = body.render(
		v,
		True,
		(255, 255, 255)
	)
	rect = image.get_rect()

	if not surface_info:
		surface_info = pygame.Surface(
			(rect.width + pos[0], rect.height + pos[1]),
			pygame.SRCALPHA
		)
	else:
		rect1 = surface_info.get_rect()
		draft = pygame.Surface((
			max(rect.right + pos[0], rect1.right),
			max(rect.bottom + pos[1], rect1.bottom)
		), pygame.SRCALPHA)

		draft.blit(surface_info, (0, 0))

		surface_info = draft

	surface_info.blit(image, pos)

def set_name(v):
	global code, room, server, name

	# Set name.
	name = v
	rooms["global"].add(server.addr, v)
	rooms["global"].update()

	write("Name: " + v,
		(10, 8 + 60)
	)

	room_update()

write("Invite: " + code,
	(10, 8))
write("Socket: " + server.addr[0] + ":" + str(server.addr[1]),
	(10, 8 + 30))


# Room System

## Player List

player_frame = kouhai.Frame({
	"rect": (600, 0, 200, 600)
})

def player_mousebuttondown(event):
	global rooms, selected_room, chatbox
	i = int(event.pos[1]/30) + rooms[selected_room].player_scroll

	addr2, name2 = rooms[selected_room].get(i)

	if addr2 and addr2 != server.addr:
		i = "0"+socket_encoder.encode(addr2)

		if i in rooms:
			rooms[i].visible = not rooms[i].visible
		else:
			rooms[i] = room.Room(i, name2)
			rooms[i].add(server.addr, name)
			rooms[i].add(addr2, name2)
			rooms[i].update()

			server.send("1" + i + rooms[i].players, addr2)
			server.send("30" + code + "_" + name, addr2)

		selected_room = i
		room_update()

player_frame.on("mousebuttondown", player_mousebuttondown)

## Room List

room_scroll = 0
room_scroll_delta = 0
room_frame = kouhai.Frame({
	"rect": (0, 270, 200, 330)
})
room_surface = None

def room_mousebuttondown(event):
	global rooms, selected_room

	i = int((event.pos[1] - 270)/30) + room_scroll

	if i < len(rooms):
		n = 0
		# Find the room with the corresponding index.
		for k in rooms:
			if i == n:
				selected_room = k
				break

			n += 1

		room_update()

room_frame.on("mousebuttondown", room_mousebuttondown)

def room_update():
	global rooms, room_surface, selected_room

	room_surface = pygame.Surface(
		(200, len(rooms)*30 + 5),
		pygame.SRCALPHA
	)

	i = 0
	for k in rooms:
		if rooms[k].visible:
			if selected_room == k:
				room_surface.blit(img_highlight,
					(-5, i*30 - 5)
				)

			image = body.render(
				rooms[k].name,
				True,
				(255, 255, 255)
			)

			room_surface.blit(image,
				(10, i*30 + 8)
			)

			i += 1

	update()


## Chatbox

chat_frame = kouhai.Frame({
	"rect": (200, 0, 400, 570)
})

chat_textbox = kouhai.TextBox({
	"rect": (200, 570, 400, 30)
})

chat_surface = pygame.Surface(
	(380, 30),
	pygame.SRCALPHA
)

def chat_mousebuttondown(event):
	if rooms[selected_room].chat_surface and (event.button == 4 or event.button == 5):
		rect = rooms[selected_room].chat_surface.get_rect()
		delta = event.button == 5 and 1 or -1

		rooms[selected_room].chat_scroll = max(0, min(
			rooms[selected_room].chat_scroll + body_line*delta,
			rect.height - 570
		))

		update()

chat_frame.on("mousebuttondown", chat_mousebuttondown)

def chat_keyinput(event):
	global room, selected_room, code, name
	text = chat_textbox.properties["text"]

	chat_surface.fill((0, 0, 0, 0))

	if event and (event.key == 13 or event.key == 271) and len(text) > 0:
		chat_textbox.properties["text"] = ""

		if text[:8] == "/invite ":
			# Invite someone in the dynamic server.
			# Does not add in your private room.
			addr = socket_encoder.decode(text[8:])

			if addr:
				server.connect(addr)
			else:
				rooms[selected_room].chat("Invite code invalid!")
		elif text[:5] == "/add ":
			# Invite someone in your private room.
			# Does not work in global room.
			pass
		else:
			# Chat in your selected room.
			text = name + " : " + text

			rooms[selected_room].chat(text)
			rooms[selected_room].broadcast(
				"0" + selected_room + "_" + text
			)

		text = ""

	d = len(text) > 0

	kuudere.draw(
		chat_surface,
		body,
		(0, 0, 380, 30),
		d and text or "[Chat Here]",
		1,
		d and (191, 191, 191) or (127, 127, 127),
		align=(0, 0.5)
	)
	update()

chat_keyinput(None)
chat_textbox.on("keyinput", chat_keyinput)


# Quit

def quit(event):
	ahoge.close_all()

imouto.on("quit", quit)

update()