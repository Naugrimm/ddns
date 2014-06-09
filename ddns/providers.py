#!/usr/bin/python
###############################################################################
#                                                                             #
# ddns - A dynamic DNS client for IPFire                                      #
# Copyright (C) 2012 IPFire development team                                  #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

# Import all possible exception types.
from .errors import *

class DDNSProvider(object):
	INFO = {
		# A short string that uniquely identifies
		# this provider.
		"handle"    : None,

		# The full name of the provider.
		"name"      : None,

		# A weburl to the homepage of the provider.
		# (Where to register a new account?)
		"website"   : None,

		# A list of supported protocols.
		"protocols" : ["ipv6", "ipv4"],
	}

	DEFAULT_SETTINGS = {}

	def __init__(self, core, **settings):
		self.core = core

		# Copy a set of default settings and
		# update them by those from the configuration file.
		self.settings = self.DEFAULT_SETTINGS.copy()
		self.settings.update(settings)

	def __repr__(self):
		return "<DDNS Provider %s (%s)>" % (self.name, self.handle)

	def __cmp__(self, other):
		return cmp(self.hostname, other.hostname)

	@property
	def name(self):
		"""
			Returns the name of the provider.
		"""
		return self.INFO.get("name")

	@property
	def website(self):
		"""
			Returns the website URL of the provider
			or None if that is not available.
		"""
		return self.INFO.get("website", None)

	@property
	def handle(self):
		"""
			Returns the handle of this provider.
		"""
		return self.INFO.get("handle")

	def get(self, key, default=None):
		"""
			Get a setting from the settings dictionary.
		"""
		return self.settings.get(key, default)

	@property
	def hostname(self):
		"""
			Fast access to the hostname.
		"""
		return self.get("hostname")

	@property
	def username(self):
		"""
			Fast access to the username.
		"""
		return self.get("username")

	@property
	def password(self):
		"""
			Fast access to the password.
		"""
		return self.get("password")

	def __call__(self):
		raise NotImplementedError

	def send_request(self, *args, **kwargs):
		"""
			Proxy connection to the send request
			method.
		"""
		return self.core.system.send_request(*args, **kwargs)

	def get_address(self, proto):
		"""
			Proxy method to get the current IP address.
		"""
		return self.core.system.get_address(proto)


class DDNSProviderNOIP(DDNSProvider):
	INFO = {
		"handle"    : "no-ip.com",
		"name"      : "No-IP",
		"website"   : "http://www.no-ip.com/",
		"protocols" : ["ipv4",]
	}

	# Information about the format of the HTTP request is to be found
	# here: http://www.no-ip.com/integrate/request and
	# here: http://www.no-ip.com/integrate/response

	url = "http://%(username)s:%(password)s@dynupdate.no-ip.com/nic/update"

	def __call__(self):
		url = self.url % {
			"username" : self.username,
			"password" : self.password,
		}

		data = {
			"hostname" : self.hostname,
			"address"  : self.get_address("ipv4"),
		}

		# Send update to the server.
		response = self.send_request(url, data=data)

		# Get the full response message.
		output = response.read()

		# Handle success messages.
		if output.startswith("good") or output.startswith("nochg"):
			return

		# Handle error codes.
		if output == "badauth":
			raise DDNSAuthenticationError
		elif output == "aduse":
			raise DDNSAbuseError
		elif output == "911":
			raise DDNSInternalServerError

		# If we got here, some other update error happened.
		raise DDNSUpdateError


class DDNSProviderSelfhost(DDNSProvider):
	INFO = {
		"handle"    : "selfhost.de",
		"name"      : "Selfhost.de",
		"website"   : "http://www.selfhost.de/",
		"protocols" : ["ipv4",],
	}

	url = "https://carol.selfhost.de/update"

	def __call__(self):
		data = {
			"username" : self.username,
			"password" : self.password,
			"textmodi" : "1",
		}

		response = self.send_request(self.url, data=data)

		match = re.search("status=20(0|4)", response.read())
		if not match:
			raise DDNSUpdateError
