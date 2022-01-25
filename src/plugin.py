# -*- coding: UTF-8 -*-
#####################################
# CSFD Lite by origin from mik9
#####################################
PLUGIN_VERSION = "1.2"

############## @TODOs
# - lokalizacia cz, sk, en
# - redesign
############## @TODOs

from Plugins.Plugin import PluginDescriptor
from twisted.web.client import downloadPage
from enigma import ePicLoad, eServiceReference, eServiceCenter, getDesktop, iServiceInformation, eConsoleAppContainer
from Screens.Screen import Screen
from Screens.EpgSelection import EPGSelection
from Screens.ChannelSelection import SimpleChannelSelection
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Button import Button
from Components.AVSwitch import AVSwitch
from Components.MenuList import MenuList
from Components.ProgressBar import ProgressBar
from Components.ConfigList import ConfigListScreen
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Components.config import config, ConfigSubsection, ConfigSelection, configfile, ConfigYesNo, getConfigListEntry
from distutils.version import StrictVersion
import traceback
import re
from random import *
import sys
from os import path, access, R_OK, remove, listdir
import time
try:
	from urllib import quote
	from urllib2 import build_opener, HTTPRedirectHandler
except:
	from urllib.request import build_opener, HTTPRedirectHandler
	from urllib.parse import quote

####################### SETTINGS
config.plugins.CSFDLite = ConfigSubsection()
SKIN_PATH = path.join(resolveFilename(SCOPE_PLUGINS), 'Extensions/CSFDLite')
skinChoices = [(fname, path.splitext(fname)[0].replace('skin','').replace('_','')) for fname in listdir(SKIN_PATH) if fname.startswith('skin') and fname.endswith('.xml') ]
skinChoices.insert(0,'auto')
config.plugins.CSFDLite.skin = ConfigSelection(default="auto", choices=skinChoices)
order = [('1', 'Podľa dátumu zostupne'), ('2', 'Podľa dátumu vzostupne'), ('3', 'Podľa hodnotenia')]
config.plugins.CSFDLite.commentsOrder = ConfigSelection(default="1", choices=order)
config.plugins.CSFDLite.replaceImdb = ConfigYesNo(default=False)
####################### SETTINGS

class eConnectCallbackObj:
	def __init__(self, obj=None, connectHandler=None):
		self.connectHandler = connectHandler
		self.obj = obj

	def __del__(self):
		if 'connect' not in dir(self.obj):
			if 'get' in dir(self.obj):
				self.obj.get().remove(self.connectHandler)
			else:
				self.obj.remove(self.connectHandler)
		else:
			del self.connectHandler
		self.connectHandler = None
		self.obj = None


def eConnectCallback(obj, callbackFun):
	if 'connect' in dir(obj):
		return eConnectCallbackObj(obj, obj.connect(callbackFun))
	else:
		if 'get' in dir(obj):
			obj.get().append(callbackFun)
		else:
			obj.append(callbackFun)
		return eConnectCallbackObj(obj, callbackFun)
	return eConnectCallbackObj()


def replaceImdb():
	try:
		if config.plugins.CSFDLite.replaceImdb.value:
			if fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/plugin.py")) or \
			fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/plugin.pyc")) or\
			fileExists(resolveFilename(SCOPE_PLUGINS, "Extensions/IMDb/plugin.pyo")):
				print('[CSFDLite] Imdb try replace.')
				#if config.misc.CSFD.CSFDreplaceIMDB.getValue() and CSFDGlobalVar.getIMDBexist():
				import Plugins.Extensions.IMDb.plugin
				Plugins.Extensions.IMDb.plugin.IMDB = CSFDLite
				print('[CSFDLite] Imdb replace DONE.')
			else:
				print('[CSFDLite] Imdb plugin not installed. Nothing to replace.')
	except:
		print('[CSFDLite] Imdb replace failed. %s'%traceback.format_exc())


def dwnpage(a, b):
	return downloadPage(a.encode('utf-8'), b) if sys.version_info[0] == 3 else downloadPage(a, b)
	# 	return downloadPage(a, b)
	# except:
	# 	return 


def toStr(a):
	try:
		if sys.version_info >= (3, 0, 0):
			if isinstance(a, str):
				return a
			if isinstance(a, bytes):
				return str(a, 'utf8')
			return str(a)
		if isinstance(a, basestring):
			if isinstance(a, unicode):
				return a.encode('utf-8')
			return a
		return str(a)
	except:
		print("[CSFDLite] toStr ERROR=%s"%traceback.format_exc())
	return "xxx"

def norm(text):
	#exp = toStr(text)
	exp = text
	try:
		if sys.version_info >= (3, 0, 0):
			import unicodedata
			exp = ''.join((c for c in unicodedata.normalize('NFD', exp) 
										if unicodedata.category(c) != 'Mn'))
		else:
			if isinstance(exp, str):
				return exp
			import unicodedata
			exp = ''.join((c for c in unicodedata.normalize('NFD', exp) 
										if unicodedata.category(c) != 'Mn')).encode('utf-8')
	except:
		pass
	return exp

