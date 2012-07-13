ReaLay
------

ReaLay is a plugin for the Reaper DAW that works in conjunction with Dropbox to allow seamless collaboration of Reaper projects. Press a button and start where your friends left off.

See the UserGuide for an illustrated tutorial.


What It Does
------------
* Allows any number of people to collaborate on Reaper projects one at a time with an exclusive checkout lock type of system
* Gives you some redundancy/backup for free thanks to Dropbox file versioning
* Removes the need for any manual intervention to move files around for syncing

Requirements
------------
* Python 3.1+
* Dropbox
* Each collaborator to have VERY similar Reaper setups (same plugins, etc)
* Some conventions (a .RPP filename which matches the project directory, centralized location for local/remote mirror, etc)
* That you NEVER edit your local project without first checking it out

Installation
------------
1. Copy this script to the `[reaper local config]/Scripts` directory
2. Create a realay-prefs.py file in the same directory (use `realay-prefs.example.py` as a reference)
3. Invoke the plugin as a ReaScript action bound to whatever UI trigger you want (e.g., a toolbar button)

Using ReaLay
------------
In the test demonstrated below, I am using a temporary directory and some sample projects. In real use, the remote directory is a Dropbox folder shared between myself and my collaborator ("James"). This is what keeps all the project metadata in sync between collaborators and facilitates the entire system.

*Disclaimers* (they are numerous):

* I've done some pretty extensive testing of the thing (including via dropbox with another human), and it has numerous safety features to prevent the user from screwing anything up. 
* The UI is visually a trainwreck, as this is the first time I've ever touched Tkinter. 
* Python is absolutely not my primary programming language, so it may be difficult to extend
* It needs a small bit of work to address portability issues (mainly with the RPP processing making some assumptions about Windows 7's user directory path). 
* It does make destructive changes to your local disk, including deleting entire trees for syncing, which I tried to make as safe as possible with things such as the confirmation dialog which tells you what it's going to do. 
* There is extensive logging which can be enabled with a debug mode. There are likely all sorts of bugs yet to be discovered. There are probably tons of race conditions that would be exposed if lots of people were collaborating and doing lots of checkins/checkouts simultaneously.

Hopefully somebody else will find it useful.

### Step 1 ###

Create your shared projects in the dropbox folder. _All media must be in the project directory_. Portable project files are key. They'll then appear in ReaLay as "non-projects."

### Step 2 ###

Open ReaLay

`(todo: find/add old image)`

### Step 3 ###

Select your new project directory, and make it a ReaLay project.

`(todo: find/add old image)`

### Step 4 ###

At this point, every collaborator will see the new project (thanks to Dropbox synchronizing the metadata). Anybody can now check out the project.

`(todo: find/add old image)`

### Step 5 ###

When checking out, you'll be prompted to confirm as the operation is destructive. Whatever's in the master version will by synced to your local project directory (which will be created if it doesn't exist). This step tries its best to post-process the local `.RPP` file to massage paths to your local configuration.

`(todo: find/add old image)`

### Step 6 ###

The project is now checked out *exclusively to you*. Nobody else can check it out until you check it back in. It's now time to open up your local version of the project and do some recording.

`(todo: find/add old image)`

### Step 7 ###

Now you've finished making your changes, so you open ReaLay to check them back in. As you can see, while we were working, somebody added a new project, and `James` started working on another. Select your project and check it in.

`(todo: find/add old image)`

### Step 8 ###

You'll be prompted to confirm, as this will replace the `master` project with your local copy.

`(todo: find/add old image)`

As an added safety measure, ReaLay will attempt to close all open projects prior to checkin, to give you an opportunity to save or discard any remaining local changes you may have outstanding.

`(todo: find/add old image)`

### Step 9 ###

All done! Your changes are pushed out to Dropbox and there is a new master copy for anybody else to check out and work with.

`(todo: find/add old image)`