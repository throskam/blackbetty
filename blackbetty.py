# Black Betty 1.0

import rg
import random

class Robot:

	#############################################################################
	# Basic API overload
	#############################################################################

	# Robots in game
	def robots(self, game):
		return game['robots'].values()

	# Move
	def move(self, location):
		return ['move', location]

	# Attack
	def attack(self, location):
		return ['attack', location]

	# Guard
	def guard(self):
		return ['guard']

	# Suicide
	def suicide(self):
		return ['suicide']

		# Is ally
	def isAlly(self, bot):
		return bot['player_id'] == self.player_id

	# Is enemy
	def isEnemy(self, bot):
		return bot['player_id'] != self.player_id

	# Invalid
	def isInvalid(self, location):
		return 'invalid' in rg.loc_types(location)

	# Normal
	def isNormal(self, location):
		return 'normal' in rg.loc_types(location)

	# Spawn
	def isSpawn(self, location):
		return 'spawn' in rg.loc_types(location)

	# Obstacle
	def isObstacle(self, location):
		return 'obstacle' in rg.loc_types(location)

	#############################################################################
	# Improved API
	#############################################################################

	# Enemies in game
	def enemies(self, game):
		enemies = []
		for bot in self.robots(game):
			if self.isEnemy(bot):
				enemies.append(bot)
		return enemies

	# Allies in game
	def allies(self, game):
		allies = []
		for bot in self.robots(game):
			if self.isAlly(bot):
				allies.append(bot)
		return allies

	# Bots around (including diagonal)
	def sight(self, game):
		sight = []
		for bot in self.robots(game):
			if self.isClose(bot):
				sight.append(bot)
		return sight

	# Bots around (excluding diagonal)
	def neighbours(self, game):
		neighbours = []
		for bot in self.robots(game):
			if self.isAdjacent(bot):
				neighbours.append(bot)
		return neighbours

	# Currently available targets
	def targets(self, game):
		targets = []
		for bot in self.neighbours(game):
			if self.isEnemy(bot):
				targets.append(bot)
		return targets

	# Next step to go to the location
	def next(self, location):
		# already there, do nothing
		if self.location == location:
			return None

		# current
		x0, y0 = self.location

		# destination
		x, y = location

		# deltas
		dx, dy = x - x0, y - y0

		# No dx, obv go to ny
		if dx == 0:
			ny = (x0, y0 + dy / abs(dy))
			if self.isOk(ny):
				return ny
			else:
				return None

		# No dy, obv go to nx
		if dy == 0:
			nx = (x0 + dx / abs(dx), y0)
			if self.isOk(nx):
				return nx
			else:
				return None

		# two options
		nx, ny = (x0 + dx / abs(dx), y0), (x0, y0 + dy / abs(dy))

		if abs(dx) < abs(dy):
			if self.isOk(ny):
				return ny
			if self.isOk(nx):
				return nx
		else:
			if self.isOk(nx):
				return nx
			if self.isOk(ny):
				return ny

		# nothing worked ...
		return None

	# 4 directions
	def cross(self):
		x0, y0 = self.location
		return [(x0+1, y0), (x0, y0+1), (x0-1, y0), (x0, y0-1)]

	# Available paths
	def paths(self):
		paths = []
		for path in self.cross():
			if self.isOk(path):
				paths.append(path)
		return paths

	# List of possible escapes
	def escapes(self, game):
		escapes = [];
		for path in self.paths():
			if self.isSafe(path, game):
				escapes.append(path)
		return escapes

	# Not obstacle and not invalid
	def isOk(self, location):
		return not self.isInvalid(location) and not self.isObstacle(location)

	# Check if a location is safe to go
	def isSafe(self, location, game):
		for bot in self.enemies(game):
			if rg.wdist(location, bot['location']) < 2:
				return False;
		return True

	# Location is at most dist away from us (including diagonal)
	def isInRange(self, location, dist):
		return rg.dist(self.location, location) <= dist

	# Location is at most dist away from us (excluding diagonal)
	def isInWalkingRange(self, location, dist):
		return rg.wdist(self.location, location) <= dist

	# Bot is next to us (including diagonal)
	def isClose(self, bot):
		return self.isInRange(bot['location'], 1)

	# Bot is next to us (excluding diagonal)
	def isAdjacent(self, bot):
		return self.isInWalkingRange(bot['location'], 1)

	#############################################################################
	# Collision
	#############################################################################

	# Bot involved in the collision
	def involved(self, location, game):
		involved = []
		for bot in self.robots(game):
			if self.location != bot['location'] and rg.wdist(location, bot['location']) < 2:
				involved.append(bot)
		return involved

	# Determine the priority rule
	def hasPriorityOver(self, bot):
		x0, y0 = self.location
		x, y = bot['location']
		return x0 > x or (x0 == x and y0 > y)

	#############################################################################
	# Actions
	#############################################################################

	# Hit a bot
	def hit(self, bot):
		return self.attack(bot['location'])

	# Choose the lowest opponent frow the given robots
	def aim(self, robots):
		target = None
		for bot in robots:
			if self.isAdjacent(bot) and (target is None or bot['hp'] < target['hp']):
				target = bot
		return target

	# Strike an ennemy in the most efficient way
	def strike(self, bot, game):
		# Avoid suicider
		if bot['hp'] < rg.settings.attack_range[1]:
			return self.run(game)

		# Worth suicide ?
		if self.hp <= len(self.targets(game))*rg.settings.attack_range[1]:
			return self.suicide()

		# Kill it!
		return self.hit(bot)

	# Move if no collision
	def go(self, location, game):
		for bot in self.involved(location, game):
			if self.isEnemy(bot):
				return None
			if not self.hasPriorityOver(bot):
				return None
		return self.move(location)

	# Move from spawn
	def hurry(self, game):
		# move some place safe
		for path in self.paths():
			if not self.isSpawn(path):
				return self.move(path)

		# try to attack someone
		target = self.aim(self.targets(game))
		if target is not None:
			return self.hit(target)

		# time to panic
		return self.panic(game)

	# Runaway
	def run(self, game):
		escapes = self.escapes(game)
		if len(escapes) > 0:
			return self.move(random.choice(escapes))
		return self.panic(game)

	# Panic mode
	def panic(self, game):
		# move randomly
		options = self.paths()
		if len(options) > 0:
			return self.move(random.choice(options))

		# try to attack someone
		target = self.aim(self.targets(game))
		if target is not None:
			return self.hit(target)

		# otherwise just guard...
		return self.guard()


	#############################################################################
	# Main
	#############################################################################

	def act(self, game):

		# Critical turn, move from spawn if it's necessary
		if int(game['turn']) % 5 == 0:
			if self.isSpawn(self.location):
				return self.hurry(game)

		targets = self.targets(game)
		target = self.aim(self.targets(game))

		# Close target
		if target is not None:
			return self.strike(target, game)

		# Predic enemies movement
		locations = []
		for bot in self.enemies(game):
			if self.isInWalkingRange(bot['location'], 2):
				location = self.next(bot['location'])
				if location is not None:
					# Avoid to hit an ally bot
					valid = True
					for ally in self.allies(game):
						if ally['location'] == location:
							valid = False
							break
					if valid:
						locations.append(location)
		if len(locations) > 0:
			return self.attack(random.choice(locations))

		# Random move
		choices = []
		paths = self.paths()
		for path in paths:
			if not self.isSpawn(path):
				choices.append(path)
		if len(choices) > 0:
			move = self.go(random.choice(choices), game)
			if move is not None:
				return move

		return self.guard()