class CSFDLiteConfigScreen(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		ConfigListScreen.__init__(self, [], session=session)#, on_change=self.changedEntry)
		#self.onChangedEntry = [ ]
		self.skinBefore = config.plugins.CSFDLite.skin.value
		self.config_list_entries = []
		size = getDesktop(0).size()
		isDmm = False
		try:
			from enigma import eMediaDatabase
			isDmm = True
		except:
			pass
		width = size.width()
		fntTitle = '35' if width >= 1920 else '28'
		itmHeight = '40' if width >= 1920 else '32'
		fntDmm = '' if isDmm else ('font="Regular;30"' if width >= 1920 else 'font="Regular;24"')
		fntFooter = '35' if width >= 1920 else '28'
		self.skin = '''
		<screen name="CSFDLiteConfigScreen" position="center,center" size="800,500" flags="wfNoBorder" backgroundColor="#80ffffff">
			<eLabel name="bg_title" position="10,10" size="780,90" zPosition="-1" backgroundColor="#20000000" />
			<eLabel name="bg_list" position="10,110" size="780,280" zPosition="-1" backgroundColor="#20000000" />
			<eLabel name="bg_bottom" position="10,400" size="780,90" zPosition="-1" backgroundColor="#20000000" />

			<widget name="title_label" font="Regular;%s" backgroundColor="#20000000" halign="left" valign="center" position="20,10" size="480,90" transparent="1" />

			<widget name="config" position="15,120" size="775,270" itemHeight="%s" %s scrollbarMode="showOnDemand" transparent="1" />

			<eLabel name="btn_red" position="20,415" size="10,60" backgroundColor="#00f23d21" zPosition="2" />
			<eLabel name="btn_green" position="370,415" size="10,60" backgroundColor="#0031a500" zPosition="2" />
			<widget backgroundColor="#20000000" transparent="1" valign="center" halign="left" font="Regular;%s" name="key_red" position="40,400" size="340,90" zPosition="1" />
			<widget backgroundColor="#20000000" transparent="1" valign="center" halign="left" font="Regular;%s" name="key_green" position="390,400" size="340,90" zPosition="1" />
		</screen>
		''' % (fntTitle, itmHeight, fntDmm, fntFooter, fntFooter)

		self['title_label'] = Label("CSFDLite - Nastavenia")
		self["key_red"] = Label("Zrušiť")
		self["key_green"] = Label("Uložiť")

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
            {
                "left": self.keyLeft,
				"right": self.keyRight,
				"up": self.keyUp,
			    "down": self.keyDown,
                "cancel": self.keyCancel,
                "green": self.keySave,
                "red": self.keyCancel,
            }, -2)

		self.onShown.append(self.getSettings)

	def getSettings(self):
		self.config_list_entries = []
		self.config_list_entries.append(getConfigListEntry("Skin", config.plugins.CSFDLite.skin))
		self.config_list_entries.append(getConfigListEntry("Radenie komentárov", config.plugins.CSFDLite.commentsOrder))
		self.config_list_entries.append(getConfigListEntry("Nahradiť IMDB", config.plugins.CSFDLite.replaceImdb))
		self["config"].list = self.config_list_entries
		self["config"].setList(self.config_list_entries)

	#def changedEntry(self):
		# for x in self.onChangedEntry:
		# 	x()
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
	def keyRight(self):
		ConfigListScreen.keyRight(self)
	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
	def keySave(self):
		def restart_e2(callback=None):
			try:
				from Screens.Standby import TryQuitMainloop
				if callback:
					from Screens.Standby import TryQuitMainloop
					self.session.open(TryQuitMainloop, 3)
				else:
					self.close(True)
			except:
				self.close(True)
		self.saveAll()
		if self.skinBefore != config.plugins.CSFDLite.skin.value:
			self.session.openWithCallback(restart_e2, MessageBox, "Zmeny v nastaveniach sa prejavia po reštarte E2. Chcete reštartovať teraz?", type=MessageBox.TYPE_YESNO)
		else:
			self.close(True)
	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class CSFDChannelSelection(SimpleChannelSelection):
	def __init__(self, session):
		SimpleChannelSelection.__init__(self, session, "Volba kanálu")
		self.skinName = "SimpleChannelSelection"

		self["ChannelSelectEPGActions"] = ActionMap(["ChannelSelectEPGActions"],
			{
				"showEPGList": self.channelSelected
			}
		)

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			self.session.openWithCallback(
				self.epgClosed,
				CSFDEPGSelection,
				ref,
				openPlugin = False
			)

	def epgClosed(self, ret = None, popis = ""):
		if ret:
			self.close(ret, popis)

class CSFDEPGSelection(EPGSelection):
	def __init__(self, session, ref, openPlugin = True):
		EPGSelection.__init__(self, session, ref)
		self.skinName = "EPGSelection"
		self["key_green"].setText(toStr("Hledání"))
		self.openPlugin = openPlugin

	def infoKeyPressed(self):
		self.timerAdd()

	def timerAdd(self):
		cur = self["list"].getCurrent()
		evt = cur[0]
		self.popiskomplet = evt.getShortDescription() + "\n" + evt.getExtendedDescription()
		sref = cur[1]
		if not evt: 
			return

		if self.openPlugin:
			self.session.open(
				CSFDLite,
				evt.getEventName(),
				self.popiskomplet
			)
			
		else:
			self.close(evt.getEventName(),self.popiskomplet)

	def onSelectionChanged(self):
		pass

