import sys, pickle, os, json
from itertools import groupby
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

from functools import cmp_to_key

filename = "data/final.cfg"
key = "St5D7yHzyE5WRpHRGuGVB6r4t4HK47TRS69Gka7Pfc2d2wArVrmyPtUZbEUxVMrZ"
func2loc = {}
func2entry = {}
func2exit = {}
block2coverage = {}
func2calls = {}
func2spell = {}
blockGraph = {}
block2range = {}
numBlocks = {}
myCallGraph = {}
func2coverage = {}
stree = None

with open(filename, "r") as f:
    data = f.readlines()

data = [x.strip() for x in data]
data = [list(group) for k, group in groupby(data, lambda x: x == key) if not k]
basicBlocks = data[::2]
callGraph = data[1::2]

def to_dot (li, fn):
    with open(fn + '.dot', 'w') as fp:
        fp.write('digraph G{\n')
        for el in list(set(li)):
            if type(el) in [list, tuple]:
                fp.write('"{}"->"{}"[label="{}"]\n'.format(el[0], el[1], el[2]))
            else:
                fp.write('"{}"\n'.format(el))
        fp.write('}\n')
    os.system("sfdp -Tsvg -Goverlap=prism {}.dot -o {}.svg".format(fn, fn))

def range2List(ls):
    temp = ls[1:-1].split(':')
    temp = [int(x) for x in temp]
    return temp

def getCallInstanceRanges(func):
    ranges = []
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            for instance in caller.findall(".//CallExpr"):
                if 'ref_id' in instance.attrib:
                    ranges.append((stree.find('.//*[@id="'+instance.attrib['ref_id']+'"]')
                    .attrib['linkage_name'],
                    instance.attrib['range.start'],
                    instance.attrib['range.end']))
                else:
                    ranges.append((stree.find('.//*[@id="'+instance.attrib['def_id']+'"]')
                    .attrib['linkage_name'],
                    instance.attrib['range.start'],
                    instance.attrib['range.end']))
    return ranges

def getStartLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.start']

def getEndLoc(func):
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            return caller.attrib['range.end']

def processBB(bb):
    if len(bb) == 0:
        return
    func, loc = bb[0].split()
    func2loc[func] = loc
    n = int(bb[1])
    numBlocks[func] = n
    for i in range(2,2+n):
        id, ext, pred, succ = bb[i].split()
        currBlock = func+"#"+id
        block2coverage[currBlock] = False
        blockGraph[currBlock] = [func+"#"+str(x) for x in eval(succ)]
        if ext == "ENTRY":
            func2entry[func] = currBlock
            loc = getStartLoc(func)
            block2range[currBlock] = range2List(loc) + range2List(loc)
        elif ext == "EXIT":
            func2exit[func] = currBlock
            loc = getEndLoc(func)
            block2range[currBlock] = range2List(loc) + range2List(loc)
        else:
            block2range[currBlock] = eval(ext)
        if len(block2range[currBlock]) == 0:
            block2range[currBlock] = block2range[func+"#"+str(int(id)-1)]
    return processBB(bb[2+n:])

def processCGN(cgn):
    n = int(cgn[0])
    for i in range(1, 1+n):
        func, calls = cgn[i].split()
        func = func[:-1]
        for x in stree.findall('.//*[@linkage_name="'+func+'"]'):
            func2spell[func] = x.attrib['spelling']
        if calls[-2] == ',':
            calls = calls[1:-2].split(',')
        else:
            calls = []
        if func not in func2calls:
            func2calls[func] = set()
        func2calls[func].update(calls)

def locComapre(r1, r2):
    if not isinstance(r1, list):
        r1, r2 = range2List(r1), range2List(r2)
    if r1[0] == r2[0]:
        return r1[1] - r2[1]
    return r1[0] - r2[0]

def isContained(totRange, firstPoint, secondPoint):
    if locComapre(totRange[:2], firstPoint) <= 0 and locComapre(firstPoint, totRange[2:]) <= 0:
        return True
    elif locComapre(totRange[:2], secondPoint) <= 0 and locComapre(secondPoint, totRange[2:]) <= 0:
        return True
    else:
        return False

def createNewFunction(func):
    instanceNode = None
    for caller in stree.findall('.//*[@linkage_name="'+func+'"]'):
        if 'isDef' in caller.attrib:
            func2spell[func] = caller.attrib['spelling']
            func2loc[func] = caller.attrib['file']
            numBlocks[func] = 1
            currBlock = func+"#0"
            func2entry[func], func2exit[func] = currBlock, currBlock
            block2coverage[currBlock] = False
            blockGraph[currBlock] = []
            block2range[currBlock] = range2List(caller.attrib['range.start']) + range2List(caller.attrib['range.end'])
            break

def processBlockRange(block, ranges, visited):
    currRange = block2range[block]
    matchRanges = [x for x in ranges if isContained(currRange, range2List(x[1]), range2List(x[2]))]
    ranges = [x for x in ranges if x not in matchRanges]

    def match_cmp(a, b):
        return locComapre(a[2], b[2])
    matchRanges = sorted(matchRanges, key = cmp_to_key(match_cmp))

    func = block.split('#')[0]
    currBlock = block
    visited.add(currBlock)
    for match in matchRanges:
        newBlock = func+"#"+str(numBlocks[func])
        numBlocks[func] += 1
        block2coverage[newBlock] = False
        match1 = range2List(match[2])
        block2range[newBlock] = match1 + block2range[currBlock][2:]
        block2range[currBlock] = block2range[currBlock][:-2] + match1
        blockGraph[newBlock] = blockGraph[currBlock]
        if match[0] not in func2entry:
            createNewFunction(match[0])
        blockGraph[currBlock] = [func2entry[match[0]]]
        blockGraph[func2exit[match[0]]].append(newBlock)
        currBlock = newBlock
        visited.add(newBlock)
    return currBlock

def processFunc(func):
    ranges = getCallInstanceRanges(func)
    if len(ranges) == 0:
        return
    myCallGraph[func] = [x[0] for x in ranges]
    func2coverage[func] = False

    bfs = [func2entry[func]]
    visited = set()
    while(len(bfs) > 0):
        node = bfs[0]
        bfs = bfs[1:]
        visited.add(node)
        finalNode = processBlockRange(node, ranges, visited)
        for i in blockGraph[finalNode]:
            if i not in visited and i.split('#')[0] == func:
                bfs.append(i)

def processDump(ls):
    pass

stree = ET.parse("data/final_static.xml").getroot()

# Create the Static Call Graph
for cgn in callGraph:
    processCGN(cgn)

for i in func2calls:
    func2calls[i] = list(func2calls[i])

# Create the Basic Block Graph
for bb in basicBlocks:
    processBB(bb)


nonAritificalFuncs = list(func2loc.keys())
for func in nonAritificalFuncs:
    processFunc(func)

runFiles = ["data/sct_0_1.dump"]
for file in runFiles:
    data = open(file, 'r').readlines()
    data = [x.strip().split() for x in data]
    processDump(data)

# Store BlockGraph
ls = []
for block in blockGraph:
    for caller in blockGraph[block]:
        ls.append((block, caller, ""))

# json.dump(block2coverage, open("templates/static/images/block2coverage.json", 'w'), indent=4)
block2coverage = json.loads(open("templates/static/images/block2coverage.json", 'r').read())

to_dot(ls, "templates/static/images/cfg")
funcList = list(func2entry.keys())
block2labels = {k:"SampleCode" for k in blockGraph}
pickle.dump((funcList, block2coverage, block2labels), open("templates/static/images/cfg.pkl", "wb"))
