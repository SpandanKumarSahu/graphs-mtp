from __future__ import print_function
from flask import Flask, render_template, make_response, Markup
from flask import redirect, request, jsonify, url_for, send_file

import io, os, uuid, pickle, json
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

app = Flask(__name__)
app.secret_key = 's3cr3t'
app.debug = True
app._static_folder = os.path.abspath("templates/static/")

project_name = 'SimplComprTest'
CXX_EXTENSIONS = ['c', 'cpp', 'cc']

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

def shorten(path):
    ls = path.split('/')
    idx = ls.index(project_name)
    return '/'.join(ls[idx+1:])

def create_dep_map(fillMe=None, toDot=True):
    dep = pickle.load(open("data/dependencies.p", "rb"))
    ls = []
    for d in dep:
        #[TODO]: Improve checking mechanism
        if d.split('.').count('o') > 0:
            ls.append((dep[d], d, "SRC"))
            continue
        ls.extend([(f, d, "OBJ") for f in dep[d] if f.split('.').count('o') > 0])
        ls.extend([(f, d, "SO/DL") for f in dep[d] if f.split('.').count('so') > 0])
        ls.extend([(f, d, "AR") for f in dep[d] if f.split('.').count('a') > 0])
    ls = [(shorten(d), shorten(f), t) for (d,f,t) in ls]
    if fillMe is not None:
        fillMe.extend(ls)
    if toDot is True:
        filename = "templates/static/images/dep"
        to_dot(ls, filename)
        return filename + ".png"

def structclassmap(root):
    #{TODO}: Handle Friends, Templates, Field variables
    ls = []
    # Do it for classes
    for c in root.findall(".//ClassDecl"):
        try:
            ls.append(c.attrib['spelling'])
        except:
            continue
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))

    # Do it for structs
    for c in root.findall(".//StructDecl"):
        try:
            ls.append(c.attrib['spelling'])
        except:
            continue
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))
    filename = "templates/static/images/classmap"
    to_dot(ls, filename)
    return filename + ".png"

def create_extern_link(ls, croot):
    for var in croot.findall(".//VarDecl[@storage_class='extern']"):
        if 'def_id' not in var.attrib:
            continue
        name = var.attrib['type']+ " " + var.attrib['spelling']
        ls.append((name, shorten(var.attrib['file']), "REFERED"))
        for x in croot.findall('.//VarDecl[@id="'+var.attrib['def_id']+'"]'):
            ls.append((name, shorten(x.attrib['file']), "DEFINED"))
    for func in croot.findall(".//FunctionDecl[@storage_class='extern']"):
        if 'def_id' not in func.attrib:
            continue
        name = func.attrib['type']+ " " + func.attrib['spelling']
        ls.append((name, shorten(func.attrib['file']), "REFERED"))
        for x in croot.findall('.//FunctionDecl[@id="'+func.attrib['def_id']+'"]'):
            ls.append((name, shorten(x.attrib['file']), "DEFINED"))

def visDOT(filename):
    with open(filename, "r") as f:
        data = f.readlines()
    data = [x.strip() for x in data]
    data = data[0]+'; '.join(data[1:-1])+"; }"
    return data

def addDOT(filename, line, col, data):
    with open(filename, 'r') as f:
        content = f.readlines()
    content[line] = content[line][:col] + "'" + data + "';\n"
    with open(filename, 'w') as f:
        f.write(''.join(content))

def getExecutables():
    dep = pickle.load(open("data/dependencies.p", "rb"))
    ls = []
    for k in dep:
        if k == "compile_instrs":
            continue
        elif len(os.path.splitext(k)[1]) == 0:
            ls.append(shorten(k))
    return ls

@app.route('/', methods=['GET'])
def index():
    title = 'Create the input'
    return render_template('layouts/index.html',
                           title=title)

@app.route('/dependency', methods=['GET'])
def results():
    title = 'Result'
    d = pickle.load(open('data/dependencies.p', 'rb'))
    return render_template('layouts/results.html',
                           title=title, dep = d)

@app.route('/dependencydev', methods=['GET'])
def dependency_dev():
    create_dep_map()
    execs = getExecutables()
    data = visDOT('templates/static/images/dep.dot')
    # addDOT('templates/layouts/dependency_dev.html', 39, 16, data)
    title = "Dependency Map"
    return render_template('layouts/dependency_dev.html', data=json.dumps(data), title=title, execs=json.dumps(execs))

@app.route('/externdev', methods=['GET'])
def extern_dev():
    ls = []
    croot = ET.parse("data/final_static.xml").getroot()
    create_extern_link(ls, croot)
    symbols = list(set([x[0] for x in ls]))
    create_dep_map(ls, False)
    to_dot(ls, "templates/static/images/extern")
    data = visDOT("templates/static/images/extern.dot")
    title = "Extern Linkage"
    return render_template('layouts/extern_dev.html', title=title,
    data=data, symbols=symbols)

@app.route('/classmapdev', methods=['GET'])
def classmap_dev():
    croot = ET.parse("data/final_static.xml").getroot()
    structclassmap(croot)
    title = "WIP: Class"
    return render_template('layouts/classmap_dev.html', title=title)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
