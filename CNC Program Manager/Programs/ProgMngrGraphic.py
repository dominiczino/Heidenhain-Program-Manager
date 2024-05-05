#Dominic Panzino
#CNC Program Manager
#April 4th 2020

import os
import shutil
import sys
#from guiboi import guiboi
#from tabulate import tabulate
import tkinter as tk
import time

Program_Path="Programs" #Where do we look for programs

Server_Path="ServerDir" #Where do we put the numbered programs

extension=".H" #Program extension to use

Reserved=(1,10) #The range of program numbers that are reserved (inclusive)

MaxNum=999 #The maximum program number that can be used
rapidAdder=1000 #The rapid version of the program will be stored with the program number incremented by this value. THIS MUST BE GREATER THAN MAXNUM
rapidFeedRate=2000 #The rapid feed rate to use

fileRefreshTime=2000 #Time in milliseconds between checking the filesystem
pageTurnTime=3000 #time in milliseconds between changing pages


#########################################################################################################################
#An object representing a mapping between groups
class mapping():
    def __init__(self):
        self.A=dict()
        self.B=dict()
        self.memos=dict()

    def addMap(self,itemA,itemB,memo=None):
        if itemA in self.A or itemB in self.B:
            raise ValueError("mapping already exists")
        self.A[itemA]=itemB
        self.B[itemB]=itemA
        if memo is not None:
            self.memos[itemA]=memo
            self.memos[itemB]=memo

    def changeMemo(self,item,newmemo):
        if item in self.A:
            itemA=item
            itemB=self.A[itemA]
            self.memos[itemA]=newmemo
            self.memos[itemB]=newmemo
        elif item in self.B:
            itemB=item
            itemA=self.B[itemB]
            self.memos[itemA]=newmemo
            self.memos[itemB]=newmemo
        else:
            raise KeyError("Tried to update memo but no entry found")

    def lookupA(self,itemA):
        if itemA in self.A:
            return self.A[itemA]
        else:
            return None

    def lookupB(self,itemB):
        if itemB in self.B:
            return self.B[itemB]
        else:
            return None

    def lookup(self,item): #this looks in both, and returns whichever one
        if item in self.A:
            return self.A[item]
        elif item in self.B:
            return self.B[item]
        else:
            return None

    def removeA(self,itemA):
        if itemA in self.A:
            del self.B[self.A[itemA]]
            del self.A[itemA]
            return True
        else:
            return False

    def removeB(self,itemB):
        if itemB in self.B:
            del self.A[self.B[itemB]]
            del self.B[itemB]
            return True
        else:
            return False

    def getMemo(self,item):
        if item in self.memos:
            return self.memos[item]
        else:
            return None

    def __contains__(self,item):
        return item in self.A or item in self.B

    def __str__(self):
        reply=""
        for itemA in self.A:
            reply+="({} --> {})\n".format(itemA,self.A[itemA])
        return reply



