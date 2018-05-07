from config import app, publish, store, socket, fingerprint
from flask import render_template, request, flash, redirect, url_for, jsonify, json
from models import *
import time
from forms import UserDefineForm, UserEnrollForm
from pprint import pprint
import os

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


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/settings_process')
def settings_process():
    our_result = dict()

    our_result['status'] = 200
    our_result['message'] = 'Nothing done yet.'
    our_result['members'] = []
    time.sleep(0.5)
    # Wait to read the finger
    while fingerprint.readImage() == 0:
        pass

    # Converts read image to characteristics and stores it in char buffer 1
    fingerprint.convertImage(0x01)

    # Checks if finger is already enrolled
    result = fingerprint.searchTemplate()
    position_number = result[0]

    if position_number >= 0:
        our_result['status'] = 201
        our_result['message'] = 'Template exists at position #' + str(position_number)

        user_id_associated_with_this_finger = db.table('fingers').where('template_position', position_number).pluck('user_id')

        admin_role_check_clause = db.table('users').where('id', user_id_associated_with_this_finger).pluck('is_admin')

        our_result['is_admin'] = admin_role_check_clause

        if admin_role_check_clause: # The finger belongs to an admin
            pprint("Hi ADMIN")

            # Retrieve all users from database
            users = db.table('users').get()

            # Loop in each user in users table
            for user in users:
                our_result['status'] = 1  # Data found

                # Retrieve all fingers related to that specific user
                this_user_related_fingers = db.table('fingers').where('user_id', user.id).get()

                # Add some information about that related finger of that specific user
                if this_user_related_fingers.count():
                    user_finger = []
                    for finger in this_user_related_fingers:
                        user_finger.append({
                            'id': finger['id'],
                            'position': finger['template_position'],
                            'created_at': finger['created_at']
                        })

                # Update result['members']
                our_result['members'].append({
                    'id': user['id'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'code_melli': user['code_melli'],
                    'created_at': user['created_at'],
                    'updated_at': user['updated_at'],
                    'related_fingers': user_finger
                })

            # Number of all users
            users_table_records_count = db.table('users').get().count()
            our_result['members_count'] = users_table_records_count

            return jsonify(our_result)


        else: # The finger does NOT belong to an admin
            pprint('You are NOT ADMIN')

        return jsonify(our_result)

    our_result['status'] = 202
    our_result['message'] = 'No match found.'

    return jsonify(our_result)

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
    # return render_template('user_enroll.html')
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
    our_result = dict()
    our_result['status'] = 0  # No data found
    our_result['members'] = []

    # Retrieve all users from database
    users = db.table('users').get()

    # Loop in each user in users table
    for user in users:
        our_result['status'] = 1  # Data found

        # Retrieve all fingers related to that specific user
        this_user_related_fingers = db.table('fingers').where('user_id', user.id).get()

        # Add some information about that related finger of that specific user
        if this_user_related_fingers.count():
            user_finger = []
            for finger in this_user_related_fingers:
                user_finger.append({
                    'id': finger['id'],
                    'position': finger['template_position'],
                    'created_at': finger['created_at']
                })

        # Update result['members']
        our_result['members'].append({
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'code_melli': user['code_melli'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at'],
            'related_fingers': user_finger
        })

    # Number of all users
    users_table_records_count = db.table('users').get().count()
    our_result['members_count'] = users_table_records_count

    return jsonify(our_result)


@app.route('/enroll_handle_rfid', methods=['POST'])
def enroll_handle_rfid():
    return 'Hi'


@app.route('/enroll_handle_finger_step_1', methods=['POST'])
def enroll_handle_finger_step_1():
    our_result = dict()
    our_result['status'] = []
    our_result['status'].append({
        'code': 0,
        'message': 'Nothing done yet.'
    })
    our_result['id'] = request.form['user_id'].encode("utf-8")

    if request.method == 'POST':
        our_result['status'].append({
            'code': 1,
            'message': 'Currently used templates: ' + str(fingerprint.getTemplateCount()) + ' / ' + str(
                fingerprint.getStorageCapacity())
        })
        pprint(our_result)

        # Wait to read the finger
        while fingerprint.readImage() == 0:
            pass

        # Converts read image to characteristics and stores it in char buffer 1
        fingerprint.convertImage(0x01)

        # Checks if finger is already enrolled
        result = fingerprint.searchTemplate()
        position_number = result[0]

        if position_number >= 0:
            our_result['status'].append({
                'code': 2,
                'message': 'Template already exists at position #' + str(position_number)
            })
            pprint(our_result)
            return jsonify(our_result)

        our_result['status'].append({
            'code': 3,
            'message': 'Remove finger...'
        })

        return jsonify(our_result)


@app.route('/enroll_handle_finger_step_2', methods=['POST'])
def enroll_handle_finger_step_2():
    our_result = dict()
    our_result['status'] = []
    our_result['id'] = request.form['user_id'].encode("utf-8")

    time.sleep(3)

    our_result['status'].append({
        'code': 4,
        'message': 'Waiting for same finger again...'
    })

    # Wait to read the finger again
    while fingerprint.readImage() == 0:
        pass

    # Converts read image to characteristics and stores it in char buffer 2
    fingerprint.convertImage(0x02)

    # Compares the char buffers
    if fingerprint.compareCharacteristics() == 0:
        our_result['status'].append({
            'code': 5,
            'message': 'Fingers do not match'
        })
        return jsonify(our_result)

    # Creates a template
    fingerprint.createTemplate()

    # Saves the template at new position number
    position_number = fingerprint.storeTemplate()
    our_result['status'].append({
        'code': 6,
        'message': 'Finger enrolled successfully!'
    })
    our_result['status'].append({
        'code': 7,
        'message': 'New template position #' + str(position_number)
    })
    db.table('fingers').insert(user_id=our_result['id'], template_position=position_number)

    our_result['status'].append({
        'code': 8,
        'message': 'This user has been enrolled successfully and inserted in the database.'
    })

    return jsonify(our_result)


@app.route('/enroll_handle_rfid_temp', methods=['POST'])
def enroll_handle_rfid_temp():
    data = dict()
    data['id'] = request.form['user_id'].encode("utf-8")
    pprint(data['id'])
    return jsonify(data)
