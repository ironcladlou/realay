# ReaLay: Internet collaboration for Reaper (http://www.reaper.fm)
# by Dan Mace (ironcladlou@gmail.com)
# http://code.google.com/p/realay/
#
# Installation:
# 1. Copy this script to the [Reaper Local Config]/Scripts directory
# 2. Create a realay-prefs.py file in the same directory
# 3. Invoke the script as a ReaScript action bound to whatever UI trigger you want

import os
import tkinter
import pickle
import sys
import traceback
import distutils.dir_util
import re
import json
from tkinter import *

sys.argv=["Main"]

# Constants
COMMAND_CLOSE_ALL_PROJECTS=40886
APP_NAME = "ReaLay"

def safelog(msg):
	RPR_ShowConsoleMsg(str(msg) + "\n")

class Prefs:
	defaults = {
		"debug": False
	}

	def __init__(self, userprefs):
		self.prefs = Prefs.defaults.copy()
		self.prefs.update(userprefs)

		for k, v in self.prefs.items():
			self.__dict__[k] = v

class Logger:
	def __init__(self, prefs):
		self.prefs = prefs

		Logger.instance = self
	
	@staticmethod
	def log(msg):
		Logger.instance.loginternal(msg)

	def loginternal(self, msg):
		if (self.prefs.debug):
			RPR_ShowConsoleMsg(str(msg) + "\n")

class ProjectMeta:
	defaults = {
		"notes": [],
		"lastModifiedBy": None,
		"lastUpdatedDate": None,
		"checkoutBy": None,
		"checkoutDate": None,
		"status": "ready"
	}

	def __init__(self):
		self.meta = ProjectMeta.defaults.copy()

		for k, v in self.meta.items():
			self.__dict__[k] = v

class ProjectAlreadyCheckedOutException(Exception):
	pass

class ProjectNotCheckedOutException(Exception):
	pass

class ProjectCreationException(Exception):
	pass
	
class Project():
	META_FILENAME = "realay.dat"

	@staticmethod
	def isProject(path):
		return os.path.isfile(os.path.join(path, Project.META_FILENAME))

	@staticmethod	
	def create(path):
		"""Creates a new Project from a Reaper project directory.

		The directory must contain a .RPP file whose name matches the parent directory.

		Arguments:
		path -- where to create the project

		Throws:
		ProjectCreationException -- if the target directory doesn't appear to be valid to us

		"""

		Logger.log("!creating new project at " + path)

		if Project.isProject(path):
			raise ProjectCreationException("There appears to already be a project at " + path)

		rpp = os.path.join(path, os.path.basename(path) + ".rpp")
		if not os.path.isfile(rpp):
			raise ProjectCreationException("Expected RPP file at " + rpp)

		Logger.log("creating new project at " + path)

		metafile = None
		try:
			metafilename = os.path.join(path, Project.META_FILENAME)
			Logger.log("creating new project with metafile " + metafilename)

			metafile = open(metafilename, "wb")
			pickle.dump(ProjectMeta(), metafile)
		finally:
			if metafile: metafile.close()


	def __init__(self, path=None):
		self.name = os.path.basename(path)
		self.path = path
		self.metafile = os.path.join(path, Project.META_FILENAME)

		if not os.path.isfile(self.metafile):
			raise "No project meta found at " + self.metafile

		Logger.log("loading project %s from %s" % (self.name, self.metafile))

		self.refresh();

		Logger.log("loaded project %s" % self.name)

	def refresh(self):
		"""Reloads the project's metadata from disk."""

		if not os.path.isfile(self.metafile):
			raise RuntimeError("Tried to refresh, but metafile has disappeared from " + self.metafile)

		Logger.log("refreshing project %s from metafile %s" % (self.name, self.metafile))
		
		mf = None
		try:
			mf = open(self.metafile, "rb")
			self.meta = pickle.load(mf)
		finally:
			if mf: mf.close()

	def __writemeta(self):
		"""Serializes the project's current metadata to disk"""

		Logger.log("writing metafile for " + self.name)
		f = open(self.metafile, "wb")
		pickle.dump(self.meta, f)
		Logger.log("successfully wrote metafile to " + self.metafile)

	def checkout(self, user, localpath):
		"""Checks out the current project and processes the project's local RPP.

		Arguments:
		user -- the user trying to perform the checkout
		localpath -- the local project directory

		Throws:
		ProjectAlreadyCheckedOutException -- if the project is already checked out

		"""

		# make sure our project data isn't stale
		self.refresh()

		if self.meta.status == "checkout":
			raise ProjectAlreadyCheckedOutException("project %s is already checked out by %s" % (self.name, self.meta.checkoutBy))

		Logger.log("checking out %s as %s" % (self.name, user))

		self.meta.checkoutBy = user
		self.meta.status = "checkout"

		# write meta up-front
		self.__writemeta()

		# blast the local copy
		if (os.path.exists(localpath)):
			Logger.log("removing local project files from " + localpath)
			distutils.dir_util.remove_tree(localpath)
		
		Logger.log("copying project from %s to %s" % (self.path, localpath))

		# copy from remote to local
		distutils.dir_util.copy_tree(self.path, localpath)

		# remove the metadata file, we don't want to blast it
		# when we check back in. this seems silly, but i couldn't
		# figure out how to apply a filter to copy_tree in 2 minutes.
		os.remove(os.path.join(localpath, Project.META_FILENAME))

		# process the RPP
		rpp = os.path.join(localpath, self.name + ".rpp")

		self.__localizeRpp(rpp, user)
		
		Logger.log("checkout complete")

	def __localizeRpp(self, rpp, user):
		"""Rewrites an RPP to convert any paths to their local equivalents.

		Current implementation is completely retarded and coupled to Windows7.

		"""

		Logger.log("Post-processing RPP: " + rpp)
		
		tmp = rpp + ".tmp"

		fin = open(rpp)
		fout = open(tmp, "wt")
		for line in fin:
			# awful
		    fout.write(re.sub('\\\\Users\\\\(\\w+)\\\\', "\\\\Users\\\\%s\\\\" % user, line))
		fin.close()
		fout.close()

		# remove original, replace with temp
		os.remove(rpp)
		os.rename(tmp, rpp)

	def checkin(self, user, localpath):
		"""Checks in the current project, overwriting the project's remote state with the local.

		Arguments:
		user -- the user trying to perform the checkin
		localpath -- the local project directory

		Throws:
		ProjectNotCheckedOutException -- if the project isn't checked out, or if user isn't the checkout holder

		"""

		# make sure our project data isn't stale
		self.refresh()

		if self.meta.status == "ready":
			raise ProjectNotCheckedOutException("project %s isn't checked out" % self.name)

		if self.meta.checkoutBy and self.meta.checkoutBy.lower() != user.lower():
			raise ProjectNotCheckedOutException("current user %s is not the checkout owner (%s)" % (user, self.meta.checkoutBy))

		Logger.log("checking in %s" % self.name)
		self.meta.checkoutBy = None
		self.meta.status = "ready"

		# write the meta up-front
		self.__writemeta()

		# copy from local to dropbox
		Logger.log("coping local project from %s to %s" % (localpath, self.path))
		distutils.dir_util.copy_tree(localpath, self.path)

		Logger.log("checkin complete")


