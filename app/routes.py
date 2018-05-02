from config import app, publish, store, socket, fingerPrint
from flask import render_template, request, flash, redirect, url_for, jsonify, json
from models import *
import time
from forms import UserDefineForm, UserEnrollForm

store['clients'] = []


# --------------#
#   Sockets     #
#               #
# --------------#
@socket.on('connect')
def socket_connect():
    socket.emit('auth', request.sid)
    store['clients'].append(request.sid)


@socket.on('disconnect')
def socket_disconnect():
    store['fingerPrintEnabled'] = False
    store['clients'].remove(request.sid)


@socket.on('setFingerPrintStatus')
def set_fingerprint_status(data):
    store['fingerPrintEnabled'] = data


# --------------#
#   Endpoints   #
#               #
# --------------#

@app.route('/index-temp')
def index_temp():
    return render_template('index-temp.html')


@app.route('/index-page')
def index_page():
    return render_template('index-page.html')


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/settings')  # TODO: If no action is done on this page for about one minute, leads to Broken Pipe Eroor on terminal but yet everything works fine
def settings():
    return render_template('settings.html')


# -------------------------#
#       User Define        #
# -------------------------#
@app.route('/user_define', methods=['POST', 'GET'])
def user_define():
    # f.readImage() #TODO: sensor should be off when on this page, unless it is needed

    form = UserDefineForm()

    if request.method == 'POST':  # TODO: form validation
        # Form NOT validated
        if form.validate() == 0:  # form.validate == False
            return render_template('user_define.html', form=form)
        # Form validated correctly
        elif form.validate() != 0:  # form.validate != False
            the_first_name = request.form['first_name']
            the_last_name = request.form['last_name']
            the_code_melli = request.form['code_melli']

            # TODO: (SOLVED) code_melli existence query
            code_melli_existence_clause = db.table('users').where('code_melli', the_code_melli).count()
            # code_melli_existence_clause = 'CODE MELLI EXISTS NOT'
            # code_melli_existence_clause = db.table('users').where_exists(db.table('users').select(db.raw(1)).where_raw('users.code_melli' == 23))

            # This code melli already exists.
            if code_melli_existence_clause != 0:
                flash('This code melli already exists.')
                return render_template('user_define.html', form=form)
            # This is a new code melli.
            elif code_melli_existence_clause == 0:
                db.table('users').insert(first_name=the_first_name, last_name=the_last_name, code_melli=the_code_melli)
                flash('The user has been successfully defined.')
                return render_template('user_define.html', form=form)
    elif request.method == 'GET':
        return render_template('user_define.html', form=form)


# -------------------------#
#       User Enroll        #
# -------------------------#
@app.route('/user_enroll', methods=['GET', 'POST'])
def user_enroll():  # TODO: Seems NOT enrolling new users when sensor memory is fresh - check again
    users = db.table('users').get()
    users_table_records_count = db.table('users').get().count()

    id_list = []
    first_name_list = []
    last_name_list = []
    code_melli_list = []
    created_at_list = []
    updated_at_list = []

    for user in users:
        id_list.append(str(user['id']))
        first_name_list.append(str(user['first_name']))
        last_name_list.append(str(user['last_name']))
        code_melli_list.append(str(user['code_melli']))
        created_at_list.append(str(user['created_at']))
        updated_at_list.append(str(user['updated_at']))

    return render_template('user_enroll.html',
                           users_table_records_count=users_table_records_count,
                           id_list=id_list,
                           first_name_list=first_name_list,
                           last_name_list=last_name_list,
                           code_melli_list=code_melli_list,
                           created_at_list=created_at_list,
                           updated_at_list=updated_at_list
                           )


@app.route('/users_table_drawer', methods=['GET', 'POST'])
def users_table_drawer():
    a = {'status': 2}

    # return jsonify(id_list, first_name_list, last_name_list, code_melli_list, created_at_list, updated_at_list)
    return jsonify(a)
