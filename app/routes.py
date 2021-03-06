from config import app, publish, store, socket, fingerprint
from flask import render_template, request, flash, redirect, url_for, jsonify, json, session
from models import *
import time
from forms import UserDefineForm, UserEnrollForm
from pprint import pprint
from global_variables import settings_timeout, enroll_finger_timeout, enroll_rfid_timeout
import RPi.GPIO as GPIO
import SimpleMFRC522
import spi

store['clients'] = []


def update_recorded_fingers_count():
    """
    Update the recorded fingers of a user in the 'users' table.

    """
    users = db.table('users').get()
    for user in users:
        recorded_fingers_count = db.table('fingers').where('user_id', user.id).count()
        db.table('users').where('id', user.id).update(recorded_fingers_count=recorded_fingers_count)
    return


# --------------#
#   Sockets     #
#               #
# --------------#
@socket.on('connect')
def socket_connect():
    """
    Connect the socket communication.

    """
    # store['fingerPrintEnabled'] = True
    socket.emit('auth', request.sid)
    store['clients'].append(request.sid)
    print('Socket Connect: ' + request.sid + '\n\n')


@socket.on('disconnect')
def socket_disconnect():
    """
    Disconnect the socket communication.

    """
    store['fingerPrintEnabled'] = False
    store['rfidEnabled'] = False
    store['clients'].remove(request.sid)
    print('Socket Disconnect: ' + request.sid + '\n\n')


@socket.on('setFingerPrintStatus')
def set_fingerprint_status(data):
    """
    Set the current fingerprint status.

    """
    store['fingerPrintEnabled'] = data


@socket.on('setRfidStatus')
def set_rfid_status(data):
    """
    Set the current rfid status.

    """
    store['rfidEnabled'] = data


# --------------#
#   Endpoints   #
#               #
# --------------#

@app.route('/')
@app.route('/index')
def index():
    """
    Return 'index.html' view.

    :return: index.html
    """
    return render_template('index.html')


@app.route('/index-page')
def index_page():
    """
    Return the 'index-page.html' view.

    PS: This method is not used currently, but is remained here for
    later uses.

    :return: index-page.html
    """
    return render_template('index-page.html')


@app.route('/settings')
def settings():
    """
    Return the 'settings.html'view.

    PS: This method is not used currently, but is remained here for
    later uses.

    :return: settings.html
    """
    return render_template('settings.html')


