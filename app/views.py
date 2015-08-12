#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# -*- coding: utf-8 -*-


from django.http import HttpResponseRedirect, HttpResponseNotFound
from django.http import HttpResponse, HttpResponseServerError
from django.core.context_processors import csrf
from django.core.cache import cache
from django.shortcuts import render_to_response
from django.template import RequestContext as RC
from django.template import Context, loader
from django.contrib.auth import logout, login, authenticate
from django.utils.translation import ugettext as _
from app.models import Project, Dashboard, Attribute
from app.models import Dead, Sprite, Mastery, Duplicate, File
from app.forms import UploadFileForm, UserForm, NewUserForm, UrlForm
from django.contrib.auth.models import User
from datetime import datetime, date
import os
import ast
import json
import sys
import urllib2
import shutil
import csv
import zipfile
from zipfile import ZipFile

# Global variables
pMastery = "hairball -p mastery.Mastery "
pDuplicateScript = "hairball -p duplicate.DuplicateScripts "
pSpriteNaming = "hairball -p convention.SpriteNaming "
pDeadCode = "hairball -p blocks.DeadCode "
pInitialization = "hairball -p initialization.AttributeInitialization "


# ########################### MAIN #############################

def main(request):
    """Main page"""
    if request.user.is_authenticated():
        user = request.user.username
    else:
        user = None
    # The first time one user enters
    # Create the dashboards associated to users
    createDashboards()
    return render_to_response('main/main.html',
                              {'user': user},
                              RC(request))


def redirectMain(request):
    """Page not found redirect to main"""
    return HttpResponseRedirect('/')

# ############################# ERROR ###############################

def error404(request):
    response = render_to_response('404.html', {},
                                  context_instance = RC(request))
    response.status_code = 404
    return response


def error505(request):
    response = render_to_response('500.html', {},
                                  context_instance = RC(request))
    return response

# ##################### TO UNREGISTERED USER ########################

def selector(request):
    if request.method == 'POST':
        print request.POST
        error = False
        id_error = False
        no_exists = False
        if '_url' in request.POST:
            d = urlUnregistered(request)
            if d['Error'] == 'analyzing':
                return render_to_response('error/analyzing.html',
                                          RC(request))
            elif d['Error'] == 'MultiValueDict':
                error = True
                return render_to_response('main/main.html',
                            {'error':error},
                            RC(request))
            elif d['Error'] == 'id_error':
                id_error = True
                return render_to_response('main/main.html',
                            {'id_error':id_error},
                            RC(request))
            elif d['Error'] == 'no_exists':
                no_exists = True
                return render_to_response('main/main.html',
                    {'no_exists':no_exists},
                    RC(request))
            else:
                if d["mastery"]["points"] >= 15:
                    return render_to_response("upload/dashboard-unregistered.html", d)
                elif d["mastery"]["points"] > 7:
                    return render_to_response("upload/dashboard-unregistered.html", d)
                else:
                    return render_to_response("upload/dashboard-unregistered.html", d)
    else:
        return HttpResponseRedirect('/')


def handler_upload(fileSaved, counter):
    """ Necessary to uploadUnregistered"""
    # If file exists,it will save it with new name: name(x)
    if os.path.exists(fileSaved):
        counter = counter + 1
        #Check the version of Scratch 1.4Vs2.0
        version = checkVersion(fileSaved)
        if version == "2.0":
            if counter == 1:
                fileSaved = fileSaved.split(".")[0] + "(1).sb2"
            else:
                fileSaved = fileSaved.split('(')[0] + "(" + str(counter) + ").sb2"
        else:
            if counter == 1:
                fileSaved = fileSaved.split(".")[0] + "(1).sb"
            else:
                fileSaved = fileSaved.split('(')[0] + "(" + str(counter) + ").sb"


        file_name = handler_upload(fileSaved, counter)
        return file_name
    else:
        file_name = fileSaved
        return file_name


def checkVersion(fileName):
    extension = fileName.split('.')[-1]
    if extension == 'sb2':
        version = '2.0'
    else:
        version = '1.4'
    return version


# _______________________Project Analysis Project___________________#