class CSFDLite(Screen):
	#def __init__(self, session, eventName='', callbackNeeded=False, EPG='', sourceEPG=False, DVBchannel='', *args, **kwargs):
	#def __init__(self, session, eventName, callbackNeeded=False, save=False, savepath=None, localpath=None):
	#def __init__(self, session, eventName, predanypopis='', args=None):
	#def __init__(self, session, eventName='', callbackNeeded=False, predanypopis='',sourceEPG=False, DVBchannel='', *args, **kwargs):
	def __init__(self, session, eventName, predanypopis='', args=None):
		settingskin = config.plugins.CSFDLite.skin.value
		self.omezenikomentaru = 500000
		self.omezeninazvu = 100 if 'FullHD' in settingskin else 70
		if settingskin == 'auto':
			self.sirkadispleje = getDesktop(0).size().width()
			if getDesktop(0).size().width() > 1800:
				try:
					from enigma import eMediaDatabase
					self.skinfile = "/usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/skinFullHD_dreambox.xml"	
				except:
					self.skinfile = "/usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/skinFullHD.xml"
				self.omezenikomentaru = 500000
				self.omezeninazvu = 100
			else:
				self.skinfile = "/usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/skinHD.xml"
				self.omezenikomentaru = 500000
				self.omezeninazvu = 70
		else:
			self.skinfile = path.join(SKIN_PATH, settingskin)

		if not path.isfile(self.skinfile): # fallback
			self.skinfile = '/usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/skinHD.xml'

		skinsoubor = open(self.skinfile)
		self.skin = skinsoubor.read()
		skinsoubor.close()
		self.version = StrictVersion(PLUGIN_VERSION)
		Screen.__init__(self, session)
		self.eventName = eventName
		self.predanypopis = predanypopis
		self["poster"] = Pixmap()
		self.picload = ePicLoad()
		self.picload_conn = eConnectCallback(self.picload.PictureData, self.paintPosterPixmapCB)
		self["stars"] = ProgressBar()
		self["starsbg"] = Pixmap()
		self["stars"].hide()
		self["starsbg"].hide()
		self.ratingstars = -1
		self["titlelabel"] = Label("CSFD Lite")
		self["detailslabel"] = ScrollLabel("")
		self["extralabel"] = ScrollLabel("")
		self["statusbar"] = Label("")
		self["ratinglabel"] = Label("")
		self.resultlist = []
		self["menu"] = MenuList(self.resultlist)
		self["menu"].hide()
		self["key_red"] = Button("Nastavenia")
		self["key_green"] = Button("")
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")
		self.commentsSort = 1
		try:
			self.commentsSort = int(config.plugins.CSFDLite.commentsOrder.value) # 1- date_desc, 2- date_asc, 3- rating 
		except:
			pass
		# 0 = multiple query selection menu page
		# 1 = movie info page
		# 2 = extra infos page
		self.Page = 0
		self["actions"] = ActionMap(["CSFDLiteActions"],
		{
			"okLite": self.showDetails,
			"cancelLite": self.__onClose,
			"downLite": self.pageDown,
			"upLite": self.pageUp,
			"rightLite": self.vpravo,
			"leftLite": self.vlevo,
			"redLite": self.openSettings,
			"greenLite": self.showMenu,
			"yellowLite": self.showDetails,
			"blueLite": self.showExtras,
			"contextMenuLite": self.openChannelSelection,
			"showEventInfoLite": self.showDetails
		}, -1)
		try:
			self.container = eConsoleAppContainer()
			self.container.appClosed.append(self.konecExekuce)
			self.kontejnerfunguje = True
		except:
			self.kontejnerfunguje = False
		self.getCSFD()

	def openSettings(self):
		def refreshSettings(cb = None):
			self.commentsSort = int(config.plugins.CSFDLite.commentsOrder.value)
		try:
			self.session.openWithCallback(refreshSettings, CSFDLiteConfigScreen)
		except:
			print("Open settings failed. %s"%traceback.format_exc())
	
	def najdi(self, retezec, celytext):
		maska = re.compile(retezec, re.DOTALL)
		vysledek = maska.findall(celytext)
		vysledek = vysledek[0] if vysledek else ""
		return vysledek

	def hledejVse(self, retezec, celytext):
		maska = re.compile(retezec, re.DOTALL)
		vysledky = maska.findall(celytext)
		return vysledky

	def odstraneniTagu(self, upravovanytext):
		self.htmltags = re.compile('<.*?>')
		upravovanytext = self.htmltags.sub('', upravovanytext)
		upravovanytext = upravovanytext.replace('&amp;', '&').replace('&nbsp;', ' ')
		return upravovanytext

	def rimskeArabske(self, vstupnirimska):
		definicecislic = {'I':1, 'V':5, 'X':10, 'L':50, 'C':100, 'D':500, 'M':1000}
		rimska = ""
		for rznak in vstupnirimska:
			if rznak in "IVXLCDM":
				rimska+= rznak
		arabska = 0
		for iii, ccc in enumerate(rimska):
			if (iii+1) == len(rimska) or definicecislic[ccc] >= definicecislic[rimska[iii+1]]:
				arabska += definicecislic[ccc]
			else:
				arabska -= definicecislic[ccc]
		if arabska == 0:
			return ""
		else:
			return str(arabska)

	def rozlozeniNazvu(self, upravovanytext):
		zbytecnosti = [" -HD", " -W", " -ST", " -AD"]
		for zbytecnost in zbytecnosti:
			upravovanytext = upravovanytext.replace(zbytecnost, '')
		serialy = self.najdi('\s+([IVX]{0,7}\.?\s?\([0-9]?[0-9]?[0-9][,-]?\s?[0-9]?[0-9]?[0-9]?\))', upravovanytext)
		casti = self.najdi('\s+(\(?[0-9]?[0-9]?[0-9]/[0-9]?[0-9]?[0-9]\)?)(?![0-9])', upravovanytext)
		rimska_na_konci = self.najdi('\s+([IVX]{1,5}\.?)\s*$', upravovanytext)
		arabska_na_konci = self.najdi('\s+([0-9]?[0-9]?[0-9])\s*$', upravovanytext)
		kompletnazev = upravovanytext.replace(serialy, '').replace(" "+casti, ' ').replace(" "+rimska_na_konci, ' ').replace(" "+arabska_na_konci, ' ')
		rimska_na_konci = rimska_na_konci.replace(".","")
		rozlozenynazev = re.split('[:,;]', kompletnazev)
		nazev1 = rozlozenynazev[0].rstrip(' ')
		nazev2 = ""
		if len(rozlozenynazev) > 1:
			nazev2 = rozlozenynazev[1].lstrip(' ').rstrip(' ')
		bserial = False
		if serialy:
			bserial = True
			serie = self.najdi('([IVX]{1,5})', serialy)
			if serie:
				kompletnazev+= "S" + self.rimskeArabske(serie).zfill(2)
			epizoda = self.najdi('\(([0-9]?[0-9]?[0-9])', serialy)
			kompletnazev+= "E" + epizoda.zfill(2)
		elif casti:
			bserial = True
			epizoda = self.najdi('([0-9]?[0-9]?[0-9])/', casti)
			kompletnazev+= "E" + epizoda.zfill(2)
		elif rimska_na_konci:
			bserial = True
			kompletnazev+= "série%20" + self.rimskeArabske(rimska_na_konci)
	
		serialy = self.najdi('\s+([IVX]{0,7}\.?\s?\([0-9]?[0-9]?[0-9][,-]?\s?[0-9]?[0-9]?[0-9]?\))', nazev1)
		casti = self.najdi('\s+(\(?[0-9]?[0-9]?[0-9]/[0-9]?[0-9]?[0-9]\)?)(?![0-9])', nazev1)
		rimska_na_konci = self.najdi('([IVX]{1,5}\.?)\s*$', nazev1)
		arabska_na_konci = self.najdi('([0-9]?[0-9]?[0-9])\s*$', nazev1)
		nazev1 = nazev1.replace(serialy, '').replace(" "+casti, ' ').replace(" "+rimska_na_konci, ' ').replace(" "+arabska_na_konci, ' ')
	
		serialy = self.najdi('\s+([IVX]{0,7}\.?\s?\([0-9]?[0-9]?[0-9][,-]?\s?[0-9]?[0-9]?[0-9]?\))', nazev2)
		casti = self.najdi('\s+(\(?[0-9]?[0-9]?[0-9]/[0-9]?[0-9]?[0-9]\)?)(?![0-9])', nazev2)
		rimska_na_konci = self.najdi('([IVX]{1,5}\.?)\s*$', nazev2)
		arabska_na_konci = self.najdi('([0-9]?[0-9]?[0-9])\s*$', nazev2)
		nazev2 = nazev2.replace(serialy, '').replace(" "+casti, ' ').replace(" "+rimska_na_konci, ' ').replace(" "+arabska_na_konci, ' ')
	
		return kompletnazev, bserial, nazev1, nazev2  

	def odstraneniInterpunkce(self, upravovanytext):
		interpunkce = ',<.>/?;:"[{]}`~!@#$%^&*()-_=+|'
		for znak in interpunkce:
			upravovanytext = upravovanytext.replace(znak, ' ')
		upravovanytext = upravovanytext.replace('   ', ' ').replace('  ', ' ')
		return upravovanytext

	def malaPismena(self, upravovanytext):
		return toStr(upravovanytext).lower()

	def adresaPredPresmerovanim(self, adresa):
		opener = build_opener(HTTPRedirectHandler)
		request = opener.open(adresa)
		return request.url

	def nactiKomentare(self, predanastranka):
		vyslednytext = ""
		komentare = self.najdi('<h2>\s+Recenze(.*?)</section>', predanastranka)
		for jedenkomentar in self.hledejVse('<article(.*?)/article>', komentare):
			autorkomentare = self.najdi('class="user-title-name">(.*?)<', jedenkomentar)
			hodnocenikomentare = self.najdi('<span class="stars\s+(.*?)">', jedenkomentar)
			if "stars" in hodnocenikomentare:
				hodnocenikomentare = self.najdi('stars-([1-5])', hodnocenikomentare)
				hodnocenikomentare = "*" * int(hodnocenikomentare)
			elif "trash" in hodnocenikomentare:
				hodnocenikomentare = "odpad!"
			else:
				hodnocenikomentare = ""
			komentar = self.najdi('<p>\s+(.*?)\s+<span', jedenkomentar)
			datumkomentare = self.najdi('<time>(.*?)</time>', jedenkomentar)
			vyslednytext += autorkomentare + '    ' + hodnocenikomentare + '\n' + komentar + '\n' + datumkomentare + '\n\n'
		return vyslednytext

	def fetchFailed(self, kde):
		print("[CSFDLite] fetch failed " + kde)
		self["statusbar"].setText(toStr("Stále stahuji z CSFD: " + kde))

	def resetLabels(self):
		self["detailslabel"].setText("")
		self["ratinglabel"].setText("")
		self["titlelabel"].setText("")
		self["extralabel"].setText("")
		self.ratingstars = -1

	def pageUp(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveUp)
		if self.Page == 1:
			self["detailslabel"].pageUp()
		if self.Page == 2:
			self["extralabel"].pageUp()
	
	def pageDown(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.moveDown)
		if self.Page == 1:
			self["detailslabel"].pageDown()
		if self.Page == 2:
			self["extralabel"].pageDown()

	def vlevo(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.pageUp)
		if self.Page == 1:
			self["detailslabel"].pageUp()
		if self.Page == 2:
			self["extralabel"].pageUp()

	def vpravo(self):
		if self.Page == 0:
			self["menu"].instance.moveSelection(self["menu"].instance.pageDown)
		if self.Page == 1:
			self["detailslabel"].pageDown()
		if self.Page == 2:
			self["extralabel"].pageDown()

	def showMenu(self):
		if ( self.Page == 1 or self.Page == 2 ) and self.resultlist:
			hlavicka = self.nazeveventuproskin
			if self.rokEPG != '':
				hlavicka += ' (' + self.rokEPG + ')'	
			self.setTitle(toStr("Výsledky hledání pro " + hlavicka + " - CSFD Lite v. " + str(self.version)))
			self["menu"].show()
			self["stars"].hide()
			self["starsbg"].hide()
			self["ratinglabel"].hide()
			self["poster"].hide()
			self["extralabel"].hide()
			self["titlelabel"].hide()
			self["detailslabel"].hide()
			self["key_blue"].setText("")
			self["key_green"].setText("Seznam")
			self["key_yellow"].setText("Info o filmu")
			self.Page = 0
			
	def showDetails(self):
		self["ratinglabel"].show()
		self["detailslabel"].show()

		if self.resultlist and self.Page == 0:
			if not self.unikatni:
				self.link = self["menu"].getCurrent()[1]
				self.nazevkomplet = self["menu"].getCurrent()[0]
			self.unikatni = False
			self["statusbar"].setText(toStr("Stahování informace o filmu v CSFD: %s" % (self.link)))
			localfile = "/tmp/CSFDquery2.html"

			# default
			fetchurl = "https://www.csfd.cz/film/" + self.link + "/recenze/?" + str(randint(1000, 9999))
			if self.commentsSort == 1:
				fetchurl = "https://www.csfd.cz/film/" + self.link + "/recenze/?sort=datetime_desc"
			if self.commentsSort == 2:
				fetchurl = "https://www.csfd.cz/film/" + self.link + "/recenze/?sort=datetime_asc"
			if self.commentsSort == 3:	
				fetchurl = "https://www.csfd.cz/film/" + self.link + "/recenze/?sort=rating"

			print("[CSFDLite] downloading query " + fetchurl + " to " + localfile)
			dwnpage(fetchurl,localfile).addCallback(self.CSFDquery2).addErrback(self.fetchFailed("showDetails"))
			self["menu"].hide()
			self.resetLabels()
			self.setTitle(self.nazevkomplet + " - CSFD Lite v. " + str(self.version))
			self["titlelabel"].show()
			self.Page = 1

		if self.Page == 2:
			self["titlelabel"].show()
			self["extralabel"].hide()
			self["poster"].show()
			if self.ratingstars > 0:
				self["starsbg"].show()
				self["stars"].show()
				self["stars"].setValue(self.ratingstars)

			self.Page = 1

	def showExtras(self):
		if self.Page == 1:
			self["extralabel"].show()
			self["detailslabel"].hide()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self["ratinglabel"].hide()
			self.Page = 2

	def openChannelSelection(self):
		self.session.openWithCallback(
			self.channelSelectionClosed,
			CSFDChannelSelection
		)

	def channelSelectionClosed(self, ret = None, popis = ""):
		if ret:
			self.eventName = ret
			self.predanypopis = popis
			self.Page = 0
			self.resultlist = []
			self["menu"].hide()
			self["ratinglabel"].show()
			self["detailslabel"].show()
			self["poster"].hide()
			self["stars"].hide()
			self["starsbg"].hide()
			self.getCSFD()

	def getCSFD(self):
		self.resetLabels()
		self.popisEPG = self.predanypopis
		if self.eventName == "":
			s = self.session.nav.getCurrentService()
			info = s and s.info()
			event = info and info.getEvent(0) # 0 = now, 1 = next
			self.popisEPG = ""
			if event:
				self.eventName = event.getEventName()
				self.popisEPG = event.getShortDescription() + "\n" + event.getExtendedDescription()

		if self.popisEPG:
			self.rokEPG = self.najdi('\([1-2][0-9]{3}\)', self.popisEPG).replace("(","").replace(")","")
			if self.rokEPG == '':
				self.rokEPG = self.najdi('[1-2][0-9]{3}', self.popisEPG)
		else:
			self.rokEPG = ''

		if self.eventName != "":
			self.nazeveventuproskin = self.eventName
			try:
				self.eventName = quote(self.eventName)
			except:
				self.eventName = quote(self.eventName.decode('utf8').encode('ascii','ignore'))

			self.nazeveventu = self.eventName
			jineznaky = list(set(self.hledejVse('(%[0-9A-F][0-9A-F])', self.nazeveventu)))
			for jinyznak in jineznaky:
				desitkove = int(jinyznak[1:3], 16)
				if desitkove > 31 and desitkove < 128:
					self.nazeveventu = self.nazeveventu.replace(jinyznak, chr(desitkove)) 
				elif desitkove > 127:
					self.nazeveventu = self.nazeveventu.replace(jinyznak, jinyznak.lower())
			self.nazeveventu = self.nazeveventu.replace('%', '\\x')

			self.celejmeno, self.je_serial, self.jmeno1, self.jmeno2 = self.rozlozeniNazvu(self.nazeveventu)
			dotaz1 = norm(self.celejmeno)
			if not self.je_serial:
				dotaz1+= "%20" + self.rokEPG
			
			dotaz1 = dotaz1.replace(" ", "%20").replace('\\x', "%")
			self.jmeno1 = self.jmeno1.replace(" ", "%20").replace('\\x', "%")
			self.jmeno2 = self.jmeno2.replace(" ", "%20").replace('\\x', "%")

			self["statusbar"].setText(toStr("Hledání v CSFD pro: %s" % (self.nazeveventuproskin)))
			localfile = "/tmp/CSFDquery.html"
			fetchurl = "https://www.csfd.cz/hledat/?q=" + dotaz1
			self.puvodniurl = fetchurl
			open(localfile, 'w').close()
			print("[CSFDLite] Downloading Query " + fetchurl + " to " + localfile)
			dwnpage(fetchurl,localfile).addCallback(self.CSFDquery).addErrback(self.CSFDquery)
		else:
			self["statusbar"].setText(toStr("Nejde získat Eventname"))

	def CSFDquery(self, string):
		print("[CSFDquery]")
		self["statusbar"].setText(toStr("Stahování z CSFD dokončeno pro %s" % (self.nazeveventuproskin)))
		self.inhtml = (open("/tmp/CSFDquery.html", "r").read())
		self.resultlist = []
		self.unikatni = False

		if '<h1 itemprop="name">' in self.inhtml:
			odkaz = self.najdi('https://www.csfd.cz/film/(.*?)/', self.inhtml)
			nazevfilmu = self.najdi('<h1 itemprop=\"name\">(.*?)<', self.inhtml)
			nazevfilmu = nazevfilmu.replace("\t","").replace("\n","")
			self.resultlist = [(nazevfilmu, odkaz)]
		else:
			print("[CSFDLite] ziskavani seznamu")
			self.resultlist = []
			seznamfilmu = self.najdi('<h2>Filmy(.*?)<h2>Seri', self.inhtml)
			seznamserialu = self.najdi('<h2>Seri(.*?)</section>', self.inhtml)
			if self.je_serial:
				seznamcely = seznamserialu + seznamfilmu
			else:
				seznamcely = seznamfilmu + seznamserialu
			for odkaz, filmnazev, filminfo in self.hledejVse('<h3.*?<a href="/film/(.*?)".*?"film-title-name">(.*?)</a>(.*?)</h3>', seznamcely):
				hlavninazev = filmnazev
				celynazev = hlavninazev
				rok = self.najdi('<span class="info">\(([0-9]{4})', filminfo)
				typnazev = self.najdi('<span class="info">.*?<span class="info">\((.*[a-z])\)', filminfo)
				if rok != "":
					celynazev += ' (' + rok + ')'
				if typnazev != "":
					celynazev += ' (' + typnazev + ')'
				self.resultlist += [(celynazev, odkaz, hlavninazev, rok)]
				
			self["statusbar"].setText(toStr("Hledání v CSFD pro: %s" % (self.nazeveventuproskin)))
			localfile = "/tmp/CSFDquery_dotaz2.html"
			fetchurl = "https://www.csfd.cz/hledat/?q=" + self.jmeno1
			self.puvodniurl = fetchurl
			print("[CSFDLite] Downloading Query " + fetchurl + " to " + localfile)
			dwnpage(fetchurl,localfile).addCallback(self.CSFDquery_dotaz2).addErrback(self.fetchFailed("CSFDquery"))

	def CSFDquery_dotaz2(self, string):			
		print("[CSFDquery_dotaz2]")
		self["statusbar"].setText(toStr("Stahování z CSFD dokončeno pro %s" % (self.nazeveventuproskin)))
		self.inhtml = (open("/tmp/CSFDquery_dotaz2.html", "r").read())

		if '<h1 itemprop="name">' in self.inhtml:
			odkaz = self.najdi('https://www.csfd.cz/film/(.*?)/', self.inhtml)
			nazevfilmu = self.najdi('<h1 itemprop=\"name\">(.*?)<', self.inhtml)
			nazevfilmu = nazevfilmu.replace("\t","").replace("\n","")
			self.resultlist = [(nazevfilmu, odkaz)]
		elif "SFD.cz </title>" in self.inhtml:
			print("[CSFDLite] ziskavani seznamu 2")
			for odkaz, filmnazev, filminfo in self.hledejVse('<h3.*?<a href="/film/(.*?)".*?"film-title-name">(.*?)</a>(.*?)</h3>', self.inhtml):
				hlavninazev = filmnazev
				celynazev = hlavninazev
				rok = self.najdi('<span class="info">\(([0-9]{4})', filminfo)
				typnazev = self.najdi('<span class="info">.*?<span class="info">\((.*[a-z])\)', filminfo)
				if rok != "":
					celynazev += ' (' + rok + ')'
				if typnazev != "":
					celynazev += ' (' + typnazev + ')'
				self.resultlist += [(celynazev, odkaz, hlavninazev, rok)]

			if self.jmeno2 != "" and self.jmeno2 != " ":
				self["statusbar"].setText(toStr("Hledání v CSFD pro: %s" % (self.nazeveventuproskin)))
				localfile = "/tmp/CSFDquery_dotaz3.html"
				fetchurl = "https://www.csfd.cz/hledat/?q=" + self.jmeno2
				self.puvodniurl = fetchurl
				print("[CSFDLite] Downloading Query " + fetchurl + " to " + localfile)
				dwnpage(fetchurl,localfile).addCallback(self.CSFDquery_dotaz3).addErrback(self.fetchFailed("CSFDquery_dotaz2"))
			else:
				self.projitSeznam()
		else:
			self["detailslabel"].setText(toStr("Dotaz na CSFD nebyl úspěšný"))

	def CSFDquery_dotaz3(self, string):			
		print("[CSFDquery_dotaz3]")
		self["statusbar"].setText(toStr("Stahování z CSFD dokončeno pro %s" % (self.nazeveventuproskin)))
		self.inhtml = (open("/tmp/CSFDquery_dotaz3.html", "r").read())

		if '<h1 itemprop="name">' in self.inhtml:
			odkaz = self.najdi('https://www.csfd.cz/film/(.*?)/', self.inhtml)
			nazevfilmu = self.najdi('<h1 itemprop=\"name\">(.*?)<', self.inhtml)
			nazevfilmu = nazevfilmu.replace("\t","").replace("\n","")
			self.resultlist = [(nazevfilmu, odkaz)]
		elif "SFD.cz </title>" in self.inhtml:
			print("[CSFDLite] ziskavani seznamu 3")
			for odkaz, filmnazev, filminfo in self.hledejVse('<h3.*?<a href="/film/(.*?)".*?"film-title-name">(.*?)</a>(.*?)</h3>', self.inhtml):
				hlavninazev = filmnazev
				celynazev = hlavninazev
				rok = self.najdi('<span class="info">\(([0-9]{4})', filminfo)
				typnazev = self.najdi('<span class="info">.*?<span class="info">\((.*[a-z])\)', filminfo)
				if rok != "":
					celynazev += ' (' + rok + ')'
				if typnazev != "":
					celynazev += ' (' + typnazev + ')'
				self.resultlist += [(celynazev, odkaz, hlavninazev, rok)]
			self.projitSeznam()
		else:
			self["detailslabel"].setText(toStr("Dotaz na CSFD nebyl úspěšný"))

	def projitSeznam(self):	
		print("[CSFDLite] prochazim seznam")
		try:
			self.resultlist = sorted(set(self.resultlist), key=self.resultlist.index)   # odstraneni duplicit v seznamu
			shoda = []
			for nazevinfo, odkaz, nazevfilmu, rok in self.resultlist:
				nazevfilmu = self.odstraneniTagu(nazevfilmu)
				konvertovanynazev = self.removeD(nazevfilmu)
				# for znak in nazevfilmu:
				# 	if ord(znak) > 127:
				# 		znak = "\\x" + znak.encode("hex")
				# 	konvertovanynazev += znak
				if self.malaPismena(self.odstraneniInterpunkce(konvertovanynazev)) == self.malaPismena(self.odstraneniInterpunkce(self.nazeveventu)):
					shoda += [(self.odstraneniTagu(nazevinfo), odkaz, rok)]
			if len(shoda) == 1:
				self.nazevkomplet, self.link, v3 = shoda[0]
				self.unikatni = True
			elif len(shoda) > 1:
				for nazevinfo, odkaz, rok in shoda:
					if self.rokEPG == rok and not self.unikatni:
						self.nazevkomplet, self.link, v3 = self.odstraneniTagu(nazevinfo), odkaz, rok
						self.unikatni = True
			self.resultlist = [(v1, v2) for v1, v2, v3, v4 in self.resultlist]

			if self.resultlist:
				self.resultlist = [(self.odstraneniTagu(nazevinfo), odkaz) for nazevinfo, odkaz in self.resultlist]
				self["menu"].l.setList(self.resultlist)
				self['menu'].moveToIndex(0)
				if len(self.resultlist) == 1 or self.unikatni:
					self.Page = 1
					self.showMenu()
					self.Page = 0
					self["extralabel"].hide()
					self.showDetails()
				elif len(self.resultlist) > 1:
					self.Page = 1
					self.showMenu()
			else:
				self["detailslabel"].setText("Nenalezena informace v CSFD pro %s" % (self.nazeveventuproskin))
				self["statusbar"].setText("Nenalezena informace v CSFD pro %s" % (self.nazeveventuproskin))
			self.kontrolaUpdate()
		except:
			print("/////////// ERROR %s"%traceback.format_exc())

	def CSFDquery2(self, string):
		self["statusbar"].setText(toStr("Stahování informace o filmu dokončeno pro:  %s" % (self.nazevkomplet)))
		self.inhtml = (open("/tmp/CSFDquery2.html", "r").read())
		if 'DOCTYPE html' in self.inhtml:
			self.CSFDparse()
		else:
			self["statusbar"].setText(toStr("Problem pri načítání: %s" % (self.link)))

	def CSFDquery3(self, string):
		self.inhtml2 = (open("/tmp/CSFDquery3.html", "r").read())
		if 'DOCTYPE html' in self.inhtml2:
			self.komentare2 += self.nactiKomentare(self.inhtml2) + toStr("...\n\n(seznam komentářů zkrácen)")
		else:
			self["statusbar"].setText(toStr("Problem pri načítání: %s" % (self.link2)))
		self.zobrazKomentare(self.komentare2)

	def zobrazKomentare(self, vsechnykomentare):
		if vsechnykomentare != "":
			vsechnykomentare = self.odstraneniTagu(vsechnykomentare)
			if len(vsechnykomentare) > self.omezenikomentaru:
				vsechnykomentare = vsechnykomentare[0:self.omezenikomentaru] + "...\n\n(seznam komentářů zkrácen)"
			self["extralabel"].setText(toStr(vsechnykomentare))
			self["extralabel"].hide()
			# razenikomentaru = "↓d"
			# if self.commentsSort == 2:
			# 	razenikomentaru = "↓h"
				
			self["key_blue"].setText(toStr("Komentáře")) # + razenikomentaru))		

	def CSFDparse(self):
		print("[CSFDparse]")
		self.Page = 1
		Detailstext = "Nenalezeny informace o filmu"
		if 'class="film-info"' in self.inhtml:
			self["key_yellow"].setText("Info o filmu")
			self["statusbar"].setText(toStr("Info o filmu z CSFD získáno pro %s" % (self.nazevkomplet)))
			nazevfilmu = self.najdi('film-header-name.*?<h1>\s+(.*?)\s+</h1>', self.inhtml).strip()
			nazevfilmu = nazevfilmu.replace("\t","").replace("\n","")
			typnazev = self.najdi('<span class="type">(.*?)</span>', self.inhtml)
			nazevfilmu += ' ' + typnazev
			nazevfilmu = self.odstraneniTagu(nazevfilmu)
			if len(nazevfilmu) > self.omezeninazvu:
				nazevfilmu = nazevfilmu[0:self.omezeninazvu] + "..."
			self["titlelabel"].setText(nazevfilmu)

			hodnoceni = self.najdi('<div class="rating-average.*?">\s+(.*?)</div>', self.inhtml)
			Ratingtext = "--"
			if hodnoceni != "" and not "?" in hodnoceni:
				Ratingtext = hodnoceni.strip()
				if "%" in Ratingtext:
					self.ratingstars = int(Ratingtext.replace("%",""))
					self["stars"].show()
					self["stars"].setValue(self.ratingstars)
					self["starsbg"].show()
			self["ratinglabel"].setText(Ratingtext)

			if not 'class="empty-image"' in self.inhtml:
				posterurl = ""
				posterurl = self.najdi('class="film-posters".*?src="(.*?)"', self.inhtml)
				if posterurl != "":
					if not "https:" in posterurl:
						posterurl = "https:" + posterurl
					posterurl = posterurl.replace('w140', 'w420')
					self["statusbar"].setText(toStr("Stahování plakátu k filmu: %s" % (posterurl)))
					localfile = "/tmp/poster.jpg"
					print("[CSFDLite] downloading poster " + posterurl + " to " + localfile)
					try:
						dwnpage(posterurl,localfile).addCallback(self.CSFDPoster).addErrback(self.fetchFailed("CSFDparse - poster"))
					except:
						print("no jpg poster!")
						self.CSFDPoster(noPoster = True)					
				else:
					print("no jpg poster!")
					self.CSFDPoster(noPoster = True)
			else:
				print("no jpg poster!")
				self.CSFDPoster(noPoster = True)

			Detailstext = ""
			nazevserialu = serie = ''
			if "epizoda" in typnazev:
				nazevserialu = self.najdi('<header class="film-header">\s+<h2>\s+<a href="/film/.*?/">(.*?)</a>', self.inhtml)
				serie = self.najdi('<header class="film-header">\s+<h2>\s+<a href="/film/.*?/">.*?</a>.*?<a href="/film/.*?/.*?/">(.*?)</a>', self.inhtml)
				nazevserialu = self.odstraneniTagu(nazevserialu)
				serie = self.odstraneniTagu(serie)
			if nazevserialu != '':
				Detailstext += 'Seriál: ' + nazevserialu
				if serie != '':
					Detailstext += ' (' + serie + ')'
				Detailstext += '\n\n'

			nazvy = self.najdi('<ul class="film-names">(.*?)</ul>', self.inhtml)
			if nazvy:
				vysledky = [(v2 + ' (' + v1 + ')') for v1, v2 in self.hledejVse('<li.*?title="(.*?)".*?/>\s+(.*?)\s+<', nazvy)]
				for nazev in vysledky:
					Detailstext += nazev + '\n'
				Detailstext += '\n'

			zanr = self.najdi('<div class="genres">(.*?)</div>', self.inhtml)
			Detailstext += zanr + '\n'

			zemerokdelka = self.najdi('<div class="origin">(.*?)</div>', self.inhtml)
			zemerokdelka = zemerokdelka.replace('<span itemprop="dateCreated">', '').replace('</span>', '').replace('<span>', '')
			zemerokdelka = re.sub('\s+'," ",zemerokdelka)
			Detailstext += zemerokdelka + '\n\n'

			vysilani = self.hledejVse('tv-list">\s+<a href=".*?">(.*?)</a>', self.inhtml)
			if vysilani:
				Detailstext += 'Nejbližší vysílání v TV:\n'
				for termin in vysilani:
					Detailstext += termin + '      '
				Detailstext += '\n\n'

			obory = ['Re\xc5\xbeie', 'P\xc5\x99edloha', 'Sc\xc3\xa9n\xc3\xa1\xc5\x99', 'Kamera','Hudba', 'Hraj\xc3\xad']
			oborytext = ""
			for obor in obory:
				jmena = self.najdi('<h4>' + obor + ': </h4>(.*?)</div>', self.inhtml)
				autori = ""
				for tvurce in self.hledejVse('<a href=".*?">(.*?)</a>', jmena):
					autori += tvurce + ", "
				if autori != "":
					autori = autori[0:len(autori)-2]
					if obor == 'Hrají':
						oborytext += '\n'	
					oborytext += obor + ': ' + autori + '\n'
			Detailstext += oborytext
			if oborytext != "":
				Detailstext += '\n'
				
			obsahy = self.najdi('<div class="body--plots">(.*?)</section>', self.inhtml)
			obsah = self.najdi('<div class="plot-full.*?">\s+<p>\s+(.*?)\s+</p>', obsahy)
			if obsah:
				Detailstext += self.odstraneniTagu(obsah).replace("\t", "").replace("\n\n\n", "    ")
				Detailstext += '\n'
			for obsah in self.hledejVse('<div class="plots-item">\s+<p>\s+(.*?)\s+</p>', obsahy):
				if obsah:
					Detailstext += self.odstraneniTagu(obsah).replace("\t", "").replace("\n\n\n", "    ")
					Detailstext += '\n' 

			Extratext = ""
			pocetkomentaru = self.najdi('<h2>\s+Recenze.*?"count">(.*?)<', self.inhtml)
			if pocetkomentaru != "" and pocetkomentaru != "(0)":
				Extratext += "Komentáře uživatelů k filmu " + pocetkomentaru + '\n\n'
			Extratext += self.nactiKomentare(self.inhtml)
			druhastranka = self.najdi('<div class="pagination">(.*?)</div>', self.inhtml)
			druhastranka = self.najdi('>1</span>\s+<a href="(.*?)">2<', druhastranka)
			if druhastranka:
				self.link2 = druhastranka.replace("&amp;","&")
				self.komentare2 = Extratext
				self["statusbar"].setText(toStr("Stahování 2. stránky komentářů: %s" % (self.link2)))
				localfile = "/tmp/CSFDquery3.html"
				fetchurl = "https://www.csfd.cz" + self.link2
				print("[CSFDLite] downloading query " + fetchurl + " to " + localfile)
				dwnpage(fetchurl,localfile).addCallback(self.CSFDquery3).addErrback(self.fetchFailed("CSFDparse - druha stranka"))
			else:
				self.zobrazKomentare(Extratext)

		self["detailslabel"].setText(toStr(Detailstext))

	def CSFDPoster(self, noPoster = False):
		self["statusbar"].setText(toStr("Info z CSFD získáno pro: %s" % (self.nazevkomplet)))
		if not noPoster:
			filename = "/tmp/poster.jpg"
		else:
			filename = resolveFilename(SCOPE_PLUGINS, "Extensions/CSFDLite/no_poster.png")
		sc = AVSwitch().getFramebufferScale()
		self.picload.setPara((self["poster"].instance.size().width(), self["poster"].instance.size().height(), sc[0], sc[1], False, 1, "#00000000"))
		self.picload.startDecode(filename)

	def paintPosterPixmapCB(self, picInfo=None):
		ptr = self.picload.getData()
		if ptr is not None:
			self["poster"].instance.setPixmap(ptr.__deref__())
			self["poster"].show()

	def createSummary(self):
		return CSFDLCDScreen

	def kontrolaUpdate(self):
		naposledy = '/tmp/CSFDLite_last_update_check'
		if (path.exists(naposledy) and path.isfile(naposledy) and access(naposledy, R_OK)):
			if time.time() - path.getmtime(naposledy) > 86400:
				kontrolovatupdate = True
			else:
				kontrolovatupdate = False
		else:
			kontrolovatupdate = True
		if kontrolovatupdate:
			print("////////// kontrolujem aktualizaciu...")
			open(naposledy, 'w').close()
			self.cisloverze = '/tmp/nova_verze.txt'
			dwnpage('https://raw.githubusercontent.com/skyjet18/enigma2-plugin-extensions-csfdlite/master/version.txt', self.cisloverze).addCallback(self.porovnaniVerze).addErrback(self.fetchFailed("kontrolaUpdate"))

	def removeD(self, text):
		searchExp = text
		try:
			if sys.version_info >= (3, 0, 0):
				import unicodedata
				searchExp = ''.join((c for c in unicodedata.normalize('NFD', searchExp) 
											if unicodedata.category(c) != 'Mn'))
			else:
				if isinstance(searchExp, str):
					return searchExp
				import unicodedata
				searchExp = ''.join((c for c in unicodedata.normalize('NFD', searchExp) 
											if unicodedata.category(c) != 'Mn')).encode('utf-8')
		except:
			print("Remove diacritics '%s' failed.\n%s"%(text,traceback.format_exc()))
			
		return searchExp

	def porovnaniVerze(self, string):
		ver = StrictVersion('')
		if (path.exists(self.cisloverze) and path.isfile(self.cisloverze) and access(self.cisloverze, R_OK)):
			with open(self.cisloverze, 'r') as f:
				ver = StrictVersion(f.read().strip())
			remove(self.cisloverze)
		else:
			self.session.open(MessageBox, toStr("Není k dospozici informace o verzích na githubu"), MessageBox.TYPE_INFO, timeout=30)
		if ver and ver > self.version:
			print("////////// najdena nova verzia pluginu: %s/%s"%(self.version, ver))
			self.koncovkasouboru = 'csfdlite_%s.%s.tar.gz'%(ver.version[0],ver.version[1])
			self.session.openWithCallback(self.provedeniUpdate, MessageBox, "Spustit aktualizaci pluginu CSFDLite na verzi " + str(ver) + "?", MessageBox.TYPE_YESNO)

	def provedeniUpdate(self, odpoved):
		if odpoved:
			if self.kontejnerfunguje:
				dwnpage('https://github.com/skyjet18/enigma2-plugin-extensions-csfdlite/blob/master/releases/' + self.koncovkasouboru+'?raw=true', '/tmp/CSFDLite.tar.gz').addCallback(self.rozbaleniTaru).addErrback(self.fetchFailed("provedeniUpdate"))
			else:
				self.session.open(MessageBox, toStr("Nainstalovaná verze enigmy nemá objekt eConsoleAppContainer, aktualizujte plugin ručně"), MessageBox.TYPE_INFO, timeout=60)

	def rozbaleniTaru(self, string):
		if self.container.execute('tar xvf /tmp/CSFDLite.tar.gz -C /usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/'):
			self.session.open(MessageBox, toStr("Problém s prováděním příkazu v containeru, aktualizace neproběhla"), MessageBox.TYPE_INFO, timeout=30)

	def konecExekuce(self, exitcode):
		if exitcode == 0:
			try:
				zmeny = (open("/usr/lib/enigma2/python/Plugins/Extensions/CSFDLite/version_history.txt", "r").read())
				zmeny = self.najdi('^(.*?)\n[0-9]?[0-9].[0-9]?[0-9]', zmeny)
			except: 
				zmeny = ""
			self.session.open(MessageBox, toStr("Aktualizace proběhla, restartujte enigmu. Změny v poslední verzi:\n\n") + zmeny, MessageBox.TYPE_INFO, timeout=30)
		else:
			self.session.open(MessageBox, toStr("Problém s aktualizací, neexistuje tar nebo se špatně stáhl soubor"), MessageBox.TYPE_INFO, timeout=30)

	def __onClose(self):
		del self.picload_conn
		del self.picload
		self.close()

