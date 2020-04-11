from __future__ import print_function
from flask import Flask, render_template, make_response
from flask import redirect, request, jsonify, url_for, send_file

import io, os, uuid, pickle
from xml.etree.ElementTree import Element, SubElement
from xml.etree import ElementTree as ET
from xml.dom import minidom

app = Flask(__name__)
app.secret_key = 's3cr3t'
app.debug = True
app._static_folder = os.path.abspath("templates/static/")

project_name = 'libpng'
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
    os.system("dot -Tpng {}.dot -o {}.png".format(fn, fn))

def shorten(path):
    ls = path.split('/')
    idx = ls.index(project_name)
    return '/'.join(ls[idx+1:])

def create_dep_map():
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
    filename = "images/dep"
    ls = [(shorten(d), shorten(f), t) for (d,f,t) in ls]
    to_dot(ls, filename)
    return filename + ".png"

def structclassmap(root):
    #{TODO}: Handle Friends, Templates, Field variables
    ls = []
    # Do it for classes
    for c in root.findall(".//ClassDecl"):
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))

    # Do it for structs
    for c in root.findall(".//StructDecl"):
        # Inheritance edges
        for p in c.findall("./CXXBaseClassSpecifier"):
            ls.append((c.attrib['spelling'], p.attrib['type'], p.attrib['inheritance_kind']))
        # # dependency edges
        # for d in c.findall("./FIELD_DECL"):
        #     for t in d.findall(".//TYPE_REF"):
        #         ls.append((str(t.attrib['type'].split()[-1]), c.attrib['spelling'], d.attrib['access_specifier']))
    filename = "images/classmap"
    to_dot(ls, filename)
    return filename + ".png"

@app.route('/', methods=['GET'])
def index():
    title = 'Create the input'
    return render_template('layouts/index.html',
                           title=title)

@app.route('/images', methods=['GET'])
def getImage():
    return send_file(os.path.join('images', request.args.get('file'))+'.png',
        mimetype='image/gif')

@app.route('/dependency', methods=['GET'])
def results():
    title = 'Result'
    d = pickle.load(open('data/dependencies.p', 'rb'))
    return render_template('layouts/results.html',
                           title=title, dep = d)

@app.route('/dependencydev', methods=['GET'])
def dependency_dev():
    create_dep_map()
    title = "WIP: Spandan"
    return render_template('layouts/results_dev.html', title=title)

@app.route('/externdev', methods=['GET'])
def extern_dev():
    create_dep_map()
    title = "WIP: Dependency"
    return render_template('layouts/results_dev.html', title=title)

@app.route('/classmapdev', methods=['GET'])
def classmap_dev():
    croot = ET.parse("data/final_static.xml").getroot()
    structclassmap(croot)
    title = "WIP: Class"
    return render_template('layouts/classmap_dev.html', title=title)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