def uploadUnregistered(request):
    """Upload file from form POST for unregistered users"""
    if request.method == 'POST':
        #Revise the form in main
        #If user doesn't complete all the fields,it'll show a warning
        try:
            file = request.FILES['zipFile']
        except:
            d = {'Error': 'MultiValueDict'}
            return  d

        # Create DB of files
        now = datetime.now()
        fileName = File (filename = file.name.encode('utf-8'), method = "project" , time = now)
        fileName.save()
        dir_zips = os.path.dirname(os.path.dirname(__file__)) + "/uploads/"

        # Version of Scratch 1.4Vs2.0
        version = checkVersion(fileName.filename)
        if version == "1.4":
            fileSaved = dir_zips + str(fileName.id) + ".sb"
        else:
            fileSaved = dir_zips + str(fileName.id) + ".sb2"

        # Create log
        pathLog = os.path.dirname(os.path.dirname(__file__)) + "/log/"
        logFile = open (pathLog + "logFile.txt", "a")
        logFile.write("FileName: " + str(fileName.filename) + "\t\t\t" + "ID: " + \
        str(fileName.id) + "\t\t\t" + "Method: " + str(fileName.method) + "\t\t\t" + \
        "Time: " + str(fileName.time) + "\n")

        # Save file in server
        counter = 0
        file_name = handler_upload(fileSaved, counter)

        with open(file_name, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        #Create 2.0Scratch's File
        file_name = changeVersion(request, file_name)

        # Analyze the scratch project
        try:
            d = analyzeProject(request, file_name)
        except:
            #There ir an error with kutz or hairball
            #We save the project in folder called error_analyzing
            fileName.method = 'project/error'
            fileName.save()
            oldPathProject = fileSaved
            newPathProject = fileSaved.split("/uploads/")[0] + \
                             "/error_analyzing/" + \
                             fileSaved.split("/uploads/")[1]
            shutil.copy(oldPathProject, newPathProject)
            d = {'Error': 'analyzing'}
            return d
        # Show the dashboard
        # Redirect to dashboard for unregistered user
        d['Error'] = 'None'
        return d
    else:
        return HttpResponseRedirect('/')

def changeVersion(request, file_name):
        p = kurt.Project.load(file_name)
        p.convert("scratch20")
        p.save()
        file_name = file_name.split('.')[0] + '.sb2'
        return file_name

# _______________________URL Analysis Project_________________________________#


def urlUnregistered(request):
    """Process Request of form URL"""
    if request.method == "POST":
        form = UrlForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['urlProject']
            idProject = processStringUrl(url)
            print "Project to analyze:", idProject
            if idProject == "error":
                d = {'Error': 'id_error'}
                return d
            else:
                try:
                    (pathProject, file) = sendRequestgetJSON(idProject)
                except: #WHEN YOUR PROJECT DOESN'T EXIST
                    d = {'Error': 'no_exists'}
                    return d
                try:
                    d = analyzeProject(request, pathProject)
                except IndentationError: # FIXME
                    #There ir an error with kutz or hairball
                    #We save the project in folder called error_analyzing
                    print "Something went wrong"
                    file.method = 'url/error'
                    file.save()
                    oldPathProject = pathProject
                    newPathProject = pathProject.split("/uploads/")[0] + \
                                     "/error_analyzing/" + \
                                     pathProject.split("/uploads/")[1]
                    shutil.copy(oldPathProject, newPathProject)
                    d = {'Error': 'analyzing'}
                    return d
                # Redirect to dashboard for unregistered user
                d['Error'] = 'None'
                return d
        else:
            d = {'Error': 'MultiValueDict'}
            return  d
    else:
        return HttpResponseRedirect('/')


def processStringUrl(url):
    """Process String of URL from Form
    
    We allow URLs fof the type:
    http://login.pencilcode.net/edit/project
    
    Responds the JSON URL
    or "error" else
    """
    idProject = ''
    protocol, blank, server, edit, name = url.split('/')
    if protocol != "http:":
        return "error"
    login, pencilcode, net = server.split('.')
    if pencilcode != "pencilcode" or net != "net":
        return "error"
    idProject = protocol + '/' + blank + '/' + server + '/' + "load" + '/' + name
    return idProject

def sendRequestgetJSON(idProject):
    """First request to getJSON"""
    fileURL = idProject + ".json"

    # Create DB of files
    now = datetime.now()
    fileName = File (filename = fileURL, method = "url", time = now)
    fileName.save()
    dir_zips = os.path.dirname(os.path.dirname(__file__)) + "/uploads/"
    fileSaved = dir_zips + str(fileName.id) + ".json"
    pathLog = os.path.dirname(os.path.dirname(__file__)) + "/log/"
    logFile = open (pathLog + "logFile.txt", "a")
    logFile.write("FileName: " + str(fileName.filename) + "\t\t\t" + "ID: " + \
    str(fileName.id) + "\t\t\t" + "Method: " + str(fileName.method) + "\t\t\t" + \
    "Time: " + str(fileName.time) + "\n")

    # Save file in server
    counter = 0
    file_name = handler_upload(fileSaved, counter)
    outputFile = open(file_name, 'wb')
    print "Retrieving: ", idProject
    jsonFile = urllib2.urlopen(idProject)
    outputFile.write(jsonFile.read())
    outputFile.close()
    return (file_name, fileName)

# ________________________ LEARN MORE __________________________________#

def learn(request):
    if request.user.is_authenticated():
        return render_to_response("learn/learn-unregistered.html",
                                RC(request))
    else:
        return render_to_response("learn/learn-unregistered.html",
                                RC(request))

# ________________________ TO REGISTERED USER __________________________#

def loginUser(request):
    """Log in app to user"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect('/myDashboard')
            else:
                flag = True
                return render_to_response("main/main.html",
                                            {'flag': flag},
                                            context_instance=RC(request))

    else:
        return HttpResponseRedirect("/")


def logoutUser(request):
    """Method for logging out"""
    logout(request)
    return HttpResponseRedirect('/')

def createUser(request):
    """Method for to sign up in the platform"""
    logout(request)
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            nickName = form.cleaned_data['nickname']
            emailUser = form.cleaned_data['emailUser']
            passUser = form.cleaned_data['passUser']
            user = User.objects.create_user(nickName, emailUser, passUser)
            return render_to_response("profile.html", {'user': user}, context_instance=RC(request))

# ________________________ PROFILE ____________________________#


def updateProfile(request):
    """Update the pass, email and avatar"""
    if request.user.is_authenticated():
        user = request.user.username
    else:
        user = None
    if request.method == "POST":
        form = UpdateForm(request.POST)
        if form.is_valid():
            newPass = form.cleaned_data['newPass']
            newEmail = form.cleaned_data['newEmail']
            choiceField = forms.ChoiceField(widget=forms.RadioSelect())
            return HttpResponseRedirect('/mydashboard')
        else:
            return HttpResponseRedirect('/')


def changePassword(request, new_password):
    """Change the password of user"""
    user = User.objects.get(username=current_user)
    user.set_password(new_password)
    user.save()

# ________________________ DASHBOARD ____________________________#

def createDashboards():
    """Get users and create dashboards"""
    allUsers = User.objects.all()
    for user in allUsers:
        try:
            newdash = Dashboard.objects.get(user=user)
        except:
            fupdate = datetime.now()
            newDash = Dashboard(user=user.username, frelease=fupdate)
            newDash.save()

def myDashboard(request):
    """Dashboard page"""
    if request.user.is_authenticated():
        user = request.user.username
        # The main page of user
        # To obtain the dashboard associated to user
        mydashboard = Dashboard.objects.get(user=user)
        projects = mydashboard.project_set.all()
        beginner = mydashboard.project_set.filter(level="beginner")
        developing = mydashboard.project_set.filter(level="developing")
        advanced = mydashboard.project_set.filter(level="advanced")
        return render_to_response("myDashboard/content-dashboard.html",
                                    {'user': user,
                                    'beginner': beginner,
                                    'developing': developing,
                                    'advanced': advanced,
                                    'projects': projects},
                                    context_instance=RC(request))
    else:
        user = None
        return HttpResponseRedirect("/")

def myProjects(request):
    """Show all projects of dashboard"""
    if request.user.is_authenticated():
        user = request.user.username
        mydashboard = Dashboard.objects.get(user=user)
        projects = mydashboard.project_set.all()
        return render_to_response("myProjects/content-projects.html",
                                {'projects': projects},
                                context_instance=RC(request))
    else:
        return HttpResponseRedirect("/")


def myRoles(request):
    """Show the roles in Doctor Scratch"""
    if request.user.is_authenticated():
        user = request.user.username
        return render_to_response("myRoles/content-roles.html",
                                context_instance=RC(request))
    else:
        return HttpResponseRedirect("/")


def myHistoric(request):
    """Show the progress in the application"""
    if request.user.is_authenticated():
        user = request.user.username
        mydashboard = Dashboard.objects.get(user=user)
        projects = mydashboard.project_set.all()
        return render_to_response("myHistoric/content-historic.html",
                                    {'projects': projects},
                                    context_instance=RC(request))
    else:
        return HttpResponseRedirect("/")

# _______________________ AUTOMATIC ANALYSIS _________________________________#

def analyzeProject(request, file_name):
    dictionary = {}
    if os.path.exists(file_name):
        list_file = file_name.split('(')
        if len(list_file) > 1:
            file_name = list_file[0] + '\(' + list_file[1]
            list_file = file_name.split(')')
            file_name = list_file[0] + '\)' + list_file[1]

        # Request to coffeelint
        with open(file_name) as data_file:    
            data = json.load(data_file)

        with open(file_name.replace(".json", ".coffee"), "w") as coffee_file:    
            coffee_file.write(data["data"])

        metricMastery = "python /home/grex/libresoft/2015-dbau/coffee-mastery/coffee-mastery.py " + file_name.replace(".json", ".coffee")
        print "Running", metricMastery
        try:
            resultMastery = os.popen(metricMastery).read()
        except:
            print "error en mastery"

        metricLint = "coffeelint --reporter raw " + file_name.replace(".json", ".coffee")
        print "Running", metricLint
        try:
            resultLint = os.popen(metricLint).read()
        except:
            print "error en lint"
            
        # Create a dictionary with necessary information
        dictionary.update(procMastery(request, resultMastery))
        dictionary.update(procLint(request, resultLint))

        return dictionary
    else:
        return HttpResponseRedirect('/')


# __________________________ JSON Analyzer _____________________________#



# __________________________ PROCESSORS _____________________________#

def procMastery(request, lines):
    """Mastery"""
    print "In procMastery"
    dic = {}
    lint_data = json.dumps(lines)
    
    dic["mastery"] = {}
    dic["mastery"]["points"] = 5
    dic["mastery"]["maxi"] = 21
    return dic


def procLint(request, lines):
    """Lint"""
    print "In procLint"
    dic = {}
    lint_data = json.dumps(lines)
    
    dic["lint"] = {}
    dic["lint"]["points"] = 3
    dic["lint"]["maxi"] = 25
    return dic


# _____________________ CREATE STATS OF ANALYSIS PERFORMED ___________#

def createStats(file_name, dictionary):
    flag = True


    return flag

# ___________________________ UNDER DEVELOPMENT _________________________#

# UNDER DEVELOPMENT: Children!!!Carefull
def registration(request):
    """Registration a user in the app"""
    return render_to_response("formulary.html")


# UNDER DEVELOPMENT: Children!!!Carefull
def profileSettings(request):
    """Main page for registered user"""
    return render_to_response("profile.html")

# UNDER DEVELOPMENT:
# TO REGISTERED USER
def uploadRegistered(request):
    """Upload and save the zip"""
    if request.user.is_authenticated():
        user = request.user.username
    else:
        return HttpResponseRedirect('/')

    if request.method == 'POST':
        form = UploadFileForm(request.POST)
        # Analyze the scratch project and save in our server files
        fileName = handle_uploaded_file(request.FILES['zipFile'])
        # Analize project and to save in database the metrics
        d = analyzeProject(request, fileName)
        fupdate = datetime.now()
        # Get the short name
        shortName = fileName.split('/')[-1]
        # Get the dashboard of user
        myDashboard = Dashboard.objects.get(user=user)
        # Save the project
        newProject = Project(name=shortName, version=1, score=0, path=fileName, fupdate=fupdate, dashboard=myDashboard)
        newProject.save()
        # Save the metrics
        dmaster = d["mastery"]
        newMastery = Mastery(myproject=newProject, abstraction=dmaster["Abstraction"], paralel=dmaster["Parallelization"], logic=dmaster["Logic"], synchronization=dmaster["Synchronization"], flowcontrol=dmaster["FlowControl"], interactivity=dmaster["UserInteractivity"], representation=dmaster["DataRepresentation"], TotalPoints=dmaster["TotalPoints"])
        newMastery.save()
        newProject.score = dmaster["Total{% if forloop.counter0|divisibleby:1 %}<tr>{% endif %}Points"]
        if newProject.score > 15:
            newProject.level = "advanced"
        elif newProject.score > 7:
            newProject.level = "developing"
        else:
            newProject.level = "beginner"
        newProject.save()

        for charx, dmetrics in d["attribute"].items():
            if charx != 'stage':
                newAttribute = Attribute(myproject=newProject, character=charx, orientation=dmetrics["orientation"], position=dmetrics["position"], costume=dmetrics["costume"], visibility=dmetrics["visibility"], size=dmetrics["size"])
            newAttribute.save()

        iterator = 0
        for deadx in d["dead"]:
            if (iterator % 2) == 0:
                newDead = Dead(myproject=newProject, character=deadx, blocks=0)
            else:
                newDead.blocks = deadx
            newDead.save()
            iterator += 1

        newDuplicate = Duplicate(myproject=newProject, numduplicates=d["duplicate"][0])
        newDuplicate.save()
        for charx in d["sprite"]:
            newSprite = Sprite(myproject=newProject, character=charx)
            newSprite.save()
        return HttpResponseRedirect('/myprojects')

# _____ ID/BUILDERS ____________#

def idProject(request, idProject):
    """Resource uniquemastery of project"""
    if request.user.is_authenticated():
        user = request.user.username
    else:
        user = None
    dmastery = {}
    project = Project.objects.get(id=idProject)
    item = Mastery.objects.get(myproject=project)
    dmastery = buildMastery(item)
    TotalPoints = dmastery["TotalPoints"]
    dsprite = Sprite.objects.filter(myproject=project)
    ddead = Dead.objects.filter(myproject=project)
    dattribute = Attribute.objects.filter(myproject=project)
    listAttribute = buildAttribute(dattribute)
    numduplicate = Duplicate.objects.filter(myproject=project)[0].numduplicates
    return render_to_response("project.html", {'project': project,
                                               'dmastery': dmastery,
                                               'lattribute': listAttribute,
                                               'numduplicate': numduplicate,
                                               'dsprite': dsprite,
                                               'Total points': TotalPoints,
                                               'ddead': ddead},
                                               context_instance=RequestContext(request))


def buildMastery(item):
    """Generate the dictionary with mastery"""
    dmastery = {}
    dmastery["Total points"] = item.TotalPoints
    dmastery["Abstraction"] = item.abstraction
    dmastery["Parallelization"] = item.paralel
    dmastery["Logic"] = item.logic
    dmastery["Synchronization"] = item.synchronization
    dmastery["Flow Control"] = item.flowcontrol
    return dmastery

def buildAttribute(qattribute):
    """Generate dictionary with attribute"""
    # Build the dictionary
    dic = {}
    for item in qattribute:
        dic[item.character] = {"orientation": item.orientation,
                               "position": item.position,
                               "costume": item.costume,
                               "visibility": item.visibility,
                               "size": item.size}
    listInfo = writeErrorAttribute(dic)
    return listInfo

# _______BUILDERS'S HELPERS ________#


def writeErrorAttribute(dic):
    """Write in a list the form correct of attribute plugin"""
    lErrors = []
    for key in dic.keys():
        text = ''
        dx = dic[key]
        if key != 'stage':
            if dx["orientation"] == 1:
                text = 'orientation,'
            if dx["position"] == 1:
                text += ' position, '
            if dx["visibility"] == 1:
                text += ' visibility,'
            if dx["costume"] == 1:
                text += 'costume,'
            if dx["size"] == 1:
                text += ' size'
            if text != '':
                text = key + ': ' + text + ' modified but not initialized correctly'
                lErrors.append(text)
            text = None
        else:
            if dx["background"] == 1:
                text = key + ' background modified but not initialized correctly'
                lErrors.append(text)
    return lErrors

# _________________________  _______________________________ #


def uncompress_zip(zip_file):
    unziped = ZipFile(zip_file, 'r')
    for file_path in unziped.namelist():
        if file_path == 'project.json':
            file_content = unziped.read(file_path)
    show_file(file_content)