class CSFDLCDScreen(Screen):
	skin = """
	<screen position="0,0" size="132,64" title="CSFD Lite">
		<widget name="headline" position="4,0" size="128,22" font="Regular;16"/>
	</screen>"""
	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["headline"] = Label("CSFD Lite")

# try replace IMDB plugin with this
replaceImdb()

def eventinfo(session, servicelist, **kwargs):
	ref = session.nav.getCurrentlyPlayingServiceReference()
	session.open(CSFDEPGSelection, ref)

def movielist(session, service, **kwargs):
	serviceHandler = eServiceCenter.getInstance()
	info = serviceHandler.info(service)
	popis = info.getInfoString(service, iServiceInformation.sDescription) or ""
	name = info and info.getName(service) or ''
	eventName = name.split(".")[0].strip()
	session.open(CSFDLite, eventName, popis)

def main(session, eventName="", popis = "", **kwargs):
	session.open(CSFDLite, eventName, popis)

def Plugins(**kwargs):
	try:
		return [PluginDescriptor(name = "CSFDLite",
				description = "CSFD Lite",
				icon = "csfd.png",
				where = PluginDescriptor.WHERE_PLUGINMENU,
				fnc = main),
				PluginDescriptor(name = "CSFDLite",
				description = "CSFD Lite",
				where = PluginDescriptor.WHERE_EVENTINFO,
				fnc = main),
				PluginDescriptor(name = "CSFDLite",
				description = "CSFD Lite",
				where = PluginDescriptor.WHERE_EXTENSIONSMENU,
				fnc = main),
				PluginDescriptor(name = "CSFDLite",
				description = "CSFD Lite",
				where = PluginDescriptor.WHERE_MOVIELIST,
				fnc = movielist)
				]
	except AttributeError:
		wherelist = [PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_PLUGINMENU]
		return PluginDescriptor(name="CSFDLite",
				description="CSFD Lite",
				icon="csfd.png",
				where = wherelist,
				fnc=main)
