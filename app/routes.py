from config import app, publish, store, socket, fingerprint
from flask import render_template, request, flash, redirect, url_for, jsonify, json
from models import *
import time
from forms import UserDefineForm, UserEnrollForm
import sys

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

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/index-temp')
def index_temp():
    return render_template('index-temp.html')


@app.route('/index-page')
def index_page():
    return render_template('index-page.html')


@app.route(
    '/settings')  # TODO: If no action is done on this page for about one minute, leads to Broken Pipe Eroor on terminal but yet everything works fine
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


@app.route('/get_all_users', methods=['GET'])
def get_all_users():  # TODO: Seems NOT enrolling new users when sensor memory is fresh - check again
    result = dict()
    result['status'] = 0  # No data found
    result['users'] = []

    # Retrieve all users from database
    users = db.table('users').get()

    for user in users:
        result['status'] = 1  # Data found
        result['users'].append({
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'code_melli': user['code_melli'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at'],
        })

    # Number of all users
    users_table_records_count = db.table('users').get().count()
    result['users_count'] = users_table_records_count

    return jsonify(result)


@app.route('/get_all_users_fingers', methods=['POST'])
def get_all_users_fingers():  # TODO: Seems NOT enrolling new users when sensor memory is fresh - check again
    result = dict()
    result['status'] = 0  # No data found
    result['users'] = []

    # Find all users from database
    users = db.table('users').get()

    for user in users:
        result['status'] = 1  # Data found
        result['users'].append({
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'code_melli': user['code_melli'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at'],
        })

    # count of all users
    users_table_records_count = db.table('users').get().count()
    result['users_count'] = users_table_records_count

    return jsonify(result)


@app.route('/enroll_handle_finger', methods=['POST'])
def enroll_handle_finger():
    our_result = {'status': 0}

    if request.method == 'POST':
        the_id = request.json['id']

        # flash('Currently used templates: ' + str(fingerprint.getTemplateCount()) + ' / ' + str(fingerprint.getStorageCapacity()))
        our_result['status'] = 1
        # Wait to read the finger
        while fingerprint.readImage() == 0:
            pass

        # Converts read image to characteristics and stores it in char buffer 1
        fingerprint.convertImage(0x01)

        # Checks if finger is already enrolled
        result = fingerprint.searchTemplate()
        position_number = result[0]

        if position_number >= 0:
            # flash('Template already exists at position #' + str(position_number))
            our_result['status'] = 2
            return jsonify(our_result)

        # flash('Remove finger...')
        our_result['status'] = 3
        time.sleep(3)
        # flash('Waiting for same finger again...')
        our_result['status'] = 4

        # Wait to read the finger again
        while fingerprint.readImage() == 0:
            pass

        # Converts read image to characteristics and stores it in char buffer 2
        fingerprint.convertImage(0x02)

        # Compares the char buffers
        if fingerprint.compareCharacteristics() == 0:
            # flash('Fingers do not match')
            our_result['status'] = 5
            return jsonify(our_result)
            # raise Exception('Fingers do not match')

        # Creates a template
        fingerprint.createTemplate()

        # Saves the template at new position number
        position_number = fingerprint.storeTemplate()
        # flash('Finger enrolled successfully!')
        our_result['status'] = 6
        # flash('New template position #' + str(position_number))
        our_result['status'] = 7
        db.table('fingers').insert(user_id=the_id, template_position=position_number)

        # flash('This user has been enrolled successfully.')
        our_result['status'] = 8

        return jsonify(our_result)


@app.route('/enroll_handle_rfid', methods=['POST'])
def enroll_handle_rfid():
    return 'Hi'


@app.route('/enroll_handle_finger_temp', methods=['POST'])
def enroll_handle_finger_temp():
    data = dict()
    data['id'] = request.form['user_id']
    return jsonify(data)


@app.route('/enroll_handle_rfid_temp', methods=['POST'])
def enroll_handle_rfid_temp():
    data = dict()
    data['id'] = request.form['user_id']
    return jsonify(data)