@app.route('/settings_process')
def settings_process():
    """
    This endpoint is triggered whenever someone tries to enter the 'settings'.

    """
    update_recorded_fingers_count()
    our_result = dict()
    # store['fingerPrintEnabled'] = False
    time.sleep(0.05)
    our_result['status'] = 200
    our_result['message'] = 'Nothing done yet.'
    our_result['members'] = []
    time.sleep(
        0.5)  # Makes sure to unset fingerprint sensor from index page in order not to submit log instead of settings approval on this endpoint

    check_time = time.time() + settings_timeout

    # Wait to read the finger for a specific time (as long as 'settings_timeout' variable)
    while (fingerprint.readImage() == 0) and (time.time() < check_time):
        pass

    if time.time() > check_time:
        our_result['status'] = 205
        our_result['message'] = 'Timeout is over.'

    else:
        our_result['status'] = 204
        our_result['message'] = 'No match found for this finger.'

    # Converts read image to characteristics and stores it in char buffer 1
    fingerprint.convertImage(0x01)

    # Checks if finger is already enrolled
    result = fingerprint.searchTemplate()
    position_number = result[0]

    if position_number >= 0:
        our_result['status'] = 201
        our_result['message'] = 'Template found at position #' + str(position_number)

        user_id_associated_with_this_finger = db.table('fingers').where('template_position', position_number).pluck(
            'user_id')

        admin_role_check_clause = db.table('users').where('id', user_id_associated_with_this_finger).pluck('is_admin')

        our_result['is_admin'] = admin_role_check_clause

        if admin_role_check_clause:  # The finger belongs to an admin
            pprint("Hi ADMIN")

            # Retrieve all users from database
            users = db.table('users').get()

            # Loop in each user in users table
            for user in users:
                our_result['status'] = 202  # Data found on users table

                recorded_fingers_count = Finger.where('user_id', user.id).count()
                maximum_allowed_fingers = db.table('users').where('id', user.id).pluck('maximum_allowed_fingers')
                is_active = db.table('users').where('id', user.id).pluck('is_active')

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

                else:  # This user has no registered finger.
                    user_finger = []

                unique_id_clause = db.table('rfid_cards').where('user_id', user['id']).count()

                if unique_id_clause:
                    unique_id = db.table('rfid_cards').where('user_id', user['id']).pluck('unique_id')
                    unique_id = str(unique_id)
                else:
                    unique_id = ''

                # Update result['members']
                our_result['members'].append({
                    'id': user['id'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'code_melli': user['code_melli'],
                    'created_at': user['created_at'],
                    'updated_at': user['updated_at'],
                    'related_fingers': user_finger,
                    'rfid_unique_id': unique_id,
                    'recorded_fingers_count': recorded_fingers_count,
                    'maximum_allowed_fingers': maximum_allowed_fingers,
                    'is_active': is_active
                })

            # Number of all users
            users_table_records_count = db.table('users').get().count()
            our_result['members_count'] = users_table_records_count

            return jsonify(our_result)

        else:  # The finger does NOT belong to an admin
            pprint('You are NOT ADMIN')
            our_result['status'] = 203
            our_result['is_admin'] = admin_role_check_clause
            our_result['message'] = 'Sorry, you are not allowed to enter settings.'

        return jsonify(our_result)

    return jsonify(our_result)


@app.route('/user_logs_process', methods=['GET', 'POST'])
def user_logs_process():
    """
    This endpoint is triggered when the admin tries to see the details about each user.

    """
    our_result = dict()

    our_result['status'] = 300
    our_result['message'] = 'Nothing done yet.'

    our_result['id'] = request.form['user_id'].encode("utf-8")

    our_result['reports'] = ''

    log_associated_with_this_user_clause = db.table('user_logs').where('user_id', our_result['id']).get().count()

    if log_associated_with_this_user_clause:  # This user_id has at least one record in user_logs table
        our_result['status'] = 301
        our_result['message'] = 'This user has at least one record.'

        all_logs_associated_with_this_user = db.table('user_logs').where('user_id', our_result['id']).order_by(
            'id', 'desc').get()

        user_report = []
        for user_log in all_logs_associated_with_this_user:
            user_report.append({
                'effected_at': str(user_log['effected_at']),
                'type': str(user_log['type']),
                'device': str(user_log['device'])
            })

        our_result['reports'] = user_report

    else:  # This user_id has no record in user_logs table
        our_result['status'] = 302
        our_result['message'] = 'This user has no records yet.'

    return jsonify(our_result)


# -------------------------#
#       User Define        #
# -------------------------#
@app.route('/user_define', methods=['POST', 'GET'])
def user_define():
    """
    This endpoint is triggered whenever the admin tries to define a new user.

    PS: This method is not used currently, but is remained here for
    later uses.
    """

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
    """
    Enroll a new user.

    PS: This method is not used currently, but is remained here for
    later uses.

    :return:
    """
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
    """
    This endpoint is triggered whenever someone tries to enter the settings.

    PS: This method is not used currently, but is remained here for
    later uses.

    """
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

        is_active = db.table('users').where('id', user['id']).pluck('is_active')

        # Add some information about that related finger of that specific user
        if this_user_related_fingers.count():
            user_finger = []
            for finger in this_user_related_fingers:
                user_finger.append({
                    'id': finger['id'],
                    'position': finger['template_position'],
                    'created_at': finger['created_at']
                })

        else:
            user_finger = []

        # Update result['members']
        our_result['members'].append({
            'id': user['id'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'code_melli': user['code_melli'],
            'created_at': user['created_at'],
            'updated_at': user['updated_at'],
            'related_fingers': user_finger,
            'is_active': is_active
        })

    # Number of all users
    users_table_records_count = db.table('users').get().count()
    our_result['members_count'] = users_table_records_count

    return jsonify(our_result)


@app.route('/enroll_handle_finger_step_1', methods=['GET', 'POST'])
def enroll_handle_finger_step_1():
    """
    This endpoint is triggered whenever the admin tries to enroll a new finger for the user (step 1).

    """
    our_result = dict()
    our_result['status'] = 400
    our_result['message'] = 'Nothing done yet.'

    # our_result['id'] = 31 # Manual test without ajax
    our_result['id'] = request.form['user_id'].encode("utf-8")
    session['key'] = str(our_result['id'])

    check_time = time.time() + enroll_finger_timeout

    recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
    maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')

    if recorded_fingers_count < maximum_allowed_fingers:
        # Wait to read the finger
        while (fingerprint.readImage() == 0) and (time.time() < check_time):
            pass

        if time.time() > check_time:
            our_result['status'] = 403
            our_result['message'] = 'Timeout is over.'
            return jsonify(our_result)

        # Converts read image to characteristics and stores it in char buffer 1
        fingerprint.convertImage(0x01)

        # Checks if finger is already enrolled
        result = fingerprint.searchTemplate()
        position_number = result[0]

        if position_number >= 0:
            our_result['status'] = 401
            our_result['message'] = 'This finger already has been enrolled.'

            pprint(our_result)
            return jsonify(our_result)

        our_result['status'] = 402
        our_result['message'] = 'Pick up your finger.'

        return jsonify(our_result)


@app.route('/enroll_handle_finger_step_2', methods=['GET', 'POST'])
def enroll_handle_finger_step_2():
    """
    This endpoint is triggered whenever the admin tries to enroll a new finger for the user (step 2).

    """
    our_result = dict()
    our_result['status'] = 410
    our_result['message'] = 'Waiting for the same finger again.'
    our_result['id'] = session.pop('key', None)

    time.sleep(3)

    check_time = time.time() + enroll_finger_timeout

    # Wait to read the finger again
    while (fingerprint.readImage() == 0) and (time.time() < check_time):
        pass

    if time.time() > check_time:
        our_result['status'] = 414
        our_result['message'] = 'Timeout is over.'
        return jsonify(our_result)

    # Converts read image to characteristics and stores it in char buffer 2
    fingerprint.convertImage(0x02)

    # Compares the char buffers
    if fingerprint.compareCharacteristics() == 0:
        our_result['status'] = 411
        our_result['message'] = 'Fingers do not match'
        return jsonify(our_result)

    # Creates a template
    fingerprint.createTemplate()

    # Saves the template at new position number
    position_number = fingerprint.storeTemplate()

    our_result['status'] = 412
    our_result['message'] = 'Finger enrolled successfully in fingerprint sensor memory at template position #' + str(
        position_number)

    db.table('fingers').insert(user_id=our_result['id'], template_position=position_number)

    update_recorded_fingers_count()

    our_result['member'] = []

    recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
    maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')
    is_active = db.table('users').where('id', our_result['id']).pluck('is_active')

    # Retrieve all fingers related to this specific user
    this_user_related_fingers = db.table('fingers').where('user_id', our_result['id']).get()

    # this_user = db.table('users').where('id', int(our_result['id'])).get()
    this_user = User.find(int(our_result['id']))

    user_finger = []
    # Add some information about that related finger of that specific user
    if this_user_related_fingers.count():
        for finger in this_user_related_fingers:
            user_finger.append({
                'id': finger['id'],
                'position': finger['template_position'],
                'created_at': finger['created_at']
            })

    unique_id_clause = db.table('rfid_cards').where('user_id', this_user.id).count()

    if unique_id_clause:
        unique_id = db.table('rfid_cards').where('user_id', this_user.id).pluck('unique_id')
        unique_id = str(unique_id)
    else:
        unique_id = ''

    # Update result['members']
    our_result['member'].append({
        'id': this_user.id,
        'first_name': this_user.first_name,
        'last_name': this_user.last_name,
        'code_melli': this_user.code_melli,
        'created_at': this_user.created_at,
        'updated_at': this_user.updated_at,
        'related_fingers': user_finger,
        'rfid_unique_id': unique_id,
        'recorded_fingers_count': recorded_fingers_count,
        'maximum_allowed_fingers': maximum_allowed_fingers,
        'is_active': is_active
    })

    our_result['status'] = 413
    our_result['message'] = 'This finger has been enrolled successfully and inserted in the fingers table.'

    maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')
    our_result['maximum_allowed_fingers'] = maximum_allowed_fingers
    updated_recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
    # updated_recorded_fingers_count = recorded_fingers_count + 1
    db.table('users').where('id', our_result['id']).update(recorded_fingers_count=updated_recorded_fingers_count)
    our_result['recorded_fingers_count'] = updated_recorded_fingers_count
    our_result['status'] = 415
    our_result['message'] = 'This finger has been added to recorded fingers count in users table.'

    return jsonify(our_result)


@app.route('/enroll_handle_rfid', methods=['GET', 'POST'])
def enroll_handle_rfid():
    """
    This endpoint is triggered whenever the admin tries to enroll a new rfid card for the user.

    """
    reader = SimpleMFRC522.SimpleMFRC522()
    try:
        our_result = dict()
        our_result['id'] = request.form['user_id'].encode("utf-8")

        rfid_owner_user_id = str(our_result['id'])

        our_result['status'] = 500
        our_result['message'] = 'Place your tag to be written please.'

        check_time = time.time() + enroll_rfid_timeout

        while time.time() < check_time:
            spi.openSPI()
            reader.write(rfid_owner_user_id)
            # spi.closeSPI()
            our_result['status'] = 501
            our_result['message'] = 'Tag has been written successfully on the card.'

            unique_id, rfid_owner_user_id = reader.read()

            unique_id = str(unique_id)

            unique_id_check_clause = db.table('rfid_cards').where('unique_id', unique_id).count()

            if unique_id_check_clause:
                db.table('rfid_cards').where('unique_id', unique_id).update(
                    user_id=our_result['id'])  # TODO: update 'updated_at'

            else:
                db.table('rfid_cards').insert(user_id=our_result['id'], unique_id=unique_id)

            our_result['status'] = 503
            our_result['message'] = 'Tag has been written successfully on rfid_cards table.'

            our_result['member'] = []

            recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
            maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')
            is_active = db.table('users').where('id', our_result['id']).pluck('is_active')

            # Retrieve all fingers related to this specific user
            this_user_related_fingers = db.table('fingers').where('user_id', our_result['id']).get()

            this_user = User.find(int(our_result['id']))

            user_finger = []
            # Add some information about that related finger of that specific user
            if this_user_related_fingers.count():
                for finger in this_user_related_fingers:
                    user_finger.append({
                        'id': finger['id'],
                        'position': finger['template_position'],
                        'created_at': finger['created_at']
                    })

            # Update result['member']
            our_result['member'].append({
                'id': this_user.id,
                'first_name': this_user.first_name,
                'last_name': this_user.last_name,
                'code_melli': this_user.code_melli,
                'created_at': this_user.created_at,
                'updated_at': this_user.updated_at,
                'related_fingers': user_finger,
                'rfid_unique_id': unique_id,
                'recorded_fingers_count': recorded_fingers_count,
                'maximum_allowed_fingers': maximum_allowed_fingers,
                'is_active': is_active
            })

            return jsonify(our_result)

        if time.time() > check_time:
            our_result['status'] = 502
            our_result['message'] = 'Timeout is over.'
            return jsonify(our_result)

    finally:
        GPIO.cleanup()


@app.route('/omit_rfid_card', methods=['GET', 'POST'])
def omit_rfid_card():
    """
    This endpoint is triggered whenever the admin tries to omit a defined rfid card.

    """
    our_result = dict()
    our_result['status'] = 600
    our_result['message'] = 'Nothing is done yet.'

    our_result['id'] = request.form['user_id'].encode("utf-8")
    rfid_owner_user_id = str(our_result['id'])

    db.table('rfid_cards').where('user_id', rfid_owner_user_id).delete()

    our_result['status'] = 601
    our_result['message'] = 'This rfid card does NOT belong to this user anymore.'

    our_result['member'] = []

    recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
    maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')
    is_active = db.table('users').where('id', our_result['id']).pluck('is_active')

    # Retrieve all fingers related to this specific user
    this_user_related_fingers = db.table('fingers').where('user_id', our_result['id']).get()

    this_user = User.find(int(our_result['id']))

    user_finger = []
    # Add some information about that related finger of that specific user
    if this_user_related_fingers.count():
        for finger in this_user_related_fingers:
            user_finger.append({
                'id': finger['id'],
                'position': finger['template_position'],
                'created_at': finger['created_at']
            })

    unique_id_clause = db.table('rfid_cards').where('user_id', this_user.id).count()

    if unique_id_clause:
        unique_id = db.table('rfid_cards').where('user_id', this_user.id).pluck('unique_id')
        unique_id = str(unique_id)
    else:
        unique_id = ''

    # Update result['members']
    our_result['member'].append({
        'id': this_user.id,
        'first_name': this_user.first_name,
        'last_name': this_user.last_name,
        'code_melli': this_user.code_melli,
        'created_at': this_user.created_at,
        'updated_at': this_user.updated_at,
        'related_fingers': user_finger,
        'rfid_unique_id': unique_id,
        'recorded_fingers_count': recorded_fingers_count,
        'maximum_allowed_fingers': maximum_allowed_fingers,
        'is_active': is_active
    })

    return jsonify(our_result)


@app.route('/omit_single_fingerprint_per_user', methods=['GET', 'POST'])
def omit_single_fingerprint_per_user():
    """
    This endpoint is triggered whenever the admin tries to omit a single fingerprint of the user.

    """
    our_result = dict()
    our_result['status'] = 700
    our_result['message'] = 'Nothing is done yet.'

    our_result['id'] = request.form['user_id'].encode("utf-8")
    our_result['id_primary_in_fingers_table'] = request.form['id_primary'].encode("utf-8")

    this_template_position = db.table('fingers').where('id', our_result['id_primary_in_fingers_table']).pluck(
        'template_position')

    db.table('fingers').where('template_position', this_template_position).delete()
    fingerprint.deleteTemplate(int(this_template_position))  # Deletes fingerprint from fingerprint sensor memory

    update_recorded_fingers_count()

    our_result['status'] = 701
    our_result['message'] = 'This fingerprint is NOT valid anymore.'

    our_result['member'] = []

    recorded_fingers_count = Finger.where('user_id', our_result['id']).count()
    maximum_allowed_fingers = db.table('users').where('id', our_result['id']).pluck('maximum_allowed_fingers')
    is_active = db.table('users').where('id', our_result['id']).pluck('is_active')

    # Retrieve all fingers related to this specific user
    this_user_related_fingers = db.table('fingers').where('user_id', our_result['id']).get()

    this_user = User.find(int(our_result['id']))

    user_finger = []
    # Add some information about that related finger of that specific user
    if this_user_related_fingers.count():
        for finger in this_user_related_fingers:
            user_finger.append({
                'id': finger['id'],
                'position': finger['template_position'],
                'created_at': finger['created_at']
            })

    unique_id_clause = db.table('rfid_cards').where('user_id', this_user.id).count()

    if unique_id_clause:
        unique_id = db.table('rfid_cards').where('user_id', this_user.id).pluck('unique_id')
        unique_id = str(unique_id)
    else:
        unique_id = ''

    # Update result['members']
    our_result['member'].append({
        'id': this_user.id,
        'first_name': this_user.first_name,
        'last_name': this_user.last_name,
        'code_melli': this_user.code_melli,
        'created_at': this_user.created_at,
        'updated_at': this_user.updated_at,
        'related_fingers': user_finger,
        'rfid_unique_id': unique_id,
        'recorded_fingers_count': recorded_fingers_count,
        'maximum_allowed_fingers': maximum_allowed_fingers,
        'is_active': is_active
    })

    return jsonify(our_result)


@app.route('/activate_user', methods=['GET', 'POST'])
def activate_user():
    """
    This endpoint is triggered whenever the admin tries to activate a user.

    """
    our_result = dict()
    our_result['status'] = 800
    our_result['message'] = 'Nothing done yet.'

    our_result['id'] = request.form['user_id'].encode("utf-8")

    db.table('users').where('id', our_result['id']).update(is_active=1)

    our_result['status'] = 801
    our_result['message'] = 'This user has been activated.'

    return jsonify(our_result)


@app.route('/deactivate_user', methods=['GET', 'POST'])
def deactivate_user():
    """
    This endpoint is triggered whenever the admin tries to deactivate a user.

    """
    our_result = dict()
    our_result['status'] = 900
    our_result['message'] = 'Nothing done yet.'

    our_result['id'] = request.form['user_id'].encode("utf-8")

    db.table('users').where('id', our_result['id']).update(is_active=0)

    our_result['status'] = 901
    our_result['message'] = 'This user has been activated.'

    return jsonify(our_result)