class ReaLayGui(Tk):
	def AddEnv(self):
		pass
 
	def createWidgets(self):
		self.grid()
		self.grid_columnconfigure(0, weight=1)
		self.grid_rowconfigure(0, weight=1)

		self.projListbox = Listbox(self, selectmode=SINGLE)
		self.projListbox.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S)

		self.refreshButton = Button(self, text="Refresh Projects", command=self.refreshProjects)
		self.refreshButton.grid(row=1, column=0, sticky=W)

		self.createProjButton = Button(self, text="Create Project", command=self.createProject)
		self.createProjButton.grid(row=1, column=1)

		self.checkoutButton = Button(self, text="Checkout", command=self.checkout)
		self.checkoutButton.grid(row=1, column=2)

		self.checkinButton = Button(self, text="Check In", command=self.checkin)
		self.checkinButton.grid(row=1, column=3)

		self.nonprojListbox = Listbox(self, selectmode=SINGLE, width=60, height=5)
		self.nonprojListbox.grid(row=2, column=0, columnspan=4, sticky=W+E+N+S)
		

	def __init__(self, parent=None, prefs=None):
		Tk.__init__(self, parent)
		
		# give us a chance to process event handler exceptions
		self._root().report_callback_exception = self.handleCallbackError

		self.parent = parent
		self.prefs = prefs
		self.projects = []
		self.nonprojects = []

		self.createWidgets()

		self.refreshProjects()

	def handleCallbackError(*args):
		a = traceback.format_exception(*args)
		Logger.log("\n".join(a[:-1]))

	def refreshProjects(self):
		Logger.log("refreshing project list")
		
		self.projects = []
		self.nonprojects = []
		self.projListbox.delete(0, END)
		self.nonprojListbox.delete(0, END)

		for f in os.listdir(self.prefs.dropbox):
			path = os.path.join(self.prefs.dropbox, f)
			
			if Project.isProject(path):
				try:
					project = Project(path)
					self.projects.append(project)
				except Exception as e:
					Logger.log("Error loading project from %s: %s" % (path, str(e)))
			else:
				Logger.log("adding nonproject " + path)
				self.nonprojects.append(path)

		for p in self.projects:
			checkoutStatus = "ready for checkout"

			if p.meta.status == "checkout":
				checkoutStatus = "checked out by " + p.meta.checkoutBy

			label = "[project] %s (%s)" % (p.name, checkoutStatus)

			self.projListbox.insert(END, label)
		
		for p in self.nonprojects:
			self.nonprojListbox.insert(END, "[non-project] " + p)
	
	def selectedListItem(self, listbox, adict):
		selections = listbox.curselection()
		
		if len(selections) == 0:
			return None
		
		index = int(selections[0])
		return adict[index]

	def selectedProject(self):
		return self.selectedListItem(self.projListbox, self.projects)

	def selectedNonproject(self):
		return self.selectedListItem(self.nonprojListbox, self.nonprojects)

	def createProject(self):
		path = self.selectedNonproject()

		# no selection
		if path == None: return

		try:
			Project.create(path)
		except ProjectCreationException as e:
			Logger.log("Couldn't create project: " + str(e))
		
		self.refreshProjects()

	def checkout(self):
		project = self.selectedProject()

		# no selection
		if project == None: return

		# build the local path
		localpath = os.path.join(self.prefs.local, project.name)

		# prompt the user to make sure
		confirm = ConfirmationDialog(
			parent=self, 
			message="Really check out %s? Your local copy will be obliterated and replaced with what's in the dropbox.\nLocal copy: %s\nDropbox copy: %s" % (project.name, localpath, project.path)
		)
		
		if not confirm.result: return

		# do the checkout
		try:
			project.checkout(self.prefs.user, localpath)
		except ProjectAlreadyCheckedOutException as e:
			Logger.log("Couldn't perform checkout: " + str(e))

		# either way, refresh the list
		self.refreshProjects()

	def checkin(self):
		project = self.selectedProject()
		
		# no selection
		if project == None: return

		# build local project path
		localpath = os.path.join(self.prefs.local, project.name)

		# prompt the user to make sure
		confirm = ConfirmationDialog(
			parent=self, 
			message="Really check in %s? This will replace whatever's in dropbox.\nLocal copy: %s\nDropbox copy: %s" % (project.name, localpath, project.path)
		)
		
		if not confirm.result: return
		
		# close all projects before checkin
		RPR_Main_OnCommand(COMMAND_CLOSE_ALL_PROJECTS, 0)

		try:
			project.checkin(self.prefs.user, localpath)
		except ProjectNotCheckedOutException as e:
			Logger.log("Couldn't perform checkin: " + str(e))

		# either way, refresh
		self.refreshProjects()


