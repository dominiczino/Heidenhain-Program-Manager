#Dominic Panzino
#CNC Program Manager
#April 4th 2020

import os
import shutil
import time
import sys
#from tabulate import tabulate

Program_Path="Programs" #Where do we look for programs

Server_Path="ServerDir" #Where do we put the numbered programs

extension=".H" #Program extension to use

Reserved=(1,10) #The range of program numbers that are reserved (inclusive)

MaxNum=8999 #The maximum program number that can be used


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
        self.boot()

    ###################################################################################################
    def addProgram(self,prog):
        progNum=self.getLowestUnallocatedPN()
        if prog.count(".")>1: #Reserved programs
            resNum=int(prog[prog.index(".")+1:-1*len(extension)])
            if resNum in self.reservedSet:
                raise ValueError("Static PN conflict! {} and {}".format(prog,self.reservedSet[resNum]))
            fromPath="{}/{}".format(Program_Path,prog)
            toPath="{}/{}".format(Server_Path,prog[prog.index(".")+1:])
            #shutil.copyfile(fromPath, toPath)
            self.copyProgram(fromPath,toPath,resNum)
            self.reservedSet[resNum]=prog
            self.progMap.addMap(prog,resNum,os.path.getmtime(toPath))
        else: #Unrestricted programs
            if prog.endswith(extension):
                fromPath="{}/{}".format(Program_Path,prog)
                toPath="{}/{}{}".format(Server_Path,progNum,extension)
                #shutil.copyfile(fromPath,toPath)
                self.copyProgram(fromPath,toPath,progNum)
                self.progMap.addMap(prog,progNum,os.path.getmtime(toPath))


    ###################################################################################################
    def copyProgram(self,fromPath,toPath,progNum):
        encoding='ascii'
        f=open(fromPath,'rb')
        t=open(toPath,'wb')
        for line in f:
            #print(line)
            strline=str(line,encoding)
            if "BEGIN PGM" in strline:
                t.write(bytes("0 BEGIN PGM {} INCH\r\n".format(progNum),encoding))
            elif "END PGM" in strline:
                lineNum=int(strline[:strline.index(" ")])
                t.write(bytes("{} END PGM {} INCH\r\n".format(lineNum,progNum),encoding))
            else:
                t.write(line)
        
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
                if resNum in self.reservedSet:
                    raise ValueError("Static PN conflict! {} and {}".format(prog,self.reservedSet[progNum]))
                fromPath="{}/{}".format(Program_Path,prog)
                toPath="{}/{}".format(Server_Path,prog[prog.index(".")+1:])
                #shutil.copyfile(fromPath, toPath)
                self.copyProgram(fromPath,toPath,resNum)
                self.reservedSet[resNum]=prog
                self.progMap.addMap(prog,resNum,os.path.getmtime(toPath))
            else: #Unrestricted programs
                if prog.endswith(extension):
                    if progNum>MaxNum:
                        raise ValueError("No more PN's to allocate!")
                    fromPath="{}/{}".format(Program_Path,prog)
                    toPath="{}/{}{}".format(Server_Path,progNum,extension)
                    #shutil.copyfile(fromPath,toPath)
                    self.copyProgram(fromPath,toPath,progNum)
                    self.progMap.addMap(prog,progNum,os.path.getmtime(toPath))
                    progNum+=1


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
            name=self.progMap.lookupB(progNum)
            #name=name[:name.index(".")]#Get the file name
            if name in namedProgs:
                fromPath="{}/{}".format(Program_Path,name)
                toPath="{}/{}".format(Server_Path,program)
                newTime=os.path.getmtime(fromPath)
                if newTime>self.progMap.getMemo(name): #if the named program is newer, then update the numbered program
                    os.remove(toPath)
                    #shutil.copyfile(fromPath,toPath)
                    self.copyProgram(fromPath,toPath,progNum)
                    updatesMade=True
                    self.progMap.changeMemo(name,newTime)
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
                formattedTime=time.strftime('%m/%d/%Y %H:%M:%S',  time.gmtime(self.progMap.getMemo(i)))
                reply+="{} --> {} \t \t \t({})\n".format(name,i,formattedTime)
        return reply


    ###################################################################################################
    def getData(self):
        reply=[]
        for i in range(1,MaxNum+1):
            name=self.progMap.lookupB(i)
            if name is not None:
                reply.append((name,i,time.strftime('%m/%d/%Y %H:%M:%S',time.gmtime(self.progMap.getMemo(i)))))
        return reply

###############################################################################################################################################
###############################################################################################################################################
###############################################################################################################################################

def tabulate(listoflists,headers,widths=None):
    reply=""
    rows=len(listoflists)
    if rows==0:
        return
    cols=len(listoflists[0])
    if widths is None:
        widths=[0 for _ in range(cols)]
    for row in listoflists:
        for colnum in range(cols):
            if len(str(row[colnum]))>widths[colnum]:
                widths[colnum]=len(str(row[colnum]))
                if widths[colnum]%2==1:
                    widths[colnum]+=1

    
    for colnum in range(cols):
        heading=headers[colnum]
        reply+=heading
        #print(heading,end="")
        for _ in range(widths[colnum]-len(heading)+4):
            reply+=" "
            #print(" ",end="")
    reply+="\n"
    for i in range(sum(widths)):
        reply+="="

    for rownum in range(rows):
        row=listoflists[rownum]
        reply+="\n"
        #print("")
        for colnum in range(cols):
            item=str(row[colnum])
            reply+=item
            #print(item,end="")
            if rownum%3>0 and colnum<cols-1:
                for _ in range(int(widths[colnum]-len(item)+4)):
                    reply+=" "
            elif colnum<cols-1:
                for _ in range(int(widths[colnum]-len(item)+4)):
                    reply+="-"
    return reply





mngr=ProgMngr()
print("Program manager booted successfully")
#print(mngr)
print(tabulate(mngr.getData(),headers=["Name","PN","Updated Time"],widths=[10,5,27]))
while True:
    time.sleep(2)
    data=tabulate(mngr.getData(),headers=["Name","PN","Updated Time"],widths=[10,5,27])
    try:
        mngr.Update()
    except:
        print("UPDATE FAILED")
    os.system("cls")
    #print("\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n")
    print("Last Updated: {}".format(time.strftime('%m/%d/%Y %H:%M:%S',  time.gmtime(time.time()) )))
    print(data)
    #print(mngr)
                
