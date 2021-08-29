import pandas as pd
import requests
import sqlite3
import pathlib
import os
import os.path
import json
from flask import Flask, render_template, request, redirect
from flask_restful import Api, Resource


app = Flask(__name__)
path = pathlib.Path('database.db')
api = Api(app)

if not path.exists():
    conn = sqlite3.connect('database.db')
    conn.execute('CREATE TABLE files (comp_name TEXT, file_name TEXT, data TEXT)')
    conn.close()


@app.cli.command()
def custom_run():
    app.run()


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/')
def form1():
    return render_template('index.html', title="Home page")


@app.route('/verify', methods=['POST', 'GET'])
def verify():
    if request.method == 'POST':
        name = request.form['name']
        return redirect(f"/{name}")


@app.route('/files', methods=['POST', 'GET'])
def saved_files():
    file_list = []
    dirs = os.listdir(os.getcwd())
    for file in dirs:
        if '.csv' in file:
            file_list.append(file[:-4])
    if len(file_list):
        return render_template('savedfiles.html', data=file_list)
    else:
        return "No data files yet"


@app.route('/database', methods=['POST', 'GET'])
def saved_indatabes():
    output_list = []
    try:
        with sqlite3.connect("database.db") as con:
            con = con.cursor()
            con.execute("SELECT comp_name FROM files")
            records = con.fetchall()
            if not records:
                return "No data in database yet"
    except sqlite3.Error:
        con.rollback()
    for i in records:
        output_list.append(i[0])
    return render_template('indatabase.html', data=output_list)


@app.route('/database/<string:name>', methods=['POST', 'GET'])
def datescompany_from_dabase(name):
    out_str = ":" + name
    return redirect(f"/{out_str}")


def read_database(name):
    """ Get data from database for "name"  """
    try:
        with sqlite3.connect("database.db") as con:
            cur = con.cursor()
            cur.execute("SELECT data FROM files WHERE comp_name=?", (name,))
            data = cur.fetchone()
            if not data:
                return "No data in database yet"
    except sqlite3.Error:
        con.rollback()
    dr = pd.DataFrame([x.split(',') for x in data[0].split('\n')])
    return dr.to_html()


def write_to_database(name, file_name, text):
    """ Write data to database """
    try:
        with sqlite3.connect("database.db") as con:
            cur = con.cursor()
            cur.execute("SELECT comp_name, file_name FROM files WHERE comp_name=?", (name,))
            if cur.fetchone():
                cur.execute("UPDATE files SET data = ? WHERE comp_name = ?", (text, name))
            else:
                cur.execute("INSERT INTO files (comp_name, file_name, data) VALUES (?,?,?)", (name, file_name, text))
                con.commit()
    except sqlite3.Error:
        con.rollback()


@app.route('/<string:name>')
def verify_name(name):
    # Unification name parameter
    name = name.upper()

    # routing processing for database data
    if name[0] == ':':
        name = name[1:]
        return render_template('result.html', list=read_database(name), title=name+' data')
    file_name = name + '.csv'

    url_name = "https://query1.finance.yahoo.com/v7/finance/download/"+name+"" \
                "?period1=0&period2=9999999999&interval=1d&events=history&includeAdjustedClose=true"

    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

    r = requests.get(url_name, headers=headers)

    # exit when company name was not found
    if '404 Not Found:' in r.text:
        return render_template('result.html', data='No data found for: ' + name)

    # write data to database
    write_to_database(name, file_name, r.text)

    # write data to file
    with open(file_name, 'w+') as f:
        f.write(r.text)
    df = pd.read_csv(file_name)
    return render_template('result.html', data=df.to_html(), title=name+' data')


class DataView(Resource):
    """API function. Processing GET function for url ..../api/<string:name>
    Parameters:
        name - the name of the company for which you want to receive data
                if the data is not available for such company - a message
                 will be returned
    """
    @staticmethod
    def read_db_json(name):
        """ Get data from database for "name"  """
        try:
            with sqlite3.connect("database.db") as con:
                cur = con.cursor()
                cur.execute("SELECT data FROM files WHERE comp_name=?", (name,))
                data = cur.fetchone()
                if not data:
                    return {'message': 'company not found'}, 404
        except sqlite3.Error:
            con.rollback()

        return json.dumps(data[0])

    @classmethod
    def get(cls, name):
        return cls.read_db_json(name)


api.add_resource(DataView, '/api/<string:name>')

if __name__ == '__main__':
    app.run(debug=True)
