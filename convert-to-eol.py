import re
import argparse
from string import Template
import base64


TEMPLATE_FILE = 'exam_xml.template'
TEX_SYNTAXES = [r"texttt", "tabular", "CodeSnippet", "begin{choices}",
                r"enspace", r'\^ ', r'\\', r"\&", r'\%', r'\#', r'\}', r'\}']
KEY_DICT = {
        "MAIN": r"question\}\{(.*?)\}(.*?)\\begin\{choices\}",
        "FIG": r"\\AMClabel\{fig:(.*?)\}",
        "TEXTTT": r"\\texttt\{(.*?)\}",
        "TABULAR": r"%beginCodeSnippet(.*?)%endCodeSnippet",
        "CODE": r"\\begin\{tabular\}\{l\}(.*?)\\end\{tabular\}",
        "SCHED": r"\\begin\{tabular\}\{lll\}(.*?)\\end\{tabular\}",
        "CHOICES": r"\\begin\{choices\}(.*?)\\end\{choices\}",
        "DIV": r'<div style="font-family: monospace; background-color:#f8f8f8; padding:10px; margin:10px; color: #773333"> ',
        "SPAN" : r'<span style="font-family: monospace; background-color:#f8f8f8; color: #773333">',
        "FIGHTML": '<img src="@@PLUGINFILE@@/{}" alt="" role="presentation" class="img-responsive atto_image_button_text-bottom" width="80%"><br>',
        "FIGBASE64": '<file name="{}" path="/" encoding="base64">{}</file>',
        }

START_REPLACE_COMMON = {
        r"\textdegree": "°",
        r"\enspace": "&nbsp;&nbsp;&nbsp;&nbsp;",
        r"\correctchoice": r"\twrongchoice",
        r"\wrongchoice": r"\tcorrectchoice",
        r"\cdots": r"...",
        r"\_": "_",
        r"\$": "$",
        r"\#": "#",
        r"& \\": "<br>", # Fix in tex is better idea imo
        r"&\\": "<br>", # Fix in tex is better idea imo
        r"\\": "<br>",
        r"\^": "^",
        }

END_REPLACE_COMMON = {
        r"\&": "&",
        r"\%": "%",
        r"\{": "{",
        r"\}": "}",
        }

def extract_questions(filename):
    with open(filename, 'r') as file:
        questions = file.read().split(r"\element{")[1:]
        question_list = [r"\element{" + question for question in questions]
    return question_list

def create_markdown(template, examtitle, question_infos):
    (partname, questionname, mainquestion, figbase64, choices, points) = question_infos
    exam_part = template.format(examtitle=examtitle, partname=partname, questionname=questionname,
                                mainquestion=mainquestion, figfile=figbase64,
                                first_choice=choices[0], 
                                second_choice=choices[1], third_choice=choices[2],
                                forth_choice=choices[3], fifth_choice=choices[4],
                                first_point=points[0], 
                                second_point=points[1], third_point=points[2],
                                forth_point=points[3], fifth_point=points[4],
                                )
    return exam_part

def get_partname(question) -> str:
    return re.search(r"\\element\{(.*?)\}", question, re.DOTALL).group(1)

def get_figure(question) -> list:
    figure = re.search(KEY_DICT["FIG"], question, re.DOTALL)
    if figure:
        filename = f"{figure.group(1)}.png"
        with open(f"images/{filename}", "rb") as f:
            baseimg = base64.b64encode(f.read()).decode('utf-8')
        fightml = KEY_DICT["FIGHTML"].format(filename)
        figbase64 = KEY_DICT["FIGBASE64"].format(filename, baseimg)
        return fightml, figbase64
    return ('', '')

def get_questionname(question) -> str:
    return re.search(r"\\begin\{question\}\{(.*?)\}", question, re.DOTALL).group(1)

def get_mainquestion(fightml, figbase64, question):
    mainquestion = fightml + re.search(KEY_DICT["MAIN"], question, re.DOTALL).group(2)
    tabular = re.search(KEY_DICT["TABULAR"], mainquestion, re.DOTALL)
    if tabular:
        code = re.search(KEY_DICT["CODE"], tabular.group(1), re.DOTALL)
        sched = re.search(KEY_DICT["SCHED"], tabular.group(1), re.DOTALL)
        if code: # code question
            tabular = code2xml(code.group(1))
            mainquestion = re.sub(KEY_DICT["TABULAR"], tabular, mainquestion, flags=re.DOTALL)
        else: # scheduling questions
            tabular = sched2xml(sched.group(1))
            mainquestion = re.sub(KEY_DICT["TABULAR"], tabular, mainquestion, flags=re.DOTALL)
    mainquestion = re.sub(KEY_DICT["TEXTTT"], fr"{KEY_DICT['SPAN']}\1</span>", mainquestion)
    return remove_texsyntax_end(mainquestion)