###############################################################################################################################################
###############################################################################################################################################
###############################################################################################################################################
class ProgMngr():
    def __init__(self):
        self.progMap=None
        self.reservedSet=None
        self.gui=None
        #self.boot()

    def attachGui(self,gui):
        self.gui=gui

    ###################################################################################################
    def addProgram(self,prog):
        progNum=self.getLowestUnallocatedPN()
        if prog.count(".")>1: #Reserved programs
            resNum=int(prog[prog.index(".")+1:-1*len(extension)])
            if resNum<Reserved[0] or resNum>Reserved[1]:
                raise ValueError("Attempted to assign reserved number outside of allowed range!")
            if resNum in self.reservedSet:
                raise ValueError("Static PN conflict! {} and {}".format(prog,self.reservedSet[resNum]))
            fromPath="{}/{}".format(Program_Path,prog)
            toPath="{}/{}".format(Server_Path,prog[prog.index(".")+1:])
            rapidToPath="{}/{}{}".format(Server_Path,resNum+rapidAdder,extension)
            #shutil.copyfile(fromPath, toPath)
            self.copyProgram(fromPath,toPath,resNum)
            self.copyProgram(fromPath,rapidToPath,resNum+rapidAdder,rapidFeedRate)
            self.reservedSet[resNum]=prog
            self.progMap.addMap(prog,resNum,max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
            self.gui.pushProgram(prog,str(resNum),max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
        else: #Unrestricted programs
            if prog.endswith(extension):
                fromPath="{}/{}".format(Program_Path,prog)
                toPath="{}/{}{}".format(Server_Path,progNum,extension)
                rapidToPath="{}/{}{}".format(Server_Path,progNum+rapidAdder,extension)
                #shutil.copyfile(fromPath,toPath)
                self.copyProgram(fromPath,toPath,progNum)
                self.copyProgram(fromPath,rapidToPath,progNum+rapidAdder,rapidFeedRate)
                self.progMap.addMap(prog,progNum,max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
                self.gui.pushProgram(prog,str(progNum),max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))


    ###################################################################################################
    def copyProgram(self,fromPath,toPath,progNum,rapidFeed=200):
        encoding='ascii'
        hasLineNumbers=False
        lineNum=-1
        f=open(fromPath,'rb')
        t=open(toPath,'wb')
        for line in f:
            #print(line)
            lineNum=lineNum+1
            strline=str(line,encoding)
            if "BEGIN PGM" in strline:
                if strline[0] is "0":
                    hasLineNumbers=True
                t.write(bytes("0 BEGIN PGM {} INCH\r\n".format(progNum),encoding))
            elif "END PGM" in strline:
                if hasLineNumbers==True:
                    lineNum=int(strline[:strline.index(" ")])
                t.write(bytes("{} END PGM {} INCH\r\n".format(lineNum,progNum),encoding))
            elif "FMAX" in strline:
                if hasLineNumbers:
                    t.write(bytes(strline.replace("FMAX","F{}".format(rapidFeed)),encoding))
                else:
                    t.write(bytes(str(lineNum)+" "+strline.replace("FMAX","F{}".format(rapidFeed)),encoding)) #This works for newly posted programs that use FMAX
            elif "F2000" in strline:
                if hasLineNumbers:
                    t.write(bytes(strline.replace("F2000","F{}".format(rapidFeed)),encoding))
                else:
                    t.write(bytes(str(lineNum)+" "+strline.replace("F2000","F{}".format(rapidFeed)),encoding)) #This is to work with legacy programs where I used 2000 as the rapid
            else:
                if hasLineNumbers:
                    t.write(line)
                else:
                    t.write(bytes(str(lineNum)+" "+strline,encoding))
        f.close()
        t.close()
        
    ###################################################################################################
    def boot(self):
        self.progMap=mapping()
        self.reservedSet=dict()

        #Clear whatever files are already in the server directory
        delFiles=os.listdir(Server_Path)
        for file in delFiles:
            os.remove("{}/{}".format(Server_Path,file))

        
        namedProgs=os.listdir(Program_Path)

        progNum=Reserved[1]+1
        for prog in namedProgs:
            if prog.count(".")>1: #Reserved programs
                resNum=int(prog[prog.index(".")+1:-1*len(extension)])
                if resNum<Reserved[0] or resNum>Reserved[1]:
                    raise ValueError("Attempted to assign reserved number outside of allowed range!")
                if resNum in self.reservedSet:
                    raise ValueError("Static PN conflict! {} and {}".format(prog,self.reservedSet[progNum]))
                fromPath="{}/{}".format(Program_Path,prog)
                toPath="{}/{}".format(Server_Path,prog[prog.index(".")+1:])
                rapidToPath="{}/{}{}".format(Server_Path,resNum+rapidAdder,extension)
                self.copyProgram(fromPath,toPath,resNum)
                self.copyProgram(fromPath,rapidToPath,resNum+rapidAdder,rapidFeedRate)
                self.reservedSet[resNum]=prog
                self.progMap.addMap(prog,resNum,max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
                self.gui.pushProgram(prog,str(resNum),max(os.path.getmtime(fromPath),os.path.getctime(fromPath)),False)
            else: #Unrestricted programs
                if prog.endswith(extension):
                    if progNum>MaxNum:
                        raise ValueError("No more PN's to allocate!")
                    fromPath="{}/{}".format(Program_Path,prog)
                    toPath="{}/{}{}".format(Server_Path,progNum,extension)
                    rapidToPath="{}/{}{}".format(Server_Path,progNum+rapidAdder,extension)
                    self.copyProgram(fromPath,toPath,progNum)
                    self.copyProgram(fromPath,rapidToPath,progNum+rapidAdder,rapidFeedRate)
                    self.progMap.addMap(prog,progNum,max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
                    self.gui.pushProgram(prog,str(progNum),max(os.path.getmtime(fromPath),os.path.getctime(fromPath)),False)
                    progNum+=1
        self.gui.pushMessage("Filesystem Booted Successfully")
        self.gui.window.state('zoomed')


    ###################################################################################################
    def getLowestUnallocatedPN(self):
        for i in range(Reserved[1]+1,MaxNum):
            if i not in self.progMap:
                return i
        raise ValueError("No more PN's to allocate!")
                
        
    ###################################################################################################
    def Update(self):
        namedProgs=os.listdir(Program_Path)
        numberedProgs=os.listdir(Server_Path)
        updatesMade=False
        #First go through the programs we already have
        for program in numberedProgs:
            progNum = int(program[:program.index(".")])
            if progNum<=MaxNum: #Use this to not mess with rapid versions
                name=self.progMap.lookupB(progNum)
                #name=name[:name.index(".")]#Get the file name
                if name in namedProgs:
                    fromPath="{}/{}".format(Program_Path,name)
                    toPath="{}/{}".format(Server_Path,program)
                    newTime=max(os.path.getmtime(fromPath),os.path.getctime(fromPath))
                    if newTime>self.progMap.getMemo(name): #if the named program is newer, then update the numbered program
                        rapidToPath="{}/{}{}".format(Server_Path,progNum+rapidAdder,extension)
                        os.remove(toPath)
                        os.remove(rapidToPath)
                        self.copyProgram(fromPath,toPath,progNum)
                        self.copyProgram(fromPath,rapidToPath,progNum+rapidAdder,rapidFeedRate)
                        updatesMade=True
                        self.progMap.changeMemo(name,newTime)
                        self.gui.updateProgram(name,str(progNum),max(os.path.getmtime(fromPath),os.path.getctime(fromPath)))
                        print("\tUpdated file {}".format(name))
        for prog in namedProgs:
            if prog not in self.progMap: #If we find a new program
                self.addProgram(prog)
                updatesMade=True
                print("\tAdded new program {}".format(prog))
        return updatesMade


    ###################################################################################################
    def __str__(self):
        reply=""
        for i in range(1,MaxNum+1):
            name=self.progMap.lookupB(i)
            if name is not None:
                formattedTime=time.strftime('%m/%d/%Y %H:%M:%S',  time.localtime(self.progMap.getMemo(i)))
                reply+="{} --> {} \t \t \t({})\n".format(name,i,formattedTime)
        return reply


    ###################################################################################################
    def getData(self):
        reply=[]
        for i in range(1,MaxNum+1):
            name=self.progMap.lookupB(i)
            if name is not None:
                reply.append((name,i,time.strftime('%m/%d/%Y %H:%M:%S',time.localtime(self.progMap.getMemo(i)))))
        return reply

###############################################################################################################################################
###############################################################################################################################################
###############################################################################################################################################

class guiboi():
    def __init__(self,mngr):
        self.mngr=mngr
        self.window=tk.Tk()
        self.window.configure(background='black')
        ########################GUI CONFIGURATION VARIABLES#############################
        self.numProgLines=12 #The max number of program lines to draw. If there are too many programs, then the programs will rotate through pages
        self.numMsgLines=14 #The max number of messages to draw. Will delete old messages as new ones come in.

        self.page=0
        self.pagetxt=tk.StringVar(value="Pg {}".format(self.page+1))
        self.lastProgTime=0
        self.currentTimeSec=time.time()
        self.currentTime=tk.StringVar(value=str(time.strftime('%H:%M:%S',  time.localtime(self.currentTimeSec) )))
        self.enableMessages=False

        self.ProgSizes=24 #Font size for Programs and headings thereof
        self.MsgSizes=14 #Font size for messages
        self.RecentSizes=24 #Font size for the recent program stuff

        self.allProgNames=[]
        self.allProgNums=[]
        self.allProgTimes=[]

        self.progNames=[]
        self.progNums=[]
        self.progTimes=[]

        ##Initialize the drawn variable arrays
        for x in range(self.numProgLines):
            self.progNames.append(tk.StringVar(value="prog"))
            self.progNums.append(tk.StringVar(value="0"))
            self.progTimes.append(tk.StringVar(value="dawn of time"))

        self.Msgs=[tk.StringVar(value="{}: GUI Initializing...".format(time.strftime('%H:%M:%S',  time.localtime(time.time()) )))]
        while len(self.Msgs)<self.numMsgLines:
            self.Msgs.append(tk.StringVar(value=" "))


        ##########DRAW THE MAIN GUI OMG ITS HAPPENING ITS HAPPENING OK PEOPLE STAY CALM STAY FUCKING CALM
        frame_banner=tk.Frame(master=self.window,relief=tk.RIDGE,borderwidth=3,bg="black")
        frame_banner.pack(fill=tk.X)
        if True:
            Banner=tk.Label(master=frame_banner,font=("Futura Bk BT",36, "bold"), text="ZINO TNC SERVER    Mk I", fg="black", bg="orange")
            Banner.pack(fill=tk.X)

        frame_recent=tk.Frame(master=self.window,relief=tk.RIDGE,borderwidth=3,bg="black")
        frame_recent.pack(fill=tk.X)
        if True:
            recent_heading=tk.Label(master=frame_recent, font=("Futura Bk BT", self.RecentSizes,), text="MOST RECENT FILE: ", fg="white", bg="black")
            recent_heading.pack(side=tk.LEFT)

            self.RecentFileName=tk.StringVar(value="---")
            self.RecentFileNum=tk.StringVar(value="---")
            self.RecentFileTime=tk.StringVar(value="---")

            label_recentFileName=tk.Label(master=frame_recent, font=("Futura Bk BT", self.RecentSizes,"bold"), textvariable=self.RecentFileName, fg="white", bg="grey10")
            label_recentFileNum=tk.Label(master=frame_recent, font=("Futura Bk BT", self.RecentSizes,"bold"), textvariable=self.RecentFileNum, fg="white", bg="grey10")
            label_recentFileTime=tk.Label(master=frame_recent, font=("Futura Bk BT", self.RecentSizes), textvariable=self.RecentFileTime, fg="white", bg="black")
            label_currentTime=tk.Label(master=frame_recent,font=("Futura Bk BT",self.RecentSizes),textvariable=self.currentTime,fg="white",bg="black",relief=tk.RAISED,borderwidth=2)

            label_recentFileName.pack(side=tk.LEFT)
            label_recentFileNum.pack(side=tk.LEFT)
            label_currentTime.pack(side=tk.RIGHT)
            label_recentFileTime.pack(side=tk.LEFT)
            
            

        frame_lower=tk.Frame(master=self.window,bg="grey10")
        frame_lower.pack(fill=tk.X)
        frame_lower.columnconfigure(0,weight=1)
        if self.enableMessages:
            frame_lower.columnconfigure(1,weight=1)

        frame_progList=tk.Frame(master=frame_lower,relief=tk.RIDGE,borderwidth=3,bg="black")
        frame_progList.grid(row=0,column=0,sticky="nsew")
        frame_progList.columnconfigure(0,minsize=400)
        frame_progList.columnconfigure(1,minsize=100)
        frame_progList.columnconfigure(2,minsize=200)

        if True:
            frame_progNames=tk.Frame(master=frame_progList,bg="black")
            frame_progNames.grid(row=0, column=0,sticky="new")
            if True:
                ProgramHeading=tk.Label(master=frame_progNames,text="PROGRAM NAMES", font=("Futura Bk BT",self.ProgSizes,"bold"),fg="black",bg="orange",relief=tk.RAISED,borderwidth=2)
                ProgramHeading.pack()
                for prog in self.progNames:
                    namelbl=tk.Label(master=frame_progNames,textvariable=prog,font=("Futura Bk BT",self.ProgSizes),fg="white",bg="black",anchor="e")
                    namelbl.pack(fill=tk.X)

            frame_progNums=tk.Frame(master=frame_progList,bg="black")
            frame_progNums.grid(row=0, column=1,sticky="n")
            if True:
                ProgramNumHeading=tk.Label(master=frame_progNums,text="P/N", font=("Futura Bk BT",self.ProgSizes,"bold"),fg="black",bg="orange",relief=tk.RAISED,borderwidth=2)
                ProgramNumHeading.pack()
                for num in self.progNums:
                    numlbl=tk.Label(master=frame_progNums,textvariable=num,font=("Futura Bk BT",self.ProgSizes),fg="white",bg="black",anchor="w")
                    numlbl.pack(fill=tk.X)

            frame_progTimes=tk.Frame(master=frame_progList,bg="black")
            frame_progTimes.grid(row=0, column=2,sticky="n")
            if True:
                ProgramTimeHeading=tk.Label(master=frame_progTimes,text="Last Updated", font=("Futura Bk BT", self.ProgSizes, "bold"),fg="black",bg="orange",relief=tk.RAISED,borderwidth=2)
                ProgramTimeHeading.pack()
                for progTime in self.progTimes:
                    timelbl=tk.Label(master=frame_progTimes,textvariable=progTime,font=("Futura Bk BT",self.ProgSizes),fg="white",bg="black",anchor="w")
                    timelbl.pack(fill=tk.X)

            timelbl=tk.Label(master=frame_progList,textvar=self.pagetxt,font=("Futura Bk BT", self.ProgSizes), bg="black",fg="white",anchor="e")
            timelbl.grid(row=0,column=3,sticky="ne")

            frame_Messages=tk.Frame(master=frame_lower,bg="black",relief=tk.RIDGE,borderwidth=3)
            if self.enableMessages:
                frame_Messages.grid(row=0,column=1,sticky="nsew")
            if True:
                MessagesHeading=tk.Label(master=frame_Messages,text="MESSAGES AND ERRORS",font=("Futura Bk BT",self.ProgSizes,"bold"),fg="black",bg="orange",relief=tk.RAISED,borderwidth=2)
                MessagesHeading.pack()
                for msg in self.Msgs:
                    msglbl=tk.Label(master=frame_Messages,textvariable=msg,font=("Futura Bk BT",self.MsgSizes),fg="white",bg="black",relief=tk.GROOVE,borderwidth=1)
                    msglbl.pack(fill=tk.X)

            #self.window.state('zoomed')
            self.window.update()
            self.pushMessage("GUI successfully initialized")

    def pushMessage(self,message):
        for i in range(self.numMsgLines-1):
            point=self.numMsgLines-1-i
            self.Msgs[point].set(self.Msgs[point-1].get())

        fullMsgTxt="{}: {}".format(time.strftime('%H:%M:%S',  time.localtime(time.time()) ),message)
        self.Msgs[0].set(fullMsgTxt)
        print(fullMsgTxt)
        self.window.update()

    def refresh(self):
        self.window.update()
        #print("get fuckt")

    def pushProgram(self,Name,Num,Time,verbose=True):
        #self.allProgNames=[Name]+self.allProgNames
        #self.allProgNums=[Num]+self.allProgNums
        #self.allProgTimes=[Time]+self.allProgTimes

        self.allProgNames.append(Name)
        self.allProgNums.append(Num)
        self.allProgTimes.append(time.strftime('%m/%d/%Y %H:%M:%S',  time.localtime(Time) ))

        if Time>self.lastProgTime:
            self.lastProgTime=Time
            if len(Name)>15:
                self.RecentFileName.set(Name[:12]+"...")
            else:
                self.RecentFileName.set(Name)
            self.RecentFileNum.set("--->"+Num)
            #self.RecentFileTime.set(time.strftime('%m/%d/%Y %H:%M:%S',  time.localtime(Time) ))
            self.RecentFileTime.set("[{}min ago]".format(-1*int((self.lastProgTime-self.currentTimeSec)/60)))

        if verbose:
            self.pushMessage("Added Program \"{}\"".format(Name))

        self.rollPage()

    def updateProgram(self,Name,Num,newTime):
        index=None
        for i in range(len(self.allProgNames)):
            if Name==self.allProgNames[i]:
                index=i
                break
        if index is not None:
            self.allProgTimes[index]=time.strftime('%m/%d/%Y %H:%M:%S',  time.localtime(newTime) )
            self.lastProgTime=newTime
            if len(Name)>15:
                self.RecentFileName.set(Name[:12]+"...")
            else:
                self.RecentFileName.set(Name)
            self.RecentFileNum.set("--->"+Num)
            self.RecentFileTime.set("[{}min ago]".format(-1*int((self.lastProgTime-self.currentTimeSec)/60)))
            self.pushMessage("Updated Program \"{}\"".format(Name))
        else:
            self.pushMessage("[ERROR]: Tried to update missing program")

    def rollPage(self):
        self.page+=1
        if self.page*self.numProgLines>=len(self.allProgNames):
            self.page=0
        start=self.page*self.numProgLines
        end=min(start+self.numProgLines, len(self.allProgNames))
        for i in range(start,end):
            name=self.allProgNames[i]
            if len(name)>23:
                name=name[:20]+"..."
            else:
                name=name[:-2] #No need to show the extension
            self.progNames[i%self.numProgLines].set(name)
            self.progNums[i%self.numProgLines].set("---->"+self.allProgNums[i]+"-----")
            self.progTimes[i%self.numProgLines].set(self.allProgTimes[i])

        if end==len(self.allProgNames) and not end==start+self.numProgLines: #This is true when we have a partial page
            for i in range(end%self.numProgLines,self.numProgLines):
                self.progNames[i].set(" ")
                self.progNums[i].set(" ")
                self.progTimes[i].set(" ")

        self.pagetxt.set("Pg {}/{}".format(self.page+1,int(len(self.allProgNames)/self.numProgLines+1)))
        self.window.update()

    def refresh(self):
        try:
            self.mngr.Update()
        except OSError:
            self.pushMessage("[ERROR]: An filesystem error occurred")
        #except:
        #    print("eRROR!?")
        #    self.pushMessage("[ERROR]: An unknown error occurred")
            
        self.currentTime.set(str(time.strftime('%H:%M:%S',  time.localtime(time.time()) )))
        self.currentTimeSec=time.time()
        self.RecentFileTime.set("[{}min ago]".format(-1*int((self.lastProgTime-self.currentTimeSec)/60)))
        self.window.after(fileRefreshTime,self.refresh)

    def pageRefresh(self):
        self.rollPage()
        self.window.after(pageTurnTime,self.pageRefresh)

    def run(self):
        self.window.after(fileRefreshTime,self.refresh)
        self.window.after(pageTurnTime,self.pageRefresh)
        self.window.mainloop()        


        #############################################################
        #############################################################
        #############################################################
        #############################################################


mngr=ProgMngr()
gui=guiboi(mngr)
mngr.attachGui(gui)
gui.pushMessage("Booting filesystem manager...")
mngr.boot()
gui.run()
print("Application window closed. I will now commit die")
    
                
