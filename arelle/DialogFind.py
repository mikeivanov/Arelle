'''
Created on May 1, 2011

@author: Mark V Systems Limited
(c) Copyright 2011 Mark V Systems Limited, All rights reserved.
'''
from tkinter import *
from tkinter.ttk import *
import tkinter.messagebox, traceback
import re
from arelle.UiUtil import (gridHdr, gridCell, gridCombobox, label, checkbox, radiobutton)
from arelle.CntlrWinTooltip import ToolTip
from arelle import (ModelDocument, ModelObject, ModelRssObject, XPathContext, XPathParser, XmlUtil)
from arelle.ModelFormulaObject import Trace

'''
caller checks accepted, if True, caller retrieves url
'''

reMetaChars = '[]\\^$.|?*+(){}'

def find(mainWin):
    dialog = DialogFind(mainWin, mainWin.config.setdefault("findOptions",FindOptions()))

  
class DialogFind(Toplevel):
    def __init__(self, mainWin, options):
        parent = mainWin.parent
        super().__init__(parent)
        self.parent = parent
        self.modelManager = mainWin.modelManager
        self.modelXbrl = None   # set when Find pressed, this blocks next prematurely
        if options is None: options = FindOptions()
        self.options = options
        parentGeometry = re.match("(\d+)x(\d+)[+]?([-]?\d+)[+]?([-]?\d+)", parent.geometry())
        dialogW = int(parentGeometry.group(1))
        dialogH = int(parentGeometry.group(2))
        dialogX = int(parentGeometry.group(3))
        dialogY = int(parentGeometry.group(4))
        self.accepted = False

        self.transient(self.parent)
        self.title(_("Find"))
        
        frame = Frame(self)

        # load grid
        findLabel = gridHdr(frame, 1, 0, "Find:", anchor="w")
        findLabel.grid(padx=8)
        self.cbExpr = gridCombobox(frame, 1, 1, values=options.priorExpressions)
        self.cbExpr.grid(columnspan=3, padx=8)
        ToolTip(self.cbExpr, text=_("Enter expression to find, or select from combo box drop down history list."), wraplength=240)

        y = 2
        
        # checkbox entries
        label(frame, 1, y, "Direction:")
        label(frame, 1, y + 3, "Match:")
        scopeLabel = label(frame, 2, y, "Scope:")
        ToolTip(scopeLabel, text=_("Scope for an XBRL document (instance or DTS).  "
                                   "For an RSS Feed, all properties are matched.  "), wraplength=240)
        rbUp = radiobutton(frame, 1, y+1, "Up", "up", "direction")
        ToolTip(rbUp, text=_("Find/Next up (on screen) from last to first match."), wraplength=240)
        rbDn = radiobutton(frame, 1, y+2, "Down", "down", "direction", rbUp.valueVar)
        ToolTip(rbDn, text=_("Find/Next down (on screen) from first to last match."), wraplength=240)
        rbText = radiobutton(frame, 1, y+4, "Text (ignore case)", "text", "exprType")
        ToolTip(rbText, text=_("Expression is a set of characters to match, ignoring case.  "
                               "The match may occur anywhere within the scope. "), wraplength=360)
        rbRegex = radiobutton(frame, 1, y+5, "Regular expression", "regex", "exprType", rbText.valueVar)
        ToolTip(rbRegex, text=_('A regular expression to match, anywhere in the scope, ignoring case.  '
                                'For example, "cash" would match cash anywhere in a string (like cash on hand), '
                                'whereas "^cash$" would match a full string to only contain cash. ' 
                                'Use regular expression metacharacters, e.g., "." for any single character, '
                                '".*" for any number of wild characters, .{3} for exactly 3 wild characters. '), wraplength=360)
        rbXPath = radiobutton(frame, 1, y+6, "XPath 2 expression", "xpath", "exprType", rbText.valueVar)
        ToolTip(rbXPath, text=_('An XPath 2 expression, where the context element, ".", is a candidate concept QName, if any concept scope is checked, '
                                'and a candidate fact item, if any fact scope is checked.  The XPath 2 functions do not need an "fn:" prefix (but it is defined).  '
                                'The XBRL Functions Registry functions do require an "xfi:" prefix.  Constructors require an "xs:" prefix.  '
                                'The expression is considered "matched" for the candidate concept QNames or fact items where the effective boolean value of the expression is "true()".  '), wraplength=360)
        self.optionControls = (
           rbUp,
           rbDn,
           rbText,
           rbRegex,
           rbXPath,
           #checkbox(frame, 2, y + 1, "All", "all"),
           checkbox(frame, 2, y + 1, "Concept label", "conceptLabel"),
           checkbox(frame, 2, y + 2, "   name", "conceptName"),
           checkbox(frame, 2, y + 3, "   type", "conceptType"),
           checkbox(frame, 2, y + 4, "   subs group", "conceptSubs"),
           checkbox(frame, 2, y + 5, "   period type", "conceptPer"),
           checkbox(frame, 2, y + 6, "   balance", "conceptBal"),
           checkbox(frame, 3, y + 1, "Fact label", "factLabel"),
           checkbox(frame, 3, y + 2, "   name", "factName"),
           checkbox(frame, 3, y + 3, "   value", "factValue"),
           checkbox(frame, 3, y + 4, "   context", "factCntx"),
           checkbox(frame, 3, y + 5, "   unit", "factUnit"),
        
           # Note: if adding to this list keep Finder.FindOptions in sync
        
           )
        y += 7
        resultLabel = gridHdr(frame, 1, y, "Result:", anchor="w")
        resultLabel.grid(padx=8)
        self.resultText = gridCell(frame, 1, y + 1)
        self.resultText.grid(columnspan=3, padx=8)
        self.resultText.config(state="readonly")
        y += 2
        
        mainWin.showStatus(None)

        buttonFrame = Frame(frame)
        buttonFrame.grid(columnspan=4, sticky=E, padx=8)
        findButton = Button(buttonFrame, text=_("Find"), width=12, command=self.find)
        ToolTip(findButton, text=_('Compile (if regular expression or XPath 2), and find first match (if down direction) or last match (if up direction).  '), wraplength=240)
        nextButton = Button(buttonFrame, text=_("Next"), width=12, command=self.next)
        ToolTip(nextButton, text=_('Advance to the next matched object (in selected direction).  '), wraplength=240)
        closeButton = Button(buttonFrame, text=_("Close"), width=12, command=self.close)
        ToolTip(closeButton, text=_('Close the find dialog.  '), wraplength=240)
        findButton.grid(row=1, column=1, pady=3)
        nextButton.grid(row=1, column=2, pady=3)
        closeButton.grid(row=1, column=3, padx=3)
        
        frame.grid(row=0, column=0, sticky=(N,S,E,W))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.columnconfigure(3, weight=1)
        window = self.winfo_toplevel()
        window.columnconfigure(0, weight=1)
        if hasattr(self.options,'geometry') and self.options.geometry:
            self.geometry(self.options.geometry)
        else:
            self.geometry("+{0}+{1}".format(dialogX+50,dialogY+100))
        
        #self.bind("<Return>", self.ok)
        #self.bind("<Escape>", self.close)
        
        self.protocol("WM_DELETE_WINDOW", self.close)
        
        # make this dialog non-modal
        self.focus_set()
        #self.grab_set()
        #self.wait_window(self)
        
    def setOptions(self):
        # set formula options
        for optionControl in self.optionControls:
            setattr(self.options, optionControl.attr, optionControl.value)
        
    def find(self, event=None):
        self.setOptions()
        self.accepted = True
        # self.close()
        
        docType = self.modelManager.modelXbrl.modelDocument.type
        if not self.modelManager.modelXbrl or not docType in (
             ModelDocument.Type.SCHEMA, ModelDocument.Type.LINKBASE, ModelDocument.Type.INSTANCE, ModelDocument.Type.INLINEXBRL,
             ModelDocument.Type.RSSFEED):
            tkinter.messagebox.showerror(_("Find cannot be completed"),
                     _("Find requires an opened DTS or RSS Feed"), parent=self.parent)
            return
        
        if docType == ModelDocument.Type.RSSFEED and self.options.exprType == "xpath":
            tkinter.messagebox.showerror(_("Find cannot be completed"),
                     _("XPath matching is not available for an RSS Feed, please choose text or regular expression.  "), parent=self.parent)
            return
            
        self.modelXbrl = self.modelManager.modelXbrl
        expr = self.cbExpr.value
        # update find expressions history
        if expr in self.options.priorExpressions:
            self.options.priorExpressions.remove(expr)
        elif len(self.options.priorExpressions) > 10:
            self.options.priorExpressions = self.options.priorExpressions[0:10]
        self.options.priorExpressions.insert(0, expr)
        self.cbExpr.config(values=self.options.priorExpressions)
        self.saveConfig()
        
        import threading
        thread = threading.Thread(target=lambda: self.backgroundFind())
        thread.daemon = True
        thread.start()


    def backgroundFind(self):
        expr = self.cbExpr.value
        inConceptLabel = self.options.conceptLabel
        inConceptName = self.options.conceptName
        inConceptType = self.options.conceptType
        inConceptSubs = self.options.conceptSubs
        inConceptPer = self.options.conceptPer
        inConceptBal = self.options.conceptBal
        inFactLabel = self.options.factLabel
        inFactName = self.options.factName
        inFactValue = self.options.factValue
        inFactCntx = self.options.factCntx
        inFactUnit = self.options.factUnit
        self.nextIsDown = self.options.direction == "down"
        
        objsFound = set()
        
        try:
            if self.options.exprType == "text":
                # escape regex metacharacters
                pattern = re.compile(''.join(
                         [(('\\' + c) if c in reMetaChars else c) for c in expr]), 
                         re.IGNORECASE)
                isRE = True
                isXP = False
            elif self.options.exprType == "regex":
                pattern = re.compile(expr, re.IGNORECASE)
                isRE = True
                isXP = False
            elif self.options.exprType == "xpath":
                isRE = False
                isXP = True
                self.resultText.setValue(_("Compiling xpath expression..."))
                XPathParser.initializeParser(self)
                self.modelManager.showStatus(_("Compiling xpath expression..."))
                xpProg= XPathParser.parse(self, 
                                          expr, 
                                          XPathParser.staticExpressionFunctionContext(), 
                                          "find expression", 
                                          Trace.CALL)
                xpCtx = XPathContext.create(self.modelXbrl, sourceElement=None)

            else:
                return  # nothing to do
            
            if self.modelXbrl.modelDocument.type == ModelDocument.Type.RSSFEED:
                for rssItem in self.modelXbrl.modelDocument.items:
                    if any(pattern.search(str(value)) for name, value in rssItem.propertyView):
                        objsFound.add(rssItem)  
            else: # DTS search
                if inConceptLabel or inConceptName or inConceptType or inConceptSubs or inConceptPer or inConceptBal:
                    self.resultText.setValue(_("Matching concepts..."))
                    self.modelManager.showStatus(_("Matching concepts..."))
                    for conceptName, concepts in self.modelXbrl.nameConcepts.items():
                        for concept in concepts:
                            if ((isXP and xpCtx.evaluateBooleanValue(xpProg, contextItem=concept.qname)) or
                                (isRE and
                                 (inConceptLabel and pattern.search(concept.label())) or
                                 (inConceptName and pattern.search(conceptName)) or
                                 (inConceptType and pattern.search(str(concept.typeQname))) or
                                 (inConceptSubs and pattern.search(str(concept.substitutionGroupQname))) or
                                 (inConceptPer and concept.periodType and pattern.search(concept.periodType)) or
                                 (inConceptBal and concept.balance and pattern.search(concept.balance))
                                 )
                                ):
                                objsFound.add(concept)  
                if inFactLabel or inFactName or inFactValue or inFactCntx or inFactUnit:
                    self.resultText.setValue(_("Matching facts..."))
                    self.modelManager.showStatus(_("Matching facts..."))
                    for fact in self.modelXbrl.facts:
                        if ((isXP and xpCtx.evaluateBooleanValue(xpProg, contextItem=fact)) or
                            (isRE and
                             (inFactName and pattern.search(fact.concept.name) or
                             (inFactLabel and pattern.search(fact.concept.label())) or
                             (inFactValue and pattern.search(fact.value)) or
                             (inFactCntx and pattern.search(XmlUtil.innerText(fact.context.element))) or
                             (inFactUnit and pattern.search(XmlUtil.innerText(fact.unit.element))))
                             )
                            ):
                            objsFound.add(fact)
        except XPathContext.XPathException as err:
            err = _("Find expression error: {0} \n{1}").format(err.message, err.sourceErrorIndication)
            self.modelManager.addToLog(err)
            self.resultText.setValue(err)
            self.modelManager.showStatus(_("Completed with errors"), 5000)
                            
        numConcepts = 0
        numFacts = 0
        numRssItems = 0
        self.objsList = []
        for obj in objsFound:
            if isinstance(obj,ModelObject.ModelConcept):
                numConcepts += 1
                self.objsList.append( ('c', obj.localName, obj.objectId()) )
            elif isinstance(obj,ModelObject.ModelFact):
                numFacts += 1
                self.objsList.append( ('f', obj.__hash__(), obj.objectId()) )
            elif isinstance(obj,ModelRssObject.ModelRssItem):
                numRssItems += 1
                self.objsList.append( ('r', obj.__hash__(), obj.objectId()) )
        self.objsList.sort()
        self.result = "Found "
        if numConcepts:
            self.result += "{0} concepts".format(numConcepts)
            if numFacts: self.result += ", "
        if numFacts:
            self.result += "{0} facts".format(numFacts)
        if numRssItems:
            self.result += "{0} RSS items".format(numRssItems)
        if numConcepts + numFacts + numRssItems == 0:
            self.result += "no matches"
            self.foundIndex = -1
            self.resultText.setValue(self.result)
        else:
            self.foundIndex = 0 if self.nextIsDown else (len(self.objsList) - 1)
            self.modelManager.cntlr.uiThreadQueue.put((self.next, []))
        self.modelManager.showStatus(_("Ready..."), 2000)
                                    
    def next(self):
        # check that asme instance applies
        if self.modelXbrl is None:
            return
        if self.modelManager.modelXbrl != self.modelXbrl:
            tkinter.messagebox.showerror(_("Next cannot be completed"),
                            _("A different DTS is active, than find was initiated with.  Please press 'find' to re-search with the current DTS"), parent=self.parent)
            return
        lenObjsList = len(self.objsList)
        if lenObjsList == 0:
            tkinter.messagebox.showwarning(_("Next cannot be completed"),
                            _("No matches were found.  Please try a different search."), parent=self.parent)
            return
            
        self.result = self.result.partition("Selection")[0]
        if 0 <= self.foundIndex < lenObjsList:
            self.modelManager.modelXbrl.viewModelObject(self.objsList[self.foundIndex][2])
            self.resultText.setValue("{0}, selection {1} of {2}".format(self.result, self.foundIndex + 1, len(self.objsList) ) )
            self.foundIndex += 1 if self.nextIsDown else -1
        elif self.nextIsDown:
            self.resultText.setValue("{0}, selection at end".format(self.result) )
        else:
            self.resultText.setValue("{0}, selection at start".format(self.result) )
        

    def close(self, event=None):
        self.options.geometry = self.geometry()
        self.saveConfig()
        self.parent.focus_set()
        self.destroy()
        
    def saveConfig(self):
        self.modelManager.cntlr.config["findOptions"] = self.options
        self.modelManager.cntlr.saveConfig()
        
class FindOptions():
    def __init__(self):
        self.direction = "down"
        self.exprType = "text"
        self.all = False
        self.conceptLabel = False
        self.conceptName = False
        self.conceptSubs = False
        self.conceptPer = False
        self.conceptBal = False
        self.factLabel = False
        self.factName = False
        self.factValue = False
        self.factCntx = False
        self.factUnit = False
        self.priorExpressions = []
        self.geometry = None