def sched2xml(sched):
    cols = sched.split("<br>")
    split_len = len(re.sub(KEY_DICT["TEXTTT"], r"\1", cols[0]))//3
    lens = [split_len, split_len, 0]
    rows = []
    for col in cols[1:]:
        elems = col.split("&")
        elems = [elem+l*"&nbsp;" for elem, l  in zip(elems, lens)]
        rows.append("".join(elems))
    cols[0] = cols[0].replace("&", "&nbsp;&nbsp;&nbsp;&nbsp;")
    sched = '<br>'.join([cols[0]] + rows)
    sched = '\n'.join([re.sub(KEY_DICT["TEXTTT"], r"\1", line) for line in sched.splitlines()])
    return KEY_DICT["DIV"] + sched + " </div>"

def code2xml(code):
    xml_code = []
    for line in code.splitlines():
        xml_line = line.split(r"\texttt{")
        if len(xml_line) - 1:
            xml_line = ''.join(xml_line[1].rsplit("}", 1))
            xml_code.append(xml_line)
    return KEY_DICT["DIV"] + '\n'.join(xml_code) + " </div>"

def choice2xml(question):
    choices = re.search(KEY_DICT["CHOICES"], question, re.DOTALL).group(1).split(r"choice{")
    points = [100 if "correct" in choice else - 20 for choice in choices][:-1]
    choices = [choice.replace(r"\tcorrect", '').replace(r"t\wrong", '') for choice in choices]
    choices = [''.join(choice.rsplit("}", 1)[:-1]) for choice in choices]
    choices = choices[1:]

    # In case there is some code in choices
    new_choices = []
    for choice in choices:
        new_choice = re.search(KEY_DICT["TABULAR"], choice, re.DOTALL)
        if new_choice:
            new_choice = re.search(KEY_DICT["CODE"], new_choice.group(1), re.DOTALL).group(1)
            choice = code2xml(new_choice)
        new_choices.append(remove_texsyntax_end(choice))

    choices = [re.sub(KEY_DICT["TEXTTT"], fr"{KEY_DICT['SPAN']}\1</span>", choice) for choice in new_choices]
    return choices, points

def remove_texsyntax_start(tex_str):
    for key, value in START_REPLACE_COMMON.items(): # replacing some stuff since tex was crying before
        tex_str = tex_str.replace(key, value)
    return tex_str

def remove_texsyntax_end(tex_str):
    tex_str = re.sub(r"Figure(.*?)\}", "the figure", tex_str)
    for key, value in END_REPLACE_COMMON.items(): # replacing some stuff since tex was crying before
        tex_str = tex_str.replace(key, value)
    return tex_str


def get_from_tex(question_list):
    question_infolist = []
    for question in question_list:
        question = remove_texsyntax_start(question)
        partname, (fightml, figbase64), questionname = get_partname(question), get_figure(question), get_questionname(question)
        mainquestion = get_mainquestion(fightml, figbase64, question)
        choices, points = choice2xml(question)
        question_infolist.append((partname, questionname, mainquestion, 
                          figbase64, choices, points))
    return question_infolist

def check_xml(markdown_file, exam_part):
    for tex_syntax in TEX_SYNTAXES:
        if tex_syntax in exam_part:
            print(fr"`{tex_syntax}` in exam file `{markdown_file}`")

def main(filename, examtitle, markdown_file):
    question_list = extract_questions(filename)
    question_infolist = get_from_tex(question_list)

    with open(TEMPLATE_FILE, 'r') as t, open(markdown_file, 'w') as m:
        template = t.read()
        m.write(r'<?xml version = "1.0" encoding = "UTF-8" ?>')
        m.write("\n<quiz>")
        for question_infos in question_infolist:
            xml_exam_part = create_markdown(template, examtitle, question_infos)
            check_xml(markdown_file, xml_exam_part)
            m.write(xml_exam_part)

if __name__== "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--filename", type=str,
                        help="name of the tex file to be converted", default='')
    parser.add_argument("-t", "--examtitle", type=str,
                        help="name of the exam", default='')
    args = parser.parse_args()
    examtitle, filename, markdown_file = args.examtitle, args.filename+'.tex', args.filename.split("/")[1]+'.xml'
    if not args.examtitle:
        raise "Exam title need to be defined"
    if not args.filename:
        raise "File name need to be defined"

    main(filename, examtitle, markdown_file)