class ConfirmationDialog(Toplevel):
	def __init__(self, parent = None, title = "Confirm", message = "Confirm", confirmButtonText="Confirm", cancelButtonText="Cancel"):
		Toplevel.__init__(self, parent)
		self.transient(parent)

		self.title(title)

		self.message = message
		self.confirmButtonText = confirmButtonText
		self.cancelButtonText = cancelButtonText
		self.parent = parent

		self.result = None

		body = Frame(self)
		self.initial_focus = self.body(body)
		body.pack(padx=5, pady=5)

		self.buttonbox()

		self.grab_set()

		if not self.initial_focus:
			self.initial_focus = self

		self.protocol("WM_DELETE_WINDOW", self.cancel)

		self.geometry("+%d+%d" % (parent.winfo_rootx()+50,
								  parent.winfo_rooty()+50))

		self.initial_focus.focus_set()

		self.wait_window(self)

	def body(self, master):
		l = Label(master, text=self.message)
		l.pack()

	def buttonbox(self):
		box = Frame(self)

		w = Button(box, text=self.confirmButtonText, width=10, command=self.ok, default=ACTIVE)
		w.pack(side=LEFT, padx=5, pady=5)
		w = Button(box, text=self.cancelButtonText, width=10, command=self.cancel)
		w.pack(side=LEFT, padx=5, pady=5)

		self.bind("<Return>", self.cancel)
		self.bind("<Escape>", self.cancel)

		box.pack()

	def ok(self, event=None):
		self.result = True

		# put focus back to the parent window
		self.parent.focus_set()
		self.destroy()

	def cancel(self, event=None):
		self.result = False
		
		# put focus back to the parent window
		self.parent.focus_set()
		self.destroy()


########################
# bootstrap the GUI
########################

gui = None

try:
	# initialize user prefs
	prefs = None
	
	try:
		prefs_path = os.path.join(os.path.expanduser("~"), ".realayprefs")
		prefs_file = open(prefs_path, encoding="utf-8")
		prefs_hash = json.load(prefs_file)
		prefs = Prefs(prefs_hash)
	except Exception as ex:
		raise Exception("Couldn't load preferences from ~/.realayprefs")

	# initialize logger
	logger = Logger(prefs)

	logger.log("initializing")
	
	# create the gui
	gui = ReaLayGui(parent=None, prefs=prefs)
	gui.title(APP_NAME)

	logger.log("starting GUI")

	# launch the gui
	gui.mainloop()

	logger.log("exiting gracefully")
except Exception as ex:
	safelog("exiting due to exception: " + str(ex))
	raise
finally:
	try:
		if gui: gui.destroy()
	except:
		pass
