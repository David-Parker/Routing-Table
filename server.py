# server.py
# EID: dp24559

# This server emulates the behavior of a routing table. Updates are sent, parsed and the server builds a prefix tree then stores the routes and 
# their costs. Queries can also be sent and the server looks up the ip address in the prefix tree and determines the best matching route.

from socket import *
import sys

serverPort = 0

# Read the port number from the command line argument
if(len(sys.argv) != 2):
	print("You must specify the port!")
	sys.exit()
else:
	serverPort = int(sys.argv[1])

# Global vars
serverName = "localhost"

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.bind(("", serverPort))
serverSocket.listen(10)

def ipToBinaryString(ip):
    decimals = map(int, ip.split('/')[0].split('.'))
    binary = '{0:08b}{1:08b}{2:08b}{3:08b}'.format(*decimals)
    range = int(ip.split('/')[1]) if '/' in ip else None
    return binary[:range] if range != None else binary

class Route:
	def __init__(self, router, ip, cost):
		self.router = router
		self.cidr = ip

		address = ip.split('/')
		self.ip = address[0]
		self.submask = address[1]
		self.cost = cost

class PrefixTreeNode:
	def __init__(self, zero, one, route):
		self.zero = zero
		self.one = one
		self.route = route

class PrefixTree:
	# Default entry is a catch-all route with cost 100
	root = PrefixTreeNode(None, None, Route('A', '0.0.0.0/0', 100))

	def addRouteHelper(self, binaryString, index, route, node):
		if(index == len(binaryString)):
			if(node.route == None):
				node.route = route

			# Update cost if it is smaller or if equal (most recent in a tie)
			elif(node.route.cost >= route.cost):
				node.route = route

			return

		bin = binaryString[index]

		if(bin == '0'):
			if(node.zero == None):
				node.zero = PrefixTreeNode(None, None, None)

			self.addRouteHelper(binaryString, index + 1, route, node.zero)
		
		elif(bin == '1'):
			if(node.one == None):
				node.one = PrefixTreeNode(None, None, None)

			self.addRouteHelper(binaryString, index + 1, route, node.one)

	def addRoute(self, route):
		binaryString = ipToBinaryString(route.cidr)

		self.addRouteHelper(binaryString, 0, route, self.root)

		return route

	def lookupRouteHelper(self, binaryString, index, node, bestRouteSoFar):
		if(node.route != None):
			if(node.route.cost <= bestRouteSoFar.cost):
				bestRouteSoFar = node.route

		if(index == len(binaryString)):
			return bestRouteSoFar

		bin = binaryString[index]

		if(bin == '0'):
			if(node.zero == None):
				# As far as we can go
				return bestRouteSoFar
			else:
				return self.lookupRouteHelper(binaryString, index + 1, node.zero, bestRouteSoFar)

		elif(bin == '1'):
			if(node.one == None):
				# As far as we can go
				return bestRouteSoFar
			else:
				return self.lookupRouteHelper(binaryString, index + 1, node.one, bestRouteSoFar)


	def lookupRoute(self, ipAddress):
		binaryString = ipToBinaryString(ipAddress)

		return self.lookupRouteHelper(binaryString, 0, self.root, self.root.route)

	def clearTree(self):
		root = PrefixTreeNode(None, None, Route('A', '0.0.0.0/0', 100))

class Command:
	def __init__(self, command, body):
		self.command = command
		self.body = body
		self.routes = []

class Router:
	def parseRoutes(self, body):
		routes = []
		for line in body:
			items = line.split(' ')
			route = Route(items[0], items[1], int(items[2]))
			routes.append(route)
		return routes

	def parseInput(self, input, prefixTree):
		sections = input.split('\r\n')
		command = sections[0]
		body = []

		for i in range(1, len(sections) - 2):
			body.append(sections[i])

		commandObj = Command(command, body)

		if(commandObj.command == 'UPDATE'):
			routes = self.parseRoutes(commandObj.body)
			commandObj.routes = routes

			for route in commandObj.routes:
				prefixTree.addRoute(route)

			return 'ACK\r\nEND\r\n'

		elif(commandObj.command == 'QUERY'):
			route = prefixTree.lookupRoute(commandObj.body[0])

			result = 'RESULT\r\n' + commandObj.body[0] + ' ' + route.router + ' ' + str(route.cost) + '\r\nEND\r\n'

			return result

		return input

router = Router()
prefixTree = PrefixTree()

while(1):

	connectionSocket, addr = serverSocket.accept()
	connectionSocket.settimeout(5)

	try:
		data = connectionSocket.recv(8192)
	except timeout:
		connectionSocket.close()
		continue

	input = data.decode()

	try:
		response = router.parseInput(input, prefixTree)
		connectionSocket.send(response.encode())
		print(response)
	except Exception as e:
		print(str(e))

	connectionSocket.close()